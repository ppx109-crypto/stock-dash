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

import os
import pickle
from pathlib import Path

# 표(features.json 4GB)를 풀면 메모리가 12GB를 넘어 작업 공간에서 꺼질 수 있어, 한 번 구운 결과를 NRL_CACHE에 담아 다시 씀.
# 표나 일봉이 바뀌면 파일을 지우면 됨(날짜가 표보다 옛것이면 저절로 다시 구움).
CACHE = Path(os.environ.get("NRL_CACHE", "/tmp/nrl-cache.pkl"))
if CACHE.exists() and CACHE.stat().st_mtime > lab.CACHE.stat().st_mtime:
    with CACHE.open("rb") as fh:
        prices, lanes, shape, BR, inside, rule._calm = pickle.load(fh)
else:
    prices = study.load_prices()
    rows = lab.load()
    caps.tag(rows, rule.TOP)
    rule.calm_edge(rows)
    rows = lab.realign([r for r in rows if r["date"] >= rule.SINCE], prices)
    lanes = lab.lanes(prices)
    shape = F.shapes(lanes, {r["code"] for r in rows})
    BR = F.breadth_by_day(rows, shape)
    inside = [r for r in rows if caps.inside(r, rule.TOP)]
    del rows
    with CACHE.open("wb") as fh:
        pickle.dump((prices, lanes, shape, BR, inside, rule._calm), fh, protocol=pickle.HIGHEST_PROTOCOL)
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
    """정배열이 깨지면 팜 · 손절 −10%(새 14회차에 −8에서 바꿈) · 본전 지키기(새 41회차: 한때 +8%에 닿은 뒤 +1% 아래로
    오면 팜). 최대 60일은 새 20회차에 뺌(한 번도 걸리지 않음)."""
    spot = start + step
    close = lane["closes"][spot]
    if (close / price - 1) * 100 <= -10:
        return True
    if (peak / price - 1) * 100 >= 8 and (close / price - 1) * 100 <= 1:
        return True
    return not shape[lane["code"]]["정배열"][spot]


def first_cross(lane, start, price, step, level):
    """오늘 처음으로 +level%를 넘었는가(어제까지 종가가 한 번도 못 닿음). 기억 없이 값 흐름만 봄(45회차 고침)."""
    c = lane["closes"]
    now = (c[start + step] / price - 1) * 100
    return now >= level and max((c[start + k] / price - 1) * 100 for k in range(0, step)) < level


def half_rule(first=5, take=13, stop=5, days=10):
    """추세 규칙 팔기(새 45회차, 사용자 결정): +5%에 처음 닿는 날 절반, +13% 전량 · −5% 손절 · 10거래일."""
    def go(lane, start, price, step, peak, row=None):
        now = (lane["closes"][start + step] / price - 1) * 100
        if now >= take or now <= -stop or step >= days:
            return True
        if first and first_cross(lane, start, price, step, first):
            return max(1, BASE_SIZE(row) // 2)
        return False
    return go


RULE_EXIT = half_rule()
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
# 계좌 10칸(새 45회차부터, 반익절에 칸을 반으로 나누려고). 한 종목 최대 40%(사용자 결정 2026-09-29):
# 추세 규칙 4칸(40%) · 정배열 2칸(20%) · 정배열 + 외국인·투신 3일 연속 둘 다 순매수 4칸(40%, 새 31회차 60%에서 낮춤).
SLOTS = 10
BASE_SIZE = lambda r: 4 if rule.holds(r) else (4 if steady(r) >= 3 else 2)


LUCK_CAP = 30.0      # 행운 뺀 연수익: 한 번 매매의 이익을 이 %에서 자름(사용자 요청 2026-09-29)


def luck(g, slots, since):
    """씨앗 0번 판의 매매목록으로 (단순 연수익, 이익 +30% 자른 연수익, 가장 크게 번 2건 뺀 연수익). 셋 다 복리 없이 더한 값이라
    서로 견줌(복리 '연'과는 견주지 않음). 드문 대박이 평균을 흔들지 않게."""
    led = (g or {}).get("매매목록") or []
    if not led:
        return None, None, None
    years = max(1, int(max(t["판 날"] for t in led)[:4]) - int(str(since)[:4]) + 1)
    w = sorted(t["손익"] * t["자리"] for t in led)
    capped = sum(min(t["손익"], LUCK_CAP) * t["자리"] for t in led) / slots / years
    return round(sum(w) / slots / years, 2), round(capped, 2), round(sum(w[:-2]) / slots / years, 2)


def line(g, slots=None, since=None):
    if not g:
        return "60건 미만"
    text = (f"매매 {g['매매']:>3} 연 {g['연수익']:>6} (폭 {g['폭']:>5}) 골 {g['최대낙폭']:>6} (골폭 {g['골 폭']:>4}) "
            f"가동 {g['가동률']:>5} 승률 {g['승률']} 보유 {g['보유중앙']}")
    if slots and since:
        s, a, b = luck(g, slots, since)
        if a is not None:
            text += f" 단순 {s:>6} 행운뺌 {a:>6} 큰2건뺌 {b:>6}"
    return text


# 하루 2종목 한도는 새 30회차에 뺌(빼도 같음). 견주려면 per_day=2를 넘김.
def run(tag, holds=BASE_HOLD, exits=BASE_EXIT, rank=rule.order, slots=SLOTS, per_day=None, years=False, **kw):
    kw.setdefault("size", BASE_SIZE)
    out = [f"  {tag:46s}"]
    for side, pool, since in (("앞", early, rule.SINCE), ("뒤", inside, rule.MID)):
        g = lab.wobble(pool, prices, holds, exits, tries=8, rank=rank, slots=slots, since=since,
                       per_day=per_day, apart=kin, realistic=True, cap=130, detail=True, **kw)
        out.append(side + " " + line(g, slots, since))
        if years and g:
            out.append(f"해마다 {g['해마다']}")
    print(" | ".join(out), flush=True)
