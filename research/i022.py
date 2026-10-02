"""I 24회차 — 코스닥 종목 폭 과열 → 코스닥150 인버스(251340). kosdaq-data(한투 · 지금 상장 1,697종목 · 2015 ~).
그날 코스닥 거래대금 상위 100(전날까지 20일 평균 · k002와 같은 순위) 가운데:
  W20 = 20일선 위 몫(%) · W5 = 5일 수익 + 몫(%) · A10 = 10일 수익 평균(%)
신호: W20 ≥ 80 · 85 · 90 / W5 ≥ 80 · 85 · 90 / A10 ≥ 8 · 10 · 12 / 그리고 코스닥150 10일 +10%(I22)와 겹치기.
나오는 법: 익절 1.5 · 2 · 3 × 손절 1.5 · 2 · 3 × 5 · 10 · 20일 × 쉬기 0 · 10. 기간 B · C1 · 2026.
치우침: 지금 상장 종목만(상장폐지 없음) → 폭이 조금 높게 나옴(문턱을 여럿으로 봄)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
IX = {d: i for i, d in enumerate(D)}
cl, va = [], []
for f in sorted(Path("/home/user/stock-dash/kosdaq-data").glob("*.json")):
    b = json.loads(f.read_text(encoding="utf-8"))
    cols = b.get("cols") or []
    if "종가" not in cols or "거래대금" not in cols:
        continue
    ic, iv = cols.index("종가"), cols.index("거래대금")
    c, v = np.full(n, np.nan), np.full(n, np.nan)
    for r in b.get("rows") or []:
        i = IX.get(str(r[0]))
        if i is not None and r[ic]:
            c[i], v[i] = float(r[ic]), float(r[iv] or 0)
    if np.isfinite(c).sum() >= 250:
        cl.append(c)
        va.append(v)
C, V = np.array(cl), np.array(va)
print(f"종목 {len(C)}", flush=True)


def roll_mean(a, w):
    out = np.full_like(a, np.nan)
    cs = np.nancumsum(np.nan_to_num(a), axis=1)
    cnt = np.cumsum(np.isfinite(a), axis=1)
    out[:, w:] = (cs[:, w:] - cs[:, :-w]) / np.maximum(cnt[:, w:] - cnt[:, :-w], 1)
    out[:, :w] = np.nan
    return out


avgv = np.full_like(V, np.nan)
avgv[:, 1:] = roll_mean(V, 20)[:, :-1]          # 전날까지 20일 평균
ma20 = roll_mean(C, 20)
r5 = np.full_like(C, np.nan); r5[:, 5:] = C[:, 5:] / C[:, :-5] - 1
r10 = np.full_like(C, np.nan); r10[:, 10:] = C[:, 10:] / C[:, :-10] - 1
W20, W5, A10 = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
for i in range(n):
    if D[i] < "20150301":
        continue
    a = avgv[:, i]
    ok = np.isfinite(a) & np.isfinite(C[:, i])
    if ok.sum() < 150:
        continue
    top = np.argsort(np.where(ok, a, -1))[::-1][:100]
    W20[i] = np.nanmean(C[top, i] > ma20[top, i]) * 100
    W5[i] = np.nanmean(r5[top, i] > 0) * 100
    A10[i] = np.nanmean(r10[top, i]) * 100
print("W20 분포(2017 ~) 50 · 90 · 99%:", np.nanpercentile(W20[np.array([d >= "2017" for d in D])], [50, 90, 99]).round(0), flush=True)
q = I.px("229200")
I.px("251340")
q10 = np.nan_to_num(I.ret(q, 10), nan=0) >= 0.10
nz = lambda a: np.nan_to_num(a, nan=0)
SIG = {}
for t in (80, 85, 90):
    SIG[f"W20 ≥ {t}"] = nz(W20) >= t
    SIG[f"W5 ≥ {t}"] = nz(W5) >= t
for t in (8, 10, 12):
    SIG[f"A10 ≥ {t}%"] = nz(A10) >= t
SIG["코스닥150 10일 +10%(I22)"] = q10
SIG["I22 · W20 ≥ 80"] = q10 & (nz(W20) >= 80)
SIG["I22 또는 A10 ≥ 10%"] = q10 | (nz(A10) >= 10)
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 24회차: 코스닥 종목 폭 과열 → 코스닥150 인버스 ==", flush=True)
for name, sig in SIG.items():
    rows = []
    for take in (0.015, 0.02, 0.03):
        for stop in (-0.015, -0.02, -0.03):
            for maxd in (5, 10, 20):
                for cool in (0, 10):
                    tr, d = I.sim(sig, "251340", stop, take, maxd, cool=cool)
                    js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
                    ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                    rows.append((ok, min(j["cagr"] for j in js), f"익절 {take*100:.1f} 손절 {stop*100:.1f} {maxd}일 쉬기 {cool}",
                                 " | ".join(f"{nm} {j['n']}건 이김 {j['win']:.0f} 연 {j['cagr']:+.1f} 골 {j['dd']:.1f}" for (nm, _, _), j in zip(PER, js))))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(f"[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(x[0] for x in rows)}/{len(rows)} · 맨 위 {rows[0][2]} (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][3]}", flush=True)
print("끝", flush=True)
