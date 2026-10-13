"""KMF-0020 탐색 3 — 손실 작은 봇 여럿 섞기(1계약 · 1분봉 셈 · exit_lab 출구 그대로).
봇: T 추세 · R 횡보 · W 시간대 · X(RX: R이 틀리면 뒤집기 s1.0) · O(아침 범위 돌파: 09:00~09:29 고저를 09:30 뒤 5분봉 종가가 넘으면 그 방향).
섞기 = 글자 순서가 우선순위. 출구: 진입 봉 반대 끝 멈춤 · 1분 n분 채널 · N분 조기 손절 · 하루 멈춤 DS · 이익 잠금 40/15.
날 단위 쉼(dd X,P)도 함께. python3 mix_lab.py"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "KMF-0019/explore"))
import exit_lab as E  # noqa: E402
import rx_lab as RXL  # noqa: E402
K, M13, M14, M15, M16, M17, D = E.K, E.M13, E.M14, E.M15, E.M16, E.M17, E.D


def orb(b):
    out = [0] * len(b); day = None
    for k, r in enumerate(b):
        if r[0] != day:
            day, hi, lo, cur = r[0], None, None, 0
        m = r[1]
        if m < 570:
            hi = r[3] if hi is None else max(hi, r[3]); lo = r[4] if lo is None else min(lo, r[4])
        elif hi is not None and cur == 0:
            if r[5] > hi:
                cur = 1
            elif r[5] < lo:
                cur = -1
        out[k] = cur if m >= 570 else 0
    return out


def intents(b, comp, S):
    out = {}
    for k, r in enumerate(b):
        v = 0
        for c in comp:
            if S[c][k]:
                v = S[c][k]; break
        out[(r[0], r[1])] = (v, r[3], r[4])
    return out


if __name__ == "__main__":
    rows = K._rows_before(M17.END); b = M17.prep(rows)
    S = {"T": M16.intent(b, M13.signals(b, M13.grid()[0])), "R": M16.intent(b, M14.signals(b, M14.grid()[0])),
         "W": M16.intent(b, M15.signals(b, M15.grid()[0]))}
    S["X"] = RXL.rx(b, S["R"], RXL.atr14(b), 1.0, 6, 4); S["O"] = orb(b)
    comps = ("W", "O", "X", "WO", "OW", "WX", "XW", "OX", "WOX", "OWX", "XWO", "TWX", "WXT", "OWT", "WOXT")
    res = []
    rules = [("none",), ("dd", 10, 5), ("dd", 15, 10), ("dd", 20, 5)]
    for comp, N, n, ds in itertools.product(comps, (10, 20), (10, 15, 20), (25, 12, 8)):
        days, _ = E.run(rows, intents(b, comp, S), N, 1, n, 1, ds, (40, 15))
        for rule in rules:
            res.append({"판": f"{comp}_N{N}_n{n}_DS{ds}_{'_'.join(map(str, rule))}", **D.summ(D.throttle(days, rule))})
    (HERE / "mix_lab_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    for comp in comps:
        v = [x for x in res if x["판"].split("_")[0] == comp and x["판"].endswith("none")]
        best = max(v, key=lambda x: x["MDD"]); top = max(v, key=lambda x: x["합계"])
        print(f"{comp:5s} 혼자 쉼없음: MDD 가장 얕은 {best['MDD']} (합 {best['합계']}) · 합계 최고 {top['합계']} (MDD {top['MDD']})")
    res.sort(key=lambda x: -x["MDD"])
    print("MDD 얕은 순"); [print(json.dumps(x, ensure_ascii=False)) for x in res[:8]]
    for lim in (-15, -20, -25, -30):
        c = sorted([x for x in res if x["MDD"] >= lim], key=lambda x: -x["합계"])
        print("MDD", lim, "이내", len(c), "판 · 상위:", [json.dumps(x, ensure_ascii=False) for x in c[:3]])
