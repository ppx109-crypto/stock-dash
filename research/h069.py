"""1시간봉 69회차 — 두 후보를 함께: 공시 거르기(67회차) + 센 장만 따라가기(59회차, 폭≥70이면 추세 문 매매를 +13% 대신 고점 15% 되밀림까지).
바탕: 1시간봉 최고 규칙. 씨앗 16 · 큰 매매 뺀 연."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h059.py", encoding="utf-8").read().split('print("== 1시간봉 59회차')[0])
def e_disc(c, b):
    m = np.asarray(e_align_or_noon(c, b), bool).copy(); n = len(b["t"])
    for k in np.flatnonzero(m):
        x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
        if x and (x["자사주20"] or x["희석20"]): m[k] = False
    return m
def trim(entry, ex):
    sg = {c: np.asarray(entry(c, b), bool) for c, b in data.items()}; got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, ex, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("== 1시간봉 69회차 (공시 거르기 + 센 장만 따라가기) ==", flush=True)
for tag, e, ex in (("지금(최고 규칙)", e_align_or_noon, make_exit()), ("공시 거르기", e_disc, make_exit()),
                   ("센 장만 따라가기(폭≥70)", e_align_or_noon, regime_exit(70, "고점 15%")), ("둘 다", e_disc, regime_exit(70, "고점 15%"))):
    res = H.simulate(data, e, ex, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(e, ex)
    print(f"  {tag:24s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
