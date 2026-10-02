"""I 17회차 — 달마다 나눠 보기(사용자 2026-10-02 "연으로만 따지면 노는 돈이 잘 안 보이니 월로 분해").
1일봉(새 82 · x008_d1.json) 한 달 동안 쓴 몫 평균 · 1일봉 수익(판 날에 확정) · 빈칸 엔진(i013 최고 판: 1일봉이 20% 미만 쓸 때만 · 급락 되돌림 먼저 → 하락 추세 달러 → 돌리기,
1일봉이 비워 둔 돈 전부)이 보탠 몫 · 합. 2017-01 ~ (시장 폭 자료가 있는 때). 결과: 화면 표 + docs/RL-INVERSE-MONTHS.md."""
import contextlib
import io
import os
import sys
from pathlib import Path

import numpy as np

for _k, _v in dict(I_DIP="1", I_DOLLAR="2", I_GATE="idle20", I_L="20", I_TOP="2", I_CANDS="133690,138230,132030,148070", I_W="1").items():
    os.environ.setdefault(_k, _v)
sys.path.insert(0, "/home/user/stock-dash/research")
with contextlib.redirect_stdout(io.StringIO()):
    import i013 as M

D = M.D
RULE = "1시간봉" if "h1" in os.environ.get("I_LEDGER", "") else "1일봉"
eng = M.mix - M.d1
FIRST = os.environ.get("I_FIRST", "201701")
months = sorted({d[:6] for d in D if d >= FIRST})
rows = []
for m in months:
    idx = [i for i, d in enumerate(D) if d.startswith(m)]
    used = M.used[idx].mean() * 100
    a = (np.prod(1 + M.d1[idx]) - 1) * 100
    c = (np.prod(1 + M.mix[idx]) - 1) * 100
    k = (M.I.K200[idx[-1]] / M.I.K200[idx[0] - 1] - 1) * 100
    rows.append((m, used, k, a, c - a, c))
out = [f"# 달마다 나눠 보기 — {os.environ.get('I_LEDGER', 'x008_d1.json')} + 빈칸 엔진 (I17 · i017)", "",
       f"쓴 몫 = {RULE}이 그달 돈을 쓴 몫(평균) · {RULE} = {RULE} 수익(판 날 확정) · 엔진 보탬 = 빈칸 엔진이 {RULE}이 비워 둔 돈으로 보탠 몫(쓴 몫 < 20%인 날만) · 합 = 계좌 전체.", "",
       f"| 달 | 쓴 몫 | 코스피 | {RULE} | 엔진 보탬 | 합 |", "|---|---|---|---|---|---|"]
for m, u, k, a, e, c in rows:
    out.append(f"| {m[:4]}-{m[4:]} | {u:.0f}% | {k:+.1f}% | {a:+.1f}% | {e:+.1f}% | {c:+.1f}% |")
Path("/home/user/stock-dash/docs/" + os.environ.get("I_OUT", "RL-INVERSE-MONTHS.md")).write_text("\n".join(out) + "\n", encoding="utf-8")
R = np.array([(u, k, a, e, c) for _, u, k, a, e, c in rows])
print(f"== I 17회차: 달마다 나눠 보기({RULE} · {FIRST[:4]}-{FIRST[4:]} ~) ==")
for lab, f in ((f"{RULE}이 거의 쉰 달(쓴 몫 < 20%)", R[:, 0] < 20), ("반쯤 쓴 달(20 ~ 60%)", (R[:, 0] >= 20) & (R[:, 0] < 60)), ("많이 쓴 달(≥ 60%)", R[:, 0] >= 60)):
    s = R[f]
    print(f"  {lab}: {f.sum()}달 | {RULE} 평균 {s[:, 2].mean():+.2f}% · 0인 달 {np.mean(np.abs(s[:, 2]) < 0.05) * 100:.0f}% | 엔진 보탬 평균 {s[:, 3].mean():+.2f}% · + 인 달 {np.mean(s[:, 3] > 0) * 100:.0f}% | 합 평균 {s[:, 4].mean():+.2f}%")
print("\n해 × 달: 쓴 몫(%) / 엔진 보탬(%p)")
print("해    " + " ".join(f"{i:>9d}월" for i in range(1, 13)))
for y in sorted({m[:4] for m in months}):
    cells = []
    for i in range(1, 13):
        r = [x for x in rows if x[0] == f"{y}{i:02d}"]
        cells.append(f"{r[0][1]:3.0f}/{r[0][4]:+5.1f}" if r else " " * 10)
    print(y, " ".join(f"{c:>10s}" for c in cells))
