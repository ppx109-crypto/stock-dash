"""후보 전략 성적표 ③ — 단순 팩터 바구니(출발점 비교: 기술 지표 · 수급 · 공매도 · 증권사 의견 하나씩).
매달 첫 거래일 t · 그날 시총 200위 · z001 재료(모두 t까지 값) 위 20종목 → t+1 종가에 같은 몫 · 다음 달까지 · 날마다 평가 · 비용 왕복 0.5%(바뀐 몫).
python research/z047.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf as P  # noqa: E402
import z001 as Z  # noqa: E402

FACTORS = [("F1 12-1 모멘텀(수익250_20 높음)", "수익250_20", 1), ("F2 52주 고점 근접", "52주고점비", 1), ("F3 저변동(변동성20 낮음)", "변동성20", -1),
           ("F4 외국인 60일 순매수 많음", "외국인60", 1), ("F5 공매도 비중 낮음", "공매도20", -1), ("F6 목표가 여력 큼", "목표가여력", 1),
           ("F7 연기금 60일 순매수 적음(Z1 −)", "연기금60", -1)]


def run(C, inside, score, N=20, cost=0.005):
    days = list(C.index)
    months = [i for i, d in enumerate(days) if d >= "20170201" and days[i - 1][:6] != d[:6] and i + 1 < len(days)]
    R = C.pct_change(fill_method=None).fillna(0.0).clip(-0.5, 1.0)
    daily = pd.Series(0.0, index=days)
    w_prev = pd.Series(dtype=float)
    for m, i in enumerate(months):
        d = days[i]
        s = score.loc[d].where(inside.loc[d]).dropna()
        if len(s) < 50:
            continue
        top = s.sort_values(ascending=False).index[:N]
        w = pd.Series(1.0 / N, index=top)
        j0, j1 = i + 1, (months[m + 1] + 1 if m + 1 < len(months) else len(days) - 1)
        daily.iloc[j0] -= w.sub(w_prev, fill_value=0).abs().sum() * cost / 2
        seg = R.iloc[j0 + 1:j1 + 1]
        daily.iloc[j0 + 1:j1 + 1] += (seg[top].fillna(0.0) * w.values).sum(axis=1).values
        w_prev = w
    return daily


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, _ = Z.universe(C)
    for lab, f, sgn in FACTORS:
        r = run(C, inside, X[f] * sgn)
        print(f"== {lab} ==")
        for h, lo, hi in (("앞 2017 ~ 21", "20170201", "20220101"), ("뒤 2022 ~ 26", "20220101", "20991231"), ("시험 2023 ~", "20230101", "20991231")):
            print(f"  {h}: {P.fmt(P.account_stats(r, lo, hi))}", flush=True)


if __name__ == "__main__":
    main()
