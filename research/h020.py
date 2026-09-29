"""1시간봉 20회차(두 번째 줄) — 비용 민감도: 짧은 판이 지는 까닭이 비용인가.
왕복 비용 0.30%(지금, 넉넉히) → 0.25% · 0.20%(수수료 0.015%×2 + 거래세 약 0.15~0.18% + 미끄러짐 조금).
견줌: 긴 판(지금 규칙) · 짧은 판 A(A그룹 꼴 전부, 2칸 +3% · −5% · 21봉) · 짧은 판 B(센 재료만, 4칸 +8% · −5% · 35봉)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def strong_ctx(x):
    return bool(x and x["가르침"] and (x["추세문"] or (door(x) is not None and x["3일연속"])))
def e_strong(c, b):
    ctx = np.array([strong_ctx(x) for x in ATT[c]]) & IN[c]
    s = H.states(c, b, "A")["정배열"] == 1
    edge = ctx & s & ~np.r_[False, s[:-1]]
    nn = ctx & hour_is(b, "11")
    days = [t[:8] for t in b["t"]]; seen = set(); m = np.zeros(len(b["t"]), bool)
    for k in range(len(m)):
        if (edge[k] or nn[k]) and days[k] not in seen:
            m[k] = True; seen.add(days[k])
    return m
def short_exit(bars): return lambda c, b, p, k: "all" if k - p["i"] >= bars else 0
def take(pct): return lambda p: (p["price"] * (1 + pct / 100), "all")
def stop(pct): return lambda p: p["price"] * (1 - pct / 100)

print("== 1시간봉 20회차 (비용 민감도) ==", flush=True)
for cost in (0.30, 0.25, 0.20):
    print(f"-- 왕복 비용 {cost}%", flush=True)
    res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, cost=cost)
    print(f"  {'긴 판(지금)':26s} " + H.line(res), flush=True)
    res = H.simulate(data, e_align_or_noon, short_exit(21), lambda c, b, k: 2, rank=rank, cost=cost, take_of=take(3), stop_of=stop(5))
    print(f"  {'짧은 판 A(전부 · +3/−5/21)':26s} " + H.line(res), flush=True)
    res = H.simulate(data, e_strong, short_exit(35), lambda c, b, k: 4, rank=rank, cost=cost, take_of=take(8), stop_of=stop(5))
    print(f"  {'짧은 판 B(센 것 · +8/−5/35)':26s} " + H.line(res), flush=True)
print("끝", flush=True)
