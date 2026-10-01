"""1시간봉 109회차(세 갈래 공통 G6 · 1시간봉) — 정배열 쪽 파는 숫자: 손절 −10% · 이익 지키기(+8% → +1%). 기준 = 94회차 · 야후 · 씨앗 16.
Q_PART=1: 손절 −8 · −12% / Q_PART=2: 이익 지키기 (6 → 1) · (10 → 2) · (8 → 3)."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
SG0 = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
sigs = SG0
KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
RK0 = rk_of(tiers(20, 5, 3))


def ex2(stop=10, keep=(8, 1)):
    def f(c, b, p, k):
        kind = door(ATT[c][p["i"]]) or "정배열"
        if kind == "추세":
            return EX(c, b, p, k)
        now = (b["c"][k] / p["price"] - 1) * 100
        pk = (p["peak"] / p["price"] - 1) * 100
        if now <= -stop:
            return "all"
        if keep and pk >= keep[0] and now <= keep[1]:
            return "all"
        if k + 1 < len(b["t"]):
            nx = ATT[c][k + 1]
            if nx is not None and not nx["정배열"]:
                return "all"
        return 0
    return f


def go(tag, ex):
    res = H.simulate(data, lambda c, b: SG0[c], ex, size, rank=RK0, stale_of=stale90, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)


part = os.environ.get("Q_PART", "1")
print(f"== 1시간봉 109회차({part}): 정배열 쪽 파는 숫자 ({len(data)}종목) ==", flush=True)
go("기준(손절 −10 · 지키기 8 → 1)", ex2())
if part == "1":
    for s in (8, 12):
        go(f"손절 −{s}%", ex2(stop=s))
else:
    for kp in ((6, 1), (10, 2), (8, 3)):
        go(f"이익 지키기 {kp[0]} → {kp[1]}", ex2(keep=kp))
print("끝", flush=True)
