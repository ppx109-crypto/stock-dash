"""장 시간이 다른 날(수능날 · 새해 첫 거래일)은 봇이 자동 판단을 쉼 · 수집기는 그대로(2026-10-06)."""
import unittest
from unittest import mock

import collect_kis_intraday as I


class SpecialHours(unittest.TestCase):
    def test_bots_rest_on_special_days(self):
        client = mock.Mock()
        self.assertFalse(I.market_open_today(client, "20261119"))
        client._market_rows.assert_not_called()

    def test_collector_still_asks(self):
        client = mock.Mock()
        client._market_rows.return_value = [{"stck_bsop_date": "20261119"}]
        self.assertTrue(I.market_open_today(client, "20261119", bots=False))

    def test_normal_day_unchanged(self):
        client = mock.Mock()
        client._market_rows.return_value = [{"stck_bsop_date": "20261007"}]
        self.assertTrue(I.market_open_today(client, "20261007"))
        self.assertIsNone(I.special_hours("20261007"))


if __name__ == "__main__":
    unittest.main()
