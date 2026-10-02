"""I 10회차(I6) — I2b를 '그날 15:15 값으로 판단'하면 '종가로 판단'과 얼마나 다른가(한투 15분봉 약 1년 · etf-m15).
15:15에 알 수 있는 값 = 15:00 칸(15:00 ~ 15:15)의 종가. 판단: 그 값 / 5거래일 앞 종가 − 1 ≤ −5%.
판(그 1년 안에서만 견줌 · KODEX 200 · 익절 3 · 손절 3 · 20일 · 손절 뒤 20일 쉬기 · 비용 0.2%):
  ① 종가 판단 → 종가에 삼(지금 연구 · 실제로는 못 함)
  ② 15:15 판단 → 종가 동시호가에 삼(할 수 있음)
  ③ 15:15 판단 → 15:15 값에 바로 삼(할 수 있음)
  ④ 종가 판단 → 다음 날 종가(하루 늦게 · I9 견줌용)
문턱 −4.5 · −5 · −5.5%도 봄(15:15 값이 종가와 조금 달라 경계에서 갈리는 날)."""
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

CODE = os.environ.get("I_CODE", "069500")
HOME = Path("/home/user/stock-dash") / os.environ.get("I_M15", "etf-m15") / CODE
p1515 = {}
for f in sorted(HOME.glob("*.csv")):
    for line in f.read_text().splitlines():
        t, o, h, l, c, v = line.split(",")[:6]
        if t[8:] == "1500":
            p1515[t[:8]] = float(c)
if not p1515:
    print(f"{HOME}에 15분봉이 아직 없음"); sys.exit(0)
px = I.PX[CODE]
mid = np.array([p1515.get(d, np.nan) for d in I.DAYS])
have = ~np.isnan(mid)
lo, hi = I.DAYS[int(np.argmax(have))], "20991231"
print(f"== I 10회차(I6): 15:15 판단 · {CODE} · {lo} ~ ({int(have.sum())}일) ==", flush=True)
gap = (mid[have] / px[have] - 1) * 100
print(f"  15:15 값과 종가 차이: 평균 {gap.mean():+.2f}% · 절대 평균 {np.abs(gap).mean():.2f}% · 가장 큰 {gap.min():+.2f} / {gap.max():+.2f}%", flush=True)
back5 = np.concatenate([np.full(5, np.nan), px[:-5]])


def sim_at(entry, buy_px, stop=-0.03, take=0.03, maxd=20, cool=20, cost=0.002):
    """itools.sim과 같되 사는 값을 buy_px[i]로(15:15 값에 바로 살 때). 사는 날 수익 = 종가 / 사는 값 − 1."""
    n = len(I.DAYS)
    daily, trades, i = np.zeros(n), [], 0
    while i < n - 1:
        if not entry[i] or np.isnan(buy_px[i]):
            i += 1
            continue
        p0 = buy_px[i]
        daily[i] += px[i] / p0 - 1 - cost / 2
        j = i + 1
        while j < n:
            daily[j] += px[j] / px[j - 1] - 1
            r = px[j] / p0 - 1
            if r <= stop or r >= take or j - i >= maxd:
                break
            j += 1
        j = min(j, n - 1)
        daily[j] -= cost / 2
        trades.append((i, j, px[j] / p0 - 1 - cost))
        i = j + 1 + (cool if px[j] / p0 - 1 <= stop else 0)
    return trades, daily


per = (("1년", lo, hi),)
for th in (-0.045, -0.05, -0.055):
    sig_close = np.nan_to_num(px / back5 - 1, nan=0) <= th
    sig_mid = np.nan_to_num(mid / back5 - 1, nan=0) <= th
    late = np.concatenate([[False], sig_close[:-1]])
    both = int((sig_close & sig_mid & have).sum())
    print(f"\n[문턱 {th*100:.1f}%] 신호 날: 종가 {int((sig_close & have).sum())} · 15:15 {int((sig_mid & have).sum())} · 둘 다 {both}", flush=True)
    for tag, (tr, d) in (("① 종가 판단 → 종가", I.sim(sig_close, CODE, -0.03, 0.03, 20, cool=20)),
                         ("② 15:15 판단 → 종가", I.sim(sig_mid & have, CODE, -0.03, 0.03, 20, cool=20)),
                         ("③ 15:15 판단 → 15:15 값", sim_at(sig_mid & have, mid)),
                         ("④ 종가 판단 → 다음 날 종가", I.sim(late, CODE, -0.03, 0.03, 20, cool=20))):
        print(I.line(tag, tr, d, per)[0], flush=True)
print("끝", flush=True)
