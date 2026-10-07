"""P16 — F5(공매도 비중 낮음 위 20)를 공매도 금지 기간에는 쉬기(docs/RL-PRO.md).
금지 기간(발표가 시작 전에 나와 그날 알 수 있음): 2020-03-16 ~ 2021-05-02(그 뒤엔 코스피200 · 코스닥150만 풀림) · 2023-11-06 ~ 2025-03-30.
판: F5 그대로 · 금지 기간엔 바탕(200위 똑같이) · 금지 기간엔 현금(0%). 날마다 수익 = z054_adj(쪼개기 고친 시총 · perf2 BASE).
바꿀 때 비용 어림: 판 쪽 0.065% + 그해 거래세 + 충격 0.1% · 산 쪽 0.065% + 충격 0.1%(F5 → 바탕은 둘 다 · 현금은 한쪽).
python research/z073.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf2 as P  # noqa: E402

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
BANS = (("20200316", "20210502"), ("20231106", "20250330"))
PER = (("학습 2017 ~ 20", "20170201", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("다시 본 2023 ~ 26", "20230101", "20991231"), ("전체", "20170201", "20991231"))


def main():
    z = np.load(SP / "z054_adj.npz")
    idx = [str(d) for d in z["days"]]
    f5 = pd.Series(z["F5 공매도 비중 낮음 위 20"], index=idx)
    base = pd.Series(z["바탕 200위 똑같이"], index=idx)
    ban = pd.Series(False, index=idx)
    for a, b in BANS:
        ban[(ban.index >= a) & (ban.index <= b)] = True
    sell = lambda d: 0.00065 + P.tax(d) + 0.001
    buy = 0.00065 + 0.001
    to_base, to_cash = f5.where(~ban, base), f5.where(~ban, 0.0)
    flips = [d for i, d in enumerate(idx[1:], 1) if ban.iloc[i] != ban.iloc[i - 1]]
    for d in flips:
        to_base[d] -= sell(d) + buy
        to_cash[d] -= sell(d) if ban[d] else buy
    print(f"== P16 · 금지 기간 날 {int(ban.sum())} · 바꾼 날 {flips} ==", flush=True)
    for a, b in BANS:
        m = (f5.index >= a) & (f5.index <= b)
        e = lambda s: (1 + s[m]).prod() - 1
        print(f"  금지 {a} ~ {b}: F5 {e(f5) * 100:+.1f}% · 바탕 {e(base) * 100:+.1f}% · 차 {(e(f5) - e(base)) * 100:+.1f}%p", flush=True)
    for lab, r in (("F5 그대로", f5), ("금지 땐 바탕", to_base), ("금지 땐 현금", to_cash), ("바탕(참고)", base)):
        print(f"== {lab} ==", flush=True)
        for h, lo, hi in PER:
            print(f"  {h:16s} {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)
    ex = f5 - base
    for h, lo, hi in PER:
        m = (ex.index >= lo) & (ex.index < hi)
        for tag, mm in (("금지 밖", m & ~ban.values), ("금지 안", m & ban.values)):
            x = ex[mm]
            if len(x) > 30:
                print(f"  {h} {tag}: 날 {len(x)} · F5 − 바탕 연 {x.mean() * 245 * 100:+.1f}%p(NW t {P.nw_t(x.to_numpy()):.1f})", flush=True)


if __name__ == "__main__":
    main()
