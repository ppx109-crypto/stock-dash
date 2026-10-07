"""N2 — 좁은 장 RL(docs/RL-NARROW.md): 좁은 오름장 '합친 점수'.
- 고르기(2017 ~ 22 좁은 오름장 날만): 재료마다 IC를 2017~19 · 2020~22로 따로 재서 **두 반 같은 쪽 · 두 반 모두 |IC| ≥ 0.015**인 재료 → 그 쪽(부호)대로.
- 점수 = 그날 대상(시총 200) 안 백분위의 평균(값 없으면 0.5) — 그날 가로줄만.
- 시험(2023 ~ 26 · 고를 때 안 봄): 좁은 오름장 날 점수 위 10% · 20% 종목을 t+1 종가에 사서 5 · 20 · 60일 초과(그날 가운데값 뺌) · 시장보다 나을 확률.
  비교로 같은 점수를 다른 국면 · 고르기 기간에도 적음(고르기 기간 값은 '맞춘 값'이라 믿지 않음).
python research/z017.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
import z008 as N  # noqa: E402

RG = "좁은 오름장"


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = {k: v for k, v in Z.features(C, F, ops, evs, qs).items() if not k.startswith("엿보기")}
    inside, size = Z.universe(C)
    reg, _ = N.regimes(C, size)
    fwd20 = Z.forward(C)
    days = [d for i, d in enumerate(C.index) if d >= Z.START and i % Z.STEP == 0 and i + 1 + 60 < len(C.index)]
    train = {"A": [d for d in days if reg[d] == RG and d < "20200101"], "B": [d for d in days if reg[d] == RG and "20200101" <= d < "20230101"]}
    chosen = []
    for f, D in X.items():
        ics = {}
        for part, ds in train.items():
            v = []
            for d in ds:
                ok = inside.loc[d] & D.loc[d].notna() & fwd20.loc[d].notna()
                if ok.sum() < 40 or D.loc[d][ok].nunique() < 2:
                    continue
                r = fwd20.loc[d][ok]
                v.append(D.loc[d][ok].rank().corr((r - r.median()).rank()))
            ics[part] = np.nanmean(v) if v else np.nan
        a, b = ics["A"], ics["B"]
        if np.sign(a) == np.sign(b) and min(abs(a), abs(b)) >= 0.015:
            chosen.append((f, 1 if a > 0 else -1, a, b))
    print(f"2017 ~ 22 좁은 오름장으로 고른 재료 {len(chosen)}개:", [(f, "+" if s > 0 else "−", round(a, 3), round(b, 3)) for f, s, a, b in chosen])
    score = None
    for f, s, *_ in chosen:
        r = X[f].where(inside).rank(axis=1, pct=True)
        r = (r if s > 0 else 1 - r).fillna(0.5).where(inside)
        score = r if score is None else score + r
    score = score / len(chosen)
    print("\n점수 위 10% · 20%를 t+1 종가에 사서 h일 초과(%) · 나을 확률 · 판단 날 수")
    for h in (5, 20, 60):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        for lab, sel in (("시험 2023~26 좁은 오름장", lambda d: reg[d] == RG and d >= "20230101"),
                         ("(고르기 2017~22 좁은 오름장 · 맞춘 값)", lambda d: reg[d] == RG and d < "20230101"),
                         ("시험 2023~26 넓은 장", lambda d: reg[d] == "넓은 장" and d >= "20230101"),
                         ("시험 2023~26 내림장", lambda d: reg[d] == "내림장" and d >= "20230101")):
            res = {10: [], 20: []}
            n = 0
            for d in days:
                if not sel(d):
                    continue
                ok = inside.loc[d] & score.loc[d].notna() & f.loc[d].notna()
                if ok.sum() < 40:
                    continue
                n += 1
                r = f.loc[d][ok]
                ex = r - r.median()
                q = score.loc[d][ok].rank(pct=True)
                for k in (10, 20):
                    res[k].extend(ex[q > 1 - k / 100].tolist())
            if n:
                print(f"  {h:2d}일 {lab:28s} 위10% {np.mean(res[10]) * 100:+.2f}(나을 {np.mean(np.array(res[10]) > 0):.0%}) · "
                      f"위20% {np.mean(res[20]) * 100:+.2f}(나을 {np.mean(np.array(res[20]) > 0):.0%}) · 중앙 {np.median(res[20]) * 100:+.2f} · {n}날")


if __name__ == "__main__":
    main()
