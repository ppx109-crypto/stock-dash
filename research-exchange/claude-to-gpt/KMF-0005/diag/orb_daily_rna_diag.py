"""KMF-0005 준비 · 판정 밖 진단(개발 2026-01 ~ 05만 · 06-01부터 안 읽음).
물음: 일봉 RNA(앞 날들 종가로만 · 그날 쓰기 전에 끝난 값)가 오름 / 내림일 때, 아침 60분 범위 돌파를 15분봉 종가로 판단해 장 끝까지 들면 어떤가.
일봉 RNA = 앞 날 종가들의 EMA 3 · 5 · 10 · 20 배열 점수(0 ~ 3) + 10선 3일 기울기 부호. 비용 · −12p 넣음(KMF simulate)."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import numpy as np
import kmf as K, kmf4 as K4
raw = K._rows_before(K.VAL[0])
b = K4.day_start_aligned(raw, 15)
days = sorted({r[0] for r in b})
close = {}
for r in b:
    close[r[0]] = r[5]
dc = np.array([close[d] for d in days])
f = K.rna(dc, (3, 5, 10, 20), slope_k=3, band=20)
state = {}                                   # 그날 쓰는 일봉 상태 = 앞 날까지 값
for k, d in enumerate(days):
    if k == 0 or np.isnan(f["order"][k - 1]) or np.isnan(f["slope"][k - 1]):
        state[d] = None
    else:
        o, s = f["order"][k - 1], f["slope"][k - 1]
        state[d] = "오름" if (o >= 2 and s > 0) else "내림" if (o <= 1 and s < 0) else "섞임"
want = [None] * len(b)
byday = defaultdict(list)
for i, r in enumerate(b):
    byday[r[0]].append(i)
for d, idx in byday.items():
    st = b[idx[0]][1] - 14                    # 그날 첫 분
    rng_idx = [i for i in idx if b[i][1] < st + 60]
    if len(rng_idx) < 4:
        continue
    hi = max(b[i][3] for i in rng_idx); lo = min(b[i][4] for i in rng_idx)
    for i in idx:
        if b[i][1] < st + 60 or b[i][1] > K.ENTRY_TO:
            continue
        if b[i][5] > hi:
            want[i] = 1; break
        if b[i][5] < lo:
            want[i] = -1; break
dd, tr = K.simulate(b, want)
out = defaultdict(lambda: {"days": 0, "sum_p": 0.0, "long_p": 0.0, "short_p": 0.0, "long_n": 0, "short_n": 0})
dirs = {}
for i, w in enumerate(want):
    if w in (1, -1):
        dirs[b[i][0]] = w
for d in byday:
    if not (K.DEV[0] <= d <= K.DEV[1]) or d not in dirs:
        continue
    g = out[str(state[d])]
    g["days"] += 1; g["sum_p"] += dd[d]
    if dirs[d] > 0:
        g["long_p"] += dd[d]; g["long_n"] += 1
    else:
        g["short_p"] += dd[d]; g["short_n"] += 1
res = {k: {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in out.items()}
agree = sum(dd[d] for d in dirs if K.DEV[0] <= d <= K.DEV[1] and ((state[d] == "오름" and dirs[d] > 0) or (state[d] == "내림" and dirs[d] < 0)))
against = sum(dd[d] for d in dirs if K.DEV[0] <= d <= K.DEV[1] and ((state[d] == "오름" and dirs[d] < 0) or (state[d] == "내림" and dirs[d] > 0)))
res["같은 방향만"] = round(agree, 2); res["역추세만"] = round(against, 2); res["전체"] = round(sum(dd[d] for d in dirs if K.DEV[0] <= d <= K.DEV[1]), 2)
print(json.dumps(res, ensure_ascii=False, indent=1))
