"""15분봉 55회차(세 갈래 공통 G7 · G8 · 15분봉) — 기준 = 22회차 후보 · 161종목 · 씨앗 16 · 두 반(2025-09-17 ~ 03-31 · 04-01 ~ 08-31).
Q_PART=1(G7): 1일봉의 '닮은 종목 거르기'(research/kinpatch.py) 0.6 · 0.5 · 0.7 / Q_PART=3(G7b): 날짜 맞춘 닮음(두 종목 모두 사려는 날 창) 0.6 · 0.5 · 0.7 / Q_PART=2(G8): 칸 수 10 → 9 · 11 · 12."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
import kinpatch as KP

part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 55회차({part}): { {'1': '닮은 종목 거르기', '2': '칸 수', '3': '날짜 맞춘 닮음'}[part]} ({len(data)}종목) ==", flush=True)


def go2(tag, slots=10):
    KP.SKIPPED[0] = 0
    res = M.simulate(data, lambda c, b: SGF[c], exit_rule, size, rank=RKF, stale_of=stale90, seeds=16, slots=slots)
    print(f"  {tag:30s} 거른 수 {KP.SKIPPED[0]:5d} " + H.line(res), flush=True)


go2("기준(22회차 · 거르기 없음 · 10칸)")
if part == "1":
    for e in (0.6, 0.5, 0.7):
        KP.set_edge(e)
        go2(f"닮음 {e} 넘으면 안 삼")
elif part == "3":
    for e in (0.6, 0.5, 0.7):
        KP.set_edge(e, align=True)
        go2(f"날짜 맞춘 닮음 {e} 넘으면 안 삼")
else:
    for s in (9, 11, 12):
        go2(f"{s}칸", slots=s)
print("끝", flush=True)
