"""Q0 — 가장 중요한 질문: KIS 시장 자료와 DART 기업 · 공시 자료를 합치면 따로 쓸 때보다 미래 수익을 더 맞히나?(사용자 2026-10-07)
- 판단 t(5거래일마다 · 2017-03 ~) · 대상 = 그날 시총 200위 · 맞힐 것 = t+1 종가 → t+21 종가 수익의 그날 순위(z001.forward · GAP 1).
- 재료(모두 t까지 · 수급 · 공시 · 실적은 장 끝난 뒤 → t+1 종가 진입이라 안전 · z001 자르기 · 더럽히기 시험 통과한 셈):
  KIS가격(8) · KIS수급등(수급 · 프로그램 · 공매도 · 신용 · 대차 · 체결 · 증권사 의견 · 22) · DART(공시 60일 갈래 · 영업이익 · 매출 증가 · 접수일 기준)
- 모형: 그날 횡단면 순위로 바꾼 재료 → ① 선형(Ridge) ② 나무 모형(HistGradientBoosting · LightGBM과 같은 방식) — 학습 2017-03 ~ 2020 ·
  검증 2021 ~ 22(나무 깊이 · 횟수 세 판 가운데 고름) · **시험 2023 ~ 26(처음 봄)**.
- 잣대(시험 기간): 날마다 순위 IC 평균 · t(겹치지 않게 20거래일마다 표본) · 부트스트랩 95% 구간 · 위 10% 종목 20일 초과 − 비용 0.5% ·
  **합친 것 − KIS만의 IC 차이**(날마다 짝지어 부트스트랩) = 'DART를 더하면 늘어나는 정보'.
python research/z040.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402

KIS_P = ["수익5", "수익20", "수익60", "수익250_20", "52주고점비", "변동성20", "정배열50_200", "거래대금증가"]
TR, VA = ("20170301", "20210101"), ("20210101", "20230101")
TE = ("20230101", "20991231")
RNG = np.random.default_rng(7)


def boot(x, n=2000):
    x = np.asarray(x)
    m = [x[RNG.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return np.percentile(m, [2.5, 97.5])


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = {k: v for k, v in Z.features(C, F, ops, evs, qs).items() if not k.startswith("엿보기")}
    inside, _ = Z.universe(C)
    fwd = Z.forward(C)
    kis_f = [k for k in X if k not in KIS_P and not k.startswith("공시60_") and k not in ("영업이익증가", "매출증가")]
    dart = [k for k in X if k.startswith("공시60_") or k in ("영업이익증가", "매출증가")]
    groups = {"KIS가격": KIS_P, "KIS전체(가격+수급 등)": KIS_P + kis_f, "DART만": dart, "DART+KIS가격": KIS_P + dart,
              "KIS+DART 전부": KIS_P + kis_f + dart}
    print(f"재료 수: KIS가격 {len(KIS_P)} · KIS수급등 {len(kis_f)} · DART {len(dart)}", flush=True)
    days = [d for i, d in enumerate(C.index) if d >= Z.START and i % Z.STEP == 0 and i + 1 + Z.H < len(C.index)]
    rows = []
    feats = list(X)
    R = {k: X[k].where(inside).rank(axis=1, pct=True) for k in feats}
    Y = fwd.where(inside).rank(axis=1, pct=True)
    EX = fwd.where(inside).sub(fwd.where(inside).median(axis=1), axis=0)
    for d in days:
        ok = inside.loc[d] & fwd.loc[d].notna()
        codes = ok[ok].index
        if len(codes) < 50:
            continue
        df = pd.DataFrame({k: R[k].loc[d, codes] for k in feats}).fillna(0.5)
        df["_y"] = Y.loc[d, codes].values
        df["_ex"] = EX.loc[d, codes].values
        df["_d"] = d
        rows.append(df)
    P = pd.concat(rows)
    print(f"표본 {len(P)}줄 · 판단 날 {P['_d'].nunique()}", flush=True)
    seg = lambda a, b: P[(P["_d"] >= a) & (P["_d"] < b)]
    tr, va, te = seg(*TR), seg(*VA), seg(*TE)
    res = {}
    for g, cols in groups.items():
        out = {}
        lin = Ridge(alpha=10.0).fit(tr[cols], tr["_y"])
        best, bs = None, -9
        for depth, it in ((2, 100), (3, 200), (4, 300)):
            m = HistGradientBoostingRegressor(max_depth=depth, max_iter=it, learning_rate=0.05, min_samples_leaf=200, random_state=0).fit(tr[cols], tr["_y"])
            v = va.assign(p=m.predict(va[cols])).groupby("_d").apply(lambda x: x["p"].corr(x["_y"], method="spearman")).mean()
            if v > bs:
                best, bs = m, v
        for lab, m in (("선형", lin), ("나무", best)):
            t = te.assign(p=m.predict(te[cols]))
            ic = t.groupby("_d").apply(lambda x: x["p"].corr(x["_y"], method="spearman"))
            top = t.groupby("_d").apply(lambda x: x.loc[x["p"] >= x["p"].quantile(0.9), "_ex"].mean())
            nov = ic.iloc[::4]
            out[lab] = (ic, top)
            lo, hi = boot(ic.values)
            print(f"  {g:22s} {lab}: 시험 IC {ic.mean():+.4f}(t {nov.mean() / nov.std() * np.sqrt(len(nov)):+.2f} · 95% {lo:+.4f} ~ {hi:+.4f})"
                  f" · 위 10% 20일 초과 {top.mean() * 100:+.2f}% → 비용 0.5% 뒤 {(top.mean() - 0.005) * 100:+.2f}%"
                  f" · 나을 날 {(top > 0).mean():.0%}", flush=True)
        res[g] = out
    print("\n[DART를 더하면 늘어나는 정보 — 시험 기간 날마다 짝지은 IC 차이]")
    for lab in ("선형", "나무"):
        for a, b in (("KIS+DART 전부", "KIS전체(가격+수급 등)"), ("DART+KIS가격", "KIS가격")):
            d_ic = (res[a][lab][0] - res[b][lab][0]).dropna()
            d_top = (res[a][lab][1] - res[b][lab][1]).dropna()
            lo, hi = boot(d_ic.values)
            print(f"  {lab} · {a} − {b}: IC {d_ic.mean():+.4f}(95% {lo:+.4f} ~ {hi:+.4f}) · 위 10% 초과 차이 {d_top.mean() * 100:+.2f}%p", flush=True)


if __name__ == "__main__":
    main()
