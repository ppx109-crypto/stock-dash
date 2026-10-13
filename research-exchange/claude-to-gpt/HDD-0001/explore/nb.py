"""E(60분 띠 벌어짐 → 쉼) 이웃 확인 + 낙폭 위치."""
import sys, json, io, contextlib; sys.path.insert(0, ".")
with contextlib.redirect_stdout(io.StringIO()): import run as R
def dd(p):
    eq = pk = 0; mdd = 0; a = b = pkd = None
    for d in R.DAYS:
        eq += p[d]
        if eq >= pk: pk = eq; pkd = d
        if eq - pk < mdd: mdd = eq - pk; a, b = pkd, d
    return a, b
out = {}
for q in (0.7, 0.75, 0.8, 0.85, 0.9):
    ch = lambda d, q=q: None if (R.BH[d] is not None and R.BH[d] >= q) else R.H(d)
    p = R.run(ch); s = R.stat(p); s["쉰날"] = sum(1 for d in R.DAYS if ch(d) is None); s["낙폭구간"] = dd(p); out[f"E 순위≥{q}"] = s; print(q, s)
print("H 낙폭", dd(R.run(R.H)))
json.dump(out, open("neighbors_E.json", "w"), ensure_ascii=False, indent=1)
