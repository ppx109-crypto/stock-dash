"""진단(규칙 고르기 없음): 거래대금 상위 100 안에서 t날 10일 수급(외국인 · 투신) 부호 → t+1 종가 ~ t+11 종가 수익, 그날 대상 평균을 뺀 초과수익을 해마다."""
import pickle, bisect, collections, json, sys
OUT = collections.defaultdict(lambda: collections.defaultdict(list))
def go(path, lo, hi):
    s = pickle.load(open(path, "rb"))
    P = {c: ([d for d, _ in b["rows"]], [x for _, x in b["rows"]]) for c, b in s["prices"].items()}
    F = s["flow"]
    byd = collections.defaultdict(list)
    for r in s["rows"]:
        if lo <= r["date"] <= hi:
            byd[r["date"]].append(r)
    for d, rs in byd.items():
        got = []
        for r in rs:
            c = r["code"]; ds, xs = P[c]; i = r["i"]
            if i + 11 >= len(xs): continue
            fwd = xs[i + 11] / xs[i + 1] - 1
            if c not in F: continue
            fd, acc, ok = F[c]
            k = bisect.bisect_right(fd, d)
            if k < 10 or ok[k] - ok[k - 10] < 10: continue
            f = acc["외국인"][k] - acc["외국인"][k - 10]; t = acc["투신"][k] - acc["투신"][k - 10]; p = acc["개인"][k] - acc["개인"][k - 10]
            g = "FT+" if f > 0 and t > 0 else "FT-" if f < 0 and t < 0 else "mix"
            got.append((g, fwd, p < 0))
        if len(got) < 30: continue
        m = sum(x[1] for x in got) / len(got)
        for g, fwd, pneg in got:
            OUT[d[:4]][g].append(fwd - m)
            if g == "FT+" and pneg: OUT[d[:4]]["FT+개인-"].append(fwd - m)
go("/tmp/brk-h.pkl", "20060102", "20151230")
go("/tmp/brk-d.pkl", "20160104", "20211230")
go("/tmp/brk-l.pkl", "20220103", "20260915")
res = {}
for y in sorted(OUT):
    o = OUT[y]
    res[y] = {g: (len(o[g]), round(sum(o[g]) / len(o[g]) * 100, 3)) for g in ("FT+", "FT+개인-", "mix", "FT-") if o[g]}
    a, b = res[y].get("FT+", (0, 0))[1], res[y].get("FT-", (0, 0))[1]
    print(y, res[y], "차", round(a - b, 3))
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
