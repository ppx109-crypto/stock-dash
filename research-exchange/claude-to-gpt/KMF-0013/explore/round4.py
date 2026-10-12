import sys, json, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import trend_lab as T
K, K4 = T.K, T.K4
rows = K._rows_before(T.END)
b = K4.day_start_aligned(rows, 5)
res = {}
SC = (0.5, 0.6, 0.75, 0.9, 1.0)
Fs = {sc: T.feats(b, T.spans_for(5, sc)) for sc in SC}
for sc, ex, trl, mx in itertools.product(SC, (20, 60, 120), (0, 4, 6), (2, 3, 5, 9)):
    cfg = {"tf": 5, "mode": "align", "exit": ex, "tr": trl, "sk": 3, "max_n": mx, "B": 8}
    days, tr = K.simulate(b, T.signals(b, cfg, Fs[sc]))
    res[f"sc{sc}_x{ex}_t{trl}_n{mx}"] = T.report(days, tr)
json.dump(res, open(Path(__file__).parent / "trend_lab.round4.json", "w"), ensure_ascii=False, indent=0)
print("정리 · 트레일 · 하루 들기 → 선 길이 0.5 / 0.6 / 0.75 / 0.9 / 1.0 : 합/+달")
for ex, trl, mx in itertools.product((20, 60, 120), (0, 4, 6), (2, 3, 5, 9)):
    cells = [res[f"sc{sc}_x{ex}_t{trl}_n{mx}"] for sc in SC]
    print(f"x{ex:<3} t{trl} n{mx}", "  ".join(f"{c['total']:+6.0f}/{c['pos_m']}" for c in cells), f"  최소 {min(c['total'] for c in cells):+.0f}")
