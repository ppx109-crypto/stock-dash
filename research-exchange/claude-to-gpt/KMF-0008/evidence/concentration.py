"""KMF-0008 쏠림 · 나간 까닭 진단(판정 밖 · 고른 칸 · 개발 · 확인만 · 09-01부터 안 읽음)."""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf as K, kmf8 as K8
b = K8.prep(K._rows_before(K.TEST[0]))
p = json.loads((K8.BOX / "evidence/pick.json").read_text())
days, trades = K.simulate(b, K8.signals(b, p["cfg"]))
out = {"name": p["name"]}
for nm, (lo, hi) in (("dev", K.DEV), ("val", K.VAL)):
    v = sorted((x for d, x in days.items() if lo <= d <= hi), reverse=True); tot = sum(v)
    tr = [t for t in trades if lo <= t[0] <= hi]
    out[nm] = {"total_p": round(tot, 2), "top1_p": round(v[0], 2), "without_top3_p": round(tot - sum(v[:3]), 2), "without_top5_p": round(tot - sum(v[:5]), 2),
               "trades": len(tr), "avg_trade_p": round(sum(t[2] * (t[4] - t[3]) - 2 * K.COST for t in tr) / len(tr), 3),
               "exit_hour": dict(sorted(Counter(t[1] // 60 for t in tr).items()))}
print(json.dumps(out, ensure_ascii=False, indent=1))
