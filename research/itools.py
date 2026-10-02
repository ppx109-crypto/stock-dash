"""I 갈래(인버스 · 하락/옆걸음 버티기) 도구 — 상장지수펀드 일봉(etf-data)으로 '들어가는 신호 + 나오는 법'을 매매 단위로 흉내.

자료: etf-data — 114800 KODEX 인버스(2009-09~) · 252670 200선물인버스2X(2016-09~) · 251340 코스닥150 인버스(2016-08~)
      · 069500 KODEX 200(2002~, 지수 대신 신호용) · 229200 코스닥150 · 122630 레버리지.
날짜판 = 069500 거래일. 신호는 그날 종가로 판단 → 그날 종가에 들어감(1일봉 규칙처럼 장 끝 무렵). 나오는 것도 종가.
비용 = 사고팔 때 합(기본 0.2% · ETF는 매도세 없음, 수수료 + 호가 차이 넉넉히). 날마다 평가(골 계산).
기간: 셋(A 2009-09 ~ 2016 · B 2017 ~ 2020 · C 2021 ~). 시장 폭 · 수급 신호는 2017 ~ 만(B · C).
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path("/home/user/stock-dash")
PERIODS = (("A", "20090916", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))


def _closes(code):
    body = json.loads((ROOT / f"etf-data/{code}.json").read_text(encoding="utf-8"))
    return {str(d): float(c) for d, c in body["closes"] if c}


base = _closes("069500")
DAYS = sorted(base)
IX = {d: i for i, d in enumerate(DAYS)}
K200 = np.array([base[d] for d in DAYS])
PX = {}
for code in ("114800", "252670", "251340", "069500", "229200", "122630"):
    got = _closes(code)
    PX[code] = np.array([got.get(d, np.nan) for d in DAYS])


def ma(a, n):
    out = np.full(len(a), np.nan)
    c = np.cumsum(np.insert(a, 0, 0.0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def low_before(a, n):
    """그날 앞 n일(그날 뺌)의 가장 낮은 종가."""
    out = np.full(len(a), np.nan)
    for i in range(n, len(a)):
        out[i] = a[i - n:i].min()
    return out


def high_before(a, n):
    out = np.full(len(a), np.nan)
    for i in range(n, len(a)):
        out[i] = a[i - n:i].max()
    return out


def ret(a, n):
    out = np.full(len(a), np.nan)
    out[n:] = a[n:] / a[:-n] - 1
    return out


def series(path, col):
    """market-data 표 → 날짜판에 맞춘 값(없는 날은 nan)."""
    rows = json.loads((ROOT / path).read_text(encoding="utf-8"))["rows"]
    got = {str(r["date"]): r.get(col) for r in rows}
    return np.array([float(got[d]) if got.get(d) is not None else np.nan for d in DAYS])


def breadth():
    """1일봉 연구의 시장 폭(그날 시총 100위 안 50일선 > 200일선 몫, 2017 ~). nrl을 불러 몇 초 걸림."""
    import sys
    sys.path.insert(0, "/home/user/stock-dash/research")
    sys.path.insert(0, "/home/user/stock-dash")
    import nrl
    return np.array([nrl.BR.get(d, np.nan) for d in DAYS])


def sim(entry, code="114800", stop=-0.05, take=0.08, maxd=10, exit_sig=None, cost=0.002, weight=1.0, cool=0):
    """entry[i] 참이고 들고 있지 않으면 i일 종가에 삼. 손절 · 익절 · 기간(거래일) · 나가는 신호(종가 판단) 가운데 먼저.
    돌려줌: 매매 목록 [(산 날 i, 판 날 j, 손익)], 날마다 계좌 수익률(배열, weight = 계좌에서 넣는 몫)."""
    px = PX[code]
    daily = np.zeros(len(DAYS))
    trades = []
    i = 0
    n = len(DAYS)
    while i < n - 1:
        if not entry[i] or np.isnan(px[i]):
            i += 1
            continue
        p0 = px[i]
        daily[i] -= cost / 2 * weight
        j = i + 1
        while j < n:
            if np.isnan(px[j]):
                j += 1
                continue
            daily[j] += (px[j] / px[j - 1] - 1) * weight if not np.isnan(px[j - 1]) else 0.0
            r = px[j] / p0 - 1
            if r <= stop or r >= take or j - i >= maxd or (exit_sig is not None and exit_sig[j]):
                break
            j += 1
        j = min(j, n - 1)
        daily[j] -= cost / 2 * weight
        trades.append((i, j, px[j] / p0 - 1 - cost))
        # cool: 손절로 나왔으면 그 뒤 cool 거래일은 새로 사지 않음(연달아 손절 막기)
        i = j + 1 + (cool if px[j] / p0 - 1 <= stop else 0)
    return trades, daily


def judge(trades, daily, lo, hi):
    """그 기간의 매매 수 · 이긴 몫 · 평균 · 연 수익 · 골 · 들고 있던 날 몫."""
    idx = [k for k, d in enumerate(DAYS) if lo <= d < hi]
    if not idx:
        return None
    a, b = idx[0], idx[-1]
    eq = np.cumprod(1 + daily[a:b + 1])
    peak = np.maximum.accumulate(eq)
    dd = float((eq / peak - 1).min()) * 100
    yrs = max((b - a + 1) / 250, 0.5)
    cagr = (eq[-1] ** (1 / yrs) - 1) * 100
    tr = [t for t in trades if a <= t[0] <= b]
    held = sum(t[1] - t[0] for t in tr) / max(b - a + 1, 1) * 100
    return {"n": len(tr), "win": (np.mean([t[2] > 0 for t in tr]) * 100) if tr else 0.0,
            "avg": (np.mean([t[2] for t in tr]) * 100) if tr else 0.0, "cagr": cagr, "dd": dd, "held": held}


def line(tag, trades, daily, periods=PERIODS):
    out = [f"  {tag:44s}"]
    worst = None
    for name, lo, hi in periods:
        j = judge(trades, daily, lo, hi)
        if not j:
            continue
        out.append(f"| {name} {j['n']:3d}건 이김 {j['win']:4.1f} 평균 {j['avg']:+5.2f} 연 {j['cagr']:+5.1f} 골 {j['dd']:6.1f} 들고 {j['held']:4.1f}%")
        worst = j["cagr"] if worst is None else min(worst, j["cagr"])
    return " ".join(out), worst
