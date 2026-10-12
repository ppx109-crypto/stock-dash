"""KMF-0001 쏠림 진단(판정 밖 · 고른 두 칸 · 개발 · 확인 기간만 · 09-01부터는 안 읽음)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf as K
rows = K._rows_before(K.TEST[0])
picks = json.loads((K.BOX / "evidence/picks.json").read_text())
out = {}
for b, p in picks.items():
    if not p:
        continue
    days, trades = K.simulate(rows, K.signals(rows, p["cfg"]))
    res = {}
    for nm, (lo, hi) in (("dev", K.DEV), ("val", K.VAL)):
        v = sorted((x for d, x in days.items() if lo <= d <= hi), reverse=True)
        tot = sum(v)
        res[nm] = {"total_p": round(tot, 2), "top1_p": round(v[0], 2), "top3_p": round(sum(v[:3]), 2),
                   "without_top1_p": round(tot - v[0], 2), "without_top3_p": round(tot - sum(v[:3]), 2),
                   "stop_days": sum(1 for x in v if x <= K.DAY_STOP + 1e-9), "days": len(v),
                   "best_days": [(d, round(x, 2)) for d, x in sorted(((d, x) for d, x in days.items() if lo <= d <= hi), key=lambda t: -t[1])[:3]]}
    out[p["name"]] = res
print(json.dumps(out, ensure_ascii=False, indent=1))
