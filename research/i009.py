"""I 9회차(I9) — I2b를 현실에 가깝게 다시: 비용 0.2 · 0.4% × 사는 때(그날 종가 · 다음 날 종가 = 하루 늦게) · 해마다 성적.
I2b: KODEX 200 5일 −5% → 익절 3 · 손절 3 · 20일 · 손절 뒤 20일 쉬기. 시가 자료가 없어 '다음 날 종가'를 가장 나쁜 쪽 대신으로 씀.
이웃 판(익절 2 ~ 4 · 손절 2 ~ 4)도 하루 늦게 · 0.4%에서 버티는지 봄(고원)."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

k = I.K200
r5 = np.nan_to_num(I.ret(k, 5), nan=0) <= -0.05
late = np.concatenate([[False], r5[:-1]])
print("== I 9회차(I9): I2b 현실 점검 ==", flush=True)
for cost in (0.002, 0.004):
    for tag, sig in (("그날 종가", r5), ("다음 날 종가", late)):
        tr, d = I.sim(sig, "069500", -0.03, 0.03, 20, cost=cost, cool=20)
        text, _ = I.line(f"비용 {cost*100:.1f} · {tag}", tr, d)
        print(text, flush=True)
print("\n-- 이웃 판(다음 날 종가 · 비용 0.4%) 합격(세 기간 연 + · 골 −15 안) --", flush=True)
for take in (0.02, 0.03, 0.04):
    cells = []
    for stop in (-0.02, -0.03, -0.04):
        tr, d = I.sim(late, "069500", stop, take, 20, cost=0.004, cool=20)
        js = [I.judge(tr, d, lo, hi) for _, lo, hi in I.PERIODS]
        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
        cells.append(f"손절 {stop*100:.0f}: {'합격' if ok else '탈락'} 가장 나쁜 연 {min(j['cagr'] for j in js):+4.1f}")
    print(f"  익절 {take*100:.0f} | " + " | ".join(cells), flush=True)
print("\n-- 해마다(그날 종가 · 비용 0.2%) --", flush=True)
tr, d = I.sim(r5, "069500", -0.03, 0.03, 20, cool=20)
for y in range(2009, 2027):
    lo, hi = (f"{y}0916" if y == 2009 else f"{y}0101"), f"{y + 1}0101"
    j = I.judge(tr, d, lo, hi)
    if j:
        yr = np.prod([1 + x for x in d[[i for i, dd in enumerate(I.DAYS) if lo <= dd < hi]]]) - 1
        print(f"  {y}: {j['n']:2d}건 이김 {j['win']:5.1f} 그해 {yr*100:+5.1f}% 골 {j['dd']:6.1f}", flush=True)
print("끝", flush=True)
