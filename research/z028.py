"""N10 — 좁은 장 RL(docs/RL-NARROW.md): 1일봉 정배열 문의 '시장 폭 ≥ 50'을 큰 종목만의 폭으로.
폭(k) = 그날 시총 1 ~ k위(그날 순위) 가운데 50일선 > 200일선 몫(%) — 그날 종가까지 값(nrl.BR과 같은 셈 · 순위만 좁힘).
판: 폭30 ≥ 50 · 폭10 ≥ 50 · (폭100 ≥ 50 또는 폭30 ≥ 50) · (폭100 ≥ 50 또는 폭10 ≥ 60) — 엔진 잣대(씨앗 8 · 두 반 · 행운뺌).
python research/z028.py
"""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402
import rule  # noqa: E402


def breadth_top(k):
    by = {}
    for r in nrl.inside:
        if (r.get("시총순위") or 999) > k:
            continue
        one = nrl.shape[r["code"]]
        if np.isnan(one["200"][r["i"]]):
            continue
        by.setdefault(r["date"], []).append(bool(one["50>200"][r["i"]]))
    return {d: sum(v) / len(v) * 100 for d, v in by.items() if len(v) >= max(5, k // 2)}


B30, B10 = breadth_top(30), breadth_top(10)


def aligned_with(gate):
    def f(r):
        g = nrl.F.form_of(nrl.shape, r)
        return g.get("정배열") and g.get("간격") is not None and nrl.LO <= g["간격"] < nrl.HI and gate(r["date"])
    return f


def holds(al):
    return lambda r: (rule.holds(r) or al(r)) and nrl.teacher(r) and not nrl.target_cut(r)


def main():
    days = sorted(nrl.BR)
    narrow = [d for d in days if nrl.BR[d] < 50]
    print(f"== N10: 큰 종목만의 폭 · 폭100 < 50 날 {len(narrow)} 가운데 폭30 ≥ 50 {sum(B30.get(d, 0) >= 50 for d in narrow)} · "
          f"폭10 ≥ 50 {sum(B10.get(d, 0) >= 50 for d in narrow)} ==", flush=True)
    base = T.once("지금(새 82 · 폭100 ≥ 50)", holds=nrl.BASE_HOLD)
    for tag, gate in (("폭30 ≥ 50", lambda d: B30.get(d, 0) >= 50),
                      ("폭10 ≥ 50", lambda d: B10.get(d, 0) >= 50),
                      ("폭100 ≥ 50 또는 폭30 ≥ 50", lambda d: nrl.BR.get(d, 0) >= 50 or B30.get(d, 0) >= 50),
                      ("폭100 ≥ 50 또는 폭10 ≥ 60", lambda d: nrl.BR.get(d, 0) >= 50 or B10.get(d, 0) >= 60)):
        got = T.once(tag, holds=holds(aligned_with(gate)))
        T.diff_check(base, got)


if __name__ == "__main__":
    main()
