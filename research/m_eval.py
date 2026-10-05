"""1일봉 달마다 플러스 연구(docs/RL-MONTH.md) 실행기 — 1일봉 장부(조용함 문턱 그때까지 자료 · 실제 비용) 위에 덧씌우기 설계를 얹어 날마다 계좌를 다시 셈.
쓰는 법: python research/m_eval.py "" "CASH" "CASH+MS3" …   (설계를 + 로 이음)
덧씌우기 판단은 그날 종가까지 · 실행은 다음 거래일 종가(팔 때 비용 0.25%) · 2026 잠금(M_OPEN2026=1) · 시험 기간은 M_SHOW_TEST=1.
설계: CASH(안 쓰는 돈 → 단기채권 153130) · MS{y}(그달 −y% 아래면 다 팔고 그달 새로 안 삼) · ML{x}(그달 +x% 넘으면 그달 새로 안 삼) ·
      MK{x}(그달 +x% 넘은 뒤 그 절반 아래면 다 팔고 그달 새로 안 삼) · SZ{p}(크기 × p/100) · TP{x}(+x%에 절반 팖 · 한 번) · SL{x}(−x%면 다 팖) ·
      MN{n}(그달 잃고 판 매매 n번이면 그달 새로 안 삼) · WC{c}(한 종목이 계좌 c% 넘으면 넘친 만큼 팖) · HG{p}(어제 코스피200 < 20일선이면 주식 값 p%만큼 인버스 114800)."""
import json
import os
import re
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np
import itools as I
import nrl

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
LED = os.environ.get("M_LEDGER", "c_s_led_base.json")
D = [d for d in I.DAYS if "20170101" <= d]
n = len(D); idx = {d: i for i, d in enumerate(D)}
_bp = I.px("153130"); _ai = {d: i for i, d in enumerate(I.DAYS)}
_ip = I.px("114800"); _K = np.asarray(I.K200, float)
INV = np.array([(_ip[_ai[d]] / _ip[_ai[d] - 1] - 1) if np.isfinite(_ip[_ai[d]]) and np.isfinite(_ip[_ai[d] - 1]) else 0.0 for d in D])
BELOW20 = np.array([_K[_ai[d]] < np.nanmean(_K[_ai[d] - 19:_ai[d] + 1]) for d in D])     # 그날 종가가 20일선 아래(다음 날 판단에 씀)
BOND = np.array([(_bp[_ai[d]] / _bp[_ai[d] - 1] - 1) if np.isfinite(_bp[_ai[d]]) and np.isfinite(_bp[_ai[d] - 1]) else 0.0 for d in D])
L0 = [t for t in json.load(open(SP + LED)) if t[1] in idx and t[2] in idx]
PX = {c: dict(nrl.prices.get(c, {}).get("rows") or []) for c in {t[0] for t in L0}}
SELL_COST = 0.0025
PERIODS = [("고르기 17~22", "20170101", "20230101")] + ([("시험 23~25", "20230101", "20260101")] if os.environ.get("M_SHOW_TEST") == "1" else []) \
    + ([("2026", "20260101", "20991231")] if os.environ.get("M_OPEN2026") == "1" else [])


def parse(design):
    o = {}
    for x in [y for y in design.split("+") if y]:
        m = re.match(r"([A-Z]+)(\d*)", x)
        o[m.group(1)] = float(m.group(2)) if m.group(2) else 1.0
    return o


def sim(design):
    o = parse(design)
    buys, sells = {}, {}
    for t, (c, b, e, p, k) in enumerate(L0):
        buys.setdefault(idx[b], []).append(t); sells.setdefault(idx[e], []).append(t)
    cash = 1.0; val, last, units, frac, halved = {}, {}, {}, {}, set()
    E = np.ones(n); C = np.ones(n)
    ms = 1.0; mmax = 0.0; block_month = None; pend_all = False; pend = {}     # pend: t → 팔 몫(1 = 다, 0.5 = 절반)
    sz = o.get("SZ", 100) / 100
    losses = 0; hedge = 0.0
    for d in range(1, n):
        mon = D[d][:6]
        if D[d - 1][:6] != mon:
            ms = E[d - 1]; mmax = 0.0; losses = 0
        if "HG" in o:                                   # 어제 정한 덮개(어제 주식 값 × p%)의 오늘 손익
            cash += hedge * INV[d]
            want = o["HG"] / 100 * sum(val.values()) if BELOW20[d - 1] else 0.0
            cash -= abs(want - hedge) * 0.001; hedge = want
        for t in list(val):
            v = PX[L0[t][0]].get(D[d])
            if v:
                val[t] *= v / last[t]; last[t] = v
        # 어제 정한 덧씌우기 매도를 오늘 종가에
        if pend_all:
            for t in list(val):
                cash += val[t] * (1 - SELL_COST); val.pop(t)
            pend_all = False; pend = {}
        for t, q in pend.items():
            if t in val:
                if q >= 1:
                    cash += val[t] * (1 - SELL_COST); val.pop(t)
                else:
                    cash += val[t] * q * (1 - SELL_COST); val[t] *= 1 - q; frac[t] *= 1 - q
        pend = {}
        for t in sells.get(d, []):
            if t in val:
                cash += units[t] * frac[t] * (1 + L0[t][3] / 100); val.pop(t)
                losses += L0[t][3] < 0
        if o.get("CASH"):
            cash *= 1 + BOND[d]
        eq = cash + sum(val.values())
        if block_month != mon:
            for t in buys.get(d, []):
                c, b, e, p, k = L0[t]; v = PX[c].get(D[d])
                if v and idx[e] > d:
                    u = min(eq * k / 10 * sz, max(cash, 0.0))
                    if u > 0:
                        units[t] = u; val[t] = u; last[t] = v; frac[t] = 1.0; cash -= u
        E[d] = cash + sum(val.values())
        C[d] = E[d] - sum(max(0.0, val[t] - units[t] * frac[t]) for t in val)
        # 오늘 종가로 판단 → 내일 실행
        mtd = E[d] / ms - 1; mmax = max(mmax, mtd)
        if "MS" in o and mtd <= -o["MS"] / 100:
            pend_all = True; block_month = mon
        if "MN" in o and losses >= o["MN"]:
            block_month = mon
        if "ML" in o and mtd >= o["ML"] / 100:
            block_month = mon
        if "MK" in o and mmax >= o["MK"] / 100 and mtd <= mmax / 2:
            pend_all = True; block_month = mon
        if "WC" in o and E[d] > 0:                       # 한 종목 몫 덮개: 그날 종가로 넘치면 다음 날 넘친 만큼 팖
            for t in val:
                w = val[t] / E[d]
                if w > o["WC"] / 100:
                    pend[t] = max(pend.get(t, 0), 1 - (o["WC"] / 100) / w)
        for t in val:
            g = val[t] / (units[t] * frac[t]) - 1
            if "SL" in o and g <= -o["SL"] / 100:
                pend[t] = 1
            elif "TP" in o and t not in halved and g >= o["TP"] / 100:
                pend[t] = max(pend.get(t, 0), 0.5); halved.add(t)
    return E, C


def stats(E, C, lo, hi):
    m = np.array([lo <= d < hi for d in D]); ii = np.flatnonzero(m)
    a, b = max(ii[0], 1), ii[-1]
    ii = ii[ii >= a]
    months = {}
    for i in ii:
        months.setdefault(D[i][:6], []).append(i)
    mr = np.array([E[v[-1]] / E[v[0] - 1] - 1 for v in months.values()]) * 100
    ann = ((E[b] / E[a - 1]) ** (250 / len(ii)) - 1) * 100
    q = C[a - 1:b + 1] / C[a - 1]
    dd = (q / np.maximum.accumulate(q) - 1).min() * 100
    qm = E[a - 1:b + 1] / E[a - 1]
    ddm = (qm / np.maximum.accumulate(qm) - 1).min() * 100
    return np.mean(mr > 0) * 100, ann, dd, mr.min(), len(mr), ddm


if __name__ == "__main__":
    for design in (sys.argv[1:] or [""]):
        E, C = sim(design)
        s = f"{design or '바탕':18s}"
        for name, lo, hi in PERIODS:
            pp, ann, dd, worst, nm, ddm = stats(E, C, lo, hi)
            s += f" | {name}: 달 플러스 {pp:5.1f}% ({nm}달) · 연 {ann:+6.1f} · 되돌림 셈 골 {ddm:6.1f} · 되돌림 뺀 골 {dd:6.1f} · 가장 나쁜 달 {worst:+6.1f}"
        print(s, flush=True)
