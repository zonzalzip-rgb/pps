"""Resume the local shopping-short pipeline using saved scenes and assets."""
import json
import os
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'scripts'))
import toolpaths
_tools = toolpaths.require('ffmpeg', 'ffprobe')
os.environ['FFMPEG_BIN'] = _tools['ffmpeg']
os.environ['FFPROBE_BIN'] = _tools['ffprobe']
import blur_text
import align
import compose
import thumbnail

project = Path(sys.argv[1]).resolve()
stage = sys.argv[2]
scenes = json.loads((project / 'scenes.json').read_text(encoding='utf-8-sig'))

if stage == 'tts':
    missing = [f"{sc['id']:02d}.wav" for sc in scenes
               if not (project / 'audio' / f"{sc['id']:02d}.wav").is_file()]
    if missing:
        raise RuntimeError('V12 has no TTS API. Add prepared WAV files to audio/: ' + ', '.join(missing))
    print('Prepared local WAV files are present; no TTS service was called.', flush=True)
elif stage == 'render':
    build = dict(width=1080, height=1920, fps=30, font_file=str(ROOT/'assets/fonts/Jua-Regular.ttf'),
                 font_name='Jua', badge='제품번호: 06', max_sec=29, out='final.mp4', scenes=[],
                 notice='유사 제품 연출 영상 · 실제 상품은 구매 링크에서 확인')
    total = 0
    for sc in scenes:
        idx = sc['id']
        wav = project / 'audio' / f'{idx:02d}.wav'
        with wave.open(str(wav), 'rb') as audio:
            dur = audio.getnframes()/audio.getframerate()
        total += dur
        clean = project / 'clean' / f'clean_{idx:02d}.mp4'
        if not clean.is_file():
            print(f'Cleaning scene {idx}, {dur:.2f}s', flush=True)
            blur_text.process(project/sc['clip'], clean, start=sc['start'], dur=dur, every=5, ocr_scale=1.0)
        spans = align.align(wav, sc['narration'].split(), dur)
        build['scenes'].append(dict(visual=f'clean/clean_{idx:02d}.mp4', audio=f'audio/{idx:02d}.wav',
                                    subtitle=sc['narration'], word_spans=spans))
    print(f'Total narration: {total:.2f}s', flush=True)
    if total >= 29:
        raise RuntimeError('Narration too long: revise or speed up audio before rendering; do not truncate speech')
    (project/'build.json').write_text(json.dumps(build, ensure_ascii=False, indent=2), encoding='utf-8')
    compose.compose(project/'build.json')
    for idx in range(1,5):
        dest = project/'thumbnails'/f'thumb_{idx}.png'
        dest.parent.mkdir(exist_ok=True)
        thumbnail.make(project/'clean'/f'clean_{idx:02d}.mp4', dest, '겨울 치트키', '입는 이불', at=1)
        print(f'Thumbnail {idx} saved', flush=True)
