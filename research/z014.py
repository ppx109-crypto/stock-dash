"""N3 — 좁은 장 RL(docs/RL-NARROW.md): '이끄는 무리'가 그 뒤도 이끄나.
- 판단일 t(5거래일마다): 그날 시총 200위 종목을 **t까지 120거래일** 하루 등락의 상관으로 묶음(평균 연결 · 상관 거리 · 18무리).
  무리 강도 = 무리 안 종목의 20일 수익 가운데값(t−20 → t). 종목마다 '자기 무리 강도'와 '자기 20일 수익'(견줌용).
- 잴 값: t+1 종가에 사서 20거래일 초과(그날 대상 가운데값 뺌) · IC(무리 강도 · 종목 강도) · 가장 센 무리(1등) 종목 vs 나머지.
- 국면별(좁은 오름장 · 내림장 · 넓은 장 — z008.regimes) · 기간별(2017~19 · 2020~22 · 2023~26).
미래 참조: 묶음 · 강도 모두 t까지 값 · 진입 t+1 종가.
python research/z014.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
import z008 as N  # noqa: E402

import os
K = 18
LOOK = 120
FORM = int(os.getenv("N_FORM", "20"))       # 무리 강도 기간
HOLD = int(os.getenv("N_HOLD", "20"))       # 들고 있는 기간


def main():
    C, *_ = Z.load()
    inside, size = Z.universe(C)
    reg, _ = N.regimes(C, size)
    r1 = C.pct_change(fill_method=None)
    mom = C / C.shift(FORM) - 1
    fwd = C.shift(-(1 + HOLD)) / C.shift(-1) - 1
    days = [d for i, d in enumerate(C.index) if d >= Z.START and i % 5 == 0 and i + 1 + HOLD < len(C.index)]
    pos = {d: i for i, d in enumerate(C.index)}
    rec = []
    for d in days:
        i = pos[d]
        codes = [c for c in C.columns if inside.at[d, c]]
        R = r1.iloc[i - LOOK + 1:i + 1][codes]
        R = R.loc[:, R.notna().sum() >= LOOK * 0.9]
        if R.shape[1] < 60:
            continue
        corr = R.corr().fillna(0).to_numpy().copy()
        np.fill_diagonal(corr, 1)
        dist = np.clip(1 - corr, 0, 2)
        lab = fcluster(linkage(squareform(dist, checks=False), "average"), K, criterion="maxclust")
        cl = pd.Series(lab, index=R.columns)
        m = mom.loc[d, cl.index]
        strength = m.groupby(cl).median()
        csize = cl.value_counts()
        ok = strength[csize[strength.index] >= 3]                     # 3종목 이상 무리만
        rank = ok.rank(ascending=False)
        f = fwd.loc[d, cl.index]
        ex = f - f.median()
        st = cl.map(ok)
        top = cl.map(rank) == 1
        df = pd.DataFrame({"ex": ex, "무리": st, "종목": m, "1등무리": top}).dropna(subset=["ex", "무리", "종목"])
        if len(df) < 40:
            continue
        rec.append((d, reg[d], df["무리"].rank().corr(df["ex"].rank()), df["종목"].rank().corr(df["ex"].rank()),
                    df.loc[df["1등무리"], "ex"].mean() - df.loc[~df["1등무리"], "ex"].mean(), int(df["1등무리"].sum())))
    E = pd.DataFrame(rec, columns=["날", "국면", "IC무리", "IC종목", "1등무리차", "1등무리수"])
    E["기간"] = E["날"].map(N.period)
    print(f"강도 {FORM}일 · 들기 {HOLD}일 · 판단 날:", len(E), E["국면"].value_counts().to_dict())
    print("국면 · 기간별 — IC(무리 강도) · IC(종목 20일 수익) · 1등 무리 − 나머지(20일 %) · 날 수")
    for rg in ("좁은 오름장", "내림장", "넓은 장"):
        for p in ("2017~19", "2020~22", "2023~26", "전체"):
            g = E[(E["국면"] == rg) & ((E["기간"] == p) if p != "전체" else True)]
            if len(g) < 3:
                continue
            t = g["IC무리"].mean() / (g["IC무리"].std(ddof=1) + 1e-12) * math.sqrt(len(g) / max(1, HOLD / 5))
            print(f"  {rg:5s} {p:7s} 무리 {g['IC무리'].mean():+.3f}(t {t:+.1f}) · 종목 {g['IC종목'].mean():+.3f} · "
                  f"1등 무리 {g['1등무리차'].mean() * 100:+.2f}% (나을 날 {(g['1등무리차'] > 0).mean():.0%}) · {len(g)}날")
    Z.SP.mkdir(parents=True, exist_ok=True)
    E.to_csv(Z.SP / "z014.csv", index=False)


if __name__ == "__main__":
    main()
