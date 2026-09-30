"""일봉 새 67회차 — 연기금 · 사모 수급(한투 투자자 자료 안에 있으나 규칙에서 안 쓴 칸)을 세기로.

모두 신호 날 전날까지 n일 순매수 합 ÷ 20일 평균 거래량(전날까지). 크기 · 순서 · 가르침 넓히기로 봄. 막힌 · 밀린 매매 손익을 직접 봄.
실행: NRL_CACHE=... python3 research/n067.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import ntools as T
import nrl
import rule

print("== 일봉 새 67회차: 연기금 · 사모 수급 세기 ==", flush=True)
PEN = lambda r, n=20: T.flow_strength(r, n, ("연기금",))
PRI = lambda r, n=20: T.flow_strength(r, n, ("사모",))
INS = lambda r, n=20: T.flow_strength(r, n, ("기관",))
print("값 있는 몫 연기금", T.cover(PEN), "% · 사모", T.cover(PRI), "%", flush=True)
rows = [r for rs in T.BY_DAY.values() for r in rs]
vals = sorted(v for v in (PEN(r) for r in rows) if v is not None)
print("연기금 20일 세기 나눔(25 · 50 · 75 · 90%):", [round(vals[int(len(vals) * q)], 3) for q in (0.25, 0.5, 0.75, 0.9)], flush=True)
base = T.once("지금 규칙(기준)")
for tag, fn in (("연기금 20일", PEN), ("사모 20일", PRI), ("기관 합계 20일", INS), ("연기금 5일", lambda r: PEN(r, 5))):
    got = T.once("순서: " + tag + " 센 것 먼저", rank=T.rank_by([(fn, False)]))
    T.diff_check(base, got)
for q in (0.75, 0.9):
    cut = vals[int(len(vals) * q)]
    size = lambda r, cut=cut: 4 if rule.holds(r) else (4 if (nrl.steady(r) >= 3 or (PEN(r) or -9) >= cut) else 2)
    got = T.once(f"크기: 정배열도 연기금 20일 위 {int((1 - q) * 100)}%면 4칸", size=size)
    T.diff_check(base, got)
hold = lambda r: (rule.holds(r) or nrl.aligned(r)) and not nrl.target_cut(r) and (nrl.teacher(r) or (
    (nrl.flow_sum(r, 5, "외국인") or 0) > 0 and (nrl.flow_sum(r, 5, "연기금") or 0) > 0 and (nrl.flow_sum(r, 5, "개인") or 0) < 0))
got = T.once("가르침 넓히기: 투신 대신 연기금도 인정", holds=hold)
T.diff_check(base, got, "늘어난")
hold = lambda r: nrl.BASE_HOLD(r) and not ((PEN(r) or 0) < 0 and (PRI(r) or 0) < 0 and (nrl.flow_sum(r, 20, "외국인") or 0) < 0)
got = T.once("거르기: 20일 연기금 · 사모 · 외국인 모두 순매도면 안 삼", holds=hold)
T.diff_check(base, got, "막은")
print("끝", flush=True)
