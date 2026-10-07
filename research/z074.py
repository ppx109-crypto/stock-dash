"""T17 — 시장 단위: 투신 + 연기금이 함께 크게 판 날 → 다음 5 · 20일 코스피200 ETF(069500)(docs/RL-TUSIN.md).
신호(t 장 끝난 뒤 앎): 코스피 투신 · 연기금 순매수 ÷ 거래대금을 각각 **앞 250거래일과만** 견준 순위가 둘 다 ≤ q(q = 0.2 미리 정함 · 0.1 참고).
결과: t+1 종가 → t+1+h 종가(h = 5 · 20) 069500 수익 − 모든 날 같은 값 평균(바탕). 겹치는 표본이라 t는 겹침 없이(신호 뒤 h일 건너뜀) 따로 셈.
'쉬기' 재료가 되려면: 고르기 2017 ~ 22와 다시 본 2023 ~ 26 둘 다 바탕보다 낮아야 하고, 빈칸 엔진이 켜지는 '폭 < 50' 날에서도 낮아야 함.
python research/z074.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
import z008 as N  # noqa: E402
from z022 import ROOT, past_rank, rows  # noqa: E402


def main():
    import json
    idx, inv = rows("index_KOSPI.json"), rows("investor_KSP.json")
    body = json.loads((ROOT / "etf-data/069500.json").read_text(encoding="utf-8"))
    etf = pd.Series({str(d): float(c) for d, c in body["closes"] if c})
    days = sorted(set(idx) & set(inv) & set(etf.index))
    D = pd.DataFrame(index=days)
    for k in ("투신", "연기금"):
        D[k] = [inv[d].get(k) / idx[d]["거래대금"] if inv[d].get(k) is not None and idx[d]["거래대금"] else np.nan for d in days]
        D[k + "순위"] = past_rank(D[k])
    px = etf.reindex(days)
    C, *_ = Z.load()
    inside, size = Z.universe(C)
    reg, br = N.regimes(C, size)
    weak = (br.reindex(days) < 50).fillna(False)
    for q in (0.2, 0.1):
        sig = (D["투신순위"] <= q) & (D["연기금순위"] <= q)
        print(f"== 둘 다 앞 250일 순위 ≤ {q} · 신호 날 {int(sig.sum())} / {int(D['투신순위'].notna().sum())} ==", flush=True)
        for h in (5, 20):
            f = px.shift(-(1 + h)) / px.shift(-1) - 1
            for tag, lo, hi in (("고르기 2017 ~ 22", "20170101", "20230101"), ("다시 본 2023 ~ 26", "20230101", "20991231")):
                m = (D.index >= lo) & (D.index < hi) & f.notna().values & D["투신순위"].notna().values
                for wtag, w in (("모든 날", np.ones(len(D), bool)), ("폭 < 50", weak.values)):
                    mm = m & w
                    b = f[mm].mean()
                    s = f[mm & sig.values]
                    # 겹침 없는 표본: 신호 뒤 h일 건너뜀
                    pick, nxt = [], -1
                    for i in np.flatnonzero(mm & sig.values):
                        if i > nxt:
                            pick.append(i)
                            nxt = i + h
                    g = f.iloc[pick] - b
                    t = g.mean() / g.std() * np.sqrt(len(g)) if len(g) > 2 and g.std() else np.nan
                    print(f"  {h:2d}일 {tag} {wtag:5s}: 신호 {len(s):3d}날 평균 {s.mean() * 100:+.2f}% vs 바탕 {b * 100:+.2f}% → "
                          f"차 {(s.mean() - b) * 100:+.2f}%p · 겹침 없이 {len(g)}건 {g.mean() * 100:+.2f}%p(t {t:.1f}) · 오른 몫 {(s > 0).mean():.0%}", flush=True)


if __name__ == "__main__":
    main()
