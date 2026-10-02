"""I 38 · 40회차.
I38: 코스닥 과열 인버스(I22 · 229200 10일 +10% → 251340 · 익절 1.5 · 손절 1.5 · 10일) 해마다 건수 · 이김 · 그해 수익(몰림 점검).
I40: 돌리기(나스닥 · 달러 · 금 · 국채10년) '미리 고르기' — 해마다 그 앞 3년 성적(연 수익 ÷ |골|)만 보고 L(10 · 20 · 40 · 60) × 위(1 · 2) 8판 중 하나를 골라 그해에 씀.
     고정 판(20일 위 2)과 해마다 견줌(계좌 전부 · 늘 켬 · i011.run)."""
import contextlib
import io
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
q10 = np.nan_to_num(I.ret(I.px("229200"), 10), nan=0) >= 0.10
tr, d = I.sim(q10, "251340", -0.015, 0.015, 10)
print("== I 38회차: 코스닥 과열 인버스 해마다 ==", flush=True)
for y in range(2016, 2027):
    idx = [i for i, x in enumerate(D) if x.startswith(str(y))]
    t = [x for x in tr if idx[0] <= x[0] <= idx[-1]]
    yr = (np.prod(1 + d[idx]) - 1) * 100
    print(f"  {y}: {len(t):2d}건 이김 {np.mean([x[2] > 0 for x in t]) * 100 if t else 0:3.0f}% · 그해 {yr:+5.1f}%", flush=True)

with contextlib.redirect_stdout(io.StringIO()):
    import i011 as R
C = ["133690", "138230", "132030", "148070"]
ALW = R.G["언제나"]
cands = [(L, top) for L in (10, 20, 40, 60) for top in (1, 2)]
runs = {c: R.run(ALW, R.momentum(c[0], c[1], C)) for c in cands}


def score(dly, lo, hi):
    s = I.stats(dly, lo, hi)
    return s[0] / max(abs(s[1]), 1)


wf = np.zeros(n)
print("\n== I 40회차: 돌리기 미리 고르기(앞 3년 성적으로 그해 판 고름) ==", flush=True)
for y in range(2014, 2027):
    lo, hi = f"{y - 3}0101", f"{y}0101"
    best = max(cands, key=lambda c: score(runs[c], lo, hi))
    idx = [i for i, x in enumerate(D) if x.startswith(str(y))]
    wf[idx] = runs[best][idx]
    fx = (np.prod(1 + runs[(20, 2)][idx]) - 1) * 100
    w = (np.prod(1 + wf[idx]) - 1) * 100
    print(f"  {y}: 고른 판 {best[0]}일 위 {best[1]} → 그해 {w:+5.1f}% | 고정(20일 위 2) {fx:+5.1f}%", flush=True)
for nm, lo, hi in (("2014 ~ 2016", "20140101", "20170101"), ("B 2017 ~ 2020", "20170101", "20210101"), ("C1 2021 ~ 2025", "20210101", "20260101"), ("2026", "20260101", "20991231")):
    a, b = I.stats(wf, lo, hi), I.stats(runs[(20, 2)], lo, hi)
    print(f"  {nm}: 미리 고르기 연 {a[0]:+.1f} 골 {a[1]:.1f} | 고정 연 {b[0]:+.1f} 골 {b[1]:.1f}", flush=True)
print("끝", flush=True)
