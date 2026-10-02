"""W 10회차(W10) — **실제 인버스 상장지수펀드 일봉**으로 다시(사용자 2026-10-02 "진행해줘").
w006은 코스피 지수로 흉내만 냈음(−지수 하루 수익 − 보수). 이번엔 etf-data의 실제 종가 — 보수 · 추적 오차 · 2배 상품의 날마다 다시 맞춤 손실이 다 들어 있음.
상품: 114800 KODEX 인버스(코스피200 −1배) · 251340 KODEX 코스닥150선물인버스(−1배) · 252670 KODEX 200선물인버스2X(−2배).
신호는 그날 종가(코스피 지수 · 시장 폭)로 정하고 그날 종가에 들어가 다음 날 종가까지(1일봉 규칙처럼). 갈아탈 때마다 비용(ETF는 매도세 없음: 0.1% · 넉넉히 0.3%).
잣대: 두 반(2017 ~ 2020 · 2021 ~) · 연 · 골 · 가장 나쁜 주 · 1일봉 규칙(새 82)과 주 손익 상관 · 반반 계좌.
[0] 실제 ETF vs 흉내(−지수 × 배수): 같은 날 묶음의 차이 — 2배 상품이 옆걸음에서 얼마나 깎이나."""
import json
import os
import sys
from datetime import date

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl
import wtools as W

rows = json.load(open("/home/user/stock-dash/market-data/index_KOSPI.json", encoding="utf-8"))["rows"]
days = [r["date"] for r in rows]
cl = np.array([r["종가"] for r in rows], float)
MID = nrl.rule.MID
ETF = {}
for code in ("114800", "251340", "252670", "069500", "229200"):
    try:
        got = dict((str(d), float(c)) for d, c in json.load(open(f"/home/user/stock-dash/etf-data/{code}.json", encoding="utf-8"))["closes"])
    except (OSError, ValueError, KeyError):
        continue
    ETF[code] = np.array([got.get(d, np.nan) for d in days], float)


def ma(n):
    out = np.full(len(cl), np.nan)
    c = np.cumsum(np.insert(cl, 0, 0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


M = {n: ma(n) for n in (5, 10, 20, 60, 120, 200)}
br = np.array([nrl.BR.get(d, np.nan) for d in days], float)


def sim(sig, cost, code="114800"):
    """sig[i] True면 i일 종가에 그 ETF를 들고 i+1일 종가까지. 날마다 계좌 % 손익(i+1일 날짜에 붙임). 값이 빈 날은 들지 않음."""
    px = ETF[code]
    out, held, flips = {}, False, 0
    for i in range(len(days) - 1):
        want = bool(sig[i]) and not (np.isnan(px[i]) or np.isnan(px[i + 1]))
        g = 0.0
        if want != held:
            g -= cost
            flips += 1
            held = want
        if held:
            g += (px[i + 1] / px[i] - 1) * 100
        if g:
            out[days[i + 1]] = out.get(days[i + 1], 0) + g
    return out, flips


def wk(s):
    return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isocalendar()[:2]


def stats(d, lo, hi):
    eq, peak, dip, w = 1.0, 1.0, 0.0, {}
    xs = [x for x in sorted(d) if lo <= x < hi]
    for x in xs:
        eq *= 1 + d[x] / 100
        peak = max(peak, eq)
        dip = min(dip, eq / peak - 1)
        w[wk(x)] = w.get(wk(x), 0) + d[x]
    yrs = max((int(hi[:4]) if hi < "2099" else 2026.75) - int(lo[:4]), 0.5)
    return sum(d[x] for x in xs), ((eq) ** (1 / yrs) - 1) * 100, dip * 100, min(w.values()) if w else 0, w


base = {}
for code, b, s, g, k in W.base_ledger():
    base[s] = base.get(s, 0) + k / 10 * g


def show(tag, sig, code="114800", costs=(0.1, 0.3)):
    for cost in costs:
        mine, flips = sim(sig, cost, code)
        line = [f"  {tag:<34} {code} 비용 {cost}%"]
        for side, lo, hi in (("앞", "20170101", MID), ("뒤", MID, "20991231")):
            tot, yr, dip, worst, w = stats(mine, lo, hi)
            a = stats(base, lo, hi)
            half = {x: base.get(x, 0) / 2 + mine.get(x, 0) / 2 for x in set(base) | set(mine)}
            h = stats(half, lo, hi)
            ws = sorted(set(a[4]) | set(w))
            va, vb = np.array([a[4].get(x, 0) for x in ws]), np.array([w.get(x, 0) for x in ws])
            corr = float(np.corrcoef(va, vb)[0, 1]) if vb.std() else float("nan")
            held = sum(1 for i, d in enumerate(days) if lo <= d < hi and sig[i]) / max(sum(1 for d in days if lo <= d < hi), 1) * 100
            line.append(f"| {side} 인버스만 합 {tot:+6.1f} 연 {yr:+5.1f} 골 {dip:6.1f} 나쁜 주 {worst:5.1f} 들고있음 {held:4.1f}% · 상관 {corr:+.2f} · "
                        f"1일봉만 합 {a[0]:+6.1f} 골 {a[2]:5.1f} 나쁜 주 {a[3]:5.1f} · 반반 합 {h[0]:+6.1f} 골 {h[2]:5.1f} 나쁜 주 {h[3]:5.1f}")
        print(" ".join(line) + f" | 갈아탐 {flips}", flush=True)


nan0 = lambda a: np.nan_to_num(a, nan=0)
print(f"== W 10회차: 실제 인버스 ETF 일봉 · 받은 상품 {sorted(ETF)} ==", flush=True)
if "114800" not in ETF:
    print("etf-data가 아직 없습니다(ETF daily prices 작업). 끝.", flush=True)
    sys.exit(0)
print("\n[0] 실제 ETF vs 흉내(−지수 × 배수) — 해마다 묶음 수익(%)", flush=True)
for code, mult in (("114800", -1), ("252670", -2)):
    if code not in ETF:
        continue
    px = ETF[code]
    for y in range(2017, 2027):
        idx = [i for i, d in enumerate(days) if d[:4] == str(y) and not np.isnan(px[i])]
        if len(idx) < 50:
            continue
        a, b = idx[0], idx[-1]
        real = (px[b] / px[a] - 1) * 100
        sim_ = (np.prod([1 + mult * (cl[i + 1] / cl[i] - 1) for i in range(a, b)]) - 1) * 100
        print(f"  {code} {y}: 실제 {real:+6.1f} · 흉내 {sim_:+6.1f} · 지수 {(cl[b] / cl[a] - 1) * 100:+6.1f}", flush=True)
sigs = [("A 지수 < 60일선", (cl < M[60]) & ~np.isnan(M[60])),
        ("B 지수 < 20일선 · 폭 < 50", (cl < M[20]) & ~np.isnan(M[20]) & (br < 50)),
        ("C 20일선 < 60일선", (M[20] < M[60]) & ~np.isnan(M[60])),
        ("D C · 지수 < 20일선 · 폭 < 40", (M[20] < M[60]) & (cl < M[20]) & (br < 40)),
        ("E 시장 폭 < 30", br < 30),
        ("F 폭 < 30 · 지수 < 20일선", (br < 30) & (cl < M[20])),
        ("G 폭 < 20", br < 20),
        ("H 5일선 < 20일선 < 60일선 · 폭 < 40", (M[5] < M[20]) & (M[20] < M[60]) & (br < 40))]
for code in ("114800", "251340", "252670"):
    if code not in ETF:
        continue
    print(f"\n[{code}]", flush=True)
    for tag, sig in sigs:
        show(tag, sig, code)
print("끝", flush=True)
