"""15분봉 58회차(세 갈래 공통 G12 · 15분봉) — 정배열 손절 고정 10% → k × 변동성(산 날 전 거래일 · research/volstop.py).
기준 = 22회차 후보 · 160종목 · 씨앗 16 · 두 반. Q_PART=1 · 2."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
exec("def make_exit" + open("/home/user/stock-dash/research/q003.py", encoding="utf-8").read().split("def make_exit", 1)[1].split("def run(tag")[0])
import volstop as VS
BASE = make_exit()


def ex_v(kk, lo, hi):
    def f(c, b, p, k):
        kind = door(ATT[c][p["i"]]) or "정배열"
        if kind == "추세":
            return BASE(c, b, p, k)
        now = (b["c"][k] / p["price"] - 1) * 100
        if now <= -VS.stop_pct(VS.vol_before(c, b["t"][p["i"]][:8]), kk, lo, hi):
            return "all"
        if (p["peak"] / p["price"] - 1) * 100 >= 8 and now <= 1:
            return "all"
        if k + 1 < len(b["t"]):
            nx = ATT[c][k + 1]
            if nx is not None and not nx["정배열"]:
                return "all"
        return 0
    return f


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 58회차({part}): 정배열 손절을 변동성 배수로 ({len(data)}종목) ==", flush=True)
go("기준(고정 10%)", ex=ex_v(0, 10, 10))
for name, kk, lo, hi in VS.VARIANTS[part]:
    go(name, ex=ex_v(kk, lo, hi))
print("끝", flush=True)
