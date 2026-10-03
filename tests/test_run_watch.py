import unittest

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

    def test_holiday(self):
        self.assertFalse(W.trading_day("20261009"))      # 한글날
        self.assertFalse(W.trading_day("20261010"))      # 토요일
        self.assertTrue(W.trading_day("20261006"))


if __name__ == "__main__":
    unittest.main()
