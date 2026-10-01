"""1시간봉 111회차(T2b) — 같은 시각 후보 순서(90 · 94회차 '수급 약 · 이미 오름' 무리)가 정말 좋은 신호를 먼저 고르나, 신호 하나하나로(칸 순서 운 뺌).
같은 봉에 신호가 둘 넘게 난 때만: 무리(0 ~ 2, 클수록 먼저 삼)마다 혼자 산 손익 평균. Q_SRC=yahoo(2023-10 ~ 2026-09) · kis(한투 1년)."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = os.environ.get("Q_SRC", "yahoo")
if src == "kis":
    os.environ["Q_BARS"] = "1h"
    exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
    T = tiers(SIGS)
    sg, EXF = SIGS, exit_rule
else:
    exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
    sigs = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
    KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
    T = tiers(20, 5, 3)
    sg, EXF = sigs, EX


def solo(c, k):
    b = data[c]
    if k + 1 >= len(b["t"]):
        return None
    i = k + 1
    p = {"price": b["o"][i], "i": i, "칸": 4, "처음칸": 4, "peak": b["o"][i], "now": i, "code": c}
    left, got = 1.0, 0.0
    for j in range(i, len(b["t"]) - 1):
        p["peak"] = max(p["peak"], b["c"][j]); p["now"] = j
        n = EXF(c, b, p, j)
        if not n:
            continue
        part = left if n == "all" else min(left, n / 4)
        got += part * (b["o"][j + 1] / p["price"] - 1) * 100
        left -= part; p["칸"] = max(1, round(left * 4))
        if left <= 1e-9:
            break
    if left > 1e-9:
        got += left * (b["c"][-1] / p["price"] - 1) * 100
    return got - H.COST


bybar = {}
for c, b in data.items():
    for k in np.flatnonzero(sg[c]):
        bybar.setdefault(b["t"][k], []).append((c, k))
rows = []
for t, L in bybar.items():
    if len(L) < 2:
        continue
    for c, k in L:
        r = solo(c, k)
        if r is not None:
            rows.append((t[:4], T.get((c, k), 0), r))
print(f"== 1시간봉 111회차: 같은 시각 순서 무리별 신호 손익 ({src} · 같은 봉 둘 넘게 · {len(rows)}건) ==", flush=True)
for y in sorted({r[0] for r in rows}) + ["모두"]:
    R = [r for r in rows if y == "모두" or r[0] == y]
    parts = []
    for g in (2, 1, 0):
        v = [r[2] for r in R if r[1] == g]
        if v:
            parts.append(f"무리 {g}: {statistics.mean(v):+.2f}(가운데 {statistics.median(v):+.2f} · {sum(x > 0 for x in v) / len(v) * 100:.0f}% · {len(v)})")
    print(f"  {y}: " + " | ".join(parts), flush=True)
print("끝", flush=True)
