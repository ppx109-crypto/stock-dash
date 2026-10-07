"""T15 — 1일봉 '새 82'가 든 종목을 투신이 크게 판 날(그날 대상 200위 안 투신 순매수 ÷ 거래량 아래 10%) 다음 날 종가에 팔면 나아지나(docs/RL-TUSIN.md).
어림(매매 목록 고치기): 쪼개기 고친 시총 매매 목록(z055_d1_adj)에서 산 날 뒤 · 판 날 앞에 그 신호가 처음 뜬 날 d가 있으면 d+1 종가에 판 것으로 손익 다시 셈
(투신 자료는 장 끝난 뒤 → d+1 종가 매도는 판단 때 아는 값). 빈 칸을 다시 채우는 효과는 셈하지 않음(어림).
견줌: 같은 조건을 '투신 크게 산 날'로 바꾼 판(대조) · 지금. 비용 perf2 BASE · 날마다 평가(a_mtm) · 학습 · 검증 · 시험.
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl python research/z066.py
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
    tu = (F["투신"] / F["vol"]).where(inside).rank(axis=1, pct=True)
    days = list(C.index)
    pos = {d: i for i, d in enumerate(days)}
    led = json.load(open(SP / "z055_d1_adj.json"))
    z = np.load(SP / "dd_now.npz")
    D0 = [str(d) for d in z["days"]]
    eng = z["mix"] - z["d1"]
    out = {}
    for lab, sig in (("지금", None), ("투신 크게 판 날 다음 날 팖", tu <= 0.1), ("대조: 투신 크게 산 날 다음 날 팖", tu > 0.9)):
        new, hit, diff = [], 0, []
        for c, b, e, p, k in led:
            if sig is None or c not in C.columns or b not in pos or e not in pos:
                new.append((c, b, e, p, k))
                continue
            i0, i1 = pos[b], pos[e]
            s = sig[c].iloc[i0 + 1:i1].to_numpy()                 # 산 다음 날 ~ 판 날 전날 신호
            j = np.flatnonzero(s == True)  # noqa: E712
            if len(j) == 0 or i0 + 1 + j[0] + 1 >= i1:
                new.append((c, b, e, p, k))
                continue
            d_sell = i0 + 1 + j[0] + 1
            p_new = (C[c].iat[d_sell] / C[c].iat[i0] - 1) * 100 - 0.25
            new.append((c, b, days[d_sell], p_new, k))
            hit += 1
            diff.append(p_new - p)
        l2, tr = recost(new, 1.0)
        r = pd.Series(a_mtm.account(D0, l2, eng, nrl.prices), index=D0)
        out[lab] = (r, tr)
        extra = f" · 바뀐 매매 {hit} · 바뀐 매매 손익 차 평균 {np.mean(diff):+.2f}%p(중앙 {np.median(diff):+.2f})" if diff else ""
        print(f"== {lab}{extra} ==", flush=True)
        for h, lo, hi in PER:
            print(f"  {h:14s} 매매: {P.fmt_t(P.trade_stats(tr, lo, hi))}", flush=True)
            print(f"  {'':14s} A 계좌: {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)


if __name__ == "__main__":
    main()
