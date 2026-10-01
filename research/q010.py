"""15분봉 9회차 — 두 후보가 사는 시각을 15분 옮겨도 버티는지(시각 고원).
Q_SPAN=A: '그 봉 뒤 사기 + 오늘 +2% 위면 안 삼'을 10:30 · 10:45 · 11:00 · 11:15 봉에서.
Q_SPAN=A4: '정오 사기 그대로'를 11:15 · 11:30 · 11:45 · 12:15 봉에서. 씨앗 16 · 두 반.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])

span = os.environ.get("Q_SPAN", "A")
print(f"== 15분봉 9회차: EMA {span} · 사는 시각 고원 ({len(data)}종목) ==", flush=True)
if span == "A":
    for nn in ("1030", "1045", "1100", "1115"):
        run3(f"{nn} 봉 뒤 + 오늘 +2% 위면 안 삼", cut_at(nn, lambda c, k: nan0(DR[c])[k] > 0.02))
else:
    for nn in ("1115", "1130", "1145", "1215"):
        run3(f"{nn} 봉 뒤 사기(거르기 없음)", entry(noon=nn))
print("끝", flush=True)
