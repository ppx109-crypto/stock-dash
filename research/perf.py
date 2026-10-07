"""공통 성적표(사용자 2026-10-07 퀀트 연구 요청): 매매 목록 · 날마다 계좌 수익률 → 요청한 지표 한 번에.
- 매매 목록: [(코드, 산 날, 판 날, 손익%(비용 전), 몫(계좌 대비 0 ~ 1))]
- 비용: 왕복 cost(기본 0.5% = 수수료 0.03 + 거래세 0.18 ~ 0.20 + 슬리피지 · 넉넉히) — stress로 ×1.5 · 슬리피지 2배 등.
- 계좌: 매매를 '산 날 몫만큼 사서 판 날 정산'하는 단순 계좌(판 날 셈) + 그날 코스피 · 코스닥과 견줌.
지표: CAGR · MDD · Sharpe · Sortino(연 245일) · PF · 승률 · 평균 손익비 · 평균 보유일 · 해마다 거래 수 · 월별 수익 ·
      최대 연속 손실 · 비용 전후 · 코스피 · 코스닥 대비 초과(연) · 국면별(상승장 · 하락장 · 횡보장) · 매매당 평균 t · 부트스트랩 95%."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(11)


def index_series(name="KOSPI"):
    rows = json.loads((ROOT / f"market-data/index_{name}.json").read_text(encoding="utf-8"))["rows"]
    return pd.Series({str(r["date"]): float(r["종가"]) for r in rows if r.get("종가")}).sort_index()


def regime(k):
    """그날 종가까지: 상승장 = 코스피 ≥ 200일선 · 60일선도 위 / 하락장 = 200일선 아래 · 60일선도 아래 / 그 밖 = 횡보장."""
    m60, m200 = k.rolling(60).mean(), k.rolling(200).mean()
    out = pd.Series("횡보장", index=k.index)
    out[(k >= m200) & (k >= m60)] = "상승장"
    out[(k < m200) & (k < m60)] = "하락장"
    return out


def trade_stats(trades, cost=0.005):
    g = np.array([t[3] / 100 - cost for t in trades])
    if len(g) == 0:
        return {}
    win, loss = g[g > 0], g[g <= 0]
    streak = best = 0
    for x in g:
        streak = streak + 1 if x <= 0 else 0
        best = max(best, streak)
    hold = [np.busday_count(pd.Timestamp(t[1]).date(), pd.Timestamp(t[2]).date()) for t in trades]
    bm = [g[RNG.integers(0, len(g), len(g))].mean() for _ in range(2000)]
    return {"매매": len(g), "승률": float((g > 0).mean()), "평균": float(g.mean()), "중앙": float(np.median(g)),
            "표준편차": float(g.std()), "t": float(g.mean() / g.std() * np.sqrt(len(g))) if g.std() else 0.0,
            "95%": tuple(np.percentile(bm, [2.5, 97.5])), "손익비": float(win.mean() / -loss.mean()) if len(win) and len(loss) and loss.mean() < 0 else np.nan,
            "PF": float(win.sum() / -loss.sum()) if loss.sum() < 0 else np.inf, "최대연속손실": best, "평균보유일": float(np.mean(hold))}


def account(trades, days, cost=0.005):
    """판 날에 '몫 × (손익 − 비용)'을 계좌에 더하는 단순 계좌(판 날 셈) → 날마다 수익률."""
    r = pd.Series(0.0, index=days)
    for c, b, e, p, w in trades:
        if e in r.index:
            r[e] += w * (p / 100 - cost)
    return r


def account_stats(r, lo="20170101", hi="20991231", label=""):
    x = r[(r.index >= lo) & (r.index < hi)]
    if len(x) < 20:
        return {}
    e = (1 + x).cumprod()
    yrs = len(x) / 245
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    mdd = (e / e.cummax() - 1).min()
    sd, dn = x.std(), x[x < 0].std()
    mon = (1 + x).groupby(pd.to_datetime(x.index).to_period("M")).prod() - 1
    out = {"CAGR": cagr, "MDD": mdd, "Sharpe": x.mean() / sd * np.sqrt(245) if sd else np.nan,
           "Sortino": x.mean() / dn * np.sqrt(245) if dn else np.nan, "나쁜달": mon.min(), "플러스달": (mon > 0).mean()}
    for nm in ("KOSPI", "KOSDAQ"):
        k = index_series(nm).reindex(x.index).ffill()
        kc = (k.iloc[-1] / k.iloc[0]) ** (1 / yrs) - 1
        out[f"{nm}초과"] = cagr - kc
    reg = regime(index_series("KOSPI")).reindex(x.index).ffill()
    for g in ("상승장", "횡보장", "하락장"):
        xs = x[reg == g]
        out[g] = xs.mean() * 245 if len(xs) else np.nan
    return out


def fmt(s):
    if not s:
        return "(표본 없음)"
    if "CAGR" in s:
        return (f"CAGR {s['CAGR'] * 100:+.1f}% · MDD {s['MDD'] * 100:.1f}% · Sharpe {s['Sharpe']:.2f} · Sortino {s['Sortino']:.2f} · 나쁜 달 {s['나쁜달'] * 100:.1f}% · "
                f"플러스 달 {s['플러스달']:.0%} · 코스피 초과 {s['KOSPI초과'] * 100:+.1f}%p · 코스닥 초과 {s['KOSDAQ초과'] * 100:+.1f}%p · "
                f"국면(연율) 상승 {s['상승장'] * 100:+.0f} / 횡보 {s['횡보장'] * 100:+.0f} / 하락 {s['하락장'] * 100:+.0f}%")
    return (f"매매 {s['매매']} · 승률 {s['승률']:.0%} · 평균 {s['평균'] * 100:+.2f}%(t {s['t']:.1f} · 95% {s['95%'][0] * 100:+.2f} ~ {s['95%'][1] * 100:+.2f}) · "
            f"중앙 {s['중앙'] * 100:+.2f}% · PF {s['PF']:.2f} · 손익비 {s['손익비']:.2f} · 최대 연속 손실 {s['최대연속손실']} · 평균 보유 {s['평균보유일']:.1f}일")
