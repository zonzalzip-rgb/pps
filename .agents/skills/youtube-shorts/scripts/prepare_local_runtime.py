"""Install video binaries and Korean alignment assets in this project only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import zipfile
import io

ROOT = Path(__file__).resolve().parents[1]

def binaries():
    target = ROOT / '.runtime' / 'bin'
    target.mkdir(parents=True, exist_ok=True)
    if all((target / n).is_file() for n in ['ffmpeg.exe', 'ffprobe.exe']):
        return 'Video binaries already present'
    url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
    with urllib.request.urlopen(url, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    for name in archive.namelist():
        if name.endswith('/ffmpeg.exe') or name.endswith('/ffprobe.exe'):
            (target / Path(name).name).write_bytes(archive.read(name))
    return 'FFmpeg and FFprobe ready'

def model():
    target = ROOT / 'assets' / 'vosk'
    if (target / 'vosk-model-small-ko-0.22' / 'am' / 'final.mdl').is_file():
        return 'Korean alignment model already present'
    target.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen('https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip', timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    archive.extractall(target)
    return 'Korean alignment model ready'

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(lambda f: f(), [binaries, model]):
            print(result, flush=True)
