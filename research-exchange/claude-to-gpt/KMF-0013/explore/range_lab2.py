"""횡보장 봇 탐색 2차: 그날 VWAP(그 봉까지 · 전형가 × 거래량) 되돌림 · 추세 배열 꼬임 / 평평 거름 · 시간대 · 전체 자료 · −25p."""
import sys, json, itertools
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import trend_lab as T
K, K4 = T.K, T.K4
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf13 as M13


def vsignals(b, cfg, F):
    c, h, l, E, atr = F
    n = len(b); want = [None] * n; pos = 0; ent = None; cnt = 0; day = None
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt, pv, vv = d, 0, 0, 0.0, 0.0
        tp = (b[i][3] + b[i][4] + b[i][5]) / 3; v = max(b[i][6], 1)
        pv += tp * v; vv += v; vw = pv / vv
        if i < 4 or np.isnan(E[120][i - 3]) or np.isnan(atr[i]) or atr[i] <= 0:
            continue
        aligned = (E[5][i] > E[20][i] > E[60][i] > E[120][i]) or (E[5][i] < E[20][i] < E[60][i] < E[120][i])
        flat = abs(E[120][i] - E[120][i - 3]) < 0.3 * atr[i]
        dev = (c[i] - vw) / atr[i]
        if pos:
            if (pos > 0 and c[i] >= vw) or (pos < 0 and c[i] <= vw) or pos * (c[i] - ent) < -cfg["stop"] * atr[i]:
                want[i], pos = 0, 0
            continue
        if m > K.ENTRY_TO or m < cfg["t0"] or m > cfg["t1"] or cnt >= cfg["max_n"]:
            continue
        gate = {"none": True, "tangle": not aligned, "flat": flat, "both": (not aligned) and flat}[cfg["gate"]]
        if gate and abs(dev) >= cfg["z"]:
            side = -1 if dev > 0 else 1
            want[i], pos, ent, cnt = side, side, c[i], cnt + 1
    return want


rows = K._rows_before(T.END)
b = K4.day_start_aligned(rows, 5)
td, _ = K.simulate(b, M13.signals(b, M13.grid()[0]))
res = {}
for sc in (0.5, 0.75, 1.0):
    F = T.feats(b, T.spans_for(5, sc))
    for gate, z, stop, (t0, t1), mx in itertools.product(("none", "tangle", "flat", "both"), (1.5, 2.0, 3.0), (1.5, 3.0), ((570, 900), (630, 840)), (3,)):
        cfg = {"gate": gate, "z": z, "stop": stop, "t0": t0, "t1": t1, "max_n": mx}
        days, tr = K.simulate(b, vsignals(b, cfg, F))
        r = T.report(days, tr)
        r["corr_trend"] = round(float(np.corrcoef([days[d] for d in sorted(days)], [td[d] for d in sorted(days)])[0, 1]), 3)
        res[f"sc{sc}_{gate}_z{z}_s{stop}_t{t0}"] = r
json.dump(res, open(Path(__file__).parent / "range_lab.round2.json", "w"), ensure_ascii=False, indent=0)
print("거름 · z · 멈춤 · 시간 → 선 길이 0.5 / 0.75 / 1.0 : 합/+달")
for gate, z, stop, t0 in itertools.product(("none", "tangle", "flat", "both"), (1.5, 2.0, 3.0), (1.5, 3.0), (570, 630)):
    cells = [res[f"sc{sc}_{gate}_z{z}_s{stop}_t{t0}"] for sc in (0.5, 0.75, 1.0)]
    print(f"{gate:<6} z{z} s{stop} t{t0}", "  ".join(f"{c['total']:+6.0f}/{c['pos_m']}" for c in cells), f"상관 {cells[1]['corr_trend']:+.2f}")
