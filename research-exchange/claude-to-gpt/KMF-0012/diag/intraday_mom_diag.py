"""KMF-0011 준비 · 판정 밖 진단(개발 01 ~ 08만 · 09-01부터 안 읽음 · 1분봉 신호 없음: 30분 덩어리 값만).
'장중 모멘텀'(Gao · Han · Li · Zhou 2018, 지수 선물 · ETF): 첫 30분 수익(어제 마지막 종가 → 09:29 종가)과
그 뒤 판단 시점 바로 앞 30분 수익(14:30 → 14:59 종가)이 마지막 30분(15:00 시가 → 15:30 정리) 방향을 맞추는가.
보는 것: 상관 · 같은 방향으로 1계약 들었을 때(비용 0.08p 왕복) 합 · 앞 반(01 ~ 04) · 뒤 반(05 ~ 08) · 두 달 묶음."""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K
rows = K._rows_before("20260901")
byd = defaultdict(dict)
for r in rows:
    byd[r[0]][r[1]] = r
days = sorted(byd)
recs = []
for n in range(1, len(days)):
    d, p = days[n], days[n - 1]
    t, y = byd[d], byd[p]
    need = (569, 870, 899, 900, 930)
    if not all(m in t for m in need) or max(y) < 930:
        continue
    prev_close = y[max(y)][5]
    r1 = t[569][5] - prev_close                 # 첫 30분(어제 끝 → 09:29 종가 · 갭 포함)
    r12 = t[899][5] - t[870][2]                 # 14:30 시가 → 14:59 종가
    last = t[930][5] - t[900][2]                # 15:00 시가에 들고 15:30 종가에 정리
    recs.append((d, r1, r12, last))
out = {"days": len(recs)}
blocks = (("01", "02"), ("03", "04"), ("05", "06"), ("07", "08"))
for nm, k in (("r1", 1), ("r12", 2), ("r1+r12", None)):
    x = np.array([(r[1] + r[2]) if k is None else r[k] for r in recs]); L = np.array([r[3] for r in recs])
    pnl = np.sign(x) * L - 0.08
    mo = lambda a, b: [i for i, r in enumerate(recs) if a <= r[0][4:6] <= b]
    out[nm] = {"corr": round(float(np.corrcoef(x, L)[0, 1]), 3), "hit": round(float((np.sign(x) == np.sign(L)).mean()), 3),
               "sum_p": round(float(pnl.sum()), 2), "per_day_p": round(float(pnl.mean()), 3),
               "front_01_04": round(float(pnl[mo("01", "04")].sum()), 2), "back_05_08": round(float(pnl[mo("05", "08")].sum()), 2),
               "blocks": [round(float(pnl[mo(a, b)].sum()), 2) for a, b in blocks],
               "worst_day": round(float(pnl.min()), 2)}
out["last30_abs_mean_p"] = round(float(np.mean([abs(r[3]) for r in recs])), 2)
print(json.dumps(out, ensure_ascii=False, indent=1))
