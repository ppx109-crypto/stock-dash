"""1시간봉 14회차(탐색 줄) — 짧은 판을 가장 센 재료로만(13회차: 한 번 매매의 기대 이익이 비용을 못 넘음).
2회차 사건 연구에서 두 반 모두 센 재료: 추세 문 + 가르침(35봉 +6.46 / +2.62) · A그룹 꼴 + 3일 연속(+1.79 / +2.81).
무엇을: ① 추세 문 + 가르침 ② A그룹 꼴 + 3일 연속 ③ 둘 중 하나 · 사는 때 = 1시간봉 A 정배열 된 봉 다음, 없으면 12시.
파는 법: 짧은 판 몇 가지(13회차에서 나은 쪽: 손절 넓게 · 시간 길게) vs 긴 판(일봉 규칙). 칸 2 · 4."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

def strong(kind):
    def f(x):
        if not x or not x["가르침"]: return False
        d = door(x)
        if kind == "추세": return d == "추세"
        if kind == "3일": return d is not None and x["3일연속"]
        return d == "추세" or (d is not None and x["3일연속"])
    return f
def entry_for(kind):
    f = strong(kind)
    def e(c, b):
        ctx = np.array([f(x) for x in ATT[c]]) & IN[c]
        s = H.states(c, b, "A")["정배열"] == 1
        edge = ctx & s & ~np.r_[False, s[:-1]]
        nn = ctx & hour_is(b, "11")
        days = [t[:8] for t in b["t"]]; seen = set(); m = np.zeros(len(b["t"]), bool)
        for k in range(len(m)):
            if (edge[k] or nn[k]) and days[k] not in seen:
                m[k] = True; seen.add(days[k])
        return m
    return e
def short_exit(bars):
    return lambda c, b, p, k: "all" if k - p["i"] >= bars else 0
def take(pct): return lambda p: (p["price"] * (1 + pct / 100), "all")
def stop(pct): return lambda p: p["price"] * (1 - pct / 100)

print("== 1시간봉 14회차 (짧은 판 · 가장 센 재료만) ==", flush=True)
for kind, name in (("추세", "추세 문 + 가르침"), ("3일", "A그룹 꼴 + 3일 연속"), ("둘", "둘 중 하나")):
    E = entry_for(kind)
    print(f"-- {name}", flush=True)
    res = H.simulate(data, E, exit_daily, size, rank=rank)
    print(f"  {'긴 판(일봉 규칙 파는 법)':26s} " + H.line(res), flush=True)
    for sz in (2, 4):
        for tp, sl, bars in ((3, 5, 21), (5, 5, 21), (8, 5, 21), (5, 5, 35), (8, 5, 35), (13, 5, 60)):
            res = H.simulate(data, E, short_exit(bars), lambda c, b, k, sz=sz: sz, rank=rank,
                             take_of=take(tp), stop_of=stop(sl))
            print(f"  {f'{sz}칸 · +{tp}% · −{sl}% · {bars}봉':26s} " + H.line(res), flush=True)
print("끝", flush=True)
