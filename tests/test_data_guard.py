import unittest

import data_guard as G


def prices(lasts):
    return {f"{n:06d}": {"rows": [("20260901", 1.0), (d, 1.0)]} for n, d in enumerate(lasts)}


class FakeClient:
    def __init__(self, days=None, fail=False):
        self.days, self.fail = days or [], fail

    def index_daily(self, index, start, end):
        if self.fail:
            raise RuntimeError("조회 실패")
        return [{"date": d, "종가": 100.0} for d in self.days]


class DailyReady(unittest.TestCase):
    def test_incident_19_of_498_is_not_ready(self):
        ok, expect, why = G.daily_ready(prices(["20261001"] * 19 + ["20260930"] * 479), "20261001")
        self.assertFalse(ok)
        self.assertIn("19/498", why)

    def test_normal_day_ignores_halted_codes(self):
        ok, _, why = G.daily_ready(prices(["20261001"] * 490 + ["20260930"] * 8 + ["20260801"] * 9), "20261001")
        self.assertTrue(ok, why)
        self.assertIn("490/498", why)

    def test_whole_collection_missing_is_caught_with_expected_day(self):
        ok, _, _ = G.daily_ready(prices(["20260930"] * 500), "20261001")
        self.assertFalse(ok)

    def test_without_expected_day_uses_most_common(self):
        ok, expect, _ = G.daily_ready(prices(["20261001"] * 480 + ["20260930"] * 20))
        self.assertEqual((ok, expect), (True, "20261001"))


class PrevDay(unittest.TestCase):
    def test_prev_trading_day_skips_today_and_holidays(self):
        c = FakeClient(["20260929", "20260930", "20261001", "20261002"])
        self.assertEqual(G.prev_trading_day(c, "20261002"), "20261001")
        self.assertEqual(G.prev_trading_day(c, "20261006"), "20261002")

    def test_failure_gives_none(self):
        self.assertIsNone(G.prev_trading_day(FakeClient(fail=True), "20261002"))
        self.assertIsNone(G.prev_trading_day(object(), "20261002"))


class PlanReady(unittest.TestCase):
    def test_plan_must_be_from_yesterday(self):
        self.assertTrue(G.plan_ready({"base": "20261001"}, "20261001")[0])
        ok, why = G.plan_ready({"base": "20260930"}, "20261001")
        self.assertFalse(ok)
        self.assertIn("낡은", why)
        self.assertTrue(G.plan_ready({"base": "20260930"}, None)[0], "어제 거래일을 모르면 막지 않음")
        self.assertFalse(G.plan_ready(None, "20261001")[0])


if __name__ == "__main__":
    unittest.main()
