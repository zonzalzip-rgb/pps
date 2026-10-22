"""Resolve ffmpeg/ffprobe/yt-dlp without depending on PATH.

Portable ffmpeg installs (unzipped to a user folder) are common on Windows where
adding to the system PATH needs rights the session may not have. Resolution order:

  1. FFMPEG_BIN / FFPROBE_BIN / YTDLP_BIN env overrides
  2. PATH (shutil.which)
  3. Known portable install locations
  4. For yt-dlp only: the importable `yt_dlp` module, run as `python -m yt_dlp`
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Portable-install locations to probe, in priority order.
PORTABLE_DIRS = [
    Path.home() / "ffmpeg" / "bin",
    Path.home() / "ffmpeg",
    Path("C:/ffmpeg/bin"),
    Path("C:/Program Files/ffmpeg/bin"),
    Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links",
    Path.home() / "scoop" / "shims",
]

_EXE = ".exe" if os.name == "nt" else ""


def _resolve(name: str, env_var: str) -> str | None:
    override = os.environ.get(env_var)
    if override and Path(override).is_file():
        return override

    found = shutil.which(name)
    if found:
        return found

    for directory in PORTABLE_DIRS:
        candidate = directory / (name + _EXE)
        if candidate.is_file():
            return str(candidate)
    return None


def ffmpeg() -> str | None:
    return _resolve("ffmpeg", "FFMPEG_BIN")


def ffprobe() -> str | None:
    return _resolve("ffprobe", "FFPROBE_BIN")


def ytdlp() -> list[str] | None:
    """Return an argv prefix, since yt-dlp may only exist as an importable module."""
    direct = _resolve("yt-dlp", "YTDLP_BIN")
    if direct:
        return [direct]
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       capture_output=True, timeout=60, check=True)
        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        return None


def report() -> dict:
    yt = ytdlp()
    return {
        "ffmpeg": ffmpeg(),
        "ffprobe": ffprobe(),
        "yt-dlp": " ".join(yt) if yt else None,
    }


def require(*names: str) -> dict:
    """Resolve the named tools or exit with an actionable install hint."""
    table = {"ffmpeg": ffmpeg, "ffprobe": ffprobe, "yt-dlp": ytdlp}
    resolved = {}
    missing = []
    for name in names:
        value = table[name]()
        if value:
            resolved[name] = value
        else:
            missing.append(name)
    if missing:
        sys.stderr.write(
            "ERROR: cannot find %s\n"
            "  ffmpeg/ffprobe: unzip a build from https://www.gyan.dev/ffmpeg/builds/\n"
            "                  to ~/ffmpeg, or set FFMPEG_BIN / FFPROBE_BIN\n"
            "  yt-dlp:         pip install yt-dlp\n" % ", ".join(missing)
        )
        raise SystemExit(2)
    return resolved
