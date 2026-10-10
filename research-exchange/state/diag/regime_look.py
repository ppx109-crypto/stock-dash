"""진단: 전날 장 끝까지 값으로 정한 국면별로, 그날 수익을 1일봉 장부 · 인버스 · 2배 인버스 · 코스닥 인버스 · KODEX200 · 레버리지가 얼마나 냈는지(2017-02 ~ 2026-09)."""
import csv, json, bisect, sys
S = sys.argv[1]
base = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(f"{S}/base_m1.csv"))}
ix = {x[0]: x[4] for x in json.load(open("etf-ohlc/069500.json"))["raw"]}
ixd = sorted(ix)
etf = {c: dict((d, x) for d, x in json.load(open(f"etf-data/{c}.json"))["closes"]) for c in ("114800", "252670", "251340", "122630", "069500")}
def phase(d):                     # d날 장 끝까지 069500 60일 수익
    k = bisect.bisect_right(ixd, d) - 1
    if k < 60: return None
    r = ix[ixd[k]] / ix[ixd[k - 60]] - 1
    return "오름" if r > 0.05 else "내림" if r < -0.05 else "횡보"
days = [d for d in sorted(base) if all(d in e for e in etf.values())]
names = {"base": "1일봉 장부", "114800": "인버스", "252670": "2배 인버스", "251340": "코스닥 인버스", "069500": "KODEX200", "122630": "레버리지"}
acc = {}
for j in range(1, len(days)):
    p, d = days[j - 1], days[j]
    ph = phase(p)                 # 전날 판정 → 오늘 수익
    if ph is None: continue
    a = acc.setdefault(ph, {k: 1.0 for k in names} | {"n": 0})
    a["n"] += 1
    a["base"] *= base[d] / base[p]
    for c in etf: a[c] *= etf[c][d] / etf[c][p]
for ph in ("오름", "횡보", "내림"):
    a = acc[ph]; n = a["n"]
    print(ph, f"{n}날", " · ".join(f"{names[k]} 연 {((a[k]) ** (250 / n) - 1) * 100:+.1f}%" for k in names))
