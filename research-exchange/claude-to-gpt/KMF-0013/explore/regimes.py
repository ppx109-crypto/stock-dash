"""국면별 성적: ① 그날 성격(효율 ER = |종가 − 시가| ÷ 5분봉 움직임 합 · 셋으로) ② 그날 하루 폭(셋으로) ③ 달 ④ 위 10일 몫 · 비용 더 들 때."""
import sys, json
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import trend_lab as T
K, K4 = T.K, T.K4
rows = K._rows_before(T.END)
b = K4.day_start_aligned(rows, 5)
byd = defaultdict(list)
for r in b:
    byd[r[0]].append(r)
er = {d: abs(v[-1][5] - v[0][2]) / (sum(abs(v[i][5] - v[i - 1][5]) for i in range(1, len(v))) + 1e-9) for d, v in byd.items()}
rg = {d: max(x[3] for x in v) - min(x[4] for x in v) for d, v in byd.items()}
qe = np.quantile(list(er.values()), [1 / 3, 2 / 3]); qr = np.quantile(list(rg.values()), [1 / 3, 2 / 3])
lab_e = lambda d: "추세일" if er[d] >= qe[1] else "횡보일" if er[d] < qe[0] else "중간일"
lab_r = lambda d: "폭 큼" if rg[d] >= qr[1] else "폭 작음" if rg[d] < qr[0] else "폭 중간"
for sc in (0.5, 0.75, 1.0):
    F = T.feats(b, T.spans_for(5, sc))
    cfg = {"tf": 5, "mode": "align", "exit": 60, "tr": 0, "sk": 3, "max_n": 3, "B": 8}
    days, tr = K.simulate(b, T.signals(b, cfg, F))
    out = {}
    for nm, f in (("성격", lab_e), ("폭", lab_r)):
        g = defaultdict(list)
        for d, v in days.items():
            g[f(d)].append(v)
        out[nm] = {k: (len(v), round(sum(v), 1), round(np.mean(v), 2)) for k, v in sorted(g.items())}
    vs = sorted(days.values(), reverse=True)
    out["위 10일 합"] = round(sum(vs[:10]), 1); out["나머지"] = round(sum(vs[10:]), 1)
    out["비용 +0.1p/거래"] = round(sum(days.values()) - 0.1 * len(tr), 1)
    print(f"sc{sc}", json.dumps(out, ensure_ascii=False))
