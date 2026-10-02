"""W 6회차(W6) — 지수 인버스(하락에 거는 것). 인버스 ETF 일봉 대신 코스피 지수 일봉으로 흉내: 하루 손익 = −(지수 하루 수익) − 보수(연 0.64%).
신호는 그날 종가로 정하고 그날 종가에 들어가 다음 날 종가까지 들고 감(1일봉 규칙처럼 장 끝 무렵 판단). 들고 갈아탈 때마다 비용(기본 0.1%, 0.5%도).
잣대: 두 반(2017 ~ 2020 · 2021 ~)의 연 · 골 · 갈아탄 수 · 1일봉 규칙(새 82)과 주 손익 상관 · 반반 계좌(1일봉 확정 손익 + 인버스 평가 손익) 합 · 골 · 가장 나쁜 주."""
import json
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
FEE = 0.0064 / 250
MID = nrl.rule.MID


def ma(n):
    out = np.full(len(cl), np.nan)
    c = np.cumsum(np.insert(cl, 0, 0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


M = {n: ma(n) for n in (5, 10, 20, 60, 120, 200)}
br = np.array([nrl.BR.get(d, np.nan) for d in days], float)


def sim(sig, cost):
    """sig[i] True면 i일 종가에 인버스를 들고 i+1일 종가까지. 날마다 계좌 % 손익(i+1일 날짜에 붙임)."""
    out, held, flips = {}, False, 0
    for i in range(len(days) - 1):
        want = bool(sig[i])
        g = 0.0
        if want != held:
            g -= cost
            flips += 1
            held = want
        if held:
            g += (-(cl[i + 1] / cl[i] - 1) - FEE) * 100
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


def show(tag, sig):
    for cost in (0.1, 0.5):
        mine, flips = sim(sig, cost)
        line = [f"  {tag:<40} 비용 {cost}%"]
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
below = lambda n: cl < nan0(M[n]) if True else None
import os
PART = os.environ.get("Q_PART", "1")
print(f"== W 6회차({PART}): 지수 인버스(코스피로 흉내) ==", flush=True)
if PART == "2":
    exec(open(__file__.replace("w006.py", "w006b.inc"), encoding="utf-8").read())
    sys.exit()
for n in (20, 60, 120, 200):
    show(f"A 지수 < {n}일선", (cl < M[n]) & ~np.isnan(M[n]))
for n in (20, 60, 120):
    show(f"B 지수 < {n}일선 · 시장 폭 < 50", (cl < M[n]) & ~np.isnan(M[n]) & (br < 50))
for a, b in ((5, 20), (10, 60), (20, 60), (20, 120)):
    show(f"C {a}일선 < {b}일선", (M[a] < M[b]) & ~np.isnan(M[b]))
show("D C(20<60) · 지수 < 20일선 · 시장 폭 < 40", (M[20] < M[60]) & (cl < M[20]) & (br < 40))
show("E 시장 폭 < 30", br < 30)
print("끝", flush=True)
