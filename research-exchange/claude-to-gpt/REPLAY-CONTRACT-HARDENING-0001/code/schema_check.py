"""REPLAY-CONTRACT-HARDENING-0001 · 보강 스키마를 합성 표본(맞는 것 · 틀린 것)과 로컬 148 의도에 대어 봄 — 네트워크 없음.
python3 -E -P schema_check.py <schema 폴더> <로컬 의도 148.json> <출력.json>"""
import hashlib
import json
import socket
import sys
from pathlib import Path

import jsonschema

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
SD, LOCI, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
V = {n: jsonschema.Draft202012Validator(json.load(open(SD / f"{n}.json")))
     for n in ("corporate-action.v2.schema", "raw-price-response.v2.schema", "intent.schema")}
ok = lambda n, x: V[n].is_valid(x)
h = hashlib.sha256(b"x").hexdigest()
ca = {"rcept_no": "20260102000100", "root_rcept_no": "20260102000100", "available_at_kst": "2026-01-02T16:00:00+09:00", "code": "A",
      "kind": "bonus_issue", "ratio": 1.5, "record_date": "20260108", "effective_date": "20260108", "price_basis_date": "20260107",
      "listing_date": "20260109", "source_endpoint": "fricDecsn", "source_cache_sha256": h}
rq = {"endpoint": "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "tr_id": "FHKST03010100",
      "params": {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "A", "FID_INPUT_DATE_1": "20260105", "FID_INPUT_DATE_2": "20260109",
                 "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "1"}}
kr = {"request": rq, "basis": "RAW", "request_param_sha256": h, "cache_file_sha256": h, "fetched_at_kst": "2026-10-09T09:00:00+09:00",
      "rows": [{"stck_bsop_date": "20260105", "stck_clpr": 103600}]}
cases = {
    "CA_정상": [True, ok("corporate-action.v2.schema", ca)],
    "CA_날짜만_공개": [True, ok("corporate-action.v2.schema", dict(ca, available_at_kst="2026-01-02"))],
    "CA_available_at_없음": [False, ok("corporate-action.v2.schema", {k: v for k, v in ca.items() if k != "available_at_kst"})],
    "CA_root_없음": [False, ok("corporate-action.v2.schema", {k: v for k, v in ca.items() if k != "root_rcept_no"})],
    "CA_무상_상장일_없음": [False, ok("corporate-action.v2.schema", {k: v for k, v in ca.items() if k != "listing_date"})],
    "CA_시간대_없는_시각": [False, ok("corporate-action.v2.schema", dict(ca, available_at_kst="2026-01-02T16:00:00"))],
    "CA_분할_원문경로": [True, ok("corporate-action.v2.schema", dict(ca, kind="split", ratio=5, source_endpoint="document"))],
    "KIS_원_정상": [True, ok("raw-price-response.v2.schema", kr)],
    "KIS_원인데_플래그0": [False, ok("raw-price-response.v2.schema", dict(kr, request=dict(rq, params=dict(rq["params"], FID_ORG_ADJ_PRC="0"))))],
    "KIS_조회시각_날짜만": [False, ok("raw-price-response.v2.schema", dict(kr, fetched_at_kst="2026-10-09"))],
    "KIS_요청해시_없음": [False, ok("raw-price-response.v2.schema", {k: v for k, v in kr.items() if k != "request_param_sha256"})],
}
loc = json.load(open(LOCI))
bad = [r["fill_id"] for r in loc if not ok("intent.schema", {k: r[k] for k in ("fill_id", "sleeve", "date", "side", "status", "intent")})]
cases["로컬_148_의도_스키마"] = [[148, 0], [len(loc), len(bad)]]
res = {"cases": {k: {"expect": v[0], "got": v[1], "pass": v[0] == v[1]} for k, v in cases.items()}}
res["pass"] = all(v["pass"] for v in res["cases"].values())
Path(OUT).write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({k: v["pass"] for k, v in res["cases"].items()} | {"pass": res["pass"]}, ensure_ascii=False))
