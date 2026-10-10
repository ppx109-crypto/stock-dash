"""BASELINE-M15-TIMING-0001 · 15분봉 복제 주문 시점 고정(완료 봉 뒤 잠금 → 그 종목 다음 봉 시가 체결) · 합성 검사 · Train 1회.
python3 -E -P et_m15.py <b2> <옛 nrl-cache.pkl> <출력> <PR68 evidence 폴더> <PR68 m15_natural.pkl> <PR76 출력 폴더(nav csv · fixed_local_only.json)> [--checks-only]

- 통제 · 옛 후보 · PR #76 일봉 고침은 다시 돌리지 않음(저장 체결 · NAV만 읽고 비용식으로 재구성).
- 고친 15분봉 후보(옛 계약과 행동 시점은 같고 한 봉 늦춤):
  · 통제가 봉 T 시가에 체결하면, 봉 T가 끝난 뒤(종가까지 확정) 통제 보유_T · E_d · k_d(=전날 후보/통제 15분봉 NAV)로 목표를 잠그고
    그 종목의 다음 봉 시가에 그 수량으로 체결(파는 것 먼저). 체결 봉 가격 · 체결 봉 통제 수량으로 다시 맞추지 않음.
  · 날 마감 뒤(그날 마지막 봉까지 확정 · 그날 NAV 확정): 통제 보유 · E_{d+1} · k_{d+1}로 보유/통제 보유 종목 목표를 잠그고 다음 날 그 종목 첫 봉 시가에 체결
    (옛 계약의 '그날 첫 봉 맞춤'과 같은 자리).
  · 잠근 목표는 그 종목의 다음 봉에서 한 번 실행. 그 사이 새로 잠그면 새 것이 앞 것을 대신함. 현금 부족은 장부가 줄임(건수).
  · 봉 시각: 0900 ~ 1515(15분 · 26개 · 점심 쉼 없음). 1515 봉 뒤 잠근 목표는 다음 거래일 첫 봉 시가로.
  · 창 첫날(2025-09-18) 첫 통제 체결 봉 전에는 주문 0. 창 앞 날(2025-09-17) 봉은 종가 기록만.
네트워크 막음 · 키 환경변수 지움 · 운영 파일 안 고침."""
import csv
import hashlib
import json
import math
import pickle
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKS_ONLY = "--checks-only" in sys.argv
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "et_m15", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41 그대로 · 자료 읽기만)", "exec"), G)
KN, CC = G["KN"], G["CC"]
OUT, IN, M15PKL, P76 = Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]), Path(sys.argv[6])
SLEEVE, TOTAL = 2_500_000.0, 10_000_000.0
LO, HI = "20250918", "20260331"
SL = ("D1", "M15", "ETF", "BASKET")
DAILY = ("D1", "ETF", "BASKET")


# ═════════ 고친 계약(15분봉 소계정) ═════════
def replay_m15(win, events, fills, E, navN, costs, cash=SLEEVE):
    """events: {T: [(c, o, cl)]} · fills: {T: [(c, ±n)]}(통제 체결 · 그 봉 시가) · E[d] · navN[d](통제 15분봉 NAV)."""
    acc = KN.Account(costs, cash)
    dix = {d: i for i, d in enumerate(win)}
    held = lambda c: sum(p["qty"] for p in acc.pos.values() if p["code"] == c)
    qn, last_close, pending = {}, {}, {}
    navC, cashC, trades, locks, notes, seq = [], [], [], [], Counter(), 0
    day = None

    def k_of(d):
        i = dix[d]
        return 1.0 if i == 0 else navC[i - 1] / navN[win[i - 1]]

    def lock(c, T, d_exec):
        tgt = math.floor(E[d_exec] * k_of(d_exec) * qn.get(c, 0))
        pending[c] = (tgt, T)
        locks.append({"locked_at": T, "code": c, "for_day": d_exec, "target": tgt, "executed_at": None})

    def close_day(d):
        pf = lambda c: (last_close.get(c, 0.0), False)
        nav, _inv = acc.mtm(pf)
        acc.check(pf)
        navC.append(nav)
        cashC.append(acc.cash)

    for T in sorted(events):
        d = T[:8]
        if d != day:
            if day is not None and day in dix:
                close_day(day)
                nxt = dix[day] + 1
                if nxt < len(win):                                # 날 마감 뒤 잠금 → 다음 날 첫 봉
                    for c in sorted({c for c, v in qn.items() if v > 0} | {p["code"] for p in acc.pos.values()}):
                        lock(c, day + "9999", win[nxt])
            day = d
        if d not in dix:                                          # 창 앞 날: 종가만 기록
            for c, o, cl in events[T]:
                last_close[c] = cl
            assert T not in fills
            continue
        here = {c: o for c, o, cl in events[T]}
        todo = sorted(c for c in pending if c in here and pending[c][1] < T)
        for side in ("sell", "buy"):                              # ① 잠근 목표를 이 봉 시가에 체결
            for c in todo:
                tgt, lt = pending[c]
                h, o = held(c), here[c]
                if not ((side == "sell" and tgt < h) or (side == "buy" and tgt > h)):
                    continue
                if not o:
                    notes["no_price"] += 1
                    continue
                if side == "sell":
                    left, sold = h - tgt, 0
                    for pid in sorted(acc.pids_of(c)):
                        if left <= 0:
                            break
                        q = min(left, acc.pos[pid]["qty"])
                        acc.sell(pid, o, T, lt, qty=q, reason="노출 맞춤(다음 봉)")
                        sold += q
                        left -= q
                    trades.append((T, c, "sell", sold))
                else:
                    seq += 1
                    got = acc.buy(f"{c}:{T}:{seq}", c, o, T, lt, qty=tgt - h, tag="노출 맞춤(다음 봉)")
                    if got < tgt - h:
                        notes["buy_reduced_or_unfilled"] += 1
                    if got:
                        trades.append((T, c, "buy", got))
        for c in todo:
            for x in reversed(locks):
                if x["code"] == c and x["locked_at"] == pending[c][1]:
                    x["executed_at"] = T
                    break
            del pending[c]
        for c, o, cl in events[T]:                                # ② 봉이 끝남: 종가 · 통제 체결 결과 확정
            last_close[c] = cl
        for c, n in fills.get(T, []):
            qn[c] = qn.get(c, 0) + n
            assert qn[c] >= 0
        for c in sorted({c for c, _ in fills.get(T, [])}):        # ③ 완료 봉 뒤 잠금 → 그 종목 다음 봉
            lock(c, T, d)
    close_day(day)
    dup = [x for x, n in Counter((t[0], t[1], t[2]) for t in trades).items() if n > 1]
    return {"acc": acc, "nav": navC, "cash": cashC, "trades": trades, "locks": locks, "notes": dict(notes), "dup": dup, "pending_end": len(pending)}


def old_m15(win, events, fills, E, navN, costs, cash=SLEEVE):
    """PR #68 rr_daily.py L212-234 옛 계약(비교용 · 합성에서만): 통제 체결 봉 · 첫 봉에서 같은 봉 시가로 목표."""
    acc = KN.Account(costs, cash)
    dix = {d: i for i, d in enumerate(win)}
    held = lambda c: sum(p["qty"] for p in acc.pos.values() if p["code"] == c)
    qn, out, navC, last_close, seen, day = {}, {}, [], {}, set(), None
    for T in sorted(events):
        d = T[:8]
        if d != day:
            if day is not None:
                navC.append(acc.mtm(lambda c: (last_close.get(c, 0.0), False))[0])
            day = d
        i = dix[d]
        k = 1.0 if i == 0 else navC[i - 1] / navN[win[i - 1]]
        for c, n in fills.get(T, []):
            qn[c] = qn.get(c, 0) + n
        traded = {c for c, _ in fills.get(T, [])}
        for c, o, cl in events[T]:
            first = (d, c) not in seen
            seen.add((d, c))
            if c in traded or (first and (qn.get(c, 0) > 0 or held(c) > 0)):
                out[(T, c)] = math.floor(E[d] * k * qn.get(c, 0))
            last_close[c] = cl
    return out


# ═════════ 합성 검사 ═════════
class Flat:
    def rate(self, side, code, day, notional):
        return 0.001, {}


def synthetic():
    win = ["20250102", "20250103", "20250106"]
    times = ["0900", "0915", "0930", "1515"]
    base = {"A": [100, 101, 102, 103, 104, 103, 102, 101, 100, 101, 102, 103],
            "B": [50, 51, 52, 53, 54, None, 56, 57, 58, 57, 56, 55]}
    E = {"20250102": 1.0, "20250103": 0.5, "20250106": 1.0}

    def world(pert=None, qpert=None):
        ev, fl = {}, {}
        k = 0
        for d in win:
            for tt in times:
                T = d + tt
                ev[T] = [(c, float(v[k]), float(v[k])) for c, v in base.items() if v[k] is not None]
                k += 1
        if pert:
            ev[pert[0]] = [(c, o * pert[2] if c == pert[1] else o, cl) for c, o, cl in ev[pert[0]]]
        o_of = lambda T, c: next(o for cc, o, _ in ev[T] if cc == c)
        # 통제: 봉 시가 체결 · 수량 = floor(금액 ÷ 그 봉 시가)(PR #68 rr_m15.py L186-188과 같은 의존)
        plan = [("20250102" "0915", "A", 300_000), ("20250102" "1515", "A", 200_000), ("20250103" "0900", "B", 200_000), ("20250103" "0930", "A", -1)]
        q = {}
        for T, c, v in plan:
            n = -q.get(c, 0) if v < 0 else math.floor(v / o_of(T, c))
            q[c] = q.get(c, 0) + n
            fl.setdefault(T, []).append((c, n))
        if qpert:
            fl.setdefault(qpert[0], []).append((qpert[1], qpert[2]))
        navN = {d: 1_000_000.0 for d in win}
        return ev, fl, navN

    res = {}
    ev0, fl0, nn0 = world()
    r0 = replay_m15(win, ev0, fl0, E, nn0, Flat(), cash=1_000_000)
    o0 = old_m15(win, ev0, fl0, E, nn0, Flat(), cash=1_000_000)
    TF, TX = "20250102" "0915", "20250102" "0930"                # A 통제 체결 봉(0915) · 고친 계약이 실행하는 봉(0930)
    for tag, pert_new, pert_old in (("체결 봉 시가 +10%(A)", dict(pert=(TX, "A", 1.10)), dict(pert=(TF, "A", 1.10))),
                                    ("체결 봉 통제 수량 +9(A)", dict(qpert=(TX, "A", 9)), dict(qpert=(TF, "A", 9)))):
        wn, wo = world(**pert_new), world(**pert_old)
        r1 = replay_m15(win, wn[0], wn[1], E, wn[2], Flat(), cash=1_000_000)
        o1 = old_m15(win, wo[0], wo[1], E, wo[2], Flat(), cash=1_000_000)
        before = lambda r: [dict(x, executed_at=None) for x in r["locks"] if x["locked_at"] < TX]
        res["실행 봉 " + tag] = {"new_locks_before_exec_bar_same": before(r0) == before(r1),
                                "new_fill_qty_at_exec_bar_same": [x for x in r0["trades"] if x[0] == TX] == [x for x in r1["trades"] if x[0] == TX],
                                "new_exec_bar_has_fill": any(x[0] == TX for x in r0["trades"]),
                                "old_target_at_control_fill_bar_same": o0.get((TF, "A")) == o1.get((TF, "A"))}
    first_fill = min(T for T in fl0)
    res["첫 통제 체결 봉까지 주문 0"] = {"trades_at_or_before_first_control_fill": sum(1 for x in r0["trades"] if x[0] <= first_fill)}
    res["장 경계(1515 체결 → 다음 날 첫 봉)"] = {
        "A_lock_after_1515": [x["for_day"] for x in r0["locks"] if x["locked_at"] == "202501021515" and x["code"] == "A"],
        "executed_at": [x["executed_at"] for x in r0["locks"] if x["locked_at"] in ("202501021515", "202501029999") and x["code"] == "A"],
        "no_trade_same_day_after_1515": not any(x[0] > "202501021515" and x[0] < "202501030900" for x in r0["trades"])}
    res["보존 · 정수 · 중복 · 음수 현금"] = {"checks": r0["acc"].counts.get("checks"), "max_gap": [r0["acc"].tot.get("max_gap_cash"), r0["acc"].tot.get("max_gap_nav")],
                                    "all_int": all(isinstance(x[3], int) for x in r0["trades"]), "dup": r0["dup"], "min_cash": min(r0["cash"])}
    res["가격 없음(B 0915 봉 없음)"] = {"B_trades_at_missing_bar": sum(1 for x in r0["trades"] if x[1] == "B" and x[0] == "202501030915")}
    r2 = replay_m15(win, ev0, fl0, E, {d: 250_000.0 for d in win}, Flat(), cash=1_000_000)     # k ≈ 4 → 목표 금액 > 현금
    res["현금 부족(k≈4)"] = {"buy_reduced_or_unfilled": r2["notes"].get("buy_reduced_or_unfilled", 0), "min_cash": min(r2["cash"])}
    audit = all(x["executed_at"] is None or x["executed_at"] > x["locked_at"] for x in r0["locks"])
    res["잠금 → 실행 순서"] = {"all_exec_after_lock": audit, "locks": len(r0["locks"]), "executed": sum(1 for x in r0["locks"] if x["executed_at"])}
    p = res
    res["pass"] = (all(v["new_locks_before_exec_bar_same"] and v["new_fill_qty_at_exec_bar_same"] and v["new_exec_bar_has_fill"]
                       and not v["old_target_at_control_fill_bar_same"] for k, v in p.items() if k.startswith("실행 봉"))
                   and p["첫 통제 체결 봉까지 주문 0"]["trades_at_or_before_first_control_fill"] == 0
                   and p["장 경계(1515 체결 → 다음 날 첫 봉)"]["no_trade_same_day_after_1515"]
                   and all(e is None or e[:8] == "20250103" for e in p["장 경계(1515 체결 → 다음 날 첫 봉)"]["executed_at"])
                   and p["보존 · 정수 · 중복 · 음수 현금"]["all_int"] and not p["보존 · 정수 · 중복 · 음수 현금"]["dup"]
                   and p["보존 · 정수 · 중복 · 음수 현금"]["min_cash"] >= 0 and p["가격 없음(B 0915 봉 없음)"]["B_trades_at_missing_bar"] == 0
                   and p["현금 부족(k≈4)"]["buy_reduced_or_unfilled"] > 0 and p["현금 부족(k≈4)"]["min_cash"] >= 0 and audit)
    return res


OUT.mkdir(parents=True, exist_ok=True)
SYN = synthetic()
print("합성", json.dumps(SYN, ensure_ascii=False), flush=True)
RES = {"synthetic": SYN}

# ═════════ 저장 입력 · 재구성 ═════════
rows = list(csv.DictReader(open(IN / "nav_control_candidate.csv", encoding="utf-8")))
WIN = [r["date"] for r in rows if LO <= r["date"] <= HI]
assert WIN == [d for d in G["DAYS"] if LO <= d <= HI] and len(WIN) == 127
R = {r["date"]: r for r in rows}
E = {d: float(R[d]["exposure"]) for d in R}
navN = {k: {d: float(R[d][f"control_{k}"]) for d in R} for k in SL}
navO = {k: {d: float(R[d][f"cand_{k}"]) for d in R} for k in SL}
CT = json.load(open(IN / "control_trades.json"))
OT = json.load(open(IN / "candidate_trades.json"))
M = pickle.load(open(M15PKL, "rb"))
F76 = {r["date"]: r for r in csv.DictReader(open(P76 / "nav_train_control_old_fixed.csv", encoding="utf-8"))}
navF76 = {k: {d: float(F76[d][f"fixed_{k}"]) for d in WIN} for k in SL}
L76 = json.load(open(P76 / "fixed_local_only.json"))
stockp = lambda c, d: G["CL"].get(c, {}).get(d)
etfp = lambda c, d: G["ETF"].get(c, {}).get(d)
PRICE = {"D1": stockp, "ETF": etfp, "BASKET": stockp}
KIND = {"D1": "stock", "ETF": "etf", "BASKET": "stock", "M15": "stock"}
m15close = {}
for c, bl in M["bars"].items():
    for T, o, cl in bl:
        m15close.setdefault(c, {})[T[:8]] = cl
m15p = lambda c, d: m15close.get(c, {}).get(d)


def recon(trades, kind, price, navs, key=lambda t: t[:8], lots=False):
    """lots=True: 한 매도 기록을 매수 묶음(pid · 매수 날짜 순 = 장부의 sorted(pid))으로 나눠 묶음마다 비용(PR #76 원장은 매도를 합쳐 적음)."""
    costs = KN.Costs(CC, G["market_of"], 2.0, kind)
    book = {}
    by = {}
    for t, c, s, n, p in trades:
        by.setdefault(key(t), []).append((t, c, s, n, p))
    q, cash, lastp = {}, SLEEVE, {}
    out = {"cash": [], "inv": [], "gap": [], "cost": 0.0, "notional": 0.0, "buy": 0, "sell": 0}
    for d in WIN:
        for t, c, s, n, p in by.get(d, []):
            pieces = [n]
            if lots and s == "buy":
                book.setdefault(c, []).append([str(t), n])
            elif lots:
                pieces, left = [], n
                for lot in sorted(book.get(c, [])):
                    if left <= 0:
                        break
                    take = min(left, lot[1])
                    pieces.append(take)
                    lot[1] -= take
                    left -= take
                assert left == 0
                book[c] = [x for x in book[c] if x[1] > 0]
            for m in pieces:
                amt = m * p
                r = costs.rate(s, c, t, amt)[0]
                cash += -amt * (1 + r) if s == "buy" else amt * (1 - r)
                out["cost"] += amt * r
                out["notional"] += amt
            q[c] = q.get(c, 0) + (n if s == "buy" else -n)
            out["buy" if s == "buy" else "sell"] += 1
        inv = 0.0
        for c, n in q.items():
            if n:
                v = price(c, d)
                if v:
                    lastp[c] = v
                inv += n * lastp.get(c, 0.0)
        out["cash"].append(cash)
        out["inv"].append(inv)
        out["gap"].append(abs(cash + inv - navs[d]))
    out["max_gap"] = max(out["gap"])
    return out


REC = {"control": {}, "old_candidate": {}, "pr76_daily_fixed": {}}
for k in SL:
    pr = m15p if k == "M15" else PRICE[k]
    REC["control"][k] = recon(CT[k], KIND[k], pr, navN[k])
    REC["old_candidate"][k] = recon(OT[k], KIND[k], pr, navO[k])
for k in DAILY:
    tr = [(d, c, s, n, PRICE[k](c, d)) for d, c, s, n in L76[k]["trades"]]
    REC["pr76_daily_fixed"][k] = recon(tr, KIND[k], PRICE[k], navF76[k], lots=True)
RES["reconstruction_max_gap_won"] = {g: {k: v["max_gap"] for k, v in REC[g].items()} for g in REC}
recon_ok = all(v <= 1.0 for g in RES["reconstruction_max_gap_won"].values() for v in g.values())
RES["reconstruction_ok(≤1원)"] = recon_ok
print("재구성", RES["reconstruction_max_gap_won"], flush=True)
if CHECKS_ONLY or not SYN["pass"] or not recon_ok:
    RES["verdict"] = "CHECKS_ONLY" if (CHECKS_ONLY and SYN["pass"] and recon_ok) else "BLOCKED"
    (OUT / "m15_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    raise SystemExit(RES["verdict"])

# ═════════ Train 1회(고친 15분봉) ═════════
events, fills = {}, {}
for c, bl in M["bars"].items():
    for T, o, cl in bl:
        if T[:8] <= HI:
            events.setdefault(T, []).append((c, o, cl))
for t, c, s, n, p in CT["M15"]:
    if t[:8] <= HI:
        fills.setdefault(t, []).append((c, n if s == "buy" else -n))
assert all(T in events for T in fills)
NEW = replay_m15(WIN, events, fills, E, navN["M15"], KN.Costs(CC, G["market_of"], 2.0, "stock"))
assert len(NEW["nav"]) == len(WIN) and not NEW["dup"]
print("고친 M15", round(NEW["nav"][-1]), "매매", len(NEW["trades"]), NEW["notes"], flush=True)
exec_ok = all(x["executed_at"] is None or x["executed_at"] > x["locked_at"] for x in NEW["locks"])
first_bar_ok = True
for x in NEW["locks"]:                                            # 실행 봉 = 잠근 뒤 그 종목의 첫 봉
    if x["executed_at"]:
        nxt = min((T for T in events if T > x["locked_at"] and any(c == x["code"] for c, _, _ in events[T])), default=None)
        first_bar_ok &= nxt == x["executed_at"]
RES["timing_audit"] = {"locks": len(NEW["locks"]), "executed": sum(1 for x in NEW["locks"] if x["executed_at"]),
                       "superseded_or_end": sum(1 for x in NEW["locks"] if not x["executed_at"]),
                       "all_exec_after_lock": exec_ok, "exec_on_next_bar_of_code": first_bar_ok,
                       "trades_before_first_control_fill": sum(1 for x in NEW["trades"] if x[0] <= min(fills))}


def metrics(nav, cash, cost, notional, trades, base):
    seg = [base] + nav
    r = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    peak, mdd = base, 0.0
    for v in seg:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(range(len(r)), key=lambda i: r[i])
    mo = {}
    for d, x in zip(WIN, r):
        mo[d[:6]] = mo.get(d[:6], 1.0) * (1 + x)
    wm = min(mo, key=mo.get)
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    yrs = (D(WIN[-1]) - D(WIN[0])).days / 365.25
    cs = [c / n for c, n in zip(cash, nav)]
    return {"end_won": nav[-1], "return_pct": (nav[-1] / base - 1) * 100, "MDD_pct": mdd * 100, "worst_day_pct": r[wd] * 100, "worst_day_at": WIN[wd],
            "worst_month_pct": (mo[wm] - 1) * 100, "worst_month_at": wm, "day_breach_-15": sum(1 for x in r if x < -0.15 - 1e-12),
            "month_breach_-15": sum(1 for v in mo.values() if v - 1 < -0.15 - 1e-12), "cost_won": cost,
            "turnover_per_year": notional / 2 / (sum(nav) / len(nav)) / yrs, "cash_share_avg_pct": sum(cs) / len(cs) * 100,
            "cash_share_min_pct": min(cs) * 100, "trades": trades}


SLV = {"control": {}, "old_candidate": {}, "pr76": {}, "new": {}}
for k in SL:
    for g, src, rec in (("control", navN, REC["control"]), ("old_candidate", navO, REC["old_candidate"])):
        SLV[g][k] = {"nav": [src[k][d] for d in WIN], "cash": rec[k]["cash"], "cost": rec[k]["cost"], "notional": rec[k]["notional"],
                     "trades": {"buy": rec[k]["buy"], "sell": rec[k]["sell"]}}
for k in DAILY:
    rr = REC["pr76_daily_fixed"][k]
    SLV["pr76"][k] = SLV["new"][k] = {"nav": [navF76[k][d] for d in WIN], "cash": rr["cash"], "cost": rr["cost"], "notional": rr["notional"],
                                      "trades": {"buy": rr["buy"], "sell": rr["sell"]}}
SLV["pr76"]["M15"] = SLV["old_candidate"]["M15"]
a = NEW["acc"]
SLV["new"]["M15"] = {"nav": NEW["nav"], "cash": NEW["cash"], "cost": a.tot["buy_cost"] + a.tot["sell_cost"],
                     "notional": a.tot["buy_notional"] + a.tot["sell_notional"],
                     "trades": {"buy": sum(1 for x in NEW["trades"] if x[2] == "buy"), "sell": sum(1 for x in NEW["trades"] if x[2] == "sell")}}
TAB = {}
for g in SLV:
    nav = [sum(SLV[g][k]["nav"][i] for k in SL) for i in range(len(WIN))]
    cash = [sum(SLV[g][k]["cash"][i] for k in SL) for i in range(len(WIN))]
    TAB[g] = {"total": metrics(nav, cash, sum(SLV[g][k]["cost"] for k in SL), sum(SLV[g][k]["notional"] for k in SL),
                               {k: SLV[g][k]["trades"] for k in SL}, TOTAL),
              "sleeves": {k: metrics(SLV[g][k]["nav"], SLV[g][k]["cash"], SLV[g][k]["cost"], SLV[g][k]["notional"], SLV[g][k]["trades"], SLEEVE) for k in SL},
              "nav": nav}
RES["table"] = {g: {"total": TAB[g]["total"], "sleeves": TAB[g]["sleeves"]} for g in TAB}
RES["diff_new_minus"] = {g: {"end_won": TAB["new"]["total"]["end_won"] - TAB[g]["total"]["end_won"],
                             "return_pp": TAB["new"]["total"]["return_pct"] - TAB[g]["total"]["return_pct"],
                             "MDD_pp": TAB["new"]["total"]["MDD_pct"] - TAB[g]["total"]["MDD_pct"]} for g in ("control", "old_candidate", "pr76")}
RES["new_m15_counts"] = {"locks": len(NEW["locks"]), "notes": NEW["notes"], "buy_counts": {k: v for k, v in a.counts.items() if k.startswith("buy_")},
                         "unfilled": {k: v for k, v in a.counts.items() if "unfilled" in k or "reduced" in k}, "pending_at_end": NEW["pending_end"]}
RES["new_m15_conservation"] = {"checks": a.counts.get("checks"), "max_gap_cash": a.tot.get("max_gap_cash"), "max_gap_nav": a.tot.get("max_gap_nav"),
                               "min_cash": min(NEW["cash"]), "dup": NEW["dup"]}
ta = RES["timing_audit"]
RES["pass"] = {"synthetic": SYN["pass"], "reconstruction": recon_ok,
               "conservation": a.tot.get("max_gap_cash", 0) <= 1 and a.tot.get("max_gap_nav", 0) <= 1 and min(NEW["cash"]) >= 0 and not NEW["dup"],
               "timing_audit": ta["all_exec_after_lock"] and ta["exec_on_next_bar_of_code"] and ta["trades_before_first_control_fill"] == 0}
RES["verdict"] = "READY" if all(RES["pass"].values()) else "BLOCKED"
with open(OUT / "nav_train_m15_fixed.csv", "w", encoding="utf-8") as f:
    f.write("date,exposure_E_t,control_nav,old_candidate_nav,pr76_nav,new_nav,new_D1,new_M15,new_ETF,new_BASKET\n")
    for i, d in enumerate(WIN):
        f.write(f"{d},{E[d]:.10f},{TAB['control']['nav'][i]:.2f},{TAB['old_candidate']['nav'][i]:.2f},{TAB['pr76']['nav'][i]:.2f},{TAB['new']['nav'][i]:.2f}," +
                ",".join(f"{SLV['new'][k]['nav'][i]:.2f}" for k in ("D1", "M15", "ETF", "BASKET")) + "\n")
raw = json.dumps({"locks": NEW["locks"], "trades": NEW["trades"]}, ensure_ascii=False, sort_keys=True).encode("utf-8")
(OUT / "m15_fixed_local_only.json").write_bytes(raw)
RES["m15_fixed_local_only_sha256"] = hashlib.sha256(raw).hexdigest()
(OUT / "m15_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
for g in TAB:
    t = TAB[g]["total"]
    print(g, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in t.items()}, flush=True)
print("M15 소계정", {g: round(TAB[g]["sleeves"]["M15"]["end_won"]) for g in TAB}, flush=True)
print("통과", RES["pass"], RES["verdict"], flush=True)
print("끝", flush=True)
