"""15분봉 23회차 — 최종 후보(22회차: 모든 사기에 '오늘 +2% 위 · 장중 시장 −1% 아래면 안 삼')의 잣대 마무리 점검:
비용 0.5 · 0.8%, 그리고 같은 자료 1시간봉 최고 규칙과 회전 · 보유 봉(시간) 견줌. 161종목 · 씨앗 16."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('part = os.environ')[0])

FIN = entry3(al_mkt=-0.01)
print(f"== 15분봉 23회차: 최종 후보 비용 · 회전 · 보유 ({len(data)}종목) ==", flush=True)
for cost in (0.3, 0.5, 0.8):
    run3(f"최종 후보 · 비용 {cost}%", FIN, cost=cost)
print("끝", flush=True)
