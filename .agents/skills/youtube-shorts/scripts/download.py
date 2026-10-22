#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""틱톡 등 영상 링크를 yt-dlp로 다운로드(REMIX용 실사 푸티지 확보).

AI 생성 없이, 사용자가 준 링크의 실제 영상을 받아 컷 편집 소스로 쓴다.

CLI:
  python download.py <url> <out.mp4>
  python download.py --dir <폴더> <url1> <url2> ...   # 01.mp4, 02.mp4 ...
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolpaths  # noqa: E402  (scripts/toolpaths.py)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def download(url, out_path):
    yt = toolpaths.ytdlp()
    if not yt:
        raise SystemExit("yt-dlp 없음 — pip install yt-dlp")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = yt + [
        "-f", "bestvideo*+bestaudio/best/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist", "--force-overwrites",
        "-o", str(out), url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0 or not out.exists():
        sys.stderr.write(r.stderr[-1200:] + "\n")
        raise RuntimeError("다운로드 실패: %s" % url)
    return out


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", help="여러 링크를 이 폴더에 01.mp4,02.mp4 ...로 저장")
    ap.add_argument("args", nargs="+")
    a = ap.parse_args()
    if a.dir:
        d = Path(a.dir)
        for i, url in enumerate(a.args, 1):
            out = d / ("%02d.mp4" % i)
            print("[download] %d/%d %s" % (i, len(a.args), url))
            try:
                download(url, out)
                print("   -> %s (%d bytes)" % (out, out.stat().st_size))
            except Exception as e:
                print("   실패:", str(e)[:200])
    else:
        if len(a.args) != 2:
            raise SystemExit("사용법: download.py <url> <out.mp4>  또는  --dir <폴더> <url...>")
        out = download(a.args[0], a.args[1])
        print("[download] %s (%d bytes)" % (out, out.stat().st_size))


if __name__ == "__main__":
    _main()
