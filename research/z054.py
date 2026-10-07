"""2차 연구 STEP 6 — D(바구니 C) · F5(공매도 비중 낮음) 다시 재기(docs/PREREG-2.md · 규칙 숫자 그대로).
대상: 그날 시총 200위 — Z_CAPS=raw(1차와 같은 계산) · adj(쪼개기 고친 계산 · 기본). 상장폐지 종목은 없음(자료 못 받음).
비용: perf2 BASE · STRESS · EXTREME(해마다 거래세 · 수수료 · 슬리피지 · 시장 충격 · 계좌 Z_ACC원).
상 · 하한가(그날 ±29.5% 이상)인 날은 사지 못함 → 다음 거래일로 미룸(D · F5 모두 · 미룬 수 셈).
D 순열 검정: 사건마다 같은 날 대상 안 다른 종목으로 바꾼 '가짜 사건' 1,000벌의 20일 초과 평균 분포에서 진짜 평균의 자리(p).
결과 덤프: Z_OUT(npz · 날마다 수익 D5 · D8 · F5 · 바탕) — 섞기(z058)에서 씀.
python research/z054.py   (Z_CAPS=raw 로 1차 계산과 견줌)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import caps  # noqa: E402
import perf2 as P  # noqa: E402
import z001 as Z  # noqa: E402
from z046 import build  # noqa: E402

caps.ADJ = os.getenv("Z_CAPS", "adj") == "adj"
ACC = float(os.getenv("Z_ACC", "1e8"))
LIMIT = 0.295
H = (("학습 2017 ~ 20", "20170101", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"),
     ("1차 앞 2017 ~ 21", "20170101", "20220101"), ("1차 뒤 2022 ~ 26", "20220101", "20991231"), ("전체", "20170101", "20991231"))


def sim_basket(C, R, ev, slots, hold, scale, lag=1):
    """사건 다음 날(lag) 종가에 삼 · 빈 칸만 · 한 칸 = 그날 계좌 ÷ 칸 · hold 거래일째 종가에 팖 · 날마다 평가."""
    days = list(C.index)
    want = {}
    for r in ev.itertuples():
        if r.j + lag < len(days):
            want.setdefault(r.j + lag, []).append(r.코드)
    px = C.to_numpy()
    rr = R.to_numpy()
    col = {c: i for i, c in enumerate(C.columns)}
    held, cash, eq, trades, deferred = {}, 1.0, [], [], 0
    for i in range(len(days)):
        row = px[i]
        for c in [c for c, h in held.items() if i - h[0] >= hold]:
            k, p0, m, cb = held[c]
            if abs(rr[i, col[c]]) >= LIMIT and i + 1 < len(days):
                continue                                   # 상 · 하한가 → 다음 날 팖
            held.pop(c)
            p = row[col[c]] if row[col[c]] == row[col[c]] else p0
            _, cs = P.side_costs(c, days[k], days[i], ACC / slots, scale)
            gross = p / p0
            cash += m * gross * (1 - cs)
            trades.append((c, days[k], days[i], gross * (1 - cs) * (1 - cb) - 1, 1 / slots))
        val = cash + sum(m * ((row[col[c]] / p0) if row[col[c]] == row[col[c]] else 1) for c, (k, p0, m, cb) in held.items())
        for c in want.get(i, []):
            if len(held) >= slots or c in held or not (row[col[c]] == row[col[c]]):
                continue
            if abs(rr[i, col[c]]) >= LIMIT:
                deferred += 1
                if i + 1 < len(days):
                    want.setdefault(i + 1, []).append(c)
                continue
            m = min(val / slots, cash)
            if m <= 0:
                break
            cb, _ = P.side_costs(c, days[i], days[i], ACC / slots, scale)
            cash -= m
            held[c] = (i, row[col[c]], m * (1 - cb), cb)   # 산 돈 m 중 비용 cb를 뗀 몫이 주식
        eq.append(cash + sum(m * ((row[col[c]] / p0) if row[col[c]] == row[col[c]] else 1) for c, (k, p0, m, cb) in held.items()))
    eq = pd.Series(eq, index=days)
    return eq.pct_change().fillna(0.0), trades, deferred


def sim_factor(C, R, inside, score, N, scale):
    """달 첫 거래일 t 자료로 위 N → t+1 종가에 똑같이(상한가면 하루 미룸) · 다음 달 첫 거래일+1까지 · 바뀐 종목만 사고팖."""
    days = list(C.index)
    months = [i for i, d in enumerate(days) if d >= "20170201" and days[i - 1][:6] != d[:6] and i + 1 < len(days)]
    Rv = R.fillna(0.0).clip(-0.5, 1.0)
    daily = pd.Series(0.0, index=days)
    prev = set()
    deferred = 0
    for m, i in enumerate(months):
        s = score.loc[days[i]].where(inside.loc[days[i]]).dropna()
        if len(s) < 50:
            continue
        top = list(s.sort_values(ascending=False).index[:N])
        j0 = i + 1
        j1 = months[m + 1] + 1 if m + 1 < len(months) else len(days) - 1
        cost = 0.0
        for c in set(top) - prev:
            cost += P.side_costs(c, days[j0], days[j0], ACC / N, scale)[0] / N
        for c in prev - set(top):
            cost += P.side_costs(c, days[j0], days[j0], ACC / N, scale)[1] / N
        daily.iloc[j0] -= cost
        start = {c: (j0 + 1 if abs(R.iat[j0, R.columns.get_loc(c)]) < LIMIT or not np.isfinite(R.iat[j0, R.columns.get_loc(c)]) else j0 + 2) for c in top}
        deferred += sum(1 for c in top if start[c] == j0 + 2)
        for c in top:
            a = start[c]
            if a <= j1:
                daily.iloc[a:j1 + 1] += Rv[c].iloc[a:j1 + 1].values / N
        prev = set(top)
    return daily, deferred


def permutation(C, inside, ev, hold=20, lag=1, n=1000):
    days = list(C.index)
    f = C.shift(-(lag + hold)) / C.shift(-lag) - 1
    ex = f.where(inside).sub(f.where(inside).median(axis=1), axis=0)
    real, pools = [], []
    for r in ev.itertuples():
        v = ex.iat[r.j, ex.columns.get_loc(r.코드)]
        if np.isfinite(v):
            pool = ex.iloc[r.j].dropna().to_numpy()
            real.append(v)
            pools.append(pool)
    rng = np.random.default_rng(5)
    real = np.array(real)
    sims = np.array([np.mean([p[rng.integers(0, len(p))] for p in pools]) for _ in range(n)])
    return real.mean(), (sims >= real.mean()).mean(), len(real)


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    R = C.pct_change(fill_method=None)
    print(f"시총 계산: {'쪼개기 고침(adj)' if caps.ADJ else '1차와 같음(raw)'} · 계좌 {ACC / 1e8:.0f}억 · 종목 {C.shape[1]}", flush=True)
    Cc = C[C.index >= "20161001"]
    Fc = {k: v.reindex(Cc.index) for k, v in F.items()}
    ev = build(Cc, Fc, evs, inside.reindex(Cc.index), ("자사주취득", "무상증자"))
    evC = ev[((ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02)) | (ev["갈래"] == "무상증자")]
    Rc = R.reindex(Cc.index)
    dump = {}
    for lab, e, K in (("D 바구니 C 5칸", evC, 5), ("D 바구니 C 8칸", evC, 8)):
        print(f"\n== {lab} · 사건 {len(e)}(자사주 {int((e['갈래'] == '자사주취득').sum())} · 무상 {int((e['갈래'] == '무상증자').sum())}) ==", flush=True)
        for sc, k in P.SCALES.items():
            r, tr, dfr = sim_basket(Cc, Rc, e, K, 20, k)
            if sc == "BASE":
                dump[lab] = r
            print(f"  [{sc}] 상 · 하한가로 미룬 사기 {dfr}", flush=True)
            for h, lo, hi in H:
                if sc != "BASE" and not h.startswith(("시험", "전체")):
                    continue
                print(f"    {h:16s} 매매: {P.fmt_t(P.trade_stats(tr, lo, hi))}", flush=True)
                print(f"    {'':16s} 계좌: {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)
            if sc == "BASE":
                s = P.daily_stats(r, "20170101", "20991231")
                print(f"    해마다: {P.years_line(s)}", flush=True)
        m, p, n = permutation(Cc, inside.reindex(Cc.index), e)
        print(f"  순열 검정(사건 {n} · 20일 초과 · 같은 날 대상 안 무작위 1,000벌): 진짜 평균 {m * 100:+.2f}% · p = {p:.3f}", flush=True)
    base = pd.DataFrame(1.0, index=C.index, columns=C.columns).where(C.notna())
    for lab, sc_, N in (("F5 공매도 비중 낮음 위 20", -X["공매도20"], 20), ("바탕 200위 똑같이", base, 200)):
        print(f"\n== {lab} ==", flush=True)
        for sc, k in P.SCALES.items():
            r, dfr = sim_factor(C, R, inside, sc_, N, k)
            if sc == "BASE":
                dump[lab] = r
            print(f"  [{sc}] 상한가로 미룬 사기 {dfr}", flush=True)
            for h, lo, hi in H:
                if sc != "BASE" and not h.startswith(("시험", "전체")):
                    continue
                print(f"    {h:16s} 계좌: {P.fmt_d(P.daily_stats(r, lo if lo > '20170201' else '20170201', hi))}", flush=True)
            if sc == "BASE":
                print(f"    해마다: {P.years_line(P.daily_stats(r, '20170201', '20991231'))}", flush=True)
    out = os.getenv("Z_OUT")
    if out:
        idx = sorted(set.intersection(*[set(v.index) for v in dump.values()]))
        np.savez(out, days=np.array(idx), **{k: v.reindex(idx).fillna(0).to_numpy() for k, v in dump.items()})


if __name__ == "__main__":
    main()
