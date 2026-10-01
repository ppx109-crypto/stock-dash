"""15분봉 31회차 — 1시간봉 15회차 '막 힘이 붙는 봉'(돌파 + 거래량)을 15분봉 최종 후보에 옮김.
돌파 = 이 봉 종가가 앞 26봉(약 하루) 최고가 위 · 거래량 = 같은 시각 거래량 배수(m15feat.relvol) 2배 이상(봉이 닫힌 때까지 값만).
Q_PART=1: 돌파 + 거래량 봉도 사는 신호로 더함(거르기는 그대로) · 돌파 + 거래량이면 4칸(1시간봉 15회차 '크기로 쓰기')
Q_PART=2: 돌파 + 거래량을 같은 시각 순서 맨 앞에 · 돌파 + 거래량 3배면 4칸
161종목 · 씨앗 16.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])


def breakout(b, n=26):
    h, c = b["h"], b["c"]
    prev = np.array([h[max(0, k - n):k].max() if k >= n else np.inf for k in range(len(c))])
    return c > prev


BO = {c: breakout(b) for c, b in data.items()}
BV = {c: BO[c] & (np.nan_to_num(RV[c], nan=0.0) >= 2) for c in data}
BV3 = {c: BO[c] & (np.nan_to_num(RV[c], nan=0.0) >= 3) for c in data}


def with_breakout(c, b):
    dr, mk = nan0(DR[c]), nan0(MKT[c])
    good = ~(dr > 0.02) & ~(mk < -0.01)
    extra = ctx_now(c, b) & BV[c] & good
    base = SGF[c] | extra
    m, seen = np.zeros(len(base), bool), set()
    for k in np.flatnonzero(base):
        if DAY[c][k] not in seen:
            m[k] = True
            seen.add(DAY[c][k])
    return m


def size_bo(mask):
    def f(c, b, k):
        s = size(c, b, k)
        return 4 if mask[c][k] else s
    return f


def go3(tag, sig=None, sz=size, rk=None):
    sg = SGF if sig is None else {c: np.asarray(sig(c, b), bool) for c, b in data.items()}
    rank = rk or (RKF if sig is None else rank_plus(tiers(sg)))
    res = M.simulate(data, lambda c, b: sg[c], exit_rule, sz, rank=rank, stale_of=stale90, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)


def rank_bo(c, b, k):
    return (0 if BV[c][k] else 1,) + RKF(c, b, k)


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 31회차({part}): 돌파 + 거래량 옮기기 ({len(data)}종목) ==", flush=True)
if part == "1":
    go3("돌파 + 거래량 2배 봉도 삼", with_breakout)
    go3("돌파 + 거래량 2배면 4칸", sz=size_bo(BV))
else:
    go3("돌파 + 거래량을 같은 시각 맨 앞에", rk=rank_bo)
    go3("돌파 + 거래량 3배면 4칸", sz=size_bo(BV3))
print("끝", flush=True)
