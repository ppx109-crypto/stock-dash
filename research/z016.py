"""Z16 — 투신 단타 T6: 크기 · 시장별(docs/RL-TUSIN.md).
투신이 그날 크게 산(대상 200 안 순매수 ÷ 거래량 위 10%) 종목을 **t+1 종가에 사서** 5 · 20일 — 그날 시총 순위(1 ~ 50 · 51 ~ 100 · 101 ~ 200) ·
시장(코스피 · 코스닥: kosdaq-data에 있는 종목 = 코스닥)으로 나눠 바탕(같은 무리 아무 날)과의 차이 · 그날 값 움직임(설명) [앞 반/뒤 반].
미래 참조: 고르기 t까지 수급 · 순위는 그날 값 · 진입 t+1 종가.
python research/z016.py
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
    inside, size = Z.universe(C)
    ok = pd.DataFrame(np.repeat((C.index >= Z.START)[:, None], C.shape[1], 1), index=C.index, columns=C.columns) & inside
    rank = size.rank(axis=1, ascending=False)
    kq = {p.stem for p in Path("kosdaq-data").glob("*.json")}
    is_kq = pd.DataFrame({c: c in kq for c in C.columns}, index=C.index)
    big = ((F["투신"] / F["vol"]).where(ok).rank(axis=1, pct=True) > 0.9)
    same = C / C.shift(1) - 1
    same_ex = same.where(ok).sub(same.where(ok).median(axis=1), axis=0)
    first = pd.Series(C.index < "20220101", index=C.index)
    groups = {"시총 1 ~ 50위": rank <= 50, "51 ~ 100위": (rank > 50) & (rank <= 100), "101 ~ 200위": (rank > 100) & (rank <= 200),
              "코스피": ~is_kq, "코스닥": is_kq}
    print("투신 크게 산 날(위 10%) · t+1 종가에 사서 · 초과(그날 대상 가운데값 뺌) − 같은 무리 바탕 [앞 반/뒤 반] · 그날 초과(설명)")
    for h in (5, 20):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        ex = f.where(ok).sub(f.where(ok).median(axis=1), axis=0)
        print(f"  [{h}일]")
        for lab, g in groups.items():
            gm = g & ok
            base = ex.where(gm)
            ev = ex.where(gm & big)
            s, b = ev.stack().dropna(), base.stack().dropna()
            sf, bf = ev[first].stack().dropna(), base[first].stack().dropna()
            sb, bb = ev[~first].stack().dropna(), base[~first].stack().dropna()
            today = same_ex.where(gm & big).stack().dropna()
            print(f"    {lab:9s} {len(s):6d}건 · {(s.mean() - b.mean()) * 100:+.2f}%p [{(sf.mean() - bf.mean()) * 100:+.2f}/{(sb.mean() - bb.mean()) * 100:+.2f}]"
                  f" · 나을 확률 {(s > 0).mean():.0%}(바탕 {(b > 0).mean():.0%}) · 그날 {today.mean() * 100:+.2f}%")


if __name__ == "__main__":
    main()
