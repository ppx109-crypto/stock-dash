"""2라운드 ④ — 빈칸 엔진을 '15:15 값으로 판단'해도 '종가로 판단'과 같은 결정인지(etf-m15 · 2025-09 ~ · 약 1년).
15:15에 아는 값 = 15:00 칸(15:00 ~ 15:15) 종가. 견주는 결정:
  ① 돌리기 위 2개(나스닥100 · 달러 · 금 · 국채10년 20일 수익) — 주 마지막 날마다
  ② 하락 추세 달러 단계(원 · 달러 20일 > +2% · 코스피 < 20일선) — 날마다
  ③ 급락 되돌림 신호(코스피 5일 ≤ −5%) · ④ 코스닥 과열(코스닥150 10일 ≥ +10%) — 날마다
같은 결정인 몫, 다를 때 그 결정을 따랐을 때 손익 차이(다음 날 종가까지)."""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

H = Path("/home/user/stock-dash/etf-m15")
D, n = I.DAYS, len(I.DAYS)


def mid(code):
    out = {}
    for f in sorted((H / code).glob("*.csv")):
        for line in f.read_text().splitlines():
            t = line.split(",")
            if t[0][8:] == "1500":
                out[t[0][:8]] = float(t[4])
    return np.array([out.get(d, np.nan) for d in D])


ROT = ("133690", "138230", "132030", "148070")
close = {c: I.px(c) for c in ROT + ("069500", "229200")}
m15 = {c: mid(c) for c in ROT + ("069500", "229200")}
have = np.isfinite(m15["069500"])
idx = [i for i in range(n) if have[i] and i >= 25]
print(f"== 2라운드 ④: 15:15 판단 vs 종가 판단 · {D[idx[0]]} ~ {D[idx[-1]]} ({len(idx)}일) ==", flush=True)
wk = [datetime.strptime(d, "%Y%m%d").isocalendar()[:2] for d in D]
week_end = [i for i in idx if i == n - 1 or wk[i + 1] != wk[i]]


def top2(i, src):
    sc = []
    for c in ROT:
        now = src[c][i]
        r = now / close[c][i - 20] - 1 if np.isfinite(now) and np.isfinite(close[c][i - 20]) else np.nan
        if r == r and r > 0:
            sc.append((r, c))
    return frozenset(c for _, c in sorted(sc, reverse=True)[:2])


same = sum(top2(i, close) == top2(i, m15) for i in week_end)
print(f"  ① 돌리기 위 2개: 주 {len(week_end)}번 중 같음 {same}번({same / len(week_end) * 100:.0f}%)", flush=True)
diffs = [i for i in week_end if top2(i, close) != top2(i, m15)]
for i in diffs:
    a, b = top2(i, close), top2(i, m15)
    print(f"     {D[i]}: 종가 {sorted(a)} / 15:15 {sorted(b)}", flush=True)


def flags(src):
    k = src["069500"]
    k_close = close["069500"]
    m20 = np.array([np.mean(np.r_[k_close[i - 19:i], k[i]]) if i >= 20 else np.nan for i in range(n)])
    dol = src["138230"]
    d20 = np.array([dol[i] / close["138230"][i - 20] - 1 if i >= 20 else np.nan for i in range(n)])
    r5 = np.array([k[i] / k_close[i - 5] - 1 if i >= 5 else np.nan for i in range(n)])
    q10 = np.array([src["229200"][i] / close["229200"][i - 10] - 1 if i >= 10 else np.nan for i in range(n)])
    return {"② 하락 추세 달러": (d20 > 0.02) & (k < m20), "③ 급락 되돌림(5일 −5%)": r5 <= -0.05, "④ 코스닥 과열(10일 +10%)": q10 >= 0.10}


fc, fm = flags(close), flags(m15)
for k in fc:
    a, b = fc[k][idx], fm[k][idx]
    print(f"  {k}: 종가 판단 {int(a.sum())}날 · 15:15 판단 {int(b.sum())}날 · 같은 날 몫 {np.mean(a == b) * 100:.1f}% · 엇갈린 날 {int((a != b).sum())}", flush=True)
print("끝", flush=True)
