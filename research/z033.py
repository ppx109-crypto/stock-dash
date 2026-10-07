"""B9② · P7 — 숏커버 사건(docs/RL-BOTS.md · RL-PRO.md P7): 대차 잔고 급감 · 공매도 비중 급락 뒤 되오름?
그날(t) 장 끝난 뒤 나오는 자료 → **t+1 종가에 사서** 5 · 20일 초과(그날 대상 가운데값 뺌) − 바탕(대상 아무 날) [앞 2017 ~ 21 / 뒤 2022 ~ 26].
- 대차 급감: 대차 잔고 5일 변화율이 그날 대상(200위) 안 아래 10% (그리고 20일 전보다도 줄었음)
- 공매도 급락: 공매도 비중 5일 평균 − 20일 평균이 아래 10% · 20일 평균은 위 30%(많이 팔리던 종목)
- 둘 다 · 그날 값 움직임(설명) · 나을 확률 · 20일 중앙값.
python research/z033.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    ok = inside & pd.DataFrame(np.repeat((C.index >= Z.START)[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    loan, sh = F["대차잔고"], F["공매도비중"]
    d5 = (loan / loan.shift(5) - 1).where(ok)
    d20 = (loan / loan.shift(20) - 1).where(ok)
    loan_drop = (d5.rank(axis=1, pct=True) <= 0.1) & (d20 < 0) & ok
    s5, s20 = sh.rolling(5, min_periods=4).mean(), sh.rolling(20, min_periods=15).mean()
    short_drop = ((s5 - s20).where(ok).rank(axis=1, pct=True) <= 0.1) & (s20.where(ok).rank(axis=1, pct=True) >= 0.7) & ok
    same = C / C.shift(1) - 1
    same_ex = same.where(ok).sub(same.where(ok).median(axis=1), axis=0)
    first = pd.Series(C.index < "20220101", index=C.index)
    print(f"대차 자료 있는 대상 줄 {int(loan.where(ok).notna().sum().sum())} · 공매도 비중 {int(sh.where(ok).notna().sum().sum())}")
    for h in (5, 20):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        ex = f.where(ok).sub(f.where(ok).median(axis=1), axis=0)
        b, bf, bb = ex.stack().dropna(), ex[first].stack().dropna(), ex[~first].stack().dropna()
        print(f"  [{h}일] 바탕 {b.mean() * 100:+.2f}% · 나을 {(b > 0).mean():.0%}")
        for lab, g in (("대차 급감", loan_drop), ("공매도 비중 급락", short_drop), ("둘 다", loan_drop & short_drop)):
            e = ex.where(g)
            s, sf, sb = e.stack().dropna(), e[first].stack().dropna(), e[~first].stack().dropna()
            if len(s) < 30:
                print(f"    {lab}: {len(s)}건(적음)")
                continue
            today = same_ex.where(g).stack().dropna()
            print(f"    {lab:12s} {len(s):6d}건 · {(s.mean() - b.mean()) * 100:+.2f}%p [{(sf.mean() - bf.mean()) * 100:+.2f}/{(sb.mean() - bb.mean()) * 100:+.2f}]"
                  f" · 중앙 {s.median() * 100:+.2f}(바탕 {b.median() * 100:+.2f}) · 나을 {(s > 0).mean():.0%} · 그날 {today.mean() * 100:+.2f}%", flush=True)


if __name__ == "__main__":
    main()
