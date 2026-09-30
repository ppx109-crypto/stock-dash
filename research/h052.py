"""1시간봉 52회차(탐색 줄) — 자리 바꾸기를 약한 장에서만(전 거래일 시장 폭 < X%일 때만 묵음을 비킴).
34회차: 센 장(뒤)에선 비킨 매매가 그대로 두었으면 +7%로 끝났음 · 약한 장(앞)에선 비킨 매매가 어차피 제자리. → 센 장에선 끄면 두 반 모두 나을까.
시장 폭은 비킬 매매의 그 봉 재료(전 거래일 값). 문턱 50 · 60 · 70 · 80 · 90 · 늘. 씨앗 8 · 큰 매매 뺀 연수익."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def stale_weak(th):
    def f(p):
        if not ((p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4): return False
        x = ATT[p["code"]][p["now"]]
        br = x["시장폭"] if x and x["시장폭"] is not None else 100
        return br < th
    return f
sigs = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in data.items()}
def trimmed(st):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, exit_daily, size, lo, hi, 10, seed, None, rank, H.COST, None, None, st)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for k in vals: vals[k].append(sum(w[k:]) / 1.5)
        got[s] = {k: round(float(np.median(v)), 1) for k, v in vals.items()}
    return got
print("== 1시간봉 52회차 (약한 장에서만 자리 바꾸기) ==", flush=True)
for tag, st in [("지금 규칙", None)] + [(f"폭<{th}일 때만 바꾸기", stale_weak(th)) for th in (50, 60, 70, 80, 90)] + [("늘 바꾸기", stale_weak(101))]:
    res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st)
    tr = trimmed(st)
    print(f"  {tag:18s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']} · 반기(씨앗 0) 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
