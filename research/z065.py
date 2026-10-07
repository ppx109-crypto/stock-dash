"""P14 — 위험 맞춤 섞기에서 F5 대신 KODEX 200(069500)을 넣으면(docs/RL-PRO.md · 2차 보고서 §15-3).
A = 1일봉 '새 82'(쪼개기 고친 시총 · perf2 BASE 비용) 날마다 평가 + 빈칸 엔진(dd_now) · D8 = 바구니 C 8칸(z054_adj · BASE) · F5(z054_adj) ·
K200 = KODEX 200 종가 수익(ETF 비용 · 다시 맞추는 비용은 넣지 않음 — 어림).
판: 역변동성(A · D8 · F5) · 역변동성(A · D8 · K200) · + 변동성 목표 연 15%(몫 합 ≤ 1 · 빚 없음) · 달마다 · 어제까지 60일.
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl python research/z065.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a_mtm  # noqa: E402
import perf2 as P  # noqa: E402
from z058 import recost, risk_parity  # noqa: E402

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
PER = (("학습 2017 ~ 20", "20170201", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"), ("전체", "20170201", "20991231"))


def main():
    import nrl
    z = np.load(SP / "dd_now.npz")
    D0 = [str(d) for d in z["days"]]
    led, _ = recost(json.load(open(SP / "z055_d1_adj.json")), 1.0)
    A = pd.Series(a_mtm.account(D0, led, z["mix"] - z["d1"], nrl.prices), index=D0)
    zz = np.load(SP / "z054_adj.npz")
    idx = [str(d) for d in zz["days"]]
    k = pd.Series(dict(json.load(open("etf-data/069500.json"))["closes"])).astype(float).sort_index()
    R = pd.DataFrame({"A": A.reindex(idx).fillna(0), "D8": zz["D 바구니 C 8칸"], "F5": zz["F5 공매도 비중 낮음 위 20"],
                      "K200": k.pct_change().reindex(idx).fillna(0).values}, index=idx)
    R = R[R.index >= "20170201"]
    print("날마다 상관: " + " · ".join(f"{a}·{b} {R[a].corr(R[b]):+.2f}" for a, b in (("A", "K200"), ("D8", "K200"), ("F5", "K200"), ("A", "F5"))), flush=True)
    for lab, keys, tgt in (("역변동성 A · D8 · F5", ["A", "D8", "F5"], None), ("역변동성 A · D8 · K200", ["A", "D8", "K200"], None),
                           ("역변동성 + 목표 15% · A · D8 · F5", ["A", "D8", "F5"], 0.15), ("역변동성 + 목표 15% · A · D8 · K200", ["A", "D8", "K200"], 0.15),
                           ("역변동성 + 목표 15% · A · D8(둘만)", ["A", "D8"], 0.15)):
        r = risk_parity(R, keys, tgt)
        print(f"== {lab} ==", flush=True)
        for h, lo, hi in PER:
            print(f"  {h:14s} {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)


if __name__ == "__main__":
    main()
