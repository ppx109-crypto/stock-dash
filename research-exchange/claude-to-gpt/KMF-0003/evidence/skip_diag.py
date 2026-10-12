"""KMF-0003 판정 밖 진단: 확인 기간에 W25가 거른 날의 B0 손익(이미 셈한 두 칸만 · 09-01부터 안 읽음)."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf as K, kmf3 as K3
rows = K._rows_before(K.TEST[0])
g = {c["tag"]: c for c in K3.grid()}
b, _ = K.simulate(rows, K3.signals(rows, g["B0"]))
w, _ = K.simulate(rows, K3.signals(rows, g["W25"]))
out = {}
for nm, (lo, hi) in (("dev", K.DEV), ("val", K.VAL)):
    ds = [d for d in b if lo <= d <= hi]
    diff = [d for d in ds if abs(b[d] - w[d]) > 1e-9]
    skipped = [d for d in diff if w[d] == 0]
    out[nm] = {"days_changed": len(diff), "skipped_days": len(skipped), "b0_pnl_on_skipped_p": round(sum(b[d] for d in skipped), 2),
               "b0_stop_on_skipped": sum(1 for d in skipped if b[d] <= K.DAY_STOP + 1e-9),
               "b0_best_skipped": sorted(((d, round(b[d], 2)) for d in skipped), key=lambda t: -t[1])[:4]}
print(json.dumps(out, ensure_ascii=False, indent=1))
