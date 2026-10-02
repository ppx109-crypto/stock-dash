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


class Filings(unittest.TestCase):
    """시세 키가 없어도 DART만으로 결산·공시를 받습니다."""

    def provider(self):
        import providers
        one = providers.Official.__new__(providers.Official)
        one.names = {"005930": "삼성전자"}
        one.corp = lambda code: "00126380"
        have = {2023, 2024, 2025}
        one.annual = lambda corp, year, basis: ({"year": year, "revenue": 10.0 * year, "profit": 1.0,
                                                 "receipt": f"{year}0301000001"}
                                                if basis == "CFS" and year in have else None)
        one.dart = lambda endpoint, **kw: ({"corp_name": "삼성전자", "est_dt": "19690113"}
                                           if endpoint == "company.json" else {"list": []})
        one.business_excerpt = lambda receipt: "사업의 개요 " + receipt
        return one

    def test_three_years_without_a_price(self):
        got = self.provider().filings("005930")
        self.assertEqual([y["year"] for y in got["years"]], [2023, 2024, 2025])
        self.assertTrue(got["no_price"])
        self.assertIsNone(got["price"])
        self.assertIn("20250301000001", got["business_excerpt"])
        self.assertEqual(got["company"]["est_dt"], "19690113")

    def test_a_single_year_is_not_enough(self):
        import providers
        one = self.provider()
        one.annual = lambda corp, year, basis: {"year": year, "revenue": 1.0, "profit": 1.0} if year == 2025 else None
        with self.assertRaises(providers.DataError):
            one.filings("005930")


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(research_ui is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class HourlyNear(unittest.TestCase):
    """1시간봉 '충족 미달': 장중에는 매시 다시 센 것(판정 시각)을, 저녁 새 후보가 나오면 그것을 씀(사용자 요청 2026-10-02)."""

    def run_with(self, files):
        from unittest import mock
        with mock.patch.object(research_ui, "repo_json", side_effect=lambda p: files.get(p)), \
                mock.patch.object(research_ui, "today_a_group", return_value={}):
            return research_ui.near_lists()

    def test_intraday_uses_hourly_recount_with_time(self):
        plan = {"base": "20261001", "made": "2026-10-01 19:40", "near": [{"code": "000001", "모자란 수": 1}]}
        now = {"date": "20261002", "at": "2026-10-02 11:01", "near": [{"code": "000002", "모자란 수": 1}]}
        hourly, _, basis, _ = self.run_with({"hourly-live/plan.json": plan, "hourly-live/near-now.json": now})
        self.assertEqual([r["code"] for r in hourly], ["000002"])
        self.assertIn("2026-10-02 11:01 판정", basis)

    def test_evening_plan_wins_over_older_recount(self):
        plan = {"base": "20261002", "made": "2026-10-02 19:40", "near": [{"code": "000001", "모자란 수": 1}]}
        now = {"date": "20261002", "at": "2026-10-02 15:31", "near": [{"code": "000002", "모자란 수": 1}]}
        hourly, _, basis, _ = self.run_with({"hourly-live/plan.json": plan, "hourly-live/near-now.json": now})
        self.assertEqual([r["code"] for r in hourly], ["000001"])
        self.assertIn("2026-10-02 19:40 판정", basis)
