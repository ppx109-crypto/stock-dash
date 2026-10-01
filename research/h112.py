"""1시간봉 112회차(T4 · 세 갈래 성적표 ①) — 같은 후보 신호를 '그날 종가에 사기(1일봉 방식)' vs '다음 날 1시간봉 신호에 사기(1시간봉 방식)'.
후보 = 다음 날 1시간봉에 붙은 일봉 재료(날 = D)로 문이 열린 (종목, D). 둘 다 같은 1시간봉 파는 규칙으로 혼자 산 손익(비용 0.30%).
1일봉 방식 = D의 마지막 1시간봉 종가에 삼 · 1시간봉 방식 = D+1의 첫 신호(정배열 된 봉 다음 시가, 없으면 12:00). 해마다.
Q_SRC=yahoo(2023-10 ~ 2026-09) · kis(한투 1년)."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = os.environ.get("Q_SRC", "yahoo")
if src == "kis":
    os.environ["Q_BARS"] = "1h"
    exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
    SIG, EXF = SIGS, exit_rule
    okf = ok
else:
    exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
    SIG = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
    EXF = EX
    okf = ok


def solo_from(c, i, price):
    """봉 i 시점에 price로 산 것으로 보고, i 봉부터 파는 판단(닫힌 봉 → 다음 봉 시가)."""
    b = data[c]
    p = {"price": price, "i": i, "칸": 4, "처음칸": 4, "peak": price, "now": i, "code": c}
    left, got = 1.0, 0.0
    for j in range(i, len(b["t"]) - 1):
        p["peak"] = max(p["peak"], b["c"][j]); p["now"] = j
        n = EXF(c, b, p, j)
        if not n:
            continue
        part = left if n == "all" else min(left, n / 4)
        got += part * (b["o"][j + 1] / price - 1) * 100
        left -= part; p["칸"] = max(1, round(left * 4))
        if left <= 1e-9:
            break
    if left > 1e-9:
        got += left * (b["c"][-1] / price - 1) * 100
    return got - H.COST


lo, hi = ("2023100100", "2026093000") if src == "yahoo" else ("202509170000", "202609010000")
rows = []
for c, b in data.items():
    if c.startswith("K"):
        continue
    t = b["t"]
    days = [s[:8] for s in t]
    first_of = {}
    for k, d in enumerate(days):
        first_of.setdefault(d, k)
    for d1, k0 in first_of.items():
        if not (lo <= t[k0] < hi) or k0 == 0:
            continue
        x = ATT[c][k0]
        if not (x and okf(x) and IN[c][k0]):
            continue
        kl = k0 - 1                                   # 전 거래일 마지막 봉(그날 종가)
        daily = solo_from(c, kl + 1, b["c"][kl])      # 종가에 사고 다음 날 첫 봉부터 판단
        ks = [k for k in range(k0, len(t)) if days[k] == d1 and SIG[c][k]]
        hourly = solo_from(c, ks[0] + 1, b["o"][ks[0] + 1]) if ks and ks[0] + 1 < len(t) else None
        rows.append((d1[:4], daily, hourly))
print(f"== 1시간봉 112회차(T4): 같은 후보, 종가 사기 vs 1시간봉 신호 사기 ({src} · 후보 {len(rows)}건) ==", flush=True)
for y in sorted({r[0] for r in rows}) + ["모두"]:
    R = [r for r in rows if (y == "모두" or r[0] == y) and r[2] is not None]
    if not R:
        continue
    a, z = [r[1] for r in R], [r[2] for r in R]
    print(f"  {y}: 종가 사기 평균 {statistics.mean(a):+.2f}(가운데 {statistics.median(a):+.2f} · {sum(v > 0 for v in a) / len(a) * 100:.0f}%) · "
          f"1시간봉 사기 평균 {statistics.mean(z):+.2f}(가운데 {statistics.median(z):+.2f} · {sum(v > 0 for v in z) / len(z) * 100:.0f}%) · "
          f"1시간봉이 나은 몫 {sum(q > p for p, q in zip(a, z)) / len(R) * 100:.0f}% ({len(R)}건)", flush=True)
print("끝", flush=True)
