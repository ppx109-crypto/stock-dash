"""일봉 새 79회차 — 75회차 후보(정배열 거래량비 2.2배↑ 4칸)를 더 날카로운 경우로만 좁혀 골을 줄이나.

좁히는 조건(그날 종가 · 전날까지 수급만): 그날 오른 날(종가 > 전날) · 250일 전고점 −3% 안 · 외국인 · 투신 3일 가운데 2일↑ 함께 순매수 · 정배열 15일 안.
실행: NRL_CACHE=... python3 research/n079.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule


def up_day(r):
    c = nrl.lanes[r["code"]]["closes"]
    return r["i"] > 0 and c[r["i"]] > c[r["i"] - 1]


def size_if(extra, big=4, v=2.2):
    def go(r):
        if rule.holds(r):
            return 4
        if nrl.steady(r) >= 3:
            return 4
        if (r.get("거래량비") or 0) >= v and extra(r):
            return big
        return 2
    return go


print("== 일봉 새 79회차: 거래량 4칸을 날카로운 경우로 좁히기 ==", flush=True)
base = T.once("지금 규칙(기준)")
T.once("후보: 거래량 2.2배 4칸(75회차)", size=size_if(lambda r: True))
for tag, extra in (("+ 오른 날", up_day),
                   ("+ 250일 전고점 −3% 안", lambda r: (r.get("250일 전고점 대비") or -99) >= -3),
                   ("+ 수급 3일 중 2일↑", lambda r: nrl.steady(r) >= 2),
                   ("+ 정배열 15일 안", lambda r: (r.get("정배열일수") or 999) <= 15),
                   ("+ 오른 날 · 전고점 −3% 안", lambda r: up_day(r) and (r.get("250일 전고점 대비") or -99) >= -3),
                   ("+ 내린 날(거꾸로)", lambda r: not up_day(r))):
    got = T.once("거래량 2.2배 4칸 " + tag, size=size_if(extra))
    T.diff_check(base, got)
print("끝", flush=True)
