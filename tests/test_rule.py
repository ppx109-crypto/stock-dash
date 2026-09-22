"""층별 성적표가 정직한지 봅니다.

화면에 '1층은 열에 일곱'이라고 적는 값입니다. 표본이 모자라는데도 숫자를
내놓거나, 비용을 빼지 않고 적으면 사람을 잘못 이끌게 됩니다.
"""
import unittest

from unittest.mock import patch

import events
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


class Filings(unittest.TestCase):
    """오늘 후보 옆에 붙는 공시. 그날까지 난 것만이어야 합니다."""

    def setUp(self):
        patcher = patch.object(events, "timeline",
                               return_value=(("20200110", "자사주취득"),
                                             ("20200320", "유상증자")))
        patcher.start(); self.addCleanup(patcher.stop)

    def test_only_filings_up_to_that_day(self):
        got = rule._filings("005930", "20200115")
        self.assertEqual([one["갈래"] for one in got], ["자사주취득"])

    def test_a_later_filing_never_appears(self):
        """3월 공시는 1월의 줄에 나오면 안 됩니다."""
        got = rule._filings("005930", "20200115")
        self.assertNotIn("유상증자", [one["갈래"] for one in got])

    def test_an_old_filing_falls_out_of_the_window(self):
        self.assertEqual(rule._filings("005930", "20200601"), [])

    def test_a_stock_with_no_data_says_so(self):
        """자료가 없는 종목은 '공시 없음'이 아니라 '모름'입니다."""
        with patch.object(events, "covered", return_value=False):
            self.assertIsNone(rule._filings("000000", "20200115"))

    def test_the_age_is_counted_back_from_the_day(self):
        got = rule._filings("005930", "20200115")
        self.assertEqual(got[0]["며칠 전"], 5)


class Spacing(unittest.TestCase):
    """하루에 담는 수. 셋을 한날에 몰아 담으면 폭락 때 셋이 함께 물립니다."""

    def test_the_rule_spaces_its_buying(self):
        self.assertLess(rule.PER_DAY, rule.SLOTS)

    def test_the_why_says_so(self):
        """화면에 나가는 설명이 규칙과 어긋나면 안 됩니다."""
        self.assertIn("하루에 새로 담는 것은 둘까지", rule.WHY)
        self.assertIn("같이 움직이던", rule.WHY)

    def test_the_kinship_bar_is_mid_range(self):
        """0.5~0.7이 모두 같은 방향이라 가운데를 씁니다. 가장자리는 위험합니다."""
        self.assertGreaterEqual(rule.KIN, 0.5)
        self.assertLessEqual(rule.KIN, 0.7)


class Risk(unittest.TestCase):
    """골 수치는 화면에서 가장 무거운 숫자입니다. 셈이 맞아야 합니다."""

    def test_the_caveat_says_the_drawdown(self):
        """주의 문구가 한 번의 손실만 말하고 이어지는 손실을 빼먹으면 안 됩니다."""
        for must in ("−39.9%", "여덟 달", "열세 번", "2008년"):
            self.assertIn(must, rule.CAVEAT, f"주의 문구에 '{must}'이 없습니다")

    def test_an_empty_run_gives_an_empty_report(self):
        with patch.object(lab, "run", return_value=None):
            self.assertEqual(rule.risk_stats([], {}), {})


if __name__ == "__main__":
    unittest.main()
