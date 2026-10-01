"""1시간봉 103회차 — 15분봉 두 거르기를 1시간봉 긴 자료(2023-10 ~ 2026-09 · 362종목)에서 '신호 하나하나'로 봄(칸 순서의 운을 뺌).
최고 규칙의 사는 신호(정배열 된 봉 · 없으면 11시 봉)마다 혼자 산 것으로 보고 파는 규칙(94회차 EX)대로 손익(비용 0.30%).
'그날 +2% 위' · '장중 시장 −1% 아래'에 걸리는 신호와 남는 신호를 해마다 견줌. 15분봉(1년)에서는 걸리는 신호가 두 반 모두 나빴음(18 · 20회차)."""
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])


def solo(c, k):
    b = data[c]
    if k + 1 >= len(b["t"]):
        return None
    i = k + 1
    p = {"price": b["o"][i], "i": i, "칸": 4, "처음칸": 4, "peak": b["o"][i], "now": i, "code": c}
    left, got = 1.0, 0.0
    for j in range(i, len(b["t"]) - 1):
        p["peak"] = max(p["peak"], b["c"][j])
        p["now"] = j
        n = EX(c, b, p, j)
        if not n:
            continue
        part = left if n == "all" else min(left, n / 4)
        got += part * (b["o"][j + 1] / p["price"] - 1) * 100
        left -= part
        p["칸"] = max(1, round(left * 4))
        if left <= 1e-9:
            break
    if left > 1e-9:
        got += left * (b["c"][-1] / p["price"] - 1) * 100
    return got - H.COST


rows = []
for c, b in data.items():
    if c.startswith("K"):
        continue
    m = entry_f()(c, b)
    for k in np.flatnonzero(m):
        t = b["t"][k]
        if not ("2023100100" <= t < "2026093000"):
            continue
        r = solo(c, k)
        if r is not None:
            rows.append((t[:4], r, DR[c][k] > 0.02, MKT[c][k] < -0.01, t < "2025040100"))


def show(tag, L):
    if not L:
        return f"{tag} 없음"
    L = sorted(L)
    cut = L[:-1] if len(L) > 3 else L
    return f"{tag} 평균 {sum(L) / len(L):+.2f} · 가운데 {statistics.median(L):+.2f} · 큰1건뺀 {sum(cut) / len(cut):+.2f} · 이김 {sum(x > 0 for x in L) / len(L) * 100:.0f}% ({len(L)})"


print(f"== 1시간봉 103회차: 15분봉 두 거르기, 신호 하나하나 ({len(data)}종목 · 신호 {len(rows)}) ==", flush=True)
for name, sel in (("앞(2023-10 ~ 2025-03)", lambda r: r[4]), ("뒤(2025-04 ~ 2026-09)", lambda r: not r[4]),
                  ("2023", lambda r: r[0] == "2023"), ("2024", lambda r: r[0] == "2024"), ("2025", lambda r: r[0] == "2025"), ("2026", lambda r: r[0] == "2026")):
    R = [r for r in rows if sel(r)]
    print(f"  {name}")
    print("    " + show("모든 신호", [r[1] for r in R]))
    print("    " + show("+2% 위(걸림)", [r[1] for r in R if r[2]]) + " | " + show("남음", [r[1] for r in R if not r[2]]))
    print("    " + show("시장 −1% 아래(걸림)", [r[1] for r in R if r[3]]) + " | " + show("남음", [r[1] for r in R if not r[3]]))
print("끝", flush=True)
