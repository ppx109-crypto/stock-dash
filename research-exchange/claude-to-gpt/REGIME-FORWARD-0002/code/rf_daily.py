"""REGIME-FORWARD-0002 · 9월 고정규칙 1회 비교 — 통제 P4(현금 1천만 원 새 시작 · 250만 원 × 4) · PR #68 고정 후보.
python3 -E -P rf_daily.py <b2> <nrl-cache-rf.pkl> <출력> <rf_m15 출력(m15_signal.pkl · m15_eval.pkl)> <PR #68 nav_control_candidate.csv>

PR #68 rr_daily.py와 같은 엔진 · 같은 복제 규칙. 바꾼 것은 창뿐:
① 신호 경로: 2025-09-18 ~ 2026-09-30 한 번 이어 돈 통제 P4(PR #68 통제와 같은 시작 · 같은 입력) → E_t(t−1 마감까지 값만).
   2026-08-31까지 소계정 NAV · E가 PR #68 기록과 한 칸도 다르지 않을 때만 ②를 돌림(연속성 증명). 이 경로는 신호에만 쓰고 평가에 안 넣음.
② 9월 평가: 2026-09-01 현금 새 시작 통제 P4 · 그 보유를 E_t · k로 정수 비례 복제한 후보. 성과 · 거래 · 비용 집계는 9월만."""
import bisect
import csv
import json
import math
import pickle
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "rf_base", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41 그대로)", "exec"), G)
KN, CC, lab = G["KN"], G["CC"], G["lab"]
OUT, M15DIR, PR68 = Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
SLEEVE = 2_500_000.0
TOTAL = 4 * SLEEVE
SL = ("D1", "M15", "ETF", "BASKET")
DAYS_ALL = list(G["DAYS"])
print("달력", DAYS_ALL[0], DAYS_ALL[-1], len(DAYS_ALL), flush=True)
assert DAYS_ALL[-1] == "20260930", DAYS_ALL[-1]
assert "ahead" not in G["nrl"].inside[0]
LOG, CUR = {}, {"name": None}
RES = {}


def window(lo, hi):
    win = [d for d in DAYS_ALL if lo <= d <= hi]
    i0 = DAYS_ALL.index(win[0])
    G["DAYS"] = win
    G["DIDX"] = {d: i - i0 for i, d in enumerate(DAYS_ALL)}      # 창 기준 상대 번호(창 앞은 음수)
    return win


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


def natural(name, fn):
    CUR["name"] = name
    LOG[name] = []
    r = fn()
    CUR["name"] = None
    return r


def control(tag, win, m15):
    """통제 소계정 넷(현금 250만 원씩 · 창 첫날 시작)."""
    KN.Account = LogAccount
    nat = {}
    nat["D1x1"] = natural(tag + "D1x1", lambda: G["run_d1"]("next", 1.0))
    nat["D1"] = natural(tag + "D1", lambda: G["run_d1"]("next", 2.0))
    d1r = {d: (inv / nav if nav > 0 else 0.0) for d, nav, inv in nat["D1x1"]["nav"]}
    used = lambda d: 0.5 * d1r.get(win[G["DIDX"][d] - 1], 0.0) if G["DIDX"].get(d, 0) > 0 else 0.0   # 원 used_series와 같은 식
    nat["ETF"] = natural(tag + "ETF", lambda: G["run_etf"]("next", 2.0, used, "engine"))
    nat["BASKET"] = natural(tag + "BASKET", lambda: G["run_basket"]("next", 2.0))
    KN.Account = BaseAccount
    for k in ("D1", "ETF", "BASKET"):
        days = [d for d, _, _ in nat[k]["nav"]]
        assert days == win, (tag, k, days[:2], len(days))
    m15days = [d for d, _, _ in m15["nav"]]
    if m15days != win:
        raise SystemExit(f"BLOCKED: 15분봉 날짜행 다름 {tag} {m15days[:2]} {len(m15days)} vs {win[:2]} {len(win)}")
    navN = {k: [n for _, n, _ in nat[k]["nav"]] for k in ("D1", "ETF", "BASKET")}
    invN = {k: [x for _, _, x in nat[k]["nav"]] for k in ("D1", "ETF", "BASKET")}
    navN["M15"] = [n for _, n, _ in m15["nav"]]
    invN["M15"] = [x for _, _, x in m15["nav"]]
    p4 = [sum(navN[k][i] for k in SL) for i in range(len(win))]
    return nat, navN, invN, p4


# ── 노출 E_t: 통제 P4의 t−1 마감까지만(PR #68 그대로) ──
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


# ═════════ ① 신호 경로 ═════════
SWIN = window("20250918", "20260930")
MS = pickle.load(open(M15DIR / "m15_signal.pkl", "rb"))
NAT_S, navS, invS, P4S = control("S:", SWIN, MS)
ES = exposure(P4S)
print("신호 경로 P4", SWIN[0], SWIN[-1], len(SWIN), round(P4S[-1]), flush=True)
old = list(csv.DictReader(open(PR68, encoding="utf-8")))
cont = {"pr68_days": len(old), "first_day": old[0]["date"], "last_day": old[-1]["date"], "mismatch": []}
for i, row in enumerate(old):
    d = row["date"]
    if SWIN[i] != d:
        cont["mismatch"].append([d, "date", SWIN[i]])
        break
    mine = {"exposure": f"{ES[i]:.10f}", "control_nav": f"{P4S[i]:.2f}", **{f"control_{k}": f"{navS[k][i]:.2f}" for k in SL}}
    for k, v in mine.items():
        if row[k] != v:
            cont["mismatch"].append([d, k, row[k], v])
cont["identical_to_pr68"] = not cont["mismatch"]
cont["mismatch"] = cont["mismatch"][:20]
RES["continuity"] = cont
print("연속성", {k: v for k, v in cont.items() if k != "mismatch"}, cont["mismatch"][:3], flush=True)
OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "nav_signal_path.csv", "w", encoding="utf-8") as f:
    f.write("date,exposure_E_t,signal_P4," + ",".join(f"signal_{k}" for k in SL) + "\n")
    for i, d in enumerate(SWIN):
        f.write(f"{d},{ES[i]:.10f},{P4S[i]:.2f}," + ",".join(f"{navS[k][i]:.2f}" for k in SL) + "\n")
if not cont["identical_to_pr68"]:
    RES["verdict"] = "BLOCKED"
    RES["why"] = "신호 경로가 2026-08-31까지 PR #68 통제와 다름(연속성 증명 실패) → 9월 평가 안 함"
    (OUT / "rf_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("BLOCKED", RES["why"], flush=True)
    raise SystemExit(3)
ESIG = dict(zip(SWIN, ES))

# ═════════ ② 9월 평가(현금 새 시작) ═════════
WIN = window("20260901", "20260930")
cal = sorted(d for d in G["CL"]["005930"] if "20260901" <= d <= "20260930")
etf_ok = [d for d in WIN if all(G["ETF"].get(c, {}).get(d) for c in ("069500", "229200", "138230"))]
ME = pickle.load(open(M15DIR / "m15_eval.pkl", "rb"))
m15_days = [d for d, _, _ in ME["nav"]]
common = [d for d in cal if d in WIN and d in etf_ok and d in m15_days]
RES["common_days"] = {"calendar_sep": cal, "n_calendar": len(cal), "d1_window": len(WIN), "etf_complete": len(etf_ok), "m15_days": len(m15_days),
                      "common": len(common), "missing_by_sleeve": {"D1/BASKET": sorted(set(cal) - set(WIN)), "ETF": sorted(set(cal) - set(etf_ok)),
                                                                  "M15": sorted(set(cal) - set(m15_days))}}
print("9월 공통", RES["common_days"], flush=True)
if len(common) < 20 or common != cal:
    RES["verdict"] = "BLOCKED"
    RES["why"] = "NEEDS_DATA: 9월 공통 완전 거래일 20일 미만"
    (OUT / "rf_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    raise SystemExit(4)
NAT, navN, invN, P4 = control("E:", WIN, ME)
E = [ESIG[d] for d in WIN]
print("통제 P4(9월)", round(P4[-1]), {k: round(navN[k][-1]) for k in SL}, "· E", [round(x, 4) for x in E], flush=True)


# ── 후보: 통제 소계정 보유의 정수 비례 복제(PR #68 그대로) ──
def qty_path(log, keyday):
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


def last_px(c, d, prices):
    for x in reversed(WIN[:WIN.index(d) + 1]):
        p = prices(c, x)
        if p:
            return p
    return 0.0


ZERO = {k: {"days": set(), "code_days": 0} for k in SL}      # 통제는 들고 있는데 후보 목표가 0주인 날


def daily_sleeve(name, kind, prices, lockable):
    rep = Rep(kind)
    qn = qty_path(LOG["E:" + name], lambda t: t[:8])
    cur, navC, invC = {}, [], []
    notes = {"locked": 0, "no_price": 0}
    for i, d in enumerate(WIN):
        if d in qn:
            cur = qn[d]
        k = 1.0 if i == 0 else navC[-1] / navN[name][i - 1]
        dec = WIN[i - 1] if i else "start"
        codes = set(c for c, v in cur.items() if v > 0) | {p["code"] for p in rep.acc.pos.values()}
        tg = {c: math.floor(E[i] * k * cur.get(c, 0)) for c in codes}
        for c in codes:
            if cur.get(c, 0) > 0 and tg[c] == 0:
                ZERO[name]["days"].add(d)
                ZERO[name]["code_days"] += 1
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
        invC.append(inv)
    return rep, navC, invC, notes


stockp = lambda c, d: G["CL"].get(c, {}).get(d)
etfp = lambda c, d: G["ETF"].get(c, {}).get(d)
REP, navC, invC, RN = {}, {}, {}, {}
for name, kind, pr, lk in (("D1", "stock", stockp, True), ("ETF", "etf", etfp, False), ("BASKET", "stock", stockp, False)):
    REP[name], navC[name], invC[name], RN[name] = daily_sleeve(name, kind, pr, lk)
    print("후보", name, round(navC[name][-1]), "매매", len(REP[name].trades), RN[name], flush=True)

# ── 15분봉 후보: 통제 체결 봉 · 그날 그 종목 첫 봉 시가(PR #68 그대로) ──
rep = Rep("stock")
nlog = sorted(ME["log"], key=lambda x: x[0])
by_t = {}
for t, c, s, n, p in nlog:
    by_t.setdefault(t, []).append((c, s, n))
events = {}
for c, bl in ME["bars"].items():
    seen = set()
    for T, o, cl in bl:
        first = T[:8] not in seen
        seen.add(T[:8])
        events.setdefault(T, []).append((c, o, cl, first))
qn, last_close, navC["M15"], invC["M15"], day = {}, {}, [], [], None
dix = {d: i for i, d in enumerate(WIN)}


def close_day(dd):
    pf = lambda c: (last_close.get(c, 0.0), False)
    nav, inv = rep.acc.mtm(pf)
    rep.acc.check(pf)
    navC["M15"].append(nav)
    invC["M15"].append(inv)
    for c, v in qn.items():
        if v > 0 and rep.held(c) == 0:
            ZERO["M15"]["days"].add(dd)
            ZERO["M15"]["code_days"] += 1


by_day = {}
for T in sorted(events):
    assert T[:8] in dix, T
    by_day.setdefault(T[:8], []).append(T)
for d in WIN:                                            # 날마다 마감(그날 봉이 없어도 · 9월 통제 체결 0이면 봉 목록이 비어 있음)
    i = dix[d]
    for T in by_day.get(d, []):
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
    close_day(d)
REP["M15"] = rep
assert len(navC["M15"]) == len(WIN), len(navC["M15"])
print("후보 M15", round(navC["M15"][-1]), "매매", len(rep.trades), flush=True)
CAND = [sum(navC[k][i] for k in SL) for i in range(len(WIN))]


# ── 지표(9월만 · 시작 1천만 원) ──
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
    return {"end_won": nav[-1], "return_pct": (nav[-1] / TOTAL - 1) * 100, "MDD_pct": mdd * 100, "MDD_at": mdd_at,
            "worst_day_pct": r[wd] * 100, "worst_day_at": WIN[wd], "best_day_pct": max(r) * 100, "worst_month_pct": (mo[wm] - 1) * 100, "worst_month_at": wm,
            "day_breach_-15": sum(1 for x in r if x < -0.15 - 1e-12), "month_breach_-15": sum(1 for v in mo.values() if v - 1 < -0.15 - 1e-12),
            "daily_returns_pct": [x * 100 for x in r]}


def costs(accs):
    return {"cost_won": sum(a.tot["buy_cost"] + a.tot["sell_cost"] for a in accs),
            "notional_won": sum(a.tot["buy_notional"] + a.tot["sell_notional"] for a in accs)}


RES["window"] = [WIN[0], WIN[-1], len(WIN)]
RES["control"] = metrics(P4)
RES["candidate"] = metrics(CAND)
nat_accs_cost = sum(NAT[k]["tot"]["buy_cost"] + NAT[k]["tot"]["sell_cost"] for k in ("D1", "ETF", "BASKET")) + ME["tot"]["buy_cost"] + ME["tot"]["sell_cost"]
nat_notional = sum(NAT[k]["tot"]["buy_notional"] + NAT[k]["tot"]["sell_notional"] for k in ("D1", "ETF", "BASKET")) + ME["tot"]["buy_notional"] + ME["tot"]["sell_notional"]
ctrl_log = {k: LOG["E:" + k] if k != "M15" else ME["log"] for k in SL}
RES["control"].update({"cost_total_won": nat_accs_cost, "notional_won": nat_notional, "sleeve_end": {k: navN[k][-1] for k in SL},
                       "trades": {k: {"buy": sum(1 for x in ctrl_log[k] if x[2] == "buy"), "sell": sum(1 for x in ctrl_log[k] if x[2] == "sell")} for k in SL},
                       "max_gap": {k: [NAT[k]["tot"].get("max_gap_cash"), NAT[k]["tot"].get("max_gap_nav")] for k in ("D1", "ETF", "BASKET")}
                       | {"M15": [ME["tot"].get("max_gap_cash"), ME["tot"].get("max_gap_nav")]},
                       "checks": {k: NAT[k]["counts"].get("checks") for k in ("D1", "ETF", "BASKET")} | {"M15": ME["counts"].get("checks")}})
cc = costs([REP[k].acc for k in SL])
RES["candidate"].update({"cost_total_won": cc["cost_won"], "notional_won": cc["notional_won"], "sleeve_end": {k: navC[k][-1] for k in SL},
                         "trades": {k: {"buy": sum(1 for x in REP[k].trades if x[2] == "buy"), "sell": sum(1 for x in REP[k].trades if x[2] == "sell")} for k in SL},
                         "max_gap": {k: [REP[k].acc.tot.get("max_gap_cash"), REP[k].acc.tot.get("max_gap_nav")] for k in SL},
                         "checks": {k: REP[k].acc.counts.get("checks") for k in SL}, "notes": RN,
                         "unfilled": {k: {kk: v for kk, v in REP[k].acc.counts.items() if "unfilled" in kk or "reduced" in kk} for k in SL}})
# 실효 노출: (후보 투자액 ÷ 후보 NAV) ÷ (통제 투자액 ÷ 통제 NAV) — 통제 투자 > 0인 날 평균
eff = {}
for k in SL + ("ALL",):
    num, den, n = 0.0, 0.0, 0
    vals = []
    for i in range(len(WIN)):
        if k == "ALL":
            ci, cn = sum(invN[x][i] for x in SL), sum(navN[x][i] for x in SL)
            ki, kn = sum(invC[x][i] for x in SL), sum(navC[x][i] for x in SL)
        else:
            ci, cn, ki, kn = invN[k][i], navN[k][i], invC[k][i], navC[k][i]
        if ci > 0 and cn > 0 and kn > 0:
            vals.append((ki / kn) / (ci / cn))
    eff[k] = {"avg_effective_over_control": sum(vals) / len(vals) if vals else None, "days": len(vals)}
RES["exposure"] = {"E_sep": dict(zip(WIN, E)), "avg_E": sum(E) / len(E), "min": min(E), "max": max(E), "days_at_0.25": sum(1 for x in E if abs(x - 0.25) < 1e-12),
                   "E_on_0901_from_signal_path_to_0831": E[0], "effective": eff,
                   "zero_share": {k: {"days": len(ZERO[k]["days"]), "code_days": ZERO[k]["code_days"]} for k in SL},
                   "zero_share_any_sleeve_days": len(set().union(*(ZERO[k]["days"] for k in SL)))}
rc, rk = RES["control"]["daily_returns_pct"], RES["candidate"]["daily_returns_pct"]
dd = [b - a for a, b in zip(rc, rk)]
RES["difference"] = {"end_won_cand_minus_ctrl": CAND[-1] - P4[-1], "return_pp": RES["candidate"]["return_pct"] - RES["control"]["return_pct"],
                     "MDD_pp": RES["candidate"]["MDD_pct"] - RES["control"]["MDD_pct"],
                     "worst_day_pp": RES["candidate"]["worst_day_pct"] - RES["control"]["worst_day_pct"],
                     "cost_won": RES["candidate"]["cost_total_won"] - RES["control"]["cost_total_won"],
                     "daily_diff_mean_pp": statistics.mean(dd), "daily_diff_sd_pp": statistics.stdev(dd),
                     "daily_diff_t": statistics.mean(dd) / (statistics.stdev(dd) / math.sqrt(len(dd))) if statistics.stdev(dd) > 0 else None,
                     "ctrl_daily_sd_pp": statistics.stdev(rc), "cand_daily_sd_pp": statistics.stdev(rk), "n_days": len(dd)}
RES["diagnostics"] = {"d1_picks_rows_by_day_sep": {d: len(G["PICKS"].get(d, [])) for d in WIN},
                      "signal_path_fills_sep": {k: sum(1 for x in (LOG["S:" + k] if k != "M15" else MS["log"]) if str(x[0])[:8] >= "20260901") for k in SL},
                      "signal_path_sep_return_pct": (P4S[-1] / P4S[SWIN.index("20260831")] - 1) * 100,
                      "signal_path_sleeve_0831_0930": {k: [navS[k][SWIN.index("20260831")], navS[k][-1]] for k in SL},
                      "control_E_D1x1_fills": len(LOG["E:D1x1"])}
c = RES["candidate"]
inv_ok = all(v[0] is not None and v[0] <= 1.0 and v[1] <= 1.0 for v in c["max_gap"].values()) and all((x or 0) > 0 for x in c["checks"].values())
RES["criteria_disclosed(완화 없음)"] = {"conservation": inv_ok, "day_ok": c["day_breach_-15"] == 0, "month_ok": c["month_breach_-15"] == 0,
                                       "mdd_ok": c["MDD_pct"] >= -15.0, "end_gt_10m": c["end_won"] > TOTAL}
RES["verdict"] = "READY"
RES["label"] = "INTERIM_FORWARD_DIAGNOSTIC(9월 USED · 수익성 확정 아님 · PAPER_VALIDATION_READY 아님)"
with open(OUT / "nav_sep_control_candidate.csv", "w", encoding="utf-8") as f:
    f.write("date,exposure_E_t,control_nav," + ",".join(f"control_{k}" for k in SL) + ",candidate_nav," + ",".join(f"cand_{k}" for k in SL) + "\n")
    for i, d in enumerate(WIN):
        f.write(f"{d},{E[i]:.10f},{P4[i]:.2f}," + ",".join(f"{navN[k][i]:.2f}" for k in SL) + f",{CAND[i]:.2f}," +
                ",".join(f"{navC[k][i]:.2f}" for k in SL) + "\n")
full = {"control": {k: [list(x) for x in ctrl_log[k]] for k in SL}, "candidate": {k: [list(x) for x in REP[k].trades] for k in SL}}
raw = json.dumps(full, ensure_ascii=False, sort_keys=True).encode("utf-8")
(OUT / "trades_local_only.json").write_bytes(raw)
import hashlib  # noqa: E402
RES["trades_local_only_sha256"] = hashlib.sha256(raw).hexdigest()
for k in ("control", "candidate"):
    RES[k]["daily_returns_pct"] = RES[k].pop("daily_returns_pct")
(OUT / "rf_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("통제", {k: v for k, v in RES["control"].items() if k != "daily_returns_pct"}, flush=True)
print("후보", {k: v for k, v in RES["candidate"].items() if k not in ("daily_returns_pct", "notes", "unfilled")}, flush=True)
print("노출", {k: v for k, v in RES["exposure"].items() if k != "E_sep"}, flush=True)
print("차이", RES["difference"], flush=True)
print("판정", RES["criteria_disclosed(완화 없음)"], RES["verdict"], flush=True)
print("끝", flush=True)
