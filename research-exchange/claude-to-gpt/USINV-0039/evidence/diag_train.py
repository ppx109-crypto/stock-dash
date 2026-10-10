"""USINV-0039 실패 원인 뜯어보기 — Train(2017-02-01 ~ 2021-12-30) 자료만 씀(Validation은 열지 않음). python3 evidence/diag_train.py"""
import importlib.util, json, statistics as st
from collections import defaultdict
from pathlib import Path
R = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("t", R / "research/t009.py"); t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
base = t.cut_base(t.base_nav(), t.TRAIN[1]); days, px, dist = t.cut_inv(t.load(t.INV), t.TRAIN[1])
bd = sorted(base); ra = {bd[i]: base[bd[i]] / base[bd[i - 1]] - 1 for i in range(1, len(bd))}
ri = {days[i]: (px[days[i]] + dist.get(days[i], 0)) / px[days[i - 1]] - 1 for i in range(1, len(days))}
com = [d for d in ra if d in ri]
x, y = [ra[d] for d in com], [ri[d] for d in com]
mx, my = st.mean(x), st.mean(y)
out = {"days": len(com), "corr_same_day": round(sum((a - mx) * (b - my) for a, b in zip(x, y)) / len(x) / st.pstdev(x) / st.pstdev(y), 3)}
top = sorted(com, key=lambda d: -ri[d])[:20]
out["inv_best20"] = {"inv_mean_pct": round(st.mean(ri[d] for d in top) * 100, 2), "a_mean_pct": round(st.mean(ra[d] for d in top) * 100, 2)}
bad = sorted(com, key=lambda d: ra[d])[:20]
out["a_worst20"] = {"a_mean_pct": round(st.mean(ra[d] for d in bad) * 100, 2), "inv_mean_pct": round(st.mean(ri[d] for d in bad) * 100, 2)}
ma, mi = defaultdict(lambda: 1.0), defaultdict(lambda: 1.0)
for d in com:
    ma[d[:6]] *= 1 + ra[d]; mi[d[:6]] *= 1 + ri[d]
out["a_worst_months"] = [[m, round((ma[m] - 1) * 100, 2), round((mi[m] - 1) * 100, 2)] for m in sorted(ma, key=lambda m: ma[m])[:6]]
out["us_crash_months"] = {m: [round((ma[m] - 1) * 100, 2), round((mi[m] - 1) * 100, 2)] for m in ["201810", "201811", "201812", "201901", "202002", "202003", "202004", "202005"]}
tot = 1.0
for d in com:
    tot *= 1 + ri[d]
out["inv_always_cagr_pct"] = round((tot ** (245 / len(com)) - 1) * 100, 2)
print(json.dumps(out, ensure_ascii=False))
