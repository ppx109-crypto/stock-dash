"""KMF-0019 탐색 3 — 노출 줄이기: 진입 시간 창(ENTRY_TO) · 거래마다 멈춤 TS(p) · 이익 잠금 폭 · 하루 멈춤 DS + 날 단위 규칙.
signals 안의 체결 셈과 sim 이 같은 규칙(TS 포함)을 씀. python3 mdd_lab2.py"""
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mdd_lab as D  # noqa: E402
L, K, M13, M14, M15, M16, M17 = D.L, D.K, D.M13, D.M14, D.M15, D.M16, D.M17


def step(state, o, h, l, m, tgt_pm, TS):
    """한 봉: 앞 판단 체결 → TS 멈춤 → 하루 멈춤. state = [pos, entry, real, done]."""
    pos, entry, real, done = state
    if tgt_pm is not None and not done and m <= K.FLAT_AT:
        tgt, pm = tgt_pm
        if tgt != pos:
            if pos:
                real += pos * (o - entry) - K.COST; pos = 0
            if tgt and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > K.DAY_STOP:
                pos, entry = tgt, o; real -= K.COST
    if pos and not done and TS:
        sp = entry - pos * TS
        if (l <= sp) if pos > 0 else (h >= sp):
            px = min(o, sp) if pos > 0 else max(o, sp)
            real += pos * (px - entry) - K.COST; pos = 0
    if pos and not done:
        sp = entry + pos * (K.DAY_STOP - real + K.COST)
        if (l <= sp) if pos > 0 else (h >= sp):
            px = min(o, sp) if pos > 0 else max(o, sp)
            real += pos * (px - entry) - K.COST; pos = 0; done = True
    if not pos and real <= K.DAY_STOP:
        done = True
    state[:] = [pos, entry, real, done]


def run(b, T, R, W, lock, TS):
    """신호와 체결을 한 번에(같은 셈) · 돌려줌 {날: 손익}."""
    n = len(b); days = {}; i = 0
    while i < n:
        d = b[i][0]; j = i
        while j < n and b[j][0] == d:
            j += 1
        st = [0, 0.0, 0.0, False]; peak, halt, last, pend = 0.0, False, 0, None
        for k in range(i, j):
            o, h, l, c, m = b[k][2], b[k][3], b[k][4], b[k][5], b[k][1]
            step(st, o, h, l, m, pend, TS); pend = None
            pos, entry, real, done = st
            if not done and (m >= K.FLAT_AT or k == j - 1) and pos:
                st[2] = real + pos * (c - entry) - K.COST; st[0] = 0
                continue
            if done or m >= K.FLAT_AT:
                continue
            mtm = real + (pos * (c - entry) - K.COST if pos else 0.0)
            peak = max(peak, mtm)
            if lock and peak >= lock[0] and mtm <= peak - lock[1]:
                halt = True
            tgt = 0 if halt else (T[k] or R[k] or W[k])
            if tgt != last:
                last = tgt
                pend = (tgt, m)
            elif not pos and tgt and False:
                pend = None
        days[d] = round(st[2], 4)
        i = j
    return days


if __name__ == "__main__":
    b = M17.prep(K._rows_before(M17.END))
    T = M16.intent(b, M13.signals(b, M13.grid()[0]))
    W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    R3 = M16.intent(b, M14.signals(b, M14.grid()[0])); zero = [0] * len(b)
    K.DAY_STOP = -25.0
    base = run(b, T, R3, W, (40, 15), 0)
    print("기준 다시 셈", D.summ(base))
    rules = [("none",), ("dd", 15, 5), ("dd", 25, 3), ("mo", 25), ("wk", 15)]
    res = []
    for et, ts, lock, ds, rk in itertools.product((600, 630, 660, 900), (0, 8, 5, 3), ((40, 15), (20, 8), None), (25, 15, 10), ("R", "-")):
        K.ENTRY_TO = et; K.DAY_STOP = -float(ds)
        days = run(b, T, R3 if rk == "R" else zero, W, lock, ts)
        for rule in rules:
            s = D.summ(D.throttle(days, rule))
            res.append({"판": f"ET{et}_TS{ts}_LK{lock}_DS{ds}_{rk}_{'_'.join(map(str, rule))}", **s})
    K.ENTRY_TO = 900; K.DAY_STOP = -25.0
    Path(__file__).with_name("mdd_lab2_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    res.sort(key=lambda x: -x["MDD"])
    print("MDD 얕은 순 10"); [print(json.dumps(x, ensure_ascii=False)) for x in res[:10]]
    for lim in (-15, -20, -25, -33, -40, -50):
        c = [x for x in res if x["MDD"] >= lim]
        if c:
            x = max(c, key=lambda x: x["합계"]); print(lim, json.dumps(x, ensure_ascii=False))
