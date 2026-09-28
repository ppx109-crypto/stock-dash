"""종목 탭을 누를 때 받아 온 최신 자료를 표로 바르게 옮기는지 봅니다."""
import unittest

try:        # 화면 쪽은 streamlit이 있어야 불러집니다.
    import research_ui
except ModuleNotFoundError:
    research_ui = None


@unittest.skipIf(research_ui is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class Years(unittest.TestCase):

    def test_three_years_with_change(self):
        got = research_ui.years_table({"years": [
            {"year": 2023, "revenue": 1000.0, "profit": -50.0},
            {"year": 2024, "revenue": 1200.0, "profit": 100.0},
            {"year": 2025, "revenue": 1500.0, "profit": 150.0}]})
        self.assertEqual([r["결산연도"] for r in got], ["2023", "2024", "2025"])
        self.assertEqual(got[0]["매출 변화"], "—")
        self.assertEqual(got[1]["매출 변화"], "+20.0%")
        self.assertEqual(got[1]["영업이익 변화"], "흑자 전환")
        self.assertEqual(got[2]["영업이익(억원)"], "150")

    def test_a_missing_account_is_a_dash(self):
        got = research_ui.years_table({"years": [{"year": 2024, "revenue": None, "profit": 10.0},
                                                 {"year": 2025, "revenue": 5.0, "profit": 20.0}]})
        self.assertEqual(got[0]["매출(억원)"], "—")
        self.assertEqual(got[1]["매출 변화"], "—")


@unittest.skipIf(research_ui is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class Flows(unittest.TestCase):

    def test_sums_the_last_days_and_skips_blanks(self):
        rows = [{"date": f"2026092{d}", "외국인": 10, "기관": None, "개인": -10} for d in range(7)]
        sums, begin, end = research_ui.flow_sums(rows, days=5)
        self.assertEqual(sums["외국인"], 50)
        self.assertIsNone(sums["기관"])
        self.assertEqual((begin, end), ("20260922", "20260926"))

    def test_no_rows(self):
        sums, begin, end = research_ui.flow_sums([])
        self.assertIsNone(begin)


@unittest.skipIf(research_ui is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class Codes(unittest.TestCase):

    def test_only_six_digits_fetch(self):
        self.assertTrue(research_ui._is_code("005930"))
        self.assertFalse(research_ui._is_code("pending-abc"))
        self.assertFalse(research_ui._is_code(None))


if __name__ == "__main__":
    unittest.main()
