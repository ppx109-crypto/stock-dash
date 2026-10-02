"""I 12회차 — 업종 ETF 급락 되돌림 묶음: I2b(지수 하나 · 1년 2 ~ 3건 · 돈의 92 ~ 97%가 놂)를 업종 ETF 여럿으로 넓혀 사는 횟수를 늘림.
후보: 069500 KODEX 200 · 229200 코스닥150 · 091160 반도체 · 091170 은행 · 091180 자동차 · 117680 철강 · 117700 건설 · 102970 증권
      · 139260 TIGER 200 IT · 266420 헬스케어(2017 ~) · 305720 2차전지(2018 ~).
규칙: 그날 종가에 5일 수익 ≤ 문턱인 것 가운데 가장 많이 빠진 것부터, 빈 칸(S칸 · 칸마다 1/S)에 삼. 익절 · 손절 · 20일 · 손절 뒤 그 종목 쉬기 20일.
켜는 때: 언제나 / 시장 폭 < 50(B · C). 비용 0.2%. 잣대: 세 기간 연 + · 골 −15 안."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

CODES = ["069500", "229200", "091160", "091170", "091180", "117680", "117700", "102970", "139260", "266420", "305720"]
D, n = I.DAYS, len(I.DAYS)
P = {}
for c in CODES:
    try:
        P[c] = I.px(c)
    except FileNotFoundError:
        print("자료 없음", c)
R5 = {c: I.ret(P[c], 5) for c in P}
PER = (("A", "20090916", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))
WEAK = None
if os.environ.get("I_WEAK"):
    WEAK = np.nan_to_num(I.breadth(), nan=100) < 50


def run(th, take, stop, slots, maxd=20, cool=20, cost=0.002):
    daily = np.zeros(n)
    hold = {}          # 코드 → (산 날, 산 값)
    rest = {}          # 코드 → 이 날까지 쉼
    trades = []
    for i in range(1, n):
        for c, (a, p0) in list(hold.items()):
            if not np.isnan(P[c][i]) and not np.isnan(P[c][i - 1]):
                daily[i] += (P[c][i] / P[c][i - 1] - 1) / slots
            if np.isnan(P[c][i]):
                continue
            r = P[c][i] / p0 - 1
            if r <= stop or r >= take or i - a >= maxd:
                daily[i] -= cost / 2 / slots
                trades.append((a, i, r - cost))
                del hold[c]
                if r <= stop:
                    rest[c] = i + cool
        if WEAK is not None and not WEAK[i]:
            continue
        free = slots - len(hold)
        if free <= 0:
            continue
        cand = sorted((R5[c][i], c) for c in P if c not in hold and rest.get(c, -1) < i
                      and not np.isnan(R5[c][i]) and R5[c][i] <= th)
        for _, c in cand[:free]:
            hold[c] = (i, P[c][i])
            daily[i] -= cost / 2 / slots
    return daily, trades


print(f"== I 12회차: 업종 ETF 급락 되돌림 묶음 · 켜는 때 {'시장 폭 < 50' if WEAK is not None else '언제나'} ==", flush=True)
rows = []
for th in (-0.05, -0.07, -0.09):
    for take, stop in ((0.03, -0.03), (0.04, -0.04), (0.05, -0.05), (0.06, -0.04), (0.08, -0.06)):
        for slots in (1, 2, 3, 4):
            d, tr = run(th, take, stop, slots)
            ss = [I.stats(d, lo, hi) for _, lo, hi in PER]
            if WEAK is not None:
                ss = ss[1:]
            ok = all(s[0] > 0 and s[1] > -15 for s in ss)
            per_year = len(tr) / (n / 250)
            win = np.mean([t[2] > 0 for t in tr]) * 100 if tr else 0
            rows.append((ok, min(s[0] for s in ss), f"5일 {th*100:.0f}% · 익절 {take*100:.0f} 손절 {stop*100:.0f} · {slots}칸 | 해마다 {per_year:4.1f}건 이김 {win:4.1f} | "
                         + " | ".join(f"연 {s[0]:+5.1f} 골 {s[1]:6.1f}" for s in ss)))
rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
print(f"합격 {sum(r[0] for r in rows)}/{len(rows)}", flush=True)
for ok, w, t in rows[:12]:
    print(f"  {'합격' if ok else '    '} (가장 나쁜 {w:+5.1f}) {t}", flush=True)
print("끝", flush=True)
