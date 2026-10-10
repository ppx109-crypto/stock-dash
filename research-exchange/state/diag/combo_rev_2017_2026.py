"""진단(판정 없음): 1일봉 기준 장부(base_m1) 80% + 내림장 5일 되돌림(REV-DOWN 규칙 그대로) 20% · 달마다 첫날 몫 맞춤."""
import csv, sys, json
sys.path.insert(0, "/home/user/stock-dash/research")
import rev_down as R
S = sys.argv[1]
base = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(f"{S}/base_m1.csv"))}
sim = R.simulate((R.FULL[0], "20170201", "20260915"))
sl = sim["nav"]
days = [d for d in sorted(base) if d in sl]
def rets(nav):
    return {days[j]: nav[days[j]] / nav[days[j - 1]] - 1 for j in range(1, len(days))}
rb, rs = rets(base), rets(sl)
def combo(w):
    vb, vs, out, m = 1 - w, w, {days[0]: 1.0}, days[0][:6]
    for d in days[1:]:
        if d[:6] != m:                       # 달 첫날: 몫 맞춤
            t = vb + vs; vb, vs, m = t * (1 - w), t * w, d[:6]
        vb *= 1 + rb[d]; vs *= 1 + rs[d]; out[d] = vb + vs
    return out
def st(nav):
    r = rets(nav); mo, yr = {}, {}
    for d, x in r.items():
        mo[d[:6]] = mo.get(d[:6], 1) * (1 + x); yr[d[:4]] = yr.get(d[:4], 1) * (1 + x)
    pk, mdd = 0, 0
    for d in days:
        pk = max(pk, nav[d]); mdd = min(mdd, nav[d] / pk - 1)
    n = len(days) / 250
    return {"연": round(((nav[days[-1]] / nav[days[0]]) ** (1 / n) - 1) * 100, 2), "나쁜하루": min(r.items(), key=lambda z: z[1]), "나쁜달": min(mo.items(), key=lambda z: z[1]),
            "낙폭": round(mdd * 100, 1), "해": {y: round((v - 1) * 100, 1) for y, v in yr.items()}, "달": mo}
B = st({d: base[d] for d in days}); SL = st(sl); C = st(combo(0.2)); C1 = st(combo(0.1))
for name, x in (("1일봉 장부", B), ("되돌림 단독", SL), ("결합 80/20", C), ("결합 90/10", C1)):
    print(name, "연", x["연"], "나쁜하루", x["나쁜하루"][0], round(x["나쁜하루"][1] * 100, 2), "나쁜달", x["나쁜달"][0], round((x["나쁜달"][1] - 1) * 100, 2), "낙폭", x["낙폭"])
    print("   ", x["해"])
worst = sorted(B["달"].items(), key=lambda z: z[1])[:10]
print("1일봉 나쁜 달 10개: 달 · 1일봉 · 되돌림 · 결합80/20")
for m, v in worst:
    print("  ", m, round((v - 1) * 100, 2), round((SL["달"].get(m, 1) - 1) * 100, 2), round((C["달"][m] - 1) * 100, 2))
import statistics
xs = [rb[d] for d in days[1:]]; ys = [rs[d] for d in days[1:]]
mx, my = statistics.mean(xs), statistics.mean(ys)
cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / len(xs)
print("날 수익 상관", round(cov / statistics.pstdev(xs) / statistics.pstdev(ys), 3), "날 수", len(days))
