"""진단: 같은 셈을 그날까지의 069500 60일 수익으로 국면을 나눠(오름 > +5% · 내림 < −5% · 그 사이 횡보) 시대(2006~2016 · 2017~2021 · 2022~2026)별로."""
import pickle, bisect, collections, json, sys
ix = {x[0]: x[4] for x in json.load(open("etf-ohlc/069500.json"))["raw"]}
IXD = sorted(ix)
def reg(d):
    k = bisect.bisect_right(IXD, d) - 1
    if k < 60: return None
    r = ix[IXD[k]] / ix[IXD[k - 60]] - 1
    return "오름" if r > 0.05 else "내림" if r < -0.05 else "횡보"
def era(d):
    return "2006~2016" if d < "20170101" else "2017~2021" if d < "20220101" else "2022~2026"
OUT = collections.defaultdict(lambda: collections.defaultdict(list)); DAYS = collections.Counter()
def go(path, lo, hi):
    s = pickle.load(open(path, "rb"))
    P = {c: [x for _, x in b["rows"]] for c, b in s["prices"].items()}
    F = s["flow"]; byd = collections.defaultdict(list)
    for r in s["rows"]:
        if lo <= r["date"] <= hi: byd[r["date"]].append(r)
    for d, rs in byd.items():
        got = []
        for r in rs:
            c = r["code"]; xs = P[c]; i = r["i"]
            if i + 11 >= len(xs) or c not in F: continue
            fd, acc, ok = F[c]; k = bisect.bisect_right(fd, d)
            if k < 10 or ok[k] - ok[k - 10] < 10: continue
            f = acc["외국인"][k] - acc["외국인"][k - 10]; t = acc["투신"][k] - acc["투신"][k - 10]
            g = "FT+" if f > 0 and t > 0 else "FT-" if f < 0 and t < 0 else None
            got.append((g, xs[i + 11] / xs[i + 1] - 1))
        if len(got) < 30: continue
        m = sum(x[1] for x in got) / len(got); key = (era(d), reg(d))
        if key[1] is None: continue
        DAYS[key] += 1
        for g, fwd in got:
            if g: OUT[key][g].append(fwd - m)
go("/tmp/brk-h.pkl", "20060102", "20151230"); go("/tmp/brk-d.pkl", "20160104", "20211230"); go("/tmp/brk-l.pkl", "20220103", "20260915")
for key in sorted(OUT):
    o = OUT[key]; a = sum(o["FT+"]) / len(o["FT+"]) * 100; b = sum(o["FT-"]) / len(o["FT-"]) * 100
    print(key, "날", DAYS[key], "FT+", len(o["FT+"]), round(a, 3), "FT-", len(o["FT-"]), round(b, 3), "차", round(a - b, 3))
