"""통합 매매 규칙 DNA → RNA 검토 ② 빈칸 엔진 · 코스닥 인버스(사용자 2026-10-03).
DNA: 급락 = 코스피200 5일 ≤ −5% · 코스닥 과열 = 코스닥150 10일 ≥ +10%.
RNA: 그 지수의 앞 60일 하루 흔들림(표준편차 · 그날까지만)으로 나눔 → 급락 = 5일 ≤ −k × σ × √5 · 과열 = 10일 ≥ +k × σ × √10.
k는 DNA와 신호 날 수가 비슷해지는 값 근처를 흔듦. 사고팔기(익절 · 손절 · 기간 · 쉼)는 그대로. 계좌 전부 · A 2012 ~ 2016 · B · C."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

PER = (("A", "20120101", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))


def sigma(p, n=60):
    r = np.concatenate([[np.nan], p[1:] / p[:-1] - 1])
    out = np.full(len(p), np.nan)
    for i in range(n, len(p)):
        w = r[i - n + 1:i + 1]
        out[i] = np.nanstd(w)
    return out


def show(tag, sig, code, st, tk, days, cool=0):
    tr, dd = I.sim(sig, code, st, tk, days, cool=cool)
    cells = []
    for p, lo, hi in PER:
        s = I.stats(dd, lo, hi)
        n = sum(1 for a, b, _ in tr if lo <= I.DAYS[a] < hi)
        cells.append(f"{p} {s[0]:+5.1f} · {s[1]:6.1f} ({n}건)" if s else f"{p} -")
    print(f"  {tag:26s} 신호 날 {int(np.nansum(sig))} | " + " | ".join(cells), flush=True)


k = I.K200
sk = sigma(k)
r5 = np.nan_to_num(I.ret(k, 5), nan=0)
print("== 급락 되돌림(KODEX 200 · 익절 3 · 손절 3 · 20일 · 손절 뒤 20일 쉼) ==")
show("DNA 5일 ≤ −5%", r5 <= -0.05, "069500", -0.03, 0.03, 20, 20)
for kk in (2.0, 2.25, 2.5, 2.75, 3.0):
    show(f"RNA 5일 ≤ −{kk}σ√5", r5 <= -kk * np.nan_to_num(sk, nan=9) * np.sqrt(5), "069500", -0.03, 0.03, 20, 20)
q = I.px("229200")
sq = sigma(q)
r10 = np.nan_to_num(I.ret(q, 10), nan=0)
print("== 코스닥 과열 인버스(251340 · 익절 1.5 · 손절 1.5 · 10일 · 코스닥150은 2015-10부터라 A는 짧음) ==")
show("DNA 10일 ≥ +10%", r10 >= 0.10, "251340", -0.015, 0.015, 10)
for kk in (2.0, 2.25, 2.5, 2.75, 3.0):
    show(f"RNA 10일 ≥ +{kk}σ√10", r10 >= kk * np.nan_to_num(sq, nan=9) * np.sqrt(10), "251340", -0.015, 0.015, 10)
