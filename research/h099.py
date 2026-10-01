"""1시간봉 99회차 — 실전 비용 버팀(일봉 새 83회차와 짝). 최고 규칙(94회차)의 왕복 비용 0.30% → 0.5 · 0.8 · 1.0%. 씨앗 16.
1시간봉은 회전이 일봉보다 커서(한 해 약 27배) 비용이 오르면 더 크게 깎일 수 있음 — 얼마나인지 숫자로 봄.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import hlab as H
exec(open("research/h094.py", encoding="utf-8").read().split('print("== 1시간봉 94회차')[0])
RK = rk_of(tiers(20, 5, 3))
print("== 1시간봉 99회차: 왕복 비용을 올리면 (씨앗 16) ==", flush=True)
for cost in (0.0, 0.30, 0.5, 0.8, 1.0):
    res = H.simulate(data, e_align_or_noon, EX, size, rank=RK, stale_of=stale90, seeds=16, cost=cost)
    print(f"  비용 {cost}%  " + H.line(res), flush=True)
print("끝", flush=True)
