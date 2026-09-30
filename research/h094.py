"""1시간봉 94회차 — 최종 검토(사용자 "최종인지 검토 후 반영"): 90회차 '같은 봉 후보 순서'의 숫자 고원.
무리 수 2 · 3 · 4 · 5 × 수익 기간 10 · 20 · 40일 × 수급 기간 5 · 10일. 같은 봉 후보끼리 순위 · 무리 안 무작위 · 씨앗 16.
자료는 전 거래일까지(가격 · 수급 · 거래량 파일을 직접, 사는 날 앞만)."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import final_group as FG
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
ROWS = {}
for c in data:
    px = json.load(open(f"price-data/{c}.json", encoding="utf-8"))["closes"]
    vv = json.load(open(f"volume-data/{c}.json", encoding="utf-8"))["날"]
    fl = sorted(FG.flow_rows(c), key=lambda x: x["date"])
    ROWS[c] = ([x[0] for x in px], [float(x[1]) for x in px], [x[0] for x in vv], [float(x[1]) for x in vv], [x["date"] for x in fl], fl)
KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
def raw(c, k, rn, fn):
    b = data[c]; day = b["t"][k + 1][:8] if k + 1 < len(b["t"]) else b["t"][k][:8]
    pd_, pc, vd, vol, fd, fl = ROWS[c]
    i = bisect.bisect_left(pd_, day) - 1; j = bisect.bisect_left(vd, day) - 1; f = bisect.bisect_left(fd, day) - 1
    r = pc[i] / pc[i - rn] - 1 if i >= rn and pc[i - rn] > 0 else np.nan
    av = np.mean(vol[j - 19:j + 1]) if j >= 20 else np.nan
    s = sum((x.get("외국인") or 0) + (x.get("투신") or 0) for x in fl[max(0, f - fn + 1):f + 1]) if f >= fn - 1 else np.nan
    return (s / av if av == av and av > 0 else np.nan, r)
def tiers(rn, fn, n):
    sc = {z: raw(*z, rn, fn) for z in KEYS}
    bybar, T = {}, {}
    for (c, k) in sc: bybar.setdefault(data[c]["t"][k], []).append((c, k))
    for t, L in bybar.items():
        if len(L) == 1: T[L[0]] = n - 1; continue
        tot = np.zeros(len(L))
        for col, good_high in ((0, False), (1, True)):
            v = np.array([sc[z][col] for z in L], float)
            v = np.where(np.isnan(v), np.nanmedian(v) if np.any(~np.isnan(v)) else 0, v)
            q = np.argsort(np.argsort(v)) / (len(v) - 1)
            if not good_high: q = 1 - q
            tot += np.minimum((q * n).astype(int), n - 1)
        for z, x in zip(L, tot): T[z] = int(x)
    return T
def rk_of(T):
    def r(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -T.get((c, k), 0))
    return r
def trim(rk):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = []
        for seed in range(8):
            r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rk, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True); vals.append(sum(w[3:]) / 1.5)
        got[s] = round(float(np.median(vals)), 1)
    return got
print("== 1시간봉 94회차 (같은 봉 후보 순서 숫자 고원 · 최종 검토) ==", flush=True)
grid = [("무리 3 · 수익 20 · 수급 5(90회차)", 20, 5, 3)]
for n in (2, 4, 5): grid.append((f"무리 {n} · 수익 20 · 수급 5", 20, 5, n))
for rn in (10, 40): grid.append((f"무리 3 · 수익 {rn} · 수급 5", rn, 5, 3))
grid.append(("무리 3 · 수익 20 · 수급 10", 20, 10, 3))
for tag, rn, fn, n in grid:
    rk = rk_of(tiers(rn, fn, n))
    res = H.simulate(data, e_align_or_noon, EX, size, rank=rk, stale_of=stale90, seeds=16)
    tr = trim(rk)
    print(f"  {tag:30s} " + H.line(res), flush=True)
    print(f"      큰3건 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
