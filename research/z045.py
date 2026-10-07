"""P10 — 가치 바구니(z042에서 보고서 날 가치 IC +0.086 · 두 반 + → 계좌 전략으로).
매달 첫 거래일 t(판단) — 그날 시총 200위 · 각 종목의 **접수일 < t 인 마지막 분기 · 반기 · 사업보고서**(quarter-data) 숫자만:
  이익 수익률 = 영업이익(연환산: 1분기 × 4 · 반기 × 2 · 3분기 × 4/3 · 사업 × 1) ÷ 그날 시총 · 장부 비율 = 자본 ÷ 그날 시총(적자 · 자본잠식 빼지 않고 순위로).
  점수 = 두 순위의 평균 → 위 N종목(20 · 40)을 **t+1 종가에 같은 몫으로** 사서 다음 달 판단 다음 날 종가까지 들기(날마다 평가).
  비용 = 바뀐 몫 × 왕복 0.5%(수수료 · 세금 · 슬리피지 넉넉히) · 스트레스 1.0%.
비교: 시총 200위 같은 몫(바탕) · 코스피 · 코스닥. 기간: 앞(2017 ~ 21) · 뒤(2022 ~ 26) · 시험(2023 ~ ).
한계(숨기지 않음): 종목 모음이 2026-09 시총으로 고른 500종목(상장폐지 빠짐) → **가치주 성적이 부풀려질 수 있는 쪽**.
python research/z045.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf as P  # noqa: E402
import z001 as Z  # noqa: E402

ANN = {"1분기": 4.0, "반기": 2.0, "3분기": 4 / 3, "사업": 1.0}


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return np.nan


def timeline(c):
    p = Path("quarter-data") / f"{c}.json"
    if not p.exists():
        return [], []
    rows = (json.loads(p.read_text(encoding="utf-8")).get("rows")) or {}
    got = []
    for k, v in rows.items():
        if v and str(v.get("접수번호", ""))[:8].isdigit():
            got.append((str(v["접수번호"])[:8], num(v.get("영업이익")) * ANN.get(k.split("-")[-1], 1.0), num(v.get("자본"))))
    got.sort()
    return [g[0] for g in got], got


def main():
    C, *_ = Z.load()
    C = C[C.index >= "20161001"]
    inside, size = Z.universe(C)
    days = list(C.index)
    TL = {c: timeline(c) for c in C.columns}
    months = [d for i, d in enumerate(days) if d >= "20170201" and (i == 0 or days[i - 1][:6] != d[:6]) and i + 1 < len(days)]
    R = C.pct_change(fill_method=None).fillna(0.0).clip(-0.5, 1.0)
    for N in (20, 40):
        for cost in (0.005, 0.010):
            w_prev = pd.Series(dtype=float)
            daily = pd.Series(0.0, index=days)
            base = pd.Series(0.0, index=days)
            picks_log = []
            for m, d in enumerate(months):
                i = days.index(d)
                ins = inside.loc[d]
                cand = ins[ins].index
                ey, bp = {}, {}
                for c in cand:
                    ds, rows = TL[c]
                    k = np.searchsorted(ds, d) - 1                 # 접수일 < d
                    if k < 0 or not np.isfinite(size.at[d, c]) or size.at[d, c] <= 0:
                        continue
                    _, op, eq = rows[k]
                    if np.isfinite(op):
                        ey[c] = op / size.at[d, c]
                    if np.isfinite(eq):
                        bp[c] = eq / size.at[d, c]
                s = (pd.Series(ey).rank(pct=True).reindex(cand).fillna(0.5) + pd.Series(bp).rank(pct=True).reindex(cand).fillna(0.5)) / 2
                s = s[[c for c in cand if c in ey or c in bp]]
                top = s.sort_values(ascending=False).index[:N]
                w = pd.Series(1.0 / len(top), index=top)
                turn = w.sub(w_prev, fill_value=0).abs().sum()
                j0 = i + 1                                           # t+1 종가에 맞춤
                j1 = days.index(months[m + 1]) + 1 if m + 1 < len(months) else len(days) - 1
                if j0 >= len(days):
                    break
                daily.iloc[j0] -= turn * cost / 2 * 2 / 2           # 바뀐 몫 × 왕복 비용의 절반씩(사고팔기) ≈ turn × cost / 2
                seg = R.iloc[j0 + 1:j1 + 1]
                daily.iloc[j0 + 1:j1 + 1] += (seg[top].fillna(0.0) * w.values).sum(axis=1).values
                bw = ins[ins].index
                base.iloc[j0 + 1:j1 + 1] += seg[bw].fillna(0.0).mean(axis=1).values
                w_prev = w
                picks_log.append((d, len(top)))
            print(f"== 가치 위 {N}종목 · 달마다 · 비용 왕복 {cost * 100:.1f}% ==")
            for lab, lo, hi in (("앞 2017 ~ 21", "20170201", "20220101"), ("뒤 2022 ~ 26", "20220101", "20991231"), ("시험 2023 ~ ", "20230101", "20991231")):
                print(f"  {lab}: {P.fmt(P.account_stats(daily, lo, hi))}")
                print(f"  {'':12s} 바탕(200위 같은 몫): {P.fmt(P.account_stats(base, lo, hi))}", flush=True)


if __name__ == "__main__":
    main()
