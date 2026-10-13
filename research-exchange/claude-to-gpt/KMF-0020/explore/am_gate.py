"""KMF-0020 탐색 4 — 아침 몰림 거름: 10:00에 '아침 1시간 범위 ÷ 앞 20거래일 평균 하루 범위'가 q 이상이면 그날 10:00 뒤 새 진입 안 함(든 자리는 그대로 출구 규칙).
앞 날 범위 · 그날 10:00까지 자료만 씀. KMF-0017(5분봉)과 W 출구판(1분봉)에 붙여 봄. python3 am_gate.py"""
import itertools, json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "KMF-0019/explore"))
import exit_lab as E  # noqa: E402
import mdd_lab as D2  # noqa: E402
K, M13, M14, M15, M16, M17, D = E.K, E.M13, E.M14, E.M15, E.M16, E.M17, E.D


def gate_days(rows, q):
    by = defaultdict(list)
    for r in rows:
        if 540 <= r[1] <= 930:
            by[r[0]].append(r)
    hist, block = [], set()
    for d in sorted(by):
        x = by[d]; am = [r for r in x if r[1] < 600]
        if len(hist) >= 20 and am:
            amr = max(r[3] for r in am) - min(r[4] for r in am)
            if amr / (sum(hist[-20:]) / 20) >= q:
                block.add(d)
        hist.append(max(r[3] for r in x) - min(r[4] for r in x))
    return block


def mask(S, b, block):
    return {c: [0 if (b[k][0] in block and b[k][1] >= 600 and v and (k == 0 or S[c][k - 1] != v or b[k - 1][0] != b[k][0])) else v
                for k, v in enumerate(S[c])] for c in S}


if __name__ == "__main__":
    rows = K._rows_before(M17.END); b = M17.prep(rows)
    S = {"T": M16.intent(b, M13.signals(b, M13.grid()[0])), "R": M16.intent(b, M14.signals(b, M14.grid()[0])), "W": M16.intent(b, M15.signals(b, M15.grid()[0]))}
    res = []
    for q in (None, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0):
        block = gate_days(rows, q) if q else set()
        # 새 진입만 막기: 막힌 날 10:00 뒤 '새로 켜지는' 의도는 0으로 · 이어지던 의도는 그대로(간단판: 막힌 날 10:00 뒤 의도 0 = 든 자리도 정리)
        S2 = {c: [0 if (b[k][0] in block and b[k][1] >= 600) else v for k, v in enumerate(S[c])] for c in S}
        days, _ = K.simulate(b, D2.signals(b, S2["T"], S2["R"], S2["W"], (40, 15)))
        res.append({"판": f"KMF17_q{q}", "막힌 날": len(block), **D.summ(days)})
        for N, n in itertools.product((10, 20), (10, 15, 20)):
            it = E.intents(b, "W", S2["T"], S2["R"], S2["W"])
            d2, _ = E.run(rows, it, N, 1, n, 1, 25, (40, 15))
            res.append({"판": f"W_N{N}_B1_n{n}_q{q}", "막힌 날": len(block), **D.summ(d2)})
    (HERE / "am_gate_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    for x in res:
        if x["판"].startswith("KMF17"):
            print(json.dumps(x, ensure_ascii=False))
    for x in sorted([x for x in res if x["판"].startswith("W")], key=lambda x: -x["MDD"])[:8]:
        print(json.dumps(x, ensure_ascii=False))
