#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""유튜브 쇼츠 썸네일(720x1280) 생성.

영상의 하이라이트 장면을 캡처해 상단에 2줄 문구를 얹는다.
  윗줄 = 파랑, 아랫줄 = 흰색. 굵은 외곽선(주아체 느낌).

CLI:
  python thumbnail.py <src(영상/이미지)> <out.png> --top "윗줄" --bottom "아랫줄" [--at 2.0]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolpaths  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

W, H = 720, 1280
JUA = str(Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Jua-Regular.ttf")
BLUE = "&H00F4C635&"   # 하늘색(#35C6F4)
WHITE = "&H00FFFFFF&"


def _fs(top, bottom):
    longest = max(len(top or " "), len(bottom or " "), 1)
    # 가로폭을 꽉 채우도록 크게(주아체 글자폭 보정 0.82)
    fs = int((W - 36) / (longest * 0.82))
    return max(64, min(150, fs))


def _ass(top, bottom, font_name):
    fs = _fs(top, bottom)
    top_mv = 72
    bot_mv = top_mv + int(fs * 1.28)
    return """[Script Info]
ScriptType: v4.00+
PlayResX: %d
PlayResY: %d
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TOP,%s,%d,%s,%s,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,11,2,8,18,18,%d,1
Style: BOT,%s,%d,%s,%s,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,11,2,8,18,18,%d,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,TOP,,0,0,0,,%s
Dialogue: 0,0:00:00.00,0:00:10.00,BOT,,0,0,0,,%s
""" % (W, H, font_name, fs, BLUE, BLUE, top_mv,
       font_name, fs, WHITE, WHITE, bot_mv,
       (top or "").strip(), (bottom or "").strip())


def make(src, out, top, bottom, at=None, font_file=JUA, font_name="Jua"):
    ff = toolpaths.ffmpeg()
    fp = toolpaths.ffprobe()
    if not ff:
        raise SystemExit("ffmpeg 없음")
    tmp = Path(tempfile.mkdtemp(prefix="cs_thumb_"))
    if Path(font_file).is_file():
        shutil.copy(font_file, tmp / "font.ttf")
    if at is None:
        try:
            d = float(subprocess.run(
                [fp, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(src)],
                capture_output=True, text=True).stdout.strip())
            at = max(0.2, d / 2)
        except (ValueError, TypeError):
            at = 1.0
    base = tmp / "base.png"
    subprocess.run([ff, "-y", "-ss", str(at), "-i", str(src), "-frames:v", "1",
                    "-vf", "scale=%d:%d:force_original_aspect_ratio=increase,"
                    "crop=%d:%d" % (W, H, W, H), str(base)],
                   capture_output=True)
    if not base.is_file():
        raise SystemExit("프레임 캡처 실패: %s" % src)
    (tmp / "t.ass").write_text(_ass(top, bottom, font_name), encoding="utf-8")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([ff, "-y", "-i", "base.png", "-vf",
                        "ass=t.ass:fontsdir=.", "-frames:v", "1", str(out.resolve())],
                       cwd=str(tmp), capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if not out.is_file():
        sys.stderr.write(r.stderr[-800:] + "\n")
        raise SystemExit("썸네일 생성 실패")
    return str(out)


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--top", required=True)
    ap.add_argument("--bottom", required=True)
    ap.add_argument("--at", type=float, default=None)
    a = ap.parse_args()
    print("[thumbnail] " + make(a.src, a.out, a.top, a.bottom, a.at))


if __name__ == "__main__":
    _main()
