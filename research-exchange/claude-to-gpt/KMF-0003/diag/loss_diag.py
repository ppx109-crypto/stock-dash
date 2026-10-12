"""KMF-0003 준비 · 기본 봇 1번(ORB-1 60분 · 하루 2번 · 반대 범위 멈춤) 손실 분석(판정 밖 · 개발 2026-01 ~ 05만 · 06-01부터 안 읽음).
무엇을 봄: 멈춘 날의 특징(범위 폭 · 들어간 시각 · 방향 · 갭 · 전날 흐름) · 들어간 뒤 가장 불리했던 폭(MAE)과 그 뒤 결과."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import kmf as K, kmf2 as K2
rows = K._rows_before(K.VAL[0])
cfg = {"bot": "ORB1", "or": 60, "max_entries": 2, "stop": "range"}
want = K2.signals(rows, cfg)
days, trades = K.simulate(rows, want)
byday = defaultdict(list)
for r in rows:
    byday[r[0]].append(r)
ds = sorted(d for d in byday if K.DEV[0] <= d <= K.DEV[1])
prev_close = {}
for a, b in zip(sorted(byday), sorted(byday)[1:]):
    prev_close[b] = byday[a][-1][5]
info = {}
for d in ds:
    rs = byday[d]; st = rs[0][1]
    rng = [r for r in rs if r[1] < st + 60]
    hi, lo = max(r[3] for r in rng), min(r[4] for r in rng)
    first = next(((r[1], 1 if r[5] > hi else -1) for r in rs if r[1] >= st + 60 and (r[5] > hi or r[5] < lo) and r[1] <= K.ENTRY_TO), None)
    # 들어간 뒤 가장 불리했던 폭(MAE · 첫 들기 · 그날 끝까지 · 멈춤 무시) · 장 끝 손익(멈춤 무시)
    mae = eod = None
    if first:
        k = next(i for i, r in enumerate(rs) if r[1] == first[0])
        if k + 1 < len(rs):
            ent = rs[k + 1][2]; dirn = first[1]
            path = rs[k + 1:]
            mae = min(dirn * ((r[4] if dirn > 0 else r[3]) - ent) for r in path)
            eod = dirn * (next((r[5] for r in reversed(path) if r[1] <= K.FLAT_AT), path[-1][5]) - ent) - 2 * K.COST
    info[d] = {"pnl": round(days.get(d, 0), 2), "width": round(hi - lo, 2), "gap": round(rs[0][2] - prev_close[d], 2) if d in prev_close else None,
               "entry_min": first[0] if first else None, "dir": first[1] if first else 0, "mae": round(mae, 2) if mae is not None else None,
               "eod_nostop": round(eod, 2) if eod is not None else None}
stop = [d for d in ds if info[d]["pnl"] <= K.DAY_STOP + 1e-9]
win = [d for d in ds if info[d]["pnl"] > 0]
avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
q = sorted(info[d]["width"] for d in ds); c1, c2 = q[len(q) // 3], q[2 * len(q) // 3]
bands = {"좁음": [d for d in ds if info[d]["width"] < c1], "중간": [d for d in ds if c1 <= info[d]["width"] < c2], "넓음": [d for d in ds if info[d]["width"] >= c2]}
ent_band = defaultdict(list)
for d in ds:
    m = info[d]["entry_min"]
    if m is not None:
        ent_band["10시대" if m < 660 else "11시대" if m < 720 else "12시 뒤"].append(d)
out = {
    "days": len(ds), "total_p": round(sum(info[d]["pnl"] for d in ds), 2), "stop_days": len(stop), "stop_sum_p": round(sum(info[d]["pnl"] for d in stop), 2),
    "width_cut_p": [c1, c2],
    "by_width": {k: {"days": len(v), "sum_p": round(sum(info[d]["pnl"] for d in v), 2), "stop_days": sum(1 for d in v if d in stop)} for k, v in bands.items()},
    "by_entry_time": {k: {"days": len(v), "sum_p": round(sum(info[d]["pnl"] for d in v), 2), "stop_days": sum(1 for d in v if d in stop)} for k, v in ent_band.items()},
    "by_dir": {k: {"days": len(v), "sum_p": round(sum(info[d]["pnl"] for d in v), 2), "stop_days": sum(1 for d in v if d in stop)}
               for k, v in (("삼", [d for d in ds if info[d]["dir"] > 0]), ("팖", [d for d in ds if info[d]["dir"] < 0]))},
    "stop_days_eod_nostop_p": {"sum": round(sum(info[d]["eod_nostop"] or 0 for d in stop), 2), "positive_days": sum(1 for d in stop if (info[d]["eod_nostop"] or 0) > 0)},
    "mae_win_days_p": sorted(info[d]["mae"] for d in win if info[d]["mae"] is not None),
    "gap_abs_avg": {"stop": avg([abs(info[d]["gap"]) for d in stop if info[d]["gap"] is not None]), "win": avg([abs(info[d]["gap"]) for d in win if info[d]["gap"] is not None])},
}
print(json.dumps(out, ensure_ascii=False, indent=1))
