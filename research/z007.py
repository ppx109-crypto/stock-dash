"""Z7 — 투신 단타 T2d: 장중 가집계(과거 없음) 대신 **지금 1년치 15분봉으로 할 수 있는 대용**
(사용자 2026-10-07 "이미 1년이 있는데 왜 또 60일을 기다려?").
15분봉엔 '누가 샀나'가 없음 → 대신 '장 초반 거래량이 평소보다 크게 터졌나'로 투신 · 기관 큰 매수 날을 골라낼 수 있나.
- 판단 10:15: 전날 종가 대비 시장보다 +1% 넘게 오름 **그리고** 09:00 ~ 10:15 거래량 ÷ 그 종목 **앞 20거래일** 같은 시간 거래량 평균 ≥ k배.
- 사기 10:30 값 · 팔기 그날 종가 · 다음 날 종가 · 5일 뒤 · 시장(그날 같은 시각 대상 가운데값) 뺀 초과 · 아무 종목 바탕과 견줌.
- 그날 실제 투신 큰 매수(대상 위 10%) 비율 · 앞 반(2025-09 ~ 2026-03) / 뒤 반(2026-04 ~).
미래 참조: 거래량 평균은 그날 앞 20거래일만(shift) · 판단은 10:15 칸 끝까지 값 · 사기는 다음 칸.
python research/z007.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
import z005 as Y  # noqa: E402

COST = 0.0025
EARLY = ("0900", "0915", "0930", "0945", "1000")          # 09:00 ~ 10:15


def early_volume(codes, days):
    want = set(days)
    out = {}
    for c in codes:
        by = {}
        for f in sorted((Path("m15-kis") / c).glob("*.csv")):
            for ln in f.read_text(encoding="utf-8").splitlines():
                p = ln.split(",")
                if len(p) == 6 and p[0][8:] in EARLY:
                    by[p[0][:8]] = by.get(p[0][:8], 0.0) + float(p[5])
        s = pd.Series(by).sort_index()
        ratio = s / s.shift(1).rolling(20, min_periods=15).mean()     # 앞 20거래일만
        for d, v in ratio.items():
            if d in want and v == v:
                out[(d, c)] = v
    return pd.Series(out)


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    days = [d for d in C.index if d >= "20250918"]
    prevC = C.shift(1)
    codes = [c for c in C.columns if (Path("m15-kis") / c).is_dir()]
    prev = {(d, c): prevC.at[d, c] for d in days for c in codes if prevC.at[d, c] == prevC.at[d, c]}
    P = pd.DataFrame.from_dict(Y.m15_paths(codes, days, prev), orient="index", columns=["시가갭"] + Y.SLOTS)
    P.index = pd.MultiIndex.from_tuples(P.index, names=["날", "종목"])
    ins = inside.loc[days].stack()
    P = P.loc[P.index.intersection(ins[ins].index)]
    med = P.groupby(level="날").transform("median")
    ex = P - med
    vr = early_volume(codes, days)
    vr.index = pd.MultiIndex.from_tuples(vr.index, names=["날", "종목"])
    vr = vr.reindex(P.index)
    d1 = (C.shift(-1) / C - 1).stack()
    d5 = (C.shift(-5) / C - 1).stack()
    m1 = (C.shift(-1) / C - 1).where(inside).median(axis=1)
    m5 = (C.shift(-5) / C - 1).where(inside).median(axis=1)
    big = ((F["투신"] / F["vol"]).loc[days].where(inside.loc[days]).rank(axis=1, pct=True) > 0.9).stack()
    print("10:15 판단 · 10:30 사기 · 초과(%) = 시장 뺌 · [앞 반/뒤 반] · 비용 0.25%")
    for lab, sel in [("아무 종목(바탕)", ex["1000"] > -9)] + \
                    [(f"+1% 오름 · 장초 거래량 ≥ {k}배", (ex["1000"] > 0.01) & (vr >= k)) for k in (1, 2, 3, 5)] + \
                    [("+1% 오름 · 장초 거래량 < 1배", (ex["1000"] > 0.01) & (vr < 1))]:
        idx = P.index[sel.fillna(False).to_numpy()]
        g, gm = P.loc[idx], med.loc[idx]
        stk = ((1 + g["1515"]) / (1 + g["1015"])).to_numpy()
        mkt = ((1 + gm["1515"]) / (1 + gm["1015"])).to_numpy()
        ds = [d for d, _ in idx]
        r0 = stk - mkt
        r1 = stk * (1 + d1.reindex(idx).to_numpy()) - mkt * (1 + m1.reindex(ds).to_numpy())
        r5 = stk * (1 + d5.reindex(idx).to_numpy()) - mkt * (1 + m5.reindex(ds).to_numpy())
        b = big.reindex(idx).fillna(False).to_numpy()
        first = np.array([d < "20260401" for d in ds])
        f = lambda v: f"{np.nanmean(v) * 100:+.2f}[{np.nanmean(v[first]) * 100:+.2f}/{np.nanmean(v[~first]) * 100:+.2f}]"
        print(f"{lab:22s} {len(idx):6d}건 · 투신 큰 매수 {b.mean():4.0%} · 종가 {f(r0)} · 다음 날 {f(r1)} · 5일 {f(r5)} · 종가 비용 뒤 {np.nanmean(r0 - COST) * 100:+.2f}")


if __name__ == "__main__":
    main()
