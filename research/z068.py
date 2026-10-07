"""P15 — F5(공매도 비중 낮음 위 20)가 2021 ~ 22에 진 까닭 해부(서술 · docs/RL-PRO.md).
달 첫 거래일 t마다 F5 위 20의 성질(대상 200위 안 순위 0 ~ 1 평균: 크기 · 모멘텀 12-1 · 변동성 60 · 베타 250 · 회전율 · 외국인 60 · 기관 60)과
다음 달(t+1 → 다음 달 첫 거래일+1) 초과 수익(위 20 평균 − 200위 평균)을 기간별로 · 2021 ~ 22 가장 나빴던 달 5개.
python research/z068.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import caps  # noqa: E402
import perf2 as P  # noqa: E402
import z001 as Z  # noqa: E402

caps.ADJ = True


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    R = C.pct_change(fill_method=None)
    kp = pd.Series({str(r["date"]): float(r["종가"]) for r in json.loads((P.ROOT / "market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"] if r.get("종가")}).reindex(C.index).ffill()
    kr = kp.pct_change()
    feats = {"크기": np.log(size), "모멘텀": X["수익250_20"], "변동성60": R.rolling(60, min_periods=45).std(),
             "베타": R.rolling(250, min_periods=200).cov(kr).div(kr.rolling(250, min_periods=200).var(), axis=0),
             "회전율": F["vol"].rolling(20, min_periods=15).mean() / (size / C), "외국인60": X["외국인60"],
             "기관60": F["기관"].rolling(60, min_periods=45).sum() / F["vol"].rolling(60, min_periods=45).sum()}
    score = -X["공매도20"]
    days = list(C.index)
    months = [i for i, d in enumerate(days) if d >= "20170201" and days[i - 1][:6] != d[:6]]
    rows = []
    for m, i in enumerate(months[:-1]):
        d = days[i]
        ok = inside.loc[d]
        s = score.loc[d].where(ok).dropna()
        if len(s) < 50:
            continue
        top = s.sort_values(ascending=False).index[:20]
        j0, j1 = i + 1, months[m + 1] + 1
        if j1 >= len(days):
            break
        fw = (C.iloc[j1] / C.iloc[j0] - 1).where(ok)
        row = {"날": d, "초과": fw[top].mean() - fw.mean()}
        for k, v in feats.items():
            rk = v.loc[d].where(ok).rank(pct=True)
            row[k] = rk[top].mean()
        rows.append(row)
    D = pd.DataFrame(rows).set_index("날")
    per = np.select([D.index < "20210101", D.index < "20230101"], ["학습 2017 ~ 20", "검증 2021 ~ 22"], "시험 2023 ~ 26")
    print("기간별: 다음 달 초과(평균 · 이긴 달) · F5 위 20의 성질(대상 안 순위 평균 · 0.5 = 보통)", flush=True)
    for p in ("학습 2017 ~ 20", "검증 2021 ~ 22", "시험 2023 ~ 26"):
        x = D[per == p]
        print(f"  {p}: 달 {len(x)} · 초과 {x['초과'].mean() * 100:+.2f}%p/달 · 이긴 달 {(x['초과'] > 0).mean():.0%} · " + " · ".join(f"{k} {x[k].mean():.2f}" for k in feats), flush=True)
    v = D[per == "검증 2021 ~ 22"].sort_values("초과")
    print("2021 ~ 22 가장 나쁜 달 5:", flush=True)
    for d, r in v.head(5).iterrows():
        print(f"  {d[:6]} 초과 {r['초과'] * 100:+.1f}%p · " + " · ".join(f"{k} {r[k]:.2f}" for k in feats), flush=True)
    # 성질과 초과의 관계(달마다 · 전체): 어떤 노출이 진 달과 같이 움직였나
    print("달마다 '성질'과 '초과'의 상관(전체 · 검증만):", flush=True)
    for k in feats:
        a = D[k].corr(D["초과"])
        b = D[per == "검증 2021 ~ 22"][k].corr(D[per == "검증 2021 ~ 22"]["초과"])
        print(f"  {k}: 전체 {a:+.2f} · 검증 {b:+.2f}", flush=True)


if __name__ == "__main__":
    main()
