"""F5 공매도 비중 낮음 + 국면 거르기(퀀트 연구): 매달 판단 날 KODEX 200(069500) 종가가 200일선 아래면 그달 현금 · 위면 위 20종목.
판단은 그날 종가까지(etf-data) · 사는 건 다음 날 종가 · 비용 0.5%. 견줌: 거르기 없음 · 바탕(200위 같은 몫).
python research/z049.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf as P  # noqa: E402
import z001 as Z  # noqa: E402
from z047 import run  # noqa: E402


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, _ = Z.universe(C)
    body = json.loads(Path("etf-data/069500.json").read_text(encoding="utf-8"))
    k = pd.Series({str(d): float(c) for d, c in body["closes"] if c}).sort_index().reindex(C.index).ffill()
    up = k >= k.rolling(200, min_periods=200).mean()
    s = -X["공매도20"]
    gated = s.where(up, other=np.nan)                         # 국면 아니면 점수 없음 → 그달 안 삼(현금)
    H = (("앞 2017 ~ 21", "20170201", "20220101"), ("뒤 2022 ~ 26", "20220101", "20991231"), ("시험 2023 ~", "20230101", "20991231"))
    for lab, sc in (("거르기 없음", s), ("200일선 아래면 현금", gated)):
        r = run(C, inside, sc, 20, 0.005)
        print(f"== F5 위 20 · {lab} ==")
        for h, lo, hi in H:
            print(f"  {h}: {P.fmt(P.account_stats(r, lo, hi))}", flush=True)


if __name__ == "__main__":
    main()
