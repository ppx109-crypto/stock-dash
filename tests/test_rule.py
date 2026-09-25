"""층별 성적표가 정직한지 봅니다.

화면에 '1층은 열에 일곱'이라고 적는 값입니다. 표본이 모자라는데도 숫자를
내놓거나, 비용을 빼지 않고 적으면 사람을 잘못 이끌게 됩니다.
"""
import unittest

from unittest.mock import patch

import caps
import events
import lab
import rule


def rows(count, tier_gap, tier_band, gain, date="20200101", code="005930"):
    return [{"code": f"{code[:4]}{k % 10}", "date": date, "i": 200,
             "중기 이격": tier_gap, "중기 이격밴드": tier_band,
             "ahead": {lab.HORIZON: gain}} for k in range(count)]


class Conditions(unittest.TestCase):
    """네 조건. 하나라도 빠지면 사면 안 됩니다."""

    def setUp(self):
        rule._calm = 2.0
        self.addCleanup(setattr, rule, "_calm", None)

    def row(self, **kw):
        got = {"code": "005930", "date": "20200101", "변동성": 1.5,
               "추세 기울기": 2.0, "60일 전 대비": 30.0,
               caps.RANK: 10}
        got.update(kw)
        return got

    def test_all_five_met_is_a_buy(self):
        self.assertTrue(rule.holds(self.row()))

    def test_outside_the_top_hundred_is_not(self):
        self.assertFalse(rule.holds(self.row(**{caps.RANK: 101})))

    def test_an_unknown_rank_is_not(self):
        """순위를 모르면 '바깥'이 아니라 '모름'이고, 사지 않습니다."""
        got = self.row()
        del got[caps.RANK]
        self.assertFalse(rule.holds(got))

    def test_too_lively_is_not(self):
        self.assertFalse(rule.holds(self.row(변동성=2.5)))

    def test_too_flat_a_slope_is_not(self):
        self.assertFalse(rule.holds(self.row(**{"추세 기울기": 1.0})))

    def test_a_missing_number_is_not(self):
        got = self.row()
        del got["추세 기울기"]
        self.assertFalse(rule.holds(got))

    def test_without_the_calm_edge_nothing_is_bought(self):
        """문턱을 아직 못 구했으면 사지 않습니다. 빈 값을 통과로 세면 안 됩니다."""
        rule._calm = None
        self.assertFalse(rule.holds(self.row()))

    def test_the_steeper_one_comes_first(self):
        steep = self.row(**{"추세 기울기": 3.0})
        gentle = self.row(**{"추세 기울기": 1.8})
        self.assertLess(rule.order(steep), rule.order(gentle))

    def test_dropping_one_condition_lets_more_through(self):
        turned = self.row(**{"추세 기울기": 1.0})
        self.assertFalse(rule.holds(turned))
        self.assertTrue(rule.holds_without(turned, "slope"))

    def test_the_calm_edge_is_a_quantile_not_a_fixed_number(self):
        """시장이 통째로 조용해져도 '상대적으로 조용한 쪽'을 가리켜야 합니다."""
        rule._calm = None
        rows = [{"변동성": v} for v in range(1, 101)]
        self.assertAlmostEqual(rule.calm_edge(rows), 41.0)


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
        self.assertIn("100등", rule.WHY)
        self.assertIn(f"{rule.SLOPE:g}", rule.WHY)

    def test_the_kinship_bar_is_mid_range(self):
        """0.5~0.7이 모두 같은 방향이라 가운데를 씁니다. 가장자리는 위험합니다."""
        self.assertGreaterEqual(rule.KIN, 0.5)
        self.assertLessEqual(rule.KIN, 0.7)


class Risk(unittest.TestCase):
    """골 수치는 화면에서 가장 무거운 숫자입니다. 셈이 맞아야 합니다."""

    def test_the_caveat_says_the_drawdown(self):
        """주의 문구가 한 번의 손실만 말하고 이어지는 손실을 빼먹으면 안 됩니다."""
        for must in ("−18.5%", "−10.5%", "임시", "살아남은", "연패"):
            self.assertIn(must, rule.CAVEAT, f"주의 문구에 '{must}'이 없습니다")

    def test_an_empty_run_gives_an_empty_report(self):
        with patch.object(lab, "run", return_value=None):
            self.assertEqual(rule.risk_stats([], {}), {})


class Halves(unittest.TestCase):
    """공격 갈래(73회차)도 규칙과 같은 길로 재야 합니다."""

    def _seen(self, **kw):
        calls = []

        def fake(rows, prices, holds, exit_at, **opts):
            calls.append((exit_at, opts["slots"]))
            return None
        with patch.object(lab, "run", side_effect=fake), \
                patch.object(lab, "exit_fixed", side_effect=lambda *a: a), \
                patch.object(rule, "apart", return_value=None):
            rule.halves([], {}, **kw)
        return calls

    def test_left_empty_it_is_the_rule(self):
        for exit_at, slots in self._seen():
            self.assertEqual(exit_at, (rule.TAKE, rule.STOP, rule.LIMIT))
            self.assertEqual(slots, rule.SLOTS)

    def test_the_aggressive_track_is_passed_through(self):
        seen = self._seen(slots=2, take=12, stop=8)
        self.assertEqual(len(seen), 2)
        for exit_at, slots in seen:
            self.assertEqual(exit_at, (12, 8, rule.LIMIT))
            self.assertEqual(slots, 2)


if __name__ == "__main__":
    unittest.main()


class OneDoor(unittest.TestCase):
    """52회차에 문을 둘로 늘렸다가 57회차에 되돌렸습니다.

    터짐 문은 주식수 자료가 절반뿐이라 순위가 헐겁던 때만 좋아 보였습니다.
    제대로 줄을 세우니 앞에서 지고 뒤에서 비기며 골만 네 배였습니다.
    `burst_leg`는 남아 있지만 `holds`는 더 이상 부르지 않습니다.
    """

    def setUp(self):
        rule._calm = 2.0

    def tearDown(self):
        rule._calm = None

    def row(self, **kw):
        got = {caps.RANK: 50, "변동성": 1.0, "추세 기울기": 2.0,
               "60일 전 대비": 30.0, "배열": 0, "거래량비": 1.0}
        got.update(kw)
        return got

    def test_the_trend_door_alone_is_enough(self):
        self.assertTrue(rule.holds(self.row()))

    def test_the_burst_door_no_longer_buys_anything(self):
        # 정배열에 거래량이 터졌어도, 시끄럽고 추세가 없으면 안 삽니다.
        loud = self.row(변동성=9.0, 배열=3, 거래량비=7.0)
        loud["추세 기울기"] = 0.0
        loud["60일 전 대비"] = 0.0
        self.assertTrue(rule.burst_leg(loud))
        self.assertFalse(rule.holds(loud))

    def test_neither_door_means_no(self):
        self.assertFalse(rule.holds(self.row(배열=3, 거래량비=2.0, 변동성=9.0)))

    def test_the_burst_door_needs_the_four_lines_in_order(self):
        self.assertFalse(rule.holds(self.row(변동성=9.0, 배열=2, 거래량비=9.0)))

    def test_the_rank_gate_covers_both_doors(self):
        out = self.row(배열=3, 거래량비=9.0)
        out[caps.RANK] = 500
        self.assertFalse(rule.holds(out))

    def test_the_trend_door_is_the_only_way_in(self):
        """네 조건 가운데 하나만 빠져도 안 삽니다 — 거래량은 이제 상관없습니다."""
        for missing in ("변동성", "추세 기울기", "60일 전 대비"):
            row = self.row(배열=3, 거래량비=99.0)
            row[missing] = 9.0 if missing == "변동성" else -99.0
            self.assertFalse(rule.holds(row), missing)
