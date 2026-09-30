"""1시간봉 74회차(확인 줄) — 희석 공시 거르기(72회차 후보)가 봉 값 잡음에도 버티나: 씨앗 16 + 잡음 세계 6개(시가 · 종가를 0.3%, 09시 시가 0.8% 흔듦, 53회차와 같음).
견줌: 최고 규칙(자리 바꾸기 폭<90) vs 최고 + 희석 공시 거르기(20일)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h053.py", encoding="utf-8").read().split('print("== 1시간봉 53회차')[0])
def e_dil(c, b):
    m = np.asarray(e_align_or_noon(c, b), bool).copy(); n = len(b["t"])
    for k in np.flatnonzero(m):
        x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
        if x and x["희석20"]: m[k] = False
    return m
print("== 1시간봉 74회차 (희석 공시 거르기 · 잡음 세계) ==", flush=True)
for tag, e in (("최고", e_align_or_noon), ("최고 + 희석 공시 거르기", e_dil)):
    res = H.simulate(REAL, e, exit_daily, size, rank=rank, seeds=16, stale_of=stale90(REAL))
    print(f"  {tag:24s} " + H.line(res), flush=True)
rows = {k: [] for k in ("최고", "희석 거르기")}
for w in range(1, 7):
    D = noisy(w); data = D; H._ST.clear()
    a = H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, seeds=4, stale_of=stale90(D))
    H._ST.clear()
    b = H.simulate(D, e_dil, exit_daily, size, rank=rank, seeds=4, stale_of=stale90(D))
    rows["최고"].append((a["앞"]["연"], a["뒤"]["연"], a["앞"]["골"], a["뒤"]["골"])); rows["희석 거르기"].append((b["앞"]["연"], b["뒤"]["연"], b["앞"]["골"], b["뒤"]["골"]))
    print(f"  잡음 세계 {w}: 최고 {a['앞']['연']}/{a['뒤']['연']} · 희석 거르기 {b['앞']['연']}/{b['뒤']['연']}", flush=True)
for k, v in rows.items():
    v = np.array(v)
    print(f"  {k}: 앞 가운데 {np.median(v[:, 0]):.1f} ({v[:, 0].min():.1f}~{v[:, 0].max():.1f}) · 뒤 가운데 {np.median(v[:, 1]):.1f} ({v[:, 1].min():.1f}~{v[:, 1].max():.1f}) · 골 가운데 {np.median(v[:, 2]):.1f} / {np.median(v[:, 3]):.1f}", flush=True)
a, b = np.array(rows["최고"]), np.array(rows["희석 거르기"])
print(f"  희석 거르기가 나은 세계: 앞 {int((b[:, 0] > a[:, 0]).sum())}/6 · 뒤 {int((b[:, 1] > a[:, 1]).sum())}/6", flush=True)
print("끝", flush=True)
