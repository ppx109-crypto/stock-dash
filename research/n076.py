"""일봉 새 76회차 — 75회차 후보(정배열 신호 날 거래량비 2.2배↑면 4칸)의 골을 −15 안에 두는 짝 찾기.

A 계좌 골이 X% 넘게 파이면 칸을 줄임(lab.run brake — 끝난 매매만으로 센 계좌라 뒷날을 안 봄)
B 시장 폭이 센 날(60 · 70%↑)에만 크게
C 거래량 4칸 대신 다른 칸을 줄임(추세 규칙 3칸 · 보통 정배열 1칸)
D 3칸(75회차에 일부 봄)
실행: NRL_CACHE=... python3 research/n076.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule

V = 2.2


def size_of(big=4, trend=4, plain=2, gate=None):
    def go(r):
        if rule.holds(r):
            return trend
        if nrl.steady(r) >= 3:
            return 4
        if (r.get("거래량비") or 0) >= V and (gate is None or gate(r)):
            return big
        return plain
    return go


print("== 일봉 새 76회차: 거래량 4칸의 골을 −15 안에 ==", flush=True)
base = T.once("지금 규칙(기준)")
cand = T.once("후보: 거래량 2.2배 4칸")
for deep, share in ((8, 0.6), (10, 0.6), (10, 0.5), (12, 0.5)):
    T.once(f"기준 + 골 {deep}%↓면 칸 {int(share * 100)}%만", brake=(deep, share))
    T.once(f"후보 + 골 {deep}%↓면 칸 {int(share * 100)}%만", brake=(deep, share), size=size_of())
for lv in (60, 70):
    got = T.once(f"후보: 시장 폭 {lv}%↑ 날만 4칸", size=size_of(gate=lambda r, lv=lv: nrl.BR.get(r["date"], 0) >= lv))
    print("      해마다", T.years(got), flush=True)
T.once("후보 + 추세 규칙 3칸", size=size_of(trend=3))
T.once("후보 + 보통 정배열 1칸", size=size_of(plain=1))
T.once("거래량 3칸", size=size_of(big=3))
T.once("거래량 3칸 + 골 10%↓면 칸 60%", size=size_of(big=3), brake=(10, 0.6))
print("끝", flush=True)
