"""KMF-0010 준비 · 판정 밖 진단 3(2026-01 ~ 08 · 09-01부터 안 읽음 · 확인 구간은 이미 8번 쓰여 독립 아님).
물음: 고정 −12p 하루 멈춤이 흔들림 큰 날(앞 5일 평균 하루 폭이 큼)에 지난 봇들을 무너뜨렸는가.
앞 5일 평균 하루 폭(그날 전까지만) ÷ 12p 로 날을 나누고, 지난 봇 셋(KMF-0007 · 0008 · 0009 고른 칸)의 하루 손익 · 멈춘 날 비율을 봄."""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf5 as K5, kmf8 as K8, kmf9 as K9
rows = K._rows_before(K.TEST[0])
byd = defaultdict(list)
for r in rows:
    byd[r[0]].append(r)
days = sorted(byd)
rng = {d: max(x[3] for x in byd[d]) - min(x[4] for x in byd[d]) for d in days}
r5 = {d: float(np.mean([rng[p] for p in days[n - 5:n]])) for n, d in enumerate(days) if n >= 5}
bots = {}
b15 = K5.prep(rows); c7 = next(c for c in K5.grid() if c["tag"] == "N60_day_e1")
bots["KMF-0007"] = K.simulate(b15, K5.signals(b15, c7))[0]
b5 = K8.prep(rows); c8 = next(c for c in K8.grid() if K8.name(c) == "N60_k1.0_H120")
bots["KMF-0008"] = K.simulate(b5, K8.signals(b5, c8))[0]
c9 = next(c for c in K9.grid() if K9.name(c) == "N30_z0.15_b0.25")
bots["KMF-0009"] = K.simulate(b5, K9.signals(b5, c9))[0]
bins = [(0, 2), (2, 3), (3, 4), (4, 99)]
out = {"note": "앞 5일 평균 하루 폭 ÷ 12p 칸별 · 날 수 · 하루 평균 p · 합 p · −11.9p 이하(멈춤 근처) 날 비율"}
for nm, dp in bots.items():
    t = {}
    for lo, hi in bins:
        ds = [d for d in r5 if lo <= r5[d] / 12 < hi and d in dp]
        v = [dp[d] for d in ds]
        t[f"{lo}~{hi}"] = {"days": len(ds), "per_day": round(float(np.mean(v)), 2) if v else None, "sum": round(sum(v), 2),
                           "stop_share": round(sum(1 for x in v if x <= -11.9) / len(v), 2) if v else None,
                           "months": sorted({d[:6] for d in ds})}
    out[nm] = t
print(json.dumps(out, ensure_ascii=False, indent=1))
