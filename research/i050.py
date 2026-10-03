"""RNA 17라운드 — D9 하락 추세 달러 RNA를 빈칸 엔진만(계좌 전부 · i040 꼴)으로 A · B · C에서.
DNA: 138230 20일 > +2% 그리고 코스피200 < 20일선. RNA: v{c}(c × 138230 σ60 × √20) · p{q}(20일 수익 자기 기록 아래 q 자리) · 띠 b(20일선 × (1 − bσ√20)).
미래 참조: σ · 백분위는 그날까지 · 달러는 하루 밀어 씀."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i011 as R
import itools as I

D, n = I.DAYS, len(I.DAYS)
k = I.K200
COST = 0.002
CANDS = ["133690", "138230", "132030", "148070"]
PER = (("A 12~16", "20120101", "20170101"), ("B 17~20", "20170101", "20210101"), ("C 21~", "20210101", "20991231"))
shift = lambda a: np.concatenate([[False], a[:-1]])
rot = R.run(R.G["언제나"], R.momentum(20, 2, CANDS), COST)
tr, dd = I.sim(np.nan_to_num(I.ret(k, 5), nan=0) <= -0.05, "069500", -0.03, 0.03, 20, cool=20, cost=COST)
dip_on = np.zeros(n, bool)
for a, b, _ in tr:
    dip_on[a + 1:b + 1] = True
dol = I.px("138230")
d20 = np.nan_to_num(dol / np.concatenate([np.full(20, np.nan), dol[:-20]]) - 1, nan=0)
dret = np.nan_to_num(np.concatenate([[0.0], dol[1:] / dol[:-1] - 1]))
sd, sk, m20 = I.sigma_n(dol, 60), I.sigma_n(k, 60), I.ma(k, 20)


def engine(th, band=0.0):
    cond = (d20 > np.nan_to_num(th, nan=9)) & (np.nan_to_num(k < m20 * (1 - band * sk * np.sqrt(20)), nan=0) > 0)
    on = shift(cond) & ~dip_on
    turn = np.abs(np.diff(np.concatenate([[0], on.astype(float)])))
    e = np.where(dip_on, dd, np.where(on, dret - turn * COST / 2, rot))
    for a, b, _ in tr:
        e[a] += dd[a]
    return e, on.mean() * 100


def show(name, th, band=0.0):
    e, on = engine(th, band)
    print(f"  {name:14s} 달러 든 날 {on:4.1f}% | " + " | ".join(f"{p} {I.stats(e, lo, hi)[0]:+5.1f} · {I.stats(e, lo, hi)[1]:6.1f}" for p, lo, hi in PER), flush=True)


print("== RNA 17라운드: 하락 추세 달러 RNA(빈칸 엔진만 · 연 · 골) ==")
show("DNA +2%", np.full(n, 0.02))
show("달러 빼기", np.full(n, 9.0))
for c in (0.3, 0.4, 0.5, 0.6, 0.8):
    show(f"v{c}", sd * c * np.sqrt(20))
for q in (0.6, 0.7, 0.8, 0.9):
    show(f"p{q}", I.pct_hist(d20, q))
for b in (-0.2, 0.2, 0.4):
    show(f"DNA · 띠 {b:+.1f}", np.full(n, 0.02), b)
print(f"  참고: +2%는 v 몇 배? 가운데 {np.nanmedian(0.02 / (sd * np.sqrt(20))):.2f}")
