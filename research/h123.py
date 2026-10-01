"""1시간봉 123회차(세 갈래 공통 G12 · 1시간봉) — 정배열 손절 고정 10% → k × 변동성(산 날 전 거래일 · research/volstop.py).
기준 = 94회차 · 씨앗 16. Q_SRC=yahoo(3년) · kis(한투 1년 · 15분봉을 묶음). Q_PART=1 · 2."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import hlab as H
import kis1h
import volstop as VS

src = os.environ.get("Q_SRC", "yahoo")
PER = kis1h.use() if src == "kis" else None
exec(open("/home/user/stock-dash/research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
SG = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
sigs = SG
KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(SG[c])]
rk = rk_of(tiers(20, 5, 3))
BASE = EX


def ex_v(kk, lo, hi):
    def f(c, b, p, k):
        kind = door(ATT[c][p["i"]]) or "정배열"
        if kind == "추세":
            return BASE(c, b, p, k)
        now = (b["c"][k] / p["price"] - 1) * 100
        pk = (p["peak"] / p["price"] - 1) * 100
        if now <= -VS.stop_pct(VS.vol_before(c, b["t"][p["i"]][:8]), kk, lo, hi):
            return "all"
        if pk >= 8 and now <= 1:
            return "all"
        if k + 1 < len(b["t"]):
            nx = ATT[c][k + 1]
            if nx is not None and not nx["정배열"]:
                return "all"
        return 0
    return f


def go(tag, ex):
    kw = {"periods": PER} if PER else {}
    res = H.simulate(data, lambda c, b: SG[c], ex, size, rank=rk, stale_of=stale90, seeds=16, **kw)
    print(f"  {tag:30s} " + H.line(res), flush=True)


part = os.environ.get("Q_PART", "1")
print(f"== 1시간봉 123회차({part}): 정배열 손절을 변동성 배수로 ({'한투 1년' if src == 'kis' else '야후 3년'} · {len(data)}종목) ==", flush=True)
go("기준(고정 10%)", ex_v(0, 10, 10))
for name, kk, lo, hi in VS.VARIANTS[part]:
    go(name, ex_v(kk, lo, hi))
print("끝", flush=True)
