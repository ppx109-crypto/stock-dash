"""KMF-0017 준비 · 손실 분석(사용자 2026-10-13 "177일은 +94p 너무 적어 · 177일만 갖고 더 연구해보자").
KMF-0016(한 계약 · 추세 우선) 전체 자료에서 그 봇 위 10일(고정 목록 TOP10)을 뺀 177일: 날 종류 · 멈춤 날 · 봇별 · 들어간 시각별 손익."""
import sys, json
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf16 as M16
b = M16.prep(K._rows_before(M16.END))
w = M16.signals(b, M16.grid()[0])
days, trades = K.simulate(b, w)
TOP10 = sorted(days, key=lambda d: -days[d])[:10]
rest = {d: v for d, v in days.items() if d not in TOP10}
print("위 10일:", TOP10, "합", round(sum(days[d] for d in TOP10), 1))
v = np.array(list(rest.values()))
print(f"177일 합 {v.sum():+.1f} · 이긴 날 {int((v > 0).sum())} 합 {v[v > 0].sum():+.1f} · 진 날 {int((v < 0).sum())} 합 {v[v < 0].sum():+.1f} · 0인 날 {int((v == 0).sum())}")
print(f"  −25p 멈춤 날 {int((v <= -24.9).sum())} 합 {v[v <= -24.9].sum():+.1f} · −10 ~ −25 날 {int(((v > -24.9) & (v <= -10)).sum())} 합 {v[(v > -24.9) & (v <= -10)].sum():+.1f}")
T = M16.intent(b, M16.M13.signals(b, M16.M13.grid()[0])); R = M16.intent(b, M16.M14.signals(b, M16.M14.grid()[0]))
idx = {(r[0], r[1]): i for i, r in enumerate(b)}
# 거래마다 누가 든 자리인지(들 때 봉 = 정리 앞 마지막 들기 신호 봉)
ent = {}
for i, x in enumerate(w):
    if x in (1, -1):
        ent[(b[i][0], i)] = ("T" if T[i] == x else "R", b[i][1])
by_bot = defaultdict(float); by_hour = defaultdict(float); cnt_b = defaultdict(int)
for d, m, pos, e, x in trades:
    if d in TOP10:
        continue
    cands = [(i, v_) for (dd, i), v_ in ent.items() if dd == d and b[i][1] < m]
    if not cands:
        continue
    i, (who, em) = max(cands)
    p = pos * (x - e) - 2 * K.COST
    by_bot[who] += p; cnt_b[who] += 1
    by_hour[f"{(em + 1) // 60:02d}시"] += p
print("봇별(177일):", {k: (cnt_b[k], round(v_, 1)) for k, v_ in by_bot.items()})
print("들어간 시각별(177일):", {k: round(v_, 1) for k, v_ in sorted(by_hour.items())})
mo = defaultdict(float)
for d, x in rest.items():
    mo[d[:6]] += x
print("달별(177일):", {k: round(x, 1) for k, x in sorted(mo.items())})
json.dump({"top10": TOP10}, open(Path(__file__).parent / "top10_kmf16.json", "w"))
