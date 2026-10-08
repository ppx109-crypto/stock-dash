"""고정 원장 old-vs-corrected 비용차(수익률 단위 진단) — 새 가격조회 · 신호 계산 없음.
python3 -I run_replay.py <d1_ledger_ASIS.csv> <출력폴더> [--perf2-check]
- 원장 sha256이 PREREG-LOCK 값과 다르면 멈춤.
- 시장: 저장소 kosdaq-data(현재 기준)에 있으면 KOSDAQ, 아니면 KOSPI 추정(시점 기준 아님).
- 금액 · NAV 지표는 만들지 않음(NEEDS_DATA).
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cost_contract as C  # noqa: E402

LEDGER_SHA = "86c5f56df56d8a7ac5b691152343568d8436f1bea90c10add318bbd9b354209b"
ACC = 1e8                               # RULES-0002 / z058 Z_ACC 기본값(가정)
src, out = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_bytes()
assert hashlib.sha256(raw).hexdigest() == LEDGER_SHA, "원장 hash 불일치"
rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
KQ = {p.stem for p in (C.ROOT / "kosdaq-data").glob("*.json")}
assert len(KQ) == 1697, len(KQ)


def market(code):
    return "KOSDAQ" if code in KQ else "KOSPI"


def pf(xs):
    w = sum(x for x in xs if x > 0)
    l = -sum(x for x in xs if x <= 0)
    return w / l if l > 0 else None


det, perf2_diff = [], None
if "--perf2-check" in sys.argv:                       # 복사 정확성 대조(원본 perf2 읽기 전용 import)
    sys.path.insert(0, str(C.ROOT / "research"))
    import perf2 as P
    perf2_diff = 0.0
    for r in rows:
        for sc in C.SCALES.values():
            n = ACC * int(r["slots"]) / 10
            a = P.side_costs(r["code"], r["entry"], r["exit"], n, sc)
            b = C.old_side_costs(r["code"], r["entry"], r["exit"], n, sc)
            perf2_diff = max(perf2_diff, abs(a[0] - b[0]), abs(a[1] - b[1]))

for r in rows:
    code, b, e, p, k = r["code"], r["entry"], r["exit"], float(r["pnl_pct_engine"]), int(r["slots"])
    mk = market(code)
    n = ACC * k / 10
    d = {"code": code, "entry": b, "exit": e, "slots": k, "market_assumed": mk, "pnl_pct_engine": p}
    for sn, sc in C.SCALES.items():
        cb, cs = C.old_side_costs(code, b, e, n, sc)
        d[f"old_{sn}"] = C.recost_row(p, cb, cs)
        for scen in C.SCENARIOS:
            try:
                cb2, cs2 = C.corrected_side_costs(code, b, e, n, mk, sc, "STOCK", scen)
                d[f"new_{scen}_{sn}"] = C.recost_row(p, cb2, cs2)
            except C.UnknownTax:
                d[f"new_{scen}_{sn}"] = None
    det.append(d)


def summarize(sel, scen, sn):
    old = [x[f"old_{sn}"] for x in sel]
    new = [x[f"new_{scen}_{sn}"] for x in sel]
    acct = lambda v, x: v * x["slots"] / 10
    d_trade = [b - a for a, b in zip(old, new)]
    by_year = defaultdict(lambda: [0, 0.0])
    for x, dd in zip(sel, d_trade):
        y = x["exit"][:4]
        by_year[y][0] += 1
        by_year[y][1] += dd * x["slots"] / 10
    return {"rows": len(sel), "codes": len({x["code"] for x in sel}),
            "mean_trade_pct_old": sum(old) / len(old), "mean_trade_pct_new": sum(new) / len(new),
            "mean_trade_delta_pctpt": sum(d_trade) / len(d_trade),
            "acct_pct_sum_old": sum(acct(v, x) for v, x in zip(old, sel)),
            "acct_pct_sum_new": sum(acct(v, x) for v, x in zip(new, sel)),
            "acct_pct_sum_delta": sum(dd * x["slots"] / 10 for dd, x in zip(d_trade, sel)),
            "trade_PF_old": pf(old), "trade_PF_new": pf(new),
            "win_rate_old": sum(v > 0 for v in old) / len(old), "win_rate_new": sum(v > 0 for v in new) / len(new),
            "sign_flips": sum((a > 0) != (b > 0) for a, b in zip(old, new)),
            "by_exit_year": {y: {"rows": v[0], "acct_pct_sum_delta": v[1]} for y, v in sorted(by_year.items())}}


res = {"kind": "fixed_ledger_diagnostic(수익률 단위 · 가정 비용)", "ledger_sha256": LEDGER_SHA, "rows": len(rows),
       "codes": len({r["code"] for r in rows}), "entry_range": [min(r["entry"] for r in rows), max(r["entry"] for r in rows)],
       "exit_range": [min(r["exit"] for r in rows), max(r["exit"] for r in rows)],
       "market_rows": {m: sum(d["market_assumed"] == m for d in det) for m in ("KOSDAQ", "KOSPI")},
       "assumptions": {"account_krw": ACC, "order": "계좌 × 칸/10", "fee": C.FEE, "slip": C.SLIP, "impact_k": C.IMPACT_K,
                       "engine_roundtrip_backout": 0.0025, "market": "kosdaq-data 현재 목록(시점 기준 아님)", "instrument": "STOCK(저장소 기대)"},
       "perf2_copy_max_abs_diff": perf2_diff, "scenarios": {}}
for scen in C.SCENARIOS:
    ok = [d for d in det if d[f"new_{scen}_BASE"] is not None]
    unk = [d for d in det if d[f"new_{scen}_BASE"] is None]
    res["scenarios"][scen] = {"computable_rows": len(ok), "unknown_rows": len(unk),
                              "unknown_by_market_year": dict(sorted(((f"{m}-{y}", sum(1 for d in unk if d["market_assumed"] == m and d["exit"][:4] == y))
                                                                    for m in ("KOSDAQ", "KOSPI") for y in sorted({d["exit"][:4] for d in unk})), key=lambda t: t[0])),
                              "scales": {sn: summarize(ok, scen, sn) for sn in C.SCALES} if ok else None}
    res["scenarios"][scen]["unknown_by_market_year"] = {k: v for k, v in res["scenarios"][scen]["unknown_by_market_year"].items() if v}
res["not_computed_NEEDS_DATA"] = ["원 단위 비용 차액 · 금액 PF(수량 · 체결가 없음)", "일별 NAV · TWR · 일별 MTM MDD · 월별 · CAGR(입출금 · 일별 평가 · 체결 시각 · 수량 없음)",
                                  "1천만 / 1억 용량(주문 크기 · 유동성 없음)", "현금 보존 · 불가능 체결(현금 흐름 없음)"]

out.mkdir(parents=True, exist_ok=True)
(out / "DELTA-SUMMARY.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
cols = list(det[0].keys())
with open(out / "DELTA-ROWS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for d in det:
        w.writerow({k: (f"{v:.10f}" if isinstance(v, float) else ("" if v is None else v)) for k, v in d.items()})
print(json.dumps({s: {"ok": v["computable_rows"], "unknown": v["unknown_rows"]} for s, v in res["scenarios"].items()}, ensure_ascii=False),
      "perf2_diff", perf2_diff)
