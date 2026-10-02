"""I 13회차 — 약세장 돌리기(i011)를 1일봉 규칙(새 82)의 쉬는 돈으로 함께 굴림(B · C · C를 2021 ~ 2025 · 2026으로도 나눔).
1일봉 손익 · 비운 몫: i005와 같음(x008_d1.json). 돌리기 몫 = 그날 비운 몫 × 돌리기 수익(켜는 때 = 시장 폭 < 50 등).
환경변수: I_CANDS(쉼표 · 기본 나스닥 · 달러 · 금 · 채권) · I_L(기본 60) · I_TOP(기본 1) · I_GATE(weak · always · ma200)."""
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
for code, buy, sell, pnl, slots in json.load(open(SP + "x008_d1.json")):
    a, b = np.searchsorted(D, buy), np.searchsorted(D, sell)
    used[a:b] += slots / 10
    if b < n:
        d1[b] += pnl * slots / 10 / 100
free = np.clip(1 - used, 0, 1)
cands = os.environ.get("I_CANDS", "133690,138230,132030,148070").split(",")
L, TOP = int(os.environ.get("I_L", "60")), int(os.environ.get("I_TOP", "1"))
gate = {"weak": R.G.get("시장 폭<50"), "always": R.G["언제나"], "ma200": R.G["코스피<200일선"]}[os.environ.get("I_GATE", "weak")]
rot = R.run(gate, R.momentum(L, TOP, cands))
mix = d1 + rot * np.concatenate([[1.0], free[:-1]])     # 어제 비워 둔 몫으로 오늘 수익
print(f"== I 13회차: 1일봉 + 약세장 돌리기({','.join(R.NAME.get(c, c) for c in cands)} · {L}일 · 위 {TOP} · {os.environ.get('I_GATE', 'weak')}) ==", flush=True)
for name, lo, hi in (("B", "20170101", "20210101"), ("C", "20210101", "20991231"), ("C1 21~25", "20210101", "20260101"), ("C2 2026", "20260101", "20991231")):
    a, m, c = I.stats(d1, lo, hi), I.stats(rot, lo, hi), I.stats(mix, lo, hi)
    print(f"  {name:9s} 1일봉만 연 {a[0]:+6.1f} 골 {a[1]:6.1f} | 돌리기만(계좌 전부) 연 {m[0]:+5.1f} 골 {m[1]:6.1f} | 함께 연 {c[0]:+6.1f} 골 {c[1]:6.1f}", flush=True)
print("끝", flush=True)
