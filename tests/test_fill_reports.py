"""자료 받기: 한 종목이 실패해도 나머지는 저장되고, 결과가 그대로 돌아와야 합니다."""
import unittest

import providers
import research_ui
from providers import DataError


class Saved:
    def __init__(self):
        self.stocks = []

    def save_stock(self, stock):
        self.stocks.append(stock)


class FakeProvider:
    """한 종목은 받아 오고, 한 종목은 실패하는 수집기."""

    def automatic(self, code):
        if code == "000002":
            raise DataError("DART 접속 확인 · HTTP 500")
        return {
            "code": code, "name": "받은기업", "price": 1000, "price_date": "20260917",
            "shares": 1000, "market_cap": 1_000_000, "anchors": [],
            "company": {"induty_code": "26"},
            "years": [{"year": 2024, "revenue": 100, "profit": 10},
                      {"year": 2025, "revenue": 120, "profit": 15}],
        }


class FillReports(unittest.TestCase):
    def setUp(self):
        self.real = providers.Official
        providers.Official = FakeProvider

    def tearDown(self):
        providers.Official = self.real

    def test_one_failure_does_not_stop_the_rest(self):
        store = Saved()
        done, failed = research_ui.fill_reports(
            store, [{"code": "000001", "name": "가"}, {"code": "000002", "name": "나"},
                    {"code": "000003", "name": "다"}])
        self.assertEqual(done, ["받은기업", "받은기업"])
        self.assertEqual([name for name, _ in failed], ["나"])
        self.assertIn("HTTP 500", failed[0][1])
        self.assertEqual(len(store.stocks), 2)

    def test_saved_stock_carries_the_report_and_clears_the_old_error(self):
        store = Saved()
        research_ui.fill_reports(store, [{"code": "000001", "name": "가",
                                          "analysis_error": "지난번 실패"}])
        saved = store.stocks[0]
        self.assertEqual(saved["year"], 2025)
        self.assertIsNone(saved["analysis_error"])
        self.assertTrue(saved["report"]["years"])
        self.assertIn("revenue_growth", saved["automatic_brief"])

    def test_limit_caps_how_many_are_fetched_in_one_press(self):
        store = Saved()
        done, failed = research_ui.fill_reports(
            store, [{"code": "00000" + str(i), "name": str(i)} for i in (1, 3, 4, 5)], limit=2)
        self.assertEqual(len(done) + len(failed), 2)


if __name__ == "__main__":
    unittest.main()
