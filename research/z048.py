"""F5 공매도 비중 낮음 — 버티나(퀀트 연구 · z047에서 두 반 모두 코스피 +9.5 / +11.0%p).
① 고원: 위 10 · 20 · 40종목 · 비용 0.5 / 1.0% ② 공매도 금지 기간(2020-03-16 ~ 2021-05-02 · 2023-11-06 ~ 2025-03-30)에 산 달 vs 허용 기간 달
③ 고른 종목의 성질(시총 순위 · 변동성20 · 수익250_20 · 거래대금증가 · 외국인60 순위)이 바탕과 어떻게 다른가 → 다른 팩터로 설명되나
④ 시총 무리 안에서 고르기(1 ~ 50 · 51 ~ 100 · 101 ~ 200위 각각 위 7종목) — 크기 효과를 걷어도 남나.
python research/z048.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf as P  # noqa: E402
import z001 as Z  # noqa: E402
from z047 import run  # noqa: E402

BAN = (("20200316", "20210502"), ("20231106", "20250330"))


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    s = -X["공매도20"]
    H = (("앞 2017 ~ 21", "20170201", "20220101"), ("뒤 2022 ~ 26", "20220101", "20991231"), ("시험 2023 ~", "20230101", "20991231"))
    print("① 고원")
    for N in (10, 20, 40):
        for cost in (0.005, 0.010):
            r = run(C, inside, s, N, cost)
            print(f"  위 {N} · 비용 {cost * 100:.1f}%: " + " | ".join(f"{h} CAGR {P.account_stats(r, lo, hi)['CAGR'] * 100:+.1f}% MDD {P.account_stats(r, lo, hi)['MDD'] * 100:.0f}%" for h, lo, hi in H), flush=True)
    base = run(C, inside, pd.DataFrame(np.random.default_rng(0).random(C.shape), index=C.index, columns=C.columns), 200, 0.0)
    r20 = run(C, inside, s, 20, 0.005)
    inban = pd.Series([any(a <= d <= b for a, b in BAN) for d in r20.index], index=r20.index)
    print("② 공매도 금지 vs 허용(날마다 수익 연율 · 위 20 − 200위 같은 몫)")
    for lab, m in (("금지 기간", inban), ("허용 기간", ~inban)):
        m = m & (r20.index >= "20170201")
        print(f"  {lab}: 위 20 연율 {r20[m].mean() * 245 * 100:+.1f}% · 바탕 {base[m].mean() * 245 * 100:+.1f}% · 차이 {(r20[m].mean() - base[m].mean()) * 245 * 100:+.1f}%p · 날 {int(m.sum())}", flush=True)
    print("③ 고른 종목의 성질(매달 위 20 평균 순위 0 ~ 1 · 바탕 0.5)")
    days = list(C.index)
    months = [d for i, d in enumerate(days) if d >= "20170201" and days[i - 1][:6] != d[:6]]
    feats = {"시총(1 = 큼)": size, "변동성20": X["변동성20"], "12-1 모멘텀": X["수익250_20"], "거래대금증가": X["거래대금증가"], "외국인60": X["외국인60"], "신용잔고율": X["신용잔고율"]}
    for lab, f in feats.items():
        v = []
        for d in months:
            sc = s.loc[d].where(inside.loc[d]).dropna()
            top = sc.sort_values(ascending=False).index[:20]
            rk = f.loc[d].where(inside.loc[d]).rank(pct=True)
            v.append(rk.reindex(top).mean())
        print(f"  {lab}: {np.nanmean(v):.2f}", flush=True)
    print("④ 시총 무리 안에서(각 무리 위 7종목 · 합 21)")
    rank = size.rank(axis=1, ascending=False)
    parts = []
    for lo_, hi_ in ((1, 50), (51, 100), (101, 200)):
        g = inside & (rank >= lo_) & (rank <= hi_)
        parts.append(run(C, g, s, 7, 0.005))
    rr = sum(parts) / 3
    print("  " + " | ".join(f"{h} CAGR {P.account_stats(rr, lo, hi)['CAGR'] * 100:+.1f}% MDD {P.account_stats(rr, lo, hi)['MDD'] * 100:.0f}% 코스피 초과 {P.account_stats(rr, lo, hi)['KOSPI초과'] * 100:+.1f}%p" for h, lo, hi in H), flush=True)


if __name__ == "__main__":
    main()
