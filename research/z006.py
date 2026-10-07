"""Z6 — 투신 단타 T2c(사용자 2026-10-07 "2.5% 오르는데 1% 오르고 나서 사서 팔아도 1% 이득이면 큰데").
T2의 '+2.5%'는 장이 끝난 뒤에야 아는 '투신이 크게 산 날'만 모은 값(결과로 고른 표본) → 장중에 **그때 알 수 있는 것만**으로 사면?
- 판단: 10:15(10:00 칸 끝)까지 전날 종가 대비 초과 수익이 +1% 넘게 오른 대상 종목(그날 대상 가운데값 뺌 · 그 시각까지 값만).
- 사기: 다음 칸 끝(10:30) 값 · 팔기: 14:45 · 15:30(종가) · 다음 날 종가 · 5일 뒤 종가. 비용 0.25%(세금 0.18 + 수수료 · 미끄러짐) 뺀 값도.
- 견줌: 그중 '그날 투신이 실제로 크게 산 날'(장 끝나야 앎 · 못 고름)과 아닌 날.
- 여러 문턱(+1 · +2 · +3%)과 판단 시각(09:15 · 10:15 · 11:15) · 앞 반(2025-09 ~ 2026-03) · 뒤 반(2026-04 ~) 따로.
미래 참조: 판단은 그 시각까지 15분봉만 · 사기는 다음 칸 · 가운데값도 그 시각 칸 값만(그날 같은 시각 횡단면).
python research/z006.py
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
    # 다음 날 · 5일 뒤 종가(전날 종가 대비가 아니라 '사고 나서'를 셈하려고 그날 종가 대비)
    nxt1 = (C.shift(-1) / C - 1).stack()
    nxt5 = (C.shift(-5) / C - 1).stack()
    mk1 = (C.shift(-1) / C - 1).where(inside).median(axis=1)
    mk5 = (C.shift(-5) / C - 1).where(inside).median(axis=1)
    big = ((F["투신"] / F["vol"]).loc[days].where(inside.loc[days]).rank(axis=1, pct=True) > 0.9).stack()
    rows = []
    for at, buy in (("0900", "0915"), ("1000", "1015"), ("1100", "1115")):
        for th in ((-9.0, 0.01, 0.02, 0.03) if at == "1000" else (0.01, 0.02, 0.03)):
            sel = ex[at] > th
            idx = ex.index[sel.to_numpy()]
            if len(idx) < 50:
                continue
            g = P.loc[idx]
            gm = med.loc[idx]
            entry = (1 + g[buy]) / (1 + 0)                        # 전날 종가 = 1 기준 값
            def ret(x, xm):
                r = (1 + x) / entry - 1
                rm = (1 + xm) / (1 + gm[buy]) - 1
                return r - rm                                      # 시장(같은 시각 가운데값)만큼 뺀 초과
            out = {"판단": f"{at[:2]}:{int(at[2:]) + 15:02d}", "문턱": ("아무 종목(바탕)" if th < -1 else f"+{th:.0%}"), "건수": len(idx),
                   "→14:45": ret(g["1430"], gm["1430"]), "→종가": ret(g["1515"], gm["1515"])}
            close_idx = pd.MultiIndex.from_tuples(idx)
            d1 = nxt1.reindex(close_idx).to_numpy()
            d5 = nxt5.reindex(close_idx).to_numpy()
            m1 = mk1.reindex([d for d, _ in idx]).to_numpy()
            m5 = mk5.reindex([d for d, _ in idx]).to_numpy()
            mkt_day = ((1 + gm["1515"]) / (1 + gm[buy])).to_numpy()            # 시장(가운데값) 산 때 → 그날 종가
            stk_day = ((1 + g["1515"]) / entry).to_numpy()
            out["→다음날 종가"] = stk_day * (1 + d1) - mkt_day * (1 + m1)
            out["→5일 뒤 종가"] = stk_day * (1 + d5) - mkt_day * (1 + m5)
            b = big.reindex(close_idx).fillna(False).to_numpy()
            first = np.array([d < "20260401" for d, _ in idx])
            res = {"판단": out["판단"], "문턱": out["문턱"], "건수": out["건수"], "그날 투신 큰 매수 비율": f"{b.mean():.0%}"}
            for k in ("→14:45", "→종가", "→다음날 종가", "→5일 뒤 종가"):
                v = np.asarray(out[k], dtype=float)
                res[k] = f"{np.nanmean(v) * 100:+.2f}(비용 뒤 {np.nanmean(v - COST) * 100:+.2f}) 앞{np.nanmean(v[first]) * 100:+.2f}/뒤{np.nanmean(v[~first]) * 100:+.2f}"
                if k == "→종가":
                    res["→종가 · 투신 큰 매수 날만(못 고름)"] = f"{np.nanmean(v[b]) * 100:+.2f}"
                    res["→종가 · 아닌 날"] = f"{np.nanmean(v[~b]) * 100:+.2f}"
                    res["→종가 오를 확률"] = f"{np.mean(v[~np.isnan(v)] > COST):.0%}"
            rows.append(res)
    for r in rows:
        print(" · ".join(f"{k} {v}" for k, v in r.items()))


if __name__ == "__main__":
    main()
