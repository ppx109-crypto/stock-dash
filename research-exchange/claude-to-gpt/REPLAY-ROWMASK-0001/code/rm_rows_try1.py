"""REPLAY-ROWMASK-0001 · 줄 만들기(잘라낸 입력 하나) — 고정 엔진 코드(b2 · 00b98ab1) + 옛 표 시점 저장소 자료(V · git b8365547).
python3 -E -P rm_rows.py <b2> <V> <CUT YYYYMMDD | full> <옛 nrl-cache.pkl> <출력.pkl>

- 가격을 CUT까지 자른 뒤 lab.build(horizons=(0, 5, 10, 20, 60))를 종목 20개씩 한 번 돌림. 특징 계산식은 그대로.
  · 고친 존재 조건(repaired): 그날까지 가격만 있으면 줄 있음 = horizons=(0,) 와 같음
  · 옛 존재 조건(orig): 앞으로 5일 가격이 있어야 줄 있음(5 in ahead) — 비교용 표시만, 고친 표에는 안 씀
  · 'ahead'(앞날 수익)는 저장 전에 지움
- 2025-08-01 ~ CUT(최대 2026-03-31) 줄만 남김. 시총 순위(caps.tag)는 repaired 묶음 · orig 묶음 따로, 날마다 그날 줄끼리만.
- D1 신호용 캐시(repaired)도 같이 씀: (가격 ≤ CUT, lanes, shape, 시장 폭, 상위100 줄, 옛 calm · 옛 달별 calm 숫자 그대로).
네트워크 막음 · 키 환경변수 지움 · 운영 파일 · 자료 안 고침."""
import hashlib
import os
import pickle
import socket
import sys
import time
from pathlib import Path

B2, V, CUT, OLD, OUT = str(Path(sys.argv[1]).resolve()), str(Path(sys.argv[2]).resolve()), sys.argv[3], Path(sys.argv[4]).resolve(), Path(sys.argv[5]).resolve()
LO, TRAIN_HI = "20250801", "20260331"


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
os.environ.pop("CAPS_ADJ", None)
os.chdir(V)
sys.path[:0] = [B2, B2 + "/research"]
t0 = time.time()
import caps  # noqa: E402
import final_study as F  # noqa: E402
import lab  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

assert Path(lab.__file__).parent == Path(B2) and Path(caps.__file__).parent == Path(B2)
P = {}
for c, b in study.load_prices().items():
    rows = [x for x in b["rows"] if CUT == "full" or x[0] <= CUT]
    if len(rows) >= 120:
        P[c] = {"name": b["name"], "rows": rows}
last = max(x[0] for b in P.values() for x in b["rows"])
HI = min(last, TRAIN_HI)
rep, orig, codes = [], [], sorted(P)
for s in range(0, len(codes), 20):
    part = {c: P[c] for c in codes[s:s + 20]}
    for r in lab.build(part, horizons=(0, 5, 10, 20, 60)):
        if not (LO <= r["date"] <= HI):
            continue
        o = 5 in r["ahead"]
        del r["ahead"]
        rep.append(r)
        if o:
            orig.append(dict(r))
print("만듦", CUT, len(P), "종목 · 마지막 가격", last, "· repaired", len(rep), "· orig", len(orig), round(time.time() - t0), "초", flush=True)
caps.tag(rep, rule.TOP)
caps.tag(orig, rule.TOP)
inside = [r for r in rep if caps.inside(r, rule.TOP)]
inside = lab.realign(inside, P)
O = pickle.load(open(OLD, "rb"))
lanes = lab.lanes(P)
shape = F.shapes(lanes, set(P))
BR = F.breadth_by_day(inside, shape)
cache = (P, lanes, shape, BR, inside, O[5], O[6])
cpath = OUT.with_suffix(".cache.pkl")
with open(cpath, "wb") as fh:
    pickle.dump(cache, fh, protocol=pickle.HIGHEST_PROTOCOL)
slim = lambda rows: [{k: v for k, v in r.items()} for r in rows]
with open(OUT, "wb") as fh:
    pickle.dump({"cut": CUT, "last_price": last, "hi": HI, "repaired": slim(rep), "orig": slim(orig), "BR": BR,
                 "cache_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest()}, fh, protocol=pickle.HIGHEST_PROTOCOL)
print("끝", CUT, round(time.time() - t0), "초", flush=True)
