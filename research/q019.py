"""15분봉 18회차 — 칸 순서의 운을 뺀 '신호 하나하나' 평가. 새 후보의 10:45 사기 신호마다 혼자 산 것으로 보고
(다음 봉 시가에 사서 파는 규칙대로 — 팔 봉이 닫히면 다음 봉 시가, 절반 팔기는 반만) 손익을 낸 뒤,
거르기에 걸리는 신호와 남는 신호의 평균을 두 반으로 견줌. 비용 0.30%. 161종목.
- 오늘 +2% 위(이미 거르는 것) · 장중 시장 흐름 x 아래(x = 0 · −0.5 · −1 · −1.5%)
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])

PER = M.periods()


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
        n = exit_rule(c, b, p, j)
        if not n:
            continue
        px = b["o"][j + 1]
        part = left if n == "all" else min(left, n / 4)
        got += part * (px / p["price"] - 1) * 100
        left -= part
        p["칸"] = max(1, round(left * 4))
        if left <= 1e-9:
            break
    if left > 1e-9:
        got += left * (b["c"][-1] / p["price"] - 1) * 100
    return got - H.COST


al_cache = {c: e_align(c, b) for c, b in data.items()}
rows = []
for c, b in data.items():
    base = entry(noon="1045")(c, b)
    for k in np.flatnonzero(base):
        if al_cache[c][k] or HH[c][k] != "1045":
            continue
        t = b["t"][k]
        side = next((n for n, (lo, hi) in PER if lo <= t < hi), None)
        if side is None:
            continue
        r = solo(c, k)
        if r is not None:
            rows.append((side, r, nan0(DR[c])[k], nan0(MKT[c])[k]))
print(f"== 15분봉 18회차: 10:45 사기 신호 하나하나 ({len(data)}종목 · 신호 {len(rows)}) ==", flush=True)
avg = lambda L: (sum(L) / len(L), len(L)) if L else (float("nan"), 0)
for side in ("앞", "뒤"):
    R = [r for r in rows if r[0] == side]
    print(f"  {side}: 모든 10:45 신호 평균 {avg([r[1] for r in R])[0]:+.2f}% ({len(R)}건)")
    up = [r for r in R if r[2] > 0.02]
    keep = [r for r in R if r[2] <= 0.02]
    print(f"    오늘 +2% 위(걸림) {avg([r[1] for r in up])[0]:+.2f}% ({len(up)}) · 남음 {avg([r[1] for r in keep])[0]:+.2f}% ({len(keep)})")
    for x in (0.0, -0.005, -0.01, -0.015):
        hit = [r[1] for r in keep if r[3] < x]
        rest = [r[1] for r in keep if r[3] >= x]
        print(f"    +2% 거른 뒤 시장 {x * 100:g}% 아래(걸림) {avg(hit)[0]:+.2f}% ({len(hit)}) · 남음 {avg(rest)[0]:+.2f}% ({len(rest)})")
import statistics
for side in ("앞", "뒤"):
    R = [r for r in rows if r[0] == side]
    for name, L in (("오늘 +2% 위(걸림)", [r[1] for r in R if r[2] > 0.02]), ("오늘 +2% 이하", [r[1] for r in R if r[2] <= 0.02]),
                    ("시장 −1% 아래(+2% 거른 뒤)", [r[1] for r in R if r[2] <= 0.02 and r[3] < -0.01])):
        L = sorted(L)
        cut = L[:-1] if len(L) > 3 else L
        print(f"  {side} {name}: 가운데값 {statistics.median(L):+.2f}% · 가장 큰 1건 뺀 평균 {sum(cut) / len(cut):+.2f}% · 이긴 비율 {sum(x > 0 for x in L) / len(L) * 100:.0f}% ({len(L)}건)")
print("끝", flush=True)
