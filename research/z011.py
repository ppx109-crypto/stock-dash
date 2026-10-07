"""P1 — 전문 트레이더 갈래(docs/RL-PRO.md): DART 공시 뒤 흐름 · 발표 날 반응으로 나눠(사용자 2026-10-07 "너가 전문트레이더이고
한투의 정보와 다트의 정보를 분석 활용하여 어떻게 투자할지 추가 연구해줘"). RL-EARN의 E10 · E12(공시 갈래 · 잠정실적 반응 뒤 흐름)를 한 번에.
- 공시 날 t0 = 접수일(장 중인지 끝난 뒤인지 모름). 반응 = t0−1 종가 → t0 종가 초과(그날 대상 가운데값 뺌 · t0 장 끝에 앎).
- **사기 = t0+1 종가**(공시 · 반응을 다 본 다음 날 · 15:15에도 같은 결정 — 반응은 전날 종가까지 값).
- 뒤 흐름 = t0+1 종가 → +5 · +20 · +60거래일 초과. 아무 날 바탕(같은 셈으로 모든 종목 · 날)을 빼서 '차이'로 봄.
- 반응 세 칸: 오름(> +2%) · 보통 · 내림(< −2%) · 앞 반(2017 ~ 21) / 뒤 반(2022 ~ 26).
- 대상: price-data 모든 종목(약 500 · 살아남은 종목 치우침 있음) · 같은 종목 같은 갈래 20거래일 안 겹친 공시는 처음 것만.
python research/z011.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

KINDS = ("잠정실적", "자사주취득", "주식소각", "자사주처분", "공급계약", "유상증자", "전환사채", "무상증자", "대량보유", "임원소유",
         "최대주주지분변동", "최대주주변경", "시설투자", "기업설명회", "배당", "조회공시", "주식매수선택권", "소송", "감자", "관리종목")
HS = (5, 20, 60)


def main():
    C, F, ops, evs, qs, name = Z.load()
    C = C[C.index >= "20160601"]
    days = list(C.index)
    pos = {d: i for i, d in enumerate(days)}
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.median(axis=1), axis=0)                         # 그날 초과
    fwd = {}
    for h in HS:
        f = C.shift(-(1 + h)) / C.shift(-1) - 1                       # (행 = t0) t0+1 종가 → t0+1+h
        fwd[h] = f.sub(f.median(axis=1), axis=0)
    base = {h: float(np.nanmean(fwd[h].loc[[d for d in days if d >= "20170101"]].to_numpy())) for h in HS}
    first_half = lambda d: d < "20220101"
    rows = []
    for c in C.columns:
        last = {}
        for d, k in evs.get(c, []):
            if k not in KINDS or d < "20170101":
                continue
            j = int(np.searchsorted(days, d))                         # 접수일이거나 그 뒤 첫 거래일
            if j + 1 + 60 >= len(days):
                continue
            if k in last and j - last[k] < 20:
                continue
            last[k] = j
            t0 = days[j]
            rv = react.at[t0, c]
            if rv != rv:
                continue
            rows.append((k, t0, rv, *(fwd[h].at[t0, c] for h in HS)))
    E = pd.DataFrame(rows, columns=["갈래", "날", "반응", *[f"{h}일" for h in HS]])
    E["칸"] = np.where(E["반응"] > 0.02, "오름", np.where(E["반응"] < -0.02, "내림", "보통"))
    E["반"] = np.where(E["날"].map(first_half), "앞", "뒤")
    print(f"사건 {len(E)}건 · 바탕(아무 날 · 가운데값 뺀 초과 평균) " + " · ".join(f"{h}일 {base[h] * 100:+.2f}" for h in HS))
    print("표: 갈래 · 반응 칸 · 건수 · h일 '바탕 뺀 차이'(%p) [앞 반/뒤 반] · 20일 시장보다 나은 확률")
    out = []
    for k in KINDS:
        for cell in ("전체", "오름", "보통", "내림"):
            g = E[E["갈래"] == k] if cell == "전체" else E[(E["갈래"] == k) & (E["칸"] == cell)]
            if len(g) < 30:
                continue
            parts = []
            for h in HS:
                col = f"{h}일"
                a = g[col].mean() - base[h]
                fa = g[g["반"] == "앞"][col].mean() - base[h]
                fb = g[g["반"] == "뒤"][col].mean() - base[h]
                parts.append(f"{h}일 {a * 100:+.2f} [{fa * 100:+.2f}/{fb * 100:+.2f}]")
            win = (g["20일"] > 0).mean()
            same = all(np.sign(g[g["반"] == s][f"{h}일"].mean() - base[h]) == np.sign(g[f"{h}일"].mean() - base[h])
                       for s in ("앞", "뒤") for h in (20, 60))
            out.append((k, cell, len(g), parts, win, same))
            print(f"  {k:8s} {cell:3s} {len(g):5d}건 · " + " · ".join(parts) + f" · 이길 확률 {win:.0%}" + (" ✔두 반 같은 쪽" if same else ""))
    Z.SP.mkdir(parents=True, exist_ok=True)
    E.to_csv(Z.SP / "z011_events.csv", index=False)


if __name__ == "__main__":
    main()
