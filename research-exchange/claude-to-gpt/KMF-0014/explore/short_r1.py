import sys, json, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import short_lab as S
rows, b, B = S.load()
res = {}
SP = [(2, 5, 15), (3, 8, 21), (3, 10, 30), (4, 15, 45), (5, 20, 60)]
XS = {(2, 5, 15): (5, 15), (3, 8, 21): (8, 21), (3, 10, 30): (10, 30), (4, 15, 45): (15, 45), (5, 20, 60): (20, 60)}
for sp, xi, tr, tg, H, watch, n in itertools.product(SP, (0, 1), (0, 1.5, 3), (0, 2, 4), (0, 12), (0, 1), (5, 10)):
    cfg = {"sp": sp, "xs": XS[sp][xi], "tr": tr, "tg": tg, "H": H, "watch": watch, "n": n}
    days, tr_ = S.K.simulate(b, S.signals(b, cfg, B))
    res[json.dumps(cfg)] = S.report(days, tr_)
json.dump(res, open(Path(__file__).parent / "short_r1.json", "w"), ensure_ascii=False)
top = sorted(res.items(), key=lambda kv: -kv[1]["ex10"])[:25]
for k, v in top:
    print(k, {x: v[x] for x in ("total", "ex10", "trades", "pos_m", "worst_m", "mdd")})
print("조합", len(res))
