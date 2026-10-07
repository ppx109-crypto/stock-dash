"""N17 — 좁은 장 RL(docs/RL-NARROW.md): 1일봉 ② 정배열 문의 '시장 폭 ≥ 50'을 좁은 오름장(코스피 ≥ 60일선)에서는 빼기.
지금: 정배열 문 = 정배열 · 간격 19 ~ 53% · 폭 ≥ 50(nrl.aligned). 수급(teacher) · 목표가(target_cut) 문은 그대로.
판: ① 폭 ≥ 50 또는 코스피 ≥ 60일선 ② 폭 ≥ 50 또는 (코스피 ≥ 60일선 · 폭 ≥ 40)(덜 풀기 · 참고).
코스피 60일선 = 그날 종가까지 60일 평균(그날 종가 포함 · 지금 규칙이 그날 폭을 쓰는 것과 같은 시점). 엔진 잣대(씨앗 8 · 두 반 · 행운뺌 · 비용).
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl python research/z072.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402
import rule  # noqa: E402

k = json.loads(Path("/home/user/stock-dash/market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"]
KC = pd.Series({str(r["date"]): float(r["종가"]) for r in k if r.get("종가")}).sort_index()
KUP = (KC >= KC.rolling(60, min_periods=60).mean()).to_dict()


def aligned_with(gate):
    def f(r):
        g = nrl.F.form_of(nrl.shape, r)
        return g.get("정배열") and g.get("간격") is not None and nrl.LO <= g["간격"] < nrl.HI and gate(r["date"])
    return f


def holds(al):
    return lambda r: (rule.holds(r) or al(r)) and nrl.teacher(r) and not nrl.target_cut(r)


def main():
    days = sorted(nrl.BR)
    nu = [d for d in days if nrl.BR[d] < 50 and KUP.get(d)]
    print(f"== N17: 폭 < 50 · 코스피 ≥ 60일선 날 {len(nu)} / {len(days)} "
          f"(2023 앞 {sum(d < '20230101' for d in nu)} · 뒤 {sum(d >= '20230101' for d in nu)}) ==", flush=True)
    base = T.once("지금(새 82 · 폭 ≥ 50)", holds=nrl.BASE_HOLD)
    for tag, gate in (("① 폭 ≥ 50 또는 코스피 ≥ 60일선", lambda d: nrl.BR.get(d, 0) >= 50 or bool(KUP.get(d))),
                      ("② 폭 ≥ 50 또는 (코스피 ≥ 60일선 · 폭 ≥ 40)", lambda d: nrl.BR.get(d, 0) >= 50 or (bool(KUP.get(d)) and nrl.BR.get(d, 0) >= 40))):
        got = T.once(tag, holds=holds(aligned_with(gate)))
        T.diff_check(base, got)


if __name__ == "__main__":
    main()
