#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""queue.csv 대기열 헬퍼.

열: 번호, 쿠팡링크, 상품명, 특징메모, 상태, 비용USD, 결과폴더
상태: 대기 / 진행중 / 완료 / 정보필요 / 실패

CLI:
  python queue_util.py add "<쿠팡링크>" --name "상품명"
  python queue_util.py list
  python queue_util.py next
  python queue_util.py set <번호> --status 완료 --cost 0.42 --out output/...
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

FIELDS = ["번호", "쿠팡링크", "상품명", "특징메모", "상태", "비용USD", "결과폴더"]
PENDING = "대기"


def _default_path():
    # 프로젝트 루트의 queue.csv (유연: 환경변수 > 현재폴더 > 레거시)
    import os
    proj = os.environ.get("COUPANG_SHORTS_PROJECT")
    if proj and Path(proj).exists():
        return Path(proj) / "queue.csv"
    legacy = Path.home() / "Desktop" / "클로드 폴더" / "쿠팡숏폼ai자동화" / "queue.csv"
    if legacy.parent.exists():
        return legacy
    return Path.cwd() / "queue.csv"


def ensure(path):
    p = Path(path)
    if not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()
    return p


def rows(path):
    p = ensure(path)
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write(path, data):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in data:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def add(path, url, name="", note=""):
    data = rows(path)
    num = str(len(data) + 1)
    data.append({"번호": num, "쿠팡링크": url, "상품명": name, "특징메모": note,
                 "상태": PENDING, "비용USD": "", "결과폴더": ""})
    _write(path, data)
    return num


def next_pending(path):
    for r in rows(path):
        if (r.get("상태") or "").strip() == PENDING:
            return r
    return None


def set_row(path, num, **fields):
    data = rows(path)
    mapping = {"status": "상태", "cost": "비용USD", "out": "결과폴더",
               "name": "상품명", "note": "특징메모"}
    hit = False
    for r in data:
        if str(r.get("번호")) == str(num):
            for k, v in fields.items():
                if v is not None:
                    r[mapping.get(k, k)] = v
            hit = True
    if hit:
        _write(path, data)
    return hit


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(_default_path()))
    sub = ap.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add"); pa.add_argument("url"); pa.add_argument("--name", default=""); pa.add_argument("--note", default="")
    sub.add_parser("list")
    sub.add_parser("next")
    ps = sub.add_parser("set"); ps.add_argument("num")
    ps.add_argument("--status"); ps.add_argument("--cost"); ps.add_argument("--out")
    ps.add_argument("--name"); ps.add_argument("--note")
    a = ap.parse_args()

    if a.cmd == "add":
        print("추가됨 #%s" % add(a.path, a.url, a.name, a.note))
    elif a.cmd == "list":
        for r in rows(a.path):
            print("#%s [%s] %s | %s" % (r.get("번호"), r.get("상태"),
                  r.get("상품명") or "(이름없음)", r.get("쿠팡링크", "")[:60]))
    elif a.cmd == "next":
        r = next_pending(a.path)
        print(("#%s %s | %s" % (r["번호"], r.get("상품명") or "(이름없음)", r["쿠팡링크"]))
              if r else "대기 중인 항목 없음")
    elif a.cmd == "set":
        ok = set_row(a.path, a.num, status=a.status, cost=a.cost, out=a.out,
                     name=a.name, note=a.note)
        print("업데이트 %s" % ("완료" if ok else "실패(번호 없음)"))


if __name__ == "__main__":
    _main()
