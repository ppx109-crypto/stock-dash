"""REPLAY-0001 순수 회계 커널(1판).

운영 코드와 떨어진 오프라인 함수입니다. 표준 라이브러리만 쓰고, 네트워크 · 파일 · 운영 모듈을 건드리지 않습니다.
입력은 사건 목록(dict)과 설정(dict), 출력은 dict입니다. 정책은 PREREG-LOCK.md 1장과 CONTRACT.md에 고정돼 있습니다.

- 금액: Decimal 원 단위. 수수료 · 세금은 체결 1건마다 ROUND_HALF_UP 원 반올림.
- 확정 체결(FILL · MODEL_FILL)만 현금 · 수량을 바꿈. 의도 · 접수 · 거절 · 취소 · 만료는 바꾸지 않음.
- 같은 시각 순서 없는 사건은 AMBIGUOUS로 실행 전체 거부.
- 평가 가격이 없거나 · 낡았거나 · 지원 안 하는 기업행동이 있으면 그날 NAV는 null(채우지 않음).
- 이 커널 통과는 전략 수익성 · 모의 준비 · 실전 합격을 뜻하지 않음.
"""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR, localcontext

KERNEL_VERSION = "REPLAY-0001-kernel-v1"
PREC = 28
SOURCE_MODES = ("SYNTHETIC", "HISTORICAL_MODEL", "OBSERVED_KIS_PAPER")
EVENT_TYPES = ("DEPOSIT", "WITHDRAW", "ORDER_INTENT", "ORDER_ACCEPTED", "ORDER_REJECTED", "ORDER_CANCELLED",
               "ORDER_EXPIRED", "FILL", "PRICE", "CORP_ACTION", "MARK", "SNAPSHOT")
FILL_CONTENT = ("order_id", "trade_id", "strategy_id", "security_id", "side", "qty", "price", "fee", "tax", "at")
SESSION_OPEN = dt.time(9, 0)
SESSION_CLOSE = dt.time(15, 30)
LIMIT = Decimal("-0.15")
ZERO = Decimal(0)
ONE = Decimal(1)


class InputError(Exception):
    pass


def dec(x):
    if isinstance(x, bool) or x is None:
        raise InputError("NOT_A_NUMBER")
    return Decimal(str(x))


def won(x):
    return x.quantize(ONE, rounding=ROUND_HALF_UP)


def floor_int(x):
    return x.to_integral_value(rounding=ROUND_FLOOR)


def parse_at(s):
    try:
        t = dt.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        raise InputError("BAD_TIME")
    if t.tzinfo is None:
        raise InputError("NO_TZ")
    return t


def add_weekdays(d, n):
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def first_last_weekday(year, month):
    d = dt.date(year, month, 1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    nxt = dt.date(year + (month == 12), month % 12 + 1, 1)
    e = nxt - dt.timedelta(days=1)
    while e.weekday() >= 5:
        e -= dt.timedelta(days=1)
    return d, e


def order_events(events):
    """(at, seq) 순서. 같은 at이 둘 이상인데 seq가 없거나 겹치면 그 사건 id들을 돌려줌."""
    seen, groups = set(), {}
    for e in events:
        if e.get("id") in seen:
            raise InputError("DUP_EVENT_ID:%s" % e.get("id"))
        seen.add(e.get("id"))
        if e.get("type") not in EVENT_TYPES:
            raise InputError("BAD_EVENT_TYPE:%s" % e.get("id"))
        groups.setdefault(parse_at(e["at"]), []).append(e)
    ambiguous = []
    for at, g in groups.items():
        if len(g) > 1:
            seqs = [e.get("seq") for e in g]
            if any(s is None for s in seqs) or len(set(seqs)) != len(seqs):
                ambiguous += [e["id"] for e in g]
    if ambiguous:
        return None, ambiguous
    keyed = [(parse_at(e["at"]), e.get("seq") or 0, i, e) for i, e in enumerate(events)]
    keyed.sort(key=lambda k: (k[0], k[1], k[2]))
    return [(k[0], k[3]) for k in keyed], []


class Account:
    def __init__(self, config):
        mode = config.get("source_mode")
        if mode not in SOURCE_MODES:
            raise InputError("BAD_SOURCE_MODE")
        self.mode = mode
        cost = config.get("cost") or {}
        self.cost = {k: dec(cost.get(k, 0)) for k in ("buy_fee", "sell_fee", "sell_tax")}
        slip = config.get("slippage")
        if slip and not slip.get("included_in_fill_price", False):
            # 미끄러짐을 현금비용으로 따로 빼는 모형은 이번 커널에 없음(가격에 넣어야 함)
            raise InputError("SLIPPAGE_NOT_IN_PRICE_UNSUPPORTED")
        self.cash = ZERO              # trade-date 경제 현금
        self.settled = ZERO
        self.pending = []             # [settle_date, signed amount, fill_id]
        self.lots = {}                # (strategy, trade, security) -> {"qty", "cost"}
        self.trades = {}
        self.orders = {}
        self.fill_seen = {}
        self.fills = []
        self.flows = []               # (at, signed amount, event_id)
        self.prices = {}              # sec -> [{"price","as_of","as_of_s","avail","version","event_id"}]
        self.corp = {}                # sec -> [at]
        self.marks = []
        self.rejections = []
        self.sizing = []
        self.discrepancies = []
        self.corrections = []
        self.snapshots = []
        self.costs_by_date = {}
        self.duplicates_ignored = 0
        self.min_cash = None

    # ---------- 공통 ----------
    def reject(self, e, reason):
        self.rejections.append({"event_id": e["id"], "reason": reason})

    def reserved(self):
        r = ZERO
        for o in self.orders.values():
            if o["state"] == "OPEN" and o["side"] == "BUY" and o["remaining"] > 0:
                n = o["remaining"] * o["price"]
                r += n + won(n * self.cost["buy_fee"])
        return r

    def orderable(self):
        return self.cash - self.reserved()

    def settle_until(self, d):
        keep = []
        for p in self.pending:
            if p[0] <= d:
                self.settled += p[1]
            else:
                keep.append(p)
        self.pending = keep

    def held(self):
        out = {}
        for (s, t, sec), lot in self.lots.items():
            if lot["qty"] > 0:
                out[sec] = out.get(sec, ZERO) + lot["qty"]
        return out

    def note_cash(self):
        if self.min_cash is None or self.cash < self.min_cash:
            self.min_cash = self.cash

    # ---------- 입출금 ----------
    def flow(self, at, e, sign):
        a = dec(e["amount"])
        if a <= 0 or a != a.to_integral_value():
            return self.reject(e, "BAD_AMOUNT")
        if sign < 0 and a > self.cash:
            return self.reject(e, "INSUFFICIENT_CASH")
        self.cash += sign * a
        self.settled += sign * a
        self.flows.append((at, sign * a, e["id"]))
        self.note_cash()

    # ---------- 주문 ----------
    def intent(self, at, e):
        oid = e["order_id"]
        if oid in self.orders:
            return self.reject(e, "DUP_ORDER_ID")
        side = e["side"]
        o = {"state": "INTENT", "side": side, "price": dec(e["price"]), "qty": None, "remaining": ZERO,
             "filled": ZERO, "cancelled_qty": ZERO, "trade_id": e["trade_id"], "strategy_id": e["strategy_id"],
             "security_id": e["security_id"]}
        self.orders[oid] = o
        if not e.get("model_fill"):
            o["qty"] = dec(e["qty"])
            return
        px = o["price"]
        if px <= 0:
            o["state"] = "NOT_SENT"
            return self.reject(e, "BAD_PRICE")
        if side == "BUY":
            alloc = dec(e["alloc_won"])
            orderable = self.orderable()
            limit = min(alloc, orderable)
            fee = self.cost["buy_fee"]
            q = floor_int(limit / (px * (1 + fee))) if limit > 0 else ZERO
            while q > 0 and q * px + won(q * px * fee) > limit:
                q -= 1
            naive = floor_int(alloc / px)
            rec = {"order_id": oid, "alloc_won": alloc, "nav_ref_won": dec(e.get("nav_ref_won", 0)),
                   "orderable_cash": orderable, "limit": limit, "naive_qty": naive, "qty": q}
            if q == 0:
                rec["reason"] = "ZERO_BY_CASH" if orderable < alloc else "ZERO_CANNOT_AFFORD_ONE_WITH_COST"
            elif orderable < alloc:
                rec["reason"] = "REDUCED_BY_CASH"
            elif q < naive:
                rec["reason"] = "REDUCED_FOR_COST"
            else:
                rec["reason"] = "OK"
            if orderable < alloc:
                rec["shortfall_won"] = alloc - orderable
            self.sizing.append(rec)
        elif side == "SELL" and e.get("sizing") == "ALL_HELD":
            lot = self.lots.get((e["strategy_id"], e["trade_id"], e["security_id"]))
            q = lot["qty"] if lot else ZERO
        else:
            o["state"] = "NOT_SENT"
            return self.reject(e, "UNSUPPORTED_SIZING")
        o["qty"] = q
        if q == 0:
            o["state"] = "NOT_SENT_ZERO"
            return
        o["state"] = "OPEN"
        o["remaining"] = q
        f = {"id": e["id"] + "#mf", "type": "FILL", "at": e["at"], "fill_id": oid + "_mf", "order_id": oid,
             "trade_id": e["trade_id"], "strategy_id": e["strategy_id"], "security_id": e["security_id"],
             "side": side, "qty": q, "price": px, "evidence": "MODEL_FILL"}
        self.fill(at, f)

    def order_status(self, e, state):
        o = self.orders.get(e["order_id"])
        if o is None:
            return self.reject(e, "UNKNOWN_ORDER")
        if state == "OPEN":
            if o["state"] != "INTENT":
                return self.reject(e, "BAD_ORDER_STATE")
            o["state"], o["remaining"] = "OPEN", o["qty"]
            return
        if o["state"] == "OPEN":
            o["cancelled_qty"] = o["remaining"]
        elif o["state"] != "INTENT":
            return self.reject(e, "BAD_ORDER_STATE")
        o["remaining"] = ZERO
        o["state"] = state

    # ---------- 체결 ----------
    def fill(self, at, e):
        fid = e["fill_id"]
        content = tuple(str(e.get(k)) for k in FILL_CONTENT)
        if fid in self.fill_seen:
            if self.fill_seen[fid] == content:
                self.duplicates_ignored += 1
                return
            return self.reject(e, "FILL_ID_CONFLICT")
        try:
            q = dec(e["qty"])
        except InputError:
            return self.reject(e, "BAD_QTY")
        if q <= 0 or q != q.to_integral_value():
            return self.reject(e, "BAD_QTY")
        try:
            px = dec(e["price"])
        except InputError:
            return self.reject(e, "BAD_PRICE")
        if px <= 0:
            return self.reject(e, "BAD_PRICE")
        if self.mode == "OBSERVED_KIS_PAPER":
            if not e.get("evidence_ref"):
                return self.reject(e, "MISSING_EVIDENCE")
        elif e.get("evidence") != "MODEL_FILL":
            return self.reject(e, "EVIDENCE_MODE_MISMATCH")
        side = e["side"]
        key = (e["strategy_id"], e["trade_id"], e["security_id"])
        lot = self.lots.get(key)
        notional = q * px
        d = at.date()
        if side == "BUY":
            fee = dec(e["fee"]) if e.get("fee") is not None else won(notional * self.cost["buy_fee"])
            tax = dec(e["tax"]) if e.get("tax") is not None else ZERO
            total = notional + fee + tax
            if total > self.cash:
                return self.reject(e, "INSUFFICIENT_CASH")
        elif side == "SELL":
            if lot is None or q > lot["qty"]:
                return self.reject(e, "OVERSELL")
            fee = dec(e["fee"]) if e.get("fee") is not None else won(notional * self.cost["sell_fee"])
            tax = dec(e["tax"]) if e.get("tax") is not None else won(notional * self.cost["sell_tax"])
        else:
            return self.reject(e, "BAD_SIDE")
        self.fill_seen[fid] = content
        sd = dt.date.fromisoformat(e["settle_date"]) if e.get("settle_date") else add_weekdays(d, 2)
        tr = self.trades.setdefault(e["trade_id"], {
            "strategy_id": e["strategy_id"], "security_id": e["security_id"], "entry_fills": 0, "exit_fills": 0,
            "entry_cost": ZERO, "realized": ZERO, "exits": [], "open_qty": ZERO, "open_cost": ZERO,
            "ledger_ret": None})
        rec = {"fill_id": fid, "event_id": e["id"], "at": e["at"], "side": side, "qty": q, "price": px,
               "notional": notional, "fee": fee, "tax": tax, "trade_id": e["trade_id"],
               "strategy_id": e["strategy_id"], "security_id": e["security_id"], "evidence": e.get("evidence"),
               "settle_date": sd.isoformat()}
        if e.get("ref_price") is not None and e.get("slippage_in_price"):
            rec["slippage_info_won"] = (px - dec(e["ref_price"])) * q
        if side == "BUY":
            self.cash -= total
            self.pending.append([sd, -total, fid])
            if lot is None:
                lot = self.lots[key] = {"qty": ZERO, "cost": ZERO}
            lot["qty"] += q
            lot["cost"] += total
            tr["entry_fills"] += 1
            tr["entry_cost"] += total
        else:
            net = notional - fee - tax
            alloc = lot["cost"] if q == lot["qty"] else won(lot["cost"] * q / lot["qty"])
            realized = net - alloc
            lot["qty"] -= q
            lot["cost"] -= alloc
            self.cash += net
            self.pending.append([sd, net, fid])
            tr["exit_fills"] += 1
            tr["realized"] += realized
            tr["exits"].append({"fill_id": fid, "qty": q, "cost_alloc": alloc, "realized": realized})
            if e.get("ledger_pnl_pct") is not None:
                tr["ledger_ret"] = dec(e["ledger_pnl_pct"]) / 100
            rec["cost_alloc"], rec["realized"] = alloc, realized
        tr["open_qty"] = sum((l["qty"] for (s, t, c), l in self.lots.items() if t == e["trade_id"]), ZERO)
        tr["open_cost"] = sum((l["cost"] for (s, t, c), l in self.lots.items() if t == e["trade_id"]), ZERO)
        if tr["open_qty"] == 0 and tr["ledger_ret"] is not None and tr["entry_cost"] > 0:
            fr = tr["realized"] / tr["entry_cost"]
            if fr != tr["ledger_ret"]:
                self.discrepancies.append({"trade_id": e["trade_id"], "ledger_ret": tr["ledger_ret"],
                                           "fill_net_ret": fr, "fill_net_pnl_won": tr["realized"],
                                           "note": "장부 pnl은 참고만; 현금 · NAV는 체결로만"})
        ds = d.isoformat()
        self.costs_by_date[ds] = self.costs_by_date.get(ds, ZERO) + fee + tax
        o = self.orders.get(e["order_id"])
        if o is not None and o["state"] == "OPEN":
            o["filled"] += q
            o["remaining"] = max(ZERO, o["remaining"] - q)
            if o["remaining"] == 0:
                o["state"] = "FILLED"
        self.fills.append(rec)
        self.note_cash()

    # ---------- 가격 ----------
    def price(self, at, e):
        av, asof = parse_at(e["available_at"]), parse_at(e["as_of"])
        if av < asof:
            return self.reject(e, "BAD_PRICE_TIME")
        if av != at:
            return self.reject(e, "PRICE_AT_MISMATCH")
        for sec, p in e["prices"].items():
            p = dec(p)
            if p <= 0:
                self.reject(e, "BAD_PRICE")
                continue
            self.prices.setdefault(sec, []).append({"price": p, "as_of": asof, "as_of_s": e["as_of"], "avail": av,
                                                    "version": int(e.get("version", 1)), "event_id": e["id"]})
            for m in self.marks:
                if asof <= m["at"] < av and sec in m["held"]:
                    self.corrections.append({"security": sec, "as_of": e["as_of"], "version": int(e.get("version", 1)),
                                             "price": p, "snapshot_date": m["date"], "applied": False})

    def pick_price(self, sec, m, d):
        if any(c <= m for c in self.corp.get(sec, [])):
            return None, "UNSUPPORTED_CORP_ACTION:%s" % sec
        cand = [p for p in self.prices.get(sec, []) if p["avail"] <= m and p["as_of"] <= m]
        if not cand:
            return None, "MISSING_PRICE:%s" % sec
        best = max(cand, key=lambda p: (p["as_of"], p["version"]))
        if best["as_of"].date() < d:
            return None, "STALE_PRICE:%s" % sec
        return best["price"], None

    # ---------- 평가 ----------
    def mark(self, at, e):
        d = dt.date.fromisoformat(e["date"])
        if d != at.date():
            raise InputError("MARK_DATE_MISMATCH:%s" % e["id"])
        if any(m["date"] == e["date"] for m in self.marks):
            raise InputError("DUP_MARK_DATE:%s" % e["id"])
        held = self.held()
        mv, reasons, used = ZERO, [], {}
        for sec in sorted(held):
            p, why = self.pick_price(sec, at, d)
            if why:
                reasons.append(why)
            else:
                used[sec] = p
                mv += held[sec] * p
        recv = sum((p[1] for p in self.pending if p[1] > 0), ZERO)
        pay = -sum((p[1] for p in self.pending if p[1] < 0), ZERO)
        if self.cash != self.settled + recv - pay:
            raise AssertionError("CASH_IDENTITY_BROKEN:%s" % e["id"])
        nav = None if reasons else self.cash + mv
        prev = self.marks[-1] if self.marks else None
        prev_at = prev["at"] if prev else None
        fs = fe = ZERO
        intraday = False
        for fat, a, _ in self.flows:
            if (prev_at is None or fat > prev_at) and fat <= at:
                if fat.date() == d and SESSION_OPEN <= fat.timetz().replace(tzinfo=None) < SESSION_CLOSE:
                    intraday = True
                elif fat.date() == d and fat.timetz().replace(tzinfo=None) >= SESSION_CLOSE:
                    fe += a
                else:
                    fs += a
        nav_prev = prev["nav"] if prev else ZERO
        r, rr = None, None
        if intraday:
            rr = "INTRADAY_FLOW"
        elif nav is None or (prev is not None and nav_prev is None):
            rr = "NAV_NULL"
        elif nav_prev + fs <= 0:
            rr = "NONPOSITIVE_BASE"
        else:
            with localcontext() as c:
                c.prec = PREC
                r = (nav - fe) / (nav_prev + fs) - 1
        snap = {"date": e["date"], "at": at, "nav": nav, "cash_td": self.cash, "settled": self.settled,
                "receivable": recv, "payable": pay, "mv": None if reasons else mv,
                "reason": ";".join(reasons) if reasons else None, "held": set(held), "r": r, "r_reason": rr,
                "positions": {k: v for k, v in held.items()}, "prices_used": used, "flow_start": fs, "flow_end": fe}
        self.marks.append(snap)

    def snapshot(self, at, e):
        self.snapshots.append({"event_id": e["id"], "at": e["at"], "cash": self.cash,
                               "orderable_cash": self.orderable(), "settled": self.settled})

    # ---------- 실행 ----------
    def apply(self, at, e):
        self.settle_until(at.date())
        t = e["type"]
        if t == "DEPOSIT":
            self.flow(at, e, 1)
        elif t == "WITHDRAW":
            self.flow(at, e, -1)
        elif t == "ORDER_INTENT":
            self.intent(at, e)
        elif t == "ORDER_ACCEPTED":
            self.order_status(e, "OPEN")
        elif t == "ORDER_REJECTED":
            self.order_status(e, "REJECTED")
        elif t == "ORDER_CANCELLED":
            self.order_status(e, "CANCELLED")
        elif t == "ORDER_EXPIRED":
            self.order_status(e, "EXPIRED")
        elif t == "FILL":
            self.fill(at, e)
        elif t == "PRICE":
            self.price(at, e)
        elif t == "CORP_ACTION":
            self.corp.setdefault(e["security_id"], []).append(at)
        elif t == "MARK":
            self.mark(at, e)
        elif t == "SNAPSHOT":
            self.snapshot(at, e)

    def summary(self):
        with localcontext() as c:
            c.prec = PREC
            return self._summary()

    def _summary(self):
        navs, returns, reasons = {}, {}, {}
        for m in self.marks:
            navs[m["date"]] = {"nav": m["nav"], "cash_td": m["cash_td"], "settled": m["settled"],
                               "receivable": m["receivable"], "payable": m["payable"], "mv": m["mv"],
                               "reason": m["reason"]}
            returns[m["date"]] = m["r"]
            if m["r_reason"]:
                reasons[m["date"]] = m["r_reason"]
        months = {}
        for m in self.marks:
            months.setdefault(m["date"][:7], []).append(m)
        mon_out = {}
        for k, ms in months.items():
            y, mo = int(k[:4]), int(k[5:])
            fw, lw = first_last_weekday(y, mo)
            first, last = dt.date.fromisoformat(ms[0]["date"]), dt.date.fromisoformat(ms[-1]["date"])
            ret = None
            if all(x["r"] is not None for x in ms):
                g = ONE
                for x in ms:
                    g *= 1 + x["r"]
                ret = g - 1
            mon_out[k] = {"ret": ret, "partial": first > fw or last < lw}
        rs = [m["r"] for m in self.marks]
        twr = mdd = None
        if rs and all(r is not None for r in rs):
            u, peak, mdd = ONE, ONE, ZERO
            for r in rs:
                u *= 1 + r
                peak = max(peak, u)
                mdd = min(mdd, u / peak - 1)
            twr = u - 1
        raw, raw_reason = None, None
        if len(self.flows) != 1 or self.flows[0][1] <= 0:
            raw_reason = "FLOWS_PRESENT"
        elif any(m["nav"] is None for m in self.marks) or not self.marks:
            raw_reason = "NAV_NULL"
        else:
            peak, raw = self.flows[0][1], ZERO
            for m in self.marks:
                peak = max(peak, m["nav"])
                raw = min(raw, m["nav"] / peak - 1)

        def verdict(vals):
            known = [v for v in vals if v is not None]
            if any(v < LIMIT for v in known):
                return "FAIL"
            if not vals or len(known) != len(vals):
                return "INCOMPLETE"
            return "PASS"
        mons = [v["ret"] for v in mon_out.values()]
        vd, vm, vx = verdict(rs), verdict(mons), verdict([mdd])
        allv = (vd, vm, vx)
        risk = {"day": min((r for r in rs if r is not None), default=None),
                "month": min((r for r in mons if r is not None), default=None),
                "mdd": mdd, "raw_nav_mdd": raw, "raw_nav_mdd_reason": raw_reason,
                "verdict_day": vd, "verdict_month": vm, "verdict_mdd": vx,
                "verdict": "FAIL" if "FAIL" in allv else ("INCOMPLETE" if "INCOMPLETE" in allv else "PASS"),
                "limit": LIMIT}
        net_flows = sum((a for _, a, _ in self.flows), ZERO)
        last = self.marks[-1] if self.marks else None
        money_pnl = (last["nav"] - net_flows) if last and last["nav"] is not None else None
        attribution = None
        if last and last["nav"] is not None:
            attribution = {}
            for tid, tr in self.trades.items():
                s = tr["strategy_id"]
                attribution[s] = attribution.get(s, ZERO) + tr["realized"]
            for (s, t, sec), lot in self.lots.items():
                if lot["qty"] > 0:
                    attribution[s] = attribution.get(s, ZERO) + lot["qty"] * last["prices_used"][sec] - lot["cost"]
        exposure = ZERO
        for m in self.marks:
            if m["nav"] is not None and m["nav"] > 0 and m["mv"] is not None:
                exposure = max(exposure, m["mv"] / m["nav"])
        orders = {k: {"state": o["state"], "side": o["side"], "qty": o["qty"], "remaining": o["remaining"],
                      "filled": o["filled"], "cancelled_qty": o["cancelled_qty"]} for k, o in self.orders.items()}
        trades = {k: {kk: vv for kk, vv in t.items()} for k, t in self.trades.items()}
        return {"status": "OK", "kernel_version": KERNEL_VERSION, "source_mode": self.mode,
                "cash_basis": "TRADE_DATE", "settlement_policy": "SYNTHETIC_T+2_WEEKDAY_OR_INPUT",
                "cost_model": {"basis": "SYNTHETIC_FIXTURE", **{k: v for k, v in self.cost.items()},
                               "real_cost_evidence": None},
                "cash": self.cash, "settled_cash": self.settled, "orderable_cash": self.orderable(),
                "positions": {k: v for k, v in self.held().items()},
                "navs": navs, "returns": returns, "return_reasons": reasons, "months": mon_out, "risk": risk,
                "twr_total": twr, "net_flows": net_flows, "money_pnl": money_pnl,
                "flows": [{"event_id": i, "at": a.isoformat(), "amount": x} for a, x, i in self.flows],
                "rejections": self.rejections, "duplicates_ignored": self.duplicates_ignored,
                "sizing": self.sizing, "orders": orders, "trades": trades, "discrepancies": self.discrepancies,
                "corrections_after_snapshot": self.corrections, "costs_by_date": self.costs_by_date,
                "snapshots": self.snapshots, "fills": self.fills, "ambiguous_ids": [],
                "min_cash": self.min_cash, "max_gross_exposure": exposure, "attribution": attribution}


def run(config, events):
    """사건 목록을 처리해 요약 dict를 돌려줌. 입력 오류는 status=INPUT_ERROR, 순서 불명은 AMBIGUOUS."""
    try:
        ordered, ambiguous = order_events(events)
        if ambiguous:
            return {"status": "AMBIGUOUS", "kernel_version": KERNEL_VERSION, "ambiguous_ids": ambiguous,
                    "navs": {}, "note": "같은 시각에 순서(seq)가 없는 사건이 있어 아무 상태도 만들지 않음"}
        acct = Account(config)
        for at, e in ordered:
            acct.apply(at, e)
        return acct.summary()
    except InputError as x:
        return {"status": "INPUT_ERROR", "kernel_version": KERNEL_VERSION, "error": str(x), "navs": {}}
