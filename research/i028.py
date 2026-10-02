"""I 43회차 — 인버스 2배(252670 KODEX 200선물인버스2X · 2016-09 ~) 일봉(사용자 2026-10-03 "인버스 x2배도 연구"). 1배(114800)와 같은 신호로 나란히.
신호(그날 종가 판단 → 그날 종가에 삼):
  하락 시작(I1): 20일 신저가 · 60일 신저가 · 역배열(5<20<60 · 종가<20일선) · 5일 −5% · 20일선 아래 · 20일선 내림
  과열 뒤(I20): 코스피 5일 +5 · +6% · 10일 +8 · +10% · 코스닥150 10일 +10%(I22 신호를 코스피 2배 인버스로)
나오는 법: 익절 2 · 4 · 6 × 손절 2 · 3 · 5 × 5 · 10 · 20일 × 손절 뒤 쉬기 0 · 20(108판). 기간 B · C1 · 2026, 비용 0.2%.
잣대(같음): 기간 모두 연 + · 골 −15% 안."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

k = I.K200
q = I.px("229200")
I.px("252670")
m5, m20, m60 = I.ma(k, 5), I.ma(k, 20), I.ma(k, 60)
m20_5 = np.concatenate([np.full(5, np.nan), m20[:-5]])
nz = lambda a: np.nan_to_num(a, nan=0) != 0
r = {n: np.nan_to_num(I.ret(k, n), nan=0) for n in (5, 10)}
SIG = {
    "20일 신저가": nz(k < I.low_before(k, 20)),
    "60일 신저가": nz(k < I.low_before(k, 60)),
    "역배열 · 종가<20일선": nz((m5 < m20) & (m20 < m60) & (k < m20)),
    "5일 −5% 급락": r[5] <= -0.05,
    "20일선 아래 · 20일선 내림": nz((k < m20) & (m20 < m20_5)),
    "코스피 5일 +5%(과열)": r[5] >= 0.05,
    "코스피 5일 +6%": r[5] >= 0.06,
    "코스피 10일 +8%": r[10] >= 0.08,
    "코스피 10일 +10%": r[10] >= 0.10,
    "코스닥150 10일 +10%": np.nan_to_num(I.ret(q, 10), nan=0) >= 0.10,
}
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 43회차: 인버스 2배(252670) vs 1배(114800) 일봉 ==", flush=True)
for name, sig in SIG.items():
    for code in ("114800", "252670"):
        rows = []
        for take in (0.02, 0.04, 0.06):
            for stop in (-0.02, -0.03, -0.05):
                for maxd in (5, 10, 20):
                    for cool in (0, 20):
                        tr, d = I.sim(sig, code, stop, take, maxd, cool=cool)
                        js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
                        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                        rows.append((ok, min(j["cagr"] for j in js), f"익절 {take*100:.0f} 손절 {stop*100:.0f} {maxd}일 쉬기 {cool}",
                                     " | ".join(f"{nm} {j['n']}건 연 {j['cagr']:+.1f} 골 {j['dd']:.1f}" for (nm, _, _), j in zip(PER, js))))
        rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
        print(f"[{name} · {'2배' if code == '252670' else '1배'}] 합격 {sum(x[0] for x in rows)}/108 · 맨 위 {rows[0][2]} (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][3]}", flush=True)
print("끝", flush=True)
