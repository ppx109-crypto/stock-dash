"""일봉 새 RL(nrl · research/ntools)의 규칙 재료 · 계좌 계산에 미래 참조가 없는지 열 겹으로 검사합니다.

guard.py는 표(features.json)의 값을 봅니다. 여기서는 그 위에 얹은 규칙 재료(수급 · 목표가 · 정배열 · 시장 폭 · 거래량 ·
다트 분기 실적 · 한투 재무비율 · 같은 날 순서)와 계좌 계산(lab.run) 전체를 봅니다(사용자 2026-10-01 "미래참조는 다양한 방법으로 차단 및 검사").

 1 시험지 잠금   — 2026-09-30 뒤 신호가 섞이지 않았는가
 2 잘라내기      — 재료마다 원자료를 '그때 알 수 있던 것'까지만 남기고 다시 만들어도 값이 같은가
 3 더럽히기      — 그 뒤의 원자료를 엉뚱한 값으로 바꿔도 값이 같은가
 4 검사 눈       — 일부러 미래를 보게 만든 재료가 2 · 3에 **반드시 걸리는가**(안 걸리면 검사가 고장)
 5 날짜 짚기     — 쓴 분기 실적 · 목표가의 날짜가 모두 신호 날 앞인가 · 재무비율을 쓰는 날이 실제 다트 발표 뒤인가
 6 가로줄        — 시장 폭(모든 종목) · 같은 날 후보 순서가 그날 뒤 자료를 지워도 같은가
 7 끝까지 잘라내기 — 가격 · 수급 · 목표가 · 정배열 · 시장 폭 · 같이 움직임(apart)을 T까지만으로 다시 만들어 계좌를 돌려도,
                   T 전에 끝난 매매가 하나도 다르지 않은가
 8 체결 감사     — 산 날 = 신호 날(그날 종가) · 판 날 > 산 날 · 들고 있던 날 수가 거래일과 맞는가
 9 문턱 달마다   — 규칙의 '조용함' 문턱(전체 기간 한 번)을 달마다 그 달 앞 자료로만 다시 재도 결과가 버티는가
10 무작위 견줌   — 같은 날 같은 수를 무작위로 사면 규칙보다 훨씬 못한가(규칙의 힘이 우연이 아닌가)

실행: NRL_CACHE=... python3 dguard.py   (통과하면 끝에 '종합: 모두 통과', 아니면 어긋난 곳을 적고 1로 끝남)
"""
import bisect
import json
import os
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np

import final_group
import final_study as F
import lab
import nrl
import ntools as T
import rule
import study

HOLDOUT = "20260930"
RNG = random.Random(20261001)
FAILS = []


def say(layer, ok, text):
    print(f"| {layer} | {'통과' if ok else '**어긋남**'} | {text} |", flush=True)
    if not ok:
        FAILS.append(f"{layer}: {text}")


def same(a, b):
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    return a == b


# ── 원자료 읽기 · 설치 (연구 코드의 조립 함수를 그대로 씀) ──
def raw_flow(code):
    return final_group.flow_rows(code)


def put_flow(code, rows):
    if rows:
        nrl.FLOW[code] = nrl.flow_entry(rows)
    else:
        nrl.FLOW.pop(code, None)


def raw_vol(code):
    return T._load(f"volume-data/{code}.json") or {}


def put_vol(code, body):
    T.VOL[code] = T.vol_entry(body)


def raw_quarter(code):
    return T._load(f"quarter-data/{code}.json") or {}


def put_quarter(code, body):
    got = T.quarter_entry(body)
    if got:
        T.QUARTER[code] = got
    else:
        T.QUARTER.pop(code, None)


def raw_ratio(code):
    return T._load(f"ratio-data/{code}.json") or {}


def put_ratio(code, body):
    got = T.ratio_entry(body)
    if got:
        T.RATIO[code] = got
    else:
        T.RATIO.pop(code, None)


def raw_opinion(code):
    return T._load(f"opinion-data/{code}.json") or {}


def put_opinion(code, body):
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / f"{code}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        got = study.target_timeline(code, folder=tmp)
    if got:
        nrl.TARGETS[code] = nrl.target_entry(got)
    else:
        nrl.TARGETS.pop(code, None)


def raw_close(code):
    return nrl.lanes[code]


def put_close(code, lane):
    nrl.lanes[code] = lane
    nrl.shape[code] = F.shapes({code: lane}, [code])[code]


# ── 원자료 자르기 · 더럽히기: (원자료, 신호 줄) → 그때 알 수 있던 것만 / 그 뒤는 엉터리 ──
def _junk():
    return RNG.choice([0.0, -1e12, 1e12, RNG.uniform(-1e7, 1e7)])


def flow_cut(rows, r, dirty):
    keep = [x for x in rows if x["date"] < r["date"]]
    if not dirty:
        return keep
    return keep + [{**x, **{c: _junk() for c in nrl.COLS}, "종가": abs(_junk()) + 1} for x in rows if x["date"] >= r["date"]]


def vol_cut(body, r, dirty):
    rows = body.get("날") or []
    keep = [x for x in rows if str(x[0]) < r["date"]]
    if dirty:
        keep += [[x[0], abs(_junk())] + list(x[2:]) for x in rows if str(x[0]) >= r["date"]]
    return {**body, "날": keep}


def quarter_cut(body, r, dirty):
    out = {}
    for k, v in (body.get("rows") or {}).items():
        if not v or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        if str(v["접수번호"])[:8] < r["date"]:
            out[k] = v
        elif dirty:
            out[k] = {**v, **{x: str(_junk()) for x in ("매출", "매출_작년", "영업이익", "영업이익_작년")}}
    return {**body, "rows": out}


def ratio_cut(body, r, dirty):
    rows = []
    for v in body.get("분기") or []:
        ym = str(v.get("결산월", ""))
        if len(ym) != 6 or not ym.isdigit():
            continue
        if T.ratio_known(ym) < r["date"]:
            rows.append(v)
        elif dirty:
            rows.append({**v, **{k: _junk() for k in ("ROE", "영업이익증가율", "매출증가율", "부채비율")}})
    return {**body, "분기": rows}


def opinion_cut(body, r, dirty):
    rows = body.get("rows") or []
    keep = [x for x in rows if str(x.get("date", "")) < r["date"]]
    if dirty:
        keep += [{**x, "target": abs(_junk()) + 1} for x in rows if str(x.get("date", "")) >= r["date"]]
    return {**body, "rows": keep}


def close_cut(lane, r, dirty):
    i = r["i"]
    closes = list(lane["closes"][:i + 1])
    days = list(lane["날"][:i + 1])
    if dirty:
        closes += [abs(_junk()) + 1.0 for _ in lane["closes"][i + 1:]]
        days += list(lane["날"][i + 1:])
    return {**lane, "closes": closes, "날": days}


SOURCES = {
    "수급": (raw_flow, put_flow, flow_cut),
    "거래량": (raw_vol, put_vol, vol_cut),
    "분기 실적": (raw_quarter, put_quarter, quarter_cut),
    "재무비율": (raw_ratio, put_ratio, ratio_cut),
    "목표가": (raw_opinion, put_opinion, opinion_cut),
    "종가": (raw_close, put_close, close_cut),
}

# 연구에서 쓰는 재료(값 함수, 원자료 이름)
MATERIALS = [
    ("가르침(외국인 · 투신 순매수 · 개인 순매도 5일)", nrl.teacher, "수급"),
    ("3일 연속", nrl.steady, "수급"),
    ("외국인 5일 합", lambda r: nrl.flow_sum(r, 5, "외국인"), "수급"),
    ("연기금 20일 합", lambda r: nrl.flow_sum(r, 20, "연기금"), "수급"),
    ("수급 세기(÷ 20일 거래량)", T.flow_strength, "수급"),
    ("수급 세기의 거래량", lambda r: T.vol_avg(r["code"], r["date"]), "거래량"),
    ("20일 수익", T.ret, "종가"),
    ("정배열 추세(정배열 · 간격)", lambda r: F.form_of(nrl.shape, r), "종가"),
    ("정배열 깨짐 모양", lambda r: bool(nrl.shape[r["code"]]["정배열"][r["i"]]), "종가"),
    ("목표가 45일 내림", nrl.target_cut, "목표가"),
    ("목표가(전날까지)", lambda r: (nrl.target_before(r) or {}).get("목표가"), "목표가"),
    ("영업이익 전년 대비", T.op_yoy, "분기 실적"),
    ("매출 전년 대비", T.sales_yoy, "분기 실적"),
    ("흑자 전환", T.op_turn, "분기 실적"),
    ("발표 뒤 지난 날", T.fresh_days, "분기 실적"),
    ("ROE", lambda r: T.ratio_now(r, "ROE"), "재무비율"),
    ("영업이익증가율(재무비율)", lambda r: T.ratio_now(r, "영업이익증가율"), "재무비율"),
]

# 검사 눈: 일부러 미래를 본 재료. 반드시 걸려야 함.
PEEKS = [
    ("엿보기: 오늘 수급까지(전날이 아니라)", lambda r: nrl.flow_sum(r, 5, "외국인", lag=0), "수급"),
    ("엿보기: 오늘 · 내일까지 든 20일 거래량", lambda r: _vol_peek(r), "거래량"),
    ("엿보기: 5일 뒤 종가", lambda r: nrl.lanes[r["code"]]["closes"][r["i"] + 5] if r["i"] + 5 < len(nrl.lanes[r["code"]]["closes"]) else None, "종가"),
    ("엿보기: 30일 뒤까지 발표된 실적", lambda r: T.op_yoy({**r, "date": _later(r["date"], 30)}), "분기 실적"),
    ("엿보기: 90일 뒤까지 재무비율", lambda r: T.ratio_now({**r, "date": _later(r["date"], 90)}, "ROE"), "재무비율"),
    ("엿보기: 30일 뒤까지 목표가", lambda r: (nrl.target_before({**r, "date": _later(r["date"], 30)}) or {}).get("목표가"), "목표가"),
]


def _vol_peek(r):
    got = T.VOL.get(r["code"])
    if not got:
        return None
    days, acc = got
    k = min(bisect.bisect_left(days, r["date"]) + 2, len(acc) - 1)
    return (acc[k] - acc[k - 20]) / 20 if k >= 20 else None


def _later(day, n):
    from datetime import date, timedelta
    d = date(int(day[:4]), int(day[4:6]), int(day[6:8])) + timedelta(days=n)
    return d.strftime("%Y%m%d")


def sample_rows(n):
    cands = [r for rs in T.BY_DAY.values() for r in rs]
    pool = RNG.sample(cands, min(n // 2, len(cands))) + RNG.sample(nrl.inside, n // 2)
    return pool


def material_check(name, fn, src, rows):
    """(잘라내기에서 달라진 수, 더럽히기에서 달라진 수, 값이 있던 수)."""
    raw_of, put, cut = SOURCES[src]
    diff_cut = diff_dirty = seen = 0
    for r in rows:
        code = r["code"]
        if src == "종가" and code not in nrl.lanes:
            continue
        full = fn(r)
        seen += full is not None and full is not False and full != {}
        original = raw_of(code)
        saved = {"flow": nrl.FLOW.get(code), "vol": T.VOL.get(code), "q": T.QUARTER.get(code), "ratio": T.RATIO.get(code),
                 "tg": nrl.TARGETS.get(code), "lane": nrl.lanes.get(code), "shape": nrl.shape.get(code)}
        try:
            for dirty in (False, True):
                put(code, cut(original, r, dirty))
                got = fn(r)
                if not same(full, got):
                    if dirty:
                        diff_dirty += 1
                    else:
                        diff_cut += 1
        finally:
            for key, table in (("flow", nrl.FLOW), ("vol", T.VOL), ("q", T.QUARTER), ("ratio", T.RATIO), ("tg", nrl.TARGETS),
                               ("lane", nrl.lanes), ("shape", nrl.shape)):
                if saved[key] is None:
                    table.pop(code, None)
                else:
                    table[code] = saved[key]
    return diff_cut, diff_dirty, seen


def layer1():
    last_row = max(r["date"] for r in nrl.inside)
    last_sig = max(T.BY_DAY)
    say("1 시험지 잠금", last_sig <= HOLDOUT and last_row <= HOLDOUT,
        f"신호 마지막 날 {last_sig} · 줄 마지막 날 {last_row} (잠금 {HOLDOUT} 뒤 없음)")


def layer23(rows):
    for name, fn, src in MATERIALS:
        c, d, seen = material_check(name, fn, src, rows)
        say("2 · 3 잘라내기 · 더럽히기", c == 0 and d == 0 and seen > 0,
            f"{name}: 표본 {len(rows)} · 값 있음 {seen} · 잘라 달라짐 {c} · 더럽혀 달라짐 {d}")


def layer4(rows):
    for name, fn, src in PEEKS:
        c, d, seen = material_check(name, fn, src, rows)
        say("4 검사 눈", (c + d) > 0, f"{name}: 걸린 수 잘라 {c} · 더럽혀 {d} (0이면 검사가 고장)")


def layer5():
    rows = [r for rs in T.BY_DAY.values() for r in rs]
    bad_q = sum(1 for r in rows if (T.quarter_now(r)[1] or "0") >= r["date"])
    bad_t = 0
    for r in rows:
        got = nrl.TARGETS.get(r["code"])
        if got:
            k = bisect.bisect_left(got[0], r["date"])
            bad_t += bool(k and got[0][k - 1] >= r["date"])
    say("5 날짜 짚기", bad_q == 0 and bad_t == 0, f"후보 {len(rows)}줄: 신호 날 이후 발표 실적을 쓴 줄 {bad_q} · 목표가 {bad_t}")
    # 재무비율을 쓰는 날(분기 끝 + 60 · 90일)이 실제 다트 분기 보고서 발표일보다 앞서는 경우(= 발표 전에 씀)
    early = total = 0
    for code, (days, vals) in T.RATIO.items():
        q = T.QUARTER.get(code)
        if not q:
            continue
        body = T._load(f"quarter-data/{code}.json") or {}
        filed = {}
        for key, v in (body.get("rows") or {}).items():
            if v and str(v.get("접수번호", ""))[:8].isdigit():
                y, kind = key.split("-")
                end = {"1분기": "03", "반기": "06", "3분기": "09", "사업": "12"}.get(kind)
                if end:
                    filed[y + end] = str(v["접수번호"])[:8]
        for v in vals:
            ym = str(v.get("결산월", ""))
            if ym in filed:
                total += 1
                early += T.ratio_known(ym) < filed[ym]
    share = early / max(1, total) * 100
    say("5 날짜 짚기", share <= 2.0,
        f"재무비율을 쓰는 날이 다트 발표보다 앞선 몫 {share:.1f}% ({early}/{total}, 2% 넘으면 늦춤을 더 늘려야 함)")


def layer6():
    # 시장 폭: 모든 종목 종가를 그날까지로 자르고 다시 만든 폭이 같은가
    days = sorted(nrl.BR)
    picks = [days[len(days) * k // 6] for k in range(1, 6)]
    codes = {r["code"] for r in nrl.inside}
    for day in picks:
        lanes_cut = {}
        for c in codes:
            lane = nrl.lanes[c]
            k = bisect.bisect_right(lane["날"], day)
            lanes_cut[c] = {**lane, "closes": lane["closes"][:k], "날": lane["날"][:k]}
        shape_cut = F.shapes(lanes_cut, codes)
        rows = [r for r in nrl.inside if r["date"] == day and r["i"] < len(lanes_cut[r["code"]]["closes"])]
        br = F.breadth_by_day(rows, shape_cut).get(day)
        say("6 가로줄", same(round(br or -1, 9), round(nrl.BR.get(day, -1), 9)),
            f"시장 폭 {day}: 원래 {nrl.BR.get(day)} · 그날까지로 다시 {br}")
    # 같은 날 후보 순서: 그날 뒤 후보를 모두 지우고 뒤 줄 값을 더럽혀도 점수가 같은가
    key_full = T.rank_by([(T.flow_strength, True), (T.ret, False)])
    days = sorted(T.BY_DAY)
    day = days[len(days) // 2]
    kept = {d: v for d, v in T.BY_DAY.items() if d <= day}
    saved = dict(T.BY_DAY)
    T.BY_DAY.clear()
    T.BY_DAY.update(kept)
    try:
        key_cut = T.rank_by([(T.flow_strength, True), (T.ret, False)])
    finally:
        T.BY_DAY.clear()
        T.BY_DAY.update(saved)
    rows = [r for d in days if d <= day for r in T.BY_DAY[d]][-300:]
    bad = sum(1 for r in rows if key_full(r) != key_cut(r))
    say("6 가로줄", bad == 0, f"같은 날 후보 순서: {day}까지 {len(rows)}줄 · 뒷날 후보를 지웠을 때 달라진 순서 {bad}")


def _cut_world(Tday):
    """T까지만의 세상: 가격 · 수급 · 목표가 · 정배열 · 시장 폭 · apart를 T까지로 다시 만듦."""
    prices_cut = {}
    for c, one in nrl.prices.items():
        rows = one.get("rows") if isinstance(one, dict) else None
        if rows is None:
            prices_cut[c] = one
            continue
        prices_cut[c] = {**one, "rows": [x for x in rows if str(x[0]) <= Tday]}
    lanes_cut = lab.lanes(prices_cut)
    codes = {r["code"] for r in nrl.inside}
    shape_cut = F.shapes(lanes_cut, codes)
    rows = [r for r in nrl.inside if r["date"] <= Tday]
    br = F.breadth_by_day(rows, shape_cut)
    flow = {c: nrl.flow_entry([x for x in final_group.flow_rows(c) if x["date"] <= Tday]) for c in nrl.FLOW}
    targets = {}
    for c in nrl.TARGETS:
        body = raw_opinion(c)
        body = {**body, "rows": [x for x in body.get("rows") or [] if str(x.get("date", "")) <= Tday]}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / f"{c}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            got = study.target_timeline(c, folder=tmp)
        if got:
            targets[c] = nrl.target_entry(got)
    kin = rule.apart(prices_cut)
    return prices_cut, rows, shape_cut, br, flow, targets, kin


def _ledger(prices, rows, kin, since):
    g = lab.run(rows, prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since,
                apart=kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
    return g["매매목록"] if g else []


def layer7():
    for Tday, since in (("20190630", rule.SINCE), ("20231231", rule.MID), ("20250630", rule.MID)):
        full = [t for t in _ledger(nrl.prices, nrl.inside, nrl.kin, since) if t["판 날"] <= Tday]
        world = _cut_world(Tday)
        saved = (nrl.shape, nrl.BR, nrl.FLOW, nrl.TARGETS)
        try:
            nrl.shape, nrl.BR, nrl.FLOW, nrl.TARGETS = world[2], world[3], world[4], world[5]
            cut = [t for t in _ledger(world[0], world[1], world[6], since) if t["판 날"] <= Tday]
        finally:
            nrl.shape, nrl.BR, nrl.FLOW, nrl.TARGETS = saved
        key = lambda t: (t["code"], t["산 날"], t["판 날"], t["자리"], round(t["손익"], 6))
        a, b = sorted(map(key, full)), sorted(map(key, cut))
        say("7 끝까지 잘라내기", a == b and len(a) > 0,
            f"T={Tday}: T 전에 끝난 매매 원래 {len(a)} · T까지만 {len(b)} · 다른 매매 {len(set(a) ^ set(b))}")


def layer8():
    bad = n = 0
    for since, pool in ((rule.SINCE, nrl.early), (rule.MID, nrl.inside)):
        for t in _ledger(nrl.prices, pool, nrl.kin, since):
            n += 1
            lane = nrl.lanes[t["code"]]
            i = t["행"]["i"]
            j = bisect.bisect_left(lane["날"], t["판 날"])
            ok = (t["산 날"] == t["행"]["date"] == lane["날"][i] and t["판 날"] > t["산 날"]
                  and j < len(lane["날"]) and lane["날"][j] == t["판 날"] and j - i == t["들고"])
            bad += not ok
    say("8 체결 감사", bad == 0 and n > 0, f"매매 {n}건: 산 날 = 신호 날 종가 · 판 날 > 산 날 · 들고 있던 거래일 수가 맞지 않은 매매 {bad}")


def _median_year(holds=None, rank=None, exits=None):
    out = []
    for since, pool in ((rule.SINCE, nrl.early), (rule.MID, nrl.inside)):
        g = lab.wobble(pool, nrl.prices, holds or nrl.BASE_HOLD, exits or nrl.BASE_EXIT, tries=8, rank=rank or rule.order,
                       slots=nrl.SLOTS, since=since, apart=nrl.kin, realistic=True, cap=130, size=nrl.BASE_SIZE)
        out.append(g["연수익"] if g else None)
    return out


def layer9(base):
    if not nrl.CALM_MONTH:
        say("9 문턱 달마다", False, "달마다 문턱이 준비 파일에 없음 — NRL_CACHE를 지우고 다시 구워야 함")
        return
    full = rule._calm
    inner = rule.holds

    def holds_past(r):
        rule._calm = nrl.CALM_MONTH.get(r["date"][:6], full)
        try:
            return inner(r)
        finally:
            rule._calm = full
    rule.holds = holds_past
    try:
        got = _median_year()
    finally:
        rule.holds = inner
    months = sorted(nrl.CALM_MONTH)
    span = [round(nrl.CALM_MONTH[m], 3) for m in (months[0], months[len(months) // 2], months[-1])]
    ok = all(g is not None and g >= b - max(3.0, abs(b) * 0.2) for g, b in zip(got, base))
    say("9 문턱 달마다", ok, f"조용함 문턱 전체 한 번 {round(full, 3)} · 달마다(처음 · 가운데 · 끝) {span} → "
                         f"연수익 앞 {base[0]} → {got[0]} · 뒤 {base[1]} → {got[1]} (20% 또는 3%p 넘게 떨어지면 어긋남)")


def layer10(base):
    counts = {d: len(v) for d, v in T.BY_DAY.items()}
    by_day = {}
    for r in nrl.inside:
        by_day.setdefault(r["date"], []).append(r)
    picked = set()
    rng = random.Random(7)
    for d, n in counts.items():
        pool = by_day.get(d) or []
        for r in rng.sample(pool, min(n, len(pool))):
            picked.add((r["code"], d))
    # 무작위 줄은 대부분 정배열이 아니라 정배열 팔기(깨지면 팜)를 쓰면 다음 날 팔림 → 모두 추세 규칙 팔기(+5 반 · +13 · −5 · 10일)로.
    rand = _median_year(holds=lambda r: (r["code"], r["date"]) in picked, exits=nrl.RULE_EXIT)
    ok = all(r is not None and b is not None and b > r + 3 for r, b in zip(rand, base))
    say("10 무작위 견줌", ok, f"같은 날 같은 수를 무작위로 삼: 연수익 앞 {rand[0]} · 뒤 {rand[1]} vs 규칙 앞 {base[0]} · 뒤 {base[1]}")


def main():
    print("# 일봉 미래 참조 검사(dguard.py)\n\n| 겹 | 결과 | 내용 |\n|---|---|---|", flush=True)
    layer1()
    rows = sample_rows(int(os.environ.get("DGUARD_SAMPLE", "240")))
    layer23(rows)
    layer4(rows)
    layer5()
    layer6()
    layer7()
    layer8()
    base = _median_year()
    layer9(base)
    layer10(base)
    print("\n**종합: " + ("모두 통과**" if not FAILS else f"어긋남 {len(FAILS)}곳**"), flush=True)
    for f in FAILS:
        print("- " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
