"""1시간봉 46회차(탐색 줄) — 자리 바꾸기에서 칸 크기(한 매매에 자금 몇 %). 지금: 센 재료(추세 문 · 3일 연속) 4칸(40%) · 나머지 2칸(20%).
자리 바꾸기로 회전이 빨라지니, 칸을 고르게(3/3 · 2/2) 하거나 약한 것도 크게(4/3 · 4/4) 하면 어떨까. 한 종목 최대 40%(사용자 결정)는 지킴.
씨앗 8 · 큰 매매 뺀 연수익도."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
def sz(strong, weak):
    return lambda c, b, k: strong if size(c, b, k) == 4 else weak
sigs = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in data.items()}
def trimmed(sfn, st):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, exit_daily, sfn, lo, hi, 10, seed, None, rank, H.COST, None, None, st)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for k in vals: vals[k].append(sum(w[k:]) / 1.5)
        got[s] = {k: round(float(np.median(v)), 1) for k, v in vals.items()}
    return got
print("== 1시간봉 46회차 (자리 바꾸기의 칸 크기) ==", flush=True)
for strong, weak in ((4, 2), (3, 3), (2, 2), (4, 3), (4, 4), (3, 2)):
    for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
        f = sz(strong, weak)
        res = H.simulate(data, e_align_or_noon, exit_daily, f, rank=rank, stale_of=st)
        tr = trimmed(f, st)
        print(f"  {f'센 {strong}칸 · 나머지 {weak}칸 · {tag}':26s} " + H.line(res), flush=True)
        print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
