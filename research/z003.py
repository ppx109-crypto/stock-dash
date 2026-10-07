"""Z3 — Z1에서 2017~22로만 골라 뒤 기간에도 버틴 두 재료(연기금 60일 순매수 −, 증권사 목표가 여력 +)를
1일봉 엔진(nrl · 새 82 · 씨앗 8)의 '같은 날 후보가 여럿일 때 사는 순서'로 넣어 엔진 잣대(앞 2017~20 · 뒤 2021~)로 봄(사용자 2026-10-07 "고").
문턱 없음(같은 날 후보끼리 순서만). 거르기 · 칸은 그대로.
- 연기금 60일: 신호 날 **전날까지** 60거래일 연기금 순매수 합 ÷ 같은 60일 거래량 합(nrl.flow_sum lag=1 · ntools.vol_avg 전날까지).
- 목표가 여력: **전날까지** 알려진 증권사 목표가 묶음(nrl.target_before) ÷ **전날** 종가 − 1.
- 합친 점수: 그날 대상(시총 100위 안 행 전체) 안 백분위로 (1 − 연기금) + 여력 · 값 없으면 보통(0.5) — 그날 가로줄만 씀.
Z_PART=check: 자르기 · 더럽히기 · 검사 눈 — 순서 재료를 T까지 자료로만 다시 만들어도 T 이하 행의 값이 같은가.
python research/z003.py   ·   Z_PART=check python research/z003.py
"""
import bisect
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402

rule = nrl.rule
HOLD = nrl.BASE_HOLD
base = rule.order
N = 60


def prev_close(r):
    rows = nrl.prices.get(r["code"], {}).get("rows") or []
    k = bisect.bisect_left([d for d, _ in rows], r["date"])
    return float(rows[k - 1][1]) if k >= 1 else None


def pension(r):
    s, v = nrl.flow_sum(r, N, "연기금"), T.vol_avg(r["code"], r["date"], N)
    return s / (v * N) if s is not None and v else None


def upside(r):
    t, pc = nrl.target_before(r), prev_close(r)
    return t["목표가"] / pc - 1 if t and t.get("목표가") and pc else None


def build_pct():
    """날마다 대상 행 전체에서 두 재료의 정렬된 값(그날 가로줄만)."""
    by = {}
    for r in nrl.inside:
        p, u = pension(r), upside(r)
        d = by.setdefault(r["date"], ([], []))
        if p is not None:
            d[0].append(p)
        if u is not None:
            d[1].append(u)
    return {d: (np.sort(a), np.sort(b)) for d, (a, b) in by.items()}


def combo_fn(table):
    def pct(arr, x):
        return np.searchsorted(arr, x, side="right") / len(arr) if x is not None and len(arr) else 0.5

    def combo(r):
        a, b = table.get(r["date"], (np.array([]), np.array([])))
        return (1 - pct(a, pension(r))) + pct(b, upside(r))
    return combo


def run():
    combo = combo_fn(build_pct())
    print("== Z3: 1일봉 엔진 순서에 연기금(−) · 목표가 여력(+) ==", flush=True)
    base_got = T.once("지금(새 82 · 추세 기울기 순)", holds=HOLD)
    tries = [
        ("순서: 연기금 60일 적게 산 것 먼저", lambda r: ((pension(r) if pension(r) is not None else 0.0), base(r))),
        ("순서: 목표가 여력 큰 것 먼저", lambda r: (-(upside(r) if upside(r) is not None else 0.0), base(r))),
        ("순서: 합친 점수 큰 것 먼저", lambda r: (-combo(r), base(r))),
        ("순서: 합친 점수 아래 1/3만 뒤로(나머지 지금 순)", lambda r: (1 if combo(r) < 2 / 3 else 0, base(r))),
        ("순서: 연기금 위 1/3(많이 산)만 뒤로", lambda r: (1 if combo_part(r) else 0, base(r))),
    ]
    for tag, key in tries:
        got = T.once(tag, holds=HOLD, rank=key)
        T.diff_check(base_got, got)


_TAB = None


def combo_part(r):
    """그날 연기금 순매수가 위 1/3(많이 산)인가."""
    global _TAB
    if _TAB is None:
        _TAB = build_pct()
    a = _TAB.get(r["date"], (np.array([]),))[0]
    p = pension(r)
    return p is not None and len(a) and np.searchsorted(a, p, side="right") / len(a) > 2 / 3


def check(cuts=("20190315", "20220615", "20250902")):
    """자르기 · 더럽히기: 원자료(수급 · 거래량 · 목표가 · 종가)를 T까지만(또는 T 뒤를 엉터리로) 남겨 순서 재료를 다시 만들어도
    T 이하 행의 값이 같아야 함. 검사 눈: 일부러 '그날 수급까지(lag=0)'를 쓴 재료는 반드시 걸려야 함."""
    import copy
    import final_group
    import study
    rows = [r for r in nrl.inside]
    full_p = {(r["code"], r["date"]): pension(r) for r in rows}
    full_u = {(r["code"], r["date"]): upside(r) for r in rows}
    cal = [d for d, _ in nrl.prices["005930"]["rows"]]
    nxt = {d: cal[i + 1] for i, d in enumerate(cal[:-1])}
    # 검사 눈: 일부러 '다음 날 수급까지' 쓴 재료(미래) — 자르기 · 더럽히기에 반드시 걸려야 함
    peek = lambda r: nrl.flow_sum({"code": r["code"], "date": nxt.get(r["date"], r["date"])}, 5, "연기금", lag=0)
    full_k = {(r["code"], r["date"]): peek(r) for r in rows}
    saved = (nrl.FLOW, T.VOL, nrl.TARGETS, nrl.prices)
    ok = True
    for cut in cuts:
        for mode in ("cut", "poison"):
            def keep(d):
                return str(d) <= cut

            def val(d, v):
                return v if mode == "cut" or str(d) <= cut or v is None else -v * 7.3 + 11
            flow, vol, tg, px = {}, {}, {}, {}
            for code in {r["code"] for r in rows}:
                fr = final_group.flow_rows(code)
                if fr:
                    fr2 = [dict(x, **{c: val(x["date"], x.get(c)) for c in nrl.COLS}) for x in fr if mode == "poison" or keep(x["date"])]
                    flow[code] = nrl.flow_entry(fr2)
                body = T._load(f"volume-data/{code}.json") or {}
                vol[code] = T.vol_entry({"날": [[d, val(d, v), *rest] for d, v, *rest in (body.get("날") or [])
                                               if mode == "poison" or keep(d)]})
                got = study.target_timeline(code)
                if got:
                    got = [(d, val(d, x) if not isinstance(x, dict) else {k: val(d, y) if isinstance(y, (int, float)) else y
                                                                          for k, y in x.items()})
                           for d, x in got if mode == "poison" or keep(d)]
                    tg[code] = nrl.target_entry(got)
                p = copy.deepcopy(nrl.prices.get(code))
                if p:
                    p["rows"] = [(d, val(d, c)) for d, c in p["rows"] if mode == "poison" or keep(d)]
                    px[code] = p
            nrl.FLOW, T.VOL, nrl.TARGETS, nrl.prices = flow, vol, tg, px
            try:
                bad = [k for k in full_p if k[1] <= cut and not same(full_p[k], pension({"code": k[0], "date": k[1]}))]
                bad += [k for k in full_u if k[1] <= cut and not same(full_u[k], upside({"code": k[0], "date": k[1]}))]
                caught = any(k[1] <= cut and not same(full_k[k], peek({"code": k[0], "date": k[1]})) for k in full_k)
            finally:
                nrl.FLOW, T.VOL, nrl.TARGETS, nrl.prices = saved
            n = sum(1 for k in full_p if k[1] <= cut)
            print(f"[{mode} {cut}] 순서 재료 {n}행 × 2: {'합격' if not bad else f'불합격 {len(bad)}건 예 {bad[:3]}'} · "
                  f"검사 눈(그날 수급 엿보기) {'걸림' if caught else '안 걸림(고장)'}", flush=True)
            ok &= not bad and caught
    return 0 if ok else 1


def same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= 1e-12 * max(1.0, abs(a)))


def pension_n(r, n):
    s, v = nrl.flow_sum(r, n, "연기금"), T.vol_avg(r["code"], r["date"], n)
    return s / (v * n) if s is not None and v else None


def run_filter():
    """Z2 '크게 산 뒤엔 조심': 연기금이 전날까지 n일 동안 거래량의 x% 넘게 순매수한 후보는 안 삼(문턱은 Z2에서 미리 정한 구간 끝 5 · 10%)."""
    print("== Z3b: 연기금 크게 산 후보 거르기 ==", flush=True)
    base_got = T.once("지금(새 82)", holds=HOLD)
    for n in (5, 20):
        for x in (0.05, 0.10):
            got = T.once(f"거름: 연기금 {n}일 순매수 > 거래량 {x:.0%}", holds=lambda r, n=n, x=x: HOLD(r) and not ((pension_n(r, n) or 0) > x))
            T.diff_check(base_got, got)


if __name__ == "__main__":
    part = os.environ.get("Z_PART")
    sys.exit(check() if part == "check" else run_filter() if part == "filter" else run())
