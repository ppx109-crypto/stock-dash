import sys, json, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import trend_lab as T
K, K4 = T.K, T.K4
rows = K._rows_before(T.END)
b = K4.day_start_aligned(rows, 5)
res = {}
Fs = {sc: T.feats(b, T.spans_for(5, sc)) for sc in (0.5, 0.75, 1.0)}
for sc, orf, erf, tf0, mx in itertools.product((0.5, 0.75, 1.0), (0, 30, 60), (0.0, 0.2, 0.35), (0, 600), (3,)):
    cfg = {"tf": 5, "mode": "align", "exit": 60, "tr": 0, "sk": 3, "max_n": mx, "B": 8, "orf": orf, "erf": erf, "t_from": tf0}
    days, tr = K.simulate(b, T.signals(b, cfg, Fs[sc]))
    res[f"sc{sc}_or{orf}_er{erf}_t{tf0}"] = T.report(days, tr)
json.dump(res, open(Path(__file__).parent / "trend_lab.round3.json", "w"), ensure_ascii=False, indent=0)
print("거름 → 선 길이 0.5 / 0.75 / 1.0 : 합 · +달 · 가장 나쁜 달 · 고점 대비")
for orf, erf, tf0 in itertools.product((0, 30, 60), (0.0, 0.2, 0.35), (0, 600)):
    cells = [res[f"sc{sc}_or{orf}_er{erf}_t{tf0}"] for sc in (0.5, 0.75, 1.0)]
    print(f"or{orf:<3} er{erf:<4} t{tf0:<4}", " | ".join(f"{c['total']:+7.1f} {c['pos_m']} {c['worst_m']:+6.1f} {c['mdd']:+6.1f}" for c in cells))
