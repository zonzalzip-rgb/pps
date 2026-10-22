# -*- coding: utf-8 -*-
"""Vosk로 TTS 음성의 단어 타이밍을 정렬 → word_spans (카라오케 정밀 동기화).

카라오케가 음성과 맞으려면 '화면 글자 = 실제 말하는 문장'이어야 한다.
그래서 자막 텍스트는 나레이션(실제 TTS 대사)으로 두고, 그 토큰에 대한
[(start,end), ...] 를 반환한다.

필요: vosk + 한국어 모델(assets/vosk/vosk-model-small-ko-0.22), ffmpeg(16k 변환).
모델이 없거나 실패하면 음절수 비례로 폴백.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolpaths  # noqa: E402

_MODEL = None
_MODEL_DIR = (Path(__file__).resolve().parent.parent / "assets" / "vosk"
              / "vosk-model-small-ko-0.22")


def _model():
    global _MODEL
    if _MODEL is None:
        from vosk import Model
        # Vosk's Windows native loader may reject non-ASCII absolute paths.
        # A relative path avoids that when the project folder has a Korean name.
        _MODEL = Model(os.path.relpath(_MODEL_DIR, Path.cwd()))
    return _MODEL


def _to16k(src):
    ff = toolpaths.ffmpeg()
    out = Path(tempfile.gettempdir()) / ("cs_align_%d.wav" % abs(hash(str(src))))
    subprocess.run([ff, "-y", "-i", str(src), "-ar", "16000", "-ac", "1",
                    "-f", "wav", str(out)], capture_output=True)
    return out


def vosk_words(wav):
    from vosk import KaldiRecognizer
    w16 = _to16k(wav)
    wf = wave.open(str(w16), "rb")
    rec = KaldiRecognizer(_model(), wf.getframerate())
    rec.SetWords(True)
    words = []
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        if rec.AcceptWaveform(data):
            words += json.loads(rec.Result()).get("result", [])
    words += json.loads(rec.FinalResult()).get("result", [])
    wf.close()
    try:
        w16.unlink()
    except OSError:
        pass
    return [(x["word"], float(x["start"]), float(x["end"])) for x in words]


def align(wav, tokens, dur):
    """tokens(표시 단어 목록)에 대한 [(start,end)] 반환. 정렬 실패 시 비례 폴백."""
    tokens = list(tokens)
    n = len(tokens)
    if n == 0:
        return []
    vw = []
    if _MODEL_DIR.exists():
        try:
            vw = vosk_words(wav)
        except Exception:
            vw = []
    if len(vw) == n:
        return [(s, e) for _, s, e in vw]
    # 개수 불일치/실패 → 음성 구간 안에서 글자수 비례
    if vw:
        s0, e0 = vw[0][1], vw[-1][2]
    else:
        s0, e0 = 0.0, float(dur)
    span = max(0.1, e0 - s0)
    weights = [max(1, len(t)) for t in tokens]
    tot = sum(weights)
    spans, t = [], s0
    for wt in weights:
        a = t
        t = t + span * wt / tot
        spans.append((a, t))
    spans[-1] = (spans[-1][0], e0)
    return spans
