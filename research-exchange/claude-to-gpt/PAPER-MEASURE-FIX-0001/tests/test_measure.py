"""PAPER-MEASURE-0001 기존 합성 시험 17개(FIX-0001에서 호출만 맞춤: expected_days 필수 · INVALID 이름 · 불완전 행 위치). python3 -I tests/test_measure.py → TEST-RESULT.json 형식 출력.
모든 값은 시험 전용 합성값입니다(주문번호 'T…', 키 'TEST-ONLY-…')."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import build_daily_measurement as B  # noqa: E402
import sanitize_fills as F  # noqa: E402

KEY = b"TEST-ONLY-KEY-000000000000000000"
R = []


def case(name, fn):
    try:
        fn()
        R.append({"case": name, "result": "PASS"})
    except Exception as e:  # noqa: BLE001 — 시험 실패 사유만 남김
        R.append({"case": name, "result": "FAIL", "why": f"{type(e).__name__}: {str(e)[:160]}"})


def eq(a, b, tol=1e-9):
    assert abs(a - b) <= tol, f"{a} != {b}"


def raises(exc, fn, text=None):
    try:
        fn()
    except exc as e:
        assert text is None or text in str(e), str(e)
        return
    raise AssertionError(f"{exc.__name__} 안 남")


def row(day="20261001", tmd="093000", side="02", code="005930", qty="10", price="5000", order="T0001", **kw):
    r = {"ord_dt": day, "ord_tmd": tmd, "sll_buy_dvsn_cd": side, "pdno": code, "prdt_name": "합성",
         "tot_ccld_qty": qty, "avg_prvs": price, "odno": order, "ord_gno_brno": "T01", "cncl_yn": "N"}
    r.update(kw)
    return r


def measure_(fills, start, prices, *a, **k):
    """FIX-0001: 기존 시험 그대로 — 기대 거래일은 가격 키(시작일 뒤)로 만듦."""
    exp = {"days": sorted(d for d in prices if d > start["date"]), "calendar": "TEST", "generated_at": "2026-10-08T00:00:00+09:00",
           "provenance": "합성 시험: 가격 키에서 만듦"}
    return B.measure(fills, start, prices, *a, expected_days=exp, **k)


def rows(o):
    return o["days"] if o["days"] is not None else o["diagnostic_partial_days"]


def mrows(o):
    return o["months"] if o["months"] is not None else o["diagnostic_partial_months"]


COST0 = {k: {"krw": 0, "kind": "actual"} for k in F.COST_ITEMS}


def ctx_all(**extra):
    return {"defaults": {"instrument_type": "STOCK", "market_at_fill": "KOSDAQ", "strategy_id": "TEST", "rule_version": "t1",
                         "signal_at_kst": "2026-10-01T09:00:00", "available_at_basis": "test", "costs": COST0, **extra}}


# ── sanitize ──
def t_confirmed_categories():
    rows = [row(), row(order="T0002", cncl_yn="Y"), row(order="T0003", qty="0"), row(order="T0004", qty=""), row()]
    fills, n = F.normalize(rows, KEY, ctx_all())
    assert len(fills) == 1 and n["confirmed"] == 1 and n["cancelled"] == 1 and n["unfilled"] == 2 and n["duplicate"] == 1, n


def t_conflict_duplicate():
    raises(F.InputError, lambda: F.normalize([row(), row(qty="11")], KEY), "다른 체결 합계")


def t_partial_fills():
    fills, n = F.normalize([row(order="T0001", qty="3", price="5000"), row(order="T0002", tmd="100000", qty="7", price="5010")], KEY, ctx_all())
    assert n["confirmed"] == 2
    eq(sum(f["quantity"] for f in fills), 10)
    eq(sum(f["amount_krw"] for f in fills), 3 * 5000 + 7 * 5010)


def t_missing_fields():
    raises(F.InputError, lambda: F.normalize([row(avg_prvs="")], KEY), "평균가")
    raises(F.InputError, lambda: F.normalize([row(avg_prvs="0")], KEY), "평균가")
    raises(F.InputError, lambda: F.normalize([row(odno="")], KEY), "주문번호")
    raises(F.InputError, lambda: F.normalize([row(side="03")], KEY), "구분")
    raises(F.InputError, lambda: F.normalize([row(day="2026101")], KEY), "일시")
    raises(F.InputError, lambda: F.normalize([row(tmd="9300")], KEY), "일시")
    raises(F.InputError, lambda: F.normalize([row(code="")], KEY), "종목코드")
    fills, n = F.normalize([row()], KEY, None)           # 맥락 없으면 null + 누락 개수
    assert fills[0]["instrument_type"] is None and n["missing_field_counts"]["market_at_fill"] == 1
    assert n["missing_field_counts"]["costs.commission"] == 1


def t_order_book_not_fill():
    book_row = {"key": "t", "at": "2026-10-01 09:00", "code": "005930", "side": "buy", "qty": 10, "status": "접수",
                "order_no": "T9999", "price": 5000}
    raises(F.InputError, lambda: F.normalize([book_row], KEY), "ORDER_ACCEPTED_NOT_FILL")


def t_same_semantics_as_predash():
    sys.path.insert(0, str(REPO))
    from predash.trades import normalize_kis
    rows = [row(), row(order="T0002", side="01", tmd="100000", qty="4", price="5100"), row(order="T0003", cncl_yn="Y"),
            row(order="T0004", qty="0"), row(), row(order="T0005", code="A00279K", qty="2", price="900", tot_ccld_amt="1800"),
            row(order="T0006", code="Q500001", qty="1", price="10000")]
    a = normalize_kis(rows)
    b, _ = F.normalize(rows, KEY)
    key = lambda x: (x["at"].isoformat(), x["code"], x["side"], x["quantity"], x["price"], x["amount"])
    keyb = lambda x: (x["fill_at_kst"], x["asset_id"], x["side"], x["quantity"], x["fill_price"], x["amount_krw"])
    assert [key(x) for x in a] == [keyb(x) for x in b], "predash.normalize_kis와 다름"


def t_hmac_uid():
    f1, _ = F.normalize([row()], KEY)
    f2, _ = F.normalize([row()], KEY)
    f3, _ = F.normalize([row()], b"TEST-ONLY-OTHER-KEY-000000000000")
    assert f1[0]["fill_uid"] == f2[0]["fill_uid"] != f3[0]["fill_uid"]
    blob = json.dumps(f1)
    assert "T0001" not in blob and '"T01"' not in blob, "주문 · 지점 번호가 출력에 남음"
    assert "odno" not in blob and "ord_gno_brno" not in blob


def t_key_fail_closed():
    raises(F.InputError, lambda: F.load_key({}), "거부")
    raises(F.InputError, lambda: F.load_key({F.KEY_ENV: "short"}), "거부")
    eq(len(F.load_key({F.KEY_ENV: KEY.decode()})), len(KEY))


def t_cli_guards():
    with tempfile.TemporaryDirectory() as td:
        rows = Path(td) / "rows.json"
        rows.write_text(json.dumps([row()]), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != F.KEY_ENV}
        run = lambda out, e: subprocess.run([sys.executable, "-I", str(HERE / "sanitize_fills.py"), "--kis-rows", str(rows),
                                             "--out", str(out)], capture_output=True, text=True, env=e)
        p = run(Path(td) / "a.jsonl", env)
        assert p.returncode == 2 and not (Path(td) / "a.jsonl").exists(), "키 없이 처리됨"
        inside = HERE / "tests" / "_should_not_exist.jsonl"
        p = run(inside, {**env, F.KEY_ENV: KEY.decode()})
        assert p.returncode == 2 and not inside.exists(), "작업트리 안 출력이 허용됨"
        p = run(Path(td) / "b.jsonl", {**env, F.KEY_ENV: KEY.decode()})
        assert p.returncode == 0 and (Path(td) / "b.jsonl").exists(), p.stdout
        assert "T0001" not in p.stdout


def t_opposite_side_same_time():
    _, n = F.normalize([row(order="T0001"), row(order="T0002", side="01")], KEY)
    assert n["same_time_opposite_side"] == 1


# ── measure ──
def base_fills(**kw):
    fl, _ = F.normalize([row(day="20261001", qty="100", price="5000", order="T0001"),
                         row(day="20261005", side="01", qty="100", price="5050", order="T0002")], KEY, ctx_all(**kw))
    fl[0]["costs"] = {**COST0, "commission": {"krw": 75.0, "kind": "actual"}}
    fl[1]["costs"] = {**COST0, "commission": {"krw": 75.75, "kind": "actual"}, "sell_tax": {"krw": 1010.0, "kind": "actual"}}
    return fl


START = {"date": "2026-09-30", "cash_krw": 1_000_000, "positions": {}}
PRICES = {"2026-09-30": {}, "2026-10-01": {"005930": 5100}, "2026-10-02": {"005930": 4900}, "2026-10-05": {"005930": 5000}}
FLOWS = [{"date": "2026-10-02", "amount_krw": 100_000}]


def t_mtm_twr_flows():
    out = measure_(base_fills(), START, PRICES, FLOWS)
    e1 = 1_000_000 - 500_075 + 510_000
    e2 = (1_000_000 - 500_075 + 100_000) + 490_000
    e3 = (1_000_000 - 500_075 + 100_000) + 505_000 - 1_085.75
    r = [e1 / 1_000_000 - 1, e2 / (e1 + 100_000) - 1, e3 / e2 - 1]
    got = [d["twr_day"] for d in rows(out)]
    for a, b in zip(got, r):
        eq(a, b, 1e-9)
    eq(rows(out)[-1]["nav_norm"], (1 + r[0]) * (1 + r[1]) * (1 + r[2]), 1e-9)
    eq(out["mdd_daily_mtm"], r[1], 1e-9)          # 둘째 날 평가 손실 — 매매 끝난 날 기준이면 0으로 숨음
    assert out["mdd_daily_mtm"] < 0
    eq(out["cost_bps"]["actual"], (75 + 75.75 + 1010) / (500_000 + 505_000) * 1e4, 1e-4)   # 공개 출력은 소수 4자리
    assert rows(out)[0]["utilization"] > 0.5 and rows(out)[-1]["utilization"] == 0


def t_day_month_boundary():
    st = {"date": "2026-09-30", "cash_krw": 0, "positions": {"005930": 100}}
    o = measure_([], st, {"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 85}})
    assert rows(o)[0]["day_loss_alert"] is False and o["day_alerts"] == 0     # 정확히 −15%는 경보 아님
    o = measure_([], st, {"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 84.99}})
    assert rows(o)[0]["day_loss_alert"] is True and o["day_alerts"] == 1
    pr = {"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 92}, "2026-10-02": {"005930": 85}}
    o = measure_([], st, pr)
    assert o["day_alerts"] == 0 and mrows(o)[0]["month_loss_alert"] is False and o["month_alerts"] == 0
    pr["2026-10-02"]["005930"] = 84.99
    o = measure_([], st, pr)
    assert o["day_alerts"] == 0 and mrows(o)[0]["month_loss_alert"] is True and o["month_alerts"] == 1
    assert mrows(o)[0]["partial"] is True


def t_valuation_and_corp_action():
    st = {"date": "2026-09-30", "cash_krw": 0, "positions": {"005930": 100}}
    pr = {"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 101}, "2026-10-02": {}, "2026-10-05": {"005930": 103}}
    o = measure_([], st, pr)
    st_ = [d["status"] for d in rows(o)]
    assert st_ == ["OK", "NULL", "NULL"] and rows(o)[2]["reason"].startswith("VALUATION_MISSING"), rows(o)
    assert mrows(o)[0]["status"] == "NULL" and o["days_valid"] == 1
    pr2 = {"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 50}}
    o = measure_([], st, pr2, corp_actions=[{"date": "2026-10-01", "code": "005930", "qty_ratio": 2}])
    eq(rows(o)[0]["twr_day"], 0.0)
    o = measure_([], st, pr2)                      # 분할 기록 없으면 −50%로 보임(입력 완전성 책임)
    eq(rows(o)[0]["twr_day"], -0.5)
    raises(B.MeasureError, lambda: measure_([], {**st, "date": "2026-10-01"}, {"2026-10-01": {"005930": 1}}))


def t_impossible_and_missing_costs():
    fl = base_fills()
    fl[1]["quantity"] = 150.0                      # 보유보다 많이 팖
    o = measure_(fl, START, PRICES, FLOWS)
    assert rows(o)[2]["status"] == "NULL" and "IMPOSSIBLE" in rows(o)[2]["reason"]
    assert o["completeness"]["impossible_fill_days"] == 1
    fl = base_fills()
    fl[0]["costs"]["sell_tax"] = {"krw": None, "kind": "missing"}
    o = measure_(fl, START, PRICES, FLOWS)
    assert rows(o)[0]["status"] == "NULL" and rows(o)[0]["reason"].startswith("COSTS_MISSING")
    assert o["data_status"] == "INVALID" and o["mdd_daily_mtm"] is None


def t_slippage():
    fl = base_fills()
    fl[0].update(reference_price=4990, reference_price_basis="t-1 종가(합성)")
    fl[1].update(reference_price=5060, reference_price_basis="판단 시각 값(합성)")
    o = measure_(fl, START, PRICES, FLOWS)
    eq(o["slippage_bps"]["buy_mean"], round((5000 - 4990) / 4990 * 1e4, 4), 1e-4)
    eq(o["slippage_bps"]["sell_mean"], round((5060 - 5050) / 5060 * 1e4, 4), 1e-4)
    o = measure_(base_fills(), START, PRICES, FLOWS)
    assert o["slippage_bps"]["buy_mean"] is None and o["slippage_bps"]["null_no_reference"] == 2


def t_public_secret_scan():
    o = measure_(base_fills(), START, PRICES, FLOWS, sanitize_counts={"confirmed": 2, "missing_field_counts": {"reference_price": 2}},
                  generator_commit="1e6ed49b9b98")
    assert B.public_guard(o) == [] and B.whitelist_guard(o) == []
    blob = json.dumps(o, ensure_ascii=False)
    for s in ("T0001", "T0002", "fill_uid", "odno", "amount_krw", "cash_krw", "quantity", "500000", "1000000"):
        assert s not in blob, s
    for inj, why in (({"order_no": "1"}, "forbidden_key"), ({"notes": "5012345601"}, "account_or_order_like_string"),
                     ({"worst_day_twr": 12_345_678}, "absolute_amount_like_number"), ({"cash_krw": 1}, "forbidden_key"),
                     ({"access_token": "x"}, "forbidden_key"), ({"raw_response": "x"}, "forbidden_key")):
        bad = B.public_guard({**o, **inj})
        assert any(b[1] == why for b in bad), (inj, bad)
    assert B.whitelist_guard({**o, "equity_curve": []}), "허용 목록 밖 필드 통과"
    assert any(b[1] == "account_or_order_like_string" for b in B.public_guard({**o, "provenance": {**o["provenance"], "generator_commit": "5012345601"}}))


def t_fill_outside_period():
    fl = base_fills()
    raises(B.MeasureError, lambda: measure_(fl, START, {"2026-09-30": {}, "2026-10-01": {"005930": 1}}), "기간 밖")


for n, f in (("확정 · 취소 · 미체결 · 중복", t_confirmed_categories), ("충돌 중복 중단", t_conflict_duplicate),
             ("부분체결", t_partial_fills), ("필드 누락 거부 · 맥락 누락 개수", t_missing_fields),
             ("주문 장부(접수) 행 거부", t_order_book_not_fill), ("predash.normalize_kis와 의미 일치", t_same_semantics_as_predash),
             ("HMAC 식별자 · 원 번호 미출력", t_hmac_uid), ("키 없음 fail-closed", t_key_fail_closed),
             ("CLI 키 · 작업트리 거부", t_cli_guards), ("반대 side 같은 시각", t_opposite_side_same_time),
             ("일별 MTM · TWR · 입출금(손셈)", t_mtm_twr_flows), ("−15% 하루 · 달 경계", t_day_month_boundary),
             ("평가 누락 · 기업행동", t_valuation_and_corp_action), ("불가능 체결 · 비용 누락", t_impossible_and_missing_costs),
             ("미끄러짐 bps · 기준가 없음 null", t_slippage), ("공개 출력 비밀 검사", t_public_secret_scan),
             ("기간 밖 체결 거부", t_fill_outside_period)):
    case(n, f)

out = {"kind": "synthetic_test(실측 아님)", "cases": R, "passed": sum(r["result"] == "PASS" for r in R), "total": len(R)}
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if out["passed"] == out["total"] else 1)
