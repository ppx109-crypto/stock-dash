"""전략 성적표(퀀트 연구 보고서용) — 지금 운영 중이거나 연구로 남은 규칙을 같은 잣대(perf.py)로.
장부(손익 % · 왕복 0.25% 이미 뺌) 위에 스트레스: 비용 +50%(+0.125%) · 슬리피지 2배(+0.25%) · 둘 다 불리(+0.5%).
기간: 전체 · 앞(학습 · 2017 ~ 20) · 뒤(2021 ~ ) · 시험(2023 ~ ) · 15분봉 · 1시간봉은 한투 1년(2025-09 ~ 2026-08)뿐.
python research/z043.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf as P  # noqa: E402

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")


def ledger(name, slots=10):
    L = json.load(open(SP / name))
    return [(c, b, e, p, k / slots) for c, b, e, p, k in L]


def show(label, trades, lo, hi, extra=0.0):
    days = sorted(P.index_series("KOSPI").index)
    days = [d for d in days if lo <= d < hi] + [d for d in sorted({t[2] for t in trades}) if d >= days[-1]] if days else []
    days = sorted(set(days))
    tr = [t for t in trades if lo <= t[1] < hi]
    r = P.account(tr, days, cost=extra)
    print(f"  [{label}] 매매: {P.fmt(P.trade_stats(tr, cost=extra))}")
    print(f"  {'':{len(label) + 2}s} 계좌: {P.fmt(P.account_stats(r, lo, hi))}", flush=True)


def main():
    d1 = ledger("x008_d1.json")
    m15 = ledger("x004_m15_final.json")
    h1 = ledger("x004_h1k.json")
    print("== 1일봉 새 82(9년 · 판 날 셈 · 왕복 0.25% 뺀 손익) ==")
    for lab, lo, hi in (("전체 2017 ~ ", "20170101", "20991231"), ("앞 2017 ~ 20", "20170101", "20210101"), ("뒤 2021 ~ ", "20210101", "20991231"), ("시험 2023 ~ ", "20230101", "20991231")):
        show(lab, d1, lo, hi)
    print("  스트레스(전체):")
    for lab, ex in (("비용 +50%", 0.00125), ("슬리피지 2배", 0.0025), ("둘 다 불리", 0.005)):
        show(lab, d1, "20170101", "20991231", ex)
    print("\n== 15분봉 22회차 · 1시간봉(한투 1년 2025-09 ~ 2026-08) ==")
    show("15분봉", m15, "20250901", "20991231")
    show("15분봉 둘 다 불리", m15, "20250901", "20991231", 0.005)
    show("1시간봉", h1, "20250901", "20991231")
    show("1일봉 같은 1년", ledger("x004_d1.json"), "20250901", "20991231")


if __name__ == "__main__":
    main()
