"""1시간봉 114회차(T4 ② 뜯어보기) — 정배열 매매(같은 후보 · 그날 종가에 삼)에서 '1시간봉마다 판단'이 '하루 한 번 종가 판단'보다 나은 까닭을 나눔.
하루 한 번 판(B)에서 하나씩 1시간봉으로 바꿈: ① 손절 −10%를 1시간봉 종가로(다음 봉 시가에 팖) ② 이익 지키기(+8 → +1%)를 1시간봉으로 ③ 정배열 깨짐을 그날 종가 대신 다음 날 첫 봉 시가에 팖.
신호 하나하나 · 해마다. Q_SRC=yahoo · kis."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/h112.py", encoding="utf-8").read().split("lo, hi = ")[0])


def mix(c, i0, price, h_stop=False, h_keep=False, next_open_break=False):
    b, t = data[c], data[c]["t"]
    peak = price
    k = i0
    while k < len(t):
        d = t[k][:8]
        j = k
        while j + 1 < len(t) and t[j + 1][:8] == d:
            j += 1
        for q in range(k, j + 1):                       # 1시간봉으로 보는 것들
            cq = b["c"][q]
            peak_q = max(peak, cq)
            g = (cq / price - 1) * 100
            if q + 1 < len(t) and ((h_stop and g <= -10) or (h_keep and (peak_q / price - 1) * 100 >= 8 and g <= 1)):
                return (b["o"][q + 1] / price - 1) * 100 - H.COST
            if h_keep:
                peak = peak_q
        close = b["c"][j]
        peak = max(peak, close)
        g = (close / price - 1) * 100
        nx = ATT[c][j + 1] if j + 1 < len(t) else None
        if (not h_stop and g <= -10) or (not h_keep and (peak / price - 1) * 100 >= 8 and g <= 1):
            return g - H.COST
        if nx is not None and not nx["정배열"]:
            if next_open_break:
                return (b["o"][j + 1] / price - 1) * 100 - H.COST
            return g - H.COST
        k = j + 1
    return (b["c"][-1] / price - 1) * 100 - H.COST


lo, hi = ("2023100100", "2026093000") if src == "yahoo" else ("202509170000", "202609010000")
rows = []
for c, b in data.items():
    if c.startswith("K"):
        continue
    t = b["t"]
    first_of = {}
    for k, s in enumerate(t):
        first_of.setdefault(s[:8], k)
    for d1, k0 in first_of.items():
        if not (lo <= t[k0] < hi) or k0 == 0:
            continue
        x = ATT[c][k0]
        if not (x and okf(x) and IN[c][k0]) or (door(x) or "정배열") != "정배열":
            continue
        p = b["c"][k0 - 1]
        rows.append((d1[:4], mix(c, k0, p), mix(c, k0, p, h_stop=True), mix(c, k0, p, h_keep=True), mix(c, k0, p, next_open_break=True),
                     mix(c, k0, p, True, True, True), solo_from(c, k0, p)))
names = ("하루 한 번(B)", "① 손절만 1시간봉", "② 지키기만 1시간봉", "③ 깨짐은 다음 날 시가", "①②③ 모두", "1시간봉 규칙(A)")
print(f"== 1시간봉 114회차: 정배열 매매 파는 판단 뜯어보기 ({src} · {len(rows)}건) ==", flush=True)
for y in sorted({r[0] for r in rows}) + ["모두"]:
    R = [r for r in rows if y == "모두" or r[0] == y]
    if len(R) < 5:
        continue
    print(f"  {y}({len(R)}): " + " · ".join(f"{n} {statistics.mean([r[i + 1] for r in R]):+.2f}" for i, n in enumerate(names)), flush=True)
print("끝", flush=True)
