"""P12 — 가치 + 이익의 질 − 기관 20일 순매수 묶음(docs/RL-PRO.md · 1차 z042 IC 이어서) · 2차 잣대(쪼개기 고친 시총 200위 · perf2 BASE 비용 · 세 기간).
달 첫 거래일 t, 접수일 < t 인 마지막 보고서 숫자만: 이익 수익률(영업이익 연환산 ÷ 그날 시총) · 장부 비율(자본 ÷ 시총) ·
이익의 질(영업현금 ÷ 영업이익 · 같은 보고서 누적 기준 · 영업이익 ≤ 0 이면 빈칸) · 기관 20일 순매수 ÷ 거래량(t까지).
판: V(가치 두 개) · VQ(+ 이익의 질) · VQI(+ 기관 순매수 적음) — 순위 평균 위 20 → t+1 종가에 똑같이(z054.sim_factor) · 바탕 200위.
python research/z059.py
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
from z045 import ANN, num  # noqa: E402
from z054 import sim_factor  # noqa: E402

caps.ADJ = True
PER = (("학습 2017 ~ 20", "20170201", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"), ("전체", "20170201", "20991231"))


def reports(c):
    q = Path("quarter-data") / f"{c}.json"
    k = Path("cash-data") / f"{c}.json"
    qr = json.loads(q.read_text(encoding="utf-8")).get("rows") if q.exists() else {}
    kr = json.loads(k.read_text(encoding="utf-8")).get("rows") if k.exists() else {}
    out = []
    for key, v in (qr or {}).items():
        if not v or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        cv = (kr or {}).get(key) or {}
        op_cum = num(cv.get("영업이익_누적")) if cv.get("영업이익_누적") else num(v.get("영업이익"))
        ocf = num(cv.get("영업현금"))
        qual = ocf / op_cum if np.isfinite(ocf) and np.isfinite(op_cum) and op_cum > 0 else np.nan
        out.append((str(v["접수번호"])[:8], num(v.get("영업이익")) * ANN.get(key.split("-")[-1], 1.0), num(v.get("자본")), qual))
    return sorted(out)


def main():
    C, F, ops, evs, qs, name = Z.load()
    inside, size = Z.universe(C)
    R = C.pct_change(fill_method=None)
    days = list(C.index)
    months = [d for i, d in enumerate(days) if d >= "20170201" and days[i - 1][:6] != d[:6]]
    inst = F["기관"].rolling(20, min_periods=15).sum() / F["vol"].rolling(20, min_periods=15).sum()
    TL = {c: reports(c) for c in C.columns}
    frames = {k: pd.DataFrame(np.nan, index=C.index, columns=C.columns) for k in ("V", "VQ", "VQI")}
    for d in months:
        ins = inside.loc[d]
        cand = list(ins[ins].index)
        ey, bp, ql = {}, {}, {}
        for c in cand:
            rows = [r for r in TL[c] if r[0] < d]
            if not rows or not np.isfinite(size.at[d, c]) or size.at[d, c] <= 0:
                continue
            _, op, eq, q = rows[-1]
            if np.isfinite(op):
                ey[c] = op / size.at[d, c]
            if np.isfinite(eq):
                bp[c] = eq / size.at[d, c]
            if np.isfinite(q):
                ql[c] = q
        rk = lambda dct: pd.Series(dct, dtype=float).rank(pct=True).reindex(cand)
        v = pd.concat([rk(ey), rk(bp)], axis=1).mean(axis=1)
        vq = pd.concat([rk(ey), rk(bp), rk(ql)], axis=1).mean(axis=1)
        vqi = pd.concat([rk(ey), rk(bp), rk(ql), (-inst.loc[d].reindex(cand)).rank(pct=True)], axis=1).mean(axis=1)
        for k_, s in (("V", v), ("VQ", vq), ("VQI", vqi)):
            frames[k_].loc[d, s.index] = s.values
    base = pd.DataFrame(1.0, index=C.index, columns=C.columns).where(C.notna())
    runs = {"바탕 200위": sim_factor(C, R, inside, base, 200, 1.0)[0]}
    for k_, lab in (("V", "V 가치(이익 수익률 + 장부 비율)"), ("VQ", "VQ + 이익의 질"), ("VQI", "VQI + 이익의 질 − 기관 20일")):
        runs[lab] = sim_factor(C, R, inside, frames[k_], 20, 1.0)[0]
    for lab, r in runs.items():
        print(f"== {lab} 위 20 · BASE ==", flush=True)
        for h, lo, hi in PER:
            print(f"  {h:14s} {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)
        print(f"  해마다: {P.years_line(P.daily_stats(r, '20170201', '20991231'))}", flush=True)


if __name__ == "__main__":
    main()
