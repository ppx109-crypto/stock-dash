"""일봉 새 68회차 — 빼 보기(자료가 늘어난 뒤 · dguard 통과 기준에서 조건 하나씩 뺌, 10회차마다 점검을 앞당김).

빼도 두 반 모두 같으면(씨앗 폭 안) 단순한 쪽으로 뺌. 행운뺌 · 큰2건뺌 · 골도 함께 봄.
실행: NRL_CACHE=... python3 research/n068.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import ntools as T
import nrl
import rule

print("== 일봉 새 68회차: 빼 보기 ==", flush=True)
base = T.once("지금 규칙(기준)")
inner_holds, inner_aligned = rule.holds, nrl.aligned


def with_patch(tag, holds_fn=None, aligned_fn=None, **kw):
    rule.holds = holds_fn or inner_holds
    nrl.aligned = aligned_fn or inner_aligned
    try:
        return T.once(tag, **kw)
    finally:
        rule.holds, nrl.aligned = inner_holds, inner_aligned


for skip, tag in (("calm", "추세: 조용함"), ("slope", "추세: 180일선 기울기"), ("sixty", "추세: 60일 20%")):
    with_patch("뺌 " + tag, holds_fn=lambda r, s=skip: rule.holds_without(r, s))
import final_study as F
with_patch("뺌 정배열: 간격 19~53%", aligned_fn=lambda r: (F.form_of(nrl.shape, r).get("정배열")
                                                    and nrl.BR.get(r["date"], 0) >= 50))
with_patch("뺌 정배열: 시장 폭 50%", aligned_fn=lambda r: (lambda f: f.get("정배열") and f.get("간격") is not None
                                                      and nrl.LO <= f["간격"] < nrl.HI)(F.form_of(nrl.shape, r)))
got = T.once("뺌 수급(가르침)", holds=lambda r: (rule.holds(r) or nrl.aligned(r)) and not nrl.target_cut(r))
T.diff_check(base, got, "늘어난")
got = T.once("뺌 목표가 45일 내림", holds=lambda r: (rule.holds(r) or nrl.aligned(r)) and nrl.teacher(r))
T.diff_check(base, got, "늘어난")
T.once("크기: 추세 4칸 → 2칸", size=lambda r: 2 if rule.holds(r) else (4 if nrl.steady(r) >= 3 else 2))
T.once("크기: 3일 연속 4칸 → 2칸", size=lambda r: 4 if rule.holds(r) else 2)
import lab


def once_noapart(tag):
    out = [f"  {tag:40s}"]
    for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
        g = lab.wobble(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, tries=8, rank=rule.order, slots=nrl.SLOTS, since=since,
                       apart=None, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
        out.append(side + " " + nrl.line(g, nrl.SLOTS, since))
    print(" | ".join(out), flush=True)


once_noapart("뺌 같이 움직임(apart) — 진짜")
# 파는 쪽
no_half = lab.exit_per_tier(nrl.tier, {"규칙": nrl.half_rule(first=None), "정배열": nrl.broken})


def broken_without(skip):
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        close = lane["closes"][spot]
        if skip != "stop" and (close / price - 1) * 100 <= -10:
            return True
        if skip != "keep" and (peak / price - 1) * 100 >= 8 and (close / price - 1) * 100 <= 1:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]
    return go


T.once("팔기: 추세 반익 뺌(+13% 한 번에)", exit_at=no_half)
for skip, tag in (("keep", "정배열 본전 지키기"), ("stop", "정배열 −10% 손절")):
    T.once("팔기: 뺌 " + tag, exit_at=lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": broken_without(skip)}))
print("끝", flush=True)
