"""Z5 — 투신 단타 연구 T2: 투신이 크게 산 날, 값은 하루 중 **언제** 오르나(docs/RL-TUSIN.md).
한투 장중 투자자 추정(가집계)은 10-01부터 4일치뿐이고 투신 칸이 없어(외국인 · 기관만) 과거를 못 봄 → 대신
한투 15분봉(m15-kis · 2025-09 ~)으로 '투신이 그날 크게 산 날(대상 200 안 위 10%)'의 하루 값 흐름을 잼:
시가 갭(전날 종가 → 09:00 시가) · 15분 칸마다 전날 종가 대비 누적(그날 대상 가운데값 뺌) · 마감 동시호가(15:15 칸 안 15:20 → 15:30).
설명(그날 수급은 장 끝나야 앎) — 따라 할 규칙이 아님. 같은 모양을 기관 · 외국인 · 개인 크게 산 날과 견줌.
python research/z005.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

SLOTS = [f"{h:02d}{m:02d}" for h in range(9, 16) for m in (0, 15, 30, 45) if (h, m) <= (15, 15)]
WHO = ("투신", "기관", "외국인", "연기금", "개인")


def m15_paths(codes, days, prev):
    """(날, 종목) → [시가 갭, 칸마다 전날 종가 대비 누적 수익(종가 기준) …] (칸이 빠지면 앞 칸 값)."""
    want = set(days)
    out = {}
    for c in codes:
        rows = {}
        for f in sorted((Path("m15-kis") / c).glob("*.csv")):
            for ln in f.read_text(encoding="utf-8").splitlines():
                p = ln.split(",")
                if len(p) == 6 and p[0][:8] in want:
                    rows.setdefault(p[0][:8], {})[p[0][8:]] = (float(p[1]), float(p[4]))
        for d, by in rows.items():
            pc = prev.get((d, c))
            if not pc or "0900" not in by:
                continue
            vals, last = [by["0900"][0] / pc - 1], None
            for s in SLOTS:
                if s in by:
                    last = by[s][1] / pc - 1
                vals.append(last if last is not None else np.nan)
            out[(d, c)] = vals
    return out


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    days = [d for d in C.index if d >= "20250918"]
    prevC = C.shift(1)
    codes = [c for c in C.columns if (Path("m15-kis") / c).is_dir()]
    prev = {(d, c): prevC.at[d, c] for d in days for c in codes if prevC.at[d, c] == prevC.at[d, c]}
    paths = m15_paths(codes, days, prev)
    cols = ["시가갭"] + SLOTS
    P = pd.DataFrame.from_dict(paths, orient="index", columns=cols)
    P.index = pd.MultiIndex.from_tuples(P.index, names=["날", "종목"])
    ins = inside.loc[days].stack()
    ins = ins[ins].index
    P = P.loc[P.index.intersection(ins)]
    Pex = P - P.groupby(level="날").transform("median")                 # 그날 대상 가운데값 뺌
    res = {"날수": len(set(P.index.get_level_values(0))), "줄": len(P)}
    for w in WHO:
        x = (F[w] / F["vol"]).loc[days].where(inside.loc[days])
        q = x.rank(axis=1, pct=True).stack()
        for side, m in (("크게 산 날", q > 0.9), ("크게 판 날", q <= 0.1)):
            idx = Pex.index.intersection(m[m].index)
            avg = Pex.loc[idx].mean() * 100
            res[f"{w} {side}"] = {"건수": len(idx), **{k: round(float(v), 2) for k, v in avg.items()}}
    Z.SP.mkdir(parents=True, exist_ok=True)
    (Z.SP / "z005.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    show = ["시가갭", "0900", "0930", "1000", "1100", "1200", "1300", "1400", "1430", "1500", "1515"]
    print(f"날 {res['날수']} · 줄 {res['줄']} · 전날 종가 대비 누적 초과(%) · 칸 이름 = 그 15분이 끝날 때 값(1515 = 마감)")
    print("                     " + " ".join(f"{s:>6s}" for s in show))
    for k, v in res.items():
        if isinstance(v, dict):
            print(f"{k:14s} {v['건수']:5d} " + " ".join(f"{v[s]:+6.2f}" for s in show))


if __name__ == "__main__":
    main()
