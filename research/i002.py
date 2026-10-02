"""I 2회차 — 지수 급락 되돌림(KODEX 200 · 레버리지 없이). I1에서 '급락 뒤 인버스'가 가장 크게 잃음 → 반대로 급락 뒤 지수 ETF를 사서 반등만 먹고 나옴.
약세 · 옆걸음 날에 쓰려는 것이라 '지수 < 60일선(큰 흐름 약함)'인 날만 따로도 봄.
들어가는 신호(그날 종가 판단 · 그날 종가에 삼):
  D1 5일 −4% · D2 5일 −6% · D3 3일 연속 하락 · 3일 −3% · D4 20일선보다 −5% 아래 · D5 20일 신저가 · D6 볼린저 하단(20일 평균 − 2표준편차) 아래
나오는 법: 익절 +2 · +4 · +6% × 손절 −4 · −8% × 기간 5 · 10 · 20일, 또는 '종가 > 20일선이면 나옴'.
상품: 069500 KODEX 200(I_CODE로 122630 레버리지도). 비용 0.2%. 잣대: 세 기간 가장 나쁜 연 수익."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

k = I.K200
m20, m60 = I.ma(k, 20), I.ma(k, 60)
sd20 = np.full(len(k), np.nan)
for i in range(19, len(k)):
    sd20[i] = k[i - 19:i + 1].std()
r3, r5 = I.ret(k, 3), I.ret(k, 5)
down3 = np.zeros(len(k), bool)
down3[3:] = (k[3:] < k[2:-1]) & (k[2:-1] < k[1:-2]) & (k[1:-2] < k[:-3])
lo20 = I.low_before(k, 20)
weak = k < m60
ENTRIES = {
    "D1 5일 −4%": r5 <= -0.04,
    "D2 5일 −6%": r5 <= -0.06,
    "D3 3일 연속 하락 · 3일 −3%": down3 & (r3 <= -0.03),
    "D4 20일선보다 −5% 아래": k <= m20 * 0.95,
    "D5 20일 신저가": k < lo20,
    "D6 볼린저 하단 아래": k < m20 - 2 * sd20,
}
above20 = k > m20
code = os.environ.get("I_CODE", "069500")
cost = float(os.environ.get("I_COST", "0.002"))
print(f"== I 2회차: 지수 급락 되돌림 · {code} · 비용 {cost * 100:.1f}% ==", flush=True)
for only_weak in (False, True):
    print(f"\n######## {'약세(지수 < 60일선)인 날만' if only_weak else '모든 날'} ########", flush=True)
    for name, sig in ENTRIES.items():
        sig = np.nan_to_num(sig.astype(float), nan=0) > 0
        if only_weak:
            sig = sig & np.nan_to_num(weak.astype(float), nan=0).astype(bool)
        best = []
        for take in (0.02, 0.04, 0.06):
            for stop in (-0.04, -0.08):
                for maxd in (5, 10, 20):
                    tr, d = I.sim(sig, code, stop, take, maxd, cost=cost)
                    text, worst = I.line(f"{name} | 익절 {take * 100:.0f} 손절 {stop * 100:.0f} {maxd}일", tr, d)
                    best.append((worst if worst is not None else -99, text))
        for stop in (-0.04, -0.08):
            tr, d = I.sim(sig, code, stop, 0.5, 40, exit_sig=above20, cost=cost)
            text, worst = I.line(f"{name} | 손절 {stop * 100:.0f} · 20일선 위면 나옴", tr, d)
            best.append((worst if worst is not None else -99, text))
        best.sort(reverse=True)
        print(f"\n[{name}] 가장 나쁜 기간 연 수익 순 위 3 · 아래 1", flush=True)
        for w, t in best[:3] + best[-1:]:
            print(f"  (가장 나쁜 {w:+5.1f}) " + t.strip(), flush=True)
print("끝", flush=True)
