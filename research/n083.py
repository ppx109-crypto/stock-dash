"""일봉 새 83회차 — 실전 비용 버팀(사용자 2026-10-01: "못 해보거나 가치있는 일봉 연구 → 모의투자로 일봉 · 1시간봉 함께").
연구 계좌의 왕복 비용은 일봉 0.25% · 1시간봉 0.30%. 실제로는 수수료 · 세금 · 미끄러짐(생각한 값과 체결 값 차이)이 더 들 수 있음.
비용을 0.5 · 0.8 · 1.0%로 올려 일봉 최고 규칙(82회차)이 얼마나 버티는지 봄(1시간봉은 research/h099.py).
실행: NRL_CACHE=... python3 research/n083.py
"""
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
print("== 일봉 새 83회차: 왕복 비용을 올리면 (씨앗 8) ==", flush=True)
for cost in (0.25, 0.5, 0.8, 1.0):
    got = T.once(f"비용 {cost}%", cost=cost)
    if cost == 0.25:
        T.once("(참고) 비용 0%", cost=0.0)
print("끝", flush=True)
