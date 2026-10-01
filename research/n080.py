"""일봉 새 80회차 — 79회차 후보(정배열 신호 날 거래량비 V배↑ · 정배열 D일 안이면 4칸)의 고원 · 해마다 · 짜임 · 골.

정배열일수 · 거래량비는 표 재료(guard.py · dguard 검사 대상). 바뀐 매매 손익을 직접 봄.
실행: NRL_CACHE=... python3 research/n080.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule


def size_vd(v=2.2, d=15, big=4):
    def go(r):
        if rule.holds(r):
            return 4
        if nrl.steady(r) >= 3:
            return 4
        if (r.get("거래량비") or 0) >= v and (r.get("정배열일수") or 999) <= d:
            return big
        return 2
    return go


print("== 일봉 새 80회차: 거래량 터진 새 정배열 4칸 — 고원 · 해마다 · 짜임 ==", flush=True)
base = T.once("지금 규칙(기준)")
print("      해마다", T.years(base), flush=True)
for v in (2.0, 2.2, 2.5):
    for d in (10, 15, 20, 30):
        got = T.once(f"거래량 {v}배 · 정배열 {d}일 안 4칸", size=size_vd(v, d))
        if (v, d) == (2.2, 15):
            print("      해마다", T.years(got), flush=True)
            T.diff_check(base, got)
T.once("거래량 2.2배 · 정배열 15일 안 3칸", size=size_vd(2.2, 15, 3))
for slots, tag in ((8, "칸 8"), (12, "칸 12")):
    T.once(f"짜임 {tag}: 기준", slots=slots)
    T.once(f"짜임 {tag}: 후보", slots=slots, size=size_vd())
for pd in (1, 2):
    T.once(f"짜임 하루 {pd}종목: 기준", per_day=pd)
    T.once(f"짜임 하루 {pd}종목: 후보", per_day=pd, size=size_vd())
print("끝", flush=True)
