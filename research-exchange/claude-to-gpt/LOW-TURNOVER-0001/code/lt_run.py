"""LOW-TURNOVER-0001 실행(PREREG 그대로): 1일봉 FIX 신호 · 주/격주 판단 · 똑같은 크기 · 정배열 깨짐/−15%만 팖 · 달력월 −8% 정지.
python3 -E -P lt_run.py <00b98ab1 폴더> <nrl 캐시> <출력 폴더>
신호 · 장부 · 비용은 PR #41 daily_exec.py · kernel2.py를 그대로 불러 씀(같은 폴더 복사본 · 바꾸지 않음)."""
import json
import math
import sys
from datetime import date as _d
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
_g = {"__name__": "lt_base", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41 그대로)", "exec"), _g)
KN, CC, lab, nrl = _g["KN"], _g["CC"], _g["lab"], _g["nrl"]
DAYS, PICKS, LANE, CL, IDXOF = _g["DAYS"], _g["PICKS"], _g["LANE"], _g["CL"], _g["IDXOF"]
RANK, KIN, market_of, stock_pf, reject, run_d1 = _g["RANK"], _g["KIN"], _g["market_of"], _g["stock_pf"], _g["reject"], _g["run_d1"]
OUT = Path(sys.argv[3])
SHAPE = nrl.shape
TRAIN, VALID = ("20170201", "20201231"), ("20210101", "20221231")
PERIODS = (("Train 2017-02~2020-12", *TRAIN), ("Validation 2021~2022", *VALID), ("진단 2023-01~2026-09(이미 봄)", "20230101", "20260930"),
           ("전체", "00000000", "99999999"))
EXPS = {"L1": (False, 5, 0.12), "L2": (False, 8, 0.075), "L3": (True, 5, 0.12), "L4": (True, 8, 0.075)}
STOCK_CAP, STOP, MONTH_STOP = 0.60, 0.85, -0.08


def isoweek(d):
    return _d(int(d[:4]), int(d[4:6]), int(d[6:])).isocalendar()[:2]


def run_lt(exp, mult, cash, end=None, CLm=None, LN=None):
    biweekly, N, w = EXPS[exp]
    CLm, LN = CLm or CL, LN or LANE
    CLDm = {c: sorted(v) for c, v in CLm.items()}
    days = [d for d in DAYS if end is None or d <= end]
    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"), cash)
    held, pending, navs, gross = {}, [], [], []
    month_base, cur_month, prev_nav, halt = cash, None, cash, None
    notes = {"decisions": 0, "month_stop": 0, "buy_skip_cap": 0, "exit_trend": 0, "exit_stop": 0}
    for k, d in enumerate(days):
        pf = stock_pf(CLm, CLDm, d)
        keep = []
        for o in sorted(pending, key=lambda x: 0 if x["side"] == "sell" else 1):
            c = o["code"]
            j, p = IDXOF[c].get(d), CLm.get(c, {}).get(d)
            if o["side"] == "sell":
                if o["pid"] not in acc.pos:
                    continue
                if p is None or (j is not None and lab.locked(LN[c]["closes"], LN[c]["날"], j, -1)):
                    reject(acc, o["pid"], c, "sell", o["dec"], d, "하한가 · 값 없음 → 다음 날 다시")
                    keep.append(o)
                    continue
                acc.sell(o["pid"], p, d, o["dec"], reason=o["why"])
                if held.get(c, {}).get("pid") == o["pid"]:
                    held.pop(c)
            else:
                if halt == d[:6]:
                    reject(acc, o["pid"], c, "buy", o["dec"], d, "달력월 정지로 취소")
                    continue
                if p is None or j is None:
                    reject(acc, o["pid"], c, "buy", o["dec"], d, "값 없음 → 다음 날 다시")
                    keep.append(o)
                    continue
                if lab.locked(LN[c]["closes"], LN[c]["날"], j, 1):
                    reject(acc, o["pid"], c, "buy", o["dec"], d, "상한가")
                    continue
                if acc.buy(o["pid"], c, p, d, o["dec"], value=o["value"], tag=exp):
                    held[c] = {"pid": o["pid"], "entry": p, "row": o["row"]}
        pending = keep
        nav, inv = acc.mtm(pf)
        acc.check(pf)
        navs.append((d, nav, inv))
        gross.append((d, nav + acc.cum_cost()))
        if cur_month != d[:6]:
            if cur_month is not None:
                month_base = prev_nav
            cur_month = d[:6]
        prev_nav = nav
        if halt != d[:6] and nav / month_base - 1 <= MONTH_STOP:
            halt = d[:6]
            notes["month_stop"] += 1
            sold = {o["pid"] for o in pending if o["side"] == "sell"}
            pending = [o for o in pending if o["side"] == "sell"] + [
                {"side": "sell", "code": c, "pid": h["pid"], "dec": d, "why": "달력월 −8% 정지"} for c, h in held.items() if h["pid"] not in sold]
            continue
        if halt == d[:6]:
            continue
        nd = days[k + 1] if k + 1 < len(days) else None
        if not (nd is None or isoweek(nd) != isoweek(d)) or (biweekly and isoweek(d)[1] % 2 == 1):
            continue
        notes["decisions"] += 1
        exiting = {o["code"] for o in pending if o["side"] == "sell"}
        for c, h in held.items():
            if c in exiting:
                continue
            j = IDXOF[c].get(d)
            if j is None:
                continue
            px = LN[c]["closes"][j]
            why = None
            if not SHAPE[c]["정배열"][j]:
                why, key = "정배열 깨짐", "exit_trend"
            elif px <= h["entry"] * STOP:
                why, key = "−15% 손절", "exit_stop"
            if why:
                notes[key] += 1
                pending.append({"side": "sell", "code": c, "pid": h["pid"], "dec": d, "why": why})
                exiting.add(c)
        free = N - (len(held) - len(exiting & set(held))) - sum(1 for o in pending if o["side"] == "buy")
        rows = [h["row"] for c, h in held.items() if c not in exiting]
        stock_now = sum(acc.pos[h["pid"]]["qty"] * pf(c)[0] for c, h in held.items() if c not in exiting and h["pid"] in acc.pos)
        for row in sorted(PICKS.get(d, []), key=RANK):
            if free <= 0:
                break
            c = row["code"]
            if c in held or any(o["code"] == c and o["side"] == "buy" for o in pending):
                continue
            if not KIN(row, rows):
                continue
            v = min(w * nav, STOCK_CAP * nav - stock_now)
            if v < (CLm.get(c, {}).get(d) or 1e18):
                notes["buy_skip_cap"] += 1
                continue
            pending.append({"side": "buy", "code": c, "pid": f"{c}:{d}", "value": v, "dec": d, "row": row, "why": "주간 신호"})
            rows.append(row)
            stock_now += v
            free -= 1
    last = days[-1]
    pfl = stock_pf(CLm, CLDm, last)
    liq, _ = acc.liquidation_nav(pfl, last)
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pfl), "fills": acc.fills, "counts": dict(acc.counts),
            "tot": dict(acc.tot), "notes": notes, "liq": liq, "cal": days, "cash0": cash}


def stats(r, periods):
    KN.START_CASH = r["cash0"]
    rep = KN.report(r["nav"], r["closed"], r["cal"], periods, r["gross"])
    for name, lo, hi in periods:
        a = rep.get(name)
        if not a:
            continue
        navs = [n for d, n, _ in r["nav"] if lo <= d <= hi]
        invs = [i for d, _, i in r["nav"] if lo <= d <= hi]
        fl = [f for f in r["fills"] if lo <= str(f["fill_at"])[:8] <= hi and f["status"] in ("FILLED", "REDUCED")]
        yrs = KN._years(a["from"], a["to"]) or 1
        by = {}
        for p in r["closed"] + r["open"]:
            ex = p.get("last_exit") or r["cal"][-1]
            if lo <= ex <= hi:
                by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
        tot = sum(by.values())
        top = max(by.items(), key=lambda x: x[1]) if by else (None, 0.0)
        a.update({"turnover_per_year": round(sum(f["notional"] for f in fl) / 2 / (sum(navs) / len(navs)) / yrs, 2),
                  "fills_per_year": round(len(fl) / yrs, 1), "cash_ratio_avg_pct": round(100 - sum(i / n for i, n in zip(invs, navs)) / len(navs) * 100, 1),
                  "cost_won": round(sum(f["cost"] for f in fl)), "top_code": top[0],
                  "top_code_share_pct": round(top[1] / tot * 100, 1) if tot > 0 else None, "pnl_pct_of_start": round(tot / r["cash0"] * 100, 2)})
    return rep


def ok_risk(a):
    return a["day_breach_-15"] == 0 and a["month_breach_-15"] == 0 and a["MDD_daily"] > -15.0


OUT.mkdir(parents=True, exist_ok=True)
P_TR = (PERIODS[0],)
TRR = {}
for e in EXPS:
    for m in (1.0, 2.0):
        r = run_lt(e, m, 1e7, end=TRAIN[1])
        TRR[(e, m)] = stats(r, P_TR)[P_TR[0][0]]
        a = TRR[(e, m)]
        print("Train", e, m, a["CAGR"], a["MDD_daily"], a["worst_month"], a["turnover_per_year"], a["top_code"], a["top_code_share_pct"], r["notes"], flush=True)
rows, passed = [], []
for e in EXPS:
    a1, a2 = TRR[(e, 1.0)], TRR[(e, 2.0)]
    c = {"risk": ok_risk(a1) and ok_risk(a2), "cagr2_pos": (a2["CAGR"] or -1) > 0,
         "concentration": a2["pnl_pct_of_start"] <= 0 or (a2["top_code_share_pct"] is not None and a2["top_code_share_pct"] <= 50)}
    rows.append({"exp": e, **c, "x1": {k: a1[k] for k in ("CAGR", "MDD_daily", "worst_day", "worst_month", "month_breach_-15", "turnover_per_year",
                                                         "fills_per_year", "cash_ratio_avg_pct", "top_code", "top_code_share_pct", "positions", "PF")},
                 "x2": {k: a2[k] for k in ("CAGR", "MDD_daily", "worst_month", "month_breach_-15", "top_code", "top_code_share_pct")}})
    if all(c.values()):
        passed.append(rows[-1])
passed.sort(key=lambda r: (-r["x2"]["CAGR"], list(EXPS).index(r["exp"])))
chosen = None
if passed:
    best = passed[0]["x2"]["CAGR"]
    tie = sorted([r for r in passed if best - r["x2"]["CAGR"] <= 0.5], key=lambda r: (-r["x2"]["MDD_daily"], list(EXPS).index(r["exp"])))
    chosen = tie[0]["exp"]
print("통과", [r["exp"] for r in passed], "고정", chosen, flush=True)

# 기준선(실험 아님): 원래 1일봉 같은 조건(1천만 · 다음 날 종가) · Train만
def baseline():
    _g["KN"].START_CASH = 1e7
    src = (HERE / "daily_exec.py").read_text(encoding="utf-8")
    assert 'acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"))' in src
    acc_cls = KN.Account

    class A1e7(acc_cls):
        def __init__(self, costs, cash=1e7):
            super().__init__(costs, 1e7)
    KN.Account = A1e7
    try:
        r = run_d1("next", 1.0)
    finally:
        KN.Account = acc_cls
    r["cash0"] = 1e7
    return stats(r, PERIODS)


BASE = baseline()
print("기준선 원래 1일봉(1천만)", {p: (BASE[p] or {}).get("CAGR") for p in BASE}, "회전율", BASE["Train 2017-02~2020-12"]["turnover_per_year"], flush=True)

# 회귀: 자르기(L1 · 2019-06-28 뒤 가격 ×1.37)
X = "20190628"
LN2 = {c: dict(v, closes=[(x * 1.37 if dd > X else x) for dd, x in zip(v["날"], v["closes"])]) for c, v in LANE.items()}
CL2 = {c: {d: (p * 1.37 if d > X else p) for d, p in v.items()} for c, v in CL.items()}
ra = run_lt("L1", 1.0, 1e7, end=TRAIN[1])
rb = run_lt("L1", 1.0, 1e7, end=TRAIN[1], CLm=CL2, LN=LN2)
key = lambda f: json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in f.items()}, sort_keys=True, default=str)
REG = {"cut_L1": {"x": X, "fills_equal": [key(f) for f in ra["fills"] if f["fill_at"] <= X] == [key(f) for f in rb["fills"] if f["fill_at"] <= X],
                  "nav_equal": [(d, round(v, 4)) for d, v, _ in ra["nav"] if d <= X] == [(d, round(v, 4)) for d, v, _ in rb["nav"] if d <= X]}}

VAL = None
import os
if os.environ.get("LT_TRAIN_ONLY") == "1":          # 점검용: Validation 구간을 계산하지 않고 멈춤
    print("Train 점검 끝", flush=True)
    sys.exit(0)
if chosen:
    FULL = {}
    for m in (1.0, 2.0):
        for cash in (1e7, 1e8):
            r = run_lt(chosen, m, cash)
            FULL[f"x{m:g}_{int(cash)}"] = (r, stats(r, PERIODS))
    r_tr = run_lt(chosen, 1.0, 1e7, end=TRAIN[1])
    REG["train_only_equals_full_prefix"] = [(d, round(v, 4)) for d, v, _ in r_tr["nav"]] == \
        [(d, round(v, 4)) for d, v, _ in FULL["x1_10000000"][0]["nav"] if d <= TRAIN[1]]
    v1, v2 = FULL["x1_10000000"][1][PERIODS[1][0]], FULL["x2_10000000"][1][PERIODS[1][0]]
    conds = {"risk": ok_risk(v1) and ok_risk(v2), "cagr2_pos": (v2["CAGR"] or -1) > 0,
             "concentration": v2["pnl_pct_of_start"] <= 0 or (v2["top_code_share_pct"] is not None and v2["top_code_share_pct"] <= 50)}
    VAL = {"chosen": chosen, "conditions": conds, "verdict": "RESEARCH_CANDIDATE" if all(conds.values()) else "NO_CANDIDATE",
           "independent_validation": "WAITING_DATA",
           "periods": {k: {p: ({kk: vv for kk, vv in a.items() if kk != "monthly"} if a else None) for p, a in rep.items()} for k, (r, rep) in FULL.items()},
           "monthly_x1_1e7": FULL["x1_10000000"][1]["전체"]["monthly"]}
    for k, (r, rep) in FULL.items():
        with open(OUT / f"nav_{chosen}_{k}.csv", "w", encoding="utf-8") as f:
            f.write("date,nav_norm,invested_ratio\n")
            for d, n, i in r["nav"]:
                f.write(f"{d},{n / r['cash0']:.6f},{i / n:.5f}\n")
else:
    VAL = {"chosen": None, "verdict": "NO_CANDIDATE", "independent_validation": "WAITING_DATA", "why": "Train 선택 조건 통과 없음 · Validation 안 돌림"}
print("판정", {k: v for k, v in VAL.items() if k in ("chosen", "conditions", "verdict")}, "회귀", REG, flush=True)
(OUT / "results.json").write_text(json.dumps({"train": rows, "passed": [r["exp"] for r in passed], "chosen": chosen, "validation": VAL,
                                               "baseline_original_d1_1e7": {p: ({kk: vv for kk, vv in a.items() if kk != "monthly"} if a else None)
                                                                            for p, a in BASE.items()}, "regression": REG},
                                              ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("끝", flush=True)
