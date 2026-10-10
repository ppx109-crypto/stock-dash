"""TOM-0028(NEW-BOT-0027 C2) — 월말 · 월초: 매달 마지막 거래일 종가에 KODEX 200(069500)을 사서 다음 달 셋째 거래일 종가에 팖.
사전등록: research-exchange/claude-to-gpt/TOM-0028/PREREG.md. 신호는 달력뿐(값을 안 봄) · 자료는 etf-data/069500.json(한투 일봉 · 분배금 없음 = 가격 수익만).
python3 research/t001.py            (T_TO=YYYYMMDD면 그날까지 자료만 읽음 — 자르기 시험)"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

SRC = Path("/home/user/stock-dash/etf-data/069500.json")
TO = os.getenv("T_TO", "")
COST, STRESS = 0.0010, 0.0030          # 왕복(ETF · 거래세 없음) · 비용 스트레스
PERIODS = {"A": ("20021014", "20121231"), "B": ("20130101", "20191231"), "C": ("20200101", "20260930")}
HOLD = 3                                # 다음 달 셋째 거래일 = 산 날 뒤 3거래일


def load():
    rows = [(str(d), float(c)) for d, c in json.loads(SRC.read_text())["closes"] if c]
    rows = sorted(rows)
    return [(d, c) for d, c in rows if not TO or d <= TO]


def trades(rows, cost):
    """(산 날, 판 날, 순수익) — 산 날 = 그 달 마지막 거래일, 판 날 = 그 뒤 3번째 거래일(다음 달 셋째 거래일). 판 날 자료가 없으면 안 셈."""
    days = [d for d, _ in rows]
    out = []
    for i, d in enumerate(days):
        last_of_month = i + 1 < len(days) and days[i + 1][:6] != d[:6]
        if last_of_month and i + HOLD < len(days):
            j = i + HOLD
            assert days[j][:6] == days[i + 1][:6], ("셋째 거래일이 다음 달이 아님", d)
            out.append((d, days[j], rows[j][1] / rows[i][1] * (1 - cost) - 1))
    return out


def control(rows, cost, skip):
    """같은 보유 길이(3거래일) 대조: 달 마지막 거래일이 아닌 모든 날 종가에 사서 3거래일 뒤 종가에 판 순수익."""
    days = [d for d, _ in rows]
    return [(days[i], rows[i + HOLD][1] / rows[i][1] * (1 - cost) - 1) for i in range(len(days) - HOLD) if days[i] not in skip]


def mean_ci(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    h = 1.96 * sd / math.sqrt(n) if n > 1 else float("nan")
    return m, sd, (m - h, m + h)


def nav(rows, ts):
    """들고 있는 날만 100% · 아니면 현금(이자 0). 날마다 종가 평가 · 비용은 판 날에 왕복 한 번."""
    pos = {}
    for b, s, _ in ts:
        pos[b] = s
    v, out, holding, sell = 1.0, [], False, None
    prev = None
    for d, c in rows:
        if holding:
            v *= c / prev
            if d == sell:
                v *= 1 - COST
                holding = False
        if not holding and d in pos:
            holding, sell = True, pos[d]
        out.append((d, v))
        prev = c
    return out


def risk(navs, lo, hi):
    sel = [(d, v) for d, v in navs if lo <= d <= hi]
    prev = [v for d, v in navs if d < lo]
    base = prev[-1] if prev else sel[0][1]
    rets, last = [], base
    for d, v in sel:
        rets.append((d, v / last - 1))
        last = v
    mon = defaultdict(lambda: 1.0)
    for d, r in rets:
        mon[d[:6]] *= 1 + r
    peak, mdd, eq = 1.0, 0.0, 1.0
    for _, r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    yrs = len(rets) / 245
    return {"cagr": round(((sel[-1][1] / base) ** (1 / yrs) - 1) * 100, 3), "worst_day": round(min(r for _, r in rets) * 100, 3),
            "worst_month": round((min(mon.values()) - 1) * 100, 3), "mdd": round(mdd * 100, 3)}


def summarize(xs):
    m, sd, ci = mean_ci(xs)
    return {"n": len(xs), "mean_pct": round(m * 100, 4), "sd_pct": round(sd * 100, 4), "ci95_pct": [round(ci[0] * 100, 4), round(ci[1] * 100, 4)],
            "median_pct": round(sorted(xs)[len(xs) // 2] * 100, 4), "win_pct": round(sum(1 for x in xs if x > 0) / len(xs) * 100, 2)}


def main():
    rows = load()
    out = {"task": "TOM-0028", "source": str(SRC), "first": rows[0][0], "last": rows[-1][0], "T_TO": TO or None}
    ts, tsS = trades(rows, COST), trades(rows, STRESS)
    skip = {b for b, _, _ in ts}
    ctl = control(rows, COST, skip)
    navs = nav(rows, ts)
    for p, (lo, hi) in list(PERIODS.items()) + [("ALL", ("20021014", "20260930"))]:
        t = [x for b, s, x in ts if lo <= b and s <= hi]
        tS = [x for b, s, x in tsS if lo <= b and s <= hi]
        c = [x for d, x in ctl if lo <= d <= hi]
        if not t:
            continue
        mt, _, _ = mean_ci(t)
        mc, sdc, _ = mean_ci(c)
        st = summarize(t)
        diff = mt - mc
        se = math.sqrt(st["sd_pct"] ** 2 / 1e4 / len(t) + sdc ** 2 / len(c))
        out[p] = {"tom": st, "tom_stress": summarize(tS), "control": summarize(c), "diff_pct": round(diff * 100, 4),
                  "diff_ci95_pct": [round((diff - 1.96 * se) * 100, 4), round((diff + 1.96 * se) * 100, 4)], "risk": risk(navs, lo, hi)}
    out["trades"] = [[b, s, round(x * 100, 4)] for b, s, x in ts]
    out["navs"] = [[d, round(v, 10)] for d, v in navs]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
