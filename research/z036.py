"""N11 — 좁은 장 RL(docs/RL-NARROW.md): 좁은 오름장이 얼마나 이어지나 · 어떻게 끝나나(폭 50 회복 vs 지수 60일선 아래) · 끝난 뒤 지수.
국면은 z008.regimes(그날 종가까지 값). 이어진 덩어리(같은 국면 연속 날)를 세고, 끝날 때 다음 국면으로 나눠
· 길이(거래일) 가운데값 · 끝난 날 t → t+1 종가에 코스피 지수를 샀다면 20 · 60일 수익(설명용 · 규칙 아님).
python research/z036.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
import z008 as N  # noqa: E402


def main():
    C, *_ = Z.load()
    inside, size = Z.universe(C)
    reg, br = N.regimes(C, size)
    reg = reg[reg.index >= "20170101"]
    k = json.loads(Path("market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"]
    kc = pd.Series({str(r["date"]): float(r["종가"]) for r in k}).reindex(reg.index)
    days = list(reg.index)
    spells, start = [], 0
    for i in range(1, len(days) + 1):
        if i == len(days) or reg.iloc[i] != reg.iloc[start]:
            spells.append((reg.iloc[start], days[start], days[i - 1], i - start, reg.iloc[i] if i < len(days) else "끝"))
            start = i
    S = pd.DataFrame(spells, columns=["국면", "시작", "끝", "길이", "다음"])
    print("국면별 덩어리 · 길이(거래일) 가운데값 · 평균 · 5일 이하 몫(잠깐 스침)")
    for g, s in S.groupby("국면"):
        print(f"  {g:6s} {len(s):3d}번 · 가운데 {s['길이'].median():.0f}일 · 평균 {s['길이'].mean():.1f}일 · 5일 이하 {np.mean(s['길이'] <= 5):.0%}")
    print("\n좁은 오름장이 끝날 때 다음 국면 · 끝난 날 다음 날 종가에 코스피를 샀다면 20 · 60일(설명용)")
    nr = S[(S["국면"] == "좁은 오름장") & (S["다음"] != "끝")]
    for nx, s in nr.groupby("다음"):
        r20, r60 = [], []
        for e in s["끝"]:
            i = days.index(e)
            if i + 61 < len(days):
                r20.append(kc.iloc[i + 21] / kc.iloc[i + 1] - 1)
                r60.append(kc.iloc[i + 61] / kc.iloc[i + 1] - 1)
        print(f"  → {nx:6s} {len(s):3d}번 · 길이 가운데 {s['길이'].median():.0f}일 · 코스피 20일 {np.mean(r20) * 100:+.2f}% · 60일 {np.mean(r60) * 100:+.2f}%")
    base20 = (kc.shift(-21) / kc.shift(-1) - 1).mean() * 100
    base60 = (kc.shift(-61) / kc.shift(-1) - 1).mean() * 100
    print(f"  (아무 날 코스피 20일 {base20:+.2f}% · 60일 {base60:+.2f}%)")
    print(f"\n지금 국면: {reg.iloc[-1]} · {S.iloc[-1]['시작']}부터 {S.iloc[-1]['길이']}거래일째 · 오늘 폭 {br.iloc[-1]:.1f}%")


if __name__ == "__main__":
    main()
