"""일봉 새 63회차~ 공통: 같은 날 후보끼리 무리 나누기 · 순서 · 막은 매매 점검 · 거래량 · 분기 실적 · 재무비율.

모든 값은 신호 날 **전날까지** 알려진 것(수급 · 거래량 · 공시 · 재무) 또는 신호 날 종가(가격, 그 종가에 삼)만 씁니다.
"""
import bisect
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import rule

HOME = Path("/home/user/stock-dash")


def _load(path):
    try:
        return json.loads((HOME / path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ── 거래량(전날까지 평균) ──
def vol_entry(body):
    got = sorted((str(d), float(v)) for d, v, *_ in (body.get("날") or []) if v is not None)
    acc = [0.0]
    for _, v in got:
        acc.append(acc[-1] + v)
    return ([d for d, _ in got], acc)


VOL = {}
for _code in {r["code"] for r in nrl.inside}:
    VOL[_code] = vol_entry(_load(f"volume-data/{_code}.json") or {})


def vol_avg(code, day, n=20):
    got = VOL.get(code)
    if not got:
        return None
    days, acc = got
    k = bisect.bisect_left(days, day)
    return (acc[k] - acc[k - n]) / n if k >= n else None


def flow_strength(r, n=5, cols=("외국인", "투신")):
    vals = [nrl.flow_sum(r, n, c) for c in cols]
    v = vol_avg(r["code"], r["date"])
    if None in vals or not v:
        return None
    return sum(vals) / v


def ret(r, m=20):
    c = nrl.lanes[r["code"]]["closes"]
    i = r["i"]
    return c[i] / c[i - m] - 1 if i >= m and c[i - m] else None


def tiers(vals, k, good_low):
    """같은 날 후보의 값 → 0..k-1(좋은 쪽이 큼). 값이 없으면 가운데. 후보가 하나면 가운데."""
    have = sorted((v, c) for c, v in vals.items() if v is not None)
    out = {c: (k - 1) / 2 for c in vals}
    if len(have) < 2:
        return out
    for spot, (v, c) in enumerate(have):
        g = int(spot * k / len(have))
        out[c] = (k - 1 - g) if good_low else g
    return out


BY_DAY = {}
for _r in nrl.inside:
    if nrl.BASE_HOLD(_r):
        BY_DAY.setdefault(_r["date"], []).append(_r)


def rank_by(parts, k=3, first=()):
    """parts = [(값 함수, 낮을수록 좋음?)]. 같은 날 후보끼리 무리 점수 합이 큰 것부터, 같으면 180일선 기울기 순."""
    score = {}
    for day, rows in BY_DAY.items():
        total = {r["code"]: 0.0 for r in rows}
        for fn, low in parts:
            for c, t in tiers({r["code"]: fn(r) for r in rows}, k, low).items():
                total[c] += t
        for r in rows:
            score[(r["code"], day)] = total[r["code"]]

    def key(r):
        head = []
        if "trend" in first:
            head.append(0 if rule.holds(r) else 1)
        if "steady" in first:
            head.append(0 if nrl.steady(r) >= 3 else 1)
        return tuple(head) + (-score.get((r["code"], r["date"]), 0), rule.order(r))
    return key


def once(tag, holds=None, **kw):
    """nrl.run과 같은 판(씨앗 8)에 회전 · 해마다를 더해 찍고 두 반의 결과를 돌려줌."""
    holds = holds or nrl.BASE_HOLD
    kw.setdefault("size", nrl.BASE_SIZE)
    kw.setdefault("rank", rule.order)
    kw.setdefault("exit_at", nrl.BASE_EXIT)
    exit_at = kw.pop("exit_at")
    out, got = [f"  {tag:40s}"], {}
    for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
        g = lab.wobble(pool, nrl.prices, holds, exit_at, tries=8, slots=nrl.SLOTS, since=since,
                       apart=nrl.kin, realistic=True, cap=130, detail=True, **kw)
        got[side] = g
        text = side + " " + nrl.line(g, nrl.SLOTS, since)
        if g:
            led = g["매매목록"]
            yrs = max(1, int(max(t["판 날"] for t in led)[:4]) - int(since[:4]) + 1)
            text += f" 회전 {round(sum(t['자리'] for t in led) / nrl.SLOTS / yrs, 1)}배"
        out.append(text)
    print(" | ".join(out), flush=True)
    return got


def years(got):
    return " · ".join(f"{s} {got[s]['해마다']}" for s in ("앞", "뒤") if got.get(s))


def diff_check(base, got, label="바뀐"):
    """기준 규칙 매매목록(씨앗 0)과 견줘: 기준에만 있는 매매(막힌/밀린)와 새로만 있는 매매(담긴)의 계좌 몫 손익."""
    for side in ("앞", "뒤"):
        b, g = base.get(side), got.get(side)
        if not b or not g:
            continue
        kb = {(t["code"], t["산 날"]) for t in b["매매목록"]}
        kg = {(t["code"], t["산 날"]) for t in g["매매목록"]}
        lost = [t for t in b["매매목록"] if (t["code"], t["산 날"]) not in kg]
        new = [t for t in g["매매목록"] if (t["code"], t["산 날"]) not in kb]
        f = lambda ts: sum(t["손익"] * t["자리"] for t in ts) / nrl.SLOTS
        print(f"      {side} {label}: 기준에만 있던 매매 {len({(t['code'], t['산 날']) for t in lost})}건 {f(lost):+.1f}%(계좌 몫) · "
              f"새로 담긴 매매 {len({(t['code'], t['산 날']) for t in new})}건 {f(new):+.1f}%", flush=True)


# ── 다트 분기 실적: 접수번호 앞 8자리 = 발표일. 신호 날 **앞** 발표만 ──
def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def quarter_entry(body):
    got = []
    for _k, v in (body.get("rows") or {}).items():
        if not v or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        got.append((str(v["접수번호"])[:8], {x: _num(v.get(x)) for x in
                    ("매출", "매출_작년", "영업이익", "영업이익_작년", "순이익", "순이익_작년", "자본", "부채")}))
    got.sort(key=lambda x: x[0])
    return ([d for d, _ in got], [x for _, x in got]) if got else None


QUARTER = {}
for _code in {r["code"] for r in nrl.inside}:
    _got = quarter_entry(_load(f"quarter-data/{_code}.json") or {})
    if _got:
        QUARTER[_code] = _got


def quarter_now(r):
    """신호 날 앞에 발표된 가장 최근 분기(누적) 실적과 발표일."""
    got = QUARTER.get(r["code"])
    if not got:
        return None, None
    days, vals = got
    k = bisect.bisect_left(days, r["date"])
    return (vals[k - 1], days[k - 1]) if k else (None, None)


def op_yoy(r):
    q, _ = quarter_now(r)
    if not q or q["영업이익"] is None or not q["영업이익_작년"]:
        return None
    return (q["영업이익"] - q["영업이익_작년"]) / abs(q["영업이익_작년"])


def sales_yoy(r):
    q, _ = quarter_now(r)
    if not q or q["매출"] is None or not q["매출_작년"]:
        return None
    return (q["매출"] - q["매출_작년"]) / abs(q["매출_작년"])


def op_turn(r):
    q, _ = quarter_now(r)
    return bool(q and q["영업이익"] is not None and q["영업이익_작년"] is not None
                and q["영업이익_작년"] <= 0 < q["영업이익"])


def fresh_days(r):
    _, d = quarter_now(r)
    if not d:
        return None
    a = date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    b = date(int(r["date"][:4]), int(r["date"][4:6]), int(r["date"][6:8]))
    return (b - a).days


# ── 한투 재무비율(분기): 발표일이 없어 분기 끝 + 60일(12월 결산 + 90일) 뒤부터 씀 ──
def ratio_known(ym):
    """재무비율 결산월(YYYYMM) → 쓸 수 있는 첫날(분기 끝 + 60일, 12월 + 90일)."""
    y, m = int(ym[:4]), int(ym[4:])
    end = date(y + (m == 12), 1 if m == 12 else m + 1, 1) - timedelta(days=1)
    return (end + timedelta(days=90 if m == 12 else 60)).strftime("%Y%m%d")


def ratio_entry(body):
    got = []
    for v in body.get("분기") or []:
        ym = str(v.get("결산월", ""))
        if len(ym) != 6 or not ym.isdigit():
            continue
        got.append((ratio_known(ym), v))
    got.sort(key=lambda x: x[0])
    return ([d for d, _ in got], [x for _, x in got]) if got else None


RATIO = {}
for _code in {r["code"] for r in nrl.inside}:
    _got = ratio_entry(_load(f"ratio-data/{_code}.json") or {})
    if _got:
        RATIO[_code] = _got


def ratio_now(r, key):
    got = RATIO.get(r["code"])
    if not got:
        return None
    days, vals = got
    k = bisect.bisect_left(days, r["date"])
    if not k:
        return None
    v = vals[k - 1].get(key)
    return None if v in (None, 0, 0.0) else float(v)


def cover(fn):
    """지금 규칙 후보 신호 가운데 값이 있는 몫(%)."""
    rows = [r for rs in BY_DAY.values() for r in rs]
    return round(sum(1 for r in rows if fn(r) is not None) / max(1, len(rows)) * 100, 1)
