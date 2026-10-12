"""KMF-0002 쏠림 · 정리 시각 진단(판정 밖 · 고른 칸 · 개발 · 확인 기간만 · 09-01부터 안 읽음)."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf as K, kmf2 as K2
rows = K._rows_before(K.TEST[0])
p = json.loads((K2.BOX / "evidence/pick.json").read_text())
days, trades = K.simulate(rows, K2.signals(rows, p["cfg"]))
out = {"name": p["name"]}
for nm, (lo, hi) in (("dev", K.DEV), ("val", K.VAL)):
    ds = {d: x for d, x in days.items() if lo <= d <= hi}
    v = sorted(ds.values(), reverse=True); tot = sum(v)
    hour = defaultdict(lambda: [0.0, 0])
    for t in trades:
        if lo <= t[0] <= hi:
            h = hour[t[1] // 60]; h[0] += t[2] * (t[4] - t[3]) - 2 * K.COST; h[1] += 1
    out[nm] = {"total_p": round(tot, 2), "top1_p": round(v[0], 2), "without_top1_p": round(tot - v[0], 2), "without_top3_p": round(tot - sum(v[:3]), 2),
               "without_top5_p": round(tot - sum(v[:5]), 2), "stop_days": sum(1 for x in v if x <= K.DAY_STOP + 1e-9), "days": len(v),
               "no_trade_days": sum(1 for x in v if x == 0), "best_days": sorted(((d, round(x, 2)) for d, x in ds.items()), key=lambda t: -t[1])[:3],
               "worst_days": sorted(((d, round(x, 2)) for d, x in ds.items()), key=lambda t: t[1])[:3],
               "by_exit_hour_p": {f"{h}시": [round(a, 2), n] for h, (a, n) in sorted(hour.items())}}
print(json.dumps(out, ensure_ascii=False, indent=1))
