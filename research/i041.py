"""I 7라운드 ② ~ ⑤ — 돌리기 다듬기를 A(2012 ~ 2016) · B · C 세 기간에서(계좌 전부 · 돌리기만).
② 후보에 단기채(153130) · 코스피 인버스(114800 · 20일 오르면 고름 = 추세 따라 인버스) 넣기
③ 기간 L 10 · 20 · 40 · 60 × 위 1 · 2개(고원)
⑤ 다시 고르는 날: 주 끝 · 날마다(비용) — 미래 참조: 고르는 날 종가까지의 L일 수익만."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i011 as R
import itools as I

for c in ("153130", "114800"):
    if c not in R.P:
        R.P[c] = I.px(c)
        p = R.P[c]
        R.R[c] = np.nan_to_num(np.concatenate([[0.0], p[1:] / p[:-1] - 1]))
BASE = ["133690", "138230", "132030", "148070"]
PER = (("A", "20120101", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))


def show(tag, x):
    cells = [I.stats(x, lo, hi) for _, lo, hi in PER]
    ok = all(c[0] > 0 and c[1] > -15 for c in cells)
    print(f"  {tag:34s} " + " | ".join(f"{p} {c[0]:+5.1f} · {c[1]:6.1f}" for (p, _, _), c in zip(PER, cells)) + ("  ✓" if ok else ""), flush=True)


print("== ② 후보 넣기(20일 · 위 2) ==")
for nm, cands in (("지금 넷", BASE), ("+ 단기채", BASE + ["153130"]), ("+ 코스피 인버스", BASE + ["114800"]), ("+ 둘 다", BASE + ["153130", "114800"])):
    show(nm, R.run(R.G["언제나"], R.momentum(20, 2, cands)))
print("== ③ 기간 × 위 몇 개(지금 넷) ==")
for L in (10, 20, 40, 60):
    for top in (1, 2):
        show(f"{L}일 · 위 {top}", R.run(R.G["언제나"], R.momentum(L, top, BASE)))
print("== ⑤ 고르는 날 ==")
for reb in ("week", "mon", "day"):
    show(f"20일 · 위 2 · {reb}", R.run(R.G["언제나"], R.momentum(20, 2, BASE), reb=reb))
