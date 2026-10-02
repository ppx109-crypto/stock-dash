"""I 6회차(I2c 고침) — 코스피 · 코스닥 급락 되돌림을 **한 번에 하나만** 듦. 둘 다 문턱을 넘으면 5일 더 빠진 쪽, 들고 있는 동안 새로 안 삼.
판: 문턱 −5 · −6 · −7% × 익절 3 · 4 · 5 × 손절 3 · 4 × 20일 × 쉬기 0 · 10 · 20. 견줌: 코스피만(I2b 맨 위 판). 기간 A(코스닥 2015-10 ~라 A는 코스피만 쓰임) · B · C."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

kq = I.PX["229200"]
r5k = np.nan_to_num(I.ret(I.K200, 5), nan=0)
r5q = np.nan_to_num(I.ret(kq, 5), nan=0)


def sim2(th, take, stop, maxd, cool, cost=0.002):
    n = len(I.DAYS)
    daily = np.zeros(n)
    trades = []
    i = 0
    while i < n - 1:
        hk, hq = r5k[i] <= th, r5q[i] <= th and not np.isnan(kq[i])
        if not (hk or hq):
            i += 1
            continue
        code = "229200" if hq and (not hk or r5q[i] <= r5k[i]) else "069500"
        px = I.PX[code]
        p0 = px[i]
        daily[i] -= cost / 2
        j = i + 1
        while j < n:
            daily[j] += px[j] / px[j - 1] - 1
            r = px[j] / p0 - 1
            if r <= stop or r >= take or j - i >= maxd:
                break
            j += 1
        j = min(j, n - 1)
        daily[j] -= cost / 2
        r = px[j] / p0 - 1
        trades.append((i, j, r - cost))
        i = j + 1 + (cool if r <= stop else 0)
    return trades, daily


print("== I 6회차: 코스피 · 코스닥 급락 되돌림 · 한 번에 하나만 ==", flush=True)
rows = []
for th in (-0.05, -0.06, -0.07):
    for take in (0.03, 0.04, 0.05):
        for stop in (-0.03, -0.04):
            for cool in (0, 10, 20):
                tr, d = sim2(th, take, stop, 20, cool)
                js = [I.judge(tr, d, lo, hi) for _, lo, hi in I.PERIODS]
                ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                text, worst = I.line(f"둘 중 더 빠진 쪽 5일 {th*100:.0f}% | 익절 {take*100:.0f} 손절 {stop*100:.0f} 쉬기 {cool}", tr, d)
                rows.append((ok, worst, min(j['dd'] for j in js), text))
good = [r for r in rows if r[0]]
print(f"  판 {len(rows)} · 합격 {len(good)}", flush=True)
for r in sorted(good or rows, key=lambda r: -r[1])[:8]:
    print(f"  {'✔' if r[0] else '·'} 가장 나쁜 연 {r[1]:+5.1f} 골 {r[2]:6.1f} " + r[3].strip(), flush=True)
tr, d = I.sim(r5k <= -0.05, "069500", -0.03, 0.03, 20, cool=20)
print("  견줌 " + I.line("코스피만(I2b 맨 위 판)", tr, d)[0].strip(), flush=True)
print("끝", flush=True)
