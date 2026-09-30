"""일봉 새 72회차 — 71회차 후보(같은 날 후보 가운데 최근 공급계약 공시 종목 먼저)의 고원 · 해마다 · 계좌 짜임 · 골.

실행: NRL_CACHE=... python3 research/n072.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule
exec(open("/home/user/stock-dash/research/n071.py", encoding="utf-8").read().split('print("== 일봉 새 71회차')[0])

print("== 일봉 새 72회차: 공급계약 먼저 — 고원 · 해마다 · 짜임 ==", flush=True)
base = T.once("지금 규칙(기준)")
print("      해마다", T.years(base), flush=True)
for days in (5, 10, 20, 30, 45, 60, 90):
    got = T.once(f"순서: 공급계약 {days}일 안 먼저", rank=lambda r, d=days: (0 if had(r, "공급계약", d) else 1, rule.order(r)))
    if days == 20:
        print("      해마다", T.years(got), flush=True)
got = T.once("순서: 공급계약 20일 안 먼저 · 정배열 갈래에만",
             rank=lambda r: (0 if (not rule.holds(r) and had(r, "공급계약", 20)) else 1, rule.order(r)))
got = T.once("순서: 공급계약 20일 안 먼저 · 추세 갈래에만",
             rank=lambda r: (0 if (rule.holds(r) and had(r, "공급계약", 20)) else 1, rule.order(r)))
got = T.once("순서: 공급계약 또는 실적공시 20일 안 먼저",
             rank=lambda r: (0 if (had(r, "공급계약", 20) or had(r, "실적공시", 20)) else 1, rule.order(r)))
k20 = lambda r: (0 if had(r, "공급계약", 20) else 1, rule.order(r))
for slots, tag in ((8, "칸 8"), (12, "칸 12")):
    T.once(f"짜임 {tag}: 기준", slots=slots)
    T.once(f"짜임 {tag}: 공급계약 먼저", slots=slots, rank=k20)
for pd in (1, 2):
    T.once(f"짜임 하루 {pd}종목: 기준", per_day=pd)
    T.once(f"짜임 하루 {pd}종목: 공급계약 먼저", per_day=pd, rank=k20)
print("끝", flush=True)
