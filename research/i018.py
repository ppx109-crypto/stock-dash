"""I 20회차 — '과열 뒤 인버스'(I2b의 거울): 한국 지수는 이어가기보다 되돌아오는 일이 많음(I1 · I2) → 급등 뒤 되돌림 하락을 1배 인버스로 먹음.
신호(그날 종가 판단 → 그날 종가에 인버스 삼):
  U1 5일 +N%(N = 4 · 5 · 6 · 7) · U2 10일 +N%(6 · 8 · 10) · U3 20일선보다 +N% 위(5 · 8 · 10) · U4 3일 연속 오름 · 3일 +N%(3 · 4)
나오는 법: 익절 2 · 3 · 4 × 손절 2 · 3 · 4 × 5 · 10 · 20일 · 손절 뒤 쉬기 20(급등이 이어지는 장에서 연달아 손절 막기).
I_CODE: 114800(코스피 · 신호 KODEX 200) · 251340(코스닥150 인버스 · 신호 229200, 2016-08 ~ B · C만). 잣대: 기간 모두 연 + · 골 −15 안."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

CODE = os.environ.get("I_CODE", "114800")
k = I.K200 if CODE == "114800" else I.px("229200")
I.px(CODE)
m20 = I.ma(np.nan_to_num(k, nan=0), 20)
r = {n: np.nan_to_num(I.ret(k, n), nan=0) for n in (3, 5, 10)}
up3 = np.zeros(len(k), bool)
up3[3:] = (k[3:] > k[2:-1]) & (k[2:-1] > k[1:-2]) & (k[1:-2] > k[:-3])
SIG = {}
for t in (0.04, 0.05, 0.06, 0.07):
    SIG[f"U1 5일 +{t*100:.0f}%"] = r[5] >= t
for t in (0.06, 0.08, 0.10):
    SIG[f"U2 10일 +{t*100:.0f}%"] = r[10] >= t
for t in (0.05, 0.08, 0.10):
    SIG[f"U3 20일선 +{t*100:.0f}% 위"] = np.nan_to_num(k / m20 - 1, nan=0) >= t
for t in (0.03, 0.04):
    SIG[f"U4 3일 연속 오름 · 3일 +{t*100:.0f}%"] = up3 & (r[3] >= t)
PER = I.PERIODS if CODE == "114800" else I.PERIODS[1:]
PER = tuple(PER) + (("C2", "20260101", "20991231"),)
print(f"== I 20회차: 과열 뒤 인버스 · {CODE} ==", flush=True)
best_all = []
for name, sig in SIG.items():
    rows = []
    for take in (0.02, 0.03, 0.04):
        for stop in (-0.02, -0.03, -0.04):
            for maxd in (5, 10, 20):
                tr, d = I.sim(sig, CODE, stop, take, maxd, cool=20)
                js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER[:-1]]
                ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                rows.append((ok, min(j["cagr"] for j in js), I.line(f"{name} | 익절 {take*100:.0f} 손절 {stop*100:.0f} {maxd}일", tr, d, PER)[0]))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(f"[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(x[0] for x in rows)}/27 · 맨 위: (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][2].strip()}", flush=True)
    best_all += rows[:1]
print("끝", flush=True)
