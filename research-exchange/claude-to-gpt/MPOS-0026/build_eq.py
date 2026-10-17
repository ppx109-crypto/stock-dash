import os, sys, json
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab, study
P = study.load_prices()
codes = sorted(P)[:6]
cut = "20181228"
Pc = {c: dict(P[c], rows=[x for x in P[c]["rows"] if x[0] <= cut]) for c in codes}
together = {(r["code"], r["date"]): r for r in lab.build(Pc, horizons=(0,))}
alone = {}
for c in codes:
    for r in lab.build({c: Pc[c]}, horizons=(0,)):
        alone[(r["code"], r["date"])] = r
diff = [k for k in together if json.dumps(together[k], sort_keys=True, default=str) != json.dumps(alone.get(k), sort_keys=True, default=str)]
print(json.dumps({"한꺼번에 줄": len(together), "하나씩 줄": len(alone), "다른 줄": len(diff), "예": diff[:3]}, ensure_ascii=False))
