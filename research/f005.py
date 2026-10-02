"""F 5회차 — 시장 전체 수급으로 때 맞추기. 그날 시총 100위(nrl.inside) 종목들의 투자자별 순매수 금액(순매수량 × 종가) 합 ÷ 거래대금 합(전날까지 n일).
Q_PART=1: 코스피 앞으로 5 · 20일 수익을 시장 수급 다섯 무리로(두 반) — 외국인 · 기관 · 투신 · 연기금 · 개인
Q_PART=2: 1일봉 엔진(새 82 그대로 · 씨앗 8)에 '시장 외국인 n일 순매수 > 문턱' 문을 더함 · 시장 개인 순매도 문."""
import bisect
import json
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl

COLS = ("개인", "외국인", "기관", "투신", "연기금", "사모")
top = {}
for r in nrl.inside:
    top.setdefault(r["date"], []).append(r["code"])
for r in getattr(nrl, "early", []):
    top.setdefault(r["date"], []).append(r["code"])
INV, TV = {}, {}
for code in {c for v in top.values() for c in v}:
    try:
        inv = json.load(open(f"investor-data/{code}.json", encoding="utf-8"))["rows"]
        vol = json.load(open(f"volume-data/{code}.json", encoding="utf-8"))["날"]
    except (OSError, ValueError, KeyError):
        continue
    INV[code] = {r[0]: r for r in inv}
    TV[code] = {r[0]: r[2] for r in vol if len(r) > 2 and r[2]}
days = sorted(top)
amt = {c: np.zeros(len(days)) for c in COLS}
tv = np.zeros(len(days))
for i, d in enumerate(days):
    for code in set(top[d]):
        row = INV.get(code, {}).get(d)
        t = TV.get(code, {}).get(d)
        if row is None or not t or row[7] is None:
            continue
        tv[i] += t
        for j, c in enumerate(COLS):
            if row[1 + j] is not None:
                amt[c][i] += row[1 + j] * row[7]
cs = lambda a: np.concatenate([[0.0], np.cumsum(a)])
AC = {c: cs(amt[c]) for c in COLS}
TC = cs(tv)


def mkt(day, col, n=5):
    """day 전날까지 n거래일 시장 순매수 ÷ 거래대금(%)."""
    k = bisect.bisect_left(days, day)
    if k < n or TC[k] - TC[k - n] <= 0:
        return None
    return (AC[col][k] - AC[col][k - n]) / (TC[k] - TC[k - n]) * 100


part = os.environ.get("Q_PART", "1")
print(f"== F 5회차({part}): 시장 전체 수급(그날 시총 100위 합) ==  날 {len(days)} · 자료 있는 종목 {len(INV)}", flush=True)
if part == "1":
    idx = json.load(open("market-data/index_KOSPI.json", encoding="utf-8"))["rows"]
    ic = {r["date"]: r["종가"] for r in idx}
    idays = sorted(ic)
    MID = nrl.rule.MID
    for col in ("외국인", "기관", "투신", "연기금", "개인"):
        for n in (5, 20):
            vals = []
            for d in days:
                k = bisect.bisect_left(idays, d)
                if k + 21 >= len(idays) or idays[k] != d:
                    continue
                v = mkt(d, col, n)
                if v is None:
                    continue
                # d 장 뒤에 알고 d+1 종가에 들어감
                f5 = ic[idays[k + 6]] / ic[idays[k + 1]] - 1
                f20 = ic[idays[k + 21]] / ic[idays[k + 1]] - 1
                vals.append((d, v + (mkt(idays[k + 1], col, n) or v) * 0, f5, f20))
            arr = np.array([(v, a, b) for _, v, a, b in vals])
            dd = np.array([d for d, *_ in vals])
            qs = np.quantile(arr[:, 0], [0.2, 0.4, 0.6, 0.8])
            line = []
            for q in range(5):
                lo = -np.inf if q == 0 else qs[q - 1]
                hi = np.inf if q == 4 else qs[q]
                m = (arr[:, 0] >= lo) & (arr[:, 0] < hi)
                part_txt = []
                for nm, hm in (("앞", dd < MID), ("뒤", dd >= MID)):
                    mm = m & hm
                    part_txt.append(f"{nm} {np.mean(arr[mm, 1]) * 100:+.2f}/{np.mean(arr[mm, 2]) * 100:+.2f}")
                line.append(f"무리{q + 1} " + " ".join(part_txt))
            print(f"  {col} {n}일 (5일/20일 코스피 수익) | " + " | ".join(line), flush=True)
else:
    import ntools as T
    base = nrl.BASE_HOLD
    T.once("지금(새 82)", holds=base)
    for col, n, th, tag in (("외국인", 5, 0.0, "시장 외국인 5일 + "), ("외국인", 20, 0.0, "시장 외국인 20일 + "),
                            ("외국인", 5, -1.0, "시장 외국인 5일 > −1%"), ("개인", 5, 0.0, "시장 개인 5일 − ")):
        if col == "개인":
            gate = lambda r, col=col, n=n: (mkt(r["date"], col, n) or 0) < 0
        else:
            gate = lambda r, col=col, n=n, th=th: (mkt(r["date"], col, n) or 0) > th
        T.once(tag, holds=lambda r, gate=gate: base(r) and gate(r))
print("끝", flush=True)
