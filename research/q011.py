"""15분봉 10회차 — 9회차에서 시각 고원이 확인된 'A + 그 봉 뒤 사기 + 오늘 +x% 위면 안 삼'을 11:00 봉에서 문턱 고원(1.5 · 2 · 2.5%)과
비용 0.5%로 다시 봄(10:45와 두 칸 짜임). 씨앗 16 · 두 반.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])

part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 10회차({part}): 11:00 봉 뒤 사기 문턱 · 비용 ({len(data)}종목) ==", flush=True)
if part == "1":
    for th in (0.015, 0.025):
        run3(f"1100 봉 뒤 + 오늘 +{th * 100:g}% 위면 안 삼", cut_at("1100", lambda c, k, th=th: nan0(DR[c])[k] > th))
else:
    run3("1100 봉 뒤 + 2% · 비용 0.5%", cut_at("1100", lambda c, k: nan0(DR[c])[k] > 0.02), cost=0.5)
    run3("1100 봉 뒤(거르기 없음)", entry(noon="1100"))
print("끝", flush=True)
