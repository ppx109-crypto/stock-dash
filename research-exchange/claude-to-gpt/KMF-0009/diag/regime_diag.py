"""KMF-0009 준비 · 판정 밖 진단(개발 2026-01 ~ 05만 · 06-01부터 안 읽음 · 5분봉 · 1분봉 신호 없음).
사용자 2026-10-13: "목표 10개월에 800p · 추세 횡보에서 각각 작동하는 단타봇 개발".
① 그날 10:00 뒤 '추세일 / 횡보일'(효율 ER = |장 끝 − 10:00| ÷ 5분봉 움직임 합 · 셋으로 나눔)을 아침 값(첫 60분 ER · 첫 60분 폭 ÷ 앞 20일 평균 폭 · 갭 ÷ 앞 20일 평균 하루 폭)으로 가릴 수 있는가.
② 상한(미래를 아는 가정 · 판정에 안 씀): 추세일엔 돌파 들고 끝까지(KMF-0007 꼴) · 횡보일엔 범위 끝 되돌림만 했다면 몇 p인가 · 비용 · −12p 포함."""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf4 as K4, kmf5 as K5
b = K4.day_start_aligned(K._rows_before(K.VAL[0]), 5)
byday = defaultdict(list)
for i, r in enumerate(b):
    byday[r[0]].append(i)
days = sorted(byday)
feat, er_rest = {}, {}
widths, dranges = [], []
for d in days:
    idx = byday[d]
    st = b[idx[0]][1] - 4
    first = [i for i in idx if b[i][1] < st + 60]
    rest = [i for i in idx if b[i][1] >= st + 60]
    if len(first) < 12 or len(rest) < 10:
        widths.append(None); dranges.append(None); continue
    hi = max(b[i][3] for i in first); lo = min(b[i][4] for i in first)
    w = hi - lo
    c0 = b[first[0]][2]; c1 = b[first[-1]][5]
    mv1 = sum(abs(b[i][5] - b[i - 1][5]) for i in first[1:]) or 1e-9
    er1 = abs(c1 - c0) / mv1
    cl = [b[i][5] for i in rest]
    mv = sum(abs(cl[k] - cl[k - 1]) for k in range(1, len(cl))) + abs(cl[0] - c1)
    er_rest[d] = abs(cl[-1] - c1) / (mv or 1e-9)
    pw = [x for x in widths[-20:] if x]; pr = [x for x in dranges[-20:] if x]
    prev_close = b[byday[days[days.index(d) - 1]][-1]][5] if days.index(d) > 0 else None
    if len(pw) >= 10 and prev_close:
        feat[d] = {"er1": er1, "wrel": w / np.mean(pw), "gaprel": abs(c0 - prev_close) / np.mean(pr)}
    widths.append(w); dranges.append(max(b[i][3] for i in idx) - min(b[i][4] for i in idx))
dev = [d for d in feat if K.DEV[0] <= d <= K.DEV[1]]
q = np.quantile([er_rest[d] for d in dev], [1 / 3, 2 / 3])
lab = {d: ("추세" if er_rest[d] >= q[1] else "횡보" if er_rest[d] < q[0] else "중간") for d in dev}
out = {"days": len(dev), "er_cut": [round(float(x), 3) for x in q], "label_count": {k: sum(1 for v in lab.values() if v == k) for k in ("추세", "중간", "횡보")}}
for f in ("er1", "wrel", "gaprel"):
    v = np.array([feat[d][f] for d in dev]); t = np.array([lab[d] == "추세" for d in dev]); s = np.array([lab[d] == "횡보" for d in dev])
    cut = np.quantile(v, [1 / 3, 2 / 3])
    out[f] = {"corr_with_er_rest": round(float(np.corrcoef(v, [er_rest[d] for d in dev])[0, 1]), 3),
              "low_third": {"추세": int(t[v < cut[0]].sum()), "횡보": int(s[v < cut[0]].sum()), "n": int((v < cut[0]).sum())},
              "high_third": {"추세": int(t[v >= cut[1]].sum()), "횡보": int(s[v >= cut[1]].sum()), "n": int((v >= cut[1]).sum())}}
# 상한(미래를 앎 · 판정 밖): 추세일 = KMF-0007 칸 손익 · 횡보일 = 범위 되돌림(위끝에서 팖 · 아래끝에서 삼 · 가운데 정리)
cfg = next(c for c in K5.grid() if c["tag"] == "N60_day_e1")
b15 = K5.prep(K._rows_before(K.VAL[0]))
t_days, _ = K.simulate(b15, K5.signals(b15, cfg))
want = [None] * len(b)
for d in dev:
    idx = byday[d]; st = b[idx[0]][1] - 4
    first = [i for i in idx if b[i][1] < st + 60]
    hi = max(b[i][3] for i in first); lo = min(b[i][4] for i in first); mid = (hi + lo) / 2
    pos = 0
    for i in idx:
        if b[i][1] < st + 60 or b[i][1] > K.ENTRY_TO and pos == 0:
            continue
        c = b[i][5]
        if pos == 0:
            if c >= hi - 0.15 * (hi - lo) and c <= hi: want[i], pos = -1, -1
            elif c <= lo + 0.15 * (hi - lo) and c >= lo: want[i], pos = 1, 1
        elif (pos < 0 and (c <= mid or c > hi + 0.25 * (hi - lo))) or (pos > 0 and (c >= mid or c < lo - 0.25 * (hi - lo))):
            want[i], pos = 0, 0
r_days, _ = K.simulate(b, want)
orc = {"추세일만 돌파 끝까지": round(sum(t_days.get(d, 0) for d in dev if lab[d] == "추세"), 2),
       "횡보일만 되돌림": round(sum(r_days.get(d, 0) for d in dev if lab[d] == "횡보"), 2),
       "추세일 되돌림(잘못 고르면)": round(sum(r_days.get(d, 0) for d in dev if lab[d] == "추세"), 2),
       "횡보일 돌파(잘못 고르면)": round(sum(t_days.get(d, 0) for d in dev if lab[d] == "횡보"), 2),
       "중간일 돌파": round(sum(t_days.get(d, 0) for d in dev if lab[d] == "중간"), 2), "중간일 되돌림": round(sum(r_days.get(d, 0) for d in dev if lab[d] == "중간"), 2)}
out["oracle_dev_p"] = orc
print(json.dumps(out, ensure_ascii=False, indent=1))
