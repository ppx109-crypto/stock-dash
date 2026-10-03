"""RNA 6라운드 — D11 코스닥 과열 인버스만 따로(1일봉 장부 · 엔진 없이 계좌 전부): DNA 익절손절 ±1.5% vs RNA c × 229200 앞 60일 σ × √10.
신호: 229200 10일 수익 ≥ 문턱(그날 종가까지) · 251340을 그날 사서 10일. 해마다 · 매매 수 · 이긴 비율. 미래 참조: σ는 산 날까지 값."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
COST = float(os.environ.get("I_COST", 0.002))
TH = float(os.environ.get("I_QTH", 0.10))
qq = I.px("229200")
I.px("251340")
sig = np.nan_to_num(I.ret(qq, 10), nan=0) >= TH
first = next(i for i in range(n) if np.isfinite(I.PX["251340"][i]))
print(f"== RNA 6라운드: 코스닥 과열 인버스만(문턱 {TH:+.1%} · 비용 {COST}) · 251340 첫날 {D[first]} ==")
sq = I.sigma_n(qq, int(os.environ.get("I_QSIGN", "60")))
YEARS = [str(y) for y in range(2016, 2027)]


def row(tr, dd, name):
    yr = " ".join(f"{y[2:]}:{(np.prod(1 + dd[[d[:4] == y for d in D]]) - 1) * 100:+5.1f}" for y in YEARS)
    win = np.mean([t[2] > 0 for t in tr]) * 100 if tr else 0
    per = " | ".join(f"{p} {I.stats(dd, lo, hi)[0]:+5.1f} · {I.stats(dd, lo, hi)[1]:6.1f}" for p, lo, hi in
                     (("16~20", "20160101", "20210101"), ("21~25", "20210101", "20260101"), ("26", "20260101", "20991231")))
    print(f"  {name:10s} 매매 {len(tr):3d} 이김 {win:3.0f}% | {per}\n             {yr}", flush=True)


tr, dd = I.sim(sig, "251340", -0.015, 0.015, 10, cost=COST)
row(tr, dd, "DNA ±1.5%")
for c in [float(x) for x in os.environ.get("I_QCS", "0.22,0.25,0.28,0.31,0.34").split(",")]:
    s = sq * c * np.sqrt(10)
    tr, dd = I.sim_var(sig, "251340", -s, s, 10, cost=COST)
    row(tr, dd, f"RNA {c:.2f}")
s = sq * 0.28 * np.sqrt(10)
print(f"  0.28 문턱 크기(산 날): 중앙 {np.nanmedian(s[sig]) * 100:.2f}% · 아래 10% {np.nanpercentile(s[sig], 10) * 100:.2f}% · 위 10% {np.nanpercentile(s[sig], 90) * 100:.2f}%")
