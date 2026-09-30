"""1시간봉 48회차(탐색 줄) — 자리 바꾸기에서 '누구를 먼저 비키나'(hlab.simulate stale_key, 판단은 전 봉까지 값).
지금: 손익이 가장 나쁜 것부터. 대안: 가장 오래 든 것부터 · 가장 최근에 산 것부터 · 작은 칸(2칸)부터 · 큰 칸(4칸)부터 ·
정배열 문 매매(추세 문이 아닌 것)부터 · 1시간봉 20봉선 아래로 가장 많이 처진 것부터. 씨앗 8 · 큰 매매 뺀 연수익."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
_E = {}
def e20(c):
    if c not in _E: _E[c] = rna.ema(data[c]["c"], 20)
    return _E[c]
gain = lambda q: data[q["code"]]["c"][q["now"]] / q["price"]
KEYS = {
    "손익 나쁜 것부터(지금)": None,
    "오래 든 것부터": lambda q: q["i"],
    "최근에 산 것부터": lambda q: -q["i"],
    "작은 칸부터": lambda q: (q["칸"], gain(q)),
    "큰 칸부터": lambda q: (-q["칸"], gain(q)),
    "정배열 문 매매부터": lambda q: (0 if (door(ATT[q["code"]][q["i"]]) or "정배열") == "정배열" else 1, gain(q)),
    "20봉선 아래 많이 처진 것부터": lambda q: data[q["code"]]["c"][q["now"]] / e20(q["code"])[q["now"]],
}
sigs = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in data.items()}
def trimmed(key):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, exit_daily, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale, None, key)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for k in vals: vals[k].append(sum(w[k:]) / 1.5)
        got[s] = {k: round(float(np.median(v)), 1) for k, v in vals.items()}
    return got
print("== 1시간봉 48회차 (누구를 먼저 비키나) ==", flush=True)
for tag, key in KEYS.items():
    res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=stale, stale_key=key)
    tr = trimmed(key)
    print(f"  {tag:24s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']} · 반기(씨앗 0) 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
