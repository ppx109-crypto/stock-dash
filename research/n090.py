"""일봉 새 90회차(세 갈래 공통 G6 · 1일봉) — 정배열 쪽 파는 숫자: 손절 −10% · 이익 지키기(+8% 닿은 뒤 +1% 아래). 기준 = 새 82회차 · 씨앗 8.
Q_PART=1: 손절 −8 · −12% / Q_PART=2: 이익 지키기 (6 → 1) · (10 → 2) · (8 → 3)."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import lab


def broken2(stop=10, keep=(8, 1)):
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        close = lane["closes"][spot]
        if (close / price - 1) * 100 <= -stop:
            return True
        if keep and (peak / price - 1) * 100 >= keep[0] and (close / price - 1) * 100 <= keep[1]:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]
    return go


ex = lambda **kw: lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": broken2(**kw)})
part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 90회차({part}): 정배열 쪽 파는 숫자 ==", flush=True)
T.once("기준(손절 −10 · 지키기 8 → 1)")
if part == "1":
    for s in (8, 12):
        T.once(f"손절 −{s}%", exit_at=ex(stop=s))
else:
    for kp in ((6, 1), (10, 2), (8, 3)):
        T.once(f"이익 지키기 {kp[0]} → {kp[1]}", exit_at=ex(keep=kp))
print("끝", flush=True)
