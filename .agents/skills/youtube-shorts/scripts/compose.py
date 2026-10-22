#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.json(씬 매니페스트) → 최종 9:16 mp4 합성 (순수 ffmpeg).

씬별로:
  - 비주얼이 이미지면 Ken Burns(무료 모션), 영상이면 1080x1920 cover 로 맞춤
  - 그 위에 씬 한글 자막(.ass)을 구움
  - 씬 나레이션 오디오를 붙임(없으면 무음)
그 다음 모든 씬 세그먼트를 이어붙이고, (선택)BGM을 깔고, 30초 미만으로 자른다.

build.json 예:
{
  "width":1080,"height":1920,"fps":30,
  "font_file":"C:/Windows/Fonts/malgun.ttf","font_name":"Malgun Gothic",
  "bgm":null,"bgm_gain_db":-20,"max_sec":29,
  "out":"final.mp4",
  "scenes":[
    {"visual":"scenes/01.jpg","audio":"audio/01.mp3","subtitle":"첫 문장"},
    {"visual":"scenes/02.mp4","audio":"audio/02.mp3","subtitle":"둘째 문장"}
  ]
}
사용: python compose.py build.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "engines"))
import toolpaths  # noqa: E402
import subtitles  # noqa: E402
import kenburns  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1500:] + "\n")
        raise RuntimeError("ffmpeg 실패 (code %s)" % r.returncode)
    return r


def _video_graph(base_vf, blur, ass_file):
    """씬 비디오 필터그래프. blur=[[x,y,w,h],...] 영역을 boxblur로 가린 뒤 자막을 굽는다.
    좌표는 출력(1080x1920) 기준.
    """
    if not blur:
        return "[0:v]%s,ass=%s:fontsdir=.[v]" % (base_vf, ass_file)
    parts = ["[0:v]%s[base]" % base_vf]
    n = len(blur)
    labels = "".join(["[m]"] + ["[c%d]" % k for k in range(n)])
    parts.append("[base]split=%d%s" % (n + 1, labels))
    cur = "m"
    for k, box in enumerate(blur):
        x, y, w, h = [int(v) for v in box]
        parts.append("[c%d]crop=%d:%d:%d:%d,boxblur=20:3[b%d]" % (k, w, h, x, y, k))
        out = "o%d" % k
        parts.append("[%s][b%d]overlay=%d:%d[%s]" % (cur, k, x, y, out))
        cur = out
    parts.append("[%s]ass=%s:fontsdir=.[v]" % (cur, ass_file))
    return ";".join(parts)


def probe_dur(ffprobe, path):
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        return None


def compose(build_path):
    ff = toolpaths.ffmpeg()
    fp = toolpaths.ffprobe()
    if not ff or not fp:
        raise SystemExit("ffmpeg/ffprobe 를 찾을 수 없습니다 (toolpaths).")

    build = json.loads(Path(build_path).read_text(encoding="utf-8"))
    root = Path(build_path).resolve().parent
    W = int(build.get("width", 1080))
    H = int(build.get("height", 1920))
    FPS = int(build.get("fps", 30))
    MAX = float(build.get("max_sec", 29))
    silent = bool(build.get("silent"))   # True면 최종 영상 무음(TTS는 타이밍/자막용으로만)
    font_name = build.get("font_name", "Malgun Gothic")
    font_file = build.get("font_file", "C:/Windows/Fonts/malgun.ttf")
    out = (root / build.get("out", "final.mp4")).resolve()

    tmp = out.parent / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    # 폰트를 tmp 로 복사해 fontsdir=. 로 참조(드라이브문자 콜론 이스케이프 회피)
    if Path(font_file).is_file():
        shutil.copy(font_file, tmp / "font.ttf")

    def rel(p):
        p = Path(p)
        return p if p.is_absolute() else (root / p)

    segs = []
    total = 0.0
    for i, sc in enumerate(build["scenes"], 1):
        visual = rel(sc["visual"])
        audio = sc.get("audio")
        audio = rel(audio) if audio else None
        dur = probe_dur(fp, audio) if audio else None
        if not dur:
            dur = float(sc.get("dur", 4.0))
        text = sc.get("subtitle", "")

        subtitles.write_ass(tmp / ("sub_%02d.ass" % i), text, dur, W, H, font_name,
                            word_spans=sc.get("word_spans"),
                            badge=build.get("badge"), notice=build.get("notice"))
        is_img = visual.suffix.lower() in IMAGE_EXT
        if is_img:
            base_vf = kenburns.kenburns_vf(dur, FPS, W, H)
        else:
            base_vf = kenburns.fit_video_vf(dur, FPS, W, H)
        vf = _video_graph(base_vf, sc.get("blur"), "sub_%02d.ass" % i)

        seg = "seg_%02d.mp4" % i
        cmd = [ff, "-y"]
        if is_img:
            cmd += ["-loop", "1", "-i", str(visual)]
        else:
            # REMIX: 소스 클립에서 start(초)부터 컷. 지정 시 해당 구간부터 사용.
            start = sc.get("start")
            if start is not None:
                cmd += ["-ss", "%.3f" % float(start)]
            cmd += ["-i", str(visual)]
        if audio and not silent:
            cmd += ["-i", str(audio)]
        else:
            # 무음(silent)이거나 오디오 없음 → 무음 트랙. dur은 위에서 TTS로 계산됨(타이밍 유지).
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        cmd += ["-filter_complex", vf, "-map", "[v]", "-map", "1:a",
                "-t", "%.3f" % dur,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
                "-c:a", "aac", "-ar", "48000", "-ac", "2", seg]
        print("[compose] 씬 %d: %s (%.2fs, %s)"
              % (i, visual.name, dur, "이미지" if is_img else "영상"))
        run(cmd, cwd=str(tmp))
        segs.append(seg)
        total += dur

    # 이어붙이기 (동일 코덱/파라미터 → concat demuxer copy)
    (tmp / "list.txt").write_text(
        "".join("file '%s'\n" % s for s in segs), encoding="utf-8")
    concat = "concat.mp4"
    try:
        run([ff, "-y", "-f", "concat", "-safe", "0", "-i", "list.txt",
             "-c", "copy", concat], cwd=str(tmp))
    except RuntimeError:
        # copy 실패 시 재인코딩 폴백
        run([ff, "-y", "-f", "concat", "-safe", "0", "-i", "list.txt",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-ar", "48000", "-ac", "2", concat], cwd=str(tmp))

    cap = min(total, MAX)
    bgm = build.get("bgm")
    out.parent.mkdir(parents=True, exist_ok=True)
    if bgm and not silent and rel(bgm).is_file():
        gain = build.get("bgm_gain_db", -20)
        fc = ("[1:a]volume=%sdB,aloop=loop=-1:size=2000000000[b];"
              "[0:a][b]amix=inputs=2:duration=first:dropout_transition=0[a]"
              % gain)
        run([ff, "-y", "-i", str(tmp / concat), "-i", str(rel(bgm)),
             "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-t", "%.3f" % cap, str(out)])
    else:
        run([ff, "-y", "-i", str(tmp / concat), "-c", "copy",
             "-t", "%.3f" % cap, str(out)])

    final_dur = probe_dur(fp, out)
    print("[compose] 완료: %s  (%.2fs, 씬 %d개, 상한 %.0fs)"
          % (out, final_dur or cap, len(segs), MAX))
    if final_dur and final_dur >= 30:
        print("[경고] 길이가 30초 이상입니다. 대본을 더 줄이세요.")
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("build", help="build.json 경로")
    a = ap.parse_args()
    compose(a.build)
