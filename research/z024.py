"""B2 — 봇 강화(docs/RL-BOTS.md): 1일봉 칸 크기를 종목 변동성에 맞추기(P8).
변동성 = 신호 날 종가까지 앞 60거래일 하루 수익 표준편차(그날 종가에 사므로 그 종가까지는 앎).
- 문턱: **앞 반(2017 ~ 20) 후보들**의 변동성 1/3 · 2/3 값(앞 반만으로 정함 · 뒤 반은 시험).
- 판 V1: 변동 큰 1/3은 칸 −1(최소 1) · V2: 큰 1/3 −1 · 작은 1/3 +1(최대 4) · V3: 칸 × (가운데값 ÷ 변동성)을 반올림 1 ~ 4.
- 반익절은 칸 // 2 그대로(nrl.half_rule이 BASE_SIZE를 부르므로 그 함수도 바꿔 끼움).
python research/z024.py
"""
import statistics
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402

HOLD = nrl.BASE_HOLD
BASE = nrl.BASE_SIZE


def vol(r, n=60):
    c = nrl.lanes[r["code"]]["closes"]
    i = r["i"]
    if i < n + 1:
        return None
    rs = [c[k] / c[k - 1] - 1 for k in range(i - n + 1, i + 1) if c[k - 1]]
    return statistics.pstdev(rs) if len(rs) >= n // 2 else None


early_v = sorted(v for v in (vol(r) for r in nrl.early if HOLD(r)) if v is not None)
LO, MIDV, HI = (early_v[int(len(early_v) * q)] for q in (1 / 3, 0.5, 2 / 3))


def v1(r):
    v, b = vol(r), BASE(r)
    return max(1, b - 1) if v is not None and v > HI else b


def v2(r):
    v, b = vol(r), BASE(r)
    if v is None:
        return b
    return max(1, b - 1) if v > HI else min(4, b + 1) if v < LO else b


def v3(r):
    v, b = vol(r), BASE(r)
    return b if not v else int(min(4, max(1, round(b * MIDV / v))))


def main():
    print(f"== B2: 칸 크기 × 변동성 · 앞 반 후보 변동성 1/3 {LO * 100:.2f}% · 가운데 {MIDV * 100:.2f}% · 2/3 {HI * 100:.2f}% ==", flush=True)
    base = T.once("지금(새 82)", holds=HOLD)
    for tag, fn in (("V1 변동 큰 1/3 칸 −1", v1), ("V2 큰 1/3 −1 · 작은 1/3 +1", v2), ("V3 칸 × 가운데 ÷ 변동성", v3)):
        nrl.BASE_SIZE = fn                       # 반익절(half_rule)도 이 칸으로 나눔
        got = T.once(tag, holds=HOLD, size=fn)
        T.diff_check(base, got)
    nrl.BASE_SIZE = BASE


if __name__ == "__main__":
    main()
