"""한투 1년(hourly-kis) vs 야후(hourly-data)의 같은 기간(2025-09-17 ~ 2026-09-29) · 같은 종목 1시간봉 차이.
한투는 운영과 같게 15시 봉을 14시 봉에 합침(research/kis1h.py). 야후는 hlab.load 그대로(15시 봉 뺌 · 14시 봉에 이미 합쳐짐).
보는 것: 봉 수 · 빠진 봉 · 종가 차이(%) · 하루 마지막 봉 종가 vs 일봉 종가 · 거래량 비 · 1시간봉 EMA 정배열(규칙이 쓰는 상태) 일치율."""
import json
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np
import hlab as H
import kis1h

LO, HI = "2025091700", "2026093000"
K = kis1h.load()
Y = H.load(sorted(K))
codes = sorted(set(K) & set(Y))
print(f"== 한투 vs 야후 1시간봉 · 같은 1년 · 같은 종목 {len(codes)}개 (한투 {len(K)} · 야후 {len(Y)}) ==", flush=True)
nk = ny = both = 0
diffs, ddiff_k, ddiff_y, vr, agree, agree_n = [], [], [], [], 0, 0
per_code = []
for c in codes:
    k, y = K[c], Y[c]
    ki = {t: i for i, t in enumerate(k["t"]) if LO <= t < HI}
    yi = {t: i for i, t in enumerate(y["t"]) if LO <= t < HI}
    nk += len(ki); ny += len(yi)
    common = sorted(set(ki) & set(yi)); both += len(common)
    if not common:
        continue
    a = np.array([k["c"][ki[t]] for t in common]); b = np.array([y["c"][yi[t]] for t in common])
    d = np.abs(a / b - 1) * 100
    diffs.extend(d.tolist())
    va = np.array([k["v"][ki[t]] for t in common]); vb = np.array([y["v"][yi[t]] for t in common])
    ok = vb > 0
    vr.extend((va[ok] / vb[ok]).tolist())
    per_code.append((float(np.median(d)), c))
    # 하루 마지막 봉 종가 vs 일봉 종가
    daily = {str(x): float(p) for x, p in json.load(open(f"/home/user/stock-dash/price-data/{c}.json", encoding="utf-8"))["closes"]}
    for src, store, idx in (("k", ddiff_k, ki), ("y", ddiff_y, yi)):
        last = {}
        for t in sorted(idx):
            last[t[:8]] = (K if src == "k" else Y)[c]["c"][idx[t]]
        store.extend(abs(v / daily[d0] - 1) * 100 for d0, v in last.items() if daily.get(d0))
    # 1시간봉 EMA 정배열 상태(규칙이 쓰는 'A' 묶음)
    sk = H.states(c + "_kis", k, "A")["정배열"]; sy = H.states(c, y, "A")["정배열"]
    m = np.array([sk[ki[t]] == sy[yi[t]] for t in common if not (np.isnan(sk[ki[t]]) or np.isnan(sy[yi[t]]))])
    agree += int(m.sum()); agree_n += len(m)
d = np.array(diffs)
print(f"  봉 수: 한투 {nk:,} · 야후 {ny:,} · 둘 다 있는 봉 {both:,} (한투만 {nk - both:,} · 야후만 {ny - both:,})", flush=True)
print(f"  같은 봉 종가 차이: 가운데 {np.median(d):.3f}% · 평균 {d.mean():.3f}% · 0.3% 넘음 {np.mean(d > 0.3) * 100:.1f}% · 1% 넘음 {np.mean(d > 1) * 100:.2f}% · 3% 넘음 {np.mean(d > 3) * 100:.2f}%", flush=True)
print(f"  하루 마지막 봉 종가 vs 일봉 종가(차이 0.1% 넘는 날): 한투 {np.mean(np.array(ddiff_k) > 0.1) * 100:.1f}% · 야후 {np.mean(np.array(ddiff_y) > 0.1) * 100:.1f}%", flush=True)
print(f"  거래량 비(한투 ÷ 야후) 가운데 {np.median(vr):.2f}", flush=True)
print(f"  1시간봉 EMA 정배열 상태 일치: {agree / max(agree_n, 1) * 100:.1f}% ({agree_n:,}봉)", flush=True)
per_code.sort(reverse=True)
print("  종가 차이가 큰 종목(가운데 %): " + " · ".join(f"{c} {v:.2f}" for v, c in per_code[:6]), flush=True)
print("끝", flush=True)
