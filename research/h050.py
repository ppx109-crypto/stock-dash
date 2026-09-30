"""1시간봉 50회차(확인 줄) — 48회차 '가장 최근에 산 묵음부터 비킴'이 진짜인지: 씨앗 16 + 봉 값 잡음 세계 6개(39회차 방식).
견줌: 지금 규칙 · 자리 바꾸기(손익 나쁜 것부터) · 자리 바꾸기(최근에 산 것부터)."""
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
def stale(D): return lambda p: (p["now"] - p["i"] >= 7) and (D[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
recent = lambda q: -q["i"]
print("== 1시간봉 50회차 (최근에 산 것부터 비킴 · 씨앗 16 · 잡음 세계) ==", flush=True)
for tag, st, key in (("지금 규칙", False, None), ("바꾸기 · 손익 나쁜 것부터", True, None), ("바꾸기 · 최근에 산 것부터", True, recent)):
    res = H.simulate(REAL, e_align_or_noon, exit_daily, size, rank=rank, seeds=16, stale_of=stale(REAL) if st else None, stale_key=key)
    print(f"  {tag:24s} " + H.line(res), flush=True)
rows = {k: [] for k in ("지금", "나쁜 것부터", "최근부터")}
for w in range(1, 7):
    D = noisy(w); data = D; H._ST.clear()
    a = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4)
    b = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4, stale_of=stale(D))
    c = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4, stale_of=stale(D), stale_key=recent)
    for k, r in (("지금", a), ("나쁜 것부터", b), ("최근부터", c)):
        rows[k].append((r["앞"]["연"], r["뒤"]["연"]))
    print(f"  잡음 세계 {w}: 지금 {a['앞']['연']}/{a['뒤']['연']} · 나쁜 것부터 {b['앞']['연']}/{b['뒤']['연']} · 최근부터 {c['앞']['연']}/{c['뒤']['연']}", flush=True)
for k, v in rows.items():
    v = np.array(v)
    print(f"  {k}: 앞 가운데 {np.median(v[:, 0]):.1f} ({v[:, 0].min():.1f}~{v[:, 0].max():.1f}) · 뒤 가운데 {np.median(v[:, 1]):.1f} ({v[:, 1].min():.1f}~{v[:, 1].max():.1f})", flush=True)
a, b, c = (np.array(rows[k]) for k in ("지금", "나쁜 것부터", "최근부터"))
print(f"  최근부터가 나쁜 것부터보다 나은 세계: 앞 {int((c[:, 0] > b[:, 0]).sum())}/6 · 뒤 {int((c[:, 1] > b[:, 1]).sum())}/6 · 지금 규칙보다: 앞 {int((c[:, 0] > a[:, 0]).sum())}/6 · 뒤 {int((c[:, 1] > a[:, 1]).sum())}/6", flush=True)
print("끝", flush=True)
