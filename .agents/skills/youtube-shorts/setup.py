#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coupang-shorts 설치 스크립트.

받는 사람이 한 번 실행: 파이썬 라이브러리 설치 + (없으면) Vosk 한국어 모델·주아체 폰트 다운로드.
  python setup.py
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _pip(*pkgs):
    print("[pip]", *pkgs)
    subprocess.run([sys.executable, "-m", "pip", "install",
                    "--disable-pip-version-check", *pkgs])


def _dl(url, timeout=1200):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def main():
    _pip("yt-dlp", "rapidocr_onnxruntime", "opencv-python-headless", "vosk")

    font = HERE / "assets" / "fonts" / "Jua-Regular.ttf"
    if not font.is_file():
        font.parent.mkdir(parents=True, exist_ok=True)
        print("[font] 주아체 다운로드")
        font.write_bytes(_dl("https://github.com/google/fonts/raw/main/ofl/jua/Jua-Regular.ttf"))

    mdir = HERE / "assets" / "vosk" / "vosk-model-small-ko-0.22"
    if not mdir.exists():
        print("[vosk] 한국어 모델 다운로드(약 86MB)...")
        (HERE / "assets" / "vosk").mkdir(parents=True, exist_ok=True)
        data = _dl("https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip")
        zipfile.ZipFile(io.BytesIO(data)).extractall(HERE / "assets" / "vosk")
        print("   모델 준비 완료")

    ff = shutil.which("ffmpeg") or (Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe").exists()
    if not ff:
        print("[주의] ffmpeg 가 없습니다 → https://www.gyan.dev/ffmpeg/builds/ 에서 받아")
        print("       ~/ffmpeg 에 풀거나 PATH 등록(또는 환경변수 FFMPEG_BIN/FFPROBE_BIN).")

    print("[완료] 설치 끝. 외부 API 키 설정은 필요하지 않습니다.")


if __name__ == "__main__":
    main()
