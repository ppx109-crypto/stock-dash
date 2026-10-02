"""I 1회차 — 인버스 '짧게 치고 빠지기'(사용자 2026-10-02 "하락 · 횡보장에 버틸 수 있는 인버스 개발").
W10은 '약세 신호가 켜진 동안 계속 들고 있기'라 반등 · 옆걸음에 다 토해 냄 → 하락이 **시작될 때** 들어가 손절 · 익절 · 기간으로 끊음.
들어가는 신호(지수 대신 KODEX 200 종가 · 2009 ~ 세 기간):
  E1 20일 신저가(앞 20일 가장 낮은 종가 아래) · E2 60일 신저가 · E3 역배열(5 < 20 < 60일선) · 종가 < 20일선
  E4 5일 −5% 급락 · E5 20일선 아래 + 20일선이 5일 전보다 낮음 · E6 E1 + 종가 < 120일선(큰 흐름도 약세)
나오는 법: 손절 −3 · −5% × 익절 +4 · +8 · +15% × 기간 5 · 10 · 20일, 또는 '종가 > 20일선이면 나옴'.
상품: 114800(−1배) · 252670(−2배, 2016-09 ~). 비용 0.2%(사고팔기 합). 잣대: 세 기간 가운데 가장 나쁜 연 수익(모두 + 여야)."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

k = I.K200
m5, m20, m60, m120 = (I.ma(k, n) for n in (5, 20, 60, 120))
lo20, lo60 = I.low_before(k, 20), I.low_before(k, 60)
r5 = I.ret(k, 5)
m20_5 = np.concatenate([np.full(5, np.nan), m20[:-5]])
nz = lambda a: np.nan_to_num(a, nan=0) != 0
ENTRIES = {
    "E1 20일 신저가": k < lo20,
    "E2 60일 신저가": k < lo60,
    "E3 역배열 · 종가 < 20일선": (m5 < m20) & (m20 < m60) & (k < m20),
    "E4 5일 −5% 급락": r5 <= -0.05,
    "E5 20일선 아래 · 20일선 내림": (k < m20) & (m20 < m20_5),
    "E6 20일 신저가 · 종가 < 120일선": (k < lo20) & (k < m120),
}
above20 = k > m20
code = os.environ.get("I_CODE", "114800")
cost = float(os.environ.get("I_COST", "0.002"))
print(f"== I 1회차: 인버스 짧게 치고 빠지기 · {code} · 비용 {cost * 100:.1f}% ==", flush=True)
for name, sig in ENTRIES.items():
    sig = np.nan_to_num(sig.astype(float), nan=0) > 0
    best = []
    for stop in (-0.03, -0.05):
        for take in (0.04, 0.08, 0.15):
            for maxd in (5, 10, 20):
                tr, d = I.sim(sig, code, stop, take, maxd, cost=cost)
                text, worst = I.line(f"{name} | 손절 {stop * 100:.0f} 익절 {take * 100:.0f} {maxd}일", tr, d)
                best.append((worst if worst is not None else -99, text))
        tr, d = I.sim(sig, code, stop, 0.5, 60, exit_sig=above20, cost=cost)
        text, worst = I.line(f"{name} | 손절 {stop * 100:.0f} · 20일선 위면 나옴", tr, d)
        best.append((worst if worst is not None else -99, text))
    best.sort(reverse=True)
    print(f"\n[{name}] 가장 나쁜 기간 연 수익 순 위 4 · 아래 1", flush=True)
    for w, t in best[:4] + best[-1:]:
        print(f"  (가장 나쁜 {w:+5.1f}) " + t.strip(), flush=True)
print("끝", flush=True)
