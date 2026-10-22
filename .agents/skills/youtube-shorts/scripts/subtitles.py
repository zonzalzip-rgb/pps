# -*- coding: utf-8 -*-
"""씬별 한글 자막(.ass) 생성.

1080x1920 세로 영상에 크고 읽기 쉬운 자막을 하단 중앙에 배치.
ffmpeg 의 ass 필터로 구워 넣는다(글자 깨짐 방지: UTF-8 ASS + 한글 폰트).
자막 타이밍은 '씬 단위'(0 ~ 해당 씬 길이)로 넣어, 전역 타임코드 계산 없이
각 씬 세그먼트를 만들 때 바로 굽는다.
"""

from __future__ import annotations

from pathlib import Path


def _ass_time(sec):
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return "%d:%02d:%05.2f" % (h, m, s)


def _wrap(text, max_chars=16):
    """너무 긴 한 줄을 2줄 정도로 접어 가독성 확보(간단 규칙)."""
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\\N".join(lines[:3])  # ASS 줄바꿈은 \N


YELLOW = "&H0000D7FF&"   # ASS(&HAABBGGRR): 노란색(R255 G215 B0 느낌)
WHITE = "&H00FFFFFF&"


def write_ass(path, text, dur, width=1080, height=1920,
              font_name="Malgun Gothic", font_size=96, word_spans=None, badge=None,
              notice=None):
    """씬 자막(0~dur)을 **화면 중앙 + 카라오케(말하는 단어만 노랑 강조)**로 생성.

    - 중앙 정렬(\\an5), 한 번에 최대 3단어 창(window), 현재 단어만 노랑+살짝 크게.
    - word_spans=[(start,end),...] 가 주어지면 그 타이밍(STT 정렬)으로, 없으면
      음절수(글자수) 비례로 TTS 길이에 맞춰 분배.
    """
    body = (text or "").strip().replace("\n", " ")
    words = [w for w in body.split(" ") if w]
    if not words:
        words = [body or " "]
    nw = len(words)

    # 단어별 타이밍
    if word_spans and len(word_spans) == nw:
        spans = [(float(s), float(e)) for s, e in word_spans]
    else:
        weights = [max(1, len(w)) for w in words]
        tot = sum(weights)
        spans, t = [], 0.0
        for wt in weights:
            s = t
            e = t + float(dur) * wt / tot
            spans.append((s, e))
            t = e
        spans[-1] = (spans[-1][0], float(dur))

    # 3단어 창 구성 + 창별 최대 글자수로 폰트 크기 산정(한 줄 유지)
    def window(i):
        lo = max(0, i - 1)
        hi = min(nw, lo + 3)
        lo = max(0, hi - 3)
        return lo, hi

    maxchars = 1
    for i in range(nw):
        lo, hi = window(i)
        maxchars = max(maxchars, len(" ".join(words[lo:hi])))
    margin_lr = 36
    fs = min(font_size, int((width - margin_lr * 2) / maxchars))
    fs = max(52, fs)
    big = int(fs * 1.16)

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: %d
PlayResY: %d
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KO,%s,%d,%s,%s,&H00141414,&H96000000,-1,0,0,0,100,100,0,0,1,7,3,5,%d,%d,0,1
Style: BADGE,%s,62,&H00000000,&H00000000,&H002EDAFF,&H00000000,-1,0,0,0,100,100,0,0,3,20,0,8,0,0,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % (width, height, font_name, fs, WHITE, WHITE, margin_lr, margin_lr, font_name)

    lines = []
    if notice:
        lines.append("Dialogue: 2,%s,%s,KO,,0,0,0,,{\\an2\\pos(%d,%d)\\fs30\\bord2}%s"
                     % (_ass_time(0), _ass_time(dur), width // 2, height - 210, notice))
    if badge:
        # 상단 노랑박스 제품번호 뱃지: 영상 전 구간 고정 표기
        lines.append("Dialogue: 1,%s,%s,BADGE,,0,0,0,,%s"
                     % (_ass_time(0), _ass_time(dur), badge))
    for i in range(nw):
        s, e = spans[i]
        if e <= s:
            e = s + 0.05
        lo, hi = window(i)
        parts = []
        for j in range(lo, hi):
            if j == i:
                # 현재 단어: 노랑 + 살짝 크게(팝)
                parts.append("{\\c%s\\fs%d}%s{\\c%s\\fs%d}"
                             % (YELLOW, big, words[j], WHITE, fs))
            else:
                parts.append(words[j])
        txt = "{\\an5\\fad(30,0)}" + " ".join(parts)
        lines.append("Dialogue: 0,%s,%s,KO,,0,0,0,,%s"
                     % (_ass_time(s), _ass_time(e), txt))

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return str(p)
