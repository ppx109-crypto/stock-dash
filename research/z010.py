"""Z10 — 투신 단타 T4: 돈 흐름 — 시장 전체 투신 순매수는 '판단'인가 '돈 들어와서 사는 것'인가(docs/RL-TUSIN.md).
자료: market-data/investor_KSP · KSQ(코스피 · 코스닥 투자자별 순매수 금액 · 날마다) · index_KOSPI(지수 · 거래대금) · funds(MMF · 고객예탁금).
A. 같은 날: 투자자별 순매수 ÷ 거래대금과 그날 지수 등락의 상관(누가 오르는 날 사나).
B. 뒤쫓기: 투신 순매수(오늘)와 **앞 1 · 5 · 20일 지수 등락**의 상관 — 크면 '오른 뒤 돈이 들어와 사는' 꼴.
   + 투신 순매수와 MMF · 고객예탁금 변화(같은 날 · 앞날)의 상관.
C. 맞히기(따라 할 수 있나): 오늘(t) 투신 순매수 5분위 → **t+1 종가에 지수를 사서** 1 · 5 · 20일 뒤 지수 등락(앞 반 17~21 / 뒤 반 22~26).
미래 참조: C는 t까지 수급(장 끝나고 나옴) → t+1 종가 진입. A · B는 설명.
python research/z010.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WHO = ("투신", "연기금", "사모", "금융투자", "외국인", "개인")


def rows(name):
    return {str(r["date"]): r for r in json.loads((ROOT / "market-data" / name).read_text(encoding="utf-8"))["rows"]}


def main():
    idx = rows("index_KOSPI.json")
    inv = rows("investor_KSP.json")
    fund = rows("funds.json")
    days = sorted(set(idx) & set(inv))
    D = pd.DataFrame(index=days)
    D["지수"] = [idx[d]["종가"] for d in days]
    D["대금"] = [idx[d]["거래대금"] for d in days]
    for w in WHO:
        D[w] = [inv[d].get(w) for d in days]
        D[f"{w}%"] = D[w] / D["대금"] * 100                    # 순매수 ÷ 거래대금(%) — 단위가 같아(백만 원) 비율로
    D["MMF"] = [fund.get(d, {}).get("MMF") for d in days]
    D["예탁금"] = [fund.get(d, {}).get("고객예탁금") for d in days]
    r = D["지수"].pct_change()
    first = pd.Series([d < "20220101" for d in days], index=days)

    print("[A] 같은 날: 순매수 ÷ 거래대금과 그날 코스피 등락의 상관 [앞 반/뒤 반]")
    for w in WHO:
        c = lambda m: D.loc[m, f"{w}%"].corr(r[m])
        print(f"  {w:5s} {D[f'{w}%'].corr(r):+.2f} [{c(first):+.2f}/{c(~first):+.2f}]")

    print("\n[B] 뒤쫓기: 오늘 순매수 ÷ 거래대금과 '앞 n일' 코스피 등락의 상관(+면 오른 뒤에 삼)")
    for w in WHO:
        cells = []
        for n in (1, 5, 20):
            past = D["지수"].shift(1) / D["지수"].shift(1 + n) - 1           # t−1까지 n일
            cells.append(f"앞 {n}일 {D[f'{w}%'].corr(past):+.2f}")
        print(f"  {w:5s} " + " · ".join(cells))
    dm = D["MMF"].diff()
    dd = D["예탁금"].diff()
    print(f"  투신 vs MMF 변화 같은 날 {D['투신%'].corr(dm):+.2f} · 앞날 {D['투신%'].corr(dm.shift(1)):+.2f} · "
          f"vs 예탁금 변화 같은 날 {D['투신%'].corr(dd):+.2f} · 앞날 {D['투신%'].corr(dd.shift(1)):+.2f}")
    ac = [D["투신%"].autocorr(k) for k in (1, 2, 5)]
    print(f"  투신 순매수 이어짐(자기상관) 1일 {ac[0]:+.2f} · 2일 {ac[1]:+.2f} · 5일 {ac[2]:+.2f}")

    print("\n[C] 오늘 순매수 5분위 → t+1 종가에 코스피를 사서 h일 뒤 등락(%) [앞 반/뒤 반] · 바탕 = 아무 날")
    for w in ("투신", "연기금", "외국인", "개인"):
        q = D[f"{w}%"].rank(pct=True)
        print(f"  {w}")
        for h in (1, 5, 20):
            fwd = D["지수"].shift(-(1 + h)) / D["지수"].shift(-1) - 1
            cells = []
            for lo, hi, lab in ((0, 0.2, "가장 팖"), (0.4, 0.6, "가운데"), (0.8, 1.01, "가장 삼")):
                m = (q > lo) & (q <= hi) & fwd.notna()
                cells.append(f"{lab} {fwd[m].mean() * 100:+.2f} [{fwd[m & first].mean() * 100:+.2f}/{fwd[m & ~first].mean() * 100:+.2f}]")
            base = fwd.dropna()
            print(f"    {h:2d}일 · " + " · ".join(cells) + f" · 바탕 {base.mean() * 100:+.2f}")


if __name__ == "__main__":
    main()
