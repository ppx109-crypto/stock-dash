"""P2 — 전문 트레이더 갈래(docs/RL-PRO.md): P1의 '살 쪽'(무상증자 · 자사주 취득 · 시설투자+반응 내림)을
그날 시총 200위 안만 · 비용 0.5%(사고팔기 합) 빼고 · 해마다 · 같은 종목 20일 안 겹침 없이 다시.
- 사기 = 공시 다음 날(t0+1) 종가 · 들고 있기 5 · 20 · 60거래일 · 시장 = 그날 대상 가운데값 · 비용 뒤 초과 = 초과 − 0.5%.
- 이길 확률 = 비용 뒤 초과 > 0 · 앞 반(2017 ~ 21) / 뒤 반(2022 ~ 26) · 해마다 건수 · 평균.
python research/z012.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

COST = 0.005
KINDS = ("무상증자", "자사주취득", "시설투자", "주식소각")
HS = (5, 20, 60)


def main():
    C, F, ops, evs, qs, name = Z.load()
    inside, _ = Z.universe(C)
    days = list(C.index)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    fwd = {}
    for h in HS:
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        fwd[h] = f.sub(f.where(inside).median(axis=1), axis=0)     # 시장 = 그날 대상(200위) 가운데값
    rows = []
    for c in C.columns:
        last = {}
        for d, k in evs.get(c, []):
            if k not in KINDS or d < "20170101":
                continue
            j = int(np.searchsorted(days, d))
            if j + 1 + 60 >= len(days):
                continue
            t0 = days[j]
            if not inside.at[t0, c] or (k in last and j - last[k] < 20):
                continue
            last[k] = j
            rows.append((k, c, name.get(c, c), t0, react.at[t0, c], *(fwd[h].at[t0, c] for h in HS)))
    E = pd.DataFrame(rows, columns=["갈래", "코드", "이름", "날", "반응", *[f"{h}일" for h in HS]]).dropna(subset=["반응"])
    E["반"] = np.where(E["날"] < "20220101", "앞", "뒤")
    for k in KINDS:
        for cell, g in (("전체", E[E["갈래"] == k]), ("반응 내림(< −2%)", E[(E["갈래"] == k) & (E["반응"] < -0.02)]),
                        ("반응 오름(> +2%)", E[(E["갈래"] == k) & (E["반응"] > 0.02)])):
            if len(g) < 15:
                continue
            print(f"\n[{k} · {cell}] {len(g)}건 (시총 200위 안 · 비용 0.5% 뺀 초과)")
            for h in HS:
                v = g[f"{h}일"] - COST
                a, b = v[g["반"] == "앞"], v[g["반"] == "뒤"]
                print(f"  {h:2d}일 · 평균 {v.mean() * 100:+.2f} · 중앙값 {v.median() * 100:+.2f} · 이길 확률 {(v > 0).mean():.0%}"
                      f" [앞 {len(a)}건 {(a > 0).mean():.0%} 중앙 {a.median() * 100:+.2f} / 뒤 {len(b)}건 {(b > 0).mean():.0%} 중앙 {b.median() * 100:+.2f}]")
            yr = g.assign(해=g["날"].str[:4]).groupby("해")["20일"].agg(["count", "median"])
            print("  해마다 20일 (건수 · 중앙값%): " + " ".join(f"{y[2:]}:{int(n)}·{m * 100:+.1f}" for y, (n, m) in yr.iterrows()))
    Z.SP.mkdir(parents=True, exist_ok=True)
    E.to_csv(Z.SP / "z012_events.csv", index=False)
    last = E.sort_values("날").groupby("갈래").tail(3)
    print("\n최근 사건 예:", [(r.갈래, r.이름, r.날) for r in last.itertuples()])


if __name__ == "__main__":
    main()
