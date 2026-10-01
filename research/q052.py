"""15분봉 49회차(세 갈래 공통 G3 · G4 · 15분봉). 기준 = 22회차 후보 · 161종목 · 씨앗 16.
Q_PART=1(G3): 목표가 내림(45일) 거르기 더함 / Q_PART=2(G4): 3일 연속 4칸 → 3칸 · 정배열 2칸 → 3칸 · 추세 4칸 → 3칸."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('\npart = os.environ')[0])
import tgcut

FIN = entry3(al_mkt=-0.01)


def mat(c, b, k):
    return ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]


def with_tg(c, b):
    m = FIN(c, b).copy()
    for k in np.flatnonzero(m):
        x = mat(c, b, k)
        if x and tgcut.target_cut(c, x["날"]):
            m[k] = False
    return m


def sz(trend=4, steady=4, align=2):
    def f(c, b, k):
        x = mat(c, b, k)
        if x and x["추세문"]:
            return trend
        return steady if x and x["3일연속"] else align
    return f


def run_s(tag, fn, s=size):
    sg = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    res = M.simulate(data, lambda c, b: sg[c], exit_rule, s, rank=rank_plus(tiers(sg)), stale_of=stale90, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 49회차({part}) ({len(data)}종목) ==", flush=True)
run_s("기준(22회차 후보)", FIN)
if part == "1":
    run_s("목표가 내림 거르기 더함", with_tg)
else:
    run_s("3일 연속 3칸", FIN, sz(steady=3))
    run_s("정배열 기본 3칸", FIN, sz(align=3))
    run_s("추세 3칸", FIN, sz(trend=3))
print("끝", flush=True)
