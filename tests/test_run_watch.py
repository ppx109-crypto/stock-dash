import io
import os
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest import mock

import run_watch as W


class WatchTest(unittest.TestCase):
    def test_all_ok(self):
        self.assertEqual(W.check("20261006", {"date": "20261006", "late": False}, {"date": "20261006", "late": False},
                                 {"last_bar": "202610061515"}), [])

    def test_missing_and_late(self):
        bad = W.check("20261006", {"date": "20261005"}, {"date": "20261006", "late": True}, {"last_bar": "202610061100"})
        self.assertEqual(len(bad), 3)
        self.assertIn("1일봉 봇이 오늘 돌지 않았어요", bad[0])
        self.assertIn("늦게 돌아", bad[1])
        self.assertIn("15분봉", bad[2])

    def test_idle_not_checked_before_start(self):
        bad = W.check("20261002", {"date": "20261002"}, {}, {"last_bar": "202610021515"})
        self.assertEqual(bad, [])

    def test_overlay_missing_and_failed(self):
        ok = ({"date": "20261012"}, {"date": "20261012"}, {"last_bar": "202610121515"})
        self.assertEqual(W.check("20261012", *ok, {"last_day": "20261012"}, {"orders": []}), [])
        bad = W.check("20261012", *ok, {"last_day": "20261008"}, {})
        self.assertTrue(any("레버리지 봇이 오늘 돌지 않았" in b for b in bad))
        book = {"orders": [{"key": "20261012:buy:122630", "side": "buy", "name": "KODEX 레버리지", "qty": 290, "status": "실패 · BrokerError"},
                           {"key": "20261008:buy:122630", "side": "buy", "qty": 1, "status": "실패 · 옛날"}]}
        bad = W.check("20261012", *ok, {"last_day": "20261012"}, book)
        self.assertEqual(len(bad), 1)
        self.assertIn("레버리지 봇 매수 실패", bad[0])
        self.assertEqual(W.check("20261010", {"date": "20261010"}, {"date": "20261010"}, {"last_bar": "202610101515"}, {}, {}), [],
                         "시작 전(10-11 전)은 안 봄")

    def test_holiday(self):
        self.assertFalse(W.trading_day("20261009"))      # 한글날
        self.assertFalse(W.trading_day("20261005"))      # 개천절 대체공휴일
        self.assertFalse(W.trading_day("20261010"))      # 토요일
        self.assertTrue(W.trading_day("20261006"))


    def test_watch_day_late_run_uses_previous_trading_day(self):
        k = W.KST
        self.assertEqual(W.watch_day(datetime(2026, 11, 20, 1, 31, tzinfo=k)), "20261119")    # 예약이 새벽으로 밀림 → 앞 거래일
        self.assertEqual(W.watch_day(datetime(2026, 11, 20, 16, 10, tzinfo=k)), "20261120")   # 평소 16:10 → 그날
        self.assertEqual(W.watch_day(datetime(2026, 11, 21, 1, 30, tzinfo=k)), "20261120")    # 토요일 새벽 → 금요일
        self.assertEqual(W.watch_day(datetime(2026, 11, 23, 0, 40, tzinfo=k)), "20261120")    # 월요일 새벽 → 금요일
        self.assertEqual(W.watch_day(datetime(2026, 10, 6, 1, 0, tzinfo=k)), "20261002")      # 주말 · 10/5 대체공휴일 건너뜀

    def test_special_hours_day_is_silent(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"WATCH_DAY": "20261119", "DISCORD_WEBHOOK_URL": ""}), redirect_stdout(out):
            self.assertEqual(W.main(), 0)
        self.assertIn("장 시간이 다른 날", out.getvalue())
        self.assertNotIn("돌지 않았어요", out.getvalue())


if __name__ == "__main__":
    unittest.main()
