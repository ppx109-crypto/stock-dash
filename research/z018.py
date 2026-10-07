"""P4 — 전문 트레이더 갈래(docs/RL-PRO.md): 사건 바구니 따로 굴리기.
- 사건: 그날 시총 200위 안 자사주 취득 · 무상증자(P2 z012_events.csv · 같은 종목 20일 안 겹침 없음).
- 사기: 공시 다음 날(t0+1) 종가 · 칸 5(한 칸 = 계좌 20%) · 빈 칸 있을 때만 · 들기 20거래일 · 비용 0.5%(사고팔기 합).
- 계좌 날마다 평가(종가) → 연 수익 · 골(고점 대비) · **가장 나쁜 하루 · 가장 나쁜 달(사용자 한도 −15%)** · 코스피와 상관 · 앞 반/뒤 반.
- 판 A: 둘 다 · B: 자사주 취득만 · C: 반응 내림(< −2%) 자사주 취득 + 무상증자.
미래 참조: 사건 · 반응은 t0 종가까지 · 진입 t0+1 종가(공시 다음 날).
python research/z018.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

SLOTS, HOLD, COST = 5, 20, 0.005


def simulate(C, ev):
    days = list(C.index)
    pos = {d: i for i, d in enumerate(days)}
    want = {}
    for r in ev.itertuples():
        j = pos.get(r.날)
        if j is not None and j + 1 < len(days):
            want.setdefault(days[j + 1], []).append(r.코드)
    held = {}                                  # 코드 → (산 날 위치, 산 값, 칸 돈)
    cash, eq = 1.0, []
    for i, d in enumerate(days):
        px = C.iloc[i]
        # 팔기: 20거래일 지남
        for c in [c for c, (k, p0, m) in held.items() if i - k >= HOLD]:
            k, p0, m = held.pop(c)
            p = px[c] if px[c] == px[c] else p0
            cash += m * p / p0 * (1 - COST / 2)
        value = cash + sum(m * (px[c] / p0 if px[c] == px[c] else 1) for c, (k, p0, m) in held.items())
        for c in want.get(d, []):
            if len(held) >= SLOTS or c in held or not (px[c] == px[c]):
                continue
            m = min(value / SLOTS, cash)
            if m <= 0:
                break
            cash -= m
            held[c] = (i, px[c] * (1 + COST / 2), m)
        eq.append(cash + sum(m * (px[c] / p0 if px[c] == px[c] else 1) for c, (k, p0, m) in held.items()))
    return pd.Series(eq, index=days)


def stats(eq, kospi, lab):
    r = eq.pct_change().dropna()
    out = []
    for part, m in (("앞 2017~21", r.index < "20220101"), ("뒤 2022~26", r.index >= "20220101")):
        x = r[m]
        e = (1 + x).cumprod()
        yrs = len(x) / 245
        ann = e.iloc[-1] ** (1 / yrs) - 1
        mdd = (e / e.cummax() - 1).min()
        mon = (1 + x).groupby(pd.to_datetime(x.index).to_period("M")).prod() - 1
        k = kospi.reindex(x.index).pct_change()
        out.append(f"{part}: 연 {ann * 100:+.1f}% · 골 {mdd * 100:.1f}% · 가장 나쁜 하루 {x.min() * 100:.1f}% · 가장 나쁜 달 {mon.min() * 100:.1f}% · 코스피 상관 {x.corr(k):+.2f}")
    print(f"[{lab}]\n  " + "\n  ".join(out))


def main():
    C, *_ = Z.load()
    C = C[C.index >= "20170101"]
    E = pd.read_csv(Z.SP / "z012_events.csv", dtype={"코드": str, "날": str})
    k = json.loads(Path("market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"]
    kospi = pd.Series({str(r["date"]): float(r["종가"]) for r in k})
    base = E[E["갈래"].isin(["자사주취득", "무상증자"])]
    for lab, ev in (("A 자사주 취득 + 무상증자", base), ("B 자사주 취득만", base[base["갈래"] == "자사주취득"]),
                    ("C 반응 내림 자사주 취득 + 무상증자", base[(base["갈래"] == "무상증자") | (base["반응"] < -0.02)])):
        stats(simulate(C, ev), kospi, f"{lab} · 사건 {len(ev)}")
    kk = kospi[kospi.index >= "20170101"]
    stats(kk / kk.iloc[0], kospi, "참고: 코스피 그냥 들기")


if __name__ == "__main__":
    main()
