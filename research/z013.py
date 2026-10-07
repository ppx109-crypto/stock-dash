"""Z13 — 투신 단타 T5: 이어 사기(docs/RL-TUSIN.md).
A. 종목 투신 순매수의 이어짐: 오늘 크게 샀으면(대상 위 10%) 내일 · 3일 · 5일 뒤에도 사고 있을 확률 · 순매수 자기상관.
B. '새로 사기 시작'(앞 10일 동안 순매수 합 ≤ 0인데 오늘 위 10%) vs '이미 사던 중'(앞 10일도 위 1/3 쪽) →
   **t+1 종가에 사서** 5 · 20일 초과(그날 대상 가운데값 뺌) [앞 반/뒤 반] · 바탕(아무 날 같은 셈)과의 차이.
미래 참조: 고르기는 t까지 수급(장 끝나고 나옴) · 진입 t+1 종가.
python research/z013.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    ok = pd.DataFrame(np.repeat((C.index >= Z.START)[:, None], C.shape[1], 1), index=C.index, columns=C.columns) & inside
    x = (F["투신"] / F["vol"]).where(ok)
    q = x.rank(axis=1, pct=True)
    big = q > 0.9
    buy = F["투신"] > 0
    print("[A] 오늘 투신 크게 산 종목(위 10%)이 그 뒤에도 순매수일 확률 · 아무 종목 바탕")
    for k in (1, 3, 5):
        fut = buy.shift(-k)
        m = big & fut.notna()
        b = ok & fut.notna()
        print(f"  {k}일 뒤 순매수: {fut[m].mean().mean():.0%}  (바탕 {fut[b].mean().mean():.0%})")
    ac = [x.stack().dropna().groupby(level=1).apply(lambda s: s.autocorr(k)).median() for k in (1, 5)]
    print(f"  종목 투신 순매수 ÷ 거래량 자기상관(종목 가운데값) 1일 {ac[0]:+.2f} · 5일 {ac[1]:+.2f}")

    prior10 = F["투신"].shift(1).rolling(10).sum()
    prior_q = (F["투신"].shift(1).rolling(10).sum() / F["vol"].shift(1).rolling(10).sum()).where(ok).rank(axis=1, pct=True)
    groups = {"새로 사기 시작(앞 10일 ≤ 0 · 오늘 위 10%)": big & (prior10 <= 0),
              "이미 사던 중(앞 10일 위 1/3 · 오늘 위 10%)": big & (prior_q > 2 / 3),
              "오늘 위 10% 전체": big}
    first = pd.Series(C.index < "20220101", index=C.index)
    print("\n[B] t+1 종가에 사서 h일 · 초과(%) − 바탕 [앞 반/뒤 반] · 시장보다 나을 확률")
    for h in (5, 20):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        f = f.where(ok)
        ex = f.sub(f.median(axis=1), axis=0)
        base = ex.stack().dropna().mean()
        bf, bb = ex[first].stack().dropna().mean(), ex[~first].stack().dropna().mean()
        for lab, m in groups.items():
            v = ex.where(m)
            a, b_ = v[first].stack().dropna(), v[~first].stack().dropna()
            s = v.stack().dropna()
            print(f"  {h:2d}일 {lab:30s} {len(s):6d}건 · {(s.mean() - base) * 100:+.2f}%p [{(a.mean() - bf) * 100:+.2f}/{(b_.mean() - bb) * 100:+.2f}] · 나을 확률 {(s > 0).mean():.0%}")


if __name__ == "__main__":
    main()
