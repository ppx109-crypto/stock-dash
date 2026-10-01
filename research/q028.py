"""15분봉 27회차 — 후보 문 조건을 1시간봉 · 일봉 연구처럼 바꿔 봄(최종 후보의 사는 때 · 거르기는 그대로).
Q_PART=1: 정배열 문의 시장 폭 문턱 50 → 45 · 40(일봉 새 44회차) · 시장 폭이 5거래일 전보다 5%p 넘게 오르면 50 아래여도 엶(일봉 새 52 · 53회차)
Q_PART=2: 전날 시장 폭 70% 아래인 날만 종목 모음을 시총 150위까지(1시간봉 11 · 42 · 45회차) · 늘 150위
161종목 · 씨앗 16 · 비용 0.30%.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
CTX = W["CTX"]

BR = {}
for c in CTX:
    for d, x in CTX[c].items():
        if x.get("시장폭") is not None:
            BR[d] = x["시장폭"]
BD = sorted(BR)


def recovering(day, n=5, up=5):
    k = BD.index(day) if day in BR else None
    return k is not None and k >= n and BR[BD[k]] - BR[BD[k - n]] >= up


def door2(x, bmin=50, recov=False):
    if not x:
        return None
    if x["추세문"]:
        return "추세"
    if x["정배열"] and 19 <= x["간격"] < 53:
        b = x["시장폭"] or 0
        if b >= bmin or (recov and recovering(x["날"])):
            return "정배열"
    return None


U150 = H.Universe({d: v for d, v in W["ranks"].items() if d >= "20250101"}, top=150)
IN150 = {c: np.array([U150.ok(c, t) for t in b["t"]]) for c, b in data.items()}


def entry4(bmin=50, recov=False, wide=None):
    """22회차 최종 후보와 같되 문 조건 · 종목 모음을 바꿈. wide=None(100위) · 'weak'(전날 폭<70이면 150위) · 'all'(늘 150위)."""
    def f(c, b):
        xs = ATT[c]
        okd = np.array([door2(x, bmin, recov) is not None and x["가르침"] for x in xs])
        if wide is None:
            inside = IN[c]
        elif wide == "all":
            inside = IN150[c]
        else:
            weak = np.array([bool(x) and (x["시장폭"] or 0) < 70 for x in xs])
            inside = IN[c] | (IN150[c] & weak)
        ctx = okd & inside
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


def size2(c, b, k):
    return size(c, b, k)


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 27회차({part}): 후보 문 조건 옮기기 ({len(data)}종목) ==", flush=True)
go("같은 짜임으로 다시 만든 최종 후보(견줌)", entry4())
if part == "1":
    for bm in (45, 40):
        go(f"정배열 문 시장 폭 {bm}%부터", entry4(bmin=bm))
    go("시장 폭 되살아나면 50 아래도 엶", entry4(recov=True))
else:
    go("전날 폭 70% 아래면 150위까지", entry4(wide="weak"))
    go("늘 150위까지", entry4(wide="all"))
print("끝", flush=True)
