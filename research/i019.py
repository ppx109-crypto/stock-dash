"""I 21회차 — 코스피 · 코스닥 짝 매매(시장 방향과 상관없이 벌어진 차이만): 한쪽 지수 ETF를 사고 다른 쪽 인버스를 반반 듦(1배만).
  짝 K: 코스피가 상대적으로 많이 빠졌을 때 → KODEX 200(069500) 0.5 + 코스닥150 인버스(251340) 0.5
  짝 Q: 코스닥이 상대적으로 많이 빠졌을 때 → 코스닥150(229200) 0.5 + KODEX 인버스(114800) 0.5
차이 = log(코스피 / 코스닥) 의 N일 변화(N = 5 · 10 · 20). 되돌림: 차이가 −X%(코스피 뒤짐) → 짝 K, +X% → 짝 Q.
  흐름 타기(거울): 반대로 듦. X = 3 · 4 · 6%. 나오는 법: 짝 손익 익절 2 · 3 · 손절 2 · 3 · 10 · 20일.
2016-08 ~ (251340 시작) → B · C1 · C2. 비용: 두 상품 사고팔기 0.2%씩(짝 전체 0.2%)."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
P = {c: I.px(c) for c in ("069500", "229200", "114800", "251340")}
lk, lq = np.log(P["069500"]), np.log(P["229200"])
PAIR = {"K": ("069500", "251340"), "Q": ("229200", "114800")}


def leg_ret(c, i):
    a, b = P[c][i - 1], P[c][i]
    return 0.0 if np.isnan(a) or np.isnan(b) else b / a - 1


def run(sig_k, sig_q, take, stop, maxd, cost=0.002):
    daily, trades, hold, i = np.zeros(n), [], None, 1
    while i < n:
        if hold:
            side, a, eq = hold
            r = 0.5 * leg_ret(PAIR[side][0], i) + 0.5 * leg_ret(PAIR[side][1], i)
            daily[i] += r
            eq *= 1 + r
            hold = (side, a, eq)
            if eq - 1 >= take or eq - 1 <= stop or i - a >= maxd:
                daily[i] -= cost / 2
                trades.append((a, i, eq - 1 - cost))
                hold = None
            i += 1
            continue
        side = "K" if sig_k[i] else ("Q" if sig_q[i] else None)
        if side and all(not np.isnan(P[c][i]) for c in PAIR[side]):
            daily[i] -= cost / 2
            hold = (side, i, 1.0)
        i += 1
    return trades, daily


PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 21회차: 코스피 · 코스닥 짝 매매(사기 + 인버스 반반) ==", flush=True)
rows = []
for N in (5, 10, 20):
    sp = np.full(n, np.nan)
    sp[N:] = (lk[N:] - lk[:-N]) - (lq[N:] - lq[:-N])
    sp = np.nan_to_num(sp, nan=0)
    for X in (0.03, 0.04, 0.06):
        for mode in ("되돌림", "흐름 타기"):
            lag_k, lag_q = sp <= -X, sp >= X          # 코스피가 뒤짐 · 코스닥이 뒤짐
            sk, sq = (lag_k, lag_q) if mode == "되돌림" else (lag_q, lag_k)
            for take in (0.02, 0.03):
                for stop in (-0.02, -0.03):
                    for maxd in (10, 20):
                        tr, d = run(sk, sq, take, stop, maxd)
                        js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER[:2]]
                        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                        rows.append((ok, min(j["cagr"] for j in js), I.line(f"{mode} {N}일 차이 {X*100:.0f}% | 익절 {take*100:.0f} 손절 {stop*100:.0f} {maxd}일", tr, d, PER)[0]))
rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
print(f"합격 {sum(x[0] for x in rows)}/{len(rows)}", flush=True)
for ok, w, t in rows[:10]:
    print(f"  {'합격' if ok else '    '} (가장 나쁜 {w:+5.1f}) {t.strip()}", flush=True)
print("끝", flush=True)
