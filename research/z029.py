"""P5 — 전문 트레이더 갈래(docs/RL-PRO.md): 실적 발표 뒤 흐름(PEAD) — 잠정실적 날 반응 × '그날까지 이미 공시된' 이익 흐름.
원래 물음('잠정실적 반응 × 이번 분기 영업이익 놀람')은 이번 분기 숫자가 **정식 보고서(잠정 날보다 몇 주 뒤)**에야 우리 자료에 들어오므로
잠정 날에 쓰면 미래 참조 → 쓰지 않음. 대신 잠정 날 t0에 **접수일 < t0인 마지막 분기 보고서**의 영업이익 전년 대비(늘음 · 줄음 · 적자)를 씀.
- 사건: event-data '잠정실적'(같은 종목 20거래일 안 겹침 없음) · 그날 시총 200위 안 · 반응 = t0 종가 초과(그날 대상 가운데값 뺌).
- 사기: t0+1 종가 · 5 · 20 · 60일 초과 − 바탕(대상 아무 날) · 앞 반 2017 ~ 21 / 뒤 반 2022 ~ 26 · 나을 확률 · 비용 0.5% 뺀 20일.
python research/z029.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

HS = (5, 20, 60)


def main():
    C, F, ops, evs, qs, name = Z.load()
    C = C[C.index >= "20160601"]
    inside, _ = Z.universe(C)
    days = list(C.index)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    fwd = {}
    for h in HS:
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        fwd[h] = f.sub(f.where(inside).median(axis=1), axis=0)
    ok = inside & (pd.DataFrame(np.repeat((C.index >= "20170101")[:, None], C.shape[1], 1), index=C.index, columns=C.columns))
    base = {h: {"앞": fwd[h].where(ok)[C.index < "20220101"].stack().dropna(), "뒤": fwd[h].where(ok)[C.index >= "20220101"].stack().dropna()} for h in HS}
    rows = []
    for c in C.columns:
        last = None
        q = qs.get(c) or []
        qd = [d for d, *_ in q]
        for d, k in evs.get(c, []):
            if k != "잠정실적" or d < "20170101":
                continue
            j = int(np.searchsorted(days, d))
            if j + 1 >= len(days) or (last is not None and j - last < 20):
                continue
            t0 = days[j]
            if not inside.at[t0, c]:
                continue
            last = j
            rv = react.at[t0, c]
            if rv != rv:
                continue
            k2 = int(np.searchsorted(qd, t0)) - 1                 # 접수일 < t0 인 마지막 분기 보고서
            trend = "모름"
            if k2 >= 0:
                _, op, op_ly, *_ = q[k2]
                if op is not None and op_ly is not None:
                    trend = "적자" if op < 0 else "늘음" if op > op_ly else "줄음"
            rows.append((c, t0, rv, trend, *(fwd[h].at[t0, c] for h in HS)))
    E = pd.DataFrame(rows, columns=["코드", "날", "반응", "앞 분기", *[f"{h}일" for h in HS]])
    E["칸"] = np.where(E["반응"] > 0.02, "오름", np.where(E["반응"] < -0.02, "내림", "보통"))
    E["반"] = np.where(E["날"] < "20220101", "앞", "뒤")
    print(f"잠정실적 사건 {len(E)}건(시총 200위 안) · 앞 분기 늘음 {int((E['앞 분기'] == '늘음').sum())} · 줄음 {int((E['앞 분기'] == '줄음').sum())} · 적자 {int((E['앞 분기'] == '적자').sum())}")
    print("표: 앞 분기 × 잠정 날 반응 · 건수 · h일 바탕 뺀 차이 %p [앞/뒤] · 20일 중앙 · 나을 확률(바탕 50%) · 20일 비용 0.5% 뺀 평균")
    for tr in ("늘음", "줄음", "적자"):
        for kan in ("오름", "보통", "내림"):
            g = E[(E["앞 분기"] == tr) & (E["칸"] == kan)]
            if len(g) < 15:
                continue
            cells = []
            for h in HS:
                col = f"{h}일"
                a, b = g[g["반"] == "앞"][col].dropna(), g[g["반"] == "뒤"][col].dropna()
                da = a.mean() - base[h]["앞"].mean() if len(a) else np.nan
                db = b.mean() - base[h]["뒤"].mean() if len(b) else np.nan
                cells.append(f"{h}일 {(g[col].mean() - (base[h]['앞'].mean() + base[h]['뒤'].mean()) / 2) * 100:+.2f}[{da * 100:+.2f}/{db * 100:+.2f}]")
            x = g["20일"].dropna()
            print(f"  {tr} × {kan:2s} {len(g):4d}건 · " + " · ".join(cells) + f" · 20일 중앙 {x.median() * 100:+.2f} · 나을 {(x > 0).mean():.0%} · 비용 뒤 {(x.mean() - 0.005) * 100:+.2f}")


if __name__ == "__main__":
    main()
