"""I 15회차 — 인버스 '반등 꺾임' 판: 하락 추세(20일선 < 60일선)에서 코스피가 20일선 위로 반등했다가 다시 20일선 아래로 꺾인 날(어제 ≥ 20일선 · 오늘 < 20일선)
또는 반등이 5일 +3% 넘게 됐다가 오늘 −1% 넘게 빠진 날, 그날 종가에 KODEX 인버스(114800 · 1배) — I1(하락 시작에 들어감)은 되돌림에 잃음 → 반등 끝에 들어감.
나오는 법: 익절 3 · 4 · 6 × 손절 2 · 3 × 5 · 10 · 20일 · 손절 뒤 쉬기 0 · 10. 켜는 때: 빈 날(시장 폭 < 50 · A는 코스피 < 200일선) 또는 언제나."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

k = I.K200
m20, m60, m200 = I.ma(k, 20), I.ma(k, 60), I.ma(k, 200)
r1 = np.nan_to_num(I.ret(k, 1), nan=0)
r5y = np.concatenate([[0], np.nan_to_num(I.ret(k, 5), nan=0)[:-1]])
nz = lambda a: np.nan_to_num(a, nan=0) > 0
down = nz(m20 < m60)
k_y, m20_y = np.concatenate([[np.nan], k[:-1]]), np.concatenate([[np.nan], m20[:-1]])
br = I.breadth()
gate = np.where(np.isnan(br), nz(k < m200), br < 50)
SIG = {
    "R1 20일선 위 → 아래로 꺾임": down & nz(k_y >= m20_y) & nz(k < m20),
    "R2 5일 +3% 반등 뒤 −1%": down & (r5y >= 0.03) & (r1 <= -0.01),
    "R3 R1 또는 R2": (down & nz(k_y >= m20_y) & nz(k < m20)) | (down & (r5y >= 0.03) & (r1 <= -0.01)),
}
PER = (("A", "20090916", "20170101"), ("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 15회차: 인버스 '반등 꺾임' ==", flush=True)
for gname, g in (("빈 날", gate), ("언제나", np.ones(len(k), bool))):
    for name, sig in SIG.items():
        rows = []
        for take in (0.03, 0.04, 0.06):
            for stop in (-0.02, -0.03):
                for maxd in (5, 10, 20):
                    for cool in (0, 10):
                        tr, d = I.sim(sig & g, "114800", stop, take, maxd, cool=cool)
                        js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
                        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                        rows.append((ok, min(j["cagr"] for j in js), I.line(f"익절 {take*100:.0f} 손절 {stop*100:.0f} {maxd}일 쉬기 {cool}", tr, d, PER)[0]))
        rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
        print(f"\n[{gname} · {name}] 신호 날 {int((sig & g).sum())} · 합격 {sum(r[0] for r in rows)}/{len(rows)}", flush=True)
        for ok, w, t in rows[:2]:
            print(f"  {'합격' if ok else '    '} (가장 나쁜 {w:+5.1f}) {t.strip()}", flush=True)
print("끝", flush=True)
