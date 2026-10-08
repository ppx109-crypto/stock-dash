"""REAL-SLEEVE-0001 · 250만 원 소계정 B(M4) · R(R30) × seed 0~3 · 비용 2배(GPT PR #61 · 클로드 PREREG e6575a9e).
MR_D1PICKS=<d1_picks.json> python3 -E -P rs_m15.py <b3> <출력>
PR #55 fr_m15.py 그대로(자본은 common.py CASH = 2.5e6 한 줄). 보고용으로 장 마감 종목별 평가금액만 더 남김."""
import bisect
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "m15_exec.py").read_text(encoding="utf-8").split("\ndef run(mult):")[0]
P = {"__name__": "mr_m15", "__file__": str(HERE / "m15_exec.py")}
exec(compile(_src, "m15_exec(앞부분 · PR #41 그대로)", "exec"), P)
sys.path.insert(0, str(HERE))
import common as CM  # noqa: E402

KN, CC, np = P["KN"], P["CC"], P["np"]
SG, RANK, EXIT, STALE, SIZE, data, market_of = P["SG"], P["RANK"], P["EXIT"], P["STALE"], P["SIZE"], P["data"], P["market_of"]
OUT = Path(sys.argv[2])
SLOTS = 10
D1 = json.loads(Path(os.environ["MR_D1PICKS"]).read_text(encoding="utf-8"))
D1CAL = D1["cal"]
D1IX = {d: i for i, d in enumerate(D1CAL)}
D1SET = {(c, d) for d, cs in D1["picks"].items() for c in cs}
CFG = {"B": {"d1filter": True}, "R": {"d1filter": True, "hold_cap": 0.30}, "F": {"d1filter": True, "fresh": True},
       "RF": {"d1filter": True, "hold_cap": 0.30, "fresh": True}}
TRAIN = ("202509170000", "202604010000")
FULLW = ("202509170000", "202609010000")
COMMONW = ("202509180000", "202609010000")
PERIODS = (("Train 2025-09-17~2026-03-31", "20250917", "20260331"), ("2026-04~08(재사용 진단)", "20260401", "20260831"),
           ("전체 2025-09-17~2026-08-31", "00000000", "99999999"))


def d1_recent(code, day):
    """그날을 뺀 최근 5거래일(1일봉 달력) 안에 1일봉 신호가 있었나."""
    i = bisect.bisect_left(D1CAL, day)
    return any((code, D1CAL[j]) in D1SET for j in range(max(0, i - 5), i))


def d1_age(code, day):
    """그날을 뺀 1일봉 달력 직전 5거래일 가운데 D1 신호가 있는 가장 최근 날까지의 거리(1~5). 없으면 6."""
    i = bisect.bisect_left(D1CAL, day)
    for age in range(1, 6):
        j = i - age
        if j >= 0 and (code, D1CAL[j]) in D1SET:
            if not D1CAL[j] < day:
                raise AssertionError("미래 참조: D1 날짜 ≥ 판단일")
            return age
    return 6


def run(cfg, mult, lo, hi, exclude=None, snaps=(), seed=0):
    opt = CFG[cfg]
    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"), CM.CASH)
    rng = np.random.default_rng(seed)
    idx, times = {}, set()
    for c in SG:
        t = data[c]["t"]
        k0, k1 = bisect.bisect_left(t, lo), bisect.bisect_left(t, hi)
        idx[c] = (k0, k1)
        times.update(t[k0:k1])
    times = sorted(times)
    at = {}
    for c, (k0, k1) in idx.items():
        for k in range(k0, k1):
            at.setdefault(data[c]["t"][k], []).append((c, k))
    pos, want_buy, want_sell, last_close = {}, {}, {}, {}
    navs, gross, last_day = [], [], None
    notes = {"cant_split": 0, "stale_bumped": 0, "buy_signal_no_slot": 0, "skip_weak": 0, "skip_no_d1": 0, "partial_suppressed": 0,
             "trim_decided": 0, "trim_filled": 0, "trim_cancelled": 0, "trim_cut_to_remaining": 0, "trim_closed_all": 0, "trim_notional": 0.0,
             "multi_candidate_times": 0, "fresh_order_changed_times": 0, "age_missing": 0}
    changed_codes = set()
    pf = lambda code: (last_close.get(code, 0.0), False)
    hold = []

    def held_values():
        v = {}
        for q in acc.pos.values():
            v[q["code"]] = v.get(q["code"], 0.0) + q["qty"] * pf(q["code"])[0]
        return v
    trim, snap, last_T = {}, {}, None                    # trim: 종목 → (고정 수량, 판단한 날, pid, 판단 봉)

    def snapshot(day):
        """그날 장 마감 시점 종목별 '누적 실현 손익 + 보유 평가 손익'."""
        by = {}
        for row in acc.closed:
            by[row["code"]] = by.get(row["code"], 0.0) + row["pnl_net"]
        for q in acc.pos.values():
            by[q["code"]] = by.get(q["code"], 0.0) + q["realized"] + q["qty"] * pf(q["code"])[0] - q["basis"]
        snap[day] = by

    for T in times:
        if last_day and T[:8] != last_day:
            nav, inv = acc.mtm(pf)
            acc.check(pf)
            navs.append((last_day, nav, inv))
            gross.append((last_day, nav + acc.cum_cost()))
            hold.append((last_day, held_values()))         # 보고용 기록(판단과 무관)
            if last_day in snaps:
                snapshot(last_day)
            cap = opt.get("hold_cap")
            if cap:                                         # ⓪ 장 마감 뒤 보유 축소 판단(그날 마지막 봉까지의 값만)
                for c, p in pos.items():
                    if c in trim:
                        continue
                    qty, px = acc.pos[p["pid"]]["qty"], pf(c)[0]
                    if qty * px > cap * nav:
                        q = math.floor(qty - cap * nav / px)
                        if q >= 1:
                            trim[c] = (q, last_day, p["pid"], last_T)
                            notes["trim_decided"] += 1
        bars = at[T]
        for c, k in bars:                                   # ① 다음 봉 시가에 팔기
            if c in want_sell and c in pos:
                n, dec = want_sell.pop(c)
                p = pos[c]
                part = p["칸"] if n == "all" or n >= p["칸"] else int(n)
                if part >= p["칸"]:
                    acc.sell(p["pid"], data[c]["o"][k], T, dec, reason="청산")
                else:
                    q = math.floor(acc.pos[p["pid"]]["qty"] * part / p["칸"])
                    if q < 1:
                        notes["cant_split"] += 1
                    else:
                        acc.sell(p["pid"], data[c]["o"][k], T, dec, qty=q, reason="나눠 팔기")
                p["칸"] -= part
                if p["칸"] <= 0:
                    del pos[c]
            if c in trim and T[:8] > trim[c][1]:            # ①' 보유 축소: 다음 거래일 이후 첫 봉 시가 · 고정 수량
                q, dday, tpid, dT = trim.pop(c)
                if not (dT < T and dday < T[:8]):
                    raise AssertionError("미래 참조: 축소 판단 봉 ≥ 체결 봉")
                p = pos.get(c)
                if p is None or p["pid"] != tpid or tpid not in acc.pos:
                    notes["trim_cancelled"] += 1
                else:
                    left = acc.pos[tpid]["qty"]
                    if q > left:
                        notes["trim_cut_to_remaining"] += 1
                    qq = min(q, left)
                    px = data[c]["o"][k]
                    if acc.sell(tpid, px, T, dT, qty=qq, reason="보유 축소"):
                        notes["trim_filled"] += 1
                        notes["trim_notional"] += qq * px
                        if tpid not in acc.pos:             # 남은 수량이 0이면 장부에서 닫혀 칸도 비움
                            notes["trim_closed_all"] += 1
                            del pos[c]
        buys = [(c, k) for c, k in bars if c in want_buy and c not in pos]
        draw = {ck: rng.random() for ck in buys}         # 원래 키와 같은 순서 · 같은 수로 난수를 뽑음
        base_key = lambda ck: (RANK(ck[0], data[ck[0]], ck[1] - 1), draw[ck])
        if opt.get("fresh"):
            ages = {ck: d1_age(ck[0], want_buy[ck[0]][1][:8]) for ck in buys}
            notes["age_missing"] += sum(1 for v in ages.values() if v == 6)
            order_b = sorted(buys, key=base_key)
            buys.sort(key=lambda ck: (ages[ck],) + base_key(ck))
            if len(buys) >= 2:
                notes["multi_candidate_times"] += 1
                if buys != order_b:
                    notes["fresh_order_changed_times"] += 1
                    changed_codes.update(x[0] for x, y in zip(buys, order_b) if x != y)
        else:
            buys.sort(key=base_key)
        for c, k in buys:                                   # ② 다음 봉 시가에 사기
            need, dec = want_buy.pop(c)
            free = SLOTS - sum(p["칸"] for p in pos.values())
            if free < need:
                weak = sorted((q for q in pos.values() if STALE(q)), key=lambda q: data[q["code"]]["c"][q["now"]] / q["price"])
                for q in weak:
                    if free >= need:
                        break
                    qc, qb = q["code"], data[q["code"]]
                    kk = bisect.bisect_left(qb["t"], T)
                    if kk < len(qb["t"]) and qb["t"][kk] == T:
                        if q["now"] >= kk:
                            raise AssertionError("미래 참조: 비킴 판단 봉 ≥ 체결 봉")
                        free += q["칸"]
                        acc.sell(q["pid"], qb["o"][kk], T, qb["t"][kk - 1], reason="묵음 비키기")
                        notes["stale_bumped"] += 1
                        del pos[qc]
                        want_sell.pop(qc, None)
            if free <= 0:
                notes["buy_signal_no_slot"] += 1
                continue
            take = min(need, free)
            o = data[c]["o"][k]
            pid = f"{c}:{T}"
            if acc.buy(pid, c, o, T, dec, value=take / SLOTS * acc.mtm(pf)[0], slots=take, tag=f"칸{take}"):
                pos[c] = {"pid": pid, "i": k, "price": o, "칸": take, "처음칸": take, "peak": o, "now": k, "day": T[:8], "code": c}
        for c, _ in bars:
            want_buy.pop(c, None)
        for c, k in bars:                                   # ③ 봉 갱신
            p = pos.get(c)
            if p:
                p["now"] = k
                p["peak"] = max(p["peak"], data[c]["c"][k])
        for c, k in bars:                                   # ④ 봉이 닫힌 뒤 판단
            bb = data[c]
            p = pos.get(c)
            if p:
                n = EXIT(c, bb, p, k)
                if opt.get("no_partial") and n and n != "all":
                    notes["partial_suppressed"] += 1
                    n = 0
                if n:
                    want_sell[c] = (n, T)
            elif SG[c][k] and k + 1 < len(bb["t"]) and c != exclude:
                need = SIZE(c, bb, k)
                if opt.get("skip_weak") and need < 4:
                    notes["skip_weak"] += 1
                elif opt.get("d1filter") and not d1_recent(c, T[:8]):
                    notes["skip_no_d1"] += 1
                else:
                    want_buy[c] = (need, T)
            last_close[c] = bb["c"][k]
        last_day, last_T = T[:8], T
    nav, inv = acc.mtm(pf)
    acc.check(pf)
    navs.append((last_day, nav, inv))
    gross.append((last_day, nav + acc.cum_cost()))
    hold.append((last_day, held_values()))
    if last_day in snaps:
        snapshot(last_day)
    notes["trim_pending_at_end"] = len(trim)
    notes["fresh_changed_codes"] = sorted(changed_codes)
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills, "counts": dict(acc.counts),
            "tot": dict(acc.tot), "notes": notes, "cal": [x[0] for x in navs], "snap": snap, "hold": hold}


import csv  # noqa: E402
import io  # noqa: E402
import subprocess  # noqa: E402
from datetime import date  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
TOTAL = 4 * CM.CASH
assert CM.CASH == 2.5e6


def agg_stats(days, nav, inv, hold):
    seg = [TOTAL] + nav
    rets = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    peak, mdd = TOTAL, 0.0
    for v in seg:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(range(len(rets)), key=lambda i: rets[i])
    months = {}
    for d, r in zip(days, rets):
        months[d[:6]] = months.get(d[:6], 1.0) * (1 + r)
    wm = min(months, key=months.get)
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    yrs = (D(days[-1]) - D(days[0])).days / 365.25
    wmax = []
    for d, n, h in zip(days, nav, hold):
        c, v = max(h.items(), key=lambda x: x[1]) if h else (None, 0.0)
        wmax.append((d, c, v / n))
    top = max(wmax, key=lambda x: x[2])
    return {"end_nav": nav[-1], "CAGR_pct": ((nav[-1] / TOTAL) ** (1 / yrs) - 1) * 100, "MDD_pct": mdd * 100, "worst_day_pct": rets[wd] * 100,
            "worst_day_at": days[wd], "day_breach_-15": sum(1 for r in rets if r < -0.15 - 1e-12), "worst_month_pct": (months[wm] - 1) * 100,
            "worst_month_at": wm, "month_breach_-15": sum(1 for v in months.values() if v - 1 < -0.15 - 1e-12),
            "avg_invest_ratio_pct": sum(i / n for i, n in zip(inv, nav)) / len(nav) * 100,
            "max_single_name_weight_pct": top[2] * 100, "max_single_name_at": top[0], "max_single_name_code": top[1], "daily_max_weight": wmax}


RES, RUNS = {"runs": {}}, {}
for cfg in ("B", "R"):
    for seed in (0, 1, 2, 3):
        r = run(cfg, 2.0, *TRAIN, seed=seed)
        key = f"{cfg}_x2_s{seed}"
        RUNS[key] = r
        fl = [f for f in r["fills"] if f["status"] in ("FILLED", "REDUCED")]
        navv = [x[1] for x in r["nav"]]
        D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
        yrs = (D(r["nav"][-1][0]) - D(r["nav"][0][0])).days / 365.25
        RES["runs"][key] = {"end_nav": navv[-1], "days": len(navv), "fills": len(fl), "cost_total_won": r["tot"]["buy_cost"] + r["tot"]["sell_cost"],
                            "notional_won": sum(f["notional"] for f in fl), "turnover_per_year": sum(f["notional"] for f in fl) / 2 / (sum(navv) / len(navv)) / yrs,
                            "max_gap_cash": r["tot"].get("max_gap_cash"), "max_gap_nav": r["tot"].get("max_gap_nav"), "checks": r["counts"].get("checks"),
                            "min_cash_ok": True, "unfilled_qty0": r["counts"].get("buy_unfilled:요청 수량 0", 0),
                            "unfilled_cash": r["counts"].get("buy_unfilled:현금 1주 미만", 0), "buy_reduced": r["counts"].get("buy_reduced", 0),
                            "trim_fills": sum(1 for f in fl if f.get("reason") == "보유 축소"), "positions_closed": len(r["closed"]), "open_at_end": len(r["open"])}
        with open(OUT / f"nav_{key}_2p5m.csv", "w", encoding="utf-8") as f:
            f.write("date,nav_won,invested_won\n")
            f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in r["nav"])
        print(key, round(navv[-1]), "체결", len(fl), "수량0 미체결", RES["runs"][key]["unfilled_qty0"], "축소", RES["runs"][key]["buy_reduced"],
              "비용", round(RES["runs"][key]["cost_total_won"]), "보존", r["tot"].get("max_gap_cash"), r["tot"].get("max_gap_nav"), flush=True)
OLD = {}
for nm in ("B4", "R4"):
    txt = subprocess.check_output(["git", "-C", os.environ.get("RS_REPO", "/home/user/stock-dash"), "show",
                                   f"24b12632560c7e4c911ce72a20df43fef004cb89:research-exchange/claude-to-gpt/PATH-ENSEMBLE-0001/evidence/ens_{nm}_EQUAL.csv"]).decode()
    OLD[nm] = {r["date"]: float(r["nav_won"]) for r in csv.DictReader(io.StringIO(txt))}
for nm, cfg in (("B4", "B"), ("R4", "R")):
    rs = [RUNS[f"{cfg}_x2_s{s}"] for s in range(4)]
    days = [x[0] for x in rs[0]["nav"]]
    if any([x[0] for x in r["nav"]] != days for r in rs):
        raise SystemExit("날짜행 다름 · 중단")
    nav = [sum(r["nav"][i][1] for r in rs) for i in range(len(days))]
    inv = [sum(r["nav"][i][2] for r in rs) for i in range(len(days))]
    hold = []
    for i in range(len(days)):
        h = {}
        for r in rs:
            assert r["hold"][i][0] == days[i]
            for c, v in r["hold"][i][1].items():
                h[c] = h.get(c, 0.0) + v
        hold.append(h)
    st = agg_stats(days, nav, inv, hold)
    st["cost_total_won"] = sum(RES["runs"][f"{cfg}_x2_s{s}"]["cost_total_won"] for s in range(4))
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    st["turnover_per_year"] = sum(RES["runs"][f"{cfg}_x2_s{s}"]["notional_won"] for s in range(4)) / 2 / (sum(nav) / len(nav)) / ((D(days[-1]) - D(days[0])).days / 365.25)
    st["sleeve_end_share_pct"] = [r["nav"][-1][1] / nav[-1] * 100 for r in rs]
    old = OLD[nm]
    if sorted(old) != days:
        raise SystemExit("PR #60 날짜행 다름")
    dif = [nav[i] - old[d] for i, d in enumerate(days)]
    st["vs_pr60_equal"] = {"end_diff_won": dif[-1], "end_diff_pct": dif[-1] / old[days[-1]] * 100, "max_abs_diff_won": max(abs(x) for x in dif),
                           "max_abs_diff_at": days[max(range(len(dif)), key=lambda i: abs(dif[i]))], "mean_abs_diff_won": sum(abs(x) for x in dif) / len(dif)}
    RES[nm] = st
    with open(OUT / f"agg_{nm}_ACTUAL.csv", "w", encoding="utf-8") as f:
        f.write("date,nav_won,invested_won,max_name_code,max_name_weight,pr60_equal_nav,diff_won\n")
        f.writelines(f"{d},{n:.2f},{iv:.2f},{w[1]},{w[2]:.6f},{old[d]:.4f},{x:.4f}\n" for d, n, iv, w, x in zip(days, nav, inv, st["daily_max_weight"], dif))
    print(nm, {k: v for k, v in st.items() if k != "daily_max_weight"}, flush=True)
d = RES["R4"]["end_nav"] - RES["B4"]["end_nav"]
RES["R4_minus_B4"] = {"won": d, "pct": d / RES["B4"]["end_nav"] * 100}
inv_ok = all(abs(v["max_gap_cash"] or 0) <= 1.0 and abs(v["max_gap_nav"] or 0) <= 1.0 and (v["checks"] or 0) > 0 for v in RES["runs"].values()) and len(RES["runs"]) == 8
r4 = RES["R4"]
crit = {"1_eight_runs_and_invariants": inv_ok, "2_R4_end_ge_B4": r4["end_nav"] >= RES["B4"]["end_nav"], "3_R4_no_day_breach": r4["day_breach_-15"] == 0,
        "4_R4_no_month_breach": r4["month_breach_-15"] == 0, "5_R4_max_name_lt_30": r4["max_single_name_weight_pct"] < 30.0}
RES["criteria"] = crit
RES["verdict"] = "IMPLEMENTATION_READY" if all(crit.values()) else "NO_CANDIDATE"
print("R4−B4", RES["R4_minus_B4"], "판정", crit, RES["verdict"], flush=True)
for nm in ("B4", "R4"):
    RES[nm].pop("daily_max_weight")
(OUT / "rs_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
print("끝", flush=True)
