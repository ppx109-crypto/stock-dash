"""I 45회차 — 1시간봉 '장중 하락 이어가기'(I44 H1) 고원 · 비용 · 거울 점검.
T시(10 · 11 · 12 · 13시 봉 끝) 코스피가 어제 종가보다 −X%(1.0 ~ 2.5) → 인버스 1 · 2배, 그날 종가에 팖. 비용 0.2 · 0.4%.
거울: 같은 때 KODEX 200(지수 1배)을 사면 잃어야 '이어가기'가 맞음."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
src = open("/home/user/stock-dash/research/i029.py", encoding="utf-8").read().split('print("== I 44회차')[0]
exec(src)
print("== I 45회차: 장중 하락 이어가기 고원 ==", flush=True)
for name in ("KOSPI", "KOSDAQ"):
    for lev in ((1, 2, -1) if name == "KOSPI" else (1, -1)):
        rows = series(name, lev)
        chg = lambda i: rows[i][2] / rows[i][5] - 1
        for cost in (0.002, 0.004):
            grid = []
            for T in (10, 11, 12, 13):
                cells = []
                for X in (0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025):
                    tr, d = run(rows, lambda i, T=T, X=X: rows[i][1] == T and chg(i) <= -X, cost=cost)
                    js = [judge(tr, d, lo, hi) for _, lo, hi in PER]
                    ok = all(j[2] > 0 and j[3] > -15 for j in js) and all(j[0] >= 3 for j in js)
                    cells.append(("O" if ok else ".") + f"{min(j[2] for j in js):+5.1f}")
                grid.append(f"   {T}시 | " + " ".join(cells))
            tag = "지수 사기(거울)" if lev == -1 else f"인버스 {lev}배"
            print(f"\n[{name} {tag} · 비용 {cost*100:.1f}%] 칸 = 합격(O) · 세 기간 중 가장 나쁜 연 수익 · 문턱 −1.0 · −1.25 · −1.5 · −1.75 · −2.0 · −2.5%", flush=True)
            print("\n".join(grid), flush=True)
print("끝", flush=True)
