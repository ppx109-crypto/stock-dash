"""I 7회차(I4) — 옆걸음 박스: 지수(KODEX 200)가 지난 N일 범위의 아래쪽이면 KODEX 200, 위쪽이면 인버스(114800). 1배만.
옆걸음 판별: N일 범위 폭(최고 ÷ 최저 − 1)이 W% 안이고, 60일선 기울기가 작음(|60일선 20일 변화| < S%).
들어감: 범위 아래 20% 자리(KODEX 200) / 위 20% 자리(인버스). 나옴: 범위 가운데 닿음(익절) · 범위 밖으로 X% 벗어남(손절) · 기간.
판: N 40 · 60 · W 8 · 12 · 16% · S 2 · 4% · 손절 2 · 3% · 기간 10 · 20. 롱만 / 인버스만 / 둘 다."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

k = I.K200
m60 = I.ma(k, 60)
slope = np.full(len(k), np.nan)
slope[20:] = m60[20:] / m60[:-20] - 1


def box(N):
    hi, lo = I.high_before(k, N), I.low_before(k, N)
    return hi, lo


def run(N, W, S, stop, maxd, side):
    hi, lo = box(N)
    width = hi / lo - 1
    flat = np.nan_to_num((width <= W) & (np.abs(slope) <= S), nan=0).astype(bool)
    pos = (k - lo) / (hi - lo)
    mid = (hi + lo) / 2
    n = len(k)
    daily = np.zeros(n)
    trades = []
    i = 0
    while i < n - 1:
        if not flat[i] or np.isnan(pos[i]):
            i += 1
            continue
        long_ = pos[i] <= 0.2 and side in ("롱", "둘 다")
        short = pos[i] >= 0.8 and side in ("인버스", "둘 다")
        if not (long_ or short):
            i += 1
            continue
        code = "069500" if long_ else "114800"
        px = I.PX[code]
        if np.isnan(px[i]):
            i += 1
            continue
        p0, m0 = px[i], mid[i]
        daily[i] -= 0.001
        j = i + 1
        while j < n:
            daily[j] += px[j] / px[j - 1] - 1
            r = px[j] / p0 - 1
            hit = (k[j] >= m0) if long_ else (k[j] <= m0)
            if hit or r <= -stop or j - i >= maxd:
                break
            j += 1
        j = min(j, n - 1)
        daily[j] -= 0.001
        trades.append((i, j, px[j] / p0 - 1 - 0.002))
        i = j + 1
    return trades, daily


print("== I 7회차(I4): 옆걸음 박스(지수 범위 아래 KODEX 200 · 위 인버스) ==", flush=True)
rows = []
for side in ("롱", "인버스", "둘 다"):
    for N in (40, 60):
        for W in (0.08, 0.12, 0.16):
            for S in (0.02, 0.04):
                for stop in (0.02, 0.03):
                    for maxd in (10, 20):
                        tr, d = run(N, W, S, stop, maxd, side)
                        js = [I.judge(tr, d, lo, hi) for _, lo, hi in I.PERIODS]
                        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                        text, worst = I.line(f"{side} N{N} 폭{W*100:.0f} 기울기{S*100:.0f} 손절{stop*100:.0f} {maxd}일", tr, d)
                        rows.append((ok, worst, side, text))
for side in ("롱", "인버스", "둘 다"):
    sel = [r for r in rows if r[2] == side]
    good = [r for r in sel if r[0]]
    print(f"\n[{side}] 판 {len(sel)} · 합격 {len(good)}", flush=True)
    for r in sorted(good or sel, key=lambda r: -r[1])[:4]:
        print(f"  {'✔' if r[0] else '·'} 가장 나쁜 연 {r[1]:+5.1f} " + r[3].strip(), flush=True)
print("끝", flush=True)
