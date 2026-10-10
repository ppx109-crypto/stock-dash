"""BACKTEST-REPAIR-0001 공통 장부(K5 현금 · 수량 보존 · K6 실제 가격 · K7 매 체결 비용 · K9 일별 MTM)와 성적표.
표준 라이브러리 + numpy만. 네트워크 · 파일 쓰기 없음(쓰기는 run_all.py)."""
import math
from datetime import date

import numpy as np

FEE, SLIP = 0.00015, 0.0005
PERIODS = (("Train 2017-02~2020-12", "20170201", "20201231"), ("Validation 2021~2022", "20210101", "20221231"),
           ("다시 본 2023-01~2026-09", "20230101", "20260930"), ("전체", "00000000", "99999999"))


class Costs:
    """편도 비용률. kind='stock'이면 충격 · 세금, 'etf'면 수수료 + 미끄러짐만. mult = 1(기본) · 2(스트레스) · 0(비용 전)."""

    def __init__(self, cc, market_of, mult=1.0, kind="stock"):
        self.cc, self.market_of, self.mult, self.kind = cc, market_of, mult, kind
        self.tax_unknown = 0

    def buy(self, code, day, notional):
        r = FEE + SLIP + (self.cc.impact(code, day, notional) if self.kind == "stock" else 0.0)
        return r * self.mult

    def sell(self, code, day, notional):
        r = FEE + SLIP
        if self.kind == "stock":
            r += self.cc.impact(code, day, notional)
            try:
                r += self.cc.sell_tax_rate(day, "STOCK", self.market_of(code), "S_KOSPI_FARM015")
            except self.cc.UnknownTax:
                self.tax_unknown += 1
                r += 0.0023           # 계약 밖 날짜(기록함) — 2021~22 값으로 둠
        return r * self.mult


class Account:
    def __init__(self, cash=1e8):
        self.cash = float(cash)
        self.lots = {}            # id → {code, qty, price, buy_cost, day, tag}
        self.trades = []
        self.notes = {"buy_skipped_no_price": 0, "buy_skipped_cash": 0, "buy_reduced_cash": 0, "sell_no_price_used_last": 0,
                      "stale_mtm_days": 0}

    def held(self, code):
        return sum(l["qty"] for l in self.lots.values() if l["code"] == code)

    def buy(self, lid, code, price, value, day, costs, tag=""):
        if not price or price <= 0:
            self.notes["buy_skipped_no_price"] += 1
            return 0
        rate = costs.buy(code, day, value)
        want = math.floor(value / price)
        can = math.floor(self.cash / (price * (1 + rate)))
        qty = min(want, can)
        if qty < 1:
            self.notes["buy_skipped_cash" if want >= 1 else "buy_skipped_no_price"] += 1
            return 0
        if qty < want:
            self.notes["buy_reduced_cash"] += 1
        notional = qty * price
        cost = notional * rate
        self.cash -= notional + cost
        assert self.cash >= -1e-6, "현금 음수"
        self.lots[lid] = {"code": code, "qty": qty, "price": price, "buy_cost": cost, "day": day, "tag": tag}
        return qty

    def sell(self, lid, price, day, costs, qty=None, reason=""):
        l = self.lots.get(lid)
        if l is None:
            return None
        q = l["qty"] if qty is None else min(qty, l["qty"])
        notional = q * price
        cost = notional * costs.sell(l["code"], day, notional)
        self.cash += notional - cost
        bc = l["buy_cost"] * q / l["qty"]
        gross = (price - l["price"]) * q
        net = gross - bc - cost
        self.trades.append({"code": l["code"], "tag": l["tag"], "entry": l["day"], "exit": day, "qty": q, "buy_price": l["price"],
                            "sell_price": price, "buy_cost": round(bc, 2), "sell_cost": round(cost, 2), "pnl_gross": round(gross, 2),
                            "pnl_net": round(net, 2), "ret_net": net / (q * l["price"] + bc), "reason": reason})
        l["qty"] -= q
        l["buy_cost"] -= bc
        if l["qty"] <= 0:
            del self.lots[lid]
        return net

    def mtm(self, price_of):
        inv = 0.0
        for l in self.lots.values():
            p, stale = price_of(l["code"])
            if stale:
                self.notes["stale_mtm_days"] += 1
            inv += l["qty"] * p
        return self.cash + inv, inv


def tdays(a, b, days_idx):
    return days_idx.get(b, 0) - days_idx.get(a, 0)


def _ci(x, reps=2000, seed=23):
    x = np.asarray(x, float)
    if len(x) < 2:
        return None
    rng = np.random.default_rng(seed)
    m = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(reps)]
    return [round(float(np.percentile(m, 2.5)) * 100, 3), round(float(np.percentile(m, 97.5)) * 100, 3)]


def report(nav_rows, trades, days_idx, gross_nav=None):
    """nav_rows: [(day, nav, invested)] · trades: Account.trades. 기간별 성적표."""
    out = {}
    d = [r[0] for r in nav_rows]
    nav = np.array([r[1] for r in nav_rows], float)
    inv = np.array([r[2] for r in nav_rows], float)
    gmap = dict((r[0], r[1]) for r in gross_nav) if gross_nav else None
    for name, lo, hi in PERIODS:
        idx = [i for i, x in enumerate(d) if lo <= x <= hi]
        if len(idx) < 20:
            out[name] = None
            continue
        i0, i1 = idx[0], idx[-1]
        base = nav[i0 - 1] if i0 > 0 else nav[i0]
        seg = np.concatenate([[base], nav[i0:i1 + 1]])
        r = seg[1:] / seg[:-1] - 1
        yrs = (date(int(d[i1][:4]), int(d[i1][4:6]), int(d[i1][6:])) - date(int(d[i0][:4]), int(d[i0][4:6]), int(d[i0][6:]))).days / 365.25
        cagr = (seg[-1] / seg[0]) ** (1 / yrs) - 1 if yrs > 0 and seg[-1] > 0 else None
        peak = np.maximum.accumulate(seg)
        mdd = float((seg / peak - 1).min())
        sd, dn = r.std(ddof=1), r[r < 0].std(ddof=1) if (r < 0).sum() > 1 else float("nan")
        months = {}
        for x, rr in zip(d[i0:i1 + 1], r):
            months[x[:6]] = months.get(x[:6], 1.0) * (1 + rr)
        mon = {k: round(float(v) - 1, 5) for k, v in months.items()}
        tt = [t for t in trades if lo <= t["exit"] <= hi]
        pos = sum(t["pnl_net"] for t in tt if t["pnl_net"] > 0)
        neg = -sum(t["pnl_net"] for t in tt if t["pnl_net"] <= 0)
        g = None
        if gmap:
            gs = np.array([gmap.get(x, np.nan) for x in d[i0:i1 + 1]], float)
            gb = gmap.get(d[i0 - 1]) if i0 > 0 else gs[0]
            if np.isfinite(gs).all() and gb:
                g = (gs[-1] / gb) ** (1 / yrs) - 1 if yrs > 0 else None
        out[name] = {
            "from": d[i0], "to": d[i1], "days": len(idx), "codes": len({t["code"] for t in tt}), "trades": len(tt),
            "CAGR": round(float(cagr) * 100, 2) if cagr is not None else None,
            "CAGR_gross": round(float(g) * 100, 2) if g is not None else None,
            "MDD_daily": round(mdd * 100, 2), "Sharpe": round(float(r.mean() / sd * math.sqrt(252)), 2) if sd > 0 else None,
            "Sortino": round(float(r.mean() / dn * math.sqrt(252)), 2) if dn == dn and dn > 0 else None,
            "worst_day": round(float(r.min()) * 100, 2), "worst_month": round(min(mon.values()) * 100, 2) if mon else None,
            "worst_month_at": min(mon, key=mon.get) if mon else None,
            "day_breach_-15": int((r < -0.15).sum()), "month_breach_-15": int(sum(1 for v in mon.values() if v < -0.15)),
            "PF": round(pos / neg, 3) if neg > 0 else None, "win_rate": round(sum(t["pnl_net"] > 0 for t in tt) / len(tt) * 100, 1) if tt else None,
            "avg_ret_net_pct": round(float(np.mean([t["ret_net"] for t in tt])) * 100, 3) if tt else None,
            "ci95_avg_ret_net_pct": _ci([t["ret_net"] for t in tt]) if tt else None,
            "avg_hold_tdays": round(float(np.mean([tdays(t["entry"], t["exit"], days_idx) for t in tt])), 1) if tt else None,
            "cost_total_pct_of_start": round(float(sum(t["buy_cost"] + t["sell_cost"] for t in tt) / seg[0]) * 100, 2) if tt else 0.0,
            "utilization_avg_pct": round(float(np.mean(inv[i0:i1 + 1] / nav[i0:i1 + 1])) * 100, 1),
            "monthly": mon,
        }
    return out
