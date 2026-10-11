"""MIX-0054 결과 보고 전용 — 최종 칸 다시 셈(같은 설정 · 결정적) · 빚 없음 점검 · 덜기 횟수 · 돈 쓰임 어림. 판정 · 고르기와 무관.
기록: evidence/report_evals.jsonl(STARTED · DONE)."""
import csv, json, os, sys, time
from pathlib import Path
os.environ["REG_BOX"] = "MIX-0054"
sys.path.insert(0, "/home/user/stock-dash/research")
import mix54_run as M
import regime_dev as D
B = M.BOX
LOG = B / "evidence/report_evals.jsonl"
out = {}
for g, ov in ((M.NOW, "none"), ((0.5, 0.3), "none"), ((0.5, 0.3), "L0.4_S0.4"), ((0.5, 0.3), "L0.2_S0.2"), ((0.5, 0.3), "L0.25_S0.3")):
    key = f"{M.name(g)}+{ov}"
    M.log(LOG, {"status": "STARTED", "key": key, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    D.BASE_CSV = M.BASES / f"{M.name(g)}.csv"; D.DATA, D.FEAT = None, None
    cfg = dict(D.R0) if M.OVERLAYS[ov] is None else dict(D.R0, **M.OVERLAYS[ov])
    navs, nst = D.account(cfg)
    r = D.stats(navs, nst)
    rows = {x["날"]: x for x in csv.DictReader(open(D.BASE_CSV))}
    base_use, etf_w = [], []
    feat = D.FEAT[1]
    for d in navs:
        if d not in rows or d not in nst:
            continue
        cash_r = float(rows[d]["현금"]) / float(rows[d]["NAV"])
        base_use.append(1 - cash_r)
        if M.OVERLAYS[ov] is not None:
            fb, code, fe = D.targets(nst[d], cfg, feat.get(d))
            etf_w.append(min(fe, fb * cash_r + (1 - fb)))
    days = {k: sum(1 for v in nst.values() if v == k) for k in ("상승", "횡보", "하락")}
    rec = {"annual_pct": r["annual_pct"], "worst_day_pct": r["worst_day_pct"], "worst_month_pct": r["worst_month_pct"], "mdd_report_pct": r["mdd_report_pct"],
           "min_cash_slack": D.account.min_slack, "etf_trims": D.account.trims, "base_trims": D.account.base_trims,
           "base_money_use_pct": round(100 * sum(base_use) / len(base_use), 2),
           "etf_target_weight_avg_pct_approx": round(100 * sum(etf_w) / len(etf_w), 2) if etf_w else 0.0,
           "state_days": days}
    M.log(LOG, {"status": "DONE", "key": key, **rec})
    out[key] = rec
print(json.dumps(out, ensure_ascii=False, indent=1))
