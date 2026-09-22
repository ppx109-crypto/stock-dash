"""층별 성적표가 정직한지 봅니다.

화면에 '1층은 열에 일곱'이라고 적는 값입니다. 표본이 모자라는데도 숫자를
내놓거나, 비용을 빼지 않고 적으면 사람을 잘못 이끌게 됩니다.
"""
import unittest

import lab
import rule


def rows(count, tier_gap, tier_band, gain, date="20200101", code="005930"):
    return [{"code": f"{code[:4]}{k % 10}", "date": date, "i": 200,
             "중기 이격": tier_gap, "중기 이격밴드": tier_band,
             "ahead": {lab.HORIZON: gain}} for k in range(count)]


class TierStats(unittest.TestCase):

    def test_a_thin_tier_gets_no_number(self):
        """59건이면 한 줄도 내지 않습니다."""
        self.assertEqual(rule.tier_stats(rows(59, -25.0, -3.0, 10.0)), [])

    def test_sixty_is_enough(self):
        found = rule.tier_stats(rows(60, -25.0, -3.0, 10.0))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["층"], 1)
        self.assertEqual(found[0]["건수"], 60)

    def test_the_cost_is_taken_off(self):
        """10% 올랐어도 왕복 비용을 뺀 값을 적습니다."""
        found = rule.tier_stats(rows(60, -25.0, -3.0, 10.0))
        self.assertAlmostEqual(found[0]["평균"], round(10.0 - lab.COST, 2))
        self.assertAlmostEqual(found[0]["중앙"], round(10.0 - lab.COST, 2))

    def test_days_are_counted_apart_from_rows(self):
        """같은 날 여러 종목이 걸린 것을 기회 여러 번으로 세면 안 됩니다."""
        found = rule.tier_stats(rows(60, -25.0, -3.0, 10.0))
        self.assertEqual(found[0]["날"], 1)
        self.assertLess(found[0]["종목"], found[0]["건수"])

    def test_rows_before_the_confirm_period_are_left_out(self):
        early = rows(60, -25.0, -3.0, 10.0, date="20100101")
        self.assertEqual(rule.tier_stats(early), [])
        self.assertEqual(len(rule.tier_stats(early, since="20090101")), 1)

    def test_a_row_without_a_forward_return_is_not_counted(self):
        mixed = rows(60, -25.0, -3.0, 10.0)
        for row in mixed[:30]:
            row["ahead"] = {}
        self.assertEqual(rule.tier_stats(mixed), [])


if __name__ == "__main__":
    unittest.main()
