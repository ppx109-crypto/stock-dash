"""T9 · T10 · T11 — 투신 단타(docs/RL-TUSIN.md · 사용자 "기관 · 투신 · 외국인 · 개인 매매법 조합 없어?").
대상 200 · 그날(t) 수급(장 끝난 뒤) → **t+1 종가에 사서** 5 · 20일 초과(그날 가운데값 뺌) − 바탕 [앞 2017 ~ 21 / 뒤 2022 ~ 26] · 나을 확률 · 20일 중앙.
T9: 투신 크게 팖(순매수 ÷ 거래량 아래 10%) · T10: 투신 위 10% × 연기금 · 사모 같이 삼(> 0) / 안 삼(≤ 0)
T11: 그날 투신 · 외국인 · 개인 순매수 부호 8가지 조합(+ + + … − − −) — 이미 쓰는 '외국인 + · 투신 + · 개인 −'(1일봉 가르침은 5일 합)도 하루치로 견줌.
python research/z038.py
"""
import itertools
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
    tu = (F["투신"] / F["vol"]).where(ok).rank(axis=1, pct=True)
    groups = {"T9 투신 크게 팖(아래 10%)": (tu <= 0.1) & ok,
              "T10 투신 위 10% · 연기금도 삼": (tu > 0.9) & (F["연기금"] > 0) & ok,
              "T10 투신 위 10% · 연기금 안 삼": (tu > 0.9) & (F["연기금"] <= 0) & ok,
              "T10 투신 위 10% · 사모도 삼": (tu > 0.9) & (F["사모"] > 0) & ok,
              "T10 투신 위 10% · 사모 안 삼": (tu > 0.9) & (F["사모"] <= 0) & ok}
    sgn = {k: F[k] > 0 for k in ("투신", "외국인", "개인")}
    for a, b, c in itertools.product((True, False), repeat=3):
        lab = f"T11 투신{'+' if a else '−'} 외국인{'+' if b else '−'} 개인{'+' if c else '−'}"
        groups[lab] = (sgn["투신"] == a) & (sgn["외국인"] == b) & (sgn["개인"] == c) & ok & F["투신"].notna() & F["외국인"].notna() & F["개인"].notna()
    first = pd.Series(C.index < "20220101", index=C.index)
    for h in (5, 20):
        f = C.shift(-(1 + h)) / C.shift(-1) - 1
        ex = f.where(ok).sub(f.where(ok).median(axis=1), axis=0)
        b, bf, bb = ex.stack().dropna(), ex[first].stack().dropna(), ex[~first].stack().dropna()
        print(f"[{h}일] 바탕 {b.mean() * 100:+.2f}% · 나을 {(b > 0).mean():.0%}", flush=True)
        for lab, g in groups.items():
            e = ex.where(g)
            s, sf, sb = e.stack().dropna(), e[first].stack().dropna(), e[~first].stack().dropna()
            print(f"  {lab:28s} {len(s):7d}건 · {(s.mean() - b.mean()) * 100:+.2f}%p [{(sf.mean() - bf.mean()) * 100:+.2f}/{(sb.mean() - bb.mean()) * 100:+.2f}]"
                  f" · 중앙 {s.median() * 100:+.2f} · 나을 {(s > 0).mean():.0%}", flush=True)


if __name__ == "__main__":
    main()
