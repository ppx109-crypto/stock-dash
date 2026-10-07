"""2차 연구 공통 성적표(docs/PREREG-2.md §2 · §3).
- 비용: 해마다 다른 증권거래세(팔 때만) + 수수료 0.015% × 2 + 슬리피지 0.05% × 2 + 시장 충격 0.10 × √(주문 ÷ 앞 20일 평균 거래대금)(사고 팔 때 각각).
  scale = 1(BASE) · 1.5(STRESS) · 2.0(EXTREME). 계좌 크기(1억 · 10억 · 100억)는 시장 충격에만 들어감.
- 날마다 계좌 수익 → CAGR · 총수익 · 해마다 · 달마다 · 날마다 평가 MDD · Sharpe · Sortino · Calmar · 가장 나쁜 하루 · 달 · Newey-West t.
- 매매 목록 → 승률 · 평균 · 중앙 · 표준편차 · t · 부트스트랩(매매) · **종목 묶음 부트스트랩** · PF · 손익비 · 최대 연속 손실 · 평균 보유 · 판 날 셈 MDD.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(23)
TAX = {2017: .0025, 2018: .0025, 2019: .0025, 2020: .0025, 2021: .0025, 2022: .0025, 2023: .0020, 2024: .0018}
SCALES = {"BASE": 1.0, "STRESS": 1.5, "EXTREME": 2.0}


def tax(day):
    return TAX.get(int(str(day)[:4]), .0015)


@lru_cache(maxsize=None)
def adv_series(code):
    """앞 20일 평균 거래대금(원) — 그날은 빼고 전날까지(volume-data 거래대금은 원 값 그대로)."""
    p = ROOT / "volume-data" / f"{code}.json"
    if not p.exists():
        return pd.Series(dtype=float)
    rows = json.loads(p.read_text(encoding="utf-8")).get("날") or []
    s = pd.Series({str(r[0]): float(r[2]) for r in rows if len(r) > 2 and r[2]}).sort_index()
    return s.rolling(20, min_periods=10).mean().shift(1)


def impact(code, day, notional):
    a = adv_series(code)
    v = a.get(day) if len(a) else None
    if v is None or not np.isfinite(v) or v <= 0:
        v = a[a.index <= day].iloc[-1] if len(a) and (a.index <= day).any() else np.nan
    if not np.isfinite(v) or v <= 0:
        return 0.002
    return 0.10 * np.sqrt(notional / v)


def side_costs(code, buy_day, sell_day, notional, scale=1.0):
    """(살 때 비율, 팔 때 비율) — scale은 수수료 · 슬리피지 · 세금 · 충격 모두에 곱함."""
    b = 0.00015 + 0.0005 + impact(code, buy_day, notional)
    s = 0.00015 + 0.0005 + tax(sell_day) + impact(code, sell_day, notional)
    return b * scale, s * scale


def nw_t(x, lag=5):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 30:
        return np.nan
    m = x.mean()
    e = x - m
    g0 = (e @ e) / n
    s = g0
    for k in range(1, lag + 1):
        gk = (e[k:] @ e[:-k]) / n
        s += 2 * (1 - k / (lag + 1)) * gk
    return m / np.sqrt(s / n) if s > 0 else np.nan


def daily_stats(r, lo="20170101", hi="20991231"):
    x = r[(r.index >= lo) & (r.index < hi)].astype(float)
    if len(x) < 20:
        return {}
    e = (1 + x).cumprod()
    yrs = len(x) / 245
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    mdd = (e / e.cummax() - 1).min()
    sd, dn = x.std(), x[x < 0].std()
    dt = pd.to_datetime(x.index)
    mon = (1 + x).groupby(dt.to_period("M")).prod() - 1
    yr = (1 + x).groupby(dt.year).prod() - 1
    return {"CAGR": cagr, "총수익": e.iloc[-1] - 1, "MDD": mdd, "Sharpe": x.mean() / sd * np.sqrt(245) if sd else np.nan,
            "Sortino": x.mean() / dn * np.sqrt(245) if dn else np.nan, "Calmar": cagr / -mdd if mdd < 0 else np.nan,
            "나쁜날": x.min(), "나쁜달": mon.min(), "좋은달": mon.max(), "플러스달": (mon > 0).mean(), "NW_t": nw_t(x.to_numpy()),
            "해마다": {int(k): float(v) for k, v in yr.items()}, "달마다": {str(k): float(v) for k, v in mon.items()}}


def trade_stats(trades, lo="20170101", hi="20991231", boot=2000):
    """trades: [(code, 산 날, 판 날, 비용 뒤 손익 비율, 몫)]."""
    tt = [t for t in trades if lo <= t[1] < hi]
    if not tt:
        return {}
    g = np.array([t[3] for t in tt])
    codes = np.array([t[0] for t in tt])
    win, loss = g[g > 0], g[g <= 0]
    streak = best = 0
    for x in g:
        streak = streak + 1 if x <= 0 else 0
        best = max(best, streak)
    hold = [np.busday_count(pd.Timestamp(t[1]).date(), pd.Timestamp(t[2]).date()) for t in tt]
    bm = [g[RNG.integers(0, len(g), len(g))].mean() for _ in range(boot)]
    uc = np.unique(codes)
    groups = {c: g[codes == c] for c in uc}
    cb = []
    for _ in range(boot):
        pick = uc[RNG.integers(0, len(uc), len(uc))]
        v = np.concatenate([groups[c] for c in pick])
        cb.append(v.mean())
    se_c = np.std(cb)
    eq = np.cumprod(1 + np.array([t[3] * t[4] for t in sorted(tt, key=lambda t: t[2])]))
    return {"매매": len(g), "종목": len(uc), "승률": float((g > 0).mean()), "평균": float(g.mean()), "중앙": float(np.median(g)),
            "표준편차": float(g.std()), "t": float(g.mean() / g.std() * np.sqrt(len(g))) if g.std() else 0.0,
            "95%": tuple(np.percentile(bm, [2.5, 97.5])), "묶음95%": tuple(np.percentile(cb, [2.5, 97.5])),
            "묶음t": float(g.mean() / se_c) if se_c else np.nan,
            "PF": float(win.sum() / -loss.sum()) if loss.sum() < 0 else np.inf,
            "손익비": float(win.mean() / -loss.mean()) if len(win) and len(loss) and loss.mean() < 0 else np.nan,
            "최대연속손실": best, "평균보유": float(np.mean(hold)), "판날MDD": float((eq / np.maximum.accumulate(eq) - 1).min())}


def fmt_d(s):
    if not s:
        return "(표본 없음)"
    return (f"CAGR {s['CAGR'] * 100:+.1f}% · 총 {s['총수익'] * 100:+.0f}% · MDD(날마다) {s['MDD'] * 100:.1f}% · Sharpe {s['Sharpe']:.2f} · "
            f"Sortino {s['Sortino']:.2f} · Calmar {s['Calmar']:.2f} · 나쁜 날 {s['나쁜날'] * 100:.1f}% · 나쁜 달 {s['나쁜달'] * 100:.1f}% · NW t {s['NW_t']:.1f}")


def fmt_t(s):
    if not s:
        return "(매매 없음)"
    return (f"매매 {s['매매']}({s['종목']}종목) · 승률 {s['승률']:.0%} · 평균 {s['평균'] * 100:+.2f}% · 중앙 {s['중앙'] * 100:+.2f}% · σ {s['표준편차'] * 100:.1f}% · "
            f"t {s['t']:.1f} · 묶음 t {s['묶음t']:.1f}(95% {s['묶음95%'][0] * 100:+.2f} ~ {s['묶음95%'][1] * 100:+.2f}) · PF {s['PF']:.2f} · "
            f"손익비 {s['손익비']:.2f} · 연속 손실 {s['최대연속손실']} · 보유 {s['평균보유']:.1f}일 · 판 날 MDD {s['판날MDD'] * 100:.1f}%")


def years_line(s):
    return " · ".join(f"{y} {v * 100:+.0f}%" for y, v in s.get("해마다", {}).items())
