"""I 5회차(I5) — 1일봉 규칙(새 82)과 함께 굴리기. 1일봉이 비워 둔 돈(10칸 중 빈 칸 몫)으로만 I 규칙(KODEX 200 급락 되돌림)을 함.
1일봉 손익: x008_d1.json 매매(산 날 · 판 날 · 손익% · 칸) — 판 날에 확정(칸/10 × 손익). 비어 있는 몫 = 1 − (들고 있는 칸 합)/10.
I 손익: itools.sim(무게 1)의 날마다 수익 × 그날 비어 있는 몫(사는 날 몫으로 고정).
견줌(B 2017 ~ 2020 · C 2021 ~): 1일봉만 / I만 / 함께 — 합 · 연 · 골 · 가장 나쁜 주 · 주 상관."""
import json
import sys
from datetime import date

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
led = json.load(open(SP + "x008_d1.json"))
D = I.DAYS
n = len(D)
used = np.zeros(n)
d1 = np.zeros(n)                       # 1일봉 확정 손익(계좌 %)
for code, buy, sell, pnl, slots in led:
    a = np.searchsorted(D, buy)
    b = np.searchsorted(D, sell)
    used[a:b] += slots / 10
    if b < n:
        d1[b] += pnl * slots / 10 / 100
free = np.clip(1 - used, 0, 1)
k = I.K200
r5 = np.nan_to_num(I.ret(k, 5), nan=0)


BR = np.nan_to_num(I.breadth(), nan=100)
MODE = __import__("os").environ.get("I_MODE", "")


def i_daily(th, take, stop, maxd, cool):
    sig = r5 <= th
    if MODE == "weak":            # 시장 폭 50 아래(1일봉 규칙이 쉬는 장)일 때만
        sig = sig & (BR < 50)
    elif MODE == "free":          # 1일봉이 70% 넘게 비워 둔 날만
        sig = sig & (free >= 0.7)
    elif MODE == "half":          # 넣는 몫을 비운 돈의 절반으로
        pass
    tr, d = I.sim(sig, "069500", stop, take, maxd, cool=cool)
    out = np.zeros(n)
    for i, j, _ in tr:                 # 사는 날 비어 있는 몫으로 고정
        out[i:j + 1] += d[i:j + 1] * free[i] * (0.5 if MODE == "half" else 1.0)
    return out, tr


def wk(s):
    return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isocalendar()[:2]


def stats(r, lo, hi):
    idx = [i for i, x in enumerate(D) if lo <= x < hi]
    a, b = idx[0], idx[-1]
    eq = np.cumprod(1 + r[a:b + 1])
    dd = float((eq / np.maximum.accumulate(eq) - 1).min()) * 100
    yrs = (b - a + 1) / 250
    w = {}
    for i in range(a, b + 1):
        w[wk(D[i])] = w.get(wk(D[i]), 0) + r[i]
    return (eq[-1] - 1) * 100, (eq[-1] ** (1 / yrs) - 1) * 100, dd, min(w.values()) * 100, w


print(f"== I 5회차(I5): 1일봉 규칙 + I 규칙(1일봉이 비워 둔 돈으로만) · 판 {MODE or '기본'} ==", flush=True)
print(f"  1일봉이 비워 둔 몫(평균): B {free[[i for i,x in enumerate(D) if '2017' <= x < '2021']].mean()*100:.0f}% · C {free[[i for i,x in enumerate(D) if x >= '2021']].mean()*100:.0f}%", flush=True)
for th, take, stop, maxd, cool in ((-0.05, 0.03, -0.03, 20, 20), (-0.05, 0.03, -0.04, 20, 20), (-0.05, 0.06, -0.05, 20, 10), (-0.06, 0.04, -0.04, 20, 20)):
    mine, tr = i_daily(th, take, stop, maxd, cool)
    print(f"\n[I: 5일 {th*100:.0f}% · 익절 {take*100:.0f} · 손절 {stop*100:.0f} · {maxd}일 · 쉬기 {cool}]", flush=True)
    for name, lo, hi in (("B", "20170101", "20210101"), ("C", "20210101", "20991231")):
        a = stats(d1, lo, hi)
        m = stats(mine, lo, hi)
        c = stats(d1 + mine, lo, hi)
        ws = sorted(set(a[4]) | set(m[4]))
        va = np.array([a[4].get(x, 0) for x in ws]); vb = np.array([m[4].get(x, 0) for x in ws])
        corr = float(np.corrcoef(va, vb)[0, 1]) if vb.std() else float("nan")
        print(f"  {name} 1일봉만 합 {a[0]:+7.1f} 연 {a[1]:+6.1f} 골 {a[2]:6.1f} 나쁜 주 {a[3]:5.1f} | I만(비운 돈) 합 {m[0]:+6.1f} 연 {m[1]:+5.1f} 골 {m[2]:6.1f} | "
              f"함께 합 {c[0]:+7.1f} 연 {c[1]:+6.1f} 골 {c[2]:6.1f} 나쁜 주 {c[3]:5.1f} · 주 상관 {corr:+.2f}", flush=True)
print("끝", flush=True)
