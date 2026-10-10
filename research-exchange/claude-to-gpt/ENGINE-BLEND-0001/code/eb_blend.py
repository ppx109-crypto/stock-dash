"""ENGINE-BLEND-0001 · PR #41 비용 2배 NAV 5개로 P4 · P5 고정 균등 결합(리밸런싱 없음) 산술. python3 eb_blend.py <evidence 폴더> <GPT_RESULTS.json>"""
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

EV = Path(sys.argv[1])
G = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
ENG = {"D1": "D1_next", "M15": "M15", "ETF": "ETF_engine_next", "INV": "ETF_inverse_next", "BASKET": "BASKET_next"}
SETS = {"P4": (["D1", "M15", "ETF", "BASKET"], 0.25), "P5": (["D1", "M15", "ETF", "INV", "BASKET"], 0.20)}
START = "20250918"


def load(name):
    rows = list(csv.DictReader(open(EV / "input" / f"nav_{ENG[name]}_x2.csv", encoding="utf-8")))
    return [(r["date"], float(r["nav_norm"])) for r in rows]


raw = {k: load(k) for k in ENG}
days = [d for d, _ in raw["M15"]]
assert days[0] == START and days[-1] == "20260831" and len(days) == 230, (days[0], days[-1], len(days))
norm, base = {}, {}
for k, rows in raw.items():
    m = dict(rows)
    if k == "M15":
        base[k] = ("파일 첫 행 앞 시작값", 1.0)
    else:
        prev = [d for d, _ in rows if d < START][-1]
        base[k] = (prev, m[prev])
    miss = [d for d in days if d not in m]
    if miss:
        raise SystemExit(f"BLOCKED: {k} 날짜 없음 {miss[:3]}")
    norm[k] = [m[d] / base[k][1] for d in days]


def stats(nav):
    seg = [1.0] + nav
    rets = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    peak, mdd, mdd_at = 1.0, 0.0, None
    for d, v in zip([None] + days, seg):
        peak = max(peak, v)
        if v / peak - 1 < mdd:
            mdd, mdd_at = v / peak - 1, d
    wd = min(range(len(rets)), key=lambda i: rets[i])
    months = {}
    for d, r in zip(days, rets):
        months[d[:6]] = months.get(d[:6], 1.0) * (1 + r)
    wm = min(months, key=months.get)
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    yrs = (D(days[-1]) - D(days[0])).days / 365.25
    return {"end_multiple": nav[-1], "end_won": nav[-1] * 1e7, "cagr_pct": (nav[-1] ** (1 / yrs) - 1) * 100, "MDD_pct": mdd * 100, "MDD_at": mdd_at,
            "worst_day_pct": rets[wd] * 100, "worst_day_at": days[wd], "worst_month_pct": (months[wm] - 1) * 100, "worst_month_at": wm,
            "day_breach_-15": sum(1 for r in rets if r < -0.15 - 1e-12), "month_breach_-15": sum(1 for v in months.values() if v - 1 < -0.15 - 1e-12),
            "months": {k: (v - 1) * 100 for k, v in months.items()}}


RES = {"base": base, "rows": len(days)}
for p, (names, w) in SETS.items():
    nav = [sum(w * norm[k][i] for k in names) for i in range(len(days))]
    nav_rev = [sum(w * norm[k][i] for k in names[::-1]) for i in range(len(days))]
    st = stats(nav)
    st["reverse_max_diff"] = max(abs(a - b) for a, b in zip(nav, nav_rev))
    g = G[p]
    tol = {"end_multiple": 1e-6, "end_won": 10.0, "cagr_pct": 0.01, "MDD_pct": 0.01, "worst_day_pct": 0.01, "worst_month_pct": 0.01}
    cmp_ = {k: {"gpt": g[k], "claude": st[k], "diff": st[k] - g[k], "same": abs(st[k] - g[k]) <= t} for k, t in tol.items()}
    for k in ("MDD_at", "worst_day_at", "worst_month_at", "day_breach_-15", "month_breach_-15"):
        cmp_[k] = {"gpt": g[k], "claude": st[k], "same": g[k] == st[k]}
    st["vs_gpt"] = cmp_
    st["engine_end_norm"] = {k: norm[k][-1] for k in names}
    st["engine_terminal_share_pct"] = {k: w * norm[k][-1] / nav[-1] * 100 for k in names}
    RES[p] = st
    with open(EV / f"blend_{p}.csv", "w", encoding="utf-8") as f:
        f.write("date,nav_multiple," + ",".join(f"{k}_norm" for k in names) + "\n")
        for i, d in enumerate(days):
            f.write(f"{d},{nav[i]:.12f}," + ",".join(f"{norm[k][i]:.12f}" for k in names) + "\n")
    print(p, {k: v for k, v in st.items() if k not in ("vs_gpt", "months")}, flush=True)
    print(p, "GPT 대조", {k: v["same"] for k, v in cmp_.items()}, flush=True)
crit = {}
for p in SETS:
    s = RES[p]
    crit[p] = {"day_ok": s["day_breach_-15"] == 0, "month_ok": s["month_breach_-15"] == 0, "mdd_ok": s["MDD_pct"] >= -15.0, "end_gt_10m": s["end_won"] > 1e7}
all_match = all(v["same"] for p in SETS for v in RES[p]["vs_gpt"].values())
cand = [p for p in SETS if all(crit[p].values())]
RES["criteria"] = crit
RES["all_match_gpt"] = all_match
RES["verdict"] = ("TRAIN_CANDIDATE_LOCKED" if cand else ("AXIS_ENDED" if all(not crit[p]["mdd_ok"] and not crit[p]["month_ok"] for p in SETS) else "AXIS_ENDED(기준 일부)")) if all_match else "불일치"
RES["verdict_if_mdd_month_are_report_only"] = [p for p in SETS if crit[p]["day_ok"] and crit[p]["end_gt_10m"]]
print("판정", crit, RES["verdict"], "· MDD/달을 보고만 할 때 통과", RES["verdict_if_mdd_month_are_report_only"], flush=True)
(EV / "eb_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
