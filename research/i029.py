"""I 44회차 — 인버스 1시간봉(사용자 2026-10-03 "인버스 1H도 연구"). 야후 지수 1시간봉(hourly-data/KOSPI · KOSDAQ · 2023-09 ~ · 하루 7봉 09 ~ 15시, 15시 봉 = 그날 종가).
인버스 값은 지수로 만듦: 그날 인버스 = 어제 인버스 종가 × (1 − 배수 × (지수 / 어제 지수 종가 − 1)) — 인버스는 하루마다 다시 맞춰져 하루 안에선 거의 정확(추적 오차 · 선물 괴리는 뺌).
판(봉 끝에 판단 → 그 봉 종가에 삼 · 미래 참조 없음):
  H1 장중 하락 이어가기: T시(10 · 11 · 13시 봉 끝) 지수가 어제 종가보다 −X%(0.5 · 1 · 1.5) → 인버스, 그날 종가에 팖
  H2 갭 상승 되돌림: 09시 봉 끝 지수가 어제 종가보다 +X%(0.7 · 1 · 1.5) → 인버스, 그날 종가에 팖
  H3 오후 과열 되돌림: 13시 봉 끝 +X%(1 · 1.5 · 2) → 인버스, 그날 종가에 팖
  H4 어제 저점 깨기: 봉 종가 < 어제 가장 낮은 값 → 인버스, 익절 1.5 · 손절 1 · 최대 7봉(하루) — 다음 날로 넘길 수 있음
  H5 코스닥 과열(코스닥 10일 +10%) 날 장중(10 · 13시 끝) → 코스닥 인버스 1배, 익절 1.5 · 손절 1.5 · 최대 70봉(10일)
배수: 코스피 1배 · 2배(코스닥 인버스는 1배만 있음). 비용 0.2%. 기간 P1 2023-10 ~ 2024 · P2 2025 · P3 2026. 잣대: 셋 다 연 + · 골 −15 안."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

H = Path("/home/user/stock-dash/hourly-data")


def load(name):
    """야후 60분봉엔 15:00 ~ 15:30(종가) 봉이 대개 없음 → 지수 일봉(market-data · 2017 ~ 09-29)의 종가 · 저가를 15시 봉으로 붙임.
    일봉이 없는 날(09-30 ~)은 15시 봉이 있으면 그것을 씀."""
    import json
    bars = {}
    for f in sorted((H / name).glob("*.csv")):
        for line in f.read_text().splitlines():
            t, o, h, l, c = line.split(",")[:5]
            bars.setdefault(t[:8], {})[int(t[8:])] = (float(h), float(l), float(c))
    daily = {r["date"]: r for r in json.loads(Path(f"/home/user/stock-dash/market-data/index_{name}.json").read_text(encoding="utf-8"))["rows"]}
    for d, b in bars.items():
        if d in daily and daily[d].get("종가"):
            r = daily[d]
            b[15] = (float(r["고가"]), float(r["저가"]), float(r["종가"]))
    days = sorted(d for d, b in bars.items() if 15 in b and len(b) >= 6)
    return days, bars


PER = (("P1 23-10~24", "20231001", "20250101"), ("P2 2025", "20250101", "20260101"), ("P3 2026", "20260101", "20991231"))


def series(name, lev):
    """봉 줄: [(날, 시, 지수 종가, 지수 저가, 인버스 값)] · 인버스는 날마다 다시 맞춤(lev 배)."""
    days, bars = load(name)
    out, inv, prev = [], 100.0, None
    for d in days:
        if prev is None:
            prev = bars[d][15][2]
            continue
        for hr in sorted(bars[d]):
            h, l, c = bars[d][hr]
            out.append((d, hr, c, l, inv * (1 - lev * (c / prev - 1)), prev))
        inv = inv * (1 - lev * (bars[d][15][2] / prev - 1))
        prev = bars[d][15][2]
    return out


def run(rows, entry, take=None, stop=None, max_bars=None, eod=True, cost=0.002):
    """entry(i) → 참이면 i봉 종가에 삼. eod: 그날 15시 봉에 팖. 아니면 익절 · 손절 · 최대 봉."""
    n = len(rows)
    val = np.array([r[4] for r in rows])
    daily = {}
    trades, i = [], 0
    while i < n - 1:
        if not entry(i):
            i += 1
            continue
        p0, j = val[i], i + 1
        while j < n:
            rr = val[j] / p0 - 1
            if eod and rows[j][1] == 15:
                break
            if not eod and ((take and rr >= take) or (stop and rr <= stop) or (max_bars and j - i >= max_bars)):
                break
            j += 1
        j = min(j, n - 1)
        trades.append((rows[i][0], rows[j][0], val[j] / p0 - 1 - cost))
        daily[rows[j][0]] = daily.get(rows[j][0], 0) + trades[-1][2]
        i = j + 1
    return trades, daily


def judge(trades, daily, lo, hi):
    ds = sorted(d for d in daily if lo <= d < hi)
    t = [x for x in trades if lo <= x[0] < hi]
    eq = np.cumprod([1 + daily[d] for d in ds]) if ds else np.array([1.0])
    dd = float((eq / np.maximum.accumulate(eq) - 1).min()) * 100
    days = [d for d in I.DAYS if lo <= d < hi and d >= "20230926"]
    yrs = max(len(days) / 250, 0.25)
    return len(t), (np.mean([x[2] > 0 for x in t]) * 100 if t else 0), (eq[-1] ** (1 / yrs) - 1) * 100, dd


def show(tag, trades, daily, out):
    js = [judge(trades, daily, lo, hi) for _, lo, hi in PER]
    ok = all(j[2] > 0 and j[3] > -15 for j in js) and all(j[0] >= 3 for j in js)
    out.append((ok, min(j[2] for j in js), tag + " | " + " | ".join(f"{nm} {j[0]}건 이김 {j[1]:.0f} 연 {j[2]:+.1f} 골 {j[3]:.1f}" for (nm, _, _), j in zip(PER, js))))


print("== I 44회차: 인버스 1시간봉(지수로 만든 인버스 값) ==", flush=True)
q_daily = I.px("229200")
q10 = {d: (q_daily[i] / q_daily[i - 10] - 1) for i, d in enumerate(I.DAYS) if i >= 10 and not np.isnan(q_daily[i]) and not np.isnan(q_daily[i - 10])}
for name, levs in (("KOSPI", (1, 2)), ("KOSDAQ", (1,))):
    for lev in levs:
        rows = series(name, lev)
        chg = lambda i: rows[i][2] / rows[i][5] - 1
        prev_low = {}
        lows = {}
        for d, hr, c, l, v, p in rows:
            lows[d] = min(lows.get(d, 1e18), l)
        dlist = sorted(lows)
        for a, b in zip(dlist, dlist[1:]):
            prev_low[b] = lows[a]
        out = []
        for T in (10, 11, 13):
            for X in (0.005, 0.01, 0.015):
                show(f"H1 {T}시 −{X*100:.1f}% → 종가", *run(rows, lambda i, T=T, X=X: rows[i][1] == T and chg(i) <= -X), out)
        for X in (0.007, 0.01, 0.015):
            show(f"H2 09시 갭 +{X*100:.1f}% → 종가", *run(rows, lambda i, X=X: rows[i][1] == 9 and chg(i) >= X), out)
        for X in (0.01, 0.015, 0.02):
            show(f"H3 13시 +{X*100:.1f}% → 종가", *run(rows, lambda i, X=X: rows[i][1] == 13 and chg(i) >= X), out)
        for tk, st in ((0.015, -0.01), (0.02, -0.01), (0.03, -0.015)):
            show(f"H4 어제 저점 깨기 · 익절 {tk*100:.1f} 손절 {st*100:.1f}",
                 *run(rows, lambda i: rows[i][1] < 15 and rows[i][2] < prev_low.get(rows[i][0], -1), take=tk * lev, stop=st * lev, max_bars=7, eod=False), out)
        if name == "KOSDAQ":
            for T in (10, 13):
                show(f"H5 코스닥 과열 날 {T}시 → 익절 1.5 손절 1.5 10일",
                     *run(rows, lambda i, T=T: rows[i][1] == T and q10.get(rows[i][0], 0) >= 0.10 * 0.95, take=0.015, stop=-0.015, max_bars=70, eod=False), out)
        out.sort(key=lambda x: (x[0], x[1]), reverse=True)
        print(f"\n[{name} 인버스 {lev}배] 합격 {sum(x[0] for x in out)}/{len(out)}", flush=True)
        for ok, w, t in out[:6]:
            print(f"  {'합격' if ok else '    '} (가장 나쁜 {w:+5.1f}) {t}", flush=True)
print("끝", flush=True)
