"""NEW-RULES-0001 실행: Train 12실험 × 비용 1 · 2배 → PREREG §5 선택 → 고정 1개만 이어 돌려 Validation 한 번 → 증거.
python3 -E -P run_nr.py <00b98ab1 작업 폴더(etf-data)> <출력 evidence 폴더>
네트워크 막음 · 키 환경변수 지움 · 운영 파일 안 고침 · 출력은 정규화 NAV · 비율 · 날짜 · 코드만(원시 가격 · 주 수 없음)."""
import csv
import json
import os
import socket
import sys
import time
from pathlib import Path

BASE, OUT = str(Path(sys.argv[1]).resolve()), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel2 as KN  # noqa: E402
import nr_engine as E  # noqa: E402

T0 = time.time()
TRAIN = ("20120102", "20181228")
VALID = ("20190102", "20221229")
DIAG = ("20230102", "20260930")
CASH = 1e7
P_TRAIN = (("Train 2012-01~2018-12", TRAIN[0], TRAIN[1]),)
P_FULL = (("Train 2012-01~2018-12", TRAIN[0], TRAIN[1]), ("Validation 2019-01~2022-12", VALID[0], VALID[1]),
          ("진단 2023-01~2026-09(이미 봄)", DIAG[0], DIAG[1]), ("전체", "00000000", "99999999"))

cal_t, data_t, fix_t = E.load(BASE, E.U, end=TRAIN[1])          # Train만 읽음(뒤 기간을 보지 않음)
print("Train 자료", cal_t[0], cal_t[-1], "고친 자료", fix_t, flush=True)


def metrics(res, periods, cash0):
    KN.START_CASH = cash0
    rep = KN.report(res["nav"], res["closed"], res["cal"], periods, res["gross"])
    for name, lo, hi in periods:
        a = rep.get(name)
        if not a:
            continue
        idx = [i for i, (d, _, _) in enumerate(res["nav"]) if lo <= d <= hi]
        navs = [res["nav"][i][1] for i in idx]
        invs = [res["nav"][i][2] for i in idx]
        traded = sum(f["notional"] for f in res["fills"] if lo <= str(f["fill_at"])[:8] <= hi and f["status"] in ("FILLED", "REDUCED"))
        yrs = KN._years(res["nav"][idx[0]][0], res["nav"][idx[-1]][0]) or 1
        attr = {}
        for d, day in res["attr_by_day"]:
            if lo <= d <= hi:
                for c, v in day.items():
                    attr[c] = attr.get(c, 0.0) + v
        tot = sum(attr.values())
        top = max(attr.items(), key=lambda x: x[1]) if attr else (None, 0.0)
        a.update({"turnover_per_year": round(traded / 2 / (sum(navs) / len(navs)) / yrs, 2),
                  "cash_ratio_avg_pct": round(100 - sum(i / n for i, n in zip(invs, navs)) / len(navs) * 100, 1),
                  "pnl_by_code_pct_of_start": {c: round(v / cash0 * 100, 3) for c, v in sorted(attr.items(), key=lambda x: -x[1])},
                  "pnl_total_pct_of_start": round(tot / cash0 * 100, 3),
                  "top_code": top[0], "top_code_share_pct": round(top[1] / tot * 100, 1) if tot > 0 else None})
    return rep


def ok_risk(a):
    return a["day_breach_-15"] == 0 and a["month_breach_-15"] == 0 and a["MDD_daily"] > -15.0


# ── 1. Train 24판 ──
TR = {}
for exp in E.EXPERIMENTS:
    for m in (1.0, 2.0):
        res = E.run((cal_t, data_t), exp, m, CASH, TRAIN[0], TRAIN[1])
        rep = metrics(res, P_TRAIN, CASH)
        TR[(exp, m)] = (res, rep[P_TRAIN[0][0]])
        a = rep[P_TRAIN[0][0]]
        print(exp, m, a["CAGR"], a["MDD_daily"], a["worst_month"], a["top_code"], a["top_code_share_pct"], round(time.time() - T0), "초", flush=True)

# ── 2. 선택(PREREG §5) ──
rows, passed = [], []
for exp in E.EXPERIMENTS:
    a1, a2 = TR[(exp, 1.0)][1], TR[(exp, 2.0)][1]
    c1 = ok_risk(a1) and ok_risk(a2)
    c2 = (a2["CAGR"] or -1) > 0
    share = a2["top_code_share_pct"]
    c3 = a2["pnl_total_pct_of_start"] <= 0 or (share is not None and share <= 50.0)
    rows.append({"exp": exp, "rule": E.EXPERIMENTS[exp][0], "params": E.EXPERIMENTS[exp][1], "c1_risk": c1, "c2_cagr2_pos": c2,
                 "c3_concentration": c3, "CAGR_x1": a1["CAGR"], "CAGR_x2": a2["CAGR"], "MDD_x1": a1["MDD_daily"], "MDD_x2": a2["MDD_daily"],
                 "worst_day_x1": a1["worst_day"], "worst_month_x1": a1["worst_month"], "worst_day_x2": a2["worst_day"],
                 "worst_month_x2": a2["worst_month"], "breach_x1": [a1["day_breach_-15"], a1["month_breach_-15"]],
                 "breach_x2": [a2["day_breach_-15"], a2["month_breach_-15"]], "top_code_x2": a2["top_code"], "top_share_x2": share,
                 "turnover_x1": a1["turnover_per_year"], "cash_avg_x1": a1["cash_ratio_avg_pct"], "util_x1": a1["utilization_avg_pct"],
                 "Sharpe_x1": a1["Sharpe"], "Sortino_x1": a1["Sortino"]})
    if c1 and c2 and c3:
        passed.append(rows[-1])
order = list(E.EXPERIMENTS)
passed.sort(key=lambda r: (-r["CAGR_x2"], order.index(r["exp"])))
chosen = None
if passed:
    best = passed[0]["CAGR_x2"]
    tie = [r for r in passed if best - r["CAGR_x2"] <= 0.5]
    tie.sort(key=lambda r: (-r["MDD_x2"], order.index(r["exp"])))
    chosen = tie[0]["exp"]
SEL = {"rows": rows, "passed": [r["exp"] for r in passed], "chosen": chosen, "rule": "PREREG §5: 위험 0 → 2배 CAGR>0 → 쏠림 ≤50% → 2배 CAGR 최고(0.5%p 동률이면 MDD)"}
print("선택:", chosen, "통과", SEL["passed"], flush=True)

# ── 3. 회귀: 자르기(규칙마다 한 실험) ──
REG = {"cut": {}}
X = "20160630"
for exp in ("A1", "B1", "C1"):
    full = TR[(exp, 1.0)][0]
    cut = E.run((cal_t, data_t), exp, 1.0, CASH, TRAIN[0], TRAIN[1], bump_after=X)
    key = lambda f: json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in f.items()}, sort_keys=True, default=str)
    fa = [key(f) for f in full["fills"] if str(f["fill_at"]) <= X]
    fb = [key(f) for f in cut["fills"] if str(f["fill_at"]) <= X]
    na = [(d, round(v, 4)) for d, v, _ in full["nav"] if d <= X]
    nb = [(d, round(v, 4)) for d, v, _ in cut["nav"] if d <= X]
    REG["cut"][exp] = {"x": X, "fills_equal": fa == fb, "n_fills": len(fa), "nav_equal": na == nb, "n_days": len(na)}
print("자르기", REG["cut"], flush=True)

# ── 4. 고정 1개만 Validation 한 번(+ 진단 · 용량) ──
FULL = {}
if os.environ.get("NR_TRAIN_ONLY") == "1":              # 점검용: Train 단계까지만(뒤 기간 자료를 읽지 않음)
    print("Train 단계 점검 끝(Validation 안 읽음)", round(time.time() - T0), "초", flush=True)
    sys.exit(0)
if chosen:
    cal_f, data_f, fix_f = E.load(BASE, E.U, end=DIAG[1])
    for m in (1.0, 2.0):
        for cash in (CASH, 1e8):
            res = E.run((cal_f, data_f), chosen, m, cash, TRAIN[0], DIAG[1])
            FULL[(m, cash)] = (res, metrics(res, P_FULL, cash))
    tr = TR[(chosen, 1.0)][0]
    full1 = FULL[(1.0, CASH)][0]
    same = [(d, round(v, 4)) for d, v, _ in tr["nav"]] == [(d, round(v, 4)) for d, v, _ in full1["nav"] if d <= TRAIN[1]]
    REG["train_only_equals_full_prefix"] = same
    REG["fixes_full"] = fix_f
    v1 = FULL[(1.0, CASH)][1][P_FULL[1][0]]
    v2 = FULL[(2.0, CASH)][1][P_FULL[1][0]]
    conds = {"risk_x1": ok_risk(v1), "risk_x2": ok_risk(v2), "cagr_x2_pos": (v2["CAGR"] or -1) > 0,
             "concentration": v2["pnl_total_pct_of_start"] <= 0 or (v2["top_code_share_pct"] is not None and v2["top_code_share_pct"] <= 50.0)}
    VERDICT = {"chosen": chosen, "conditions": conds, "verdict": "RESEARCH_CANDIDATE" if all(conds.values()) else "NO_CANDIDATE",
               "independent_validation": "WAITING_DATA"}
else:
    VERDICT = {"chosen": None, "conditions": None, "verdict": "NO_CANDIDATE", "independent_validation": "WAITING_DATA",
               "why": "Train 선택 조건을 통과한 실험 없음 · Validation 안 돌림"}
print("판정", VERDICT, flush=True)


# ── 5. 증거 ──
def nav_csv(name, res):
    with open(OUT / f"nav_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "nav_norm", "cash_ratio", "invested_ratio", "gross_same_fills_norm"])
        g = dict(res["gross"])
        for d, nav, inv in res["nav"]:
            w.writerow([d, round(nav / res["cash0"], 6), round((nav - inv) / nav, 5), round(inv / nav, 5), round(g[d] / res["cash0"], 6)])


def fills_csv(name, res):
    navd = {d: n for d, n, _ in res["nav"]}
    with open(OUT / f"fills_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lot_id", "code", "side", "decision_at", "fill_at", "status", "reason", "notional_pct_nav", "cost_bp"])
        for x in res["fills"]:
            nv = navd.get(str(x["fill_at"])[:8])
            w.writerow([x["pid"], x["code"], x["side"], x["decision_at"], x["fill_at"], x["status"], x.get("reason") or x.get("tag", ""),
                        round(x["notional"] / nv * 100, 4) if nv and x["notional"] else 0, round(x["cost"] / x["notional"] * 1e4, 2) if x["notional"] else 0])


def slim(rep):
    return {k: ({kk: vv for kk, vv in v.items()} if v else None) for k, v in rep.items()}


RESULTS = {"train": {f"{e}_x{m:g}": {"report": TR[(e, m)][1], "notes": TR[(e, m)][0]["notes"], "counts": TR[(e, m)][0]["counts"],
                                     "events": TR[(e, m)][0]["events"][:200], "liquidation_end": TR[(e, m)][0]["liquidation"]}
                     for e, m in TR},
           "selection": SEL, "verdict": VERDICT, "data_fixes_train": fix_t}
for (e, m), (res, _) in TR.items():
    nav_csv(f"train_{e}_x{m:g}", res)
for (m, cash), (res, rep) in FULL.items():
    tag = f"full_{chosen}_x{m:g}_{'1e7' if cash == CASH else '1e8'}"
    RESULTS[tag] = {"report": slim(rep), "notes": res["notes"], "counts": res["counts"], "events": res["events"],
                    "liquidation_end": res["liquidation"], "open_end": len(res["open"]), "pending_at_end": res["pending_at_end"]}
    nav_csv(tag, res)
    fills_csv(tag, res)
(OUT / "results.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
(OUT / "selection.json").write_text(json.dumps({"selection": SEL, "verdict": VERDICT}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
(OUT / "regression.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

L = ["### Train 12실험 × 비용 1 · 2배(2012-01-02 ~ 2018-12-28 · 시작 1천만 원 · 이미 노출된 기간)\n",
     "| 실험 | 규칙 | 설정 | CAGR 1배 | CAGR 2배 | MDD 1배 | MDD 2배 | 최악 하루 1배 | 최악 달 1배 | 넘음 하루/달(1배·2배) | 쏠림 최대 종목(2배) | 회전율/년 | 현금% | 활용% | Sharpe | Sortino | 위험 | 2배>0 | 쏠림 | 통과 |",
     "|" + "---|" * 20]
for r in rows:
    L.append(f"| {r['exp']} | {r['rule']} | {r['params']} | {r['CAGR_x1']} | {r['CAGR_x2']} | {r['MDD_x1']} | {r['MDD_x2']} | {r['worst_day_x1']} | "
             f"{r['worst_month_x1']} | {r['breach_x1']}·{r['breach_x2']} | {r['top_code_x2']} {r['top_share_x2']}% | {r['turnover_x1']} | {r['cash_avg_x1']} | "
             f"{r['util_x1']} | {r['Sharpe_x1']} | {r['Sortino_x1']} | {'O' if r['c1_risk'] else 'X'} | {'O' if r['c2_cagr2_pos'] else 'X'} | "
             f"{'O' if r['c3_concentration'] else 'X'} | {'**통과**' if r['exp'] in SEL['passed'] else ''} |")
L.append(f"\n고정: **{chosen}** · 판정: **{VERDICT['verdict']}** · 독립검증: {VERDICT['independent_validation']}\n")
if chosen:
    L.append("### 고정 1개 · 이어 돈 계좌의 기간별(Validation은 이 표가 유일한 적용)\n")
    L.append("| 판 | 기간 | CAGR | 같은 체결 비용 전 | MDD | 최악 하루 | 최악 달 | 넘음 하루/달 | 회전율/년 | 현금% | 활용% | Sharpe | Sortino | 쏠림 최대 | 순손익(시작%) |")
    L.append("|" + "---|" * 15)
    for (m, cash), (res, rep) in FULL.items():
        for p, a in rep.items():
            if not a:
                continue
            L.append(f"| {m:g}배 · {'1천만' if cash == CASH else '1억'} | {p} | {a['CAGR']} | {a['CAGR_gross_same_fills']} | {a['MDD_daily']} | {a['worst_day']} | "
                     f"{a['worst_month']}({a['worst_month_at']}) | {a['day_breach_-15']}/{a['month_breach_-15']} | {a['turnover_per_year']} | {a['cash_ratio_avg_pct']} | "
                     f"{a['utilization_avg_pct']} | {a['Sharpe']} | {a['Sortino']} | {a['top_code']} {a['top_code_share_pct']}% | {a['pnl_total_pct_of_start']} |")
    L.append("\n### 고정 1개 · 월별 수익(1배 · 1천만 원, %)\n")
    mon = FULL[(1.0, CASH)][1]["전체"]["monthly"]
    years = sorted({k[:4] for k in mon})
    L.append("| 해 | " + " | ".join(f"{i:02d}" for i in range(1, 13)) + " |")
    L.append("|" + "---|" * 13)
    for y in years:
        L.append(f"| {y} | " + " | ".join(f"{mon[y + f'{i:02d}'] * 100:.1f}" if y + f"{i:02d}" in mon else "" for i in range(1, 13)) + " |")
(OUT / "tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("끝", round(time.time() - T0), "초", flush=True)
