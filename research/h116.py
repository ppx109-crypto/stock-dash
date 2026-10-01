"""1시간봉 116회차(G9 · 1일봉 → 1시간봉 옮기기) — 1일봉 새 82회차의 '정배열 문인데 전 거래일 거래량이 앞 20일 가운데값 2배↑ · 정배열 된 지 10거래일 안이면 3칸'을 1시간봉 최고 규칙에.
(15분봉 3 · 11회차에선 앞 반이 짐.) Q_SRC=yahoo · kis · 씨앗 16."""
import bisect
import json
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = os.environ.get("Q_SRC", "yahoo")
if src == "kis":
    os.environ["Q_BARS"] = "1h"
    exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
    SG = SIGS
    def RK(sg):
        return RANK
    SIM, EXF = M.simulate, exit_rule
else:
    exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
    SG = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
    def RK(sg):
        global sigs, KEYS
        sigs = sg
        KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sg[c])]
        return rk_of(tiers(20, 5, 3))
    SIM, EXF = H.simulate, EX

VOL, RUN = {}, {}
for c in data:
    if c.startswith("K"):
        continue
    try:
        body = json.load(open(f"volume-data/{c}.json", encoding="utf-8"))
        j = body["칸"].index("거래량")
        rows = sorted((str(r[0]), r[j]) for r in body["날"] if r[j])
        VOL[c] = ([d for d, _ in rows], [v for _, v in rows])
    except (OSError, ValueError, KeyError):
        VOL[c] = ([], [])
    run, out, seen = 0, {}, set()
    for x in ATT[c]:
        if x and x["날"] not in seen:
            seen.add(x["날"])
            run = run + 1 if x["정배열"] else 0
            out[x["날"]] = run
    RUN[c] = out


def vol_ratio(c, day):
    days, vals = VOL.get(c, ([], []))
    k = bisect.bisect_right(days, day)
    if k < 21 or days[k - 1] != day:
        return None
    m = statistics.median(vals[k - 21:k - 1])
    return vals[k - 1] / m if m else None


def size3(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    if x and (x["추세문"] or x["3일연속"]):
        return 4
    if x and x["정배열"] and (RUN[c].get(x["날"]) or 999) <= 10 and (vol_ratio(c, x["날"]) or 0) >= 2.0:
        return 3
    return 2


rk = RK(SG)
print(f"== 1시간봉 116회차(G9): 거래량 터진 새 정배열 3칸 ({src} · {len(data)}종목) ==", flush=True)
for tag, sz in (("기준(94회차)", size), ("+ 거래량 터진 새 정배열 3칸", size3)):
    res = SIM(data, lambda c, b: SG[c], EXF, sz, rank=rk, stale_of=stale90, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)
print("끝", flush=True)
