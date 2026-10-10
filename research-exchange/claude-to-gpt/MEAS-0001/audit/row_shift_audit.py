"""MEAS-0001 B — 종목별 '수급 줄' 기준 창(nrl.flow_sum: 그 종목의 앞 5줄)이 시장 거래일 5일과 다른 경우 세기. 자료 JSON만 읽음.
python row_shift_audit.py <00b98ab1 폴더> <out.json>"""
import bisect
import json
import sys
from pathlib import Path

BASE, OUT = Path(sys.argv[1]), sys.argv[2]
cal = sorted(str(r["date"]) for r in json.loads((BASE / "market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"] if r.get("종가"))
pos = {d: i for i, d in enumerate(cal)}
tot = {"codes": 0, "decision_days": 0, "window_span_gt5": 0, "window_span_gt6": 0, "stale_gt10_calendar": 0, "missing_trading_days_inside_coverage": 0,
       "rows_not_trading_day": 0}
worst = []
for p in sorted((BASE / "investor-data").glob("*.json")):
    rows = json.loads(p.read_text(encoding="utf-8")).get("rows") or []
    days = sorted({str(r[0]) for r in rows if r and str(r[0]) >= "20170101"})
    if len(days) < 10:
        continue
    tot["codes"] += 1
    tot["rows_not_trading_day"] += sum(1 for d in days if d not in pos)
    lo, hi = pos.get(days[0]), pos.get(days[-1])
    if lo is None or hi is None:
        continue
    have = set(days)
    miss = [cal[i] for i in range(lo, hi + 1) if cal[i] not in have]
    tot["missing_trading_days_inside_coverage"] += len(miss)
    for i in range(lo + 6, hi + 1):
        T = cal[i]
        k = bisect.bisect_left(days, T)
        if k < 5:
            continue
        tot["decision_days"] += 1
        first = days[k - 5]
        if first not in pos:
            continue
        span = i - pos[first]                       # 결정일 T에서 창 첫 줄까지 거래일 수(정상 = 5)
        if span > 5:
            tot["window_span_gt5"] += 1
        if span > 6:
            tot["window_span_gt6"] += 1
            if len(worst) < 15:
                worst.append({"code": p.stem, "T": T, "window_first": first, "trading_days_back": span})
        last = days[k - 1]
        if (int(T) - int(last)) > 0 and pos[T] - pos[last] > 7:   # 마지막 줄이 7거래일 넘게 앞
            tot["stale_gt10_calendar"] += 1
Path(OUT).write_text(json.dumps({"summary": tot, "examples_span_gt6": worst}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(tot, ensure_ascii=False))
