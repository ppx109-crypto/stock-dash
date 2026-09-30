"""1시간봉 92회차 — 90회차 '같은 봉 후보 순서(수급 약 + 20일 수익 큼)'에 91회차 공급계약 먼저 · 84회차 희석 공시 거르기(첫 발표 날)를 더하면 더해지나.
순서: 추세 문 → 3일 연속 → (선택) 공급계약 20일 안 먼저 → 같은 봉 무리 합. 거르기: 희석 20일(dart-events ∪ event-data 첫 발표). 씨앗 16 + 잡음 세계 6."""
import sys, json, bisect, re
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
SRC90 = open("research/h090.py", encoding="utf-8").read()
exec(SRC90.split('CASES = {"지금"')[0].replace("== 1시간봉 90회차 (같은 봉 시각 후보끼리 순위) ==", "== 1시간봉 92회차 (순서 + 공급계약 + 희석 거르기) =="))
DIL = ("유상증자", "전환사채", "신주인수권부사채", "교환사채")
own = re.compile(r"주요사항보고서\((유상증자결정|전환사채권발행결정|신주인수권부사채권발행결정|교환사채권발행결정)\)")
PDAYS, DILD, SUP = {}, {}, {}
for c in data:
    p = Path(f"price-data/{c}.json"); PDAYS[c] = [x[0] for x in json.loads(p.read_text(encoding="utf-8"))["closes"]] if p.exists() else []
    e = H._events(c); ds = [x for k in DIL for x in e.get(k, ())]; sp = []
    q = Path(f"event-data/{c}.json")
    if q.exists():
        for x in json.loads(q.read_text(encoding="utf-8"))["rows"]:
            t = x.get("title", "")
            if own.search(t) and "종속" not in t and "자회사" not in t: ds.append(x["date"])
            if x.get("kind") == "공급계약": sp.append(x["date"])
    DILD[c] = sorted(ds); SUP[c] = sorted(sp)
def had(dates, c, day, n):
    d = PDAYS[c]; i = bisect.bisect_right(d, day) - 1
    if i < 0: return False
    lo = d[max(0, i - n)]; j = bisect.bisect_right(dates, lo)
    return j < len(dates) and dates[j] <= day
def ctx(c, b, k): return ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
BLOCK = {}
for c, b in data.items():
    m = sigs[c].copy()
    for k in np.flatnonzero(m):
        x = ctx(c, b, k)
        if x and had(DILD[c], c, x["날"], 20): m[k] = False
    BLOCK[c] = m
def rk_of(T, supply):
    def r(c, b, k):
        x = ctx(c, b, k)
        hot = supply and bool(x) and had(SUP[c], c, x["날"], 20)
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, 0 if hot else 1, -T.get((c, k), 2))
    return r
def run(tag, rk, dil):
    sg = BLOCK if dil else sigs
    res = H.simulate(data, lambda c, b: sg[c], EX, size, rank=rk, stale_of=stale90, seeds=16)
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, EX, size, lo, hi, 10, seed, None, rk, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    print(f"  {tag:40s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {got['앞']} · 뒤 {got['뒤']}", flush=True)
TB2 = {z: TF[z] + TR[z] for z in F}
CASES = [("지금", rank, False), ("순서(90회차)", rk_of(TB2, False), False), ("순서 + 공급계약 먼저", rk_of(TB2, True), False),
         ("순서 + 희석 거르기", rk_of(TB2, False), True), ("순서 + 공급계약 먼저 + 희석 거르기", rk_of(TB2, True), True)]
for tag, rk, dil in CASES: run(tag, rk, dil)
print("끝", flush=True)
