"""점검 A18 · A19 — 가장 나빴던 때 해부 · 1일봉 매매 손익 뒤섞기(i013 I_DUMP 파일 · 1일봉 장부)."""
import json
import sys

import numpy as np

z = np.load(sys.argv[1]); D = z["days"]; s = int(np.searchsorted(D, "20170102"))
mix, d1, dip, qinv = (z[k][s:] for k in ("mix", "d1", "dip", "qinv")); D = D[s:]
other = mix - d1 - dip - qinv          # 돌리기 · 달러(빈 몫에 곱한 값)
eq = np.cumprod(1 + mix)
print("== A18 골 다섯 개(겹치지 않게) ==")
taken = np.zeros(len(eq), bool)
for _ in range(5):
    peak = np.maximum.accumulate(np.where(taken, 0, eq))
    dd = np.where(taken, 0, eq / np.maximum.accumulate(eq) - 1)
    t = int(dd.argmin())
    if dd[t] > -0.03:
        break
    p = int(np.argmax(eq[:t + 1] == np.maximum.accumulate(eq)[t]))
    rec = next((k for k in range(t, len(eq)) if eq[k] >= eq[p]), None)
    seg = slice(p + 1, t + 1)
    parts = {n: (np.prod(1 + a[seg]) - 1) * 100 for n, a in (("1일봉", d1), ("급락", dip), ("인버스", qinv), ("돌리기 · 달러", other))}
    print(f"  골 {dd[t] * 100:+.1f}% · 꼭대기 {D[p]} → 바닥 {D[t]}({t - p}거래일) · 회복 {D[rec] if rec else '아직'}"
          f"({(rec - t) if rec else '-'}거래일) · 조각별: " + " · ".join(f"{n} {v:+.1f}" for n, v in parts.items()))
    taken[p:(rec or len(eq) - 1) + 1] = True
if len(sys.argv) > 2:
    L = json.load(open(sys.argv[2])); idx = {d: i for i, d in enumerate(D)}
    rng = np.random.default_rng(19); pn = np.array([t[3] for t in L])
    base = mix - d1
    res = []
    for _ in range(1000):
        sh = rng.permutation(pn); dn = np.zeros(len(D))
        for (c, b, e, p, k), v in zip(L, sh):
            if e in idx:
                dn[idx[e]] += v * k / 10 / 100
        q = np.cumprod(1 + base + dn)
        res.append(((q[-1] ** (250 / len(q)) - 1) * 100, (q / np.maximum.accumulate(q) - 1).min() * 100))
    r = np.array(res)
    q0 = eq
    print(f"== A19 1일봉 매매 손익 1,000번 뒤섞기(같은 매매 · 순서 · 종목만 바뀜) ==\n  실제: 연 {(q0[-1] ** (250 / len(q0)) - 1) * 100:+.1f} · 골 {(q0 / np.maximum.accumulate(q0) - 1).min() * 100:.1f}"
          f"\n  뒤섞기: 연 가운데 {np.median(r[:, 0]):+.1f} · 골 가운데 {np.median(r[:, 1]):.1f} · 골 아래 10% {np.percentile(r[:, 1], 10):.1f} · 아래 1% {np.percentile(r[:, 1], 1):.1f} · 가장 깊음 {r[:, 1].min():.1f}")
