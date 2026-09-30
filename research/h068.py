"""1시간봉 68회차 — 66회차에서 두 반 모두 같은 쪽(0.03 넘게)으로 기운 RNA 재료로 거르기: 1시간봉 이격속도(60봉선 3봉 · 20봉선 5봉 · 120봉선 3봉)가 큰 쪽
(사기 직전 몇 시간 동안 EMA 위로 빠르게 벌어진 것)을 막음. 문턱은 달마다 그 달 앞 신호들로만(66회차와 같음)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = open("research/h066.py", encoding="utf-8").read()
exec(src.split('print("\\n  ② RNA 거르기')[0].replace("66회차 (EMA · RNA로 좋은 매매 · 나쁜 매매 가르기)", "68회차 (RNA 이격속도 거르기)").replace("for r in tab[:30]:", "for r in tab[:0]:"))
run("지금", set())
for nm in ("1시간 A 이격속도60_3", "1시간 A 이격속도20_5", "1시간 A 이격속도120_3"):
    for q in (0.1, 0.2, 0.3):
        run(f"{nm} 큰 쪽 {int(q * 100)}% 막음", monthly_block(nm, "큰", q))
print("끝", flush=True)
