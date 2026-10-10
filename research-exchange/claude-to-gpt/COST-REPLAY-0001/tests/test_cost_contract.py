"""비용 계약 합성 시험(실측 아님). python3 -I tests/test_cost_contract.py → TEST-RESULT.json"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import cost_contract as C  # noqa: E402

R = []


def case(name, fn):
    try:
        fn()
        R.append({"case": name, "result": "PASS"})
    except AssertionError as e:
        R.append({"case": name, "result": "FAIL", "why": str(e)[:200]})


def eq(a, b, tol=1e-12):
    assert abs(a - b) <= tol, f"{a} != {b}"


def raises(fn):
    try:
        fn()
    except C.UnknownTax:
        return
    raise AssertionError("UnknownTax 안 남")


def t_boundaries():
    exp = [("20170101", .0030), ("20190602", .0030), ("20190603", .0025), ("20201231", .0025), ("20210101", .0023),
           ("20221231", .0023), ("20230101", .0020), ("20231231", .0020), ("20240101", .0018), ("20241231", .0018),
           ("20250101", .0015), ("20251231", .0015), ("20260101", .0020), ("2026-10-08", .0020)]
    for d, r in exp:
        eq(C.sell_tax_rate(d, "STOCK", "KOSDAQ"), r)
    raises(lambda: C.sell_tax_rate("20261009", "STOCK", "KOSDAQ"))   # 검토일 뒤 자동 기본값 금지
    raises(lambda: C.sell_tax_rate("20161230", "STOCK", "KOSDAQ"))
    raises(lambda: C.sell_tax_rate("20270104", "STOCK", "KOSDAQ"))


def t_buy_untaxed():
    eq(C.buy_tax_rate("20260105", "STOCK", "KOSDAQ"), 0.0)
    C.impact = lambda code, day, n: 0.0          # 충격 0으로 고정해 세금만 봄
    try:
        b, s = C.corrected_side_costs("X", "20260105", "20260106", 1e7, "KOSDAQ")
        eq(b, C.FEE + C.SLIP)
        eq(s, C.FEE + C.SLIP + .0020)
        b2, s2 = C.corrected_side_costs("X", "20260105", "20260106", 1e7, "KOSDAQ", scale=2.0)
        eq(b2, 2 * (C.FEE + C.SLIP))
        eq(s2, 2 * (C.FEE + C.SLIP + .0020))
    finally:
        import importlib
        importlib.reload(C)


def t_partial_fill():
    whole = C.sell_tax_amount(100, 10_000, "20260302", "STOCK", "KOSDAQ")
    parts = C.sell_tax_amount(30, 10_000, "20260302", "STOCK", "KOSDAQ") + C.sell_tax_amount(70, 10_000, "20260302", "STOCK", "KOSDAQ")
    eq(whole, parts, 1e-9)
    eq(whole, 2000.0, 1e-9)
    # 해를 넘긴 부분체결은 각 체결일 세율
    a = C.sell_tax_amount(50, 10_000, "20251230", "STOCK", "KOSDAQ")
    b = C.sell_tax_amount(50, 10_000, "20260102", "STOCK", "KOSDAQ")
    eq(a, 750.0, 1e-9)
    eq(b, 1000.0, 1e-9)
    for q, p in ((0, 1), (-1, 1), (1, 0)):
        try:
            C.sell_tax_amount(q, p, "20260302", "STOCK", "KOSDAQ")
        except ValueError:
            continue
        raise AssertionError("0 · 음수 수량/가격 통과")


def t_unknown_refusal():
    raises(lambda: C.sell_tax_rate("20240105", "STOCK", "KOSPI"))            # 과거 농특세 미확인
    raises(lambda: C.sell_tax_rate("20240105", "STOCK", "KONEX"))
    raises(lambda: C.sell_tax_rate("20240105", "STOCK", None))
    raises(lambda: C.sell_tax_rate("2024015", "STOCK", "KOSDAQ"))
    raises(lambda: C.sell_tax_rate("20240105", "STOCK", "KOSDAQ", scenario="BASE_GUESS"))
    eq(C.sell_tax_rate("20260105", "STOCK", "KOSPI"), .0020)


def t_product_split():
    for it in ("ETF", "ETN", "INVERSE_ETF", "OTHER", None):
        raises(lambda it=it: C.sell_tax_rate("20260105", it, "KOSDAQ"))
        raises(lambda it=it: C.sell_tax_rate("20260105", it, "KOSPI", scenario="S_KOSPI_FARM015"))


def t_scenario():
    exp = [("20180102", .0030), ("20190603", .0025), ("20210104", .0023), ("20230102", .0020), ("20240102", .0018),
           ("20250102", .0015), ("20260102", .0020)]
    for d, r in exp:
        eq(C.sell_tax_rate(d, "STOCK", "KOSPI", scenario="S_KOSPI_FARM015"), r)
    raises(lambda: C.sell_tax_rate("20261009", "STOCK", "KOSPI", scenario="S_KOSPI_FARM015"))


def t_old_reproduced():
    eq(C.old_tax("20260105"), .0015)     # 기존 결함: 2026을 0.15%로
    eq(C.old_tax("20180105"), .0025)
    eq(C.old_tax("20210105"), .0025)
    eq(C.old_tax("20240105"), .0018)
    # 2026 일반 주식 BASE 매도세금 차 = 매도금액 × 0.0005
    eq(C.sell_tax_rate("20260105", "STOCK", "KOSDAQ") - C.old_tax("20260105"), .0005)


for n, f in (("날짜 경계", t_boundaries), ("매수 비과세 · 배율", t_buy_untaxed), ("부분체결", t_partial_fill),
             ("UNKNOWN 거부", t_unknown_refusal), ("상품 구분", t_product_split), ("가정 시나리오", t_scenario),
             ("old 재현 · 2026 차", t_old_reproduced)):
    case(n, f)

out = {"kind": "synthetic_unit_test(실측 아님)", "cases": R, "passed": sum(r["result"] == "PASS" for r in R), "total": len(R)}
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if out["passed"] == out["total"] else 1)
