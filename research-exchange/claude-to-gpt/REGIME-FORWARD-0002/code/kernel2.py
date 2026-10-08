"""BACKTEST-REPAIR-0002 공통 장부와 성적표(표준 라이브러리 + numpy). 네트워크 · 파일 쓰기 없음.

장부 원칙(PREREG §2 · §3 · §4):
- 정수 주 · 한 진입 = 한 포지션(pid) = 한 번 매수. 나눠 팔기는 기존 수량에서 팜(미래 분할이 매수 수량 · 비용에 안 들어감).
- 현금이 모자라면 '실제 체결 금액'으로 충격 비용을 다시 셈해 비용 포함 금액이 현금 안에 드는 가장 큰 수량을 찾음.
- 못 산 요청 · 줄여 산 요청 · 다시 미룬 매도는 모두 기록(임의 취소 · 유령 포지션 없음).
- 날마다: 현금 = 처음 현금 − Σ매수금액 − Σ매수비용 + Σ매도금액 − Σ매도비용, NAV − 처음 현금 = 실현 순손익 + 평가 손익(산 비용 포함 원가 대비).
"""
import bisect
import math
from collections import defaultdict
from datetime import date

import numpy as np

FEE, SLIP, IMPACT_K = 0.00015, 0.0005, 0.10
ADV_MISSING_IMPACT = 0.002      # cost_contract.impact가 ADV 없을 때 쓰는 값(계약 그대로 · 건수 공개)
TAX_ASSUMED = 0.0023            # 세금 계약 밖 날짜에 둔 가정(건수 공개)
START_CASH = 1e8
PERIODS = (("Train 2017-02~2020-12", "20170201", "20201231"), ("Validation 2021~2022", "20210101", "20221231"),
           ("다시 본 2023-01~2026-09", "20230101", "20260930"), ("전체", "00000000", "99999999"))
BLOCK, REPS, SEED = 20, 2000, 23
MIN_DAYS_BLOCK = 250
LOSS_EDGE, EPS = -0.15, 1e-12    # 사용자 기준: −15%보다 나쁠 때만 넘음(부동소수 오차 1e-12 여유)


class Costs:
    """편도 비용률. kind='stock' = 수수료 + 미끄러짐 + 충격 + (매도)세금 · 'etf' = 수수료 + 미끄러짐(세금 0 · 충격 0 가정)."""

    def __init__(self, cc, market_of, mult=1.0, kind="stock"):
        self.cc, self.market_of, self.mult, self.kind = cc, market_of, float(mult), kind
        self._adv = {}

    def adv(self, code, day):
        if code not in self._adv:
            a = self.cc.adv_series(code)
            ks = [k for k, v in a if v == v and v > 0]
            vs = [v for k, v in a if v == v and v > 0]
            self._adv[code] = (ks, vs)
        ks, vs = self._adv[code]
        j = bisect.bisect_right(ks, str(day)) - 1
        return vs[j] if j >= 0 else None

    def rate(self, side, code, day, notional):
        """돌려줌: (비율, 깃발 dict). 깃발은 실제 체결에서만 셈."""
        flags = {}
        day = str(day)[:8]                    # 15분봉 체결 시각(12자리)도 그날 날짜로(세금 계약 · ADV는 날 단위)
        r = FEE + SLIP
        if self.kind == "stock":
            a = self.adv(code, day)
            if a is None:
                r += ADV_MISSING_IMPACT
                flags["adv_missing"] = 1
            else:
                r += IMPACT_K * math.sqrt(max(notional, 0.0) / a)
            if side == "sell":
                try:
                    r += self.cc.sell_tax_rate(day, "STOCK", self.market_of(code), "S_KOSPI_FARM015")
                except self.cc.UnknownTax:
                    r += TAX_ASSUMED
                    flags["tax_unknown"] = 1
        return r * self.mult, flags


class Account:
    def __init__(self, costs, cash=START_CASH):
        self.costs = costs
        self.cash = float(cash)
        self.start = float(cash)
        self.pos = {}           # pid → 포지션
        self.closed = []        # 닫힌 포지션(pid 단위)
        self.fills = []         # 체결 · 미체결 · 미룸 기록(요청 단위)
        self.tot = defaultdict(float)
        self.counts = defaultdict(int)
        self.realized = 0.0

    # ── 사기 ──
    def buy(self, pid, code, price, day, decision_at, value=None, qty=None, slots=None, tag=""):
        """value(원) 또는 qty(주)로 요청. 돌려줌: 산 수량(0 = 못 삼)."""
        rec = {"pid": pid, "code": code, "side": "buy", "decision_at": decision_at, "fill_at": day, "slots": slots, "tag": tag}
        if pid in self.pos:
            raise AssertionError(f"같은 pid 두 번 매수: {pid}")
        if not price or price <= 0:
            self._miss(rec, "UNFILLED", "체결 시각 값 없음")
            return 0
        want = int(qty) if qty is not None else math.floor(value / price)
        if want < 1:
            self._miss(rec, "UNFILLED", "요청 수량 0")
            return 0

        def total(q):
            n = q * price
            return n * (1 + self.costs.rate("buy", code, day, n)[0])
        q = want
        if total(q) > self.cash:
            lo, hi = 0, want
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if total(mid) <= self.cash:
                    lo = mid
                else:
                    hi = mid - 1
            q = lo
        if q < 1:
            self._miss(rec, "UNFILLED", "현금 1주 미만")
            return 0
        n = q * price
        r, flags = self.costs.rate("buy", code, day, n)
        cost = n * r
        self.cash -= n + cost
        if self.cash < -1e-6:
            raise AssertionError("현금 음수")
        for k in flags:
            self.counts[k + "_fills"] += 1
        self.tot["buy_notional"] += n
        self.tot["buy_cost"] += cost
        status = "REDUCED" if q < want else "FILLED"
        self.counts["buy_" + status.lower()] += 1
        self.pos[pid] = {"pid": pid, "code": code, "qty": q, "qty0": q, "basis": n + cost, "invest0": n + cost, "entry_notional": n,
                         "buy_cost": cost, "decision_at": decision_at, "first_fill": day, "slots": slots, "tag": tag,
                         "realized": 0.0, "sold_notional": 0.0, "sell_cost": 0.0, "n_sells": 0}
        self.fills.append(dict(rec, status=status, qty_ratio=round(q / want, 6), notional=n, cost=cost))
        return q

    # ── 팔기 ──
    def sell(self, pid, price, day, decision_at, qty=None, reason=""):
        """qty None = 모두. 돌려줌: 판 수량."""
        p = self.pos.get(pid)
        if p is None:
            raise AssertionError(f"없는 포지션 매도: {pid}")
        rec = {"pid": pid, "code": p["code"], "side": "sell", "decision_at": decision_at, "fill_at": day, "slots": p["slots"],
               "tag": p["tag"], "reason": reason}
        if not price or price <= 0:
            self._miss(rec, "RETRY", "체결 시각 값 없음")
            return 0
        q = p["qty"] if qty is None else int(qty)
        if q < 1 or q > p["qty"]:
            raise AssertionError(f"매도 수량 오류 {q} / {p['qty']}")
        n = q * price
        r, flags = self.costs.rate("sell", p["code"], day, n)
        cost = n * r
        for k in flags:
            self.counts[k + "_fills"] += 1
        part = p["basis"] * q / p["qty"]
        net = n - cost - part
        self.cash += n - cost
        self.tot["sell_notional"] += n
        self.tot["sell_cost"] += cost
        self.realized += net
        p["basis"] -= part
        p["qty"] -= q
        p["realized"] += net
        p["sold_notional"] += n
        p["sell_cost"] += cost
        p["n_sells"] += 1
        p["last_exit"] = day
        self.fills.append(dict(rec, status="FILLED", qty_ratio=round(q / p["qty0"], 6), notional=n, cost=cost, pnl_net=net))
        if p["qty"] == 0:
            self.closed.append(self._close_row(p, "CLOSED"))
            del self.pos[pid]
        return q

    def _miss(self, rec, status, why):
        self.counts[f"{rec['side']}_{status.lower()}:{why}"] += 1
        self.fills.append(dict(rec, status=status, reason=(rec.get("reason", "") + " · " if rec.get("reason") else "") + why,
                               qty_ratio=0.0, notional=0.0, cost=0.0))

    @staticmethod
    def _close_row(p, status, mtm=None):
        pnl = p["realized"] + ((mtm - p["basis"]) if mtm is not None else 0.0)
        return {"pid": p["pid"], "code": p["code"], "tag": p["tag"], "slots": p["slots"], "decision_at": p["decision_at"],
                "first_fill": p["first_fill"], "last_exit": p.get("last_exit"), "n_sells": p["n_sells"], "status": status,
                "buy_cost": p["buy_cost"], "sell_cost": p["sell_cost"], "invest0": p["invest0"], "pnl_net": pnl,
                "ret_net": pnl / p["invest0"]}

    def held(self, code):
        return sum(p["qty"] for p in self.pos.values() if p["code"] == code)

    def pids_of(self, code):
        return [k for k, p in self.pos.items() if p["code"] == code]

    def mtm(self, price_of):
        inv = 0.0
        for p in self.pos.values():
            px, stale = price_of(p["code"])
            if stale:
                self.counts["stale_mtm_position_days"] += 1
            inv += p["qty"] * px
        return self.cash + inv, inv

    def check(self, price_of, tol=1.0):
        """보존 검사(허용 1원 · 부동소수 누적). 돌려줌: (현금 차이, NAV 항등식 차이)."""
        cash = self.start - self.tot["buy_notional"] - self.tot["buy_cost"] + self.tot["sell_notional"] - self.tot["sell_cost"]
        nav, _ = self.mtm(price_of)
        unreal = sum(p["qty"] * price_of(p["code"])[0] - p["basis"] for p in self.pos.values())
        gap_cash = abs(cash - self.cash)
        gap_nav = abs((nav - self.start) - (self.realized + unreal))
        if any(p["qty"] < 0 for p in self.pos.values()):
            raise AssertionError("수량 음수")
        self.counts["checks"] += 1
        self.tot["max_gap_cash"] = max(self.tot["max_gap_cash"], gap_cash)
        self.tot["max_gap_nav"] = max(self.tot["max_gap_nav"], gap_nav)
        if gap_cash > tol or gap_nav > tol:
            raise AssertionError(f"보존 깨짐: 현금 {gap_cash} · NAV {gap_nav}")
        return gap_cash, gap_nav

    def cum_cost(self):
        return self.tot["buy_cost"] + self.tot["sell_cost"]

    def liquidation_nav(self, price_of, day):
        """마지막 날 모두 청산 시나리오: 같은 날 종가 · 매도 비용까지 같은 NAV에."""
        v, cost = self.cash, 0.0
        for p in self.pos.values():
            px, _ = price_of(p["code"])
            n = p["qty"] * px
            r, _ = self.costs.rate("sell", p["code"], day, n)
            v += n * (1 - r)
            cost += n * r
        return v, cost

    def open_rows(self, price_of):
        return [self._close_row(p, "OPEN", p["qty"] * price_of(p["code"])[0]) for p in self.pos.values()]


# ───────── 성적표 ─────────
def _years(a, b):
    return (date(int(b[:4]), int(b[4:6]), int(b[6:])) - date(int(a[:4]), int(a[4:6]), int(a[6:]))).days / 365.25


def sortino(r):
    r = np.asarray(r, float)
    dd = math.sqrt(float(np.mean(np.minimum(r, 0.0) ** 2))) if len(r) else 0.0
    return float(r.mean() / dd * math.sqrt(252)) if dd > 0 else None


def iid_ci(x, reps=REPS, seed=SEED):
    x = np.asarray(x, float)
    if len(x) < 2:
        return None
    rng = np.random.default_rng(seed)
    m = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(reps)]
    return [round(float(np.percentile(m, 2.5)) * 100, 3), round(float(np.percentile(m, 97.5)) * 100, 3)]


def block_ci(r, reps=REPS, block=BLOCK, seed=SEED):
    """일별 수익률의 이어 붙인 블록 부트스트랩(RULES-0002 common.block_boot_ci와 같은 뽑기) → 평균 × 252의 95% CI(%/년)."""
    r = np.asarray(r, float)
    n = len(r)
    if n < block * 2:
        return None, "계산 불가(날 < 40)"
    rng = np.random.default_rng(seed)
    m = []
    for _ in range(reps):
        starts = rng.integers(0, n - block + 1, n // block + 1)
        s = np.concatenate([r[i:i + block] for i in starts])[:n]
        m.append(s.mean())
    ci = [round(float(np.percentile(m, 2.5)) * 252 * 100, 2), round(float(np.percentile(m, 97.5)) * 252 * 100, 2)]
    return ci, ("불충분 표본(날 < 250)" if n < MIN_DAYS_BLOCK else "")


def month_partial(cal, lo, hi):
    """기간 [lo, hi]가 달 전체 거래일을 덮지 않는 달 = 부분월."""
    by = defaultdict(list)
    for d in cal:
        by[d[:6]].append(d)
    out = set()
    for m, ds in by.items():
        inside = [d for d in ds if lo <= d <= hi]
        if inside and len(inside) < len(ds):
            out.add(m)
    return out


def report(nav_rows, positions, cal, periods=PERIODS, gross_rows=None):
    """nav_rows: [(day, nav, invested)] (날 순) · positions: 닫힌 포지션 행 · cal: 전체 거래일 달력.
    기간 시작 기준 = 앞 거래일 NAV(첫 기간은 처음 현금)."""
    out = {}
    d = [x[0] for x in nav_rows]
    nav = np.array([x[1] for x in nav_rows], float)
    inv = np.array([x[2] for x in nav_rows], float)
    gmap = {x[0]: x[1] for x in gross_rows} if gross_rows else None
    for name, lo, hi in periods:
        idx = [i for i, x in enumerate(d) if lo <= x <= hi]
        if len(idx) < 20:
            out[name] = None
            continue
        i0, i1 = idx[0], idx[-1]
        base = nav[i0 - 1] if i0 > 0 else START_CASH
        seg = np.concatenate([[base], nav[i0:i1 + 1]])
        r = seg[1:] / seg[:-1] - 1
        yrs = _years(d[i0], d[i1])
        cagr = (seg[-1] / seg[0]) ** (1 / yrs) - 1 if yrs > 0 and seg[-1] > 0 else None
        g = None
        if gmap:
            gb = gmap[d[i0 - 1]] if i0 > 0 else START_CASH
            g = (gmap[d[i1]] / gb) ** (1 / yrs) - 1 if yrs > 0 else None
        peak = np.maximum.accumulate(seg)
        mdd = float((seg / peak - 1).min())
        sd = r.std(ddof=1)
        months = {}
        for x, rr in zip(d[i0:i1 + 1], r):
            months[x[:6]] = months.get(x[:6], 1.0) * (1 + rr)
        mraw = {k: float(v) - 1 for k, v in months.items()}
        mon = {k: round(v, 6) for k, v in mraw.items()}
        part = month_partial(cal, d[i0], d[i1])
        tt = [p for p in positions if p.get("last_exit") and lo <= p["last_exit"] <= hi]
        pos_ = sum(p["pnl_net"] for p in tt if p["pnl_net"] > 0)
        neg = -sum(p["pnl_net"] for p in tt if p["pnl_net"] <= 0)
        ci_b, ci_note = block_ci(r)
        worst_m = min(mraw, key=mraw.get) if mraw else None
        hold = [_tdays(p["first_fill"], p["last_exit"], cal) for p in tt]
        out[name] = {
            "from": d[i0], "to": d[i1], "days": len(idx), "base": "처음 현금 1억" if i0 == 0 else f"{d[i0 - 1]} NAV",
            "positions": len(tt), "codes": len({p["code"] for p in tt}),
            "CAGR": round(float(cagr) * 100, 2) if cagr is not None else None,
            "CAGR_gross_same_fills": round(float(g) * 100, 2) if g is not None else None,
            "MDD_daily": round(mdd * 100, 2), "Sharpe": round(float(r.mean() / sd * math.sqrt(252)), 2) if sd > 0 else None,
            "Sortino": round(sortino(r), 2) if sortino(r) is not None else None,
            "worst_day": round(float(r.min()) * 100, 2), "worst_day_at": d[i0 + int(r.argmin())],
            "worst_month": round(mon[worst_m] * 100, 2) if worst_m else None, "worst_month_at": worst_m,
            "worst_month_partial": bool(worst_m in part),
            "day_breach_-15": int((r < LOSS_EDGE - EPS).sum()), "month_breach_-15": int(sum(1 for v in mraw.values() if v < LOSS_EDGE - EPS)),
            "PF": round(pos_ / neg, 3) if neg > 0 else None,
            "win_rate": round(sum(p["pnl_net"] > 0 for p in tt) / len(tt) * 100, 1) if tt else None,
            "avg_pos_ret_pct": round(float(np.mean([p["ret_net"] for p in tt])) * 100, 3) if tt else None,
            "ci95_pos_iid_ref": iid_ci([p["ret_net"] for p in tt]) if tt else None,
            "ci95_block20_ann_mean_ret_pct": ci_b, "ci_block_note": ci_note,
            "avg_hold_tdays": round(float(np.mean(hold)), 1) if hold else None,
            "cost_total_pct_of_base": round(float(sum(p["buy_cost"] + p["sell_cost"] for p in tt) / seg[0]) * 100, 2) if tt else 0.0,
            "utilization_avg_pct": round(float(np.mean(inv[i0:i1 + 1] / nav[i0:i1 + 1])) * 100, 1),
            "monthly": mon, "partial_months": sorted(part),
        }
    return out


_cal_idx = {}


def _tdays(a, b, cal):
    key = id(cal)
    if key not in _cal_idx:
        _cal_idx[key] = {x: i for i, x in enumerate(cal)}
    ix = _cal_idx[key]
    a8, b8 = str(a)[:8], str(b)[:8]
    return ix.get(b8, 0) - ix.get(a8, 0)
