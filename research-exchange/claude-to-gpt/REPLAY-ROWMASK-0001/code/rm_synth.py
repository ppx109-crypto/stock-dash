"""REPLAY-ROWMASK-0001 · 합성 3사례(손익 없음) — 정상 추가 · 마지막 5일 · 중단 종목(+ 추가 사례: 신규 상장 · 종목 길이 문턱).
python3 -E -P rm_synth.py <b2> <V> <출력.json>
가짜 종목(Z9000x · 자료 파일 없음)의 종가만 만들어 고정 엔진 lab.build로 줄을 만들고, 잘라낸 입력(앞 380일)과 긴 입력(400일)을 견줌."""
import json, os, sys
from pathlib import Path
import numpy as np
B2, V, OUTF = sys.argv[1], sys.argv[2], sys.argv[3]
os.chdir(V)
sys.path[:0] = [B2]
import lab, study
cal = [d for d, _ in study.load_prices()["005930"]["rows"] if d <= "20260331"][-400:]
rng = np.random.default_rng(20261008)
walk = lambda n: [round(10000 * float(x), 2) for x in np.exp(np.cumsum(rng.normal(0.0005, 0.02, n)))]
P = {"Z90001": {"name": "정상", "rows": list(zip(cal, walk(400)))},
     "Z90002": {"name": "마지막5일", "rows": list(zip(cal, walk(400)))},
     "Z90003": {"name": "중단", "rows": list(zip(cal[:300], walk(300)))},
     "Z90004": {"name": "신규 상장(추가 사례)", "rows": list(zip(cal[215:], walk(185)))}}
cut = cal[379]


def build(prices, upto):
    pp = {c: {"name": b["name"], "rows": [x for x in b["rows"] if x[0] <= upto]} for c, b in prices.items()}
    rep = {(r["code"], r["date"]): {k: v for k, v in r.items() if k != "ahead"} for r in lab.build(pp, horizons=(0,))}
    orig = {(r["code"], r["date"]) for r in lab.build(pp, horizons=(5, 10, 20, 60))}
    return rep, orig


full_rep, full_orig = build(P, cal[-1])
pre_rep, pre_orig = build(P, cut)
res = {}
same_pre = all(full_rep.get(k) == v for k, v in pre_rep.items())
miss_pre = [k for k in full_rep if k[1] <= cut and k not in pre_rep]
res["정상 추가(앞 380일 vs 400일, 고친 조건)"] = {"prefix_rows": len(pre_rep), "same_values": same_pre, "rows_missing_in_prefix": len(miss_pre)}
res["옛 조건(5 in ahead) 같은 비교"] = {"prefix_orig_rows": len(pre_orig), "full_orig_rows_le_cut": sum(1 for k in full_orig if k[1] <= cut),
                                     "lost_at_prefix_end": len({k for k in full_orig if k[1] <= cut} - pre_orig)}
z2_last5 = cal[-5:]
res["마지막 5일(Z90002)"] = {"repaired_rows_in_last5": sum(1 for d in z2_last5 if ("Z90002", d) in full_rep),
                         "orig_rows_in_last5": sum(1 for d in z2_last5 if ("Z90002", d) in full_orig)}
z3 = cal[:300]
res["중단 종목(Z90003, 300일째 끝 · 다른 종목은 400일)"] = {
    "repaired_last_row": max(d for c, d in full_rep if c == "Z90003"), "series_last_day": z3[-1],
    "orig_last_row": max(d for c, d in full_orig if c == "Z90003"),
    "orig_lost_rows_before_halt": sum(1 for d in z3[-5:] if ("Z90003", d) not in full_orig),
    "repaired_same_in_prefix_and_full": all(full_rep.get(k) == v for k, v in pre_rep.items() if k[0] == "Z90003")}
res["추가 · 신규 상장(Z90004, 앞 묶음 끝에 가격 165개 · 긴 묶음 185개 · 옛 길이 문턱 > 180)"] = {
    "prefix_repaired_rows": sum(1 for k in pre_rep if k[0] == "Z90004"), "full_repaired_rows_le_cut": sum(1 for k in full_rep if k[0] == "Z90004" and k[1] <= cut),
    "prefix_orig_rows": sum(1 for k in pre_orig if k[0] == "Z90004"), "full_orig_rows_le_cut": sum(1 for k in full_orig if k[0] == "Z90004" and k[1] <= cut)}
res["pass"] = (same_pre and not miss_pre and res["마지막 5일(Z90002)"]["repaired_rows_in_last5"] == 5
               and res["중단 종목(Z90003, 300일째 끝 · 다른 종목은 400일)"]["repaired_last_row"] == z3[-1])
Path(OUTF).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
