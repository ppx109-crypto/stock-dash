"""Presentation-only regression checks: hide requested rows without erasing ledgers."""
import copy
import unittest
from pathlib import Path

import dashboard_ui as D


class DashboardHistoryVisibility(unittest.TestCase):
    def setUp(self):
        self.idle_orders = [
            {"at": "2026-10-06 15:14", "side": "buy", "code": "251340",
             "name": "KODEX 코스닥150선물인버스", "qty": 45539,
             "status": "실패 · 모의투자 주문이 거절되었습니다 · 40250000.", "price": 2130},
            {"at": "2026-10-07 15:13", "side": "buy", "code": "251340",
             "name": "KODEX 코스닥150선물인버스", "qty": 36116,
             "status": "접수 · 44,495주 중 살 수 있는 36,116주로 줄임", "price": 2180},
            {"at": "2026-10-12 15:13", "side": "sell", "code": "251340",
             "name": "KODEX 코스닥150선물인버스", "qty": 36116,
             "status": "접수", "price": 2325},
        ]
        self.lever_order = {"at": "2026-10-12 15:13", "side": "buy",
                            "code": "122630", "qty": 290, "status": "실패 · BrokerError"}

    def test_exactly_four_identifiers_are_hidden(self):
        for o in self.idle_orders + [self.lever_order]:
            self.assertFalse(D._visible_dashboard_order(o))
        other = {**self.lever_order, "at": "2026-10-16 15:13"}
        self.assertTrue(D._visible_dashboard_order(other))
        other = {**self.idle_orders[1], "qty": 36115}
        self.assertTrue(D._visible_dashboard_order(other))
        self.assertTrue(D._visible_dashboard_order({"at": "2026-10-12 15:13", "code": "251340"}))

    def test_top_mini_and_detailed_idle_do_not_reintroduce_hidden_history(self):
        book = {"orders": copy.deepcopy(self.idle_orders)}
        before = copy.deepcopy(book)
        closed = [{"판 날": "20261012", "산 날": "20261007", "code": "251340",
                   "name": "KODEX 코스닥150선물인버스", "손익": 6.65, "칸": 8}]
        state = {"positions": {}, "closed": closed}
        for output in (
            D.ledger_mini("빈칸 엔진", state, book),
            D.ledger_panel("빈칸 엔진", state, book),
            D.idle_panel({"date": "20261012", "orders": [self.idle_orders[2]]}, state, book),
        ):
            self.assertNotIn("44,495주", output)
            self.assertNotIn("40250000", output)
            self.assertNotIn("36,116주", output)
            self.assertNotIn("2,325원", output)
            self.assertNotIn("20261012 ·", output)  # closed detail, not the summary
        self.assertIn("끝난 매매 1건", D.ledger_mini("빈칸 엔진", state, book))
        self.assertEqual(book, before)
        self.assertEqual(len(book["orders"]), 3)

    def test_overlay_history_hidden_but_new_orders_displayed(self):
        b = {"orders": [self.lever_order]}
        for output in (D.overlay_mini({}, b), D.overlay_panel({}, b)):
            self.assertNotIn("BrokerError", output)
            self.assertNotIn("290주", output)
        future = {**self.lever_order, "at": "2026-10-19 15:13", "qty": 300}
        self.assertIn("300주", D.overlay_mini({}, {"orders": [future]}))

    def test_retired_m15_section_is_not_rendered(self):
        source = (Path(__file__).resolve().parents[1] / "research_ui.py").read_text(encoding="utf-8")
        self.assertNotIn("⏱️ 15분봉 매매 규칙 · 장중 15분마다", source)
        self.assertNotIn("D.ledger_mini('⏱️ 15분봉", source)


if __name__ == "__main__":
    unittest.main()
