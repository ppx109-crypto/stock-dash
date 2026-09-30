"""1시간봉 39회차(확인 줄) — 봉 값 흔들림에 버티나(38회차: 야후 09시 시가가 한투와 ±1% 다름 · 한 건의 운이 결과를 크게 바꿈).
모든 봉의 시가 · 종가에 작은 잡음(가운데 0.3% · 09시 시가는 0.8%)을 넣은 세계 6개에서 지금 규칙 · 자리 바꾸기를 다시 돌려
연수익이 얼마나 흔들리는지, 자리 바꾸기가 지금 규칙보다 나은 세계가 몇 개인지 봄. 잡음은 봉 범위(저가~고가) 안으로 자름."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
REAL = data
def noisy(seed):
    rng = np.random.default_rng(seed); out = {}
    for c, b in REAL.items():
        n = len(b["t"]); first = np.array([t[8:] == "09" for t in b["t"]])
        o = b["o"] * np.exp(rng.normal(0, np.where(first, 0.008, 0.003), n))
        cc = b["c"] * np.exp(rng.normal(0, 0.003, n))
        out[c] = {"t": b["t"], "o": np.clip(o, b["l"], b["h"]), "c": np.clip(cc, b["l"], b["h"]), "h": b["h"], "l": b["l"], "v": b["v"]}
    return out
stale = lambda D: (lambda p: (p["now"] - p["i"] >= 7) and (D[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4)
print("== 1시간봉 39회차 (봉 값 흔들림에 버티나) ==", flush=True)
res = {"지금": [], "바꾸기": []}
for w in range(7):
    D = REAL if w == 0 else noisy(w)
    data = D; H._ST.clear()
    a = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4)
    b = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4, stale_of=stale(D))
    res["지금"].append((a["앞"]["연"], a["뒤"]["연"])); res["바꾸기"].append((b["앞"]["연"], b["뒤"]["연"]))
    print(f"  {'진짜 봉' if w == 0 else f'잡음 세계 {w}':10s} 지금 앞 {a['앞']['연']:>6} 뒤 {a['뒤']['연']:>7} 골 {a['앞']['골']}/{a['뒤']['골']} | 바꾸기 앞 {b['앞']['연']:>6} 뒤 {b['뒤']['연']:>7} 골 {b['앞']['골']}/{b['뒤']['골']}", flush=True)
for k, v in res.items():
    v = np.array(v[1:])
    print(f"  {k} 잡음 세계 6개: 앞 가운데 {np.median(v[:, 0]):.1f} (범위 {v[:, 0].min():.1f}~{v[:, 0].max():.1f}) · 뒤 가운데 {np.median(v[:, 1]):.1f} (범위 {v[:, 1].min():.1f}~{v[:, 1].max():.1f})", flush=True)
a = np.array(res["지금"][1:]); b = np.array(res["바꾸기"][1:])
print(f"  바꾸기가 나은 세계: 앞 {int((b[:, 0] > a[:, 0]).sum())}/6 · 뒤 {int((b[:, 1] > a[:, 1]).sum())}/6", flush=True)
print("끝", flush=True)
