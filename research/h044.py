"""1시간봉 44회차(확인 줄) — 자리 바꾸기 후보도 '큰 매매 몇 건'에 기대나(43회차에서 넓히기가 그랬음).
씨앗 8개마다 지금 규칙 · 자리 바꾸기의 연수익을 '가장 큰 매매 k건(k = 0 · 1 · 2 · 3 · 5)을 뺀 값'으로 다시 셈 → 가운데 값 비교."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
sigs = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in data.items()}
YEARS = {"앞": 1.5, "뒤": 1.5}
print("== 1시간봉 44회차 (자리 바꾸기도 큰 매매 몇 건에 기대나) ==", flush=True)
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    out = {}
    for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
        vals = {k: [] for k in (0, 1, 2, 3, 5)}
        for seed in range(8):
            r = H._one_run(data, sigs, exit_daily, size, lo, hi, 10, seed, None, rank, H.COST, None, None, st)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for k in vals:
                vals[k].append(sum(w[k:]) / YEARS[s])
        out[tag] = {k: float(np.median(v)) for k, v in vals.items()}
        print(f"  {s} {tag:8s} " + " · ".join(f"큰 {k}건 뺌 {v:6.1f}" for k, v in out[tag].items()), flush=True)
    print(f"  {s} 차이(바꾸기 − 지금) " + " · ".join(f"큰 {k}건 뺌 {out['자리 바꾸기'][k] - out['지금 규칙'][k]:+6.1f}" for k in out["지금 규칙"]), flush=True)
print("끝", flush=True)
