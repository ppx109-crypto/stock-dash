"""4차: 나가기 꼴을 바로 셈 — 'none' 멈춤 · 장 끝만 / 'cross' z가 0을 건너면(평균 돌아옴) / 'opp' z가 반대쪽 +k/2 넘으면 · 거름 f 0.4 ~ 1.0 · 그 밖은 3차와 같음."""
import sys, json, itertools
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import range_r3 as R
S, b, c, atr, d13 = R.S, R.b, R.c, R.atr, R.d13


def rsig(cfg):
    z = R.zband(cfg["L"], cfg["W"])
    n = len(b); want = [None] * n; pos = 0; ent = None; cnt = 0; day = None
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt = d, 0, 0
        if np.isnan(z[i]) or np.isnan(atr[i]) or np.isnan(R.slope90[i]) or np.isnan(R.e90[i]):
            continue
        if pos:
            ex = {"none": False, "cross": pos * z[i] >= 0, "opp": pos * z[i] >= cfg["k"] / 2}[cfg["x"]]
            if ex or pos * (c[i] - ent) <= -cfg["s"] * atr[i]:
                want[i], pos = 0, 0
            continue
        if m < S.K.ENTRY_FROM or m > S.K.ENTRY_TO or cnt >= cfg["n"]:
            continue
        if abs(R.slope90[i]) < cfg["f"] * atr[i] and abs(z[i]) >= cfg["k"]:
            side = -1 if z[i] > 0 else 1
            want[i], pos, ent, cnt = side, side, c[i], cnt + 1
    return want


top13 = set(sorted(d13, key=lambda d: -d13[d])[:10])
res = {}
for L, W, f, k, x, s, n in itertools.product((10, 15, 25), (90, 120, 180), (0.4, 0.6, 0.8, 1.0), (1.5, 2.0, 2.5), ("none", "cross", "opp"), (2.0, 3.0, 4.0), (3, 5)):
    cfg = {"L": L, "W": W, "f": f, "k": k, "x": x, "s": s, "n": n}
    days, tr = S.K.simulate(b, rsig(cfg))
    r = S.report(days, tr); ds = sorted(days)
    both = {d: days[d] + d13[d] for d in ds}
    r.update({"corr13": round(float(np.corrcoef([days[d] for d in ds], [d13[d] for d in ds])[0, 1]), 3),
              "with13": round(sum(both.values()), 1), "with13_ex10": round(sum(sorted(both.values(), reverse=True)[10:]), 1),
              "with13_exTop13": round(sum(v for d, v in both.items() if d not in top13), 1),
              "with13_worst_d": round(min(both.values()), 1)})
    res[json.dumps(cfg)] = r
json.dump(res, open(Path(__file__).parent / "range_r4.json", "w"), ensure_ascii=False)
print("조합", len(res))
for x in ("none", "cross", "opp"):
    sub = [v for k_, v in res.items() if json.loads(k_)["x"] == x]
    print(f"나가기 {x}: 혼자 합 > 0 비율 {sum(v['total'] > 0 for v in sub) / len(sub):.2f} · 혼자 합 가운데값 {np.median([v['total'] for v in sub]):+.0f} · 함께 가운데값 {np.median([v['with13'] for v in sub]):+.0f}")
for k_, v in sorted(res.items(), key=lambda kv: -kv[1]["with13_ex10"])[:15]:
    print(k_, {q: v[q] for q in ("total", "ex10", "trades", "pos_m", "worst_m", "corr13", "with13", "with13_ex10", "with13_exTop13", "with13_worst_d")})
