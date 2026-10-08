"""PR #34 독립 재현 결함 D1 · D2 · D3를 같은 방식으로 수정 전 · 수정 후 도구에 돌림(합성 · 네트워크 0).
python3 -I tests/repro_defects.py <도구 폴더> <Git 작업트리 안 임시 폴더> <결과.json>
PASS = 결함이 막힘, FAIL = 결함이 재현됨."""
import importlib.util
import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL, PROBE, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3])
KEY = "TEST-ONLY-KEY-000000000000000000"


def load(name):
    spec = importlib.util.spec_from_file_location(f"_t_{name}", TOOL / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = load("build_daily_measurement")
NEW_API = "expected_days" in inspect.signature(B.measure).parameters
START = {"date": "2026-09-30", "cash_krw": 0, "positions": {"005930": 100}}
HEAD = ("mdd_daily_mtm", "worst_day_twr", "worst_month_twr", "day_alerts", "month_alerts")


def run_measure(prices, days):
    kw = {"expected_days": {"days": days, "calendar": "TEST-KRX", "generated_at": "2026-10-08T00:00:00+09:00",
                            "provenance": "합성 시험"}} if NEW_API else {}
    try:
        return B.measure([], START, prices, **kw), None
    except B.MeasureError as e:
        return None, str(e)[:120]


res = {"tool_dir_name": TOOL.parent.name + "/" + TOOL.name, "new_api": NEW_API, "cases": {}}

# D1 중간 거래일(10-02) 가격 누락
o, err = run_measure({"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 101}, "2026-10-05": {"005930": 103}},
                     ["2026-10-01", "2026-10-02", "2026-10-05"])
blocked = err is not None or o["data_status"] not in ("MEASURED", "MEASURED_COMPLETE")
res["cases"]["D1_missing_calendar_day"] = {"result": "PASS" if blocked else "FAIL", "rejected": err is not None,
                                           "data_status": None if o is None else o["data_status"],
                                           "days_total": None if o is None else o["days_total"]}

# D2 첫날 유효 · 다음날 보유 평가 누락
o, err = run_measure({"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 101}, "2026-10-02": {}},
                     ["2026-10-01", "2026-10-02"])
if o is None:
    blocked, info = True, {"rejected": True}
else:
    blocked = o["data_status"] not in ("MEASURED", "MEASURED_COMPLETE") and all(o.get(k) is None for k in HEAD)
    info = {"data_status": o["data_status"], "days_valid": o["days_valid"], "days_total": o["days_total"],
            "headline_non_null": [k for k in HEAD if o.get(k) is not None]}
res["cases"]["D2_broken_chain_headline"] = {"result": "PASS" if blocked else "FAIL", **info}

# D3 비공개 KIS 원문 입력이 Git 작업트리 안 · 출력은 밖
PROBE.mkdir(parents=True, exist_ok=True)
inside = PROBE / "rows_inside.json"
inside.write_text(json.dumps([{"ord_dt": "20261001", "ord_tmd": "093000", "sll_buy_dvsn_cd": "02", "pdno": "005930",
                               "tot_ccld_qty": "1", "avg_prvs": "5000", "odno": "T0001", "ord_gno_brno": "T01", "cncl_yn": "N"}]),
                  encoding="utf-8")
try:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "ledger.jsonl"
        p = subprocess.run([sys.executable, "-I", str(TOOL / "sanitize_fills.py"), "--kis-rows", str(inside), "--out", str(out)],
                           capture_output=True, text=True, env={**os.environ, "PAPER_MEASURE_HMAC_KEY": KEY})
        created = out.exists()
finally:
    inside.unlink()
res["cases"]["D3_private_input_inside_git"] = {"result": "PASS" if p.returncode != 0 and not created else "FAIL",
                                               "returncode": p.returncode, "output_created": created}
res["blocked"] = sum(c["result"] == "PASS" for c in res["cases"].values())
res["total"] = len(res["cases"])
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v["result"] for k, v in res["cases"].items()}, ensure_ascii=False))
