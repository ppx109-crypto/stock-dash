"""I 47회차 — DART · 한투 '시장 분위기 점수'로 매매(i031 지표 · scratchpad/agg.npz).
점수 = 앞 250일 순위 평균: 전환사채 공시 수 + 공급계약 공시 수 + 목표가 올림 몫 + (100 − 대차잔고 20일 변화). (두 기간 같은 방향이던 것만)
판(그날 판단 → 그날 종가):
  L 점수 ≥ 70 · 80 · 90 → KODEX 200(069500) 사기 · 익절 3 · 5 · 8 × 손절 3 · 5 × 10 · 20일
  S 점수 ≤ 10 · 20 · 30 → KODEX 인버스(114800) · 코스닥 인버스(251340) · 익절 2 · 4 × 손절 2 · 3 × 5 · 10 · 20일
  R 들고 있기: 점수 ≥ X인 날 KODEX 200 · 아니면 현금(X = 50 · 60 · 70) — 바꿀 때 비용 0.2%
낱개 지표도 같은 판으로(전환사채 · 공급계약 · 목표가 · 대차). 기간 B(2017 ~ 2020) · C1(2021 ~ 2025) · C2(2026)."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
A = dict(np.load(SP + "agg.npz"))
D, n = I.DAYS, len(I.DAYS)


def rank250(a):
    out = np.full(n, np.nan)
    for i in range(250, n):
        h = a[i - 250:i]
        h = h[np.isfinite(h)]
        if len(h) > 150 and np.isfinite(a[i]):
            out[i] = (h < a[i]).mean() * 100
    return out


R = {"전환사채": rank250(A["DART 전환사채 20일 수"]), "공급계약": rank250(A["DART 공급계약 20일 수"]),
     "목표가": rank250(A["한투 목표가 올림 몫(20일)"]), "대차(반대)": 100 - rank250(A["한투 대차잔고 20일 변화"])}
score = np.nanmean(np.array(list(R.values())), axis=0)
score[np.isfinite(np.array(list(R.values()))).sum(axis=0) < 3] = np.nan
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
SC = {"점수(넷 합)": score, **{f"{k} 낱개": v for k, v in R.items()}}
nz = lambda a: np.nan_to_num(a, nan=-1)


def best(sig, code, grid):
    rows = []
    for take, stop, maxd in grid:
        tr, d = I.sim(sig, code, stop, take, maxd)
        js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
        rows.append((ok, min(j["cagr"] for j in js), f"익절 {take*100:.0f} 손절 {stop*100:.0f} {maxd}일",
                     " | ".join(f"{nm} {j['n']}건 연 {j['cagr']:+.1f} 골 {j['dd']:.1f} 들고 {j['held']:.0f}%" for (nm, _, _), j in zip(PER, js))))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return sum(x[0] for x in rows), len(rows), rows[0]


GL = [(t, s, m) for t in (0.03, 0.05, 0.08) for s in (-0.03, -0.05) for m in (10, 20)]
GS = [(t, s, m) for t in (0.02, 0.04) for s in (-0.02, -0.03) for m in (5, 10, 20)]
print("== I 47회차: DART · 한투 시장 분위기 점수 매매 ==", flush=True)
print("  점수 분포(2017 ~):", np.nanpercentile(score[np.array([d >= '2017' for d in D])], [10, 50, 90]).round(0), flush=True)
for name, s in SC.items():
    print(f"\n[{name}]", flush=True)
    for th in (70, 80, 90):
        ok, tot, top = best(nz(s) >= th, "069500", GL)
        print(f"  L ≥ {th} → KODEX 200: 합격 {ok}/{tot} · 맨 위 {top[2]} (가장 나쁜 {top[1]:+.1f}) {top[3]}", flush=True)
    for th in (10, 20, 30):
        for code in ("114800", "251340"):
            sig = (nz(s) >= 0) & (nz(s) <= th)
            ok, tot, top = best(sig, code, GS)
            print(f"  S ≤ {th} → {code}: 합격 {ok}/{tot} · 맨 위 {top[2]} (가장 나쁜 {top[1]:+.1f}) {top[3]}", flush=True)
    r = I.R if hasattr(I, "R") else None
    k = I.px("069500")
    kr = np.nan_to_num(np.concatenate([[0], k[1:] / k[:-1] - 1]), nan=0)
    for X in (50, 60, 70):
        on = nz(s) >= X
        w = np.concatenate([[0], on[:-1].astype(float)])
        d = kr * w - np.abs(np.diff(np.concatenate([[0], w]))) * 0.001
        parts = []
        for nm, lo, hi in PER:
            st = I.stats(d, lo, hi)
            bh = I.stats(kr, lo, hi)
            parts.append(f"{nm} 연 {st[0]:+.1f} 골 {st[1]:.1f} (그냥 들기 {bh[0]:+.1f} · {bh[1]:.1f}) 든 날 {np.mean(w[[i for i, x in enumerate(D) if lo <= x < hi]]) * 100:.0f}%")
        print(f"  R 점수 ≥ {X}인 날만 KODEX 200: " + " | ".join(parts), flush=True)
print("끝", flush=True)
