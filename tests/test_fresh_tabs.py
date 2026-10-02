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


@unittest.skipIf(research_ui is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class IntradayFlow(unittest.TestCase):
    """장중 흐름(사용자 요청 2026-10-02 '실시간 반영 · 장중 변화 흐름으로 대시보드 내용이 변하는지 테스트'):
    15분마다 다시 센 파일이 바뀌면 두 칸(1시간봉 · 1일봉)의 충족 미달과 1일봉 후보가 따라 바뀌고, 15:20 판단 뒤에는 그 판단을 씀."""

    plan = {"base": "20261001", "made": "2026-10-01 19:40", "candidates": [], "near": [{"code": "000009", "모자란 수": 1}]}

    def board(self, files):
        from unittest import mock
        with mock.patch.object(research_ui, "repo_json", side_effect=lambda p: files.get(p)), \
                mock.patch.object(research_ui, "today_a_group", return_value={}):
            return research_ui.near_lists(), research_ui.board_marks()

    def snap(self, at, near, picks, near_daily=None, picks_daily=None):
        return {"date": "20261002", "at": at, "near": near, "picks": picks,
                "near_daily": near if near_daily is None else near_daily,
                "picks_daily": picks if picks_daily is None else picks_daily}

    def test_board_follows_the_day(self):
        n = lambda c: {"code": c, "name": c, "모자란 수": 1}
        p = lambda c: {"code": c, "name": c}
        # 10:03 — 15분봉 실행이 셈: 1개 모자람 A · 지금 값이면 후보 없음
        files = {"hourly-live/plan.json": self.plan,
                 "m15-live/near-now.json": self.snap("2026-10-02 10:03", [n("A")], [])}
        (h, d, hb, db), (_, daily) = self.board(files)
        self.assertEqual([r["code"] for r in h], ["A"])
        self.assertEqual([r["code"] for r in d], ["A"])
        self.assertIn("10:03 판정", hb)
        self.assertIn("10:03 판정", db)
        self.assertEqual(daily, {})
        # 10:11 — 1시간봉 실행(매시)도 셈했지만 10:18 15분봉 셈이 더 늦음 → 늦은 것을 씀 · B가 지금 값이면 후보가 됨
        files["hourly-live/near-now.json"] = self.snap("2026-10-02 10:11", [n("A")], [])
        files["m15-live/near-now.json"] = self.snap("2026-10-02 10:18", [n("C")], [p("B")])
        (h, d, hb, db), (_, daily) = self.board(files)
        self.assertEqual([r["code"] for r in h], ["C"])
        self.assertIn("10:18 판정", hb)
        self.assertIn("B", daily)
        self.assertIn("지금 값이면", daily["B"])
        # 목표가가 내린 후보는 1일봉 칸에서 충족 미달(거름)로 · 1시간봉 칸 충족 미달은 그대로
        files["m15-live/near-now.json"] = self.snap("2026-10-02 10:33", [n("C")], [p("B")],
                                                    near_daily=[{"code": "B", "모자란 수": 1}, n("C")], picks_daily=[])
        (h, d, hb, db), (_, daily) = self.board(files)
        self.assertEqual([r["code"] for r in d], ["B", "C"])
        self.assertNotIn("B", daily)
        # 15:32 — 15:20 1일봉 판단이 나오면 1일봉 칸은 그 판단을 씀(미리 보기 끝)
        files["daily-live/today.json"] = {"date": "20261002", "made": "2026-10-02 15:32", "candidates": [{"code": "D", "name": "D", "칸": 2}],
                                          "near": [n("E")]}
        files["m15-live/near-now.json"] = self.snap("2026-10-02 15:48", [n("C")], [p("B")])
        (h, d, hb, db), (_, daily) = self.board(files)
        self.assertEqual([r["code"] for r in d], ["E"])
        self.assertIn("15:20 판단", db)
        self.assertEqual(set(daily), {"D"})
        self.assertIn("15:48 판정", hb, "1시간봉 칸은 장 끝까지 15분마다")
        # 저녁 — 다음 거래일 후보(plan)가 나오면 1시간봉 칸은 그것을 씀
        files["hourly-live/plan.json"] = {"base": "20261002", "made": "2026-10-02 19:40", "candidates": [], "near": [n("F")]}
        (h, d, hb, db), _ = self.board(files)
        self.assertEqual([r["code"] for r in h], ["F"])
