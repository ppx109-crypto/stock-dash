"""호환 점검 C5 — 같은 1시간봉 규칙이 야후 1시간봉(연구)과 한투 1분봉 모음(운영과 같은 자료)에서 왜 다르게 나오나.
같은 종목 · 같은 기간(2025-09-17 ~ 2026-08-31) 1시간봉끼리: 봉 시각 짜임 · 하루 봉 수 · 종가 차이 · 1시간봉 EMA 정배열 상태가 같은 봉 몫 · 사는 신호가 같은 몫."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import m15lab as M
import rna

K = M.to_hours(M.load(None, os.environ.get("M15_HOME")))
Y = H.load(sorted(K))
both = sorted(set(K) & set(Y))
print(f"== 호환 점검 C5: 야후 1시간봉 vs 한투 모음 ({len(both)}종목) ==", flush=True)
per_day_y, per_day_k, cdiff, same_state, n_state, hours_y = [], [], [], 0, 0, {}
for c in both:
    ky = {t[:10]: i for i, t in enumerate(Y[c]["t"]) if "2025091700" <= t[:10] < "2026090100"}
    kk = {t[:10]: i for i, t in enumerate(K[c]["t"]) if "202509170000" <= t < "202609010000"}
    for t in ky:
        hours_y[t[8:10]] = hours_y.get(t[8:10], 0) + 1
    days_y, days_k = {}, {}
    for t in ky:
        days_y[t[:8]] = days_y.get(t[:8], 0) + 1
    for t in kk:
        days_k[t[:8]] = days_k.get(t[:8], 0) + 1
    per_day_y += list(days_y.values())
    per_day_k += list(days_k.values())
    common = sorted(set(ky) & set(kk))
    for t in common:
        a, b = Y[c]["c"][ky[t]], K[c]["c"][kk[t]]
        if a and b:
            cdiff.append(abs(a / b - 1) * 100)
    sy = rna.states(Y[c]["c"], rna.SETS["A"])["정배열"]
    sk = rna.states(K[c]["c"], rna.SETS["A"])["정배열"]
    for t in common:
        x, y = sy[ky[t]], sk[kk[t]]
        if not (np.isnan(x) or np.isnan(y)):
            n_state += 1
            same_state += x == y
print(f"  하루 봉 수: 야후 가운데 {statistics.median(per_day_y)} · 한투 모음 가운데 {statistics.median(per_day_k)}", flush=True)
print(f"  야후 봉 시각 분포: {dict(sorted(hours_y.items()))}", flush=True)
print(f"  같은 시각 종가 차이: 가운데 {statistics.median(cdiff):.3f}% · 90% {np.percentile(cdiff, 90):.3f}% · 99% {np.percentile(cdiff, 99):.3f}% ({len(cdiff)}봉)", flush=True)
print(f"  1시간봉 EMA 정배열 상태가 같은 봉: {same_state / max(1, n_state) * 100:.1f}% ({n_state}봉)", flush=True)
print("끝", flush=True)
