"""15분봉 11회차 — 161종목이 다 찬 뒤 핵심 판 다시: 0회차 · 10:45 봉 뒤 · 10:45 / 11:00 봉 뒤 + 오늘 +2% 위면 안 삼 · 비용 0.5%. 씨앗 16 · 두 반."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])

print(f"== 15분봉 11회차: 161종목 핵심 판 ({len(data)}종목) ==", flush=True)
run3("0회차(정오 사기)", entry())
run3("10:45 봉 뒤", entry(noon="1045"))
run3("10:45 봉 뒤 + 오늘 +2% 위면 안 삼", cut_at("1045", lambda c, k: nan0(DR[c])[k] > 0.02))
run3("11:00 봉 뒤 + 오늘 +2% 위면 안 삼", cut_at("1100", lambda c, k: nan0(DR[c])[k] > 0.02))
run3("11:00 + 2% · 비용 0.5%", cut_at("1100", lambda c, k: nan0(DR[c])[k] > 0.02), cost=0.5)
print("끝", flush=True)
