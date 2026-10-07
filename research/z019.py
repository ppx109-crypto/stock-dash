"""Z19 — 투신 단타 T7: 상대편(docs/RL-TUSIN.md).
투신이 그날 크게 산(대상 200 안 순매수 ÷ 거래량 위 10%) 종목을, 같은 날 **누가 팔았나**로 나눔:
개인만 팖(외국인 삼) · 외국인만 팖(개인 삼) · 둘 다 팖 · 둘 다 삼(다른 기관이 팖).
**t+1 종가에 사서** 5 · 20일 초과(그날 대상 가운데값 뺌) − 바탕(대상 아무 날) [앞 반 2017~21 / 뒤 반 2022~26] · 나을 확률 · 그날 초과(설명).
미래 참조: 수급은 t 장 끝난 뒤 → 진입 t+1 종가.
python research/z019.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    ok = pd.DataFrame(np.repeat((C.index >= Z.START)[:, None], C.shape[1], 1), index=C.index, columns=C.columns) & inside
    big = ((F["투신"] / F["vol"]).where(ok).rank(axis=1, pct=True) > 0.9) & ok
    ind, fr = F["개인"], F["외국인"]
    groups = {"개인만 팖(외국인 삼)": (ind < 0) & (fr > 0), "외국인만 팖(개인 삼)": (fr < 0) & (ind > 0),
              "둘 다 팖": (ind < 0) & (fr < 0), "둘 다 삼(다른 기관 팖)": (ind > 0) & (fr > 0)}
    # 외국인이 '크게' 판 경우 따로(외국인 순매수 ÷ 거래량 아래 1/5)
    fr_low = (fr / F["vol"]).where(ok).rank(axis=1, pct=True) < 0.2
    groups["외국인 크게 팖(아래 1/5)"] = fr_low
    groups["외국인 크게 삼(위 1/5)"] = (fr / F["vol"]).where(ok).rank(axis=1, pct=True) > 0.8
    same = C / C.shift(1) - 1
    same_ex = same.where(ok).sub(same.where(ok).median(axis=1), axis=0)
    first = pd.Series(C.index < "20220101", index=C.index)
    print(f"투신 크게 산 날 {int(big.sum().sum())}건 · t+1 종가에 사서 · 초과 − 바탕 [앞/뒤] · 나을 확률(바탕) · 그날 초과")
    for h in (5, 20):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        ex = f.where(ok).sub(f.where(ok).median(axis=1), axis=0)
        b, bf, bb = ex.stack().dropna(), ex[first].stack().dropna(), ex[~first].stack().dropna()
        print(f"  [{h}일] 바탕 {b.mean() * 100:+.2f}% · 나을 {(b > 0).mean():.0%}")
        for lab, g in [("투신 위 10% 전체", big)] + [(k, big & v) for k, v in groups.items()]:
            ev = ex.where(g)
            s = ev.stack().dropna()
            sf, sb = ev[first].stack().dropna(), ev[~first].stack().dropna()
            today = same_ex.where(g).stack().dropna()
            print(f"    {lab:22s} {len(s):6d}건 · {(s.mean() - b.mean()) * 100:+.2f}%p [{(sf.mean() - bf.mean()) * 100:+.2f}/{(sb.mean() - bb.mean()) * 100:+.2f}]"
                  f" · 중앙 {s.median() * 100:+.2f}(바탕 {b.median() * 100:+.2f}) · 나을 {(s > 0).mean():.0%} · 그날 {today.mean() * 100:+.2f}%")


if __name__ == "__main__":
    main()
