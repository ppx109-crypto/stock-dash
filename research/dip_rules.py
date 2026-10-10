"""DIP-DEEP-0042 개발 판 모음 — 판 이름 → (살 조건 · 팔 조건 · 칸 · 순서 · 메모). 판은 지우지 않고 더하기만 함(기록 보존).
python3 research/dip_rules.py 판이름 [판이름 ...]    → 판마다 dip_dev.evaluate()(평가 판 하나씩 · evals.jsonl)"""
import json
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import dip_dev as D  # noqa: E402


def sideways(r, lim=5.0, n=60):
    v = D.ix_ret(r["date"], n)
    return v is not None and abs(v) < lim


def dip(r, lim=-5.0, n=5):
    v = D.ret(r, n)
    return v is not None and v <= lim


def smart(r, n=5, cols=("외국인", "투신")):
    vals = [D.flow_sum(r, n, c) for c in cols]
    return None not in vals and all(v > 0 for v in vals)


def rel(r, n=20):
    a, b = D.ret(r, n), D.ix_ret(r["date"], n)
    return None if a is None or b is None else a - b


def high_break(r, n=60):
    c = D.LANES[r["code"]]["closes"]
    i = r["i"]
    return i >= n and c[i] >= max(c[i - n:i])


def above_ma(r, n=120):
    g = D.ma_gap(r, n)
    return g is not None and g > 0


def ix_above(day, n=200):
    import bisect
    k = bisect.bisect_right(D.IXD, day) - 1
    if k < n - 1:
        return False
    vals = [D.IX[D.IXD[j]] for j in range(k - n + 1, k + 1)]
    return D.IX[D.IXD[k]] > sum(vals) / n


def hb(n=60, side=3, extra=lambda r: True, take=5, stop=7, days=10, cols=("외국인", "투신"), note="", flown=5):
    return dict(holds=lambda r: (side is None or sideways(r, side)) and high_break(r, n) and smart(r, flown, cols) and extra(r),
                exits=D.fixed_exit(take, stop, days), size=lambda r: 2, rank=lambda r: -(rel(r) or 0), note=note)


def flow_rank(r):
    f, t = D.flow_sum(r, 5, "외국인"), D.flow_sum(r, 5, "투신")
    cap = r.get("시가총액") or 0
    return -((f or 0) + (t or 0)) * (r.get("price") or 0) / cap if cap else 0.0


def guard_exit(take, stop, days, reach=5.0, floor=1.0):
    """기본 팔기 + 본전 지키기(한때 +reach% 닿은 뒤 +floor% 아래면 팖)."""
    base = D.fixed_exit(take, stop, days)

    def go(lane, start, price, step, peak, row=None):
        now = (lane["closes"][start + step] / price - 1) * 100
        if (peak / price - 1) * 100 >= reach and now <= floor:
            return True
        return base(lane, start, price, step, peak, row)
    return go


def steady3(r):
    got = D.FLOW.get(r["code"])
    if not got:
        return False
    import bisect
    days, acc, ok = got
    k = bisect.bisect_left(days, r["date"])
    if k < 3:
        return False
    return all(acc["외국인"][j] - acc["외국인"][j - 1] > 0 and acc["투신"][j] - acc["투신"][j - 1] > 0 for j in range(k - 2, k + 1))


def vol20(r):
    import statistics
    c = D.LANES[r["code"]]["closes"]
    i = r["i"]
    if i < 21:
        return None
    return statistics.pstdev([c[j] / c[j - 1] - 1 for j in range(i - 19, i + 1)]) * 100


def deeper_first(r):
    v = D.ret(r, 5)
    return v if v is not None else 0.0


def make(side=5.0, dipv=-5.0, dipn=5, flown=5, cols=("외국인", "투신"), take=5, stop=7, days=10, size=2, note=""):
    """격자 판 만들기(side=None이면 횡보 거르기 없음)."""
    def holds(r):
        return (side is None or sideways(r, side)) and dip(r, dipv, dipn) and smart(r, flown, cols)
    return dict(holds=holds, exits=D.fixed_exit(take, stop, days), size=lambda r, k=size: k, rank=deeper_first, note=note)


WAYS = {
    # 1번 평가 · 첫 채택판(PLAN 5-2)
    "R0": dict(holds=lambda r: sideways(r) and dip(r) and smart(r), exits=D.fixed_exit(5, 7, 10),
               size=lambda r: 2, rank=deeper_first, note="R0: 횡보(069500 60일 |수익| < 5%) · 5일 −5% 이하 · 5일 외국인+투신+ · +5/−7/10일 · 2칸 · 깊은 순"),
    # 2 ~ 10번: R0에서 한 가지씩
    "R0-noside": make(side=None, note="횡보 거르기 뺌(덜어냄)"),
    "R0-side3": make(side=3, note="횡보 문턱 3"),
    "R0-side8": make(side=8, note="횡보 문턱 8"),
    "R0-dip3": make(dipv=-3, note="눌림 −3"),
    "R0-dip8": make(dipv=-8, note="눌림 −8"),
    "R0-tp8": make(take=8, note="익절 8"),
    "R0-sl10": make(stop=10, note="손절 10"),
    "R0-d20": make(days=20, note="기간 20"),
    "R0-fl10": make(flown=10, note="수급 창 10"),
    # 11 ~ : R1(= R0-side3) 위에서 갈래 바꾸기
    "R1-rs5": dict(holds=lambda r: sideways(r, 3) and (rel(r) or -99) >= 5 and smart(r), exits=D.fixed_exit(5, 7, 10),
                   size=lambda r: 2, rank=lambda r: -(rel(r) or 0), note="시장보다 강함(20일 상대 ≥ 5) · 수급 · 횡보3 · 강한 순"),
    "R1-rs10": dict(holds=lambda r: sideways(r, 3) and (rel(r) or -99) >= 10 and smart(r), exits=D.fixed_exit(5, 7, 10),
                    size=lambda r: 2, rank=lambda r: -(rel(r) or 0), note="시장보다 강함(20일 상대 ≥ 10)"),
    "R1-hb60": dict(holds=lambda r: sideways(r, 3) and high_break(r) and smart(r), exits=D.fixed_exit(5, 7, 10),
                    size=lambda r: 2, rank=lambda r: -(rel(r) or 0), note="60일 고가 돌파 · 수급 · 횡보3"),
    "R1-hb60-x": hb(60, take=10, stop=7, days=20, note="고가 돌파 + 팔기 +10/−7/20일"),
    "R1-hb60-ix200": hb(60, extra=lambda r: ix_above(r["date"], 200), note="고가 돌파 + 069500 200일선 위"),
    "R1-hb60-br50": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 50, note="고가 돌파 + 시장 폭 ≥ 50"),
    "R1-hb20": hb(20, note="20일 고가 돌파"),
    "R1-hb60-br40": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="고원: 시장 폭 ≥ 40"),
    "R1-hb60-br60": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 60, note="고원: 시장 폭 ≥ 60"),
    "R1-hb120": hb(120, note="120일 고가 돌파"),
    # 22 ~ : R2(= 고가 돌파 60 · 시장 폭 40 · 횡보 3) 위에서 한 가지씩
    "R2-noside": hb(60, side=None, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 − 횡보 거르기(덜어냄)"),
    "R2-side5": hb(60, side=5, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 횡보 5"),
    "R2-tp3": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, take=3, note="R2 익절 3"),
    "R2-tp8": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, take=8, note="R2 익절 8"),
    "R2-sl5": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, stop=5, note="R2 손절 5"),
    "R2-sl10": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, stop=10, note="R2 손절 10"),
    "R2-d5": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, days=5, note="R2 기간 5"),
    "R2-d20": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, days=20, note="R2 기간 20"),
    "R2-fgn": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, cols=("외국인",), note="R2 수급 외국인만"),
    # 31 ~
    "R2-ind": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40 and (D.flow_sum(r, 5, "개인") or 1) < 0, note="R2 + 개인 순매도"),
    "R2-fl3": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, flown=3, note="R2 수급 창 3"),
    "R2-fl10": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, flown=10, note="R2 수급 창 10"),
    "R2-hb40": hb(40, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 돌파 창 40"),
    "R2-hb90": hb(90, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 돌파 창 90"),
    "R2-rkflow": dict(hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40), rank=flow_rank, note="R2 순서 = 시총 대비 외+투 순매수 큰 순"),
    "R2-guard": dict(hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40), exits=guard_exit(5, 7, 10, 3, 0.5), note="R2 + 본전 지키기(+3 닿은 뒤 +0.5 아래면 팖)"),
    # 38 ~ : 촘촘한 이웃
    "R2-side2": hb(60, side=2, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 횡보 2"),
    "R2-side4": hb(60, side=4, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 횡보 4"),
    "R2-br30": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 30, note="R2 시장 폭 30"),
    "R2-br45": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 45, note="R2 시장 폭 45"),
    "R2-hb50": hb(50, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 돌파 창 50"),
    "R2-hb70": hb(70, extra=lambda r: D.BR.get(r["date"], 0) >= 40, note="R2 돌파 창 70"),
    "R2-d15": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, days=15, note="R2 기간 15"),
    "R2-fl7": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40, flown=7, note="R2 수급 창 7"),
    # 46 ~ : 구조 바꿈
    "R2-steady": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40 and steady3(r), note="R2 + 외+투 3일 연속"),
    "R2-ix20": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40 and (D.ix_ret(r["date"], 20) or -1) > 0, note="R2 + 069500 20일 > 0"),
    "R2-lowvol": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40 and (vol20(r) or 99) < 2.5, note="R2 + 20일 변동성 < 2.5%"),
    "R2-top50": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40 and r.get("시총순위", 999) <= 50, note="R2 + 시총 50위 안"),
    "R2-rel60": dict(hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40), rank=lambda r: -(rel(r, 60) or 0), note="R2 순서 = 60일 상대 강세"),
    # 51 ~
    "R2-noflow": dict(holds=lambda r: sideways(r, 3) and high_break(r, 60) and D.BR.get(r["date"], 0) >= 40,
                      exits=D.fixed_exit(5, 7, 10), size=lambda r: 2, rank=lambda r: -(rel(r) or 0), note="R2 − 수급(덜어냄)"),
    "R2-sz1": dict(hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40), size=lambda r: 1, note="R2 칸 1"),
    "R2-sz3": dict(hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40), size=lambda r: 3, note="R2 칸 3"),
    "R2-fresh": hb(60, extra=lambda r: D.BR.get(r["date"], 0) >= 40 and
                   D.LANES[r["code"]]["closes"][r["i"]] <= 1.03 * max(D.LANES[r["code"]]["closes"][r["i"] - 60:r["i"]]), note="R2 갓 돌파(≤ 1.03배)"),
    "R2-brband": hb(60, side=None, extra=lambda r: 40 <= D.BR.get(r["date"], 0) <= 65, note="횡보 판단을 시장 폭 40 ~ 65로 바꿈"),
    "R1-ma120": dict(holds=lambda r: sideways(r, 3) and dip(r) and above_ma(r) and smart(r), exits=D.fixed_exit(5, 7, 10),
                     size=lambda r: 2, rank=deeper_first, note="R1 + 120일선 위(오름 추세 안 눌림)"),
}


def main():
    out = {}
    for tag in sys.argv[1:]:
        w = WAYS[tag]
        out[tag] = D.evaluate(tag, w["holds"], w["exits"], size=w["size"], rank=w["rank"], note=w["note"])
        print(D.line(tag, out[tag]), flush=True)
    return out


if __name__ == "__main__":
    main()
