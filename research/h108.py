"""1시간봉 108회차(세 갈래 공통 G3 · G4 · 1시간봉). 기준 = 94회차 · 야후 · 씨앗 16.
Q_PART=1(G3): 목표가 내림(45일) 거르기 더함 / Q_PART=2(G4): 3일 연속 4칸 → 3칸 · 정배열 2칸 → 3칸 · 추세 4칸 → 3칸."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
import tgcut


def run_s(tag, fn, sz):
    global sigs, KEYS
    sigs = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
    res = H.simulate(data, lambda c, b: sigs[c], EX, sz, rank=rk_of(tiers(20, 5, 3)), stale_of=stale90, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)


def mat(c, b, k):
    return ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]


def with_tg(c, b):
    m = entry_f()(c, b).copy()
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


part = os.environ.get("Q_PART", "1")
print(f"== 1시간봉 108회차({part}) ({len(data)}종목) ==", flush=True)
run_s("기준(94회차)", entry_f(), size)
if part == "1":
    run_s("목표가 내림 거르기 더함", with_tg, size)
else:
    run_s("3일 연속 3칸", entry_f(), sz(steady=3))
    run_s("정배열 기본 3칸", entry_f(), sz(align=3))
    run_s("추세 3칸", entry_f(), sz(trend=3))
print("끝", flush=True)
