"""Render a batch of shorts using local audio files only; no service APIs."""
import json
import os
import sys
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import toolpaths
TOOLS = toolpaths.require('ffmpeg', 'ffprobe')
os.environ['FFMPEG_BIN'] = TOOLS['ffmpeg']
os.environ['FFPROBE_BIN'] = TOOLS['ffprobe']
import align
import blur_text
import compose
import thumbnail

root = Path(sys.argv[1]).resolve()
stage = sys.argv[2]
batch = json.loads((root / 'batch.json').read_text(encoding='utf-8-sig'))
plans = json.loads((root / 'scene_plan.json').read_text(encoding='utf-8'))
for product in batch['products']:
    (root / product['slug'] / 'scenes.json').write_text(
        json.dumps(plans[product['number']], ensure_ascii=False, indent=2), encoding='utf-8')


def duration(path):
    with wave.open(str(path), 'rb') as audio:
        return audio.getnframes() / audio.getframerate()


def check_audio(product):
    folder = root / product['slug']
    missing = []
    for scene in plans[product['number']]:
        wav = folder / 'audio' / f"{scene['id']:02d}.wav"
        if not wav.is_file() or wav.stat().st_size <= 44:
            missing.append(str(wav))
        else:
            print(f"AUDIO {product['number']}/{scene['id']} {duration(wav):.2f}s", flush=True)
    if missing:
        raise RuntimeError('Add prepared local WAV narration files; V12 does not call TTS services:\n' + '\n'.join(missing))


def render(product):
    folder = root / product['slug']
    scenes = plans[product['number']]
    check_audio(product)
    total = sum(duration(folder / 'audio' / f"{s['id']:02d}.wav") for s in scenes)
    if total >= 29:
        raise RuntimeError(f"Narration too long ({total:.2f}s); revise audio or script before rendering")
    build = dict(width=1080, height=1920, fps=30,
                 font_file=str(REPO / 'assets/fonts/Jua-Regular.ttf'), font_name='Jua',
                 badge=f"제품번호: {product['number']}",
                 notice='유사 제품 연출 영상 · 실제 상품은 구매 링크에서 확인',
                 max_sec=29, out='final.mp4', scenes=[])
    for scene in scenes:
        idx = scene['id']
        wav = folder / 'audio' / f'{idx:02d}.wav'
        dur = duration(wav)
        clean = folder / 'clean' / f'clean_{idx:02d}.mp4'
        if not clean.is_file() or clean.stat().st_size < 1000:
            clean.parent.mkdir(exist_ok=True)
            print(f"OCR {product['number']}/{idx}, {dur:.2f}s", flush=True)
            blur_text.process(folder / scene['clip'], clean, start=scene['start'], dur=dur,
                              every=3, ocr_scale=1.6, blur_kernel=81)
        spans = align.align(wav, scene['narration'].split(), dur)
        build['scenes'].append(dict(visual=f'clean/clean_{idx:02d}.mp4',
                                    audio=f'audio/{idx:02d}.wav',
                                    subtitle=scene['narration'], word_spans=spans))
    (folder / 'build.json').write_text(json.dumps(build, ensure_ascii=False, indent=2), encoding='utf-8')
    compose.compose(folder / 'build.json')
    for idx in range(1, 5):
        dest = folder / 'thumbnails' / f'thumb_{idx}.png'
        dest.parent.mkdir(exist_ok=True)
        thumbnail.make(folder / 'clean' / f'clean_{idx:02d}.mp4', dest,
                       product['thumbnail_top'], product['thumbnail_bottom'], at=1)
    return product['number']


def write_metadata(product):
    folder = root / product['slug']
    request_path = folder / 'request.json'
    request = json.loads(request_path.read_text(encoding='utf-8')) if request_path.is_file() else {}
    url = product.get('original_product_url') or request.get('original_product_url') or ''
    tags = product.get('tags') or '생활용품,살림템,주방용품,생활용품추천,쇼츠추천'
    description = product.get('description') or f"{product['product_name']}의 정보와 사용 장면을 소개합니다. 구매 전 상품 페이지에서 규격과 주의사항을 확인해 주세요."
    text = f"[제목]\n{product['title']}\n\n[설명]\n{description}\n\n[태그]\n{tags}\n\n[상품 확인 링크]\n{url}\n"
    (folder / '설명.txt').write_text(text, encoding='utf-8')
    print(f"METADATA {product['number']}", flush=True)


if stage == 'tts':
    for product in batch['products']:
        check_audio(product)
    print('All prepared local WAV files are present. No TTS API was called.', flush=True)
elif stage == 'render':
    for product in batch['products']:
        print('RENDER READY', render(product), flush=True)
elif stage == 'metadata':
    for product in batch['products']:
        write_metadata(product)
else:
    raise ValueError('Unknown stage; use tts (WAV validation), render, or metadata')
