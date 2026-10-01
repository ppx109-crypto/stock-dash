"""15분봉 50회차(세 갈래 공통 G6 · 15분봉) — 정배열 쪽 파는 숫자: 손절 −10% · 이익 지키기(+8% → +1%). 기준 = 22회차 후보 · 161종목 · 씨앗 16.
Q_PART=1: 손절 −8 · −12% / Q_PART=2: 이익 지키기 (6 → 1) · (10 → 2) · (8 → 3)."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
exec("def make_exit" + open("/home/user/stock-dash/research/q003.py", encoding="utf-8").read().split("def make_exit", 1)[1].split("def run(tag")[0])

part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 50회차({part}): 정배열 쪽 파는 숫자 ({len(data)}종목) ==", flush=True)
go("기준(손절 −10 · 지키기 8 → 1)", ex=make_exit())
if part == "1":
    for s in (8, 12):
        go(f"손절 −{s}%", ex=make_exit(astop=s))
else:
    for kp in ((6, 1), (10, 2), (8, 3)):
        go(f"이익 지키기 {kp[0]} → {kp[1]}", ex=make_exit(keep=kp))
print("끝", flush=True)
