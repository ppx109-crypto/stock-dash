"""I 8회차(I8) — 지수 단기 과매도 새 신호를 I2b(5일 −5% 급락)와 견줌. KODEX 200 · 1배 · 그날 종가에 삼.
신호(그날까지 알려진 것만):
  S0 5일 −5%(I2b 그대로 · 견줌용)
  S1 RSI 2일 < 10 · S2 RSI 2일 < 5
  S3 3일 연속 하락 · S4 4일 연속 하락
  S5 주 −5%(금요일 · 그 주 마지막 거래일 종가가 앞 주 마지막 종가보다 −5%)
  S6 첫 반등: 어제까지 5일 −5% 이상 빠졌고 오늘 오름(떨어지는 칼 피하기)
  S7 RSI 2일 < 10 그리고 종가 < 200일선(약세 안에서만)
나오는 법: 익절 2 · 3 · 4 × 손절 3 · 4 · 5 × 20일 × 손절 뒤 쉬기 0 · 20(36판).
잣대: 세 기간 모두 연 + · 골 −15% 안 = 합격. 신호마다 합격 판 수 · 맨 위 3판."""
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

k = I.K200
n = len(k)
chg = np.zeros(n)
chg[1:] = k[1:] / k[:-1] - 1


def rsi2(a):
    up, dn = np.zeros(len(a)), np.zeros(len(a))
    d = np.diff(a, prepend=a[0])
    up[d > 0], dn[d < 0] = d[d > 0], -d[d < 0]
    out = np.full(len(a), np.nan)
    au, ad = up[1:3].mean(), dn[1:3].mean()
    for i in range(3, len(a)):
        au = (au * 1 + up[i]) / 2
        ad = (ad * 1 + dn[i]) / 2
        out[i] = 100 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


R2 = rsi2(k)
downs = np.zeros(n, int)
for i in range(1, n):
    downs[i] = downs[i - 1] + 1 if chg[i] < 0 else 0
r5 = np.nan_to_num(I.ret(k, 5), nan=0)
r5y = np.concatenate([[0], r5[:-1]])
m200 = I.ma(k, 200)
wk = [datetime.strptime(d, "%Y%m%d").isocalendar()[:2] for d in I.DAYS]
week_end = np.array([i == n - 1 or wk[i + 1] != wk[i] for i in range(n)])
weekly = np.zeros(n, bool)
last_end = None
for i in range(n):
    if week_end[i]:
        if last_end is not None and k[i] / k[last_end] - 1 <= -0.05:
            weekly[i] = True
        last_end = i
SIG = {
    "S0 5일 −5%(I2b)": r5 <= -0.05,
    "S1 RSI2 < 10": np.nan_to_num(R2, nan=50) < 10,
    "S2 RSI2 < 5": np.nan_to_num(R2, nan=50) < 5,
    "S3 3일 연속 하락": downs >= 3,
    "S4 4일 연속 하락": downs >= 4,
    "S5 주 −5%": weekly,
    "S6 5일 −5% 뒤 첫 반등": (r5y <= -0.05) & (chg > 0),
    "S7 RSI2 < 10 · 200일선 아래": (np.nan_to_num(R2, nan=50) < 10) & (k < np.nan_to_num(m200, nan=0)),
}
print("== I 8회차(I8): 과매도 새 신호 견줌 · KODEX 200 · 비용 0.2% ==", flush=True)
for name, sig in SIG.items():
    rows = []
    for take in (0.02, 0.03, 0.04):
        for stop in (-0.03, -0.04, -0.05):
            for cool in (0, 20):
                tr, d = I.sim(sig, "069500", stop, take, 20, cool=cool)
                js = [I.judge(tr, d, lo, hi) for _, lo, hi in I.PERIODS]
                ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                worst = min(j["cagr"] for j in js)
                text, _ = I.line(f"익절 {take*100:.0f} 손절 {stop*100:.0f} 쉬기 {cool}", tr, d)
                rows.append((ok, worst, text))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    print(f"\n[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(r[0] for r in rows)}/36", flush=True)
    for ok, w, t in rows[:3]:
        print(f"  {'합격' if ok else '    '} (가장 나쁜 {w:+5.1f}) {t.strip()}", flush=True)
print("끝", flush=True)
