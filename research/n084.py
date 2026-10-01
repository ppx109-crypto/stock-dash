"""일봉 새 84회차 — 마감 직전 값(15:15쯤, 15분봉 15:00 칸 종가)으로 판단해도 진짜 종가 판단과 같은가.
1일봉 모의투자(daily_live.py)는 15:20 값을 오늘 종가로 보고 판단해 마감 동시호가에 삼. 15분봉 161종목(2025-09-17 ~ 2026-08-31)으로
날마다 '오늘 종가 자리에 15:00 칸 종가를 넣은 판단'과 '진짜 종가 판단'을 견줌.
- 추세 문 세 조건(60일 전 대비 20%↑ · 180일 EMA 닷새 기울기 1.46%↑ · 20일 변동성 ≤ 그날 문턱(a_group calm_edge 2.148 고정)) — 시총 순위 · 수급은 전날 값이라 같음
- 정배열 문(SMA 3 > 15 > 20 > 90 > 150 > 200 · 간격 19 ~ 53%) — 시장 폭은 빼고 봄
"""
import json
import sys
from pathlib import Path
import os
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import final_group as FG

HOME = Path(os.environ.get("M15_HOME", "m15-kis"))
CALM = 2.148


def ema(x, n):
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    a = 2 / (n + 1)
    out[n - 1] = np.mean(x[:n])
    for i in range(n, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def trend_parts(cl):
    i = len(cl) - 1
    sixty = (cl[i] / cl[i - 60] - 1) * 100 >= 20 if i >= 60 else False
    e = ema(cl, 180)
    slope = (e[i] / e[i - 5] - 1) * 100 >= 1.46 if i >= 185 and not np.isnan(e[i - 5]) else False
    mv = np.diff(cl[-21:]) / cl[-21:-1] * 100
    calm = np.std(mv, ddof=1) <= CALM if len(mv) == 20 else False
    return sixty, slope, calm


def align_door(cl):
    got = FG.lines_now(list(cl))
    return bool(got and got["정배열"] and 19 <= got["간격"] < 53)


stats = {"추세 문": [0, 0, 0], "정배열 문": [0, 0, 0], "60일 20%": [0, 0, 0], "기울기": [0, 0, 0], "변동성": [0, 0, 0]}
moves = []
codes = sorted(p.name for p in HOME.iterdir() if p.is_dir())
for c in codes:
    pf = Path(f"price-data/{c}.json")
    if not pf.exists():
        continue
    daily = {d: float(x) for d, x in json.load(open(pf, encoding="utf-8"))["closes"]}
    days = sorted(daily)
    pre = {}
    for f in sorted((HOME / c).glob("*.csv")):
        for line in open(f, encoding="utf-8"):
            p = line.strip().split(",")
            if len(p) >= 5 and p[0][8:12] == "1500":
                pre[p[0][:8]] = float(p[4])
    for d, px in pre.items():
        if d not in daily or d >= "20260901":
            continue
        k = days.index(d)
        if k < 260:
            continue
        real = np.array([daily[x] for x in days[k - 259:k + 1]])
        early = real.copy()
        early[-1] = px
        moves.append(abs(px / real[-1] - 1) * 100)
        a, b = trend_parts(real), trend_parts(early)
        ta, tb = all(a), all(b)
        for name, x, y in (("추세 문", ta, tb), ("정배열 문", align_door(real), align_door(early)),
                           ("60일 20%", a[0], b[0]), ("기울기", a[1], b[1]), ("변동성", a[2], b[2])):
            s = stats[name]
            s[0] += 1
            s[1] += x
            s[2] += x != y
print(f"== 일봉 새 84회차: 15:15 값 판단 vs 종가 판단 ({len(codes)}종목 · 종목·날 {len(moves):,}개) ==")
print(f"  15:00 칸 종가와 진짜 종가 차이: 가운데 {np.median(moves):.2f}% · 90% {np.percentile(moves, 90):.2f}% · 99% {np.percentile(moves, 99):.2f}%")
for name, (n, on, flip) in stats.items():
    print(f"  {name}: 종가로 열린 날 {on:,} · 판단이 달라진 종목·날 {flip:,} ({flip / max(1, n) * 100:.2f}% · 열린 날 대비 {flip / max(1, on) * 100:.1f}%)")
print("끝")
