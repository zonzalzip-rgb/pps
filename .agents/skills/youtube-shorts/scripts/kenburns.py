# -*- coding: utf-8 -*-
"""정지 이미지에 무료 Ken Burns(천천히 확대/이동) 모션을 주는 ffmpeg 필터.

유료 image-to-video 를 아끼기 위해, 실제 상품사진 등은 이 모션으로 '살아있는' 컷을
무료로 만든다. 출력은 항상 1080x1920(9:16) 세로.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def kenburns_vf(dur, fps=30, width=1080, height=1920, zoom_per_frame=0.0009,
                max_zoom=1.15):
    """이미지 입력(-loop 1)에 적용할 비디오 필터 문자열을 반환.

    cover 스케일 → zoompan 으로 서서히 줌인 → 정확한 길이로 trim.
    """
    frames = max(1, int(round(float(dur) * fps)))
    over_w, over_h = int(width * 1.5), int(height * 1.5)
    return (
        "scale=%d:%d:force_original_aspect_ratio=increase,"
        "crop=%d:%d,"
        "zoompan=z='min(zoom+%s,%s)':d=1:"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        "s=%dx%d:fps=%d,"
        "trim=duration=%s,setsar=1,format=yuv420p"
        % (over_w, over_h, over_w, over_h,
           zoom_per_frame, max_zoom, width, height, fps, dur)
    )


def fit_video_vf(dur, fps=30, width=1080, height=1920):
    """영상 클립을 1080x1920 cover 로 맞추고, 짧으면 마지막 프레임을 늘려 정확한 길이로."""
    return (
        "scale=%d:%d:force_original_aspect_ratio=increase,"
        "crop=%d:%d,fps=%d,"
        "tpad=stop_mode=clone:stop_duration=30,"
        "trim=duration=%s,setsar=1,format=yuv420p"
        % (width, height, width, height, fps, dur)
    )


def render(ffmpeg, image, out, dur, fps=30, width=1080, height=1920):
    """단독 CLI/테스트용: 이미지 한 장 → 모션 클립(무음)."""
    vf = kenburns_vf(dur, fps, width, height)
    cmd = [ffmpeg, "-y", "-loop", "1", "-i", str(image), "-t", str(dur),
           "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
           str(out)]
    subprocess.run(cmd, check=True)
    return out


if __name__ == "__main__":
    import argparse
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import toolpaths
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=4.0)
    a = ap.parse_args()
    ff = toolpaths.ffmpeg()
    if not ff:
        raise SystemExit("ffmpeg 없음")
    render(ff, a.image, a.out, a.dur)
    print("[kenburns] %s" % a.out)
