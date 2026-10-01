"""15분봉 3회차 — 1회차 후보(정오 대신 10:45 봉 뒤 · 11:00 시가)의 비용 버팀 + 전 거래일 재료 조합(docs/DATA-AUDIT-15M.md 4절 ⑤).
- 희석 공시 거르기: 사는 날 전 20거래일 안 유상증자 · CB · BW · EB 공시(접수일이 전날까지)면 안 삼(1시간봉 72회차 후보 · ATT['희석20']).
- 목표가 내림 거르기: 45일 사이 증권사 목표가(가운데 값, 전날까지 나온 것)가 내렸으면 안 삼(일봉 새 28회차 · 1시간봉 83회차와 같은 셈).
- 거래량 터진 새 정배열 3칸: 정배열 문인데 전 거래일 거래량이 앞 20일 가운데값의 2배 이상이고 정배열이 된 지 10거래일 안이면 3칸(일봉 새 82회차).
씨앗 16 · 두 반 · 비용 0.30%(+ 0.5% 확인).
"""
import bisect
import json
import statistics
import sys
from datetime import date, timedelta
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q002.py", encoding="utf-8").read().split('nan_ok = lambda')[0])
import study

CTX = W["CTX"]


def mat(c, b, k):
    return ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]


# 목표가(전날까지)
TG = {}
for c in data:
    g = study.target_timeline(c)
    if g:
        TG[c] = ([d for d, _ in g], [x for _, x in g])


def tb(c, day, back=0):
    got = TG.get(c)
    if not got:
        return None
    days, vals = got
    if back:
        day = (date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=back)).strftime("%Y%m%d")
    k = bisect.bisect_left(days, day)
    if k == 0:
        return None
    return vals[k - 1] if days[k - 1] >= study._months_before(day, 3) else None


def target_cut(c, day, back=45):
    a, z = tb(c, day), tb(c, day, back)
    return bool(a and z and a["목표가"] < z["목표가"])


# 거래량비 · 정배열일수(재료 날 = 전 거래일)
VOL = {}
for c in data:
    body = json.load(open(f"volume-data/{c}.json", encoding="utf-8"))
    j = body["칸"].index("거래량")
    rows = sorted((str(r[0]), r[j]) for r in body["날"] if r[j])
    VOL[c] = ([d for d, _ in rows], [v for _, v in rows])


def vol_ratio(c, day):
    days, vals = VOL.get(c, ([], []))
    k = bisect.bisect_right(days, day)
    if k < 21 or days[k - 1] != day:
        return None
    m = statistics.median(vals[k - 21:k - 1])
    return vals[k - 1] / m if m else None


ALIGN_RUN = {}
for c in data:
    run, out = 0, {}
    for day in sorted(CTX.get(c, {})):
        run = run + 1 if CTX[c][day]["정배열"] else 0
        out[day] = run
    ALIGN_RUN[c] = out


def fresh_big(c, x):
    day = x["날"]
    return (x["정배열"] and not x["추세문"] and (ALIGN_RUN[c].get(day) or 999) <= 10
            and (vol_ratio(c, day) or 0) >= 2.0)


def size3(c, b, k):
    x = mat(c, b, k)
    if x and (x["추세문"] or x["3일연속"]):
        return 4
    return 3 if x and fresh_big(c, x) else 2


def entry_f(noon="1045", dil=False, tgt=False):
    base = entry(noon=noon)

    def f(c, b):
        m = base(c, b).copy()
        for k in np.flatnonzero(m):
            x = mat(c, b, k)
            if x is None:
                continue
            if (dil and x["희석20"]) or (tgt and target_cut(c, x["날"])):
                m[k] = False
        return m
    return f


def run2(tag, fn, sz=size, cost=H.COST):
    sigs = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    rk = rank_of(tiers(sigs))
    res = M.simulate(data, lambda c, b: sigs[c], exit_rule, sz, rank=rk, stale_of=stale90, seeds=16, cost=cost)
    print(f"  {tag:34s} 신호 {sum(int(v.sum()) for v in sigs.values()):5d} " + H.line(res), flush=True)


print("== 15분봉 3회차: 후보(10:45 봉 뒤)의 비용 버팀 + 전 거래일 재료 조합 ==", flush=True)
run2("0회차 그대로", entry())
run2("0회차 · 비용 0.5%", entry(), cost=0.5)
run2("후보: 10:45 봉 뒤", entry_f())
run2("후보 · 비용 0.5%", entry_f(), cost=0.5)
run2("후보 + 희석 공시 거르기", entry_f(dil=True))
run2("후보 + 목표가 내림 거르기", entry_f(tgt=True))
run2("후보 + 거래량 터진 새 정배열 3칸", entry_f(), sz=size3)
run2("후보 + 셋 모두", entry_f(dil=True, tgt=True), sz=size3)
print("끝", flush=True)
