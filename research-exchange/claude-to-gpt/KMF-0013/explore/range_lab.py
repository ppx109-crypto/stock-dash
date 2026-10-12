"""횡보장 봇 탐색(KMF-0014 준비 · 전체 자료 01-02 ~ 10-12 · −25p · 5분봉 · 그 봉까지 값만).
RNA 되돌림: 추세 봇 배열이 '꼬였을 때'(정배열 · 역배열 아님) 또는 90선 기울기가 작을 때만 ·
 종가가 기준선(45봉 EMA)에서 z × ATR 넘게 벗어나면 반대로 듦 → 기준선(또는 빠른 선) 닿으면 정리 · 반대로 m × ATR 더 가면 정리."""
import sys, json, itertools
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import trend_lab as T
K, K4 = T.K, T.K4
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf13 as M13


def rsignals(b, cfg, F):
    c, h, l, E, atr = F
    n = len(b); want = [None] * n; pos = 0; ent = None; cnt = 0; day = None
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt = d, 0, 0
        if i < 4 or np.isnan(E[120][i - 3]) or np.isnan(atr[i]) or atr[i] <= 0:
            continue
        aligned = (E[5][i] > E[20][i] > E[60][i] > E[120][i]) or (E[5][i] < E[20][i] < E[60][i] < E[120][i])
        flat = abs(E[120][i] - E[120][i - 3]) < cfg["sl"] * atr[i]
        base = E[cfg["base"]][i]
        dev = (c[i] - base) / atr[i]
        if pos:
            if (pos > 0 and c[i] >= E[cfg["tgt"]][i]) or (pos < 0 and c[i] <= E[cfg["tgt"]][i]) or pos * (c[i] - ent) < -cfg["stop"] * atr[i]:
                want[i], pos = 0, 0
            continue
        if m > K.ENTRY_TO or cnt >= cfg["max_n"]:
            continue
        calm = (not aligned) if cfg["gate"] == "tangle" else flat if cfg["gate"] == "flat" else ((not aligned) and flat)
        if calm and abs(dev) >= cfg["z"]:
            side = -1 if dev > 0 else 1
            want[i], pos, ent, cnt = side, side, c[i], cnt + 1
    return want


rows = K._rows_before(T.END)
b = K4.day_start_aligned(rows, 5)
td, _ = K.simulate(b, M13.signals(b, M13.grid()[0]))
res = {}
for sc in (0.5, 0.75, 1.0):
    F = T.feats(b, T.spans_for(5, sc))
    for gate, z, stop, base, tgt, sl in itertools.product(("tangle", "flat", "both"), (1.5, 2.0, 3.0), (1.5, 3.0), (60, 120), (20, 60), (0.3,)):
        if tgt == base == 60 and False:
            continue
        cfg = {"gate": gate, "z": z, "stop": stop, "base": base, "tgt": tgt, "sl": sl, "max_n": 5}
        days, tr = K.simulate(b, rsignals(b, cfg, F))
        r = T.report(days, tr)
        both = {d: days.get(d, 0) + td.get(d, 0) for d in set(days) | set(td)}
        r["corr_trend"] = round(float(np.corrcoef([days[d] for d in sorted(days)], [td[d] for d in sorted(days)])[0, 1]), 3)
        r["with_trend_total"] = round(sum(both.values()), 1)
        r["with_trend_worst_d"] = round(min(both.values()), 1)
        res[f"sc{sc}_{gate}_z{z}_s{stop}_b{base}_t{tgt}"] = r
json.dump(res, open(Path(__file__).parent / "range_lab.round1.json", "w"), ensure_ascii=False, indent=0)
top = sorted(res.items(), key=lambda kv: (-kv[1]["pos_m"], -kv[1]["total"]))[:20]
for k, v in top:
    print(k, {x: v[x] for x in ("total", "per_day", "trades", "pos_m", "worst_m", "mdd", "corr_trend", "with_trend_total", "with_trend_worst_d")})
