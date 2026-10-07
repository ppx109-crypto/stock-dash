"""Z9 — 투신 단타 T3: 달력(월말 · 분기말 수익률 관리 · 6/12월 지수 정기변경 · 연말 배당)과 투신 매매 · 그 뒤 되돌림(docs/RL-TUSIN.md).
A. 시장 전체: 대상(그날 시총 200위) 투신 순매수 금액 합 ÷ 대상 거래대금 합(%)을 '달 끝까지 남은 거래일'(−5 ~ +5)별 평균 — 분기말 달 vs 다른 달.
   + 6 · 12월 둘째 목요일(선물 · 옵션 만기 = 코스피200 정기변경 직전) 앞뒤 · 12월 마지막 5일.
B. 종목: 분기 마지막 5거래일에 투신이 가장 많이 산 종목(그 5일 순매수 ÷ 거래량 · 대상 위 10%) →
   분기 마지막 날 **다음 날 종가**에 샀을 때 5 · 10 · 20일 초과(그날 대상 가운데값 뺀) — 분기말 아닌 달 끝과 견줌.
   (수익률 관리라면 분기말에 끌어올린 종목이 새 분기 초에 되밀림.)
미래 참조: B의 고르기는 그 5일까지 수급(장 끝나고 나옴) → 다음 날 종가 진입. 달력(달 끝 · 둘째 목요일)은 미리 아는 날.
python research/z009.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402


def second_thursday(y, m):
    d = date(y, m, 1)
    first = (3 - d.weekday()) % 7 + 1
    return f"{y}{m:02d}{first + 7:02d}"


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    days = [d for d in C.index if d >= Z.START]
    idx = pd.Index(days)
    month = pd.Series([d[:6] for d in days], index=idx)
    # 달 끝까지 남은 거래일(0 = 마지막 날) · 달 처음부터 몇째(1 = 첫날)
    to_end = month.groupby(month).cumcount(ascending=False)
    from_start = month.groupby(month).cumcount() + 1
    val = (F["투신"] * C).where(inside).loc[days].sum(axis=1)
    tv = F["value"].where(inside).loc[days].sum(axis=1)
    share = val / tv * 100                                     # 투신 순매수 ÷ 거래대금(%)
    qend = month.str[4:6].isin(["03", "06", "09", "12"])
    print("[A] 투신 순매수 ÷ 대상 거래대금(%) · 평균(앞 반 17~21 / 뒤 반 22~26)")
    first = pd.Series([d < "20220101" for d in days], index=idx)

    def avg(mask):
        m = mask & share.notna()
        return f"{share[m].mean():+.3f} ({share[m & first].mean():+.3f} / {share[m & ~first].mean():+.3f}) n={int(m.sum())}"
    print("  아무 날:", avg(pd.Series(True, index=idx)))
    for k in (4, 3, 2, 1, 0):
        print(f"  달 끝 {k}일 전 · 분기말 달: {avg((to_end == k) & qend)} · 다른 달: {avg((to_end == k) & ~qend)}")
    for k in (1, 2, 3):
        print(f"  다음 달 {k}째 날 · 분기 시작: {avg((from_start == k) & month.str[4:6].isin(['01', '04', '07', '10']))}")
    # 6 · 12월 둘째 목요일(만기) 앞뒤
    exp = {second_thursday(int(y), m) for y in range(2017, 2027) for m in (6, 12)}
    pos = {d: i for i, d in enumerate(days)}
    near = {}
    for e in exp:
        k = next((pos[d] for d in days if d >= e), None)
        if k is None:
            continue
        for off in range(-3, 3):
            if 0 <= k + off < len(days):
                near.setdefault(off, []).append(days[k + off])
    for off in sorted(near):
        print(f"  6 · 12월 만기일 {off:+d}일: {avg(idx.isin(near[off]))}")
    print(f"  12월 마지막 5일: {avg((to_end <= 4) & (month.str[4:6] == '12'))} · 1월 첫 5일: {avg((from_start <= 5) & (month.str[4:6] == '01'))}")

    # B: 분기 마지막 5일 투신 큰 매수 종목 → 다음 날 종가 진입 뒤
    print("\n[B] 달 마지막 5일 투신 순매수(÷거래량) 위 10% 종목 → 달 마지막 날 다음 날 종가에 사서 초과(%) [앞 반/뒤 반] · 건수")
    flow5 = F["투신"].rolling(5).sum() / F["vol"].rolling(5).sum()
    last_days = [d for d in days if to_end[d] == 0]
    res = {}
    for d in last_days:
        k = pos[d]
        if k + 1 + 20 >= len(days):
            continue
        q = flow5.loc[d].where(inside.loc[d]).rank(pct=True)
        top = q[q > 0.9].index
        e = days[k + 1]
        for h in (5, 10, 20):
            x = days[k + 1 + h]
            r = (C.loc[x] / C.loc[e] - 1).where(inside.loc[d])
            exr = (r - r.median())[top].mean()
            res.setdefault(("분기말" if d[4:6] in ("03", "06", "09", "12") else "다른 달", h), []).append((d, exr))
    for kind in ("분기말", "다른 달"):
        cells = []
        for h in (5, 10, 20):
            v = res.get((kind, h), [])
            a = np.array([x for _, x in v], dtype=float)
            f_ = np.array([d < "20220101" for d, _ in v])
            cells.append(f"{h}일 {np.nanmean(a) * 100:+.2f} [{np.nanmean(a[f_]) * 100:+.2f}/{np.nanmean(a[~f_]) * 100:+.2f}] 오른 달 {np.mean(a > 0):.0%}")
        print(f"  {kind:5s} " + " · ".join(cells) + f" · {len(res.get((kind, 5), []))}번")


if __name__ == "__main__":
    main()
