"""15분봉 48회차(세 갈래 공통 G1 · G2 · 15분봉) — 정배열 문 숫자: 간격 범위(19 ~ 53%) · 시장 폭 문턱(50%). 기준 = 22회차 후보 · 161종목 · 씨앗 16.
Q_PART=1: 간격 15 ~ 53 · 19 ~ 45 · 19 ~ 60 · 25 ~ 53 / Q_PART=2: 시장 폭 45 · 55 · 60%."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('\npart = os.environ')[0])


def door2(x, lo=19, hi=53, bmin=50):
    if not x:
        return None
    if x["추세문"]:
        return "추세"
    if x["정배열"] and lo <= x["간격"] < hi and (x["시장폭"] or 0) >= bmin:
        return "정배열"
    return None


def entry_d(**kw):
    def f(c, b):
        ctx = np.array([bool(x) and door2(x, **kw) is not None and x["가르침"] for x in ATT[c]]) & IN[c]
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
print(f"== 15분봉 48회차({part}): 정배열 문 숫자 ({len(data)}종목) ==", flush=True)
run3("기준(간격 19 ~ 53 · 폭 50)", entry_d())
if part == "1":
    for lo, hi in ((15, 53), (19, 45), (19, 60), (25, 53)):
        run3(f"간격 {lo} ~ {hi}", entry_d(lo=lo, hi=hi))
else:
    for bm in (45, 55, 60):
        run3(f"시장 폭 {bm}%", entry_d(bmin=bm))
print("끝", flush=True)
