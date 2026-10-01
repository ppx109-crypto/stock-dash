"""1시간봉 117 · 118회차(세 갈래 공통 G7 · G8 · 1시간봉) — 기준 = 94회차 · 씨앗 16 · Q_SRC=yahoo · kis.
Q_PART=1(G7 · 117회차): 1일봉의 '닮은 종목 거르기'(들고 있는 것과 60일 일봉 수익률 상관 0.6 넘으면 안 삼 · research/kinpatch.py)를 1시간봉에 — 0.6 · 0.5 · 0.7.
Q_PART=3(G7b): 날짜 맞춘 닮음(두 종목 모두 사려는 날 창) 0.6 · 0.5 · 0.7 / Q_PART=2(G8 · 118회차): 칸 수 10 → 9 · 11 · 12."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/h116.py", encoding="utf-8").read().split("\nVOL, RUN = {}, {}")[0])
import kinpatch as KP

part = os.environ.get("Q_PART", "1")
rk = RK(SG)
print(f"== 1시간봉 {'118' if part == '2' else '117'}회차({ {'1': 'G7 닮은 종목 거르기', '2': 'G8 칸 수', '3': 'G7b 날짜 맞춘 닮음'}[part]} · {src} · {len(data)}종목) ==", flush=True)


def go(tag, slots=10):
    KP.SKIPPED[0] = 0
    res = SIM(data, lambda c, b: SG[c], EXF, size, rank=rk, stale_of=stale90, seeds=16, slots=slots)
    print(f"  {tag:30s} 거른 수 {KP.SKIPPED[0]:5d} " + H.line(res), flush=True)


go("기준(94회차 · 거르기 없음 · 10칸)")
if part == "1":
    for e in (0.6, 0.5, 0.7):
        KP.set_edge(e)
        go(f"닮음 {e} 넘으면 안 삼")
elif part == "3":
    for e in (0.6, 0.5, 0.7):
        KP.set_edge(e, align=True)
        go(f"날짜 맞춘 닮음 {e} 넘으면 안 삼")
else:
    for s in (9, 11, 12):
        go(f"{s}칸", slots=s)
print("끝", flush=True)
