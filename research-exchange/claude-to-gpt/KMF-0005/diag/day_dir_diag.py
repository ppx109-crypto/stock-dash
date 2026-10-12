"""KMF-0005 준비 · 판정 밖 진단(개발 2026-01 ~ 05만 · 06-01부터 안 읽음 · 1분봉 신호 없음).
물음: 아침 판단 시각(10:00 · 10:30 · 11:00)에 N분봉(15 · 30 · 60) RNA 상태가 '그 뒤 장 끝까지 움직임'(다음 봉 시가 → 15:29 종가)의 방향과 맞는가.
RNA 상태 = 정배열 점수(0 ~ 3) × 120선 기울기 부호. 비용 · 멈춤은 넣지 않은 원 움직임(p)."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "research"))
import numpy as np
import kmf as K, kmf4 as K4
raw = K._rows_before(K.VAL[0])
out = {}
for tf in (15, 30, 60):
    b = K4.day_start_aligned(raw, tf)
    c = np.array([r[5] for r in b])
    f = K.rna(c, (5, 20, 60, 120), slope_k=4, band=60)
    byday = defaultdict(list)
    for i, r in enumerate(b):
        byday[r[0]].append(i)
    for t in (599, 629, 659):
        groups = defaultdict(list)
        for d, idx in byday.items():
            if not (K.DEV[0] <= d <= K.DEV[1]):
                continue
            dec = [i for i in idx if b[i][1] <= t]
            if not dec or dec[-1] + 1 > idx[-1]:
                continue
            i = dec[-1]
            if b[i][1] != t:                              # 그 시각에 끝난 봉이 없으면(늦게 연 날 등) 뺌
                continue
            o, s = f["order"][i], f["slope"][i]
            if np.isnan(o) or np.isnan(s):
                continue
            move = b[idx[-1]][5] - b[i + 1][2]
            key = ("위" if s > 0 else "아래") + f"{int(o)}"
            groups[key].append(move)
        res = {}
        for k, v in sorted(groups.items()):
            res[k] = {"days": len(v), "mean_p": round(float(np.mean(v)), 2), "up_share": round(sum(1 for x in v if x > 0) / len(v), 2)}
        # 간단 규칙 셈(판정 밖): 정배열 3 + 위 → 삼, 역배열 0 + 아래 → 팖, 나머지 쉼
        rule = [x for k, v in groups.items() for x in v if k == "위3"] + [-x for k, v in groups.items() for x in v if k == "아래0"]
        res["규칙(위3 삼 · 아래0 팖)"] = {"days": len(rule), "sum_p": round(float(sum(rule)), 2), "hit": round(sum(1 for x in rule if x > 0) / len(rule), 2) if rule else None}
        out[f"{tf}분봉 · 판단 {(t + 1) // 60}:{(t + 1) % 60:02d}"] = res
print(json.dumps(out, ensure_ascii=False, indent=1))
