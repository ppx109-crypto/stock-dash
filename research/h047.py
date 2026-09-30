"""1시간봉 47회차(탐색 줄) — 자리 바꾸기의 '묵음'을 시장 대비로: 산 뒤 코스피보다 X%p 못한 매매만 비킴.
지금 묵음(절대: 7봉 · +4% 미만)은 약한 장에서 시장보다 잘 버티는 종목도 비키게 함 → 시장 대비로 고르면 반기 흔들림이 줄까.
시장 대비 = (종목 전 봉 종가 ÷ 산 값) − (코스피 같은 시각 종가 ÷ 산 봉 시각 코스피) (%p). 코스피 1시간봉은 그 시각까지 닫힌 봉만.
문턱 X = 0 · 2 · 4 · 6 × 봉 7 · 10, 그리고 '절대 +4% 미만 그리고 시장 대비 < 0' 둘 다. 씨앗 8 · 큰 매매 뺀 연수익도."""
import sys, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
K = H.load(["KOSPI"])["KOSPI"]
def kospi_at(T):
    k = bisect.bisect_right(K["t"], T) - 1
    return K["c"][k] if k >= 0 else np.nan
def rel(p):
    b = data[p["code"]]
    own = (b["c"][p["now"]] / p["price"] - 1) * 100
    k0 = kospi_at(b["t"][p["i"] - 1] if p["i"] > 0 else b["t"][p["i"]])     # 산 값 = i봉 시가 → 그 앞 봉 종가 시각의 코스피
    k1 = kospi_at(b["t"][p["now"]])
    return own - (k1 / k0 - 1) * 100 if k0 == k0 and k1 == k1 else own
def st_abs(n, x): return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
def st_rel(n, x): return lambda p: (p["now"] - p["i"] >= n) and rel(p) < x
def st_both(n): return lambda p: st_abs(n, 4)(p) and rel(p) < 0
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
print("== 1시간봉 47회차 (묵음을 시장 대비로) ==", flush=True)
cases = [("지금 규칙", None), ("절대 7봉 · <4%(후보)", st_abs(7, 4))]
for n in (7, 10):
    for x in (0, 2, 4, 6):
        cases.append((f"시장 대비 {n}봉 · <{x}%p", st_rel(n, x)))
    cases.append((f"절대 <4% 그리고 시장 대비 <0 · {n}봉", st_both(n)))
for tag, st in cases:
    res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st)
    tr = trimmed(st)
    print(f"  {tag:30s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']} · 반기(씨앗 0) 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
