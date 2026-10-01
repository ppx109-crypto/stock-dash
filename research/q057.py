"""15분봉 57회차(세 갈래 공통 G11 · RNA 시장 폭 문턱 · 15분봉) — 정배열 문의 '시장 폭 50% 이상'을 '앞 n일 q분위 이상'으로(research/rnabr.py).
기준 = 22회차 후보 · 160종목 · 씨앗 16 · 두 반. Q_PART=1 · 2."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
import rnabr as R
CTX = W["CTX"]
BR = {}
for c in CTX:
    for d, x in CTX[c].items():
        if x.get("시장폭") is not None:
            BR[d] = x["시장폭"]


def door2(x, gate=None):
    if not x:
        return None
    if x["추세문"]:
        return "추세"
    ok = (x["시장폭"] or 0) >= 50 if gate is None else gate(x["날"], x["시장폭"])
    if x["정배열"] and 19 <= x["간격"] < 53 and ok:
        return "정배열"
    return None


def entry_g(gate=None):
    def f(c, b):
        xs = ATT[c]
        ctx = np.array([door2(x, gate) is not None and x["가르침"] for x in xs]) & IN[c]
        s = H.states(c, b, SPAN)["정배열"] == 1
        al = ctx & s & ~np.r_[False, s[:-1]]
        dr, mk = nan0(DR[c]), nan0(MKT[c])
        good = ~(dr > 0.02) & ~(mk < -0.01)
        nn = ctx & (HH[c] == "1045") & good
        al &= good
        m, seen = np.zeros(len(al), bool), set()
        for k in np.flatnonzero(al | nn):
            if DAY[c][k] not in seen:
                m[k] = True
                seen.add(DAY[c][k])
        return m
    return f


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 57회차({part}): RNA 시장 폭 문턱 ({len(data)}종목) ==", flush=True)
go("같은 짜임으로 다시 만든 최종 후보(고정 50%)", entry_g())
for name, n, q, mix in R.VARIANTS[part]:
    g = R.make_gate(BR, n, q, mix)
    fx, rn = R.open_share(BR, g, "20250917")
    go(f"{name}(열린 날 {fx}→{rn}%)", entry_g(g))
print("끝", flush=True)
