"""1시간봉 25회차(탐색 줄) — 약한 장에서만 쓰는 짧은 판(사용자 약한 장 요청 + 빠른 회전).
지금 규칙은 시장 폭 50% 아래면 정배열 문이 닫혀 돈이 쉼. 그때만(전날 시장 폭 < X) 센 종목을 짧게 돌림:
센 종목 = 추세 문 + 가르침, 또는 정배열(간격 19~53, 시장 폭 무시) + 가르침 + 3일 연속.
짧은 판 = 1시간봉 A 정배열 된 봉 다음(없으면 12시) · 반 +8% 지정가 · 반 20봉선 따라가기 · −5% 장중 손절 · 4칸(또는 2칸).
긴 판(지금 규칙)은 그대로 같은 계좌에서 돌고, 약한 장 짧은 판 매매만 짧게 팜."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

_E = {}
def ema20(c, b):
    if c not in _E: _E[c] = rna.ema(b["c"], 20)
    return _E[c]
def weak_strong(x, below):
    if not x or (x["시장폭"] if x["시장폭"] is not None else 100) >= below or not x["가르침"]: return False
    if x["추세문"]: return True
    return bool(x["정배열"] and 19 <= x["간격"] < 53 and x["3일연속"])
TAG = {}
def entries(below):
    def e(c, b):
        base = e_align_or_noon(c, b).copy()
        a = ATT[c]
        ws = np.array([weak_strong(x, below) for x in a]) & IN[c]
        s = H.states(c, b, "A")["정배열"] == 1
        edge = s & ~np.r_[False, s[:-1]]
        days = [t[:8] for t in b["t"]]; seen = {days[k] for k in np.flatnonzero(base)}
        for k in range(len(base)):
            if ws[k] and days[k] not in seen and (edge[k] or b["t"][k][8:] == "11") and not ok(a[k]):
                base[k] = True; seen.add(days[k])
                TAG[(c, k + 1)] = "short"
        return base
    return e
def sz(short_size):
    def f(c, b, k):
        return short_size if TAG.get((c, k + 1)) == "short" else size(c, b, k)
    return f
def exit_mix(c, b, p, k):
    if TAG.get((c, p["i"])) == "short":
        if p["칸"] < p["처음칸"]:
            return "all" if (b["c"][k] < ema20(c, b)[k] or k - p["i"] >= 70) else 0
        return "all" if k - p["i"] >= 35 else 0
    return exit_daily(c, b, p, k)
take_half = lambda p: ((p["price"] * 1.08, p["처음칸"] // 2) if TAG.get((p["code"], p["i"])) == "short" and p["칸"] == p["처음칸"] else (None, 0))
stop5 = lambda p: p["price"] * 0.95 if TAG.get((p["code"], p["i"])) == "short" else None

print("== 1시간봉 25회차 (약한 장에서만 짧은 판) ==", flush=True)
print(f"  {'지금(긴 판만)':30s} " + H.line(H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)), flush=True)
for below in (50, 60, 70):
    for s_ in (4, 2):
        TAG.clear()
        res = H.simulate(data, entries(below), exit_mix, sz(s_), rank=rank, take_of=take_half, stop_of=stop5)
        n_short = {side: sum(1 for t in res[side]["목록"] if TAG.get((t["code"], data[t["code"]]["t"].index(t["산 때"])) ) == "short") for side in ("앞", "뒤")}
        print(f"  {f'시장 폭 {below}% 아래 · 짧은 판 {s_}칸':30s} " + H.line(res) + f" · 짧은 판 매매 {n_short}", flush=True)
        print(f"      반기(씨앗 0): 앞 {res['앞']['반기']} · 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
