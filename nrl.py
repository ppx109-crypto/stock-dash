"""새 RL 공통 재료 — 표(날짜로 다시 맞춤) · 정배열 · 시장 폭 · 수급 창 합 · 맞춤 계좌. (scratchpad가 지워져도 쓰도록 저장소에도 둠)

import 하면 한 번 굽습니다(몇 분). 각 회차 스크립트는 WAYS만 바꿔 run()을 부릅니다.
"""
import bisect
import sys
from datetime import date, timedelta

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
    """정배열이 깨지면 팜 · 손절 −10%(새 14회차에 −8에서 바꿈). 최대 60일은 새 20회차에 뺌(한 번도 걸리지 않음)."""
    spot = start + step
    close = lane["closes"][spot]
    if (close / price - 1) * 100 <= -10:
        return True
    return not shape[lane["code"]]["정배열"][spot]


RULE_EXIT = lab.exit_fixed(10, 5, 10)
tier = lambda r: "규칙" if rule.holds(r) else "정배열"
BASE_EXIT = lab.exit_per_tier(tier, {"규칙": RULE_EXIT, "정배열": broken})


def steady(r, n=3):
    """전날까지 n거래일 가운데 외국인과 투신이 **둘 다** 순매수한 날 수(새 17~19회차)."""
    got = FLOW.get(r["code"])
    if not got:
        return 0
    days, acc, ok, _ = got
    k = bisect.bisect_left(days, r["date"])
    if k < n:
        return 0
    return sum(1 for j in range(k - n + 1, k + 1)
               if acc["외국인"][j] - acc["외국인"][j - 1] > 0 and acc["투신"][j] - acc["투신"][j - 1] > 0)


# 목표가(opinion-data, 2017~ · 새 24회차에 모음): 날마다 증권사별 최근 3달 안 마지막 목표가의 가운데.
TARGETS = {}
for code in {r["code"] for r in inside}:
    got = study.target_timeline(code)
    if got:
        TARGETS[code] = ([d for d, _ in got], [x for _, x in got])


def target_before(r, back_days=0):
    """신호 날(에서 back_days 앞) **전날까지** 알려진 목표가 묶음. 3달 넘게 새 목표가가 없으면 None."""
    got = TARGETS.get(r["code"])
    if not got:
        return None
    days, vals = got
    day = r["date"]
    if back_days:
        d = date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=back_days)
        day = d.strftime("%Y%m%d")
    k = bisect.bisect_left(days, day)
    if k == 0:
        return None
    return vals[k - 1] if days[k - 1] >= study._months_before(day, 3) else None


def target_cut(r, back_days=45):
    """back_days 사이 목표가가 내렸으면 True. 목표가가 없으면 False(빼지 않음)."""
    now, before = target_before(r), target_before(r, back_days)
    return bool(now and before and now["목표가"] < before["목표가"])


# 새 28회차에 더함: 45일 새 목표가가 내린 종목은 사지 않음(A).
BASE_HOLD = lambda r: (rule.holds(r) or aligned(r)) and teacher(r) and not target_cut(r)
# 새 9회차: 추세 규칙 신호는 두 자리(계좌의 2/5). 정배열 신호는 한 자리, 외국인·투신이 3일 연속 둘 다 샀으면
# 두 자리(새 28회차) → 세 자리(새 31회차, 계좌의 3/5).
BASE_SIZE = lambda r: 2 if rule.holds(r) else (3 if steady(r) >= 3 else 1)


def line(g):
    if not g:
        return "60건 미만"
    return (f"매매 {g['매매']:>3} 연 {g['연수익']:>6} (폭 {g['폭']:>5}) 골 {g['최대낙폭']:>6} (골폭 {g['골 폭']:>4}) "
            f"가동 {g['가동률']:>5} 승률 {g['승률']} 보유 {g['보유중앙']}")


# 하루 2종목 한도는 새 30회차에 뺌(빼도 같음). 견주려면 per_day=2를 넘김.
def run(tag, holds=BASE_HOLD, exits=BASE_EXIT, rank=rule.order, slots=5, per_day=None, years=False, **kw):
    kw.setdefault("size", BASE_SIZE)
    out = [f"  {tag:46s}"]
    for side, pool, since in (("앞", early, rule.SINCE), ("뒤", inside, rule.MID)):
        g = lab.wobble(pool, prices, holds, exits, tries=8, rank=rank, slots=slots, since=since,
                       per_day=per_day, apart=kin, realistic=True, cap=130, **kw)
        out.append(side + " " + line(g))
        if years and g:
            out.append(f"해마다 {g['해마다']}")
    print(" | ".join(out), flush=True)
