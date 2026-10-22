#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""footage(틱톡) 영상의 '모든 글자'를 OCR로 찾아 blur 처리.

핵심: 원본 한국어 자막과 외국어 텍스트를 언어 구분 없이 OCR로 검출해
글자 박스 영역만 블러한다. TTS 한글 자막은 블러 검수를 통과한 clean 클립을
만든 뒤 compose에서 얹으므로 원본 자막과 섞이지 않는다.

구간(start,dur)만 처리해 그 씬의 컷을 '글자 가린 클립'으로 만든다. 출력은 무음
(오디오는 compose에서 TTS로 교체).

CLI:
  python blur_text.py <input.mp4> <output.mp4> [--start 8] [--dur 4.5] [--every 3] [--pad 2]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _load():
    import cv2
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    return cv2, np, RapidOCR


def process(inp, out, start=0.0, dur=None, every=3, pad=2, ocr_scale=1.6, blur_kernel=81):
    cv2, np, RapidOCR = _load()
    ocr = RapidOCR()

    def detect(frame):
        """프레임을 업스케일해 OCR → 작은/장식체 글자까지 잡고 박스는 원좌표로."""
        if ocr_scale and ocr_scale != 1.0:
            small = cv2.resize(frame, None, fx=ocr_scale, fy=ocr_scale,
                               interpolation=cv2.INTER_CUBIC)
            try:
                res, _ = ocr(small)
            except Exception:
                res = None
            if not res:
                return []
            return [[[p[0] / ocr_scale, p[1] / ocr_scale] for p in r[0]] for r in res]
        try:
            res, _ = ocr(frame)
        except Exception:
            res = None
        return [r[0] for r in res] if res else []

    cap = cv2.VideoCapture(str(inp))
    if not cap.isOpened():
        raise SystemExit("영상을 열 수 없음: %s" % inp)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if start:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(start) * 1000.0)
    need = int(float(dur) * fps) if dur else None

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    boxes, i = [], 0
    while True:
        ok, frame = cap.read()
        if not ok or (need is not None and i >= need):
            break
        if i % max(1, every) == 0:
            boxes = detect(frame)
        for box in boxes:
            pts = np.array(box).astype(int)
            x, y, bw, bh = cv2.boundingRect(pts)
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1, y1 = min(w, x + bw + pad), min(h, y + bh + pad)
            roi = frame[y0:y1, x0:x1]
            if roi.size:
                k = max(int(blur_kernel) | 1, (((x1 - x0) // 4) | 1))
                frame[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (k, k), 0)
        writer.write(frame)
        i += 1
    cap.release()
    writer.release()
    if i == 0:
        raise SystemExit("프레임을 읽지 못함")
    return out, i


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--every", type=int, default=3)
    ap.add_argument("--pad", type=int, default=2,
                    help="pixels of margin around each detected subtitle text box; keep small to avoid broad bands")
    ap.add_argument("--ocr-scale", type=float, default=1.6)
    ap.add_argument("--blur-kernel", type=int, default=81,
                    help="odd Gaussian kernel size; higher values hide original subtitle text more strongly")
    a = ap.parse_args()
    out, n = process(a.input, a.output, a.start, a.dur, a.every, a.pad, a.ocr_scale, a.blur_kernel)
    print("[blur_text] %s (%d frames)" % (out, n))


if __name__ == "__main__":
    _main()
