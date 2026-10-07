"""2차 연구 §4 — F5(공매도 비중 낮음) 잔여 알파: 다른 요인의 대리인가? (docs/PREREG-2.md · 대상 = 쪼개기 고친 그날 시총 200위)
① 달 첫 거래일 t 횡단면: F5 점수(−공매도 비중 20일 평균)와 통제 9개의 순위 상관(달 평균).
② Fama-MacBeth: 다음 달(t+1 종가 → 다음 달 첫 거래일+1 종가) 초과 수익 ~ F5 + 통제 9개(모두 0 ~ 1 순위) → F5 계수 평균 · Newey-West t(지연 3) · 학습 · 검증 · 시험 따로.
   통제: 크기(log 시총) · 가치(장부 자본 ÷ 시총 · DART 접수일 다음 날부터) · 모멘텀(12-1) · 변동성(60일) · 베타(250일 · 코스피) · 유동성(log 20일 거래대금)
        · 회전율(20일 거래량 ÷ 주식수) · 외국인 60일 순매수 ÷ 거래량 · 기관 60일 순매수 ÷ 거래량.
③ 시계열: F5 위 20(달마다 · 비용 뺀 z054 흐름 대신 여기선 비용 전) − 바탕 = α + Σ β × (요인 위 20 − 아래 20) → α 연율 · NW t.
python research/z056.py
"""
import json
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

caps.ADJ = os.getenv("Z_CAPS", "adj") == "adj"
PER = (("학습 2017 ~ 20", "20170101", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"), ("전체", "20170101", "20991231"))


def equity_frame(C):
    days = list(C.index)
    out = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for c in C.columns:
        p = Path("quarter-data") / f"{c}.json"
        if not p.exists():
            continue
        q = json.loads(p.read_text(encoding="utf-8")).get("rows") or {}
        got = []
        for v in q.values():
            no = str((v or {}).get("접수번호", ""))
            try:
                eq = float(str(v.get("자본")).replace(",", ""))
            except (TypeError, ValueError):
                continue
            if no[:8].isdigit():
                got.append((no[:8], eq))
        if not got:
            continue
        s = pd.Series(np.nan, index=C.index)
        for d, eq in sorted(got):
            j = int(np.searchsorted(days, d, side="right"))     # 접수일 다음 거래일부터
            if j < len(days):
                s.iloc[j] = eq
        out[c] = s.ffill()
    return out


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    R = C.pct_change(fill_method=None)
    k = P.ROOT / "market-data/index_KOSPI.json"
    kp = pd.Series({str(r["date"]): float(r["종가"]) for r in json.loads(k.read_text(encoding="utf-8"))["rows"] if r.get("종가")}).reindex(C.index).ffill()
    kr = kp.pct_change()
    beta = R.rolling(250, min_periods=200).cov(kr) .div(kr.rolling(250, min_periods=200).var(), axis=0)
    shares = size / C
    ctrl = {
        "크기": np.log(size),
        "가치": equity_frame(C) / size,
        "모멘텀": X["수익250_20"],
        "변동성60": R.rolling(60, min_periods=45).std(),
        "베타": beta,
        "유동성": np.log(F["value"].rolling(20, min_periods=15).mean()),
        "회전율": F["vol"].rolling(20, min_periods=15).mean() / shares,
        "외국인60": X["외국인60"],
        "기관60": F["기관"].rolling(60, min_periods=45).sum() / F["vol"].rolling(60, min_periods=45).sum(),
    }
    f5 = -X["공매도20"]
    days = list(C.index)
    months = [i for i, d in enumerate(days) if d >= "20170201" and days[i - 1][:6] != d[:6] and i + 1 < len(days)]
    rows, corr = [], []
    for m, i in enumerate(months[:-1]):
        d = days[i]
        j0, j1 = i + 1, months[m + 1] + 1
        if j1 >= len(days):
            break
        ok = inside.loc[d]
        fw = C.iloc[j1] / C.iloc[j0] - 1
        fw = fw.where(ok)
        fw = fw - fw.median()
        df = pd.DataFrame({"F5": f5.loc[d], **{k_: v.loc[d] for k_, v in ctrl.items()}, "y": fw}).where(ok, np.nan).dropna()
        if len(df) < 60:
            continue
        rk = df.drop(columns="y").rank(pct=True)
        corr.append(rk.corr(method="spearman")["F5"].drop("F5"))
        A = np.column_stack([np.ones(len(rk)), rk.to_numpy()])
        b1 = np.linalg.lstsq(A, df["y"].to_numpy(), rcond=None)[0]
        A0 = np.column_stack([np.ones(len(rk)), rk["F5"].to_numpy()])
        b0 = np.linalg.lstsq(A0, df["y"].to_numpy(), rcond=None)[0]
        rows.append({"날": d, "F5홀로": b0[1], "F5통제": b1[1], **{f"b_{c_}": b1[2 + n] for n, c_ in enumerate(ctrl)}, "n": len(df)})
    B = pd.DataFrame(rows).set_index("날")
    cm = pd.DataFrame(corr).mean()
    print("① F5 점수와 통제 요인의 순위 상관(달 평균 · +면 '공매도 비중 낮음'이 그 요인이 큰 쪽):")
    print("   " + " · ".join(f"{k_} {v:+.2f}" for k_, v in cm.items()))
    print(f"② Fama-MacBeth(달 {len(B)} · 종목 평균 {B['n'].mean():.0f}) · 계수 = 순위 0 → 1로 갈 때 다음 달 초과 수익 차(%p):")
    for h, lo, hi in PER:
        b = B[(B.index >= lo) & (B.index < hi)]
        if len(b) < 6:
            continue
        line = (f"   {h:14s} 달 {len(b):3d} · F5 홀로 {b['F5홀로'].mean() * 100:+.2f}%p(NW t {P.nw_t(b['F5홀로'], 3):+.1f}) · "
                f"F5 통제 뒤 {b['F5통제'].mean() * 100:+.2f}%p(NW t {P.nw_t(b['F5통제'], 3):+.1f})")
        print(line)
        print("      통제 계수: " + " · ".join(f"{c_} {b['b_' + c_].mean() * 100:+.2f}(t {P.nw_t(b['b_' + c_], 3):+.1f})" for c_ in ctrl))
    # ③ 시계열 요인 회귀
    from z047 import run
    base = pd.DataFrame(1.0, index=C.index, columns=C.columns).where(C.notna())
    rb = run(C, inside, base, 200, 0.0)
    y = run(C, inside, f5, 20, 0.0) - rb
    fac = {}
    for k_, v in ctrl.items():
        fac[k_] = run(C, inside, v, 20, 0.0) - run(C, inside, -v, 20, 0.0)
    idx = [d for d in C.index if d >= "20170301"]
    Y = y.reindex(idx).to_numpy()
    Xf = np.column_stack([np.ones(len(idx))] + [fac[k_].reindex(idx).to_numpy() for k_ in ctrl])
    print("③ 시계열: F5 위 20 − 바탕 = α + Σβ × (요인 위 20 − 아래 20) · 날마다(비용 전):")
    for h, lo, hi in PER:
        msk = np.array([lo <= d < hi for d in idx])
        if msk.sum() < 200:
            continue
        b = np.linalg.lstsq(Xf[msk], Y[msk], rcond=None)[0]
        res = Y[msk] - Xf[msk] @ b
        alpha_series = res + b[0]
        print(f"   {h:14s} 날 {msk.sum()} · 원 초과 연 {Y[msk].mean() * 245 * 100:+.1f}%p(NW t {P.nw_t(Y[msk]):+.1f}) · "
              f"α 연 {b[0] * 245 * 100:+.1f}%p(NW t {P.nw_t(alpha_series):+.1f}) · β " + " · ".join(f"{k_} {b[1 + n]:+.2f}" for n, k_ in enumerate(ctrl)))


if __name__ == "__main__":
    main()
