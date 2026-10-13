"""공정성 점검(판정 밖): ① 창 고르지 않음(09:05 ~ 13:35 열 창 모두 이어감 · 14:05 · 14:35 되돌림)
② 반 나눠 고르기: 앞 반(01 ~ 05)에서 +인 창만 골라 뒤 반(06 ~ 10)에서 · 거꾸로도 ③ 수급만: 09:05 → 15:30 하루 한 번 전날 개인 z 방향."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import window_lab as W
K, b, S = W.K, W.b, W.S


def run(wins, flow=1, q=0.0, lo=None, hi=None):
    days, tr = K.simulate(b, W.sig({"wins": wins, "q": q, "flow": flow}))
    if lo:
        days = {d: v for d, v in days.items() if lo <= d <= hi}
        tr = [t for t in tr if lo <= t[0] <= hi]
    return S.report(days, tr)


ALL = [545 + 30 * k for k in range(10)]
for flow in (0, 1):
    r = run([(x, "mom") for x in ALL] + [(845, "rev"), (875, "rev")], flow)
    print(f"① 열 창 모두 + 늦은 되돌림 · 수급 {flow}:", {k: r[k] for k in ("total", "ex10", "trades", "pos_m", "worst_m", "mdd")})
# ② 반 나눠 고르기(창 하나씩 앞 반 성적으로)
halves = (("20260101", "20260531"), ("20260601", "20261012"))
for a, bb in ((0, 1), (1, 0)):
    lo, hi = halves[a]
    pick = []
    for x in ALL + [845, 875]:
        mode_ok = []
        for mode in ("mom", "rev"):
            r = run([(x, mode)], 1, 0.0, lo, hi)
            mode_ok.append((r["total"], mode))
        best = max(mode_ok)
        if best[0] > 0:
            pick.append((x, best[1]))
    lo2, hi2 = halves[bb]
    r = run(pick, 1, 0.0, lo2, hi2)
    print(f"② {lo[:6]}~{hi[:6]}에서 고른 창 {len(pick)}개 → {lo2[:6]}~{hi2[:6]}:", {k: r[k] for k in ("total", "ex10", "trades", "pos_m", "worst_m")}, [f"{p[0]//60:02d}:{p[0]%60:02d}{p[1][0]}" for p in pick])
# ③ 수급만: 하루 한 번
want = [None] * len(b)
for d in sorted({r[0] for r in b}):
    i0 = W.idx.get((d, 549)); i1 = W.idx.get((d, 924))
    if i0 is None or i1 is None or d not in W.bias:
        continue
    want[i0] = W.bias[d]                              # 09:05 ~ 09:09 봉 종가 판단 → 09:10 시가 체결
days, tr = K.simulate(b, want)
r = S.report(days, tr)
print("③ 수급만(하루 한 번 · 장 끝까지):", {k: r[k] for k in ("total", "ex10", "trades", "pos_m", "worst_m", "mdd")}, r["months"])
