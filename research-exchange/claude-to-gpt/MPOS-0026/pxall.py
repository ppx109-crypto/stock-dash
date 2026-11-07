import os, sys, json
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import nrl, study
P = study.load_prices()
out = {}
for c in P:
    if c not in nrl.prices:
        out[c] = "캐시에 없음"
    elif P[c]["rows"] != nrl.prices[c]["rows"]:
        a, b = P[c]["rows"], nrl.prices[c]["rows"]
        out[c] = {"지금": [a[0][0], a[-1][0], len(a)], "캐시": [b[0][0], b[-1][0], len(b)]}
print(json.dumps(out, ensure_ascii=False))
