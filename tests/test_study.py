"""조사 엔진. 만들어 둔 가격으로 셈이 맞는지 봅니다."""
import unittest
import unittest.mock

import study


def rising(n=200, start=100.0, step=0.01):
    return [(f"2026{(i // 30) + 1:02d}{(i % 30) + 1:02d}", start * (1 + step) ** i)
            for i in range(n)]


class Observing(unittest.TestCase):
    def prices(self, rows):
        return {"005930": {"name": "테스트", "rows": rows}}

    def test_a_steady_rise_is_read_as_the_top_group(self):
        found = study.observations(self.prices(rising()), {})
        self.assertTrue(found)
        self.assertTrue(all(r["group"] == "A" for r in found))

    def test_the_future_is_never_used_to_judge_today(self):
        # 마지막 날은 앞을 볼 수 없어 관측에 들어가지 않습니다.
        rows = rising(130)
        found = study.observations(self.prices(rows), {}, horizons=(5,), warmup=60)
        self.assertLessEqual(max(r["date"] for r in found), rows[-6][0])

    def test_a_win_rate_and_a_middle_are_counted(self):
        rows = [{"ahead": {20: 5.0}}, {"ahead": {20: -3.0}},
                {"ahead": {20: 1.0}}, {"ahead": {20: 9.0}}]
        found = study.tally(rows, 20)
        self.assertEqual(found["건수"], 4)
        self.assertEqual(found["상승확률"], 75.0)
        self.assertEqual(found["중앙수익률"], 3.0)
        self.assertEqual(found["최악"], -3.0)

    def test_nothing_to_count_is_nothing(self):
        self.assertIsNone(study.tally([], 20))
        self.assertIsNone(study.tally([{"ahead": {5: 1.0}}], 20))


class MoneyAxis(unittest.TestCase):
    def test_growth_and_margin_come_out_as_percentages(self):
        axis = study.money_axis({"financial": {
            "revenue": 110.0, "prior_revenue": 100.0,
            "operating_profit": 11.0, "prior_operating_profit": 10.0}})
        self.assertAlmostEqual(axis["매출성장"], 10.0)
        self.assertAlmostEqual(axis["영업이익성장"], 10.0)
        self.assertAlmostEqual(axis["영업이익률"], 10.0)
        self.assertTrue(axis["흑자"])

    def test_a_loss_last_year_gives_no_growth_number(self):
        # 적자에서 흑자로 가면 증가율을 %로 말할 수 없습니다.
        axis = study.money_axis({"financial": {
            "revenue": 110.0, "prior_revenue": 100.0,
            "operating_profit": 5.0, "prior_operating_profit": -10.0}})
        self.assertNotIn("영업이익성장", axis)
        self.assertTrue(axis["흑자"])

    def test_no_financials_is_empty(self):
        self.assertEqual(study.money_axis({}), {})
        self.assertEqual(study.money_axis(None), {})


class Lift(unittest.TestCase):
    def rows(self, pairs):
        return [{"group": "A", "ahead": {20: move}, "매출성장": axis}
                for move, axis in pairs]

    def test_a_condition_that_helps_shows_a_positive_gap(self):
        rows = self.rows([(5.0, 20.0), (4.0, 30.0), (-2.0, -5.0), (-3.0, -8.0)])
        found = study.lift(rows, "매출성장", 0.0, 20)
        self.assertEqual(found["기준 상승확률"], 50.0)
        self.assertEqual(found["더한 뒤"], 100.0)
        self.assertEqual(found["차이"], 50.0)

    def test_a_condition_nobody_meets_is_not_reported(self):
        rows = self.rows([(5.0, -20.0), (-4.0, -30.0)])
        self.assertIsNone(study.lift(rows, "매출성장", 99.0, 20))


class PointInTime(unittest.TestCase):
    """그날 이미 공시된 실적만 써야 합니다. 안 그러면 어떤 규칙이든 좋아 보입니다."""

    def timeline(self):
        return [("20250311", {"매출성장": 16.2, "영업이익률": 10.9}),
                ("20260310", {"매출성장": 10.9, "영업이익률": 13.1}),
                ("20260814", {"매출성장": 98.7, "영업이익률": 48.0})]

    def test_before_the_first_filing_nothing_is_known(self):
        self.assertEqual(study.known_by(self.timeline(), "20240101"), {})

    def test_the_day_of_the_filing_counts_as_known(self):
        self.assertEqual(study.known_by(self.timeline(), "20250311")["매출성장"], 16.2)

    def test_the_day_before_a_filing_still_uses_the_older_one(self):
        self.assertEqual(study.known_by(self.timeline(), "20260813")["매출성장"], 10.9)

    def test_a_later_day_uses_the_newest_filing(self):
        self.assertEqual(study.known_by(self.timeline(), "20260901")["영업이익률"], 48.0)

    def test_two_filings_on_the_same_day_do_not_stop_the_run(self):
        # 연간과 반기가 같은 날 들어오는 종목이 있습니다.
        import json, tempfile, pathlib
        folder = tempfile.mkdtemp()
        (pathlib.Path(folder) / "005930.json").write_text(json.dumps({
            "years": [{"year": 2024, "revenue": 100, "profit": 10, "receipt": "20250311000001"},
                      {"year": 2025, "revenue": 110, "profit": 11, "receipt": "20260310000001"}],
            "halves": [{"period": "2025-06", "revenue": 50, "profit": 5,
                        "receipt": "20260310000002", "measure": "cumulative"},
                       {"period": "2026-06", "revenue": 60, "profit": 6,
                        "receipt": "20260310000003", "measure": "cumulative"}]}),
            encoding="utf-8")
        found = study.money_timeline("005930", folder=folder)
        self.assertEqual([day for day, _ in found], ["20260310", "20260310"])

    def test_a_growth_rate_needs_a_profitable_year_to_compare_with(self):
        self.assertNotIn("영업이익성장", study._axis(110, 100, 5, -10))
        self.assertIn("영업이익성장", study._axis(110, 100, 11, 10))


class Combo(unittest.TestCase):
    def rows(self, items):
        return [{"group": "A", "ahead": {20: move}, "매출성장": a, "영업이익률": b}
                for move, a, b in items]

    def test_a_thin_result_is_withheld(self):
        # 표본이 적으면 높은 확률도 우연과 구분되지 않습니다.
        rows = self.rows([(5.0, 20.0, 12.0)] * 10)
        self.assertIsNone(study.combo(rows, (("매출성장", 0.0),), 20, floor=30))

    def test_both_conditions_must_hold(self):
        rows = self.rows([(5.0, 20.0, 12.0)] * 20 + [(-5.0, 20.0, 1.0)] * 20)
        found = study.combo(rows, (("매출성장", 0.0), ("영업이익률", 10.0)), 20, floor=10)
        self.assertEqual(found["건수"], 20)
        self.assertEqual(found["상승확률"], 100.0)


class Downside(unittest.TestCase):
    def test_the_worst_tenth_is_measured(self):
        rows = [{"ahead": {20: float(i)}} for i in range(-50, 50)]
        found = study.worst_case(rows, 20, share=10)
        self.assertEqual(found["하위 10% 경계"], -41.0)

    def test_too_few_days_gives_nothing(self):
        self.assertIsNone(study.worst_case([{"ahead": {20: 1.0}}] * 5, 20))


class Search(unittest.TestCase):
    """돈이 되는 조합을 찾는 부분. 순서가 기대수익이어야 합니다."""

    def rows(self, items):
        return [{"group": "A", "ahead": {20: move}, "매출성장": a, "영업이익률": b}
                for move, a, b in items]

    def test_costs_come_off_the_expected_return(self):
        block = {"평균수익률": 1.0}
        self.assertAlmostEqual(study.net(block, cost=0.25), 0.75)

    def test_a_high_win_rate_with_small_wins_loses_to_a_bigger_one(self):
        # 자주 이기지만 조금 버는 쪽보다, 덜 이겨도 크게 버는 쪽이 위여야 합니다.
        often = self.rows([(0.4, 20.0, 12.0)] * 90 + [(-0.5, 20.0, 12.0)] * 10)
        rarely = self.rows([(9.0, -5.0, 1.0)] * 55 + [(-5.0, -5.0, 1.0)] * 45)
        found = study.search(often + rarely, 20, floor=60)
        top = found[0]
        self.assertIn("조건 없음", top["조건"])
        better = [r for r in found if "매출성장 ≥ 0" in r["조건"]][0]
        self.assertLess(better["순기대수익"], top["순기대수익"])

    def test_a_thin_combination_is_dropped(self):
        found = study.search(self.rows([(5.0, 20.0, 12.0)] * 10), 20, floor=60)
        self.assertEqual(found, [])

    def test_the_excess_is_measured_against_the_baseline(self):
        rows = self.rows([(5.0, 20.0, 12.0)] * 100)
        base = study.tally(self.rows([(1.0, 0.0, 0.0)] * 100), 20)
        found = study.search(rows, 20, floor=60, baseline=base)
        self.assertAlmostEqual(found[0]["전체대비"], 4.0)

    def test_the_group_effect_is_kept_apart_from_the_condition(self):
        # 조건이 걸러 내는 것이 없으면 그룹대비는 0이어야 합니다. 그래야
        # 전체대비에 섞인 그룹의 몫을 조건의 공으로 돌리지 않습니다.
        rows = self.rows([(5.0, 20.0, 12.0)] * 100)
        base = study.tally(self.rows([(1.0, 0.0, 0.0)] * 100), 20)
        found = study.search(rows, 20, floor=60, baseline=base)
        picked = [r for r in found if "매출성장 ≥ 0" in r["조건"]][0]
        self.assertAlmostEqual(picked["그룹대비"], 0.0)
        self.assertAlmostEqual(picked["전체대비"], 4.0)


if __name__ == "__main__":
    unittest.main()


class AroundFilings(unittest.TestCase):
    """공시 앞뒤를 가르는 부분. 앞이 크면 이미 들어가 있었다는 뜻입니다."""

    def prices(self, before, after, span=5):
        """공시 전 span일에 before배, 공시 후 span일에 after배가 되는 값입니다."""
        rows, price = [], 100.0
        for i in range(span):
            rows.append((f"2025{i + 1:02d}01", price))
        price *= before
        rows.append(("20260101", price))          # 공시 뒤 첫 거래일
        for i in range(span):
            rows.append((f"2027{i + 1:02d}01", price * after))
        return {"005930": {"name": "테스트", "rows": rows}}

    def timeline(self, margin):
        return [("20260101", {"영업이익률": margin, "흑자": True})]

    def test_a_run_up_before_the_filing_is_visible(self):
        prices = self.prices(1.5, 1.05)
        with unittest.mock.patch.object(study, "money_timeline",
                                        return_value=self.timeline(20.0)):
            found = study.around_filings(prices, span=5, floor=1)
        self.assertAlmostEqual(found["좋음"]["공시전 중앙"], 50.0)
        self.assertAlmostEqual(found["좋음"]["공시후 중앙"], 5.0)

    def test_a_thin_margin_lands_in_the_ordinary_bucket(self):
        with unittest.mock.patch.object(study, "money_timeline",
                                        return_value=self.timeline(3.0)):
            found = study.around_filings(self.prices(1.2, 1.1), span=5, floor=1)
        self.assertIn("보통", found)
        self.assertNotIn("좋음", found)

    def test_a_loss_is_kept_apart(self):
        with unittest.mock.patch.object(
                study, "money_timeline",
                return_value=[("20260101", {"영업이익률": -2.0, "흑자": False})]):
            found = study.around_filings(self.prices(1.1, 1.1), span=5, floor=1)
        self.assertIn("적자", found)

    def test_too_few_filings_report_nothing(self):
        with unittest.mock.patch.object(study, "money_timeline", return_value=[]):
            self.assertEqual(study.around_filings(self.prices(1.2, 1.1), span=5), {})
