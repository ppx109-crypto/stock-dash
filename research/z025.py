"""B0 — 1일봉 규칙(새 82) 검증 ①: 숫자 고원(사용자 2026-10-07 "지금 1일봉의 규칙도 검증하면서 강화해줘").
규칙의 숫자를 하나씩 한 칸 위 · 아래로 옮겨도 두 반(앞 2017 ~ 20 · 뒤 2021 ~) 성적이 크게 안 무너지는가(맞춘 숫자인지 확인).
+ 해마다 성적(지금 규칙).
python research/z025.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab  # noqa: E402
import nrl  # noqa: E402
import ntools as T  # noqa: E402
import rule  # noqa: E402

HOLD = nrl.BASE_HOLD


def broken_v(stop=10, arm=8, floor=1):
    def go(lane, start, price, step, peak, row=None):
        close = lane["closes"][start + step]
        if (close / price - 1) * 100 <= -stop:
            return True
        if (peak / price - 1) * 100 >= arm and (close / price - 1) * 100 <= floor:
            return True
        return not nrl.shape[lane["code"]]["정배열"][start + step]
    return go


def exit_v(trend=None, align=None):
    return lab.exit_per_tier(nrl.tier, {"규칙": trend or nrl.RULE_EXIT, "정배열": align or nrl.broken})


def aligned_b(r, b):
    f = nrl.F.form_of(nrl.shape, r)
    return f.get("정배열") and f.get("간격") is not None and nrl.LO <= f["간격"] < nrl.HI and nrl.BR.get(r["date"], 0) >= b


def main():
    print("== B0 ①: 1일봉 숫자 고원 ==", flush=True)
    base = T.once("지금(새 82)", holds=HOLD)
    print("  해마다:", T.years(base), flush=True)
    for tag, kw in [
        ("추세 절반 +4%", dict(exit_at=exit_v(trend=nrl.half_rule(first=4)))),
        ("추세 절반 +6%", dict(exit_at=exit_v(trend=nrl.half_rule(first=6)))),
        ("추세 익절 +11%", dict(exit_at=exit_v(trend=nrl.half_rule(take=11)))),
        ("추세 익절 +15%", dict(exit_at=exit_v(trend=nrl.half_rule(take=15)))),
        ("추세 손절 −4%", dict(exit_at=exit_v(trend=nrl.half_rule(stop=4)))),
        ("추세 손절 −6%", dict(exit_at=exit_v(trend=nrl.half_rule(stop=6)))),
        ("추세 기간 8일", dict(exit_at=exit_v(trend=nrl.half_rule(days=8)))),
        ("추세 기간 12일", dict(exit_at=exit_v(trend=nrl.half_rule(days=12)))),
        ("정배열 손절 −8%", dict(exit_at=exit_v(align=broken_v(stop=8)))),
        ("정배열 손절 −12%", dict(exit_at=exit_v(align=broken_v(stop=12)))),
        ("정배열 지키기 +6→+1", dict(exit_at=exit_v(align=broken_v(arm=6)))),
        ("정배열 지키기 +10→+1", dict(exit_at=exit_v(align=broken_v(arm=10)))),
        ("가르침 수급 3일", dict(holds=lambda r: (rule.holds(r) or nrl.aligned(r)) and nrl.teacher(r, 3) and not nrl.target_cut(r))),
        ("가르침 수급 7일", dict(holds=lambda r: (rule.holds(r) or nrl.aligned(r)) and nrl.teacher(r, 7) and not nrl.target_cut(r))),
        ("정배열 시장 폭 ≥ 45", dict(holds=lambda r: (rule.holds(r) or aligned_b(r, 45)) and nrl.teacher(r) and not nrl.target_cut(r))),
        ("정배열 시장 폭 ≥ 55", dict(holds=lambda r: (rule.holds(r) or aligned_b(r, 55)) and nrl.teacher(r) and not nrl.target_cut(r))),
    ]:
        kw.setdefault("holds", HOLD)
        T.once(tag, **kw)


if __name__ == "__main__":
    main()
