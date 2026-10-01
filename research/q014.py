"""15분봉 13회차 — 12회차 후보 둘의 숫자 고원: 추세 손절(−3 · −3.5 · −4 · −4.5%), 정배열 손절(−6 · −7 · −8 · −9%), 그리고 둘을 합친 판.
새 후보(10:45 봉 뒤 + 오늘 +2% 위면 안 삼 · 161종목). Q_PART=1 추세 손절 · Q_PART=2 정배열 손절 + 합침. 씨앗 16 · 두 반.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q013.py", encoding="utf-8").read().split('part = os.environ')[0])

part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 13회차({part}): 손절 숫자 고원 ({len(data)}종목) ==", flush=True)
if part == "1":
    for s in (3, 3.5, 4.5):
        go(f"추세 손절 −{s:g}%", make_exit(stop=s))
    go("추세 손절 −4% · 비용 0.5%", make_exit(stop=4), cost=0.5)
else:
    for a in (6, 8, 9):
        go(f"정배열 손절 −{a}%", make_exit(astop=a))
    go("추세 −4% + 정배열 −7%", make_exit(stop=4, astop=7))
    go("추세 −4% + 정배열 −8%", make_exit(stop=4, astop=8))
    go("추세 −4% + 정배열 −7% · 비용 0.5%", make_exit(stop=4, astop=7), cost=0.5)
print("끝", flush=True)
