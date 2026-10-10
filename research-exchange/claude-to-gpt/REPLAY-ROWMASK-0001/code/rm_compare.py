"""REPLAY-ROWMASK-0001 · 구조 검사와 제거 전후 차이(손익 없음).
python3 -E -P rm_compare.py <rows 폴더> <옛 nrl-cache.pkl> <출력.json>
rows 폴더: rows_20260130.pkl · rows_20260227.pkl · rows_20260331.pkl · rows_full.pkl · signals_{old,20260130,20260227,20260331}.json"""
import json
import pickle
import sys
from collections import Counter
from pathlib import Path

D, OLD, OUTF = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
CUTS = ("20260130", "20260227", "20260331")
TLO, THI = "20250918", "20260331"
R = {c: pickle.load(open(D / f"rows_{c}.pkl", "rb")) for c in CUTS + ("full",)}
SG = {c: json.load(open(D / f"signals_{c}.json")) for c in ("old",) + CUTS}
key = lambda rows: {(r["code"], r["date"]): r for r in rows}


def rows_cmp(a, b, upto):
    A = {k: v for k, v in key(a).items() if k[1] <= upto}
    B = {k: v for k, v in key(b).items() if k[1] <= upto}
    diff = Counter()
    for k in set(A) & set(B):
        for f in set(A[k]) | set(B[k]):
            if A[k].get(f) != B[k].get(f):
                diff[f] += 1
    return {"rows_a": len(A), "rows_b": len(B), "only_a": len(set(A) - set(B)), "only_b": len(set(B) - set(A)),
            "only_b_dates": dict(Counter(k[1] for k in set(B) - set(A))), "only_a_dates": dict(Counter(k[1] for k in set(A) - set(B))),
            "value_diffs": dict(diff)}


def top100(rows, lo, hi):
    out = {}
    for r in rows:
        if lo <= r["date"] <= hi and r.get("시총순위") is not None and r["시총순위"] <= 100:
            out.setdefault(r["date"], set()).add((r["code"], r["시총순위"]))
    return out


def picks_cmp(a, b, lo, hi):
    days = sorted(set(d for d in a["picks"] if lo <= d <= hi) | set(d for d in b["picks"] if lo <= d <= hi))
    bad = {d: {"a": a["picks"].get(d, []), "b": b["picks"].get(d, [])} for d in days if a["picks"].get(d, []) != b["picks"].get(d, [])}
    br = [d for d in set(a["BR"]) | set(b["BR"]) if lo <= d <= hi and a["BR"].get(d) != b["BR"].get(d)]
    t = [d for d in set(a["top100"]) | set(b["top100"]) if lo <= d <= hi and a["top100"].get(d) != b["top100"].get(d)]
    return {"signal_days_a": sum(1 for d in a["picks"] if lo <= d <= hi), "signal_days_b": sum(1 for d in b["picks"] if lo <= d <= hi),
            "signal_rows_a": sum(len(v) for d, v in a["picks"].items() if lo <= d <= hi),
            "signal_rows_b": sum(len(v) for d, v in b["picks"].items() if lo <= d <= hi),
            "signal_diff_days": len(bad), "signal_diff_detail_first5": dict(list(bad.items())[:5]),
            "BR_diff_days": len(br), "top100_diff_days(엔진 inside 기준)": len(t),
            "days_a": len([d for d in a["days"] if lo <= d <= hi]), "days_b": len([d for d in b["days"] if lo <= d <= hi])}


res = {"cuts": CUTS, "last_price": {c: R[c]["last_price"] for c in R}}
# A. 고친 조건 · 앞 잘라낸 입력 vs 더 긴 입력
res["A_prefix_repaired"] = {}
for c in CUTS[:2]:
    t_a, t_b = top100(R[c]["repaired"], "20250801", c), top100(R["20260331"]["repaired"], "20250801", c)
    res["A_prefix_repaired"][f"{c}_vs_20260331"] = {
        "rows": rows_cmp(R[c]["repaired"], R["20260331"]["repaired"], c),
        "top100_diff_days": sum(1 for d in set(t_a) | set(t_b) if t_a.get(d) != t_b.get(d)),
        "signals": picks_cmp(SG[c], SG["20260331"], TLO, c)}
t_a, t_b = top100(R["20260331"]["repaired"], "20250801", THI), top100(R["full"]["repaired"], "20250801", THI)
res["A_prefix_repaired"]["20260331_vs_full(2026-09-23까지)"] = {"rows": rows_cmp(R["20260331"]["repaired"], R["full"]["repaired"], THI),
                                                            "top100_diff_days": sum(1 for d in set(t_a) | set(t_b) if t_a.get(d) != t_b.get(d))}
# B. 옛 조건 · 같은 비교(결함 보이기)
res["B_prefix_orig"] = {}
for c in CUTS:
    res["B_prefix_orig"][f"{c}_vs_full"] = rows_cmp(R[c]["orig"], R["full"]["orig"], c)
# C. Train 제거 전후(같은 입력 V · 같은 빌드에서 존재 조건만 다름)
rep_n = Counter(r["date"] for r in R["full"]["repaired"] if TLO <= r["date"] <= THI)
ori_n = Counter(r["date"] for r in R["full"]["orig"] if TLO <= r["date"] <= THI)
tr, to = top100(R["full"]["repaired"], TLO, THI), top100(R["full"]["orig"], TLO, THI)
res["C_train_before_after"] = {
    "days": len(rep_n), "rows_before(orig)": sum(ori_n.values()), "rows_after(repaired)": sum(rep_n.values()),
    "row_count_diff_days": {d: [ori_n.get(d, 0), rep_n.get(d, 0)] for d in sorted(set(rep_n) | set(ori_n)) if ori_n.get(d, 0) != rep_n.get(d, 0)},
    "row_value_diffs": rows_cmp(R["full"]["orig"], R["full"]["repaired"], THI)["value_diffs"],
    "top100_diff_days": sum(1 for d in set(tr) | set(to) if tr.get(d) != to.get(d)),
    "signals_old_cache(PR68 실제 입력)_vs_repaired_20260331": picks_cmp(SG["old"], SG["20260331"], TLO, THI)}
# D. 옛 캐시(PR68 입력) 상위100 줄과 고친 줄 직접 대조
O = pickle.load(open(OLD, "rb"))
oi = {(r["code"], r["date"]): r for r in O[4] if TLO <= r["date"] <= THI}
ri = {(r["code"], r["date"]): r for r in R["20260331"]["repaired"] if TLO <= r["date"] <= THI and (r.get("시총순위") or 999) <= 100}
dv = Counter()
for k in set(oi) & set(ri):
    for f in (set(oi[k]) | set(ri[k])) - {"ahead", "i"}:
        if oi[k].get(f) != ri[k].get(f):
            dv[f] += 1
res["D_old_cache_inside_vs_repaired_top100"] = {"old": len(oi), "repaired": len(ri), "only_old": len(set(oi) - set(ri)), "only_repaired": len(set(ri) - set(oi)),
                                               "value_diffs(ahead · i 빼고)": dict(dv)}
sig_diff = res["C_train_before_after"]["signals_old_cache(PR68 실제 입력)_vs_repaired_20260331"]["signal_diff_days"]
pre_ok = all(v["rows"]["only_a"] == 0 and v["rows"]["only_b"] == 0 and not v["rows"]["value_diffs"] and v["top100_diff_days"] == 0
             and v["signals"]["signal_diff_days"] == 0 and v["signals"]["BR_diff_days"] == 0 for k, v in res["A_prefix_repaired"].items() if "signals" in v)
res["structure_pass"] = pre_ok
res["train_signal_diff_days"] = sig_diff
res["portfolio_run_needed"] = sig_diff > 0
OUTF.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps({"structure_pass": pre_ok, "train_signal_diff_days": sig_diff, "C": {k: v for k, v in res["C_train_before_after"].items() if k != "row_count_diff_days"},
                  "D": res["D_old_cache_inside_vs_repaired_top100"]}, ensure_ascii=False, default=str))
