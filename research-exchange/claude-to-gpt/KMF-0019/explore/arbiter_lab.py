"""KMF-0019 탐색 8 — 자리 양보 없이 1계약 나누기(사용자 2026-10-13 "12a도 완벽하지않아 자리를 양보할 필요는없어").
자리 정하기(arb):
  V   v12a 우선(비교 기준) · K  신규봇 우선 · F  먼저 든 쪽이 나갈 때까지 자리 가짐
  P5/P10/P20  앞 5/10/20거래일 '혼자 돌렸을 때' 손익이 큰 쪽 우선(그날 아침 정함 · 앞 날만 봄)
  O   둘이 반대 방향이면 둘 다 쉼(같은 방향이거나 한쪽만 원하면 그쪽)
신규봇 몫 하루 한도 C · 신규봇 몫 누적 내림 쉼 PZ(고점에서 X 내려가면 P거래일 신규봇 끔).
python3 arbiter_lab.py <v12a 원장>"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exit_lab as E  # noqa: E402
K, M13, M14, M15, M16, M17, ML, MC, D = E.K, E.M13, E.M14, E.M15, E.M16, E.M17, E.ML, E.MC, E.D


def day_sim(rows, V, KK, lo, hi, arb, vfirst, cap, allowK, ds=25.0):
    pos, own, entry, real, kreal, stopped, kdone = 0, None, 0.0, 0.0, 0.0, False, not allowK
    for i in range(lo, hi):
        d, m, o, h, l, c = rows[i][:6]
        if i > lo and not stopped and m <= K.FLAT_AT:
            pm, pc = rows[i - 1][1], rows[i - 1][5]
            v, k = V[i - 1], KK[i - 1]
            if own == "K" and pos and kreal + pos * (pc - entry) - K.COST <= -cap:
                kdone = True
            if kreal <= -cap:
                kdone = True
            if kdone:
                k = 0
            if arb == "O":
                w, who = ((0, None) if (v and k and v != k) else ((v, "V") if v else ((k, "K") if k else (0, None))))
            elif arb == "F":
                if own == "V" and v:
                    w, who = v, "V"
                elif own == "K" and k:
                    w, who = k, "K"
                else:
                    w, who = (v, "V") if v else ((k, "K") if k else (0, None))
            else:
                first = vfirst
                if first:
                    w, who = (v, "V") if v else ((k, "K") if k else (0, None))
                else:
                    w, who = (k, "K") if k else ((v, "V") if v else (0, None))
            if w != pos:
                if pos:
                    g = pos * (o - entry) - K.COST; real += g
                    if own == "K":
                        kreal += g
                    pos, own = 0, None
                if w and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > -ds:
                    pos, own, entry = w, who, o; real -= K.COST
                    if who == "K":
                        kreal -= K.COST
            elif pos and who and who != own:
                own = who
        if pos and not stopped:
            sp = entry + pos * (-ds - real + K.COST)
            if (l <= sp) if pos > 0 else (h >= sp):
                px = min(o, sp) if pos > 0 else max(o, sp)
                g = pos * (px - entry) - K.COST; real += g
                if own == "K":
                    kreal += g
                pos, stopped = 0, True
        elif not pos and real <= -ds:
            stopped = True
        if pos and (m >= K.FLAT_AT or i == hi - 1):
            g = pos * (c - entry) - K.COST; real += g
            if own == "K":
                kreal += g
            pos = 0
    return real, kreal


def run(rows, spans, V, KK, arb, cap, pz, vsolo, ksolo):
    days, keq, kpk, rest, hist = {}, 0.0, 0.0, 0, []
    for d, lo, hi in spans:
        allow = rest == 0
        if rest:
            rest -= 1
        vfirst = arb in ("V", "F", "O")
        if arb == "K":
            vfirst = False
        if arb.startswith("P"):
            n = int(arb[1:]); past = hist[-n:]
            vfirst = sum(x[0] for x in past) >= sum(x[1] for x in past)
        tot, ks = day_sim(rows, V, KK, lo, hi, arb, vfirst, cap, allow)
        days[d] = tot
        hist.append((vsolo.get(d, 0.0), ksolo.get(d, 0.0)))
        if allow:
            keq += ks; kpk = max(kpk, keq)
            if pz and kpk - keq >= pz[0]:
                rest = pz[1]; kpk = keq
    return days


if __name__ == "__main__":
    rows = K._rows_before(M17.END); b = M17.prep(rows)
    T = M16.intent(b, M13.signals(b, M13.grid()[0])); R = M16.intent(b, M14.signals(b, M14.grid()[0])); W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    vs = ML.v12a_spans(sys.argv[1], rows)
    V = []
    for r in rows:
        v = 0
        for e, x, s, _ in vs.get(r[0], []):
            if e <= r[1] < x:
                v = s
        V.append(v)
    spans, lo = [], 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or rows[i][0] != rows[lo][0]:
            spans.append((rows[lo][0], lo, i)); lo = i
    vsolo, _ = MC.sim(rows, V, [0] * len(V), 999)
    res = []
    for comp, N, n in itertools.product(("W", "TW", "TRW"), (10, 20), (10, 15, 20)):
        it = E.intents(b, comp, T, R, W)
        ksolo, desire = E.run(rows, it, N, 1, n, 1, 25, (40, 15))
        for arb, cap, pz in itertools.product(("V", "K", "F", "P5", "P10", "P20", "O"), (3, 999), (None, (10, 10), (15, 10))):
            s = D.summ(run(rows, spans, V, desire, arb, cap, pz, vsolo, ksolo))
            res.append({"판": f"{comp}_N{N}_B1_n{n}|{arb}|C{cap}|P{pz}", "자리": arb, **s})
    (HERE / "arbiter_lab_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    import collections
    g = collections.defaultdict(list)
    for x in res:
        g[x["자리"]].append(x)
    print("자리 규칙별: 판 수 · MDD≤−15 판 수 · 합계 가운데값 · MDD 가운데값 · 최고 합계(MDD≤−15)")
    for a, v in g.items():
        ok = [x for x in v if x["MDD"] >= -15]
        print(a, len(v), len(ok), sorted(x["합계"] for x in v)[len(v) // 2], sorted(x["MDD"] for x in v)[len(v) // 2],
              max((x["합계"] for x in ok), default=None))
    for lim in (-15, -20):
        c = sorted([x for x in res if x["MDD"] >= lim], key=lambda x: -x["합계"])[:8]
        print("MDD", lim, "이내 상위")
        for x in c:
            print("  ", json.dumps(x, ensure_ascii=False))
