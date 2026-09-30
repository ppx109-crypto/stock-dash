"""일봉 새 71회차 — 다트 공시 목록(event-data 505종목, 첫 발표 날짜)을 크기 · 순서로.

공급계약 · 실적공시(잠정) · 자사주취득 · 배당 공시가 신호 날 **앞** n일(달력) 안에 있었으면 → 정배열도 4칸 / 같은 날 후보 가운데 먼저.
54회차(주요사항보고서 거르기)와 달리 거르지 않고 크기 · 순서만 봄. 밀린 · 바뀐 매매 손익을 직접 봄.
실행: NRL_CACHE=... python3 research/n071.py
"""
import bisect
import sys
from datetime import date, timedelta

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule

EV = {}
for code in {r["code"] for r in nrl.inside}:
    body = T._load(f"event-data/{code}.json") or {}
    for r in body.get("rows") or []:
        if str(r.get("date", "")).isdigit():
            EV.setdefault((code, r.get("kind")), []).append(str(r["date"]))
for k in EV:
    EV[k].sort()


def had(r, kind, days):
    """신호 날 앞(그날 빼고) days일 안에 그 갈래 공시가 있었나."""
    got = EV.get((r["code"], kind))
    if not got:
        return False
    d = r["date"]
    edge = (date(int(d[:4]), int(d[4:6]), int(d[6:8])) - timedelta(days=days)).strftime("%Y%m%d")
    k = bisect.bisect_left(got, d)
    return k > 0 and got[k - 1] >= edge


print("== 일봉 새 71회차: 다트 공시 목록 → 크기 · 순서 ==", flush=True)
rows = [r for rs in T.BY_DAY.values() for r in rs]
for kind in ("공급계약", "실적공시", "자사주취득", "배당"):
    print(f"후보 신호 가운데 {kind} 20일 안 몫 {round(sum(had(r, kind, 20) for r in rows) / len(rows) * 100, 1)}%", flush=True)
base = T.once("지금 규칙(기준)")
for kind in ("공급계약", "실적공시", "자사주취득"):
    for days in (10, 30):
        size = lambda r, kind=kind, days=days: 4 if rule.holds(r) else (4 if (nrl.steady(r) >= 3 or had(r, kind, days)) else 2)
        got = T.once(f"크기: 정배열도 {kind} {days}일 안이면 4칸", size=size)
        T.diff_check(base, got)
    got = T.once(f"순서: {kind} 20일 안 먼저", rank=lambda r, kind=kind: (0 if had(r, kind, 20) else 1, rule.order(r)))
    T.diff_check(base, got)
print("끝", flush=True)
