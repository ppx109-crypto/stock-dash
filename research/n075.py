"""일봉 새 75회차 — 74회차 후보(정배열 신호 날 거래량비 2배↑면 4칸)의 고원 · 크기 · 해마다 · 짜임 · 골.

거래량비 = 그날 거래량 ÷ 지난 20일 평균(표 재료 · guard.py 검사 대상, 그날 종가에 사므로 앎).
실행: NRL_CACHE=... python3 research/n075.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule


def size_vol(th, big=4):
    return lambda r: 4 if rule.holds(r) else (4 if nrl.steady(r) >= 3 else (big if (r.get("거래량비") or 0) >= th else 2))


print("== 일봉 새 75회차: 거래량 터진 정배열 크게 — 고원 · 크기 · 해마다 ==", flush=True)
base = T.once("지금 규칙(기준)")
print("      해마다", T.years(base), flush=True)
for th in (1.8, 2.0, 2.2, 2.5, 3.0):
    got = T.once(f"거래량비 {th}배↑ 4칸", size=size_vol(th))
    if th == 2.0:
        print("      해마다", T.years(got), flush=True)
        T.diff_check(base, got)
for th in (2.0, 2.5):
    T.once(f"거래량비 {th}배↑ 3칸", size=size_vol(th, 3))
# 추세 갈래에도(이미 4칸) 효과 없음 · 정배열이 3일 연속이면 이미 4칸 → 겹치는 몫
rows = [r for rs in T.BY_DAY.values() for r in rs if not rule.holds(r)]
hit = [r for r in rows if (r.get("거래량비") or 0) >= 2.0]
print(f"  정배열 후보 {len(rows)} 가운데 거래량비 2배↑ {len(hit)} · 그 가운데 이미 3일 연속 {sum(1 for r in hit if nrl.steady(r) >= 3)}", flush=True)
for slots, tag in ((8, "칸 8"), (12, "칸 12")):
    T.once(f"짜임 {tag}: 기준", slots=slots)
    T.once(f"짜임 {tag}: 거래량 2배 4칸", slots=slots, size=size_vol(2.0))
for pd in (1, 2):
    T.once(f"짜임 하루 {pd}종목: 기준", per_day=pd)
    T.once(f"짜임 하루 {pd}종목: 거래량 2배 4칸", per_day=pd, size=size_vol(2.0))
print("끝", flush=True)
