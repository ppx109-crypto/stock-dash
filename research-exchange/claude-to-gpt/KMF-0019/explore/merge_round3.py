"""KMF-0019 탐색 6 — 합병 계좌 MDD ≤ −15p 찾기: v12a 우선 · W(시간대 봇) 출구판 · KMF 몫 하루 한도 C · 계좌 하루 멈춤 DS
 · KMF 몫 누적 내림 쉼(KMF 몫 누적이 고점에서 X 내려가면 다음 P거래일 KMF 끔 · 다시 켤 때 고점 새로 셈 · 앞 날까지만 봄).
체결 셈은 merge_cap.sim 과 같음(다음 분 시가 · 15:30 정리 · 편도 0.04p).  python3 merge_round3.py <v12a 원장>"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exit_lab as E  # noqa: E402
K, M13, M14, M15, M16, M17, ML, D = E.K, E.M13, E.M14, E.M15, E.M16, E.M17, E.ML, E.D


def day_sim(rows, V, KK, lo, hi, cap, ds, allowK):
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
            w, who = (v, "V") if v else ((k, "K") if (k and not kdone) else (0, None))
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


def run(rows, spans, V, KK, cap, ds, pause):
    days, keq, kpk, rest = {}, 0.0, 0.0, 0
    for d, lo, hi in spans:
        allow = rest == 0
        if rest:
            rest -= 1
        tot, ks = day_sim(rows, V, KK, lo, hi, cap, ds, allow)
        days[d] = tot
        if allow:
            keq += ks; kpk = max(kpk, keq)
            if pause and kpk - keq >= pause[0]:
                rest = pause[1]; kpk = keq
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
    itW = E.intents(b, "W", T, R, W)
    res = []
    pauses = [None] + [(x, p) for x in (6, 10, 15) for p in (3, 5, 10)]
    for N, B, n in itertools.product((0, 10, 20, 30), (0, 1), (10, 15, 20)):
        _, desire = E.run(rows, itW, N, B, n, 1, 25, (40, 15))
        for cap, ds, pz in itertools.product((2, 3, 5, 999), (25, 15), pauses):
            s = D.summ(run(rows, spans, V, desire, cap, ds, pz))
            res.append({"판": f"W_N{N}_B{B}_n{n}_C{cap}_DS{ds}_P{pz}", **s})
    (HERE / "merge_round3_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    res.sort(key=lambda x: -x["MDD"])
    for x in res[:12]:
        print(json.dumps(x, ensure_ascii=False))
    for lim in (-12, -15, -17):
        c = [x for x in res if x["MDD"] >= lim]
        print("MDD", lim, "이내 판 수", len(c))
        for x in sorted(c, key=lambda x: -x["합계"])[:5]:
            print("  ", json.dumps(x, ensure_ascii=False))
