"""1시간봉 122회차(세 갈래 공통 G11 · RNA 시장 폭 문턱 · 1시간봉) — 정배열 문의 '시장 폭 50% 이상'을 '앞 n일 q분위 이상'으로(research/rnabr.py).
기준 = 94회차 · 씨앗 16. Q_SRC=yahoo(3년 · 두 반) · kis(한투 1년 · research/kis1h.py · 두 반). Q_PART=1 · 2."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import hlab as H
import kis1h
import rnabr as R

src = os.environ.get("Q_SRC", "yahoo")
PER = None
if src == "kis":
    PER = kis1h.use()
exec(open("/home/user/stock-dash/research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
BR = {}
for c in ATT:
    for x in ATT[c]:
        if x and x.get("시장폭") is not None:
            BR[x["날"]] = x["시장폭"]


def door2(x, gate=None):
    if not x:
        return None
    if x["추세문"]:
        return "추세"
    ok = (x["시장폭"] or 0) >= 50 if gate is None else gate(x["날"], x["시장폭"])
    if x["정배열"] and 19 <= x["간격"] < 53 and ok:
        return "정배열"
    return None


def entry_d(gate=None):
    def f(c, b):
        ctx = np.array([bool(x) and door2(x, gate) is not None and x["가르침"] for x in ATT[c]]) & IN[c]
        s = H.states(c, b, "A")["정배열"] == 1
        al = ctx & s & ~np.r_[False, s[:-1]]
        nn = ctx & hour_is(b, "11")
        days = [t[:8] for t in b["t"]]
        seen, m = set(), np.zeros(len(b["t"]), bool)
        for k in np.flatnonzero(al | nn):
            if days[k] not in seen:
                m[k] = True
                seen.add(days[k])
        return m
    return f


def go(tag, fn):
    global sigs, KEYS
    sigs = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
    rk = rk_of(tiers(20, 5, 3))
    kw = {"periods": PER} if PER else {}
    res = H.simulate(data, lambda c, b: sigs[c], EX, size, rank=rk, stale_of=stale90, seeds=16, **kw)
    print(f"  {tag:34s} 신호 {sum(int(v.sum()) for v in sigs.values()):5d} " + H.line(res), flush=True)


part = os.environ.get("Q_PART", "1")
print(f"== 1시간봉 122회차({part}): RNA 시장 폭 문턱 ({'한투 1년' if src == 'kis' else '야후 3년'} · {len(data)}종목) ==", flush=True)
go("기준(고정 50%)", entry_d())
for name, n, q, mix in R.VARIANTS[part]:
    g = R.make_gate(BR, n, q, mix)
    fx, rn = R.open_share(BR, g, PER[0][1][0][:8] if PER else "20231001")
    go(f"{name}(열린 날 {fx}→{rn}%)", entry_d(g))
print("끝", flush=True)
