"""15분봉 15회차 — 14회차: 뒤 반 큰 하락(2026-05-29 → 07-20, −29%)은 10:45 봉 뒤(11:00) 늦게 산 매매가 하락장에서 크게 진 것.
새 후보(10:45 + 오늘 +2% 위면 안 삼)에 '장중 시장 흐름(161종목 오늘 수익 평균, 그 봉까지)이 x 아래면 10:45 사기 쉼'을 더함.
x = 0 · −0.3 · −0.5 · −1%. 정배열 신호로 사는 것은 그대로. 씨앗 16 · 두 반 · 161종목. Q_PART=1/2로 나눠 돌림.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])

part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 15회차({part}): 장이 빠지는 날 10:45 사기 쉼 ({len(data)}종목) ==", flush=True)
cuts = (0.0, -0.003) if part == "1" else (-0.005, -0.01)
for x in cuts:
    run3(f"+2% + 시장 {x * 100:g}% 아래 쉼", cut_at("1045", lambda c, k, x=x: nan0(DR[c])[k] > 0.02 or nan0(MKT[c])[k] < x))
if part == "2":
    run3("+2% + 시장 −0.5% 아래 쉼 · 비용 0.5%",
         cut_at("1045", lambda c, k: nan0(DR[c])[k] > 0.02 or nan0(MKT[c])[k] < -0.005), cost=0.5)
print("끝", flush=True)
