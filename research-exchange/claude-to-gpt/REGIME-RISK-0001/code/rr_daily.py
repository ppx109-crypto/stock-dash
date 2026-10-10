"""REGIME-RISK-0001 · 통제 P4(현금 시작 · 정수 · 250만 원 × 4) · 후보(20일 변동성 목표 20% · 25~100% · 60일 SMA 아래 25%) 2판.
python3 -E -P rr_daily.py <b2> <nrl-cache.pkl> <출력(m15_natural.pkl 있음)> <PR66 blend_P4.csv>
PR #41 daily_exec.py 앞부분을 그대로 불러 D1 · 빈칸 · 바구니 통제 소계정을 돌리고(창 · 250만 원), 후보는 통제 소계정 보유의 정수 비례 복제."""
import bisect
import csv
import json
import math
import pickle
import statistics
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "rr_base", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41 그대로)", "exec"), G)
KN, CC, lab = G["KN"], G["CC"], G["lab"]
OUT, BLEND = Path(sys.argv[3]), Path(sys.argv[4])
SLEEVE = 2_500_000.0
TOTAL = 4 * SLEEVE
LO, HI = "20250918", "20260831"
DAYS_ALL = list(G["DAYS"])
WIN = [d for d in DAYS_ALL if LO <= d <= HI]
i0 = DAYS_ALL.index(WIN[0])
G["DAYS"] = WIN
G["DIDX"] = {d: i - i0 for i, d in enumerate(DAYS_ALL)}      # 창 기준 상대 번호(창 앞은 음수)
LOG = {}
CUR = {"name": None}


class LogAccount(KN.Account):
    def __init__(self, costs, cash=None):
        super().__init__(costs, SLEEVE)

    def buy(self, pid, code, price, day, decision_at, value=None, qty=None, slots=None, tag=""):
        q = super().buy(pid, code, price, day, decision_at, value=value, qty=qty, slots=slots, tag=tag)
        if q and CUR["name"]:
            LOG[CUR["name"]].append((str(day), code, "buy", q, price))
        return q

    def sell(self, pid, price, day, decision_at, qty=None, reason=""):
        code = self.pos[pid]["code"] if pid in self.pos else None
        q = super().sell(pid, price, day, decision_at, qty=qty, reason=reason)
        if q and CUR["name"]:
            LOG[CUR["name"]].append((str(day), code, "sell", q, price))
        return q


BaseAccount = KN.Account
KN.Account = LogAccount


def natural(name, fn):
    CUR["name"] = name
    LOG[name] = []
    r = fn()
    CUR["name"] = None
    return r


NAT = {}
NAT["D1x1"] = natural("D1x1", lambda: G["run_d1"]("next", 1.0))
NAT["D1"] = natural("D1", lambda: G["run_d1"]("next", 2.0))
d1r = {d: (inv / nav if nav > 0 else 0.0) for d, nav, inv in NAT["D1x1"]["nav"]}
used = lambda d: 0.5 * d1r.get(WIN[G["DIDX"][d] - 1], 0.0) if G["DIDX"].get(d, 0) > 0 else 0.0   # 원 used_series와 같은 식
NAT["ETF"] = natural("ETF", lambda: G["run_etf"]("next", 2.0, used, "engine"))
NAT["BASKET"] = natural("BASKET", lambda: G["run_basket"]("next", 2.0))
KN.Account = BaseAccount
M = pickle.load(open(OUT / "m15_natural.pkl", "rb"))
for k in ("D1", "ETF", "BASKET"):
    days = [d for d, _, _ in NAT[k]["nav"]]
    assert days == WIN, (k, days[:2], len(days))
m15days = [d for d, _, _ in M["nav"]]
if m15days != WIN:
    raise SystemExit(f"BLOCKED: 15분봉 날짜행 다름 {m15days[:2]} {len(m15days)} vs {WIN[:2]} {len(WIN)}")
navN = {k: [n for _, n, _ in NAT[k]["nav"]] for k in ("D1", "ETF", "BASKET")}
navN["M15"] = [n for _, n, _ in M["nav"]]
SL = ("D1", "M15", "ETF", "BASKET")
P4 = [sum(navN[k][i] for k in SL) for i in range(len(WIN))]
print("통제 P4", round(P4[-1]), {k: round(navN[k][-1]) for k in SL}, flush=True)


# ── 노출 E_t: 통제 P4의 t−1 마감까지만 ──
def exposure(navs):
    seg = [TOTAL] + navs
    r = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    E = []
    for t in range(len(navs)):
        past_r, past_n = r[:t], navs[:t]
        assert len(past_r) == t and len(past_n) == t           # t일 값 쓰지 않음
        ev = 1.0 if len(past_r) < 20 else min(1.0, max(0.25, 0.20 / (statistics.stdev(past_r[-20:]) * math.sqrt(252))))
        tc = 1.0 if len(past_n) < 60 else (1.0 if past_n[-1] >= sum(past_n[-60:]) / 60 else 0.25)
        E.append(min(ev, tc))
    return E


E = exposure(P4)


# ── 후보: 통제 소계정 보유의 정수 비례 복제 ──
def qty_path(log, keyday):
    """통제 소계정의 시각별 종목 수량 변화 → 날(또는 봉) 끝 수량."""
    q, out = {}, {}
    for t, c, s, n, _ in sorted(log, key=lambda x: x[0]):
        q[c] = q.get(c, 0) + (n if s == "buy" else -n)
        out[keyday(t)] = dict(q)
    return out


class Rep:
    def __init__(self, kind):
        self.acc = KN.Account(KN.Costs(CC, G["market_of"], 2.0, kind), SLEEVE)
        self.trades, self.seq = [], 0

    def held(self, c):
        return sum(p["qty"] for p in self.acc.pos.values() if p["code"] == c)

    def trade_to(self, c, target, price, when, dec, side_only=None, lock=None):
        h = self.held(c)
        if target < h and side_only in (None, "sell"):
            if lock and lock(-1):
                return "lock"
            left = h - target
            for pid in sorted(self.acc.pids_of(c)):
                if left <= 0:
                    break
                q = min(left, self.acc.pos[pid]["qty"])
                self.acc.sell(pid, price, when, dec, qty=q, reason="노출 맞춤")
                self.trades.append((when, c, "sell", q, price))
                left -= q
        elif target > h and side_only in (None, "buy"):
            if lock and lock(1):
                return "lock"
            self.seq += 1
            got = self.acc.buy(f"{c}:{when}:{self.seq}", c, price, when, dec, qty=target - h, tag="노출 맞춤")
            if got:
                self.trades.append((when, c, "buy", got, price))
        return None


def daily_sleeve(name, kind, prices, lockable):
    rep = Rep(kind)
    qn = qty_path(LOG[name], lambda t: t[:8])
    cur, navC = {}, []
    notes = {"locked": 0, "no_price": 0}
    for i, d in enumerate(WIN):
        if d in qn:
            cur = qn[d]
        k = 1.0 if i == 0 else navC[-1] / navN[name][i - 1]
        dec = WIN[i - 1] if i else "start"
        codes = set(c for c, v in cur.items() if v > 0) | {p["code"] for p in rep.acc.pos.values()}
        tg = {c: math.floor(E[i] * k * cur.get(c, 0)) for c in codes}
        for side in ("sell", "buy"):
            for c in sorted(codes):
                px = prices(c, d)
                if not px:
                    notes["no_price"] += 1
                    continue
                lock = None
                if lockable:
                    ln, j = G["LANE"].get(c), G["IDXOF"].get(c, {}).get(d)
                    lock = (lambda s, ln=ln, j=j: ln is not None and j is not None and lab.locked(ln["closes"], ln["날"], j, s))
                if rep.trade_to(c, tg[c], px, d, dec, side_only=side, lock=lock) == "lock":
                    notes["locked"] += 1
        pf = lambda c, d=d: ((prices(c, d), False) if prices(c, d) else (last_px(c, d, prices), True))
        nav, inv = rep.acc.mtm(pf)
        rep.acc.check(pf)
        navC.append(nav)
    return rep, navC, notes


def last_px(c, d, prices):
    for x in reversed(WIN[:WIN.index(d) + 1]):
        p = prices(c, x)
        if p:
            return p
    return 0.0


stockp = lambda c, d: G["CL"].get(c, {}).get(d)
etfp = lambda c, d: G["ETF"].get(c, {}).get(d)
REP, navC, RN = {}, {}, {}
for name, kind, pr, lk in (("D1", "stock", stockp, True), ("ETF", "etf", etfp, False), ("BASKET", "stock", stockp, False)):
    REP[name], navC[name], RN[name] = daily_sleeve(name, kind, pr, lk)
    print("후보", name, round(navC[name][-1]), "매매", len(REP[name].trades), RN[name], flush=True)

# ── 15분봉 후보: 통제 체결 봉 · 그날 그 종목 첫 봉 시가 ──
rep = Rep("stock")
nlog = sorted(M["log"], key=lambda x: x[0])
by_t = {}
for t, c, s, n, p in nlog:
    by_t.setdefault(t, []).append((c, s, n))
events = {}
for c, bl in M["bars"].items():
    seen = set()
    for T, o, cl in bl:
        first = T[:8] not in seen
        seen.add(T[:8])
        events.setdefault(T, []).append((c, o, cl, first))
qn, last_close, navC["M15"], day = {}, {}, [], None
dix = {d: i for i, d in enumerate(WIN)}


def close_day(dd):
    pf = lambda c: (last_close.get(c, 0.0), False)
    nav, inv = rep.acc.mtm(pf)
    rep.acc.check(pf)
    navC["M15"].append(nav)


for T in sorted(events):
    d = T[:8]
    if d != day:
        if day is not None and day in dix:
            close_day(day)
        day = d
    if d not in dix:                                     # 창 앞 2025-09-17 봉: 통제 엔진도 체결 없음(첫 NAV 날 09-18)
        for c, o, cl, first in events[T]:
            last_close[c] = cl
        assert T not in by_t
        continue
    i = dix[d]
    k = 1.0 if i == 0 else navC["M15"][i - 1] / navN["M15"][i - 1]
    for c, s, n in by_t.get(T, []):
        qn[c] = qn.get(c, 0) + (n if s == "buy" else -n)
    traded = {c for c, _, _ in by_t.get(T, [])}
    acts = [(c, o) for c, o, cl, first in events[T] if (c in traded or (first and (qn.get(c, 0) > 0 or rep.held(c) > 0)))]
    for side in ("sell", "buy"):
        for c, o in sorted(acts):
            rep.trade_to(c, math.floor(E[i] * k * qn.get(c, 0)), o, T, WIN[i - 1] if i else "start", side_only=side)
    for c, o, cl, first in events[T]:
        last_close[c] = cl
close_day(day)
REP["M15"] = rep
assert len(navC["M15"]) == len(WIN), len(navC["M15"])
print("후보 M15", round(navC["M15"][-1]), "매매", len(rep.trades), flush=True)
CAND = [sum(navC[k][i] for k in SL) for i in range(len(WIN))]


# ── 지표 ──
def metrics(nav):
    seg = [TOTAL] + nav
    r = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    peak, mdd, mdd_at = TOTAL, 0.0, None
    for d, v in zip([None] + WIN, seg):
        peak = max(peak, v)
        if v / peak - 1 < mdd:
            mdd, mdd_at = v / peak - 1, d
    wd = min(range(len(r)), key=lambda i: r[i])
    mo = {}
    for d, x in zip(WIN, r):
        mo[d[:6]] = mo.get(d[:6], 1.0) * (1 + x)
    wm = min(mo, key=mo.get)
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    yrs = (D(WIN[-1]) - D(WIN[0])).days / 365.25
    return {"end_won": nav[-1], "CAGR_pct": ((nav[-1] / TOTAL) ** (1 / yrs) - 1) * 100, "MDD_pct": mdd * 100, "MDD_at": mdd_at,
            "worst_day_pct": r[wd] * 100, "worst_day_at": WIN[wd], "worst_month_pct": (mo[wm] - 1) * 100, "worst_month_at": wm,
            "day_breach_-15": sum(1 for x in r if x < -0.15 - 1e-12), "month_breach_-15": sum(1 for v in mo.values() if v - 1 < -0.15 - 1e-12),
            "months_pct": {k: (v - 1) * 100 for k, v in mo.items()}}


def cost_turn(accs, navs):
    cost = sum(a.tot["buy_cost"] + a.tot["sell_cost"] for a in accs)
    notional = sum(a.tot["buy_notional"] + a.tot["sell_notional"] for a in accs)
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    return cost, notional / 2 / (sum(navs) / len(navs)) / ((D(WIN[-1]) - D(WIN[0])).days / 365.25)


RES = {"window": [WIN[0], WIN[-1], len(WIN)], "control": metrics(P4), "candidate": metrics(CAND)}
nat_cost = sum(NAT[k]["tot"]["buy_cost"] + NAT[k]["tot"]["sell_cost"] for k in ("D1", "ETF", "BASKET")) + M["tot"]["buy_cost"] + M["tot"]["sell_cost"]
RES["control"]["cost_total_won"] = nat_cost
RES["control"]["sleeve_end"] = {k: navN[k][-1] for k in SL}
cc, ct = cost_turn([REP[k].acc for k in SL], CAND)
RES["candidate"].update({"cost_total_won": cc, "turnover_per_year": ct, "sleeve_end": {k: navC[k][-1] for k in SL},
                         "trades": {k: {"buy": sum(1 for x in REP[k].trades if x[2] == "buy"), "sell": sum(1 for x in REP[k].trades if x[2] == "sell")} for k in SL},
                         "max_gap": {k: [REP[k].acc.tot.get("max_gap_cash"), REP[k].acc.tot.get("max_gap_nav")] for k in SL},
                         "checks": {k: REP[k].acc.counts.get("checks") for k in SL}, "notes": RN,
                         "unfilled": {k: {kk: v for kk, v in REP[k].acc.counts.items() if "unfilled" in kk or "reduced" in kk} for k in SL}})
chg = [i for i in range(1, len(E)) if abs(E[i] - E[i - 1]) > 1e-12]
RES["exposure"] = {"avg": sum(E) / len(E), "min": min(E), "max": max(E), "changes": len(chg), "sum_abs_delta": sum(abs(E[i] - E[i - 1]) for i in range(1, len(E))),
                   "days_at_0.25": sum(1 for x in E if abs(x - 0.25) < 1e-12)}


# ── GPT 선별값과 비교 ──
def screen(base_navs, base0):
    seg = [base0] + base_navs
    r = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    e = exposure_from(base_navs, base0)
    out, v = [], 1.0
    for x, ee in zip(r, e):
        v *= 1 + ee * x
        out.append(v)
    return out, e


def exposure_from(navs, base0):
    seg = [base0] + navs
    r = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    E2 = []
    for t in range(len(navs)):
        ev = 1.0 if t < 20 else min(1.0, max(0.25, 0.20 / (statistics.stdev(r[t - 20:t]) * math.sqrt(252))))
        tc = 1.0 if t < 60 else (1.0 if navs[t - 1] >= sum(navs[t - 60:t]) / 60 else 0.25)
        E2.append(min(ev, tc))
    return E2


b66 = {r["date"]: float(r["nav_multiple"]) for r in csv.DictReader(open(BLEND, encoding="utf-8"))}
assert sorted(b66) == WIN
s66, e66 = screen([b66[d] for d in WIN], 1.0)
sF, eF = screen([x / TOTAL for x in P4], 1.0)
assert all(abs(a - b) < 1e-12 for a, b in zip(eF, E))
cand_n = [x / TOTAL for x in CAND]
first = lambda a, b, tol: next((WIN[i] for i in range(len(WIN)) if abs(a[i] - b[i]) > tol), None)
RES["vs_gpt_screen"] = {"gpt_screen_end_multiple(PR66 P4 기반)": s66[-1], "gpt_screen_json": 1.6161818289727041,
                        "screen_matches_gpt_json": abs(s66[-1] - 1.6161818289727041) < 1e-9,
                        "candidate_end_multiple": cand_n[-1], "diff_vs_pr66_screen": cand_n[-1] - s66[-1],
                        "first_diff_date_vs_pr66_screen(1e-6)": first(cand_n, s66, 1e-6),
                        "screen_on_cash_start_P4_end_multiple": sF[-1], "diff_vs_cash_start_screen": cand_n[-1] - sF[-1],
                        "first_diff_date_vs_cash_start_screen(1e-6)": first(cand_n, sF, 1e-6),
                        "exposure_same_days_pr66_vs_cash_start": sum(1 for a, b in zip(e66, E) if abs(a - b) < 1e-12)}
RES["pr66_P4_end_multiple"] = b66[WIN[-1]]
c = RES["candidate"]
inv_ok = all(v[0] is not None and v[0] <= 1.0 and v[1] <= 1.0 for v in c["max_gap"].values()) and all((x or 0) > 0 for x in c["checks"].values())
crit = {"inputs_timing_conservation": inv_ok, "day_ok": c["day_breach_-15"] == 0, "month_ok": c["month_breach_-15"] == 0, "mdd_ok": c["MDD_pct"] >= -15.0,
        "end_gt_10m": c["end_won"] > TOTAL}
RES["criteria"] = crit
RES["verdict"] = "TRAIN_CANDIDATE_LOCKED" if all(crit.values()) else "AXIS_ENDED"
with open(OUT / "nav_control_candidate.csv", "w", encoding="utf-8") as f:
    f.write("date,exposure,control_nav," + ",".join(f"control_{k}" for k in SL) + ",candidate_nav," + ",".join(f"cand_{k}" for k in SL) +
            ",screen_pr66,screen_cash_start\n")
    for i, d in enumerate(WIN):
        f.write(f"{d},{E[i]:.10f},{P4[i]:.2f}," + ",".join(f"{navN[k][i]:.2f}" for k in SL) + f",{CAND[i]:.2f}," +
                ",".join(f"{navC[k][i]:.2f}" for k in SL) + f",{s66[i]:.10f},{sF[i]:.10f}\n")
json.dump({k: [list(x) for x in REP[k].trades] for k in SL}, open(OUT / "candidate_trades.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump({k: [list(x) for x in (LOG[k] if k != "M15" else M["log"])] for k in SL}, open(OUT / "control_trades.json", "w", encoding="utf-8"), ensure_ascii=False)
for k in ("control", "candidate"):
    RES[k]["months_pct"] = RES[k].pop("months_pct")
(OUT / "rr_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("통제", {k: v for k, v in RES["control"].items() if k != "months_pct"}, flush=True)
print("후보", {k: v for k, v in RES["candidate"].items() if k not in ("months_pct", "notes", "unfilled")}, flush=True)
print("노출", RES["exposure"], flush=True)
print("GPT 대조", RES["vs_gpt_screen"], flush=True)
print("판정", crit, RES["verdict"], flush=True)
print("끝", flush=True)
