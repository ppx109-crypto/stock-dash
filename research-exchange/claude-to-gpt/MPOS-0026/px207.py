import os, sys, json
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import nrl, study
P = study.load_prices()
a, b = dict(P["207940"]["rows"]), dict(nrl.prices["207940"]["rows"])
common = sorted(set(a) & set(b))
diff = [d for d in common if abs(a[d] - b[d]) > 1e-9]
r = [a[d] / b[d] for d in diff]
print(json.dumps({"지금 가격 날": [min(a), max(a), len(a)], "캐시 가격 날": [min(b), max(b), len(b)], "다른 날": len(diff),
                  "다른 날 범위": [diff[0], diff[-1]] if diff else None, "비율(지금 ÷ 캐시) 최소 · 최대": [min(r), max(r)] if r else None,
                  "예": [(d, a[d], b[d]) for d in diff[:3]]}, ensure_ascii=False))
