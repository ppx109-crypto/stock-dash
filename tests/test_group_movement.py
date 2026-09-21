"""새 종가가 들어오면 종목이 스스로 다른 그룹으로 옮겨가야 합니다.

장이 끝나고 다음 날 시세가 한 줄 늘면, EMA가 다시 계산되고 그룹도 따라 바뀝니다.
사람이 손으로 옮기는 자리가 없으므로, 그 연결이 끊기지 않았는지 지켜봅니다.
"""
import unittest

import trend


def rising(days=120, rate=1.004, start=100.0):
    return [start * rate ** i for i in range(days)]


class GroupMovesWithNewCloses(unittest.TestCase):
    def test_a_group_while_the_price_stays_above_every_line(self):
        self.assertEqual(trend.assess(rising())["group"], "A")

    def test_one_bad_day_drops_it_to_b_by_the_short_line_alone(self):
        closes = rising()
        closes.append(closes[-1] * 0.97)
        result = trend.assess(closes)
        self.assertEqual(result["group"], "B")
        self.assertEqual([name for name, ok in result["trend"]["checks"].items() if not ok],
                         ["종가 > EMA5"])

    def test_a_longer_fall_takes_it_to_c(self):
        closes = rising()
        for drop in (0.97, 0.96, 0.95):
            closes.append(closes[-1] * drop)
        self.assertEqual(trend.assess(closes)["group"], "C")

    def test_recovery_brings_it_back_to_a(self):
        closes = rising()
        for drop in (0.97, 0.96, 0.95):
            closes.append(closes[-1] * drop)
        self.assertEqual(trend.assess(closes)["group"], "C")
        for _ in range(12):
            closes.append(closes[-1] * 1.05)
        self.assertEqual(trend.assess(closes)["group"], "A")

    def test_the_newest_close_is_the_one_that_decides(self):
        """맨 뒤가 가장 최근이라는 약속이 지켜지는지 봅니다."""
        closes = rising()
        self.assertEqual(trend.assess(closes)["trend"]["price"], closes[-1])


if __name__ == "__main__":
    unittest.main()
