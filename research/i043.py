"""I 9라운드 ① — 옆걸음 강화: 돌리기 후보를 해외 지수로 넓히기(중국 192090 · 유럽 195930 · 일본 241180 · 다우 245340).
지금 넷(나스닥 · 달러 · 금 · 국채10년)과 견줌. 계좌 전부 · 20일 · 위 2 · 주 끝. A'(2014-06 ~ 2016 · 일본은 2016-04부터라 거의 없음) · B · C.
코스피 옆걸음 달(−2 ~ +2%) 평균도 따로. 고르는 기간은 B(앞)에서 보고 C(뒤) · A'(안 본 앞)에서 시험."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i011 as R
import itools as I

EXTRA = {"192090": "중국", "195930": "유럽", "241180": "일본", "245340": "다우"}
for c in EXTRA:
    R.P[c] = I.px(c)
    p = R.P[c]
    R.R[c] = np.nan_to_num(np.concatenate([[0.0], p[1:] / p[:-1] - 1]))
D = I.DAYS
BASE = ["133690", "138230", "132030", "148070"]
PER = (("A'", "20140601", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))
k = I.K200
kd = np.nan_to_num(np.concatenate([[0.0], k[1:] / k[:-1] - 1]))
months = sorted(set(d[:6] for d in D if d >= "20140601"))
side = {m for m in months if abs(np.prod(1 + kd[np.array([d[:6] == m for d in D])]) - 1) <= 0.02}


def show(tag, x):
    cells = [I.stats(x, lo, hi) for _, lo, hi in PER]
    sm = []
    for _, lo, hi in PER:
        v = [np.prod(1 + x[np.array([d[:6] == m for d in D])]) - 1 for m in side if lo[:6] <= m < hi[:6]]
        sm.append(np.mean(v) * 100 if v else np.nan)
    print(f"  {tag:30s} " + " | ".join(f"{p} {c[0]:+5.1f} · {c[1]:6.1f} (옆 {s:+.2f})" for (p, _, _), c, s in zip(PER, cells, sm)), flush=True)


for nm, cands, top in (("지금 넷 · 위 2", BASE, 2), ("+ 중국 · 유럽", BASE + ["192090", "195930"], 2), ("+ 중국 · 유럽 · 일본", BASE + ["192090", "195930", "241180"], 2),
                       ("+ 넷 다(중 · 유 · 일 · 다우)", BASE + list(EXTRA), 2), ("+ 넷 다 · 위 3", BASE + list(EXTRA), 3), ("지금 넷 + 일본", BASE + ["241180"], 2)):
    show(nm, R.run(R.G["언제나"], R.momentum(20, top, cands)))
