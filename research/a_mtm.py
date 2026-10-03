"""점검 A18 다시(2026-10-04): 1일봉을 '실제 계좌처럼' 날마다 평가 — 산 날 계좌의 칸 몫만큼 사서 그 뒤엔 값이 오르내리는 대로(몫이 커지거나 작아짐).
엔진 · 인버스 · 돌리기 몫(i013 mix − d1)은 그날 계좌에 곱함. 판 날 그 매매의 값을 장부 손익(비용 · 반 팔기 포함)에 맞춤.
인자: i013 I_DUMP 파일 · 1일봉 장부 · 저장할 npy(날마다 계좌 수익률)."""
import json
import sys

import numpy as np


def account(days, ledger, base, prices=None):
    """1일봉 장부(code · 산 날 · 판 날 · 손익% · 칸)를 실제 계좌처럼 날마다 평가한 계좌 수익률(날마다).
    산 날 그날 계좌의 칸 몫만큼 사서 값이 오르내리는 대로 두고(몫이 커지거나 작아짐) 판 날 장부 손익에 맞춤.
    base = 1일봉 밖 몫(엔진 · 인버스 · 돌리기)의 날마다 계좌 수익률(어제 계좌에 곱함)."""
    if prices is None:
        sys.path.insert(0, "/home/user/stock-dash")
        import nrl
        prices = nrl.prices
    D = list(days); n = len(D); idx = {d: i for i, d in enumerate(D)}
    px, buys, sells = {}, {}, {}
    for t, (c, b, e, p, k) in enumerate(ledger):
        if b not in idx or e not in idx:
            continue
        if c not in px:
            px[c] = dict(prices.get(c, {}).get("rows") or [])
        buys.setdefault(idx[b], []).append(t)
        sells.setdefault(idx[e], []).append(t)
    E = np.ones(n); val, last, units = {}, {}, {}
    for i in range(1, n):
        e_prev = E[i - 1]
        cash = e_prev - sum(val.values())
        for t in list(val):
            v = px[ledger[t][0]].get(D[i])
            if v:
                val[t] *= v / last[t]; last[t] = v
        for t in sells.get(i, []):
            if t in val:
                cash += units[t] * (1 + ledger[t][3] / 100); val.pop(t)
        eq = cash + sum(val.values()) + base[i] * e_prev
        for t in buys.get(i, []):
            c, b, e, p, k = ledger[t]; v = px[c].get(D[i])
            if v and idx[e] > i:
                units[t] = eq * k / 10; val[t] = units[t]; last[t] = v
        E[i] = eq
    return np.concatenate([[0.0], E[1:] / E[:-1] - 1])


if __name__ == "__main__":
    z = np.load(sys.argv[1]); D = list(z["days"])
    r = account(D, json.load(open(sys.argv[2])), z["mix"] - z["d1"])
    np.save(sys.argv[3], r)
    for lo, hi in (("20170101", "20210101"), ("20210101", "20260101"), ("20260101", "20991231")):
        m = np.array([lo <= d < hi for d in D]); q = np.cumprod(1 + r[m]); qm = np.cumprod(1 + z["mix"][m])
        print(f"  {lo[:4]} ~: 판 날 적기 해마다 {(qm[-1] ** (250 / m.sum()) - 1) * 100:+.1f} · 실제 기간 {(qm[-1] - 1) * 100:+.1f} · 골 {(qm / np.maximum.accumulate(qm) - 1).min() * 100:.1f}"
              f" | 날마다 평가 해마다 {(q[-1] ** (250 / m.sum()) - 1) * 100:+.1f} · 실제 기간 {(q[-1] - 1) * 100:+.1f} · 골 {(q / np.maximum.accumulate(q) - 1).min() * 100:.1f}")
