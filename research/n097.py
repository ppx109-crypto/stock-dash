"""일봉 새 97회차(세 갈래 공통 G12 · 1일봉) — 정배열 손절 고정 10% → k × 변동성(그날 lab 변동성 · research/volstop.py). 기준 = 새 82회차 · 씨앗 8. Q_PART=1 · 2."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import lab
import volstop as VS


def broken_v(k, lo, hi):
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        close = lane["closes"][spot]
        if (close / price - 1) * 100 <= -VS.stop_pct(lane["변동성"][start], k, lo, hi):
            return True
        if (peak / price - 1) * 100 >= 8 and (close / price - 1) * 100 <= 1:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]
    return go


part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 97회차({part}): 정배열 손절을 변동성 배수로 ==", flush=True)
T.once("기준(고정 10%)")
for name, k, lo, hi in VS.VARIANTS[part]:
    T.once(name, exit_at=lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": broken_v(k, lo, hi)}))
print("끝", flush=True)
