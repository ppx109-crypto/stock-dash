"""1시간봉 113회차(T4 · 세 갈래 성적표 ②) — 같은 후보 · 같은 산 값(그날 종가)에서 '파는 판단 단위'만 다르게:
A) 1시간봉마다(1시간봉 규칙 EX: 추세 +5% 절반 · +13 · −5% · 60봉 / 정배열 −10% · +8 → +1% · 일봉 정배열 깨짐 → 다음 봉 시가)
B) 하루 한 번 종가로(1일봉 규칙과 같은 숫자: 추세 +5% 절반 · +13 · −5% · 10거래일 / 정배열 −10% · +8 → +1% · 정배열 깨짐 → 그날 종가)
신호 하나하나 손익(비용 0.30%) · 해마다. Q_SRC=yahoo · kis."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/h112.py", encoding="utf-8").read().split("lo, hi = ")[0])


def daily_exit(c, i0, price, kind):
    """i0 = 산 다음 날 첫 봉. 날마다 마지막 봉 종가로 판단 · 그 종가에 팖."""
    b = data[c]
    t = b["t"]
    left, got, peak, days, first_half = 1.0, 0.0, price, 0, False
    k = i0
    while k < len(t):
        d = t[k][:8]
        j = k
        while j + 1 < len(t) and t[j + 1][:8] == d:
            j += 1
        close = b["c"][j]
        days += 1
        peak = max(peak, close)
        g = (close / price - 1) * 100
        sell = 0.0
        if kind == "추세":
            if g >= 13 or g <= -5 or days >= 10:
                sell = left
            elif g >= 5 and not first_half:
                sell, first_half = left / 2, True
        else:
            nx = ATT[c][j + 1] if j + 1 < len(t) else None
            if g <= -10 or ((peak / price - 1) * 100 >= 8 and g <= 1) or (nx is not None and not nx["정배열"]):
                sell = left
        if sell:
            got += sell * g
            left -= sell
            if left <= 1e-9:
                return got - H.COST
        k = j + 1
    return got + left * (b["c"][-1] / price - 1) * 100 - H.COST


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
        if not (x and okf(x) and IN[c][k0]):
            continue
        kind = door(x) or "정배열"
        price = b["c"][k0 - 1]
        rows.append((d1[:4], kind, solo_from(c, k0, price), daily_exit(c, k0, price, kind)))
print(f"== 1시간봉 113회차(T4 ②): 파는 판단 1시간봉마다 vs 하루 한 번 ({src} · 후보 {len(rows)}건) ==", flush=True)
for kind in ("추세", "정배열", "모두"):
    for y in sorted({r[0] for r in rows}) + ["모두"]:
        R = [r for r in rows if (y == "모두" or r[0] == y) and (kind == "모두" or r[1] == kind)]
        if len(R) < 5:
            continue
        a, z = [r[2] for r in R], [r[3] for r in R]
        print(f"  {kind} {y}: 1시간봉마다 {statistics.mean(a):+.2f}(가운데 {statistics.median(a):+.2f}) · 하루 한 번 {statistics.mean(z):+.2f}(가운데 {statistics.median(z):+.2f}) · 하루 한 번이 나은 몫 {sum(q > p for p, q in zip(a, z)) / len(R) * 100:.0f}% ({len(R)}건)", flush=True)
print("끝", flush=True)
