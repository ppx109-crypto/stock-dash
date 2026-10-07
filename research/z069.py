"""T16 — 1일봉 '새 82'가 사는 날(t)의 전날(t−1) 투신이 크게 판(대상 200위 안 투신 순매수 ÷ 거래량 아래 10%) 종목은 사지 않기(docs/RL-TUSIN.md).
어림: 쪼개기 고친 시총 매매 목록(z055_d1_adj)에서 그런 매매를 뺌(빈 칸에 다른 후보를 사는 효과는 안 셈). 대조: 전날 투신 크게 산(위 10%) 매매 빼기.
비용 perf2 BASE · 날마다 평가(a_mtm) · 학습 · 검증 · 시험. 투신 자료는 장 끝난 뒤 → t−1 값은 t 15:20 판단 때 앎.
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl python research/z069.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a_mtm  # noqa: E402
import caps  # noqa: E402
import perf2 as P  # noqa: E402
import z001 as Z  # noqa: E402
from z058 import recost  # noqa: E402

caps.ADJ = True
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
PER = (("학습 2017 ~ 20", "20170201", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"), ("전체", "20170201", "20991231"))


def main():
    import nrl
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    tu = (F["투신"] / F["vol"]).where(inside).rank(axis=1, pct=True).shift(1)     # 전날 값
    led = json.load(open(SP / "z055_d1_adj.json"))
    z = np.load(SP / "dd_now.npz")
    D0 = [str(d) for d in z["days"]]
    eng = z["mix"] - z["d1"]
    for lab, cond in (("지금", None), ("전날 투신 크게 판 종목 안 삼", lambda v: v <= 0.1), ("대조: 전날 투신 크게 산 종목 안 삼", lambda v: v > 0.9)):
        keep, drop = [], []
        for t in led:
            c, b = t[0], t[1]
            v = tu.at[b, c] if (cond and c in tu.columns and b in tu.index) else np.nan
            (drop if cond and np.isfinite(v) and cond(v) else keep).append(t)
        l2, tr = recost(keep, 1.0)
        _, trd = recost(drop, 1.0)
        r = pd.Series(a_mtm.account(D0, l2, eng, nrl.prices), index=D0)
        extra = f" · 뺀 매매 {len(drop)}(그 매매 평균 {np.mean([x[3] for x in trd]) * 100:+.2f}%)" if drop else ""
        print(f"== {lab}{extra} ==", flush=True)
        for h, lo, hi in PER:
            print(f"  {h:14s} 매매: {P.fmt_t(P.trade_stats(tr, lo, hi))}", flush=True)
            print(f"  {'':14s} A 계좌: {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)


if __name__ == "__main__":
    main()
