"""일봉 새 82회차 — 사용자 결정(나) 반영 뒤 새 기준 숫자(씨앗 8 · 해마다 · 매매마다 바뀐 시드로 굴린 계좌).
실행: NRL_CACHE=... python3 research/n082.py
"""
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule
exec(open("/home/user/stock-dash/research/n077.py", encoding="utf-8").read().split('print("== 일봉 새 77회차')[0])
import lab
print("== 일봉 새 82회차: 새 규칙(거래량 터진 새 정배열 3칸) 기준 숫자 ==", flush=True)
got = T.once("새 규칙")
print("      해마다", T.years(got), flush=True)
old = T.once("옛 규칙(47회차 크기)", size=lambda r: 4 if rule.holds(r) else (4 if nrl.steady(r) >= 3 else 2))
T.diff_check(old, got)
g = lab.run(nrl.inside, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=rule.SINCE,
            apart=nrl.kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
p = path(g["매매목록"])
years = {}
for d, v in p:
    years[d[:4]] = v
print("  매매마다 바뀐 시드(2017 ~ 2026-09, 1,000만 원 시작): " + " · ".join(f"{y} {v:,.0f}" for y, v in years.items()), flush=True)
print("끝", flush=True)
