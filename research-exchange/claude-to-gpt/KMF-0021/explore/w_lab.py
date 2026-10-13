"""KMF-0021 탐색 1 — 신규봇 혼자 MDD ≤ −20p · 합계 ≥ +800p(사용자 2026-10-13 "신규봇혼자 mdd 20으로 개발 · 수익은 +800").
시간대 봇(W)을 넓힘: 창 모음(A = KMF-0015가 고른 6창 + 되돌림 14:05 · B = 09:05 ~ 14:35 30분마다 10창 이어감 · B+R = B + 되돌림 14:05)
 · 보는 길이 L(15/30분) · 드는 길이 H(30/60/90분) · 작은 움직임 거름 q(0/0.5 ATR) · 전날 개인 수급 거름 f(1/0).
출구(1분봉 · exit_lab): 진입 봉 반대 끝 멈춤 B · 1분 n분 채널 · N분 조기 손절 · 하루 −25p · 이익 잠금 40/15(켬/끔) · 날 단위 쉼.
python3 w_lab.py"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "KMF-0019/explore"))
import exit_lab as E  # noqa: E402
K, M15, M16, M17, D = E.K, E.M15, E.M16, E.M17, E.D

WIN = {"A": ((545, 575, 605, 695, 785, 815), (845,)), "B": (tuple(range(545, 816, 30)), ()), "BR": (tuple(range(545, 816, 30)), (845,))}


def w_signals(b, mom, rev, Lm, Hm, q, flow, bias, atr, idx):
    n = len(b); want = [None] * n
    c = [r[5] for r in b]; o = [r[2] for r in b]
    wins = sorted([(x, 1) for x in mom] + [(x, -1) for x in rev])
    for d in sorted({r[0] for r in b}):
        for h0, sgn in wins:
            s0, s1, e1 = idx.get((d, h0 + 4)), idx.get((d, h0 + Lm - 1)), idx.get((d, h0 + Lm + Hm - 1))
            if s0 is None or s1 is None:
                continue
            a = c[s1] - o[s0]
            if a == 0 or (q and (np.isnan(atr[s1]) or abs(a) < q * atr[s1])):
                continue
            side = int(np.sign(a)) * sgn
            if flow and bias.get(d) != side:
                continue
            if want[s1] is None or want[s1] == 0:
                want[s1] = side
            if e1 is not None:
                want[e1] = 0
    return want


if __name__ == "__main__":
    rows = K._rows_before(M17.END); b = M17.prep(rows)
    c = np.array([r[5] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b]); pc = np.r_[c[0], c[:-1]]
    trr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc)); atr = np.full(len(b), np.nan)
    for i in range(20, len(b)):
        atr[i] = trr[i - 20:i].mean()
    idx = {(r[0], r[1]): i for i, r in enumerate(b)}
    bias = M15.flow_bias(sorted({r[0] for r in b}))
    res = []
    for wk, Lm, Hm, q, f in itertools.product(WIN, (15, 30), (30, 60, 90), (0, 0.5), (1, 0)):
        mom, rev = WIN[wk]
        Wi = M16.intent(b, w_signals(b, mom, rev, Lm, Hm, q, f, bias, atr, idx))
        it = E.intents(b, "W", Wi, Wi, Wi)
        for N, B, n, LK in itertools.product((0, 20), (0, 1), (10, 15, 30), ((40, 15), None)):
            days, _ = E.run(rows, it, N, B, n, 1, 25, LK)
            for rule in (("none",), ("dd", 15, 10), ("dd", 20, 5)):
                res.append({"판": f"{wk}_L{Lm}_H{Hm}_q{q}_f{f}_N{N}_B{B}_n{n}_LK{LK}_{'_'.join(map(str, rule))}", **D.summ(D.throttle(days, rule))})
    (HERE / "w_lab_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    ok = [x for x in res if x["MDD"] >= -20]
    print("MDD ≤ −20 판 수", len(ok), "· 그중 합계 ≥ 800:", sum(1 for x in ok if x["합계"] >= 800))
    for x in sorted(ok, key=lambda x: -x["합계"])[:8]:
        print("  ", json.dumps(x, ensure_ascii=False))
    print("합계/MDD 비 상위")
    for x in sorted(res, key=lambda x: -x["합계"] / max(1, -x["MDD"]))[:8]:
        print("  ", round(x["합계"] / max(1, -x["MDD"]), 1), json.dumps(x, ensure_ascii=False))
    print("합계 상위")
    for x in sorted(res, key=lambda x: -x["합계"])[:5]:
        print("  ", json.dumps(x, ensure_ascii=False))
