"""T14 — 투신 60일 누적 순매수 ÷ 60일 거래량 위 20종목 달마다 바구니(docs/RL-TUSIN.md · F4 외국인 · F7 연기금과 같은 잣대).
2차 잣대: 쪼개기 고친 시총 200위 · 달 첫 거래일 t까지 수급 → t+1 종가에 똑같이(z054.sim_factor · perf2 BASE 비용) · 날마다 평가 · 학습 · 검증 · 시험.
견줌: 거꾸로(투신 많이 판 위 20) · 바탕 200위.
python research/z063.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import caps  # noqa: E402
import perf2 as P  # noqa: E402
import z001 as Z  # noqa: E402
from z054 import sim_factor  # noqa: E402

caps.ADJ = True
PER = (("학습 2017 ~ 20", "20170301", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"), ("전체", "20170301", "20991231"))


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    R = C.pct_change(fill_method=None)
    tu60 = F["투신"].rolling(60, min_periods=45).sum() / F["vol"].rolling(60, min_periods=45).sum()
    base = pd.DataFrame(1.0, index=C.index, columns=C.columns).where(C.notna())
    for lab, sc, n in (("투신 60일 많이 산 위 20", tu60, 20), ("투신 60일 많이 판 위 20", -tu60, 20), ("바탕 200위", base, 200)):
        r, _ = sim_factor(C, R, inside, sc, n, 1.0)
        print(f"== {lab} · BASE ==", flush=True)
        for h, lo, hi in PER:
            print(f"  {h:14s} {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)
        print(f"  해마다: {P.years_line(P.daily_stats(r, '20170301', '20991231'))}", flush=True)


if __name__ == "__main__":
    main()
