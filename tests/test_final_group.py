"""A그룹(최종 조건)이 시킨 대로 나뉘고 그려지는지 봅니다."""
import tempfile
import unittest
from pathlib import Path

import final_group

try:        # 화면 쪽은 streamlit이 있어야 불러집니다. A그룹을 세는 CI에는 없습니다.
    from dashboard_ui import a_group_panel
except ModuleNotFoundError:
    a_group_panel = None


class Regroup(unittest.TestCase):
    """관심종목 그룹판: A는 오늘 목록으로, 예전 A는 B로, 나머지는 그대로."""

    found = {"picks": [{"code": "000001", "갈래": ["정배열"]}]}

    def test_a_listed_stock_becomes_a(self):
        got = final_group.regroup([{"code": "000001", "group": "C"}], self.found)
        self.assertEqual(got[0]["group"], "A")
        self.assertIn("정배열", got[0]["reason"])

    def test_an_old_ema_a_that_is_not_listed_drops_to_b(self):
        got = final_group.regroup([{"code": "000002", "group": "A"}], self.found)
        self.assertEqual(got[0]["group"], "B")

    def test_b_and_c_stay_and_ungraded_is_untouched(self):
        rows = [{"code": "000003", "group": "B"}, {"code": "000004", "group": "C"},
                {"code": "000005", "group": None}]
        got = final_group.regroup(rows, self.found)
        self.assertEqual([r["group"] for r in got], ["B", "C", None])

    def test_no_list_means_no_a(self):
        got = final_group.regroup([{"code": "000001", "group": "A"}], None)
        self.assertEqual(got[0]["group"], "B")


class Files(unittest.TestCase):

    def test_load_of_a_missing_file_is_none(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(final_group.load(Path(folder) / "없음.json"))


class Lines(unittest.TestCase):
    """단순이동평균 3>15>20>90>150>200 판정."""

    def test_a_steady_rise_is_aligned_and_counts_its_days(self):
        closes = [100 * 1.004 ** k for k in range(400)]
        got = final_group.lines_now(closes)
        self.assertTrue(got["정배열"])
        self.assertGreater(got["된 지"], 100)
        self.assertTrue(got["50>200"])
        self.assertGreater(got["간격"], 0)

    def test_a_steady_fall_is_not(self):
        closes = [100 * 0.996 ** k for k in range(400)]
        got = final_group.lines_now(closes)
        self.assertFalse(got["정배열"])
        self.assertEqual(got["된 지"], 0)

    def test_too_short_a_history_is_unknown(self):
        self.assertIsNone(final_group.lines_now([100.0] * 200))


@unittest.skipIf(a_group_panel is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class Panel(unittest.TestCase):

    def test_empty_day_says_so(self):
        html = a_group_panel({"date": "20260923", "breadth": 41.0, "picks": [],
                              "near": [{"name": "가", "code": "000001", "모자란 것": "시장 폭 41%"}]})
        self.assertIn("채운 종목이", html)
        self.assertIn("2026-09-23", html)
        self.assertIn("시장 폭만 모자란", html)

    def test_listed_stocks_are_named(self):
        html = a_group_panel({"date": "20260923", "breadth": 60.0,
                              "picks": [{"name": "나<b>", "code": "000002", "갈래": ["기본 규칙"],
                                         "시총순위": 5, "추세 기울기": 2.0, "60일 전 대비": 30.0,
                                         "팔기": "종가 +10% 익절"}]})
        self.assertIn("000002", html)
        self.assertNotIn("나<b>", html, "이름을 그대로 넣으면 화면이 깨집니다")

    def test_missing_result_is_explained(self):
        self.assertIn("아직 없습니다", a_group_panel(None))



if __name__ == "__main__":
    unittest.main()
