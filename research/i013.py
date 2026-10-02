"""I 13회차 — 약세장 돌리기(i011)를 1일봉 규칙(새 82)의 쉬는 돈으로 함께 굴림(B · C · C를 2021 ~ 2025 · 2026으로도 나눔).
1일봉 손익 · 비운 몫: i005와 같음(x008_d1.json). 돌리기 몫 = 그날 비운 몫 × 돌리기 수익(켜는 때 = 시장 폭 < 50 등).
환경변수: I_CANDS(쉼표 · 기본 나스닥 · 달러 · 금 · 채권) · I_L(기본 60) · I_TOP(기본 1) · I_GATE(weak · always · ma200)
  · I_W(비운 돈 가운데 넣는 몫 · 기본 1) · I_MA(상품이 그 이평선 위일 때만 · 기본 0 = 안 봄)
  · I_COST(기본 0.002) · I_REB(week · mon · day) · I_GUARD(trend · crash · nas20 — 나스닥 빼는 때)
  · I_DOLLAR=2(원 · 달러 20일 +2% · 코스피 < 20일선인 날은 돌리기 대신 달러만)
  · I_DIP=1(시장 폭 < 50 급락 되돌림 I2b가 켜진 날은 그 돈을 급락 되돌림에 쓰고 돌리기는 쉼)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i011 as R  # noqa: E402  (불러올 때는 i011 표를 찍지 않음)
import itools as I

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
D, n = I.DAYS, len(I.DAYS)
used, d1 = np.zeros(n), np.zeros(n)
LEDGER = os.environ.get("I_LEDGER", "x008_d1.json")   # 1시간봉: x008_h1y3.json(야후 3년)
for code, buy, sell, pnl, slots in json.load(open(SP + LEDGER)):
    a, b = np.searchsorted(D, buy), np.searchsorted(D, sell)
    used[a:b] += slots / 10
    if b < n:
        d1[b] += pnl * slots / 10 / 100
free = np.clip(1 - used, 0, 1)
cands = os.environ.get("I_CANDS", "133690,138230,132030,148070").split(",")
L, TOP = int(os.environ.get("I_L", "60")), int(os.environ.get("I_TOP", "1"))
gate_weak = R.G.get("시장 폭<50")
prev_used = np.concatenate([[0.0], used[:-1]])
gate = {"weak": R.G.get("시장 폭<50"), "always": R.G["언제나"], "ma200": R.G["코스피<200일선"],
        # 1일봉이 거의 쉴 때만(어제까지 쓴 몫 < 20 · 50%) — 반쯤 쓴 달에 엔진이 깎아 먹음(I17)
        "idle20": prev_used < 0.2, "idle50": prev_used < 0.5}[os.environ.get("I_GATE", "weak")]
W, MA_N = float(os.environ.get("I_W", "1")), int(os.environ.get("I_MA", "0"))
COST, REB, GUARD = float(os.environ.get("I_COST", "0.002")), os.environ.get("I_REB", "week"), os.environ.get("I_GUARD", "")
kk = I.K200
m20k, m60k = I.ma(kk, 20), I.ma(kk, 60)
nasp = R.P["133690"]
GUARDS = {
    "": None,
    # 코스피 하락 추세(20일선 < 60일선 · 코스피 < 20일선)면 나스닥 빼고 달러 · 금 · 채권에서만 고름
    "trend": {"133690": np.nan_to_num((kk < m20k) & (m20k < m60k), nan=0) > 0},
    # 코스피 5일 −5% 이면서 나스닥도 20일선 아래면 나스닥 뺌(함께 빠지는 때)
    "crash": {"133690": (np.nan_to_num(I.ret(kk, 5), nan=0) <= -0.05) & (np.nan_to_num(nasp < I.ma(np.nan_to_num(nasp, nan=0), 20), nan=0) > 0)},
    # 나스닥이 20일선 아래면 뺌
    "nas20": {"133690": np.nan_to_num(nasp < I.ma(np.nan_to_num(nasp, nan=0), 20), nan=0) > 0},
}
rot = R.run(gate, R.momentum(L, TOP, cands, MA_N, GUARDS[GUARD]), cost=COST, reb=REB) * W
if os.environ.get("I_DOLLAR"):
    # 하락 추세(원 · 달러 20일 +I_DOLLAR% · 코스피 < 20일선)인 날은 돌리기 대신 달러(138230)만 — 그날 종가 판단 → 다음 날 수익
    dol = R.P["138230"]
    d20 = np.nan_to_num(dol / np.concatenate([np.full(20, np.nan), dol[:-20]]) - 1, nan=0)
    cond = (d20 > float(os.environ["I_DOLLAR"]) / 100) & (np.nan_to_num(kk < m20k, nan=0) > 0)
    cy = np.concatenate([[False], (cond & gate)[:-1]])     # 켜는 때(gate)가 꺼진 날은 달러도 안 듦
    flip = np.concatenate([[False], cy[1:] != cy[:-1]])
    rot = np.where(cy, R.R["138230"] * W, rot) - flip * COST / 2 * W
prev_free = np.concatenate([[1.0], free[:-1]])
mix = d1 + rot * prev_free     # 어제 비워 둔 몫으로 오늘 수익
if os.environ.get("I_DIP"):
    # 급락 되돌림(I2b · 시장 폭 < 50일 때만)이 켜진 날은 그 돈을 급락 되돌림에 쓰고 돌리기는 쉼(돈이 겹치지 않게)
    sig = (np.nan_to_num(I.ret(I.K200, 5), nan=0) <= -0.05) & gate_weak
    tr, dd = I.sim(sig, "069500", -0.03, 0.03, 20, cool=20, cost=COST)
    on = np.zeros(n, bool)
    dip = np.zeros(n)
    for a, b, _ in tr:
        on[a + 1:b + 1] = True
        dip[a:b + 1] += dd[a:b + 1] * free[a]
    rot_on = np.where(on, 0.0, rot)
    mix = d1 + rot_on * prev_free + dip
    rot = rot_on
print(f"== I 13회차: 1일봉 + 약세장 돌리기({','.join(R.NAME.get(c, c) for c in cands)} · {L}일 · 위 {TOP} · {os.environ.get('I_GATE', 'weak')} · 몫 {W} · 이평 {MA_N}{' · 급락 되돌림 먼저' if os.environ.get('I_DIP') else ''} · 비용 {COST} · 고르는 날 {REB} · 거르기 {GUARD or '없음'} · 하락 추세 달러 {os.environ.get('I_DOLLAR', '안 씀')}) ==", flush=True)
for name, lo, hi in (("B", "20170101", "20210101"), ("C", "20210101", "20991231"), ("C1 21~25", "20210101", "20260101"), ("C2 2026", "20260101", "20991231")):
    a, m, c = I.stats(d1, lo, hi), I.stats(rot, lo, hi), I.stats(mix, lo, hi)
    print(f"  {name:9s} 1일봉만 연 {a[0]:+6.1f} 골 {a[1]:6.1f} | 돌리기만(계좌 전부) 연 {m[0]:+5.1f} 골 {m[1]:6.1f} | 함께 연 {c[0]:+6.1f} 골 {c[1]:6.1f}", flush=True)
print("끝", flush=True)
