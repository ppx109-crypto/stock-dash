"""T12 — 투신 '이어 사기'가 끝난 날 뒤 주가(docs/RL-TUSIN.md · T5: 투신은 2 ~ 3일 이어 사고 끝남).
물음: 투신이 k일(3 · 5) 이어 순매수하다 오늘(t) 순매도(≤ 0)로 돌아서면, 그 종목은 뒤에 바탕보다 못한가(팔 신호 · 피할 신호)?
     거울: 투신이 k일 이어 팔다 오늘 사기로 돌아서면 나은가(살 신호)? · 견줌: 오늘도 이어 사는 중(k일째 이상).
대상 200 · 그날(t) 수급은 장 끝난 뒤 → **t+1 종가에 사서** 5 · 20일 초과(그날 가운데값 뺌) − 바탕 [앞 2017 ~ 21 / 뒤 2022 ~ 26] · 나을 확률 · 중앙.
python research/z051.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402


def runs(pos):
    """그날까지 이어진 참 일수(그날 포함)."""
    a = pos.to_numpy().astype(int)
    out = np.zeros_like(a)
    for i in range(len(a)):
        out[i] = (out[i - 1] + 1) * a[i] if i else a[i]
    return pd.DataFrame(out, index=pos.index, columns=pos.columns)


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    ok = inside & pd.DataFrame(np.repeat((C.index >= Z.START)[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    tu = F["투신"]
    has = tu.notna()
    buy = runs((tu > 0) & has)
    sell = runs((tu < 0) & has)
    pb, ps = buy.shift(1).fillna(0), sell.shift(1).fillna(0)
    groups = {}
    for k in (3, 5):
        groups[f"이어 사기 {k}일+ 뒤 오늘 팖(끝남)"] = (pb >= k) & (tu <= 0) & has & ok
        groups[f"이어 사기 {k}일째 이상 · 오늘도 삼"] = (buy >= k) & ok
        groups[f"이어 팔기 {k}일+ 뒤 오늘 삼(돌아섬)"] = (ps >= k) & (tu > 0) & has & ok
    first = pd.Series(C.index < "20220101", index=C.index)
    for h in (5, 20):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        ex = f.where(ok).sub(f.where(ok).median(axis=1), axis=0)
        b, bf, bb = ex.stack().dropna(), ex[first].stack().dropna(), ex[~first].stack().dropna()
        print(f"[{h}일] 바탕 {b.mean() * 100:+.2f}% · 나을 {(b > 0).mean():.0%}", flush=True)
        for lab, g in groups.items():
            e = ex.where(g)
            s, sf, sb = e.stack().dropna(), e[first].stack().dropna(), e[~first].stack().dropna()
            se = s.std() / np.sqrt(len(s) / h) if len(s) else np.nan    # 겹침 어림: 독립 표본 ≈ 건수 ÷ h
            print(f"  {lab:30s} {len(s):7d}건 · {(s.mean() - b.mean()) * 100:+.2f}%p(t≈{(s.mean() - b.mean()) / se:+.1f}) "
                  f"[{(sf.mean() - bf.mean()) * 100:+.2f}/{(sb.mean() - bb.mean()) * 100:+.2f}] · 중앙 {s.median() * 100:+.2f} · 나을 {(s > 0).mean():.0%}", flush=True)


if __name__ == "__main__":
    main()
