"""1시간봉 53회차(확인 줄) — 52회차 '시장 폭 90% 미만일 때만 자리 바꾸기'(아주 센 날은 묵음도 그대로 둠)가 진짜인지: 씨앗 16 + 봉 값 잡음 세계 6개.
견줌: 지금 규칙 · 늘 자리 바꾸기 · 폭<90일 때만 자리 바꾸기(폭은 비킬 매매의 그 봉 재료 = 전 거래일 값)."""
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
def stale90(D):
    base = stale(D)
    def f(p):
        if not base(p): return False
        x = ATT[p["code"]][p["now"]]
        return (x["시장폭"] if x and x["시장폭"] is not None else 100) < 90
    return f
print("== 1시간봉 53회차 (폭<90일 때만 자리 바꾸기 · 씨앗 16 · 잡음 세계) ==", flush=True)
for tag, st in (("지금 규칙", None), ("늘 바꾸기", stale), ("폭<90일 때만 바꾸기", stale90)):
    res = H.simulate(REAL, e_align_or_noon, exit_daily, size, rank=rank, seeds=16, stale_of=st(REAL) if st else None)
    print(f"  {tag:24s} " + H.line(res), flush=True)
rows = {k: [] for k in ("지금", "늘 바꾸기", "폭<90만")}
for w in range(1, 7):
    D = noisy(w); data = D; H._ST.clear()
    a = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4)
    b = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4, stale_of=stale(D))
    c = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4, stale_of=stale90(D))
    for k, r in (("지금", a), ("늘 바꾸기", b), ("폭<90만", c)):
        rows[k].append((r["앞"]["연"], r["뒤"]["연"]))
    print(f"  잡음 세계 {w}: 지금 {a['앞']['연']}/{a['뒤']['연']} · 늘 바꾸기 {b['앞']['연']}/{b['뒤']['연']} · 폭<90만 {c['앞']['연']}/{c['뒤']['연']}", flush=True)
for k, v in rows.items():
    v = np.array(v)
    print(f"  {k}: 앞 가운데 {np.median(v[:, 0]):.1f} ({v[:, 0].min():.1f}~{v[:, 0].max():.1f}) · 뒤 가운데 {np.median(v[:, 1]):.1f} ({v[:, 1].min():.1f}~{v[:, 1].max():.1f})", flush=True)
a, b, c = (np.array(rows[k]) for k in ("지금", "늘 바꾸기", "폭<90만"))
print(f"  폭<90만이 늘 바꾸기보다 나은 세계: 앞 {int((c[:, 0] > b[:, 0]).sum())}/6 · 뒤 {int((c[:, 1] > b[:, 1]).sum())}/6 · 지금 규칙보다: 앞 {int((c[:, 0] > a[:, 0]).sum())}/6 · 뒤 {int((c[:, 1] > a[:, 1]).sum())}/6", flush=True)
print("끝", flush=True)
