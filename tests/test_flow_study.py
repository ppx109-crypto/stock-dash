"""스승님 수급 조건의 신호 판정을 봅니다(그날까지의 수급만 씀)."""
import unittest

import flow_study


def day(f, t, p, o=0.0, close=100.0, d="20200102"):
    return {"date": d, "외국인": f, "투신": t, "개인": p, "기관": o, "종가": close}


class Signals(unittest.TestCase):

    def test_today_teacher_condition(self):
        got = flow_study.signals([day(10, 5, -15)], cap=None)
        self.assertTrue(got["그날 외국인·투신 매수 + 개인 매도"])
        self.assertFalse(flow_study.signals([day(10, -5, -5)], None)["그날 외국인·투신 매수 + 개인 매도"])

    def test_three_in_a_row_needs_every_day(self):
        w = [day(1, 1, -2)] * 2 + [day(1, -1, 0)]
        self.assertFalse(flow_study.signals(w, None)["사흘 연속"])
        self.assertTrue(flow_study.signals([day(1, 1, -2)] * 3, None)["사흘 연속"])

    def test_five_day_sums_and_strength(self):
        w = [day(-1, 0, 1)] * 2 + [day(5, 2, -7)] * 3
        got = flow_study.signals(w, cap=1_000_000)
        self.assertTrue(got["닷새 합"])
        self.assertAlmostEqual(got["_세기"], (13 + 6) * 100 / 1_000_000 * 100)

    def test_a_missing_value_is_unknown_not_false(self):
        self.assertIsNone(flow_study.signals([day(1, None, -1)], None)["그날 외국인·투신 매수 + 개인 매도"])


if __name__ == "__main__":
    unittest.main()
