"""일봉 새 70회차 — 숫자 흔들기(자료가 늘고 dguard를 통과한 기준에서 고원 다시 확인, 60 · 61회차의 새 판).

추세 규칙 기울기 · 60일 오름, 정배열 간격 · 시장 폭, 팔기 숫자(반익 · 전량 · 손절 · 정배열 손절 · 본전 지키기)를 양옆으로 흔듦.
실행: NRL_CACHE=... python3 research/n070.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import final_study as F
import lab
import ntools as T
import nrl
import rule

print("== 일봉 새 70회차: 숫자 흔들기 ==", flush=True)
T.once("지금 규칙(기준)")
S0, X0 = rule.SLOPE, rule.SIXTY
for s in (1.3, 1.4, 1.55, 1.7):
    rule.SLOPE = s
    T.once(f"추세 기울기 {s}(지금 {S0})")
rule.SLOPE = S0
for x in (15, 25):
    rule.SIXTY = x
    T.once(f"추세 60일 {x}%(지금 {X0})")
rule.SIXTY = X0
inner = nrl.aligned
for lo, hi in ((16, 53), (22, 53), (19, 48), (19, 60)):
    nrl.LO, nrl.HI = lo, hi
    T.once(f"정배열 간격 {lo}~{hi}%")
nrl.LO, nrl.HI = 19, 53
for br in (45, 55):
    nrl.aligned = lambda r, br=br: (lambda f: f.get("정배열") and f.get("간격") is not None and nrl.LO <= f["간격"] < nrl.HI
                                    and nrl.BR.get(r["date"], 0) >= br)(F.form_of(nrl.shape, r))
    T.once(f"정배열 시장 폭 {br}%")
nrl.aligned = inner


def exits(rule_exit=None, broken=None):
    return lab.exit_per_tier(nrl.tier, {"규칙": rule_exit or nrl.RULE_EXIT, "정배열": broken or nrl.broken})


for kw in ({"first": 4}, {"first": 6}, {"take": 10}, {"take": 16}, {"stop": 4}, {"stop": 6}, {"days": 7}, {"days": 15}):
    T.once("추세 팔기 " + " ".join(f"{k}={v}" for k, v in kw.items()), exit_at=exits(rule_exit=nrl.half_rule(**kw)))


def broken_with(stop=10, arm=8, floor=1):
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        close = lane["closes"][spot]
        if (close / price - 1) * 100 <= -stop:
            return True
        if (peak / price - 1) * 100 >= arm and (close / price - 1) * 100 <= floor:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]
    return go


for kw in ({"stop": 8}, {"stop": 12}, {"arm": 6}, {"arm": 10}, {"floor": 0}, {"floor": 3}):
    T.once("정배열 팔기 " + " ".join(f"{k}={v}" for k, v in kw.items()), exit_at=exits(broken=broken_with(**kw)))
print("끝", flush=True)
