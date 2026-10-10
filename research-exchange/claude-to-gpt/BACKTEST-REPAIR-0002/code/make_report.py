"""BACKTEST-REPAIR-0002 성적표 · 증거 파일 만들기.
python3 make_report.py <실행 결과 폴더(*.pkl)> <PR #39 evidence/results.json> <test_kernel.json> <출력 evidence 폴더>
원시 가격 · 수량은 내보내지 않음(정규화 NAV · 비율 · 비용 bp · 날짜 · 코드만)."""
import csv
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel2 as KN  # noqa: E402

RUN, PR39, TK, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
P39 = json.load(open(PR39, encoding="utf-8"))["runs"]
M15 = pickle.load(open(RUN / "m15.pkl", "rb"))
M15C = pickle.load(open(RUN / "m15_cut.pkl", "rb"))
META = pickle.load(open(RUN / "daily_meta.pkl", "rb"))
M15P = (("앞 2025-09-17~2026-03(이미 봄)", "20250917", "20260331"), ("뒤 2026-04~08(이미 봄)", "20260401", "20260831"),
        ("전체", "00000000", "99999999"))

CORE = [("1일봉 새82 FIX", "D1_next", "D1_FIX_next"), ("15분봉 22회차 FLOW-LAG2", "M15", "M15_FLOW-LAG2"),
        ("빈칸 엔진", "ETF_engine_next", "ETF_engine_FIX_next"), ("코스닥 인버스", "ETF_inverse_next", "ETF_inverse_FIX_next"),
        ("바구니 C FIX", "BASKET_next", "BASKET_FIX_next")]
EXEC = {"D1_next": "d 종가 판단 → 다음 거래일 종가(별도 연구 규칙)", "M15": "봉 닫힌 뒤 판단 → 다음 봉 시가(원 순서 · 정확한 봉 자료)",
        "ETF_engine_next": "d 종가 판단 → 다음 거래일 종가(별도 연구 규칙)", "ETF_inverse_next": "d 종가 판단 → 다음 거래일 종가(별도 연구 규칙)",
        "BASKET_next": "d 종가 판단 → 다음 거래일 종가(별도 연구 규칙)"}


def load(name):
    if name.startswith("M15"):
        m = {"x1": 1.0, "x2": 2.0, "x0": 0.0}[name.split("_")[-1]]
        return M15["runs"][m]
    return pickle.load(open(RUN / f"{name}.pkl", "rb"))


def summarize(name, res, periods):
    cal = res["cal"]
    rep = KN.report(res["nav"], res["closed"], cal, periods, res["gross"])
    full = rep["전체"]
    nav_last = res["nav"][-1][1]
    yrs = KN._years(res["nav"][0][0], res["nav"][-1][0])
    liq = res["liquidation"]["nav"]
    open_mtm = sum(o["invest0"] + o["pnl_net"] for o in res["open"])
    fills = res["fills"]
    by = {}
    for f in fills:
        k = f"{f['side']}:{f['status']}"
        by[k] = by.get(k, 0) + 1
    why = {}
    for f in fills:
        if f["status"] in ("UNFILLED", "RETRY"):
            k = f"{f['side']}:{f['status']}:{f['reason'].split(' · ')[-1]}"
            why[k] = why.get(k, 0) + 1
    qty_ok, qty_bad = 0, 0
    sold = {}
    for f in fills:
        if f["side"] == "sell" and f["status"] == "FILLED":
            sold[f["pid"]] = sold.get(f["pid"], 0.0) + f["qty_ratio"]
    for p in res["closed"]:
        if abs(sold.get(p["pid"], 0.0) - 1.0) < 1e-9:
            qty_ok += 1
        else:
            qty_bad += 1
    open_bad = sum(1 for o in res["open"] if sold.get(o["pid"], 0.0) >= 1.0 - 1e-12)
    s = {
        "final_nav_norm": round(nav_last / KN.START_CASH, 6),
        "positions_closed": len(res["closed"]), "positions_open_end": len(res["open"]),
        "open_end_mtm_pct_nav": round(open_mtm / nav_last * 100, 2) if nav_last else None,
        "open_end_unrealized_pct_start": round(sum(o["pnl_net"] for o in res["open"]) / KN.START_CASH * 100, 3),
        "liquidation_nav_norm": round(liq / KN.START_CASH, 6), "liquidation_cost_pct_nav": round(res["liquidation"]["cost"] / nav_last * 100, 4),
        "CAGR_liquidation_scenario": round(((liq / KN.START_CASH) ** (1 / yrs) - 1) * 100, 2) if yrs > 0 and liq > 0 else None,
        "fills_by_status": by, "unfilled_or_retry_by_reason": why,
        "counts": {k: v for k, v in res["counts"].items() if not k.startswith(("buy_unfilled", "sell_retry"))},
        "notes": res.get("notes", {}),
        "cost_buy_pct_start": round(res["tot"]["buy_cost"] / KN.START_CASH * 100, 3),
        "cost_sell_pct_start": round(res["tot"]["sell_cost"] / KN.START_CASH * 100, 3),
        "conservation": {"daily_checks": res["counts"].get("checks", 0), "max_gap_cash_won": res["tot"].get("max_gap_cash", 0.0),
                         "max_gap_nav_identity_won": res["tot"].get("max_gap_nav", 0.0), "closed_positions_qty_fully_sold": qty_ok,
                         "closed_positions_qty_mismatch": qty_bad, "open_positions_wrongly_fully_sold": open_bad,
                         "max_slots_used": res.get("max_slots_used")},
    }
    return rep, s


def nav_csv(name, res):
    with open(OUT / f"nav_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "nav_norm", "cash_ratio", "invested_ratio", "gross_same_fills_norm"])
        g = dict(res["gross"])
        for d, nav, inv in res["nav"]:
            w.writerow([d, round(nav / KN.START_CASH, 6), round((nav - inv) / nav, 5) if nav else "", round(inv / nav, 5) if nav else "",
                        round(g[d] / KN.START_CASH, 6)])


def pos_csv(name, res):
    with open(OUT / f"positions_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entry_id", "code", "decision_at", "first_fill", "last_exit", "slots", "n_sells", "status", "ret_net_pct",
                    "pnl_net_pct_of_start", "cost_bp_of_entry"])
        for p in sorted(res["closed"] + res["open"], key=lambda x: (str(x["first_fill"]), x["pid"])):
            w.writerow([p["pid"], p["code"], p["decision_at"], p["first_fill"], p.get("last_exit") or "", p["slots"], p["n_sells"], p["status"],
                        round(p["ret_net"] * 100, 4), round(p["pnl_net"] / KN.START_CASH * 100, 5),
                        round((p["buy_cost"] + p["sell_cost"]) / p["invest0"] * 1e4, 2)])


def fills_csv(name, res):
    navd = {d: n for d, n, _ in res["nav"]}
    with open(OUT / f"fills_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entry_id", "code", "side", "decision_at", "fill_at", "status", "reason", "slots", "qty_share_of_entry",
                    "notional_pct_nav", "cost_bp"])
        for x in res["fills"]:
            nv = navd.get(str(x["fill_at"])[:8])
            w.writerow([x["pid"], x["code"], x["side"], x["decision_at"], x["fill_at"], x["status"], x.get("reason", ""), x.get("slots"),
                        x["qty_ratio"], round(x["notional"] / nv * 100, 4) if nv and x["notional"] else 0,
                        round(x["cost"] / x["notional"] * 1e4, 2) if x["notional"] else 0])


def pr39(key, mult):
    r = P39.get(f"{key}_x{mult}")
    return (r or {}).get("report", {}).get("전체") or {}


RESULTS, ROWS = {"meta": {"daily": META["meta"], "x_cut": META["x_cut"], "m15_window": [M15["lo"], M15["hi"]]}, "runs": {}}, {}
names = []
for _, key, _ in CORE:
    for m in ("x1", "x2", "x0"):
        names.append(f"{key}_{m}")
names += ["D1_close_x1", "ETF_engine_close_x1", "ETF_inverse_close_x1", "BASKET_close_x1"]
for n in names:
    res = load(n)
    periods = M15P if n.startswith("M15") else KN.PERIODS
    rep, s = summarize(n, res, periods)
    RESULTS["runs"][n] = {"report": rep, "summary": s}
    ROWS[n] = (rep, s)
    nav_csv(n, res)
    if n.endswith(("_x1", "_x2")) and "close" not in n:
        pos_csv(n, res)
        fills_csv(n, res)
    print(n, rep["전체"]["CAGR"], s["positions_closed"], s["positions_open_end"], flush=True)


# ───── 비교 기준과 순차 실행의 차이 ─────
def d1_vs_engine():
    res = load("D1_close_x1")
    ref = META["d1_reference"]
    eng = {(c, e, x) for c, e, x, _s, _p in ref}
    mine = {(f["code"], f["pid"].split(":")[1], f["fill_at"]) for f in res["fills"] if f["side"] == "sell" and f["status"] == "FILLED"}
    eb = {(c, e) for c, e, *_ in ref}
    mb = {(f["code"], f["fill_at"]) for f in res["fills"] if f["side"] == "buy" and f["status"] != "UNFILLED"}
    first = min([e for _, e in eb ^ mb] or [None], key=lambda x: x or "99999999")
    return {"engine_rows": len(ref), "engine_entries": len(eb), "seq_entries": len(mb), "entries_common": len(eb & mb),
            "entries_engine_only": len(eb - mb), "entries_seq_only": len(mb - eb), "exits_common": len(eng & mine),
            "exits_engine_only": len(eng - mine), "exits_seq_only": len(mine - eng), "first_entry_divergence": first,
            "cause": "같은 종가 근사 · 같은 함수. 다른 점은 돈 장부(현금이 1주 미만이면 칸을 비움 · 원 엔진은 칸만 셈)와 그 뒤 칸 차이의 연쇄"}


def m15_vs_ref():
    res = M15["runs"][1.0]
    ref = M15["reference"]
    rb = {(c, e) for c, e, x, k in ref}
    mb = {(f["code"], f["fill_at"]) for f in res["fills"] if f["side"] == "buy" and f["status"] != "UNFILLED"}
    rx = {(c, e, x.lstrip("끝")) for c, e, x, k in ref if not x.startswith("끝")}
    mx = {(f["code"], f["pid"].split(":")[1], f["fill_at"]) for f in res["fills"] if f["side"] == "sell" and f["status"] == "FILLED"}
    first = min([e for _, e in rb ^ mb] or [None], key=lambda x: x or "9" * 12)
    return {"ref_rows": len(ref), "ref_entries": len(rb), "seq_entries": len(mb), "entries_common": len(rb & mb),
            "entries_ref_only": len(rb - mb), "entries_seq_only": len(mb - rb), "exits_common": len(rx & mx),
            "exits_ref_only": len(rx - mx), "exits_seq_only": len(mx - rx), "ref_end_closures": sum(1 for r in ref if r[2].startswith("끝")),
            "first_entry_divergence": first}


def m15_cut():
    full, cut = M15["runs"][1.0], M15C["runs"][1.0]
    x = "20260115"
    key = lambda r: json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, sort_keys=True, default=str)
    fa = [key(r) for r in full["fills"] if str(r["fill_at"]) < x]
    fb = [key(r) for r in cut["fills"] if str(r["fill_at"]) < x]
    na = [(d, round(v, 4)) for d, v, _ in full["nav"] if d < x]
    nb = [(d, round(v, 4)) for d, v, _ in cut["nav"] if d < x]
    return {"cut": M15C["cut"], "how": "HLAB_CUT로 봉 · 일봉 재료를 처음부터 안 읽은 채 전 과정(신호 · 순위 · 실행) 다시",
            "fills_equal": fa == fb, "n_fills": len(fa), "nav_equal": na == nb, "n_days": len(na)}


REG = {"synthetic": json.load(open(TK, encoding="utf-8")), "synthetic_first_run": "10/11 — loss_boundary_strict 실패(정확히 −15%가 부동소수로 "
       "−0.15000000000000002가 되어 '넘음'으로 셈) → 경계 비교에 1e-12 여유 · 달 손실은 반올림 전 값으로 비교하게 고친 뒤 11/11",
       "cut_daily_executor": {k: v for k, v in META["cuts"].items()}, "cut_daily_how": f"{META['x_cut']} 뒤 가격 ×1.37 · 뒤 신호/사건 지움 → 그날까지 체결 · NAV · 상태(대기 요청 포함) 비교",
       "cut_m15_full_pipeline": m15_cut(), "d1_close_vs_engine_slot_ledger": d1_vs_engine(), "m15_vs_original_slot_sim": m15_vs_ref(),
       "ledger_files_read": 0}
RESULTS["regression"] = REG
(OUT / "regression.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
cons = {n: ROWS[n][1]["conservation"] for n in names}
(OUT / "conservation.json").write_text(json.dumps(cons, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
(OUT / "results.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


# ───── 표 ─────
def f(x, nd=2):
    return "" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


L = []
L.append("### 핵심 10판(전 기간 · 주 결과 = 끝 열린 포지션 MTM)\n")
L.append("| 전략 | 실행 | 비용 | 기간 | 포지션(닫힘/끝 열림) | 종목 | CAGR | 같은 체결 비용 전 | 비용 0 재거래 | 청산 시나리오 CAGR | 일별 MDD | Sharpe | Sortino | 최악 하루 | 최악 달 | −15% 넘음 하루/달 | PF | 승률 | 평균 포지션% | IID CI(참고) | 블록20 CI(연%) | 보유일 | 활용% | 비용 합(시작%) |")
L.append("|" + "---|" * 24)
for label, key, _ in CORE:
    for m in ("x1", "x2"):
        rep, s = ROWS[f"{key}_{m}"]
        a = rep["전체"]
        z = ROWS[f"{key}_x0"][0]["전체"]
        wm = f"{f(a['worst_month'])}({a['worst_month_at']}{'·부분월' if a['worst_month_partial'] else ''})"
        ci = f"{a['ci95_block20_ann_mean_ret_pct']}{' ' + a['ci_block_note'] if a['ci_block_note'] else ''}"
        L.append(f"| {label} | {EXEC[key]} | {m[1]}배 | {a['from']}~{a['to']} | {s['positions_closed']}/{s['positions_open_end']} | {a['codes']} | "
                 f"**{f(a['CAGR'])}** | {f(a['CAGR_gross_same_fills'])} | {f(z['CAGR'])} | {f(s['CAGR_liquidation_scenario'])} | {f(a['MDD_daily'])} | "
                 f"{f(a['Sharpe'])} | {f(a['Sortino'])} | {f(a['worst_day'])} | {wm} | {a['day_breach_-15']}/{a['month_breach_-15']} | {f(a['PF'], 3)} | "
                 f"{f(a['win_rate'], 1)} | {f(a['avg_pos_ret_pct'], 3)} | {a['ci95_pos_iid_ref']} | {ci} | {f(a['avg_hold_tdays'], 1)} | "
                 f"{f(a['utilization_avg_pct'], 1)} | {f(a['cost_total_pct_of_base'])} |")
L.append("\n### 참고: 종가 근사(같은 날 종가 체결 · 원본 15:10 실행 재현 불가 · 비용 1배)\n")
L.append("| 판 | CAGR | MDD | 최악 달 | −15% 넘음 하루/달 | 포지션 | PF | Sortino |")
L.append("|---|---|---|---|---|---|---|---|")
for n, lab in (("D1_close_x1", "1일봉"), ("ETF_engine_close_x1", "빈칸 엔진"), ("ETF_inverse_close_x1", "코스닥 인버스"), ("BASKET_close_x1", "바구니 C")):
    a = ROWS[n][0]["전체"]
    L.append(f"| {lab} | {f(a['CAGR'])} | {f(a['MDD_daily'])} | {f(a['worst_month'])}({a['worst_month_at']}) | {a['day_breach_-15']}/{a['month_breach_-15']} | "
             f"{a['positions']} | {f(a['PF'], 3)} | {f(a['Sortino'])} |")
L.append("\n### PR #39 산술 결과 → 이번 순차 재실행(같은 이름 판 · 전 기간)\n")
L.append("| 판 | CAGR PR39 → 지금 | MDD | 최악 달 | Sortino(PR39 식 → RMS 식) | 매매(PR39 행) → 포지션 | 달 −15% 넘음 |")
L.append("|---|---|---|---|---|---|---|")
for label, key, k39 in CORE:
    for m in ("x1", "x2"):
        a, b = pr39(k39, m[1]), ROWS[f"{key}_{m}"][0]["전체"]
        L.append(f"| {label} {m[1]}배 | {f(a.get('CAGR'))} → **{f(b['CAGR'])}** | {f(a.get('MDD_daily'))} → {f(b['MDD_daily'])} | "
                 f"{f(a.get('worst_month'))} → {f(b['worst_month'])} | {f(a.get('Sortino'))} → {f(b['Sortino'])} | {a.get('trades')} → {b['positions']} | "
                 f"{a.get('month_breach_-15')} → {b['month_breach_-15']} |")
L.append("\n### 기간별(핵심 1배 · 모두 이미 본 기간)\n")
L.append("| 전략 | 기간 | 기준 | CAGR | MDD | 최악 달 | 넘음 하루/달 | 포지션 | PF | 블록20 CI(연%) |")
L.append("|---|---|---|---|---|---|---|---|---|---|")
for label, key, _ in CORE:
    for p, a in ROWS[f"{key}_x1"][0].items():
        if not a:
            L.append(f"| {label} | {p} | 자료 없음 | | | | | | | |")
            continue
        L.append(f"| {label} | {p} | {a['base']} | {f(a['CAGR'])} | {f(a['MDD_daily'])} | {f(a['worst_month'])}({a['worst_month_at']}) | "
                 f"{a['day_breach_-15']}/{a['month_breach_-15']} | {a['positions']} | {f(a['PF'], 3)} | {a['ci95_block20_ann_mean_ret_pct']} {a['ci_block_note']} |")
L.append("\n### 실행 결손 · 가정 건수(핵심 1배)\n")
L.append("| 전략 | 체결 상태 | 못 삼/미룸 까닭 | ADV 없음 체결 | 세금 가정 체결 | 기타 |")
L.append("|---|---|---|---|---|---|")
for label, key, _ in CORE:
    s = ROWS[f"{key}_x1"][1]
    L.append(f"| {label} | {s['fills_by_status']} | {s['unfilled_or_retry_by_reason'] or '없음'} | {s['counts'].get('adv_missing_fills', 0)} | "
             f"{s['counts'].get('tax_unknown_fills', 0)} | {s['notes']} |")
(OUT / "tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("끝")
