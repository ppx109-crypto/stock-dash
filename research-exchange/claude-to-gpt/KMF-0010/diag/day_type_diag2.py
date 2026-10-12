"""KMF-0010 준비 · 판정 밖 진단 2(개발 2026-01 ~ 05만 · 06-01부터 안 읽음 · 5분봉).
KMF-0009 진단은 아침 가격 값(ER · 폭 · 갭)으로 추세일 / 횡보일을 못 가렸음(상관 ≈ 0).
여기서는 아직 안 본 값: ① 첫 30분 거래량 ÷ 앞 20일 같은 때 평균(상대 거래량) ② 어제 10:00 뒤 ER ③ 앞 5일 ER 평균
④ 앞 5일 하루 폭 ÷ 앞 60일 하루 폭(흔들림 국면) — 모두 그날 10:00(또는 그 전날)까지 아는 값."""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf4 as K4
b = K4.day_start_aligned(K._rows_before(K.VAL[0]), 5)
byday = defaultdict(list)
for i, r in enumerate(b):
    byday[r[0]].append(i)
days = sorted(byday)
er_rest, v30, drange, feat = {}, {}, {}, {}
for n, d in enumerate(days):
    idx = byday[d]; st = b[idx[0]][1] - 4
    first = [i for i in idx if b[i][1] < st + 60]; f30 = [i for i in idx if b[i][1] < st + 30]
    rest = [i for i in idx if b[i][1] >= st + 60]
    drange[d] = max(b[i][3] for i in idx) - min(b[i][4] for i in idx)
    v30[d] = sum(b[i][6] for i in f30)
    if len(first) < 12 or len(rest) < 10:
        continue
    c1 = b[first[-1]][5]; cl = [b[i][5] for i in rest]
    mv = sum(abs(cl[k] - cl[k - 1]) for k in range(1, len(cl))) + abs(cl[0] - c1)
    er_rest[d] = abs(cl[-1] - c1) / (mv or 1e-9)
    prev = days[max(0, n - 20):n]
    if len(prev) >= 20 and all(p in er_rest for p in prev[-5:]):
        feat[d] = {"rvol30": v30[d] / np.mean([v30[p] for p in prev]),
                   "er_prev1": er_rest[prev[-1]], "er_prev5": float(np.mean([er_rest[p] for p in prev[-5:]])),
                   "vol5_60": float(np.mean([drange[p] for p in prev[-5:]]) / np.median([drange[p] for p in days[max(0, n - 60):n]]))}
dev = [d for d in feat if K.DEV[0] <= d <= K.DEV[1] and d in er_rest]
q = np.quantile([er_rest[d] for d in dev], [1 / 3, 2 / 3])
out = {"days": len(dev)}
y = np.array([er_rest[d] for d in dev])
for f in ("rvol30", "er_prev1", "er_prev5", "vol5_60"):
    v = np.array([feat[d][f] for d in dev]); c = np.quantile(v, [1 / 3, 2 / 3])
    half = len(dev) // 2
    out[f] = {"corr": round(float(np.corrcoef(v, y)[0, 1]), 3),
              "corr_front_half": round(float(np.corrcoef(v[:half], y[:half])[0, 1]), 3),
              "corr_back_half": round(float(np.corrcoef(v[half:], y[half:])[0, 1]), 3),
              "trend_share_low_third": round(float((y[v < c[0]] >= q[1]).mean()), 3),
              "trend_share_high_third": round(float((y[v >= c[1]] >= q[1]).mean()), 3)}
print(json.dumps(out, ensure_ascii=False, indent=1))
