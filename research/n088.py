"""일봉 새 88회차(세 갈래 공통 G3 · G4 · 1일봉). 기준 = 새 82회차 · 씨앗 8.
Q_PART=1(G3): 목표가 내림 거르기 뺌 / Q_PART=2(G4): 3일 연속 4칸 → 3칸 · 정배열 2칸 → 3칸 · 추세 4칸 → 3칸."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule

part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 88회차({part}) ==", flush=True)
T.once("기준(새 82회차)")
if part == "1":
    T.once("목표가 내림 거르기 뺌", holds=lambda r: (rule.holds(r) or nrl.aligned(r)) and nrl.teacher(r))
else:
    fresh = lambda r: (r.get("거래량비") or 0) >= nrl.VOL_BIG and (r.get("정배열일수") or 999) <= nrl.FRESH_DAYS
    T.once("3일 연속 3칸", size=lambda r: 4 if rule.holds(r) else (3 if nrl.steady(r) >= 3 else (nrl.FRESH_SIZE if fresh(r) else 2)))
    T.once("정배열 기본 3칸", size=lambda r: 4 if rule.holds(r) else (4 if nrl.steady(r) >= 3 else 3))
    T.once("추세 3칸", size=lambda r: 3 if rule.holds(r) else (4 if nrl.steady(r) >= 3 else (nrl.FRESH_SIZE if fresh(r) else 2)))
print("끝", flush=True)
