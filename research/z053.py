"""2차 연구 S0 — 시가총액 계산의 '주식 쪼개기 미반영' 치우침 크기(caps.CAPS_ADJ).
가격(price-data)은 수정주가인데 DART 주식수는 그때 값 → 쪼개기 · 무상증자 앞 시총이 작게 나옴.
고친 판(CAPS_ADJ=1): 보고서 날 원주가 ÷ 수정주가(대차 자료 원주가)로 지금 기준 주식수로 맞춤(없으면 어림).
잼: 날마다 100위 · 200위 명단이 얼마나 바뀌나 · 정확 / 어림 / 고칠 것 없음 종목 수 · 크게 바뀐 종목 예.
python research/z053.py
"""
import importlib
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import caps  # noqa: E402
import z001 as Z  # noqa: E402


def sizes(C, adj):
    caps.ADJ = adj
    size = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for c in C.columns:
        tl = caps.timeline(c)
        if not tl:
            continue
        ds = np.array([int(d) for d, _ in tl])
        cnt = np.array([n for _, n in tl], dtype=float)
        k = np.searchsorted(ds, np.array([int(d) for d in C.index]), side="right") - 1
        size[c] = np.where(k >= 0, cnt[np.maximum(k, 0)], np.nan) * C[c].to_numpy()
    return size


def main():
    C, *_ = Z.load()
    C = C[C.index >= "20170102"]
    exact = sum(1 for c in C.columns if caps.raw_timeline(c) and caps._exact_factors(c, [d for d, _ in caps.raw_timeline(c)]))
    have = sum(1 for c in C.columns if caps.raw_timeline(c))
    print(f"주식수 있는 종목 {have} · 원주가로 정확히 고침 {exact} · 어림 {have - exact}")
    a, b = sizes(C, False), sizes(C, True)
    ra, rb = a.rank(axis=1, ascending=False), b.rank(axis=1, ascending=False)
    for top in (100, 200):
        ia, ib = ra <= top, rb <= top
        same = (ia & ib).sum(axis=1) / top
        yr = same.groupby(same.index.str[:4]).mean()
        print(f"{top}위 명단이 같은 몫(날 평균): 전체 {same.mean():.1%} · 해마다 " + " · ".join(f"{y} {v:.0%}" for y, v in yr.items()))
    d = (np.log(b / a)).abs().max()
    big = d[d > np.log(1.5)].sort_values(ascending=False)
    print(f"시총이 어느 날이든 1.5배 넘게 바뀐 종목 {len(big)}")
    for c in big.index[:25]:
        x = (rb[c] - ra[c])
        i = x.abs().idxmax()
        print(f"  {c} · 가장 크게 바뀐 날 {i}: 순위 {ra.at[i, c]:.0f} → {rb.at[i, c]:.0f} · 배수 {np.exp(d[c]):.1f}")


if __name__ == "__main__":
    main()
