"""KMF-0002 준비 · 손실 분석(판정 밖 · 개발 기간 2026-01 ~ 05만 · 06-01부터 안 읽음).
ORB 30분(거름 끔) · TR mid gap2 두 칸의 손실이 어디서 오는지: 비용 · 하루 거래 수 · 멈춘 날의 특징 · 들어간 시각 · 아침 범위 폭."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf as K
rows = K._rows_before(K.VAL[0])
byday = defaultdict(list)
for r in rows:
    byday[r[0]].append(r)
feat = {}
for d, rs in byday.items():
    first = [r for r in rs if r[1] < rs[0][1] + 30]       # 그날 첫 30분(늦게 연 날도)
    hi, lo = max(r[3] for r in first), min(r[4] for r in first)
    rest = [r for r in rs if r[1] >= rs[0][1] + 30]
    feat[d] = {"or30": hi - lo, "day_range": max(r[3] for r in rs) - min(r[4] for r in rs),
               "trend": rs[-1][5] - rs[0][2], "after_range": (max(r[3] for r in rest) - min(r[4] for r in rest)) if rest else 0}
out = {}
for cfg in ({"bot": "ORB", "or": 30, "filter": False}, {"bot": "TR", "spans": "mid", "exit_gap": 2}):
    days, trades = K.simulate(rows, K.signals(rows, cfg))
    dev = {d: v for d, v in days.items() if K.DEV[0] <= d <= K.DEV[1]}
    tr = [t for t in trades if K.DEV[0] <= t[0] <= K.DEV[1]]
    per = defaultdict(list)
    for t in tr:
        per[t[0]].append(t)
    gross = sum(t[2] * (t[4] - t[3]) for t in tr)
    stop = [d for d, v in dev.items() if v <= K.DAY_STOP + 1e-9]
    good = [d for d, v in dev.items() if v > 0]
    avg = lambda ds, k: round(sum(feat[d][k] for d in ds) / len(ds), 2) if ds else None
    hour = defaultdict(float); hourn = defaultdict(int)
    for t in tr:
        hour[t[1] // 60] += t[2] * (t[4] - t[3]) - 2 * K.COST; hourn[t[1] // 60] += 1
    # 아침 범위 폭 셋으로 나눠 날 손익
    q = sorted(feat[d]["or30"] for d in dev)
    c1, c2 = q[len(q) // 3], q[2 * len(q) // 3]
    band = {"좁음": [], "중간": [], "넓음": []}
    for d, v in dev.items():
        w = feat[d]["or30"]; band["좁음" if w < c1 else "중간" if w < c2 else "넓음"].append(v)
    nt = [len(per[d]) for d in dev]
    out[K.name(cfg)] = {
        "days": len(dev), "total_p": round(sum(dev.values()), 2), "gross_before_cost_p": round(gross, 2), "cost_p": round(2 * K.COST * len(tr), 2),
        "trades": len(tr), "trades_per_day_avg": round(sum(nt) / len(nt), 2), "trades_per_day_max": max(nt),
        "stop_days": len(stop), "stop_days_sum_p": round(sum(dev[d] for d in stop), 2),
        "stop_days_avg_trades": round(sum(len(per[d]) for d in stop) / len(stop), 2) if stop else None,
        "good_days_avg_trades": round(sum(len(per[d]) for d in good) / len(good), 2) if good else None,
        "or30_avg": {"stop": avg(stop, "or30"), "good": avg(good, "or30")},
        "after_range_avg": {"stop": avg(stop, "after_range"), "good": avg(good, "after_range")},
        "abs_trend_avg": {"stop": round(sum(abs(feat[d]["trend"]) for d in stop) / len(stop), 2) if stop else None,
                          "good": round(sum(abs(feat[d]["trend"]) for d in good) / len(good), 2) if good else None},
        "by_exit_hour_p": {f"{h}시": [round(hour[h], 2), hourn[h]] for h in sorted(hour)},
        "by_or30_band_p": {k: [round(sum(v), 2), len(v), sum(1 for x in v if x <= K.DAY_STOP + 1e-9)] for k, v in band.items()},
        "or30_cut_p": [round(c1, 2), round(c2, 2)],
    }
print(json.dumps(out, ensure_ascii=False, indent=1))
