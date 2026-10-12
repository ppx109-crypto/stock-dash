import sys, json, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import trend_lab as T
K, K4 = T.K, T.K4
rows = K._rows_before(T.END)
res = {}
for tf in (5, 10, 15):
    b = K4.day_start_aligned(rows, tf)
    for sc in (0.5, 0.75, 1.0, 1.5, 2.0):
        F = T.feats(b, T.spans_for(tf, sc))
        for mode, ex, trl, mx in itertools.product(("align", "box"), (20, 60), (0, 3), (2, 3, 5)):
            cfg = {"tf": tf, "mode": mode, "exit": ex, "tr": trl, "sk": max(1, 15 // tf), "max_n": mx, "B": max(2, 40 // tf)}
            days, tr = K.simulate(b, T.signals(b, cfg, F))
            res[f"T{tf}_sc{sc}_{mode}_x{ex}_t{trl}_n{mx}"] = T.report(days, tr)
json.dump(res, open(Path(__file__).parent / "trend_lab.round2.json", "w"), ensure_ascii=False, indent=0)
# 같은 규칙 · 봉 · 선 길이별 표(align x60 t0 n3)
for mode in ("align", "box"):
    for ex in (60, 20):
        print(mode, ex, "· 칸: 봉 tf × 선 길이 배수 → 합 / +달")
        for tf in (5, 10, 15):
            print("  T%-3d" % tf, "  ".join(f"{res[f'T{tf}_sc{sc}_{mode}_x{ex}_t0_n3']['total']:+7.1f}/{res[f'T{tf}_sc{sc}_{mode}_x{ex}_t0_n3']['pos_m']}" for sc in (0.5, 0.75, 1.0, 1.5, 2.0)))
