"""일봉 새 65회차 — 다트 분기 실적(한 번도 안 쓴 자료)을 순서 · 크기 · 거르기로.

값: 신호 날 **앞**에 발표된(접수번호 날짜 < 신호 날) 가장 최근 분기 누적 실적의 영업이익 · 매출 전년 같은 때 대비, 흑자 전환, 발표 뒤 지난 날.
거르기는 막은 매매의 손익을 직접 봄(57회차 교훈). 순서는 같은 날 후보끼리만 셈.
실행: NRL_CACHE=... python3 research/n065.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import ntools as T
import nrl
import rule

print("== 일봉 새 65회차: 다트 분기 실적 ==", flush=True)
print("값 있는 몫: 영업이익 전년 대비", T.cover(T.op_yoy), "% · 매출", T.cover(T.sales_yoy), "%", flush=True)
rows = [r for rs in T.BY_DAY.values() for r in rs]
vals = sorted(v for v in (T.op_yoy(r) for r in rows) if v is not None)
if vals:
    print("영업이익 전년 대비 나눔(10 · 25 · 50 · 75 · 90%):",
          [round(vals[int(len(vals) * q)], 2) for q in (0.1, 0.25, 0.5, 0.75, 0.9)], flush=True)
print("흑자 전환 후보 신호", sum(1 for r in rows if T.op_turn(r)), "/", len(rows), flush=True)

base = T.once("지금 규칙(기준)")
OP = (T.op_yoy, False)
SA = (T.sales_yoy, False)
FLOW, RET = (T.flow_strength, True), (T.ret, False)
got = T.once("순서: 영업이익 증가 큰 것 먼저", rank=T.rank_by([OP]))
T.diff_check(base, got)
T.once("순서: 매출 증가 큰 것 먼저", rank=T.rank_by([SA]))
T.once("순서: 영업이익 + 매출", rank=T.rank_by([OP, SA]))
got = T.once("순서: 수급 약 + 수익 큼 + 영업이익", rank=T.rank_by([FLOW, RET, OP]))
T.diff_check(base, got)
for cut in (-0.5, -0.3, 0.0):
    hold = lambda r, cut=cut: nrl.BASE_HOLD(r) and not ((T.op_yoy(r) is not None) and T.op_yoy(r) < cut)
    got = T.once(f"거르기: 영업이익 전년 대비 {int(cut * 100)}% 아래면 안 삼", holds=hold)
    T.diff_check(base, got, "막은")
for up in (0.2, 0.5):
    size = lambda r, up=up: 4 if rule.holds(r) else (4 if (nrl.steady(r) >= 3 or ((T.op_yoy(r) or -9) >= up)) else 2)
    got = T.once(f"크기: 정배열도 영업이익 +{int(up * 100)}%↑면 4칸", size=size)
    T.diff_check(base, got)
size = lambda r: 4 if rule.holds(r) else (4 if (nrl.steady(r) >= 3 or T.op_turn(r)) else 2)
T.once("크기: 정배열도 흑자 전환이면 4칸", size=size)
for fresh in (30, 60):
    size = lambda r, fresh=fresh: 4 if rule.holds(r) else (4 if (nrl.steady(r) >= 3 or ((T.op_yoy(r) or -9) >= 0.2 and (T.fresh_days(r) or 999) <= fresh)) else 2)
    T.once(f"크기: 발표 {fresh}일 안 · 영업이익 +20%↑면 4칸", size=size)
print("끝", flush=True)
