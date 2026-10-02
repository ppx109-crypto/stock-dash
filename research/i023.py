"""I 25회차 — 시장 수급 과열 뒤 코스닥150 인버스(251340 · 2017 ~ · market-data 그날까지 알려진 값만).
과열 생각: 개인이 크게 사들인 뒤(개인 5 · 10일 순매수가 지난 1년 위 5 · 10%) · 외국인 · 기관이 크게 판 뒤 · 신용융자 20일 +X% 급증.
신호를 단독으로, 그리고 코스닥150 10일 +10%(I22)와 겹치거나 더해서 봄. 나오는 법 54판(익절 1.5 · 2 · 3 × 손절 1.5 · 2 · 3 × 5 · 10 · 20일 × 쉬기 0 · 10)."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

n = len(I.DAYS)
q = I.px("229200")
I.px("251340")
q10 = np.nan_to_num(I.ret(q, 10), nan=0) >= 0.10


def rsum(a, w):
    out = np.full(n, np.nan)
    for i in range(w - 1, n):
        x = a[i - w + 1:i + 1]
        if np.isfinite(x).sum() >= w - 1:
            out[i] = np.nansum(x)
    return out


def high_rank(a, pct, look=250):
    """그날 값이 앞 1년(그날 뺌) 값들의 위 pct% 안이면 참."""
    out = np.zeros(n, bool)
    for i in range(look, n):
        h = a[i - look:i]
        h = h[np.isfinite(h)]
        if len(h) > 100 and np.isfinite(a[i]):
            out[i] = a[i] >= np.percentile(h, 100 - pct)
    return out


ind, fr, ins = (I.series("market-data/investor_KSQ.json", c) for c in ("개인", "외국인", "기관"))
credit = I.series("market-data/funds.json", "신용융자잔고")
c20 = np.full(n, np.nan)
c20[20:] = credit[20:] / credit[:-20] - 1
SIG = {}
for w in (5, 10):
    s = rsum(ind, w)
    for pct in (5, 10):
        SIG[f"개인 {w}일 순매수 위 {pct}%"] = high_rank(s, pct)
    sf = rsum(-(np.nan_to_num(fr) + np.nan_to_num(ins)), w)
    SIG[f"외국인+기관 {w}일 순매도 위 10%"] = high_rank(sf, 10)
for x in (0.05, 0.08):
    SIG[f"신용융자 20일 +{x*100:.0f}%"] = np.nan_to_num(c20, nan=0) >= x
base = {k: v for k, v in SIG.items()}
for k, v in base.items():
    SIG[f"I22 · {k}"] = q10 & v
    SIG[f"I22 또는 {k}"] = q10 | v
SIG["I22 단독"] = q10
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 25회차: 시장 수급 과열 뒤 코스닥150 인버스 ==", flush=True)
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
                                 " | ".join(f"{nm} {j['n']}건 연 {j['cagr']:+.1f} 골 {j['dd']:.1f}" for (nm, _, _), j in zip(PER, js))))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(f"[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(x[0] for x in rows)}/54 · 맨 위 {rows[0][2]} (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][3]}", flush=True)
print("끝", flush=True)
