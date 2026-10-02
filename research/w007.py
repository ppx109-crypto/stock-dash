"""W 7회차(W9) — 쉬는 현금의 이자. 1일봉 규칙(새 82)이 칸을 비워 둔 몫에 연 r%(CMA · 예탁금 이용료 · 단기채 상장지수펀드 흉내)를 붙이면 얼마나 더해지나.
날마다 든 몫 = 그날 들고 있는 매매의 칸 ÷ 10. 쉬는 몫 × r/250을 날마다 더함(복리)."""
import json
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl
import wtools as W

days = [r["date"] for r in json.load(open("/home/user/stock-dash/market-data/index_KOSPI.json", encoding="utf-8"))["rows"]]
led = W.base_ledger()
held = {d: 0.0 for d in days}
gain = {}
for code, b, s, g, k in led:
    for d in days:
        if b <= d < s:
            held[d] += k / 10
    gain[s] = gain.get(s, 0) + k / 10 * g
MID = nrl.rule.MID
for side, lo, hi in (("앞", "20170101", MID), ("뒤", MID, "20991231")):
    ds = [d for d in days if lo <= d < hi]
    idle = sum(max(0.0, 1 - held[d]) for d in ds) / len(ds)
    yrs = len(ds) / 250
    line = [f"  {side}: 쉬는 몫 평균 {idle * 100:4.1f}%"]
    for r in (0.0, 2.0, 3.0):
        eq, peak, dip = 1.0, 1.0, 0.0
        for d in ds:
            eq *= 1 + gain.get(d, 0) / 100 + max(0.0, 1 - held[d]) * r / 100 / 250
            peak = max(peak, eq)
            dip = min(dip, eq / peak - 1)
        line.append(f"| 이자 연 {r}%: 연 {(eq ** (1 / yrs) - 1) * 100:5.1f} 골 {dip * 100:5.1f}")
    print(" ".join(line), flush=True)
