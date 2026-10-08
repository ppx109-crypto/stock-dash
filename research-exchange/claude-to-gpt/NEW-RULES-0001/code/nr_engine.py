"""NEW-RULES-0001 규칙 엔진 · 실행기(PREREG §1 ~ §3 그대로). 표준 라이브러리 + numpy. 네트워크 · 파일 쓰기 없음.

- 자료: <base>/etf-data/<코드>.json의 종가(수정주가 · 분배금 미반영). 자료 이상 규칙(PREREG §0)을 기계적으로 적용.
- 판단: d 종가까지의 값만. 체결: 다음 거래일 종가(kernel2.Account · 정수 주 · 현금 확인 · 일별 MTM).
- 공통 손실 제어: 고점 대비 노출 배수 m · 달력월 −6% 정지(PREREG §2).
"""
import bisect
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

import kernel2 as KN

U = ("069500", "229200", "091160", "091170", "091180", "102970", "117680", "117700", "266420", "305720",
     "133690", "143850", "192090", "195930", "241180", "148070", "114820", "132030", "138230")
G_SECTOR = {"091160", "091170", "091180", "102970", "117680", "117700", "266420", "305720"}
U_C = ("069500", "229200", "133690", "143850", "192090", "195930", "241180")
CAL_CODE = "069500"
FIX_LIST = {("114820", "20130628")}                  # PREREG §0: 대상 안에서 고칠 자료 이상(157450 · 261240은 대상 밖)
ELIG = 260
BAND = 0.02
DD_LEVELS = ((-0.05, 1.0), (-0.10, 0.5))       # DD > −5% → 1.0 · > −10% → 0.5 · 그 밖 0.25
M_FLOOR = 0.25
MONTH_STOP = -0.06

EXPERIMENTS = {
    "A1": ("A", {"K": 3, "V": 0.08}), "A2": ("A", {"K": 3, "V": 0.12}), "A3": ("A", {"K": 5, "V": 0.08}), "A4": ("A", {"K": 5, "V": 0.12}),
    "B1": ("B", {"N": 55, "X": 20, "b": 0.015}), "B2": ("B", {"N": 55, "X": 20, "b": 0.025}),
    "B3": ("B", {"N": 120, "X": 40, "b": 0.015}), "B4": ("B", {"N": 120, "X": 40, "b": 0.025}),
    "C1": ("C", {"k": 1.0, "H": 5}), "C2": ("C", {"k": 1.0, "H": 10}), "C3": ("C", {"k": 1.5, "H": 5}), "C4": ("C", {"k": 1.5, "H": 10}),
}


# ───────── 자료 ─────────
def load(base, codes, end=None):
    """돌려줌: (달력, {코드: (날짜 목록, 종가 np.array)}, 고친 기록)."""
    out, fixes = {}, []
    for c in sorted(set(codes) | {CAL_CODE}):
        rows = [(str(d), float(v)) for d, v in json.loads(Path(base, "etf-data", f"{c}.json").read_text(encoding="utf-8"))["closes"] if v]
        rows.sort()
        if end:
            rows = [r for r in rows if r[0] <= end]
        ds = [r[0] for r in rows]
        px = np.array([r[1] for r in rows], float)
        for t in range(1, len(px) - 1):            # PREREG §0 자료 이상: 튀었다 되돌아옴(찾기만 기록)
            a, b = px[t] / px[t - 1] - 1, px[t + 1] / px[t] - 1
            if abs(a) > 0.08 and a * b < 0 and abs(px[t + 1] / px[t - 1] - 1) <= 0.015:
                hit = (c, ds[t]) in FIX_LIST
                fixes.append({"code": c, "date": ds[t], "jump": round(float(a), 4), "back": round(float(b), 4), "fixed": hit})
                if hit:                            # PREREG 본문이 고친다고 적은 것만 고침(실제 시장 급변일은 그대로)
                    px[t] = px[t - 1]
        out[c] = (ds, px)
    cal = out[CAL_CODE][0]
    return cal, out, fixes


class Series:
    """한 종목의 지표(그날까지 값만)."""

    def __init__(self, ds, px):
        self.ds, self.px = ds, px
        self.ix = {d: i for i, d in enumerate(ds)}
        self.cs = np.concatenate([[0.0], np.cumsum(px)])
        r = np.diff(px) / px[:-1]
        self.r = np.concatenate([[np.nan], r])

    def at(self, d):
        return self.ix.get(d)

    def sma(self, i, n):
        return (self.cs[i + 1] - self.cs[i + 1 - n]) / n if i + 1 >= n else None

    def ret(self, i, n):
        return self.px[i] / self.px[i - n] - 1 if i >= n else None

    def sd(self, i, n):
        if i < n:
            return None
        return float(np.std(self.r[i - n + 1:i + 1], ddof=1))

    def hi(self, i, n):        # 앞 n일 최고(오늘 제외)
        return float(self.px[i - n:i].max()) if i >= n else None

    def lo(self, i, n):
        return float(self.px[i - n:i].min()) if i >= n else None

    def atrc(self, i, n=20):
        return float(np.mean(np.abs(np.diff(self.px[i - n:i + 1])))) if i >= n else None


# ───────── 실행기 ─────────
class Runner:
    def __init__(self, cal, data, rule, params, mult=1.0, cash=1e7, start="20120102", end=None, bump_after=None):
        self.cal = [d for d in cal if d >= start and (end is None or d <= end)]
        self.S = {}
        for c, (ds, px) in data.items():
            if bump_after:
                px = np.array([v * 1.37 if d > bump_after else v for d, v in zip(ds, px)], float)
            self.S[c] = Series(ds, px)
        self.rule, self.p = rule, params
        self.costs = KN.Costs(None, lambda c: "ETF", mult, "etf")
        self.acc = KN.Account(self.costs, cash)
        self.cash0 = cash
        self.pending = []
        self.navs, self.gross = [], []
        self.peak, self.m_applied = cash, 1.0
        self.halt_month, self.month_base, self.cur_month = None, cash, None
        self.notes = defaultdict(int)
        self.attr = defaultdict(float)          # 종목별 순손익(날마다 평가 변화 − 비용)
        self.attr_by_day = []                   # (날, {코드: 그날 손익})
        self.last_px = {}
        self.pos_meta = {}                      # 코드 → {entry, peak, atr0, days}
        self.w_month = {}
        self.events = []

    # 값
    def close(self, c, d):
        s = self.S[c]
        i = s.at(d)
        return (float(s.px[i]), i) if i is not None else (None, None)

    def price_of(self, d):
        def f(c):
            p, _ = self.close(c, d)
            if p:
                return p, False
            s = self.S[c]
            k = bisect.bisect_right(s.ds, d) - 1
            return (float(s.px[k]) if k >= 0 else 0.0), True
        return f

    def held(self):
        h = defaultdict(int)
        for p in self.acc.pos.values():
            h[p["code"]] += p["qty"]
        return dict(h)

    # 체결
    def sell_code(self, c, qty, d, dec, why):
        """FIFO로 qty주(None = 모두) 팖."""
        p, _ = self.close(c, d)
        pids = sorted(self.acc.pids_of(c), key=lambda k: (self.acc.pos[k]["first_fill"], k))
        left = None if qty is None else int(qty)
        for pid in pids:
            q = self.acc.pos[pid]["qty"] if left is None else min(left, self.acc.pos[pid]["qty"])
            if q < 1:
                break
            before = self.acc.cum_cost()
            self.acc.sell(pid, p, d, dec, qty=q, reason=why)
            self.attr[c] -= self.acc.cum_cost() - before
            self._day_attr[c] = self._day_attr.get(c, 0.0) - (self.acc.cum_cost() - before)
            if left is not None:
                left -= q
                if left <= 0:
                    break

    def fill(self, d):
        keep = []
        for o in sorted(self.pending, key=lambda x: 0 if x["side"] == "sell" else 1):
            c = o["code"]
            p, _ = self.close(c, d)
            if p is None:
                self.notes[f"{o['side']}_retry_no_price"] += 1
                keep.append(o)
                continue
            if o["side"] == "sell":
                have = sum(x["qty"] for x in self.acc.pos.values() if x["code"] == c)
                if have < 1:
                    continue
                q = None if o.get("qty") is None or o["qty"] >= have else o["qty"]
                if q is not None and q < 1:
                    continue
                self.sell_code(c, q, d, o["dec"], o["why"])
                if c not in self.held():
                    self.pos_meta.pop(c, None)
            else:
                pid = f"{c}:{d}"
                if pid in self.acc.pos:
                    pid += ":2"
                before = self.acc.cum_cost()
                got = self.acc.buy(pid, c, p, d, o["dec"], value=o.get("value"), qty=o.get("qty"), tag=o["why"])
                cost = self.acc.cum_cost() - before
                self.attr[c] -= cost
                self._day_attr[c] = self._day_attr.get(c, 0.0) - cost
                if got:
                    meta = self.pos_meta.get(c)
                    if meta is None or o.get("new"):
                        s = self.S[c]
                        i = s.at(d)
                        self.pos_meta[c] = {"entry": p, "peak": p, "atr0": s.atrc(i) or 0.0, "days": 0, "fill": d}
        self.pending = keep

    # 하루
    def step(self, d, nxt_month_differs):
        pf = self.price_of(d)
        self._day_attr = {}
        for c, q in self.held().items():           # 평가 변화(전날 종가 → 오늘 종가)
            p, _ = self.close(c, d)
            if p is not None and c in self.last_px:
                v = q * (p - self.last_px[c])
                self.attr[c] += v
                self._day_attr[c] = self._day_attr.get(c, 0.0) + v
        self.fill(d)
        for c in self.held():
            p, _ = self.close(c, d)
            if p is not None:
                self.last_px[c] = p
        for c in list(self.last_px):
            if c not in self.held():
                self.last_px.pop(c)
        nav, inv = self.acc.mtm(pf)
        self.acc.check(pf)
        self.navs.append((d, nav, inv))
        self.gross.append((d, nav + self.acc.cum_cost()))
        self.attr_by_day.append((d, dict(self._day_attr)))
        for c, meta in self.pos_meta.items():
            meta["days"] += 1 if meta["fill"] != d else 0
            p, _ = self.close(c, d)
            if p is not None:
                meta["peak"] = max(meta["peak"], p)
        # 손실 제어
        if self.cur_month != d[:6]:
            if self.cur_month is not None:
                self.month_base = self._prev_nav
            self.cur_month = d[:6]
        self._prev_nav = nav
        self.peak = max(self.peak, nav)
        dd = nav / self.peak - 1
        m = next((v for edge, v in DD_LEVELS if dd > edge), M_FLOOR)
        mtd = nav / self.month_base - 1
        if self.halt_month != d[:6] and mtd <= MONTH_STOP:
            self.halt_month = d[:6]
            self.notes["month_stop"] += 1
            self.events.append((d, "달력월 정지", round(mtd, 4)))
            self.pending = [{"code": c, "side": "sell", "qty": None, "dec": d, "why": "달력월 −6% 정지"} for c in self.held()]
            self.w_month = {}
            return
        if self.halt_month == d[:6]:
            return
        held = self.held()
        orders = []
        scale = 1.0
        if m < self.m_applied - 1e-12:
            scale = m / self.m_applied
            self.notes["dd_scale_down"] += 1
            self.events.append((d, "노출 줄이기", self.m_applied, m, round(dd, 4)))
            for c, q in held.items():
                cut = math.floor(q * (1 - scale))
                if cut >= 1:
                    orders.append({"code": c, "side": "sell", "qty": cut, "dec": d, "why": f"노출 {self.m_applied}→{m}"})
        self.m_applied = m
        orders = getattr(self, "rule_" + self.rule)(d, nav, m, held, orders, nxt_month_differs)
        self.pending = orders

    def run(self):
        for k, d in enumerate(self.cal):
            nd = self.cal[k + 1] if k + 1 < len(self.cal) else None
            self.step(d, nd is None or nd[:6] != d[:6])
        last = self.cal[-1]
        pf = self.price_of(last)
        liq, liq_cost = self.acc.liquidation_nav(pf, last)
        return {"nav": self.navs, "gross": self.gross, "closed": self.acc.closed, "open": self.acc.open_rows(pf), "fills": self.acc.fills,
                "counts": dict(self.acc.counts), "tot": dict(self.acc.tot), "notes": dict(self.notes), "attr": dict(self.attr),
                "attr_by_day": self.attr_by_day, "events": self.events, "liquidation": {"nav": liq, "cost": liq_cost},
                "pending_at_end": len(self.pending), "cal": self.cal, "cash0": self.cash0}

    # ── 규칙 A: 분산 추세 · 상대강도 포트폴리오 ──
    def rule_A(self, d, nav, m, held, orders, month_end):
        K, V = self.p["K"], self.p["V"]
        sold = {o["code"] for o in orders if o["side"] == "sell" and o["qty"] is None}
        if not month_end:
            for c in held:                                       # 달 중간: 200일 평균 아래 → 전부 팖
                s = self.S[c]
                i = s.at(d)
                if i is not None and i >= ELIG and s.px[i] < s.sma(i, 200):
                    orders = [o for o in orders if o["code"] != c]
                    orders.append({"code": c, "side": "sell", "qty": None, "dec": d, "why": "200일 평균 아래"})
                    self.w_month.pop(c, None)
            return orders
        cand = []
        for c in U:
            s = self.S.get(c)
            i = s.at(d) if s else None
            if i is None or i < ELIG:
                continue
            sc = np.mean([s.ret(i, 63), s.ret(i, 126), s.ret(i, 252)])
            if sc > 0 and s.px[i] > s.sma(i, 200):
                cand.append((sc, c))
        cand.sort(reverse=True)
        pick, nsec = [], 0
        for sc, c in cand:
            if len(pick) >= K:
                break
            if c in G_SECTOR:
                if nsec >= 2:
                    continue
                nsec += 1
            pick.append(c)
        w = {}
        if pick:
            sig = {c: self.S[c].sd(self.S[c].at(d), 60) * math.sqrt(252) for c in pick}
            raw = {c: 1 / sig[c] for c in pick if sig[c] and sig[c] > 0}
            tot = sum(raw.values())
            w = {c: v / tot for c, v in raw.items()}
            pv = self._port_vol(d, w)
            if pv and pv > V:
                w = {c: v * V / pv for c, v in w.items()}
            w = {c: min(v, 0.35) for c, v in w.items()}
        self.w_month = dict(w)
        out = [o for o in orders]
        for c in sorted(set(held) | set(w)):
            p, _ = self.close(c, d)
            if p is None:
                continue
            want = w.get(c, 0.0) * m * nav
            have = held.get(c, 0) * p
            if c not in w:
                out = [o for o in out if o["code"] != c]
                out.append({"code": c, "side": "sell", "qty": None, "dec": d, "why": "리밸런싱 빠짐"})
            elif c not in held:
                q = math.floor(want / p)
                if q >= 1:
                    out.append({"code": c, "side": "buy", "qty": q, "dec": d, "why": "리밸런싱 새로", "new": True})
            elif abs(want - have) >= BAND * nav:
                out = [o for o in out if o["code"] != c]
                q = math.floor(abs(want - have) / p)
                if q >= 1:
                    out.append({"code": c, "side": "sell" if want < have else "buy", "qty": q, "dec": d, "why": "리밸런싱 조정"})
        return out

    def _port_vol(self, d, w):
        cs = list(w)
        rows = []
        k = self.cal.index(d) if d in self.cal else None
        if k is None:
            return None
        for dd in self.cal[max(0, k - 80):k + 1]:
            vals = []
            for c in cs:
                s = self.S[c]
                i = s.at(dd)
                vals.append(s.r[i] if i is not None and i > 0 else np.nan)
            if not any(np.isnan(vals)):
                rows.append(vals)
        rows = rows[-60:]
        if len(rows) < 40:
            return None
        cov = np.cov(np.array(rows).T, ddof=1) * 252
        wv = np.array([w[c] for c in cs])
        return float(math.sqrt(max(wv @ np.atleast_2d(cov) @ wv, 0.0)))

    # ── 규칙 B: 변동성 조절 돌파 ──
    def rule_B(self, d, nav, m, held, orders, month_end):
        N, X, b = self.p["N"], self.p["X"], self.p["b"]
        out = list(orders)
        for c in sorted(held):
            s = self.S[c]
            i = s.at(d)
            if i is None:
                continue
            meta = self.pos_meta.get(c) or {}
            low = s.lo(i, X)
            atr = s.atrc(i)
            if (low is not None and s.px[i] < low) or (atr and meta and s.px[i] <= meta["peak"] - 3 * atr):
                out = [o for o in out if o["code"] != c]
                out.append({"code": c, "side": "sell", "qty": None, "dec": d, "why": "돌파 청산"})
        invested = sum(q * (self.close(c, d)[0] or 0) for c, q in held.items())
        room = m * nav - invested
        for c in U:
            if c in held:
                continue
            s = self.S.get(c)
            i = s.at(d) if s else None
            if i is None or i < max(ELIG, N):
                continue
            if s.px[i] > s.hi(i, N) and s.px[i] > s.sma(i, 200):
                sig = s.sd(i, 20) * math.sqrt(252)
                w = min(0.25, b / sig) * m if sig > 0 else 0.0
                v = min(w * nav, room)
                if v >= s.px[i]:
                    out.append({"code": c, "side": "buy", "value": v, "dec": d, "why": "돌파", "new": True})
                    room -= v
                else:
                    self.notes["entry_no_room"] += 1
        return out

    # ── 규칙 C: 추세 조건 단기 되돌림 ──
    def rule_C(self, d, nav, m, held, orders, month_end):
        k, H = self.p["k"], self.p["H"]
        out = list(orders)
        exiting = set()
        for c in sorted(held):
            s = self.S[c]
            i = s.at(d)
            if i is None:
                continue
            meta = self.pos_meta.get(c) or {}
            why = None
            if s.px[i] > s.sma(i, 5):
                why = "5일 평균 위로"
            elif meta and meta["days"] >= H:
                why = f"{H}일 보유"
            elif meta and s.px[i] <= meta["entry"] - 2.5 * meta["atr0"]:
                why = "손절(2.5 ATR)"
            elif s.px[i] < s.sma(i, 200):
                why = "200일 평균 아래"
            if why:
                exiting.add(c)
                out = [o for o in out if o["code"] != c]
                out.append({"code": c, "side": "sell", "qty": None, "dec": d, "why": why})
        slots = 3 - (len(held) - len(exiting))
        cand = []
        for c in U_C:
            if c in held:
                continue
            s = self.S.get(c)
            i = s.at(d) if s else None
            if i is None or i < ELIG:
                continue
            if not (s.px[i] > s.sma(i, 200) and s.sma(i, 50) > s.sma(i, 200)):
                continue
            sd = s.sd(i, 20)
            r3 = s.ret(i, 3)
            if sd and r3 is not None and r3 <= -k * sd * math.sqrt(3):
                cand.append((r3 / (sd * math.sqrt(3)), c, sd))
        cand.sort()
        for z, c, sd in cand[:max(slots, 0)]:
            w = min(0.30, 0.06 / (sd * math.sqrt(252))) * m
            out.append({"code": c, "side": "buy", "value": w * nav, "dec": d, "why": f"되돌림 z={z:.2f}", "new": True})
        if len(cand) > max(slots, 0):
            self.notes["entry_no_slot"] += len(cand) - max(slots, 0)
        return out


def run(base_data, exp, mult=1.0, cash=1e7, start="20120102", end=None, bump_after=None):
    cal, data = base_data
    rule, params = EXPERIMENTS[exp]
    codes = U_C if rule == "C" else U
    return Runner(cal, {c: data[c] for c in set(codes) | {CAL_CODE} if c in data}, rule, params, mult, cash, start, end, bump_after).run()
