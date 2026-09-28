"""확률 검증(최종 조건)의 셈과 표 옮기기를 봅니다."""
import unittest

import numpy as np

import caps
import final_group
import final_study
import rule

try:        # 화면 쪽은 streamlit이 있어야 불러집니다.
    import study_ui
except ModuleNotFoundError:
    study_ui = None


class Grade(unittest.TestCase):

    def setUp(self):
        self.old = rule._calm
        rule._calm = 2.0
        n = 300
        self.shape = {"000001": {"정배열": np.ones(n, bool), "간격": np.full(n, 30.0),
                                 "50>200": np.ones(n, bool), "200": np.ones(n)}}

    def tearDown(self):
        rule._calm = self.old

    def row(self, **kw):
        return {"code": "000001", "i": 280, "date": "20240102", caps.RANK: 10, "변동성": 1.5,
                "추세 기울기": 2.0, "60일 전 대비": 30.0, **kw}

    def test_both_doors_open(self):
        group, doors = final_study.grade(self.row(), self.shape, {"20240102": 60.0})
        self.assertEqual(group, "A")
        self.assertEqual(doors, [final_group.RULE_DOOR, final_group.LINES_DOOR])

    def test_a_thin_market_leaves_only_the_rule(self):
        group, doors = final_study.grade(self.row(), self.shape, {"20240102": 40.0})
        self.assertEqual(doors, [final_group.RULE_DOOR])

    def test_one_short_on_both_is_b(self):
        got = final_study.grade(self.row(**{caps.RANK: 150}), self.shape, {"20240102": 60.0})
        self.assertEqual(got, ("B", []))

    def test_three_short_is_out(self):
        row = self.row(**{caps.RANK: 150, "변동성": 5.0, "추세 기울기": 0.1})
        self.shape["000001"]["정배열"][:] = False
        self.assertEqual(final_study.grade(row, self.shape, {"20240102": 40.0})[0], "밖")

    def test_early_rows_cannot_be_aligned(self):
        self.assertEqual(final_study.form_of(self.shape, self.row(i=100)), {})


class Tally(unittest.TestCase):

    def test_counts(self):
        got = final_study.tally([1.0, -2.0, 3.0, 4.0], {"a", "b"})
        self.assertEqual(got["건수"], 4)
        self.assertEqual(got["상승확률"], 75.0)
        self.assertEqual(got["종목수"], 2)
        self.assertEqual(got["최악"], -2.0)

    def test_nothing(self):
        self.assertIsNone(final_study.tally([], set()))


@unittest.skipIf(study_ui is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class Tables(unittest.TestCase):

    trading = {"2017~2020": {"매매": 173, "연수익": 7.01, "최대낙폭": -11.5, "승률": 45.1, "평균": 0.8,
                             "보유중앙": 8, "가동률": 28.4, "연패": 6, "해마다": {"2017": 5.2}},
               "2021~": {"매매": 430, "연수익": 41.41, "최대낙폭": -20.5, "승률": 34.4, "평균": 1.2,
                         "보유중앙": 6, "가동률": 48.4, "연패": 9, "해마다": {"2021": -19.3}}}

    def test_trade_rows(self):
        got = study_ui.trade_rows(self.trading)
        self.assertEqual(got[1]["연수익"], "+41.4%")
        self.assertEqual(got[0]["최대 낙폭"], "-11.5%")

    def test_years_are_in_order(self):
        self.assertEqual([r["해"] for r in study_ui.year_rows(self.trading)], ["2017", "2021"])

    def test_group_names_are_readable(self):
        tal = {"건수": 1, "종목수": 1, "상승확률": 50.0, "평균수익률": 1.0, "중앙수익률": 1.0,
               "최악": -1.0, "최고": 2.0}
        got = study_ui.group_rows({"A · 추세 규칙": {"5": tal}, "밖": {"5": tal}, "C": {}})
        self.assertEqual([r["그룹"] for r in got], ["A그룹 · 추세 규칙", "A·B그룹 밖"])


if __name__ == "__main__":
    unittest.main()
