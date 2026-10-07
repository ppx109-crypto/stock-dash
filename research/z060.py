"""T13 — 투신의 '골라 산 매수' vs '돈이 들어와 산 매수'(docs/RL-TUSIN.md).
종목 투신 큰 매수 = 그날 투신 순매수 ÷ 거래량이 대상(시총 200위) 안 위 10%.
시장 투신(코스피 전체 투신 순매수 · market-data/investor_KSP)이 그날 '앞 250일 자기 기록' 위 20% = 돈 들어온 날 / 가운데값 아래 = 골라 산 날.
(시장 순위는 그날까지 값만 · 앞으로 굴린 창). 종목 · 시장 수급 모두 장 끝난 뒤 → **t+1 종가에 사서** 5 · 20일 초과 − 바탕 [앞 2017 ~ 21 / 뒤 2022 ~ 26].
python research/z060.py
"""
import json
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
    rows = json.loads(Path("market-data/investor_KSP.json").read_text(encoding="utf-8"))["rows"]
    mk = pd.Series({str(r["date"]): r.get("투신") for r in rows}).astype(float).reindex(C.index)
    pct = mk.rolling(250, min_periods=120).apply(lambda a: (a[:-1] < a[-1]).mean() if np.isfinite(a[-1]) else np.nan, raw=True)
    flood, quiet = pct >= 0.8, pct <= 0.5
    tu = (F["투신"] / F["vol"]).where(ok).rank(axis=1, pct=True)
    big = (tu > 0.9) & ok
    rowmask = lambda m: pd.DataFrame(np.repeat(m.fillna(False).to_numpy()[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    groups = {"투신 큰 매수 · 전체": big, "· 시장 투신 위 20%(돈 들어온 날)": big & rowmask(flood), "· 시장 투신 가운데 아래(골라 산 날)": big & rowmask(quiet),
              "참고: 시장 투신 위 20% 날의 모든 종목": ok & rowmask(flood), "참고: 시장 투신 가운데 아래 날의 모든 종목": ok & rowmask(quiet)}
    first = pd.Series(C.index < "20220101", index=C.index)
    print(f"시장 투신 위 20% 날 {int(flood.sum())} · 가운데 아래 날 {int(quiet.sum())}", flush=True)
    for h in (5, 20):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        ex = f.where(ok).sub(f.where(ok).median(axis=1), axis=0)
        b, bf, bb = ex.stack().dropna(), ex[first].stack().dropna(), ex[~first].stack().dropna()
        print(f"[{h}일] 바탕 {b.mean() * 100:+.2f}% · 나을 {(b > 0).mean():.0%}", flush=True)
        for lab, g in groups.items():
            e = ex.where(g)
            s, sf, sb = e.stack().dropna(), e[first].stack().dropna(), e[~first].stack().dropna()
            se = s.std() / np.sqrt(len(s) / h) if len(s) else np.nan
            print(f"  {lab:34s} {len(s):7d}건 · {(s.mean() - b.mean()) * 100:+.2f}%p(t≈{(s.mean() - b.mean()) / se:+.1f}) "
                  f"[{(sf.mean() - bf.mean()) * 100:+.2f}/{(sb.mean() - bb.mean()) * 100:+.2f}] · 중앙 {s.median() * 100:+.2f} · 나을 {(s > 0).mean():.0%}", flush=True)
    # 그날 반응(같은 날 초과)도 견줌: 돈 들어온 날의 큰 매수가 그날 더 오르나
    r0 = C / C.shift(1) - 1
    e0 = r0.where(ok).sub(r0.where(ok).median(axis=1), axis=0)
    for lab in ("· 시장 투신 위 20%(돈 들어온 날)", "· 시장 투신 가운데 아래(골라 산 날)"):
        print(f"  그날 초과 {lab}: {e0.where(groups[lab]).stack().mean() * 100:+.2f}%", flush=True)


if __name__ == "__main__":
    main()
