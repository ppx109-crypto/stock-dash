"""B1 — 봇 강화(docs/RL-BOTS.md): 1일봉 후보 거르기 — 이번 주 수급 연구에서 '약하지만 두 반 같은 쪽'으로 남은 것들.
신호 날 d(그날 종가에 삼)의 **전날(d−1)까지** 수급만 씀(nrl.flow_sum lag=1 · 장 끝난 뒤 나오는 수급 → 다음 날부터).
- F1 투신 오래 사던 종목(T5 '이미 사던 중' 20일 −0.34%p): 전날까지 n일 투신 순매수 ÷ 그 n일 거래량 > x
- F2 외국인이 판 걸 투신이 받음(T7 −0.29%p): 전날 투신 순매수 > 거래량(20일 평균) × x 이고 외국인 순매도 < −x
- F3 코스닥 투신 큰 매수 다음 날(T6 −0.76%p): 코스닥 종목 · 전날 투신 순매수 > 거래량(20일 평균) × x
문턱은 Z2 · T 회차에서 미리 본 구간 끝(2 · 5 · 10%) — 앞 반(2017 ~ 20)으로 고르고 뒤 반(2021 ~ )은 시험.
python research/z023.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402

HOLD = nrl.BASE_HOLD
KQ = {p.stem for p in Path("/home/user/stock-dash/kosdaq-data").glob("*.json")}


def share(r, n, col):
    s, v = nrl.flow_sum(r, n, col), T.vol_avg(r["code"], r["date"], n)
    return s / (v * n) if s is not None and v else None


def day1(r, col):
    s, v = nrl.flow_sum(r, 1, col), T.vol_avg(r["code"], r["date"], 20)
    return s / v if s is not None and v else None


def f1(n, x):
    return lambda r: (share(r, n, "투신") or 0) > x


def f2(x):
    return lambda r: (day1(r, "투신") or 0) > x and (day1(r, "외국인") or 0) < -x


def f3(x):
    return lambda r: r["code"] in KQ and (day1(r, "투신") or 0) > x


def main():
    print("== B1: 1일봉 후보 거르기(수급) ==", flush=True)
    base = T.once("지금(새 82)", holds=HOLD)
    tests = [(f"F1 투신 {n}일 순매수 > 거래량 {x:.0%}", f1(n, x)) for n in (5, 10, 20) for x in (0.02, 0.05)]
    tests += [(f"F2 전날 투신 > {x:.0%} · 외국인 < −{x:.0%}", f2(x)) for x in (0.02, 0.05, 0.10)]
    tests += [(f"F3 코스닥 · 전날 투신 > {x:.0%}", f3(x)) for x in (0.02, 0.05)]
    for tag, bad in tests:
        got = T.once("거름: " + tag, holds=lambda r, bad=bad: HOLD(r) and not bad(r))
        T.diff_check(base, got)


if __name__ == "__main__":
    main()
