"""과거 배수를 모아 적정가치 범위를 낼 수 있는지 확인합니다.

시세를 실제로 묻지 않고, 아는 값으로 대신 답하게 해서 계산만 봅니다.
"""
import unittest
from datetime import date

from automatic import brief
from providers import Official


class FakePrices(Official):
    """결산 발표 뒤의 시가총액을 미리 정해 둔 수집기.

    열쇠는 결산연도가 아니라 **발표된 해**입니다. 2023년 결산은 2024년에 발표되고,
    배수는 그 발표 직후의 시가총액으로 잽니다.
    """

    CAPS = {2024: 8_000_000_000_000, 2025: 15_000_000_000_000}

    def __init__(self, caps=None):
        super().__init__()
        self.caps = caps if caps is not None else dict(self.CAPS)
        self.asked = []

    def price(self, code, asof):
        self.asked.append(asof.isoformat())
        cap = self.caps.get(asof.year)
        self.price_rows[(code, asof.isoformat())] = {
            "mrktTotAmt": str(cap) if cap else "", "lstgStCnt": "100000000"}
        return 50000.0, asof.strftime("%Y%m%d"), "테스트기업"


YEARS = [
    {"year": 2023, "revenue": 100000, "profit": 10000, "receipt": "20240315000001"},
    {"year": 2024, "revenue": 120000, "profit": 12500, "receipt": "20250315000001"},
    {"year": 2025, "revenue": 150000, "profit": 15000, "receipt": "20260315000001"},
]


class Anchors(unittest.TestCase):
    def test_past_settlements_give_one_multiple_each(self):
        found = FakePrices().anchors("005930", YEARS, date(2026, 9, 21))
        self.assertEqual([a["year"] for a in found], [2023, 2024])
        self.assertAlmostEqual(found[0]["multiple"], 8_000_000_000_000 / (10000 * 1e8))

    def test_the_newest_settlement_is_not_used_as_an_anchor(self):
        """가장 최근 결산은 값을 매길 대상이지 기준이 아닙니다."""
        found = FakePrices().anchors("005930", YEARS, date(2026, 9, 21))
        self.assertNotIn(2025, [a["year"] for a in found])

    def test_a_loss_making_year_is_skipped(self):
        years = [{**YEARS[0], "profit": -500}, YEARS[1], YEARS[2]]
        found = FakePrices().anchors("005930", years, date(2026, 9, 21))
        self.assertEqual([a["year"] for a in found], [2024])

    def test_two_anchors_produce_a_reference_range(self):
        report = {"years": YEARS, "price": 50000, "shares": 100_000_000,
                  "company": {"induty_code": "26"},
                  "anchors": FakePrices().anchors("005930", YEARS, date(2026, 9, 21))}
        fair = brief(report)["fair"]
        self.assertIsNotNone(fair)
        # 배수가 서로 다르면 낮은 값·중간값·높은 값이 벌어집니다.
        self.assertLess(fair["low"], fair["high"])
        self.assertLessEqual(fair["low"], fair["base"])
        self.assertLessEqual(fair["base"], fair["high"])

    def test_one_anchor_is_not_enough_and_says_so(self):
        caps = {2024: 8_000_000_000_000}
        report = {"years": YEARS, "price": 50000, "shares": 100_000_000,
                  "company": {"induty_code": "26"},
                  "anchors": FakePrices(caps).anchors("005930", YEARS, date(2026, 9, 21))}
        result = brief(report)
        self.assertIsNone(result["fair"])
        self.assertIn("2개", result["fair_reason"])

    def test_a_loss_in_the_latest_year_cannot_be_priced_at_all(self):
        """적자는 배수를 곱할 대상이 없어, 자료를 더 모아도 채울 수 없습니다."""
        years = YEARS[:-1] + [{**YEARS[2], "profit": -17000}]
        report = {"years": years, "price": 50000, "shares": 100_000_000,
                  "company": {"induty_code": "26"},
                  "anchors": FakePrices().anchors("005930", years, date(2026, 9, 21))}
        result = brief(report)
        self.assertIsNone(result["fair"])
        self.assertIn("영업이익", result["fair_reason"])


if __name__ == "__main__":
    unittest.main()


class FinancialSector(unittest.TestCase):
    """업종코드가 같아도, 매출을 공시하면 배수를 쓸 수 있어야 합니다."""

    BANK = [{"year": 2023, "revenue": None, "profit": 30000, "receipt": "20240315000001"},
            {"year": 2024, "revenue": None, "profit": 32000, "receipt": "20250315000001"},
            {"year": 2025, "revenue": None, "profit": 34000, "receipt": "20260315000001"}]

    def report(self, years, anchors):
        return {"years": years, "price": 50000, "shares": 100_000_000,
                "company": {"induty_code": "64992"}, "anchors": anchors}

    def test_a_holding_company_filing_revenue_gets_a_range(self):
        anchors = FakePrices().anchors("003550", YEARS, date(2026, 9, 21))
        result = brief(self.report(YEARS, anchors))
        self.assertIsNotNone(result["fair"])

    def test_a_bank_with_no_revenue_line_still_needs_another_model(self):
        anchors = [{"year": 2023, "multiple": 9.0}, {"year": 2024, "multiple": 11.0}]
        result = brief(self.report(self.BANK, anchors))
        self.assertIsNone(result["fair"])
        self.assertIn("금융업", result["fair_reason"])
