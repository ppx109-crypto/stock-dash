"""N16 — 좁은 오름장(어제 폭 < 50 · 코스피 ≥ 60일선)에서 '1일봉 정배열 문(폭 조건만 뺌) ∩ F5 공매도 비중 낮음 위 40'이 고르기 재료가 되나(docs/RL-NARROW.md).
대상: 쪼개기 고친 그날 시총 100위. 정배열 = 3 > 15 > 20 > 90 > 150 > 200일선 · 3일선이 200일선보다 19 ~ 53% 위(1일봉 ② 문에서 시장 폭만 뺌).
F5 = 공매도 비중 20일 평균 낮은 순 위 40(대상 200위 안 · 그날까지). 그날 t 종가까지 → t+1 종가 사기 → 20거래일 초과(그날 200위 가운데값 뺌) − 바탕.
같은 종목 20거래일 안 겹침 없음. 판: 정배열만 · 정배열 ∩ F5 · 정배열 ∩ F5 아님 · F5만(정배열 아님). 고르기 2017 ~ 22 · 시험 2023 ~ 26.
python research/z067.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import caps  # noqa: E402
import z001 as Z  # noqa: E402
from z008 import regimes  # noqa: E402

caps.ADJ = True


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    reg, br = regimes(C, size)
    narrow = (reg.shift(1) == "좁은 오름장").reindex(C.index).fillna(False)
    rank = size.rank(axis=1, ascending=False)
    top100 = rank <= 100
    m = {n: C.rolling(n, min_periods=n).mean() for n in (3, 15, 20, 90, 150, 200)}
    aligned = (m[3] > m[15]) & (m[15] > m[20]) & (m[20] > m[90]) & (m[90] > m[150]) & (m[150] > m[200])
    gap = m[3] / m[200] - 1
    aligned &= (gap >= 0.19) & (gap <= 0.53) & top100
    f5r = (-X["공매도20"]).where(inside).rank(axis=1, ascending=False)
    f5 = f5r <= 40
    f = C.shift(-21) / C.shift(-1) - 1
    ex = f.where(inside).sub(f.where(inside).median(axis=1), axis=0)
    days = list(C.index)
    first = np.array([d < "20230101" for d in days])
    base = {k: float(np.nanmean(ex.where(inside).to_numpy()[msk])) for k, msk in (("고르기", first), ("시험", ~first))}
    nar = narrow.to_numpy()
    groups = {"정배열만(좁은 오름장)": aligned, "정배열 ∩ F5 위 40": aligned & f5, "정배열 ∩ F5 아님": aligned & ~f5, "F5 위 40 · 정배열 아님(대상 100위)": f5 & ~aligned & top100}
    print(f"좁은 오름장 날 {int(nar.sum())} · 바탕 20일 초과 고르기 {base['고르기'] * 100:+.2f}% · 시험 {base['시험'] * 100:+.2f}%", flush=True)
    E = ex.to_numpy()
    for lab, g in groups.items():
        G = g.to_numpy() & nar[:, None]
        rows = []
        for k in range(G.shape[1]):
            last = -99
            for i in np.flatnonzero(G[:, k]):
                if i - last < 20 or not np.isfinite(E[i, k]):
                    continue
                last = i
                rows.append((i, E[i, k]))
        if not rows:
            print(f"  {lab}: 0건", flush=True)
            continue
        idx = np.array([r[0] for r in rows]); val = np.array([r[1] for r in rows])
        cells = []
        for p, msk in (("고르기", first[idx]), ("시험", ~first[idx])):
            x = val[msk] - base[p]
            t = x.mean() / (x.std() / np.sqrt(len(x))) if len(x) > 2 else np.nan
            cells.append(f"{p} {len(x)}건 {x.mean() * 100:+.2f}%p(중앙 {np.median(x) * 100:+.2f} · 나을 {(x > 0).mean():.0%} · t {t:+.1f})")
        print(f"  {lab:28s} " + " | ".join(cells), flush=True)


if __name__ == "__main__":
    main()
