"""F 10회차 — 파는 쪽 수급: 들고 있는 동안 큰손이 돌아서면 팜(1일봉 엔진 · 새 82 그대로 · 씨앗 8).
그날 장 끝 판단(그날 종가에 팖) · 수급은 전날까지(flow_sum lag=1 — 사는 쪽과 같음, 미래 참조 없음).
Q_PART=1: 정배열 매매에만 / Q_PART=2: 추세 · 정배열 모두."""
import os
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import ntools as T

rule = nrl.rule


def at(lane, start, step):
    return {"code": lane["code"], "date": lane["날"][start + step]}


def fsum(lane, start, step, col, n=5):
    return nrl.flow_sum(at(lane, start, step), n, col)


TESTS = {
    "가르침 깨짐(외+ 투+ 개− 아님)": lambda l, s, k: not nrl.teacher(at(l, s, k)),
    "거꾸로 가르침(외− 투− 개+)": lambda l, s, k: (lambda f, t, p: None not in (f, t, p) and f < 0 and t < 0 and p > 0)(
        fsum(l, s, k, "외국인"), fsum(l, s, k, "투신"), fsum(l, s, k, "개인")),
    "외국인 5일 −": lambda l, s, k: (fsum(l, s, k, "외국인") or 0) < 0,
    "외국인 · 투신 5일 모두 −": lambda l, s, k: (fsum(l, s, k, "외국인") or 0) < 0 and (fsum(l, s, k, "투신") or 0) < 0,
    "외국인 3일 −": lambda l, s, k: (fsum(l, s, k, "외국인", 3) or 0) < 0,
    "외국인 10일 −": lambda l, s, k: (fsum(l, s, k, "외국인", 10) or 0) < 0,
}


def with_flow(base, test, min_step=1, only_profit=False):
    def go(lane, start, price, step, peak, row=None):
        got = base(lane, start, price, step, peak, row)
        if got:
            return got
        if step < min_step:
            return False
        if only_profit and lane["closes"][start + step] <= price:
            return False
        return bool(test(lane, start, step))
    return go


part = os.environ.get("Q_PART", "1")
print(f"== F 10회차({part}): 들고 있는 동안 수급이 돌아서면 팜 ==", flush=True)
if part == "1":
    T.once("지금(새 82)")
    for name, test in TESTS.items():
        ex = lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": with_flow(nrl.broken, test)})
        T.once(f"정배열만 · {name}", exit_at=ex)
else:
    for name in ("가르침 깨짐(외+ 투+ 개− 아님)", "거꾸로 가르침(외− 투− 개+)", "외국인 · 투신 5일 모두 −"):
        test = TESTS[name]
        ex = lab.exit_per_tier(nrl.tier, {"규칙": with_flow(nrl.RULE_EXIT, test), "정배열": with_flow(nrl.broken, test)})
        T.once(f"모두 · {name}", exit_at=ex)
        ex = lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": with_flow(nrl.broken, test, min_step=3)})
        T.once(f"정배열 · 3일 지난 뒤 · {name}", exit_at=ex)
        ex = lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": with_flow(nrl.broken, test, only_profit=True)})
        T.once(f"정배열 · 이익 중일 때만 · {name}", exit_at=ex)
print("끝", flush=True)
