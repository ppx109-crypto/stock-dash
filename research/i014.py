"""I 14회차 — '빈칸 엔진'(사용자 2026-10-02 "1H · 1일봉이 쉬는 빈 공간에 하락장에서도 · 횡보 · 상승에서도 버는 것").
1일봉 · 1시간봉은 시장 폭 50 이상일 때만 삼 → 빈 공간 = 시장 폭 < 50인 날(A 기간은 시장 폭이 없어 코스피 < 200일선으로 대신).
빈 공간에서 날마다(그날 종가 판단 → 다음 날 수익) 하나를 고름 — 앞에 있는 것이 먼저:
  ① 급락 되돌림: KODEX 200 5일 −5% → 익절 3 · 손절 3 · 20일 · 손절 뒤 20일 쉬기(I2b)
  ② 하락 추세 → KODEX 인버스(114800 · 1배): 추세 판(T) 아래
  ③ 그 밖(옆걸음 · 오름) → 돌리기: 나스닥 · 달러 · 금 · 국채10년 중 20일 수익 위 2개(주마다 · 다 − 면 현금)
하락 추세 판:
  T0 인버스 안 씀(①+③만)
  T1 코스피 < 20일선 · 20일선 < 60일선
  T2 코스피 < 60일선 · 20일선이 5일 전보다 낮음
  T3 코스피 20일 수익 < −3% · 코스피 < 20일선
  T4 T1 · 인버스가 손절(들어간 뒤 −3%)이면 그 추세 끝날 때까지 다시 안 들어감
  T5 T1 · 코스피 5일 수익 < 0(아직 빠지는 중)
비용: 바꿀 때 0.2%(사고팔기 합). 기간: A(2011 ~ 2016 · 대신 신호) · B · C1(2021 ~ 2025) · C2(2026). 계좌 전부를 빈 날에만 넣었을 때."""
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
k = I.K200
m20, m60, m200 = I.ma(k, 20), I.ma(k, 60), I.ma(k, 200)
r5, r20 = np.nan_to_num(I.ret(k, 5), nan=0), np.nan_to_num(I.ret(k, 20), nan=0)
br = I.breadth()
gate = np.where(np.isnan(br), np.nan_to_num(k < m200, nan=0) > 0, br < 50)
CANDS = ["133690", "138230", "132030", "148070"]
P = {c: I.px(c) for c in CANDS + ["114800", "069500"]}
R = {c: np.nan_to_num(np.concatenate([[0], P[c][1:] / P[c][:-1] - 1]), nan=0) for c in P}
wk = [datetime.strptime(d, "%Y%m%d").isocalendar()[:2] for d in D]
week_end = np.array([i == n - 1 or wk[i + 1] != wk[i] for i in range(n)])
nz = lambda a: np.nan_to_num(a, nan=0) > 0
m20_5 = np.concatenate([np.full(5, np.nan), m20[:-5]])
T = {
    "T0 인버스 안 씀": np.zeros(n, bool),
    "T1 20<60 · 코스피<20": nz((k < m20) & (m20 < m60)),
    "T2 코스피<60 · 20일선 내림": nz((k < m60) & (m20 < m20_5)),
    "T3 20일 −3% · 코스피<20": (r20 < -0.03) & nz(k < m20),
    "T4 T1 · 손절 뒤 쉼": nz((k < m20) & (m20 < m60)),
    "T5 T1 · 5일 −": nz((k < m20) & (m20 < m60)) & (r5 < 0),
}
# 밖에서 오는 하락 신호(I14b): 원 · 달러 급등 · 미국 나스닥 약세 · 외국인 매도(2017 ~)
dollar, nas = P["138230"], P["133690"]
d20 = np.nan_to_num(dollar / np.concatenate([np.full(20, np.nan), dollar[:-20]]) - 1, nan=0)
nas50 = I.ma(np.nan_to_num(nas, nan=0), 50)
fr = I.series("market-data/investor_KSP.json", "외국인")
fr20 = np.array([np.nansum(fr[max(0, i - 19):i + 1]) if np.isfinite(fr[max(0, i - 19):i + 1]).sum() >= 15 else np.nan for i in range(n)])
below20 = nz(k < m20)
T.update({
    "T6 달러 20일 +2% · 코스피<20": (d20 > 0.02) & below20,
    "T7 나스닥<50일선 · 코스피<20": nz(nas < nas50) & below20,
    "T8 외국인 20일 순매도 · 코스피<20": (np.nan_to_num(fr20, nan=0) < 0) & below20,
    "T9 달러 +2% · 나스닥<50 · 코스피<20": (d20 > 0.02) & nz(nas < nas50) & below20,
})
# ① 급락 되돌림 들고 있는 날
dip_on = np.zeros(n, bool)
tr, _ = I.sim(gate & (r5 <= -0.05), "069500", -0.03, 0.03, 20, cool=20)
for a, b, _ in tr:
    dip_on[a:b] = True          # a일 종가에 사서 b일 종가에 팖 → a ~ b−1일 종가에 들고 있음


def rot_pick(i):
    sc = []
    for c in CANDS:
        if i < 20 or np.isnan(P[c][i]) or np.isnan(P[c][i - 20]):
            continue
        r = P[c][i] / P[c][i - 20] - 1
        if r > 0:
            sc.append((r, c))
    sc.sort(reverse=True)
    return {c: 0.5 for _, c in sc[:2]}


def engine(tname, use_rot=True, cost=0.002):
    trend = T[tname]
    daily, w, chosen = np.zeros(n), {}, {}
    inv_in, banned, mode = None, False, np.zeros(n, int)
    for i in range(1, n):
        daily[i] = sum(x * R[c][i] for c, x in w.items())
        if week_end[i] or not chosen:
            chosen = rot_pick(i)
        if not trend[i]:
            banned = False
        new = {}
        if gate[i]:
            if dip_on[i]:
                new, mode[i] = {"069500": 1.0}, 1
            elif trend[i] and not banned:
                new, mode[i] = {"114800": 1.0}, 2
                if inv_in is None:
                    inv_in = P["114800"][i]
                elif tname.startswith("T4") and P["114800"][i] / inv_in - 1 <= -0.03:
                    new, banned, mode[i] = {}, True, 0
            elif use_rot:
                new, mode[i] = chosen, 3
        if "114800" not in new:
            inv_in = None
        daily[i] -= sum(abs(new.get(c, 0) - w.get(c, 0)) for c in set(new) | set(w)) * cost / 2
        w = new
    return daily, mode


PER = (("A 11~16", "20110101", "20170101"), ("B 17~20", "20170101", "20210101"), ("C1 21~25", "20210101", "20260101"), ("C2 2026", "20260101", "20991231"))
if __name__ == "__main__":
    on = " · ".join(f"{nm} {gate[[i for i, d in enumerate(D) if lo <= d < hi]].mean() * 100:.0f}%" for nm, lo, hi in PER)
    print(f"== I 14회차: 빈칸 엔진(빈 날에만 · 계좌 전부) · 빈 날 몫: {on} ==", flush=True)
    import os
    names = [t for t in T if t >= os.environ.get("I_FROM", "")]
    for tname in names:
        for use_rot in (True, False):
            d, mode = engine(tname, use_rot)
            parts = []
            for nm, lo, hi in PER:
                s = I.stats(d, lo, hi)
                idx = [i for i, x in enumerate(D) if lo <= x < hi]
                inv_days = (mode[idx] == 2).mean() * 100
                parts.append(f"| {nm} 연 {s[0]:+5.1f} 골 {s[1]:6.1f} 인버스 {inv_days:3.0f}%")
            print(f"  {tname + (' + 돌리기' if use_rot else ' (돌리기 없음)'):28s} " + " ".join(parts), flush=True)
    print("끝", flush=True)
