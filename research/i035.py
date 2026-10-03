"""I 52회차 — 1시간봉 인버스를 '실제 ETF 15분봉 · 실제 호가 비용'으로 다시(i029 · i030은 지수로 만든 값 · 비용 고정).
자료: etf-m15(한투 1분봉 → 15분봉 · 2025-09 ~ · 약 1년) — 069500(판단용) · 114800(1배) · 252670(2배, 받는 중).
판: T시(10 · 11 · 12시)에 KODEX 200이 어제 종가보다 −X%(1.0 · 1.25 · 1.5 · 2.0)면 그 15분 칸 종가에 인버스 사서 그날 종가(15:15 칸 종가 = 마감)에 팖.
비용: 사고팔기 = 그때 값의 호가 1칸(2,000원 아래 1원 · 위 5원) + 수수료 0.03%. 견줌: 비용 0.2% 고정."""
import os
import sys
from pathlib import Path

import numpy as np

H = Path("/home/user/stock-dash/etf-m15")


def bars(code):
    out = {}
    for f in sorted((H / code).glob("*.csv")):
        for line in f.read_text().splitlines():
            t, o, h, l, c, v = line.split(",")[:6]
            out.setdefault(t[:8], {})[t[8:]] = float(c)
    return out


k = bars("069500")
days = sorted(d for d in k if "1515" in k[d])
SLOT = {10: "0945", 11: "1045", 12: "1145"}           # 그 칸 종가 = 10:00 · 11:00 · 12:00에 아는 값
for code in [c for c in ("114800", "252670") if (H / c).exists()]:
    e = bars(code)
    dd = [d for d in days if d in e and "1515" in e[d]]
    print(f"\n== {code} 실제 15분봉 · {dd[0]} ~ {dd[-1]} ({len(dd)}일) ==", flush=True)
    for T, slot in SLOT.items():
        cells = []
        for X in (0.01, 0.0125, 0.015, 0.02):
            res = {}
            for mode in ("고정 0.2%", "실제 호가"):
                rets = []
                for a, b in zip(days, days[1:]):
                    if b not in e or slot not in k[b] or slot not in e[b] or "1515" not in e[b]:
                        continue
                    if k[b][slot] / k[a]["1515"] - 1 > -X:
                        continue
                    p0, p1 = e[b][slot], e[b]["1515"]
                    tick = 1.0 if p0 < 2000 else 5.0
                    cost = 0.002 if mode == "고정 0.2%" else tick / p0 + 0.0003
                    rets.append(p1 / p0 - 1 - cost)
                rets = np.array(rets)
                res[mode] = (len(rets), (np.prod(1 + rets) - 1) * 100 if len(rets) else 0.0, np.mean(rets > 0) * 100 if len(rets) else 0)
            cells.append(f"−{X*100:.2f}%: {res['실제 호가'][0]}건 합 {res['고정 0.2%'][1]:+5.1f} → 실제 {res['실제 호가'][1]:+5.1f}% (이김 {res['실제 호가'][2]:.0f})")
        print(f"  {T}시 | " + " | ".join(cells), flush=True)
print("끝", flush=True)
