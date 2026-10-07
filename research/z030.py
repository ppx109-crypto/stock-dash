"""T3b — 투신 단타(docs/RL-TUSIN.md): 분기말 되밀림을 1일봉 엔진 거르기로.
T3(z009)에서 분기 마지막 5거래일 투신 큰 매수 종목이 새 분기에 되밀림(수익률 관리 매수의 반대 매매).
거르기: 신호 날 d가 새 분기 첫 10거래일 안이고, 그 종목의 **앞 분기 마지막 5거래일** 투신 순매수 합 ÷ (그 5일 거래량 합) > x 이면 안 삼.
그 5일은 모두 d 앞(전 분기)이라 신호 날에 이미 앎. x ∈ {2, 5, 10%} — 앞 반(2017 ~ 20)으로 고르고 뒤 반 시험 · 엔진 잣대(씨앗 8).
python research/z030.py
"""
import bisect
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402

CAL = sorted(nrl.BR)
QSTART = {}                                   # 날 → (그 분기 첫 거래일 위치)
for i, d in enumerate(CAL):
    q = (d[:4], (int(d[4:6]) - 1) // 3)
    if i == 0 or (CAL[i - 1][:4], (int(CAL[i - 1][4:6]) - 1) // 3) != q:
        start = i
    QSTART[d] = start


def qend_buy(r):
    """신호 날이 새 분기 첫 10거래일 안이면 앞 분기 마지막 5거래일 투신 순매수 ÷ 거래량, 아니면 None."""
    d = r["date"]
    if d not in QSTART:
        return None
    s = QSTART[d]
    if CAL.index(d) - s >= 10 or s < 5:
        return None
    lastday = CAL[s - 1]
    got = nrl.FLOW.get(r["code"])
    if not got:
        return None
    days, acc, ok, _ = got
    hi = bisect.bisect_right(days, lastday)
    lo = hi - 5
    if lo < 0 or ok[hi] - ok[lo] < 5 or days[hi - 1] != lastday:
        return None
    t = acc["투신"][hi] - acc["투신"][lo]
    v = T.vol_avg(r["code"], CAL[s], 5)                 # 새 분기 첫날 전날까지 5일 평균 = 그 5일
    return t / (v * 5) if v else None


def main():
    print("== T3b: 분기말 투신 큰 매수 종목 새 분기 10일 안 사기(1일봉 엔진) ==", flush=True)
    rows = [r for r in nrl.inside if nrl.BASE_HOLD(r)]
    hit = {x: sum(1 for r in rows if (qend_buy(r) or 0) > x) for x in (0.02, 0.05, 0.10)}
    print("  후보 줄 가운데 걸리는 수: " + " · ".join(f"> {x:.0%} {n}" for x, n in hit.items()), flush=True)
    base = T.once("지금(새 82)", holds=nrl.BASE_HOLD)
    for x in (0.02, 0.05, 0.10):
        got = T.once(f"거름: 분기말 투신 > {x:.0%}", holds=lambda r, x=x: nrl.BASE_HOLD(r) and not ((qend_buy(r) or 0) > x))
        T.diff_check(base, got)


if __name__ == "__main__":
    main()
