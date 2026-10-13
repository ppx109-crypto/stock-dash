"""KMF-0015 탐색 진단(사용자 2026-10-13 "고" — 짧은 추세를 거래량 급증 · 시간대 · 수급으로).
전체 자료 01-02 ~ 10-12 · 5분봉. 거래량 급증 rvol = 그 봉 거래량 ÷ 앞 20거래일 같은 시각 봉 거래량 평균(그날 · 그 봉 제외).
그 봉 몸통 방향(종가 − 시가)으로, 다음 봉 시가에 들었다면 h봉 뒤 종가까지 움직임(ATR 단위 · 비용 뺌 전) 평균."""
import sys, json
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf4 as K4
rows = K._rows_before("20261013")
b = K4.day_start_aligned(rows, 5)
c = np.array([r[5] for r in b]); o = np.array([r[2] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b]); v = np.array([r[6] for r in b], float)
pc = np.r_[c[0], c[:-1]]; trr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc))
atr = np.full(len(c), np.nan)
for i in range(20, len(c)):
    atr[i] = trr[i - 20:i].mean()
slot_hist = defaultdict(list); rvol = np.full(len(c), np.nan); days_seen = []
day_of = [r[0] for r in b]
cur = None; buf = []
for i, r in enumerate(b):
    if r[0] != cur:
        for (s, vv) in buf:
            slot_hist[s].append(vv)
        buf = []; cur = r[0]
    s = r[1]
    hist = slot_hist[s][-20:]
    if len(hist) >= 10 and np.mean(hist) > 0:
        rvol[i] = v[i] / np.mean(hist)
    buf.append((s, v[i]))
out = {}
for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 99)):
    for mv in (0.0, 1.0):
        res = {}
        for hz in (1, 3, 6, 12):
            vals = []; first = []
            for i in range(len(c) - hz - 1):
                if not (lo <= (rvol[i] if not np.isnan(rvol[i]) else -1) < hi) or np.isnan(atr[i]) or atr[i] <= 0:
                    continue
                if day_of[i + hz + 1] != day_of[i] or b[i][1] < K.ENTRY_FROM or b[i][1] > K.ENTRY_TO:
                    continue
                body = c[i] - o[i]
                if abs(body) < mv * atr[i] or body == 0:
                    continue
                side = 1 if body > 0 else -1
                x = side * (c[i + hz] - o[i + 1]) / atr[i] if hz >= 1 else 0
                vals.append(x); first.append(day_of[i] < "20260601")
            a = np.array(vals); f = np.array(first)
            res[f"h{hz}"] = [len(a), round(float(a.mean()), 3) if len(a) else None, round(float(a[f].mean()), 3) if f.any() else None, round(float(a[~f].mean()), 3) if (~f).any() else None]
        out[f"rvol{lo}-{hi}_body{mv}"] = res
print("칸: [건수, 평균(ATR), 앞 반 01 ~ 05, 뒤 반 06 ~ 10]")
for k, r in out.items():
    print(k, r)
