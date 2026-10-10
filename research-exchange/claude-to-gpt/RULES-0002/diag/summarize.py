"""RULES-0002 요약 — d1_result.json · {m15,h1k}_{판}.json → float_impact.{json,csv} · flow_lag_impact.{json,csv}.
python summarize.py <꺼낸 폴더(perf2 비용용)> <results 폴더>"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as K  # noqa: E402

BASE, R = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(BASE), str(BASE / "research")]
import socket  # noqa: E402
socket.socket = K._blocked
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import perf2 as P  # noqa: E402

d1 = json.loads((R / "d1_result.json").read_text(encoding="utf-8"))
intr = {}
for part in ("m15", "h1k"):
    for v in ("ASIS", "FLOAT-V1", "FLOW-LAG2", "FLOW-LAG3"):
        p = R / f"{part}_{v}.json"
        intr[(part, v)] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def group(led):
    g = {}
    for t in led:
        g.setdefault((t[0], t[1]), []).append(tuple(t[2:]))
    return {k: sorted(v) for k, v in g.items()}


def acct(rows):
    return sum(r[1] * r[2] / 10 for r in rows)


def recost_intraday(led, scale):
    """엔진 손익(왕복 0.30% 뺀 값) → 비용 전 어림 → perf2 비용(가정: 1억 계좌 · 칸/10 몫)."""
    tot = 0.0
    for c, b, e, p, k in led:
        g = (1 + p / 100) / (1 - 0.003) - 1
        cb, cs = P.side_costs(c, b[:8], e[:8], 1e8 * k / 10, scale)
        tot += ((1 + g) * (1 - cb) * (1 - cs) - 1) * 100 * k / 10
    return tot


def cmp(a, b):
    A, B = group(a), group(b)
    com = set(A) & set(B)
    ch = [k for k in com if A[k] != B[k]]
    diffs = [acct(B[k]) - acct(A[k]) for k in ch]
    return {"asis_trades": len(A), "variant_trades": len(B), "common": len(com), "only_asis": len(set(A) - set(B)),
            "only_variant": len(set(B) - set(A)), "common_changed": len(ch),
            "changed_acctpct_diff": K.describe(diffs), "changed_ci_cluster_code": K.boot_ci(diffs, groups=[k[0] for k in ch]) if diffs else None,
            "acctpct_sum_asis": sum(acct(v) for v in A.values()), "acctpct_sum_variant": sum(acct(v) for v in B.values()),
            "changed": [{"code": k[0], "entry": k[1], "asis": A[k], "variant": B[k]} for k in sorted(ch)]}


float_out, flow_out, fl_rows, fw_rows = {"D1": {}, "M15": {}, "H1": {}}, {"D1": {}, "M15": {}, "H1": {}}, [], []
# D1
f1 = d1["F1"]
float_out["D1"] = {"evaluations_with_repeats": f1["evaluations_with_repeats(8씨앗·두 반)"], "mismatch_unique_by_rule": f1["mismatch_unique"],
                   "trade_compare_seed0": {k: v for k, v in d1["pairs_vs_ASIS"]["FLOAT-V1"]["trades"].items() if k != "changed_detail"},
                   "engine_8seed_identical": d1["runs"]["ASIS"]["metrics_engine(8씨앗·엔진 비용 0.25%)"] == d1["runs"]["FLOAT-V1"]["metrics_engine(8씨앗·엔진 비용 0.25%)"],
                   "daily_mtm_delta": d1["pairs_vs_ASIS"]["FLOAT-V1"]["daily_diff"], "tick_exposure_seed0_entries": f1["tick_exposure_seed0_entries"],
                   "nonint_price_rows": f1["nonint_price_rows_in_cache"]}
log = R / "d1_float_mismatch_log.csv"
if log.exists():
    for r in pd.read_csv(log, dtype=str).drop_duplicates(subset=["rule", "code", "entry_day", "step"]).to_dict("records"):
        fl_rows.append({"strategy": "D1", **{k: r[k] for k in ("rule", "code", "entry_day", "day", "step", "price", "close", "float", "exact")},
                        "trade_outcome_changed": "no"})
for v in ("FLOW-LAG2", "FLOW-LAG3"):
    p = d1["pairs_vs_ASIS"][v]
    flow_out["D1"][v] = {"candidates": d1["F2_candidates"][v], "trades_seed0": {k: x for k, x in p["trades"].items() if k != "changed_detail"},
                         "changed_trade_acctpct_diff": p.get("changed_trade_pnl_diff"),
                         "engine_8seed": d1["runs"][v]["metrics_engine(8씨앗·엔진 비용 0.25%)"],
                         "engine_8seed_asis": d1["runs"]["ASIS"]["metrics_engine(8씨앗·엔진 비용 0.25%)"],
                         "daily_mtm(seed0 · a_mtm · 1D 계좌 전체 크기)": {sc: {"asis": d1["runs"]["ASIS"]["scales"][sc]["전체"], "variant": d1["runs"][v]["scales"][sc]["전체"],
                                                                         "delta": p["daily_diff"][sc]} for sc in ("BASE", "STRESS", "EXTREME")}}
    for sc in ("BASE", "STRESS", "EXTREME"):
        a, b = d1["runs"]["ASIS"]["scales"][sc]["전체"], d1["runs"][v]["scales"][sc]["전체"]
        fw_rows.append({"strategy": "D1", "variant": v, "scale": sc, "CAGR_asis": a["CAGR"], "CAGR_variant": b["CAGR"], "MDD_asis": a["MDD"], "MDD_variant": b["MDD"],
                        "worst_day_asis": a["나쁜날"], "worst_day_variant": b["나쁜날"], "worst_month_asis": a["나쁜달"], "worst_month_variant": b["나쁜달"],
                        "paired_daily_diff_mean": p["daily_diff"][sc]["paired_daily_diff"]["mean"], "paired_daily_diff_ci_lo": (p["daily_diff"][sc]["paired_daily_diff_ci_block20"] or [None, None])[0],
                        "paired_daily_diff_ci_hi": (p["daily_diff"][sc]["paired_daily_diff_ci_block20"] or [None, None])[1]})
# 15m · 1h
for part, key in (("m15", "M15"), ("h1k", "H1")):
    base = intr[(part, "ASIS")]
    if base is None:
        float_out[key] = flow_out[key] = {"status": "미실행"}
        continue
    fv = intr[(part, "FLOAT-V1")]
    if fv:
        mm = pd.DataFrame(base["mismatch"] + fv["mismatch"])
        uniq = mm.drop_duplicates(subset=["rule", "code", "entry_bar", "bar"]) if len(mm) else mm
        c = cmp(base["ledger"], fv["ledger"])
        float_out[key] = {"evaluations_asis": base["evaluations"], "evaluations_v1": fv["evaluations"],
                          "mismatch_unique_by_rule": uniq.groupby("rule").size().to_dict() if len(uniq) else {},
                          "trade_compare": c, "transcription_check": base["asis_transcription_check"],
                          "cost_scaled_acctpct_sum": {sc: {"asis": recost_intraday(base["ledger"], s), "variant": recost_intraday(fv["ledger"], s)} for sc, s in P.SCALES.items()},
                          "daily_mtm": "검증하지 못함(장중 진입 · 청산가가 일봉 종가와 달라 날마다 평가를 재구성할 수 없음)"}
        for r in uniq.to_dict("records") if len(uniq) else []:
            fl_rows.append({"strategy": key, "rule": r["rule"], "code": r["code"], "entry_day": r["entry_bar"], "day": r["bar"], "step": r["held"],
                            "price": r["price"], "close": r["close"], "float": r["float"], "exact": r["exact"], "trade_outcome_changed": "see trade_compare"})
    for v in ("FLOW-LAG2", "FLOW-LAG3"):
        x = intr[(part, v)]
        if not x:
            flow_out[key][v] = {"status": "미실행"}
            continue
        A = {}
        for c_, d_ in base["signal_days"]:
            A.setdefault(d_, set()).add(c_)
        B = {}
        for c_, d_ in x["signal_days"]:
            B.setdefault(d_, set()).add(c_)
        days = sorted(set(A) | set(B))
        jac = [len(A.get(d, set()) & B.get(d, set())) / len(A.get(d, set()) | B.get(d, set())) for d in days]
        flags = {"teach_changed": 0, "steady_changed": 0, "both_known": 0, "noncomparable": 0}
        for code, dd in base["att_flags"].items():
            for d, (t0, s0, e0) in dd.items():
                t1 = x["att_flags"].get(code, {}).get(d)
                if t1 is None:
                    flags["noncomparable"] += 1
                    continue
                flags["both_known"] += 1
                flags["teach_changed"] += t0 != t1[0]
                flags["steady_changed"] += s0 != t1[1]
        c = cmp(base["ledger"], x["ledger"])
        flow_out[key][v] = {"signal_days": len(days), "signal_changed_days": sum(1 for d in days if A.get(d, set()) != B.get(d, set())),
                            "jaccard": K.describe(jac), "jaccard_ci": K.boot_ci(jac),
                            "new_signals": sum(len(B.get(d, set()) - A.get(d, set())) for d in days),
                            "gone_signals": sum(len(A.get(d, set()) - B.get(d, set())) for d in days),
                            "att_flags(종목·날)": flags, "trade_compare": c,
                            "cost_scaled_acctpct_sum": {sc: {"asis": recost_intraday(base["ledger"], s), "variant": recost_intraday(x["ledger"], s)} for sc, s in P.SCALES.items()},
                            "summary_asis": base["summary"], "summary_variant": x["summary"],
                            "daily_mtm": "검증하지 못함(장중 가격)"}
        for sc, s in P.SCALES.items():
            fw_rows.append({"strategy": key, "variant": v, "scale": sc, "acctpct_sum_asis": recost_intraday(base["ledger"], s),
                            "acctpct_sum_variant": recost_intraday(x["ledger"], s), "trades_asis": c["asis_trades"], "trades_variant": c["variant_trades"],
                            "common": c["common"], "common_changed": c["common_changed"], "jaccard_median": float(np.median(jac)) if jac else None})
(R / "float_impact.json").write_text(json.dumps(float_out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
(R / "flow_lag_impact.json").write_text(json.dumps(flow_out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
pd.DataFrame(fl_rows).to_csv(R / "float_impact_decisions.csv", index=False)
pd.DataFrame(fw_rows).to_csv(R / "flow_lag_impact_summary.csv", index=False)
print("요약 끝", len(fl_rows), len(fw_rows))
