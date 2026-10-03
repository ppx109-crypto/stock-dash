"""점검 A13 — 뒤로 걷기(walk-forward): 해마다 '그해 앞까지의 자료로만' 숫자를 다시 골라 그해에 씀 → 고정 숫자 판과 해마다 견줌.
조각별(계좌 전부 · 그 조각만): 코스닥 인버스 신호 문턱 · 급락 되돌림 문턱 · 돌리기 기간. 고르는 잣대 = 앞 기간 연 수익(골이 −15% 넘게 깊으면 뺌)."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i011 as R
import itools as I

D = np.array(I.DAYS)
yr = np.array([d[:4] for d in D])


def yearly(daily, y):
    m = yr == y
    return (np.prod(1 + daily[m]) - 1) * 100


def score(daily, end_year, start="2012"):
    m = (yr >= start) & (yr < end_year)
    if m.sum() < 200:
        return -9e9
    eq = np.cumprod(1 + daily[m])
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    ann = eq[-1] ** (250 / m.sum()) - 1
    return ann if dd > -0.15 else ann - 1


def walk(name, grid, make, fixed, years, start):
    runs = {g: make(g) for g in grid}
    print(f"\n== {name} · 고르는 판 {list(grid)} · 고정 {fixed} ==")
    print("  해   고른 값   고른 판 그해   고정 판 그해")
    a = b = 1.0
    for y in years:
        best = max(grid, key=lambda g: score(runs[g], y, start))
        r1, r2 = yearly(runs[best], y), yearly(runs[fixed], y)
        a *= 1 + r1 / 100
        b *= 1 + r2 / 100
        print(f"  {y}  {best!s:>7}  {r1:+8.1f}   {r2:+8.1f}")
    print(f"  합쳐(곱): 뒤로 걷기 {(a - 1) * 100:+.1f}% · 고정 {(b - 1) * 100:+.1f}%")


q = I.px("229200")
I.px("251340")
sq = np.clip(I.sigma_n(q, 60) * 0.25 * np.sqrt(10), 0.015, 0.025)
one = np.full(len(D), 0.015)
walk("코스닥 인버스 신호 문턱(10일)", (0.08, 0.085, 0.09, 0.095, 0.10, 0.11, 0.12),
     lambda th: I.sim_var(np.nan_to_num(I.ret(q, 10), nan=0) >= th, "251340", -one, sq, 10)[1],
     0.095, [str(y) for y in range(2018, 2027)], "2016")
k = I.K200
walk("급락 되돌림 문턱(5일)", (-0.035, -0.04, -0.045, -0.05, -0.055, -0.06),
     lambda th: I.sim(np.nan_to_num(I.ret(k, 5), nan=0) <= th, "069500", -0.03, 0.03, 20, cool=20)[1],
     -0.045, [str(y) for y in range(2014, 2027)], "2010")
C = ["133690", "138230", "132030", "148070"]
walk("돌리기 기간(위 2)", (10, 15, 20, 30, 40, 60),
     lambda L: R.run(R.G["언제나"], R.momentum(L, 2, C), 0.002),
     20, [str(y) for y in range(2014, 2027)], "2011")
