"""새 RL 공통 재료 — 표(날짜로 다시 맞춤) · 정배열 · 시장 폭 · 수급 창 합 · 맞춤 계좌. (scratchpad가 지워져도 쓰도록 저장소에도 둠)

import 하면 한 번 굽습니다(몇 분). 각 회차 스크립트는 WAYS만 바꿔 run()을 부릅니다.
"""
import bisect
import sys

sys.path.insert(0, "/home/user/stock-dash")
import final_group
import final_study as F
import caps
import lab
import rule
import study

prices = study.load_prices()
rows = lab.load()
caps.tag(rows, rule.TOP)
rule.calm_edge(rows)
rows = lab.realign([r for r in rows if r["date"] >= rule.SINCE], prices)
lanes = lab.lanes(prices)
shape = F.shapes(lanes, {r["code"] for r in rows})
BR = F.breadth_by_day(rows, shape)
inside = [r for r in rows if caps.inside(r, rule.TOP)]
early = [r for r in inside if r["date"] < rule.MID]
kin = rule.apart(prices)
LO, HI = final_group.SPREAD

# 수급: 종목마다 날짜 목록과 누적합(칸별). 창 합을 전날까지로 빠르게 셉니다.
COLS = ("개인", "외국인", "기관", "투신", "연기금", "사모")
FLOW = {}
for code in {r["code"] for r in inside}:
    fr = final_group.flow_rows(code)
    if not fr:
        continue
    days = [x["date"] for x in fr]
    acc = {c: [0.0] for c in COLS}
    ok = [0]
    for x in fr:
        good = all(x.get(c) is not None for c in COLS)
        ok.append(ok[-1] + (1 if good else 0))
        for c in COLS:
            acc[c].append(acc[c][-1] + (x.get(c) or 0.0))
    closes = [x.get("종가") for x in fr]
    FLOW[code] = (days, acc, ok, closes)


def flow_sum(row, n, col, lag=1):
    """그 행의 날 전날까지(lag=1) n거래일 col 순매수 합. 자료가 모자라면 None."""
    got = FLOW.get(row["code"])
    if not got:
        return None
    days, acc, ok, _ = got
    k = bisect.bisect_left(days, row["date"]) - (lag - 1)   # k = 신호 날 앞(전날까지)의 끝
    if lag == 0:
        k = bisect.bisect_right(days, row["date"])
    lo = k - n
    if lo < 0 or ok[k] - ok[lo] < n:
        return None
    return acc[col][k] - acc[col][lo]


def teacher(row, n=5):
    f, t, p = flow_sum(row, n, "외국인"), flow_sum(row, n, "투신"), flow_sum(row, n, "개인")
    return None not in (f, t, p) and f > 0 and t > 0 and p < 0


def aligned(r):
    f = F.form_of(shape, r)
    return f.get("정배열") and f.get("간격") is not None and LO <= f["간격"] < HI and BR.get(r["date"], 0) >= 50


def broken(lane, start, price, step, peak, row=None):
    spot = start + step
    close = lane["closes"][spot]
    if (close / price - 1) * 100 <= -8 or step >= 60:
        return True
    return not shape[lane["code"]]["정배열"][spot]


RULE_EXIT = lab.exit_fixed(10, 5, 10)
tier = lambda r: "규칙" if rule.holds(r) else "정배열"
BASE_HOLD = lambda r: (rule.holds(r) or aligned(r)) and teacher(r)
BASE_EXIT = lab.exit_per_tier(tier, {"규칙": RULE_EXIT, "정배열": broken})


def line(g):
    if not g:
        return "60건 미만"
    return (f"매매 {g['매매']:>3} 연 {g['연수익']:>6} (폭 {g['폭']:>5}) 골 {g['최대낙폭']:>6} (골폭 {g['골 폭']:>4}) "
            f"가동 {g['가동률']:>5} 승률 {g['승률']} 보유 {g['보유중앙']}")


def run(tag, holds=BASE_HOLD, exits=BASE_EXIT, rank=rule.order, slots=5, per_day=2, years=False, **kw):
    out = [f"  {tag:46s}"]
    for side, pool, since in (("앞", early, rule.SINCE), ("뒤", inside, rule.MID)):
        g = lab.wobble(pool, prices, holds, exits, tries=8, rank=rank, slots=slots, since=since,
                       per_day=per_day, apart=kin, realistic=True, cap=130, **kw)
        out.append(side + " " + line(g))
        if years and g:
            out.append(f"해마다 {g['해마다']}")
    print(" | ".join(out), flush=True)
