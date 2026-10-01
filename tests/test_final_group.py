"""A·B그룹(최종 조건)이 시킨 대로 나뉘고 그려지는지 봅니다."""
import tempfile
import unittest
from pathlib import Path

import caps
import final_group
import rule

try:        # 화면 쪽은 streamlit이 있어야 불러집니다. A그룹을 세는 CI에는 없습니다.
    from dashboard_ui import sortie_panel, group_buckets, stock_score, close_panel, ledger_panel
except ModuleNotFoundError:
    sortie_panel = group_buckets = stock_score = close_panel = ledger_panel = None


class Regroup(unittest.TestCase):
    """관심종목 그룹판: A는 오늘 목록, B는 1~2개 미달(코멘트), 그 밖은 싣지 않음."""

    found = {"date": "20260923",
             "picks": [{"code": "000001", "갈래": ["정배열 추세"]}],
             "b_group": [{"code": "000002", "모자란 수": 1,
                          "코멘트": "추세 규칙까지 1개 모자람: 60일 상승 +11.10%"}],
             "counted": ["000001", "000002", "000003"]}

    def test_a_listed_stock_becomes_a(self):
        got = final_group.regroup([{"code": "000001", "group": "C"}], self.found)
        self.assertEqual(got[0]["group"], "A")
        self.assertIn("정배열", got[0]["comment"])

    def test_a_near_stock_becomes_b_with_its_reason(self):
        got = final_group.regroup([{"code": "000002", "group": "A"}], self.found)
        self.assertEqual(got[0]["group"], "B")
        self.assertIn("60일 상승", got[0]["comment"])
        self.assertEqual(got[0]["shortfall"], 1)

    def test_a_counted_stock_that_misses_more_is_left_out(self):
        got = final_group.regroup([{"code": "000003", "group": "B"}], self.found)
        self.assertEqual(got[0]["group"], "밖")

    def test_a_far_stock_keeps_what_it_misses(self):
        found = {**self.found, "far": {"000003": {"모자란 수": 3, "코멘트": "추세 규칙까지 3개 모자람: 가, 나, 다"}}}
        got = final_group.regroup([{"code": "000003"}], found)
        self.assertEqual(got[0]["shortfall"], 3)
        self.assertIn("가, 나, 다", got[0]["comment"])

    def test_a_stock_outside_the_study_is_pending(self):
        got = final_group.regroup([{"code": "999999", "group": "A"}], self.found)
        self.assertIsNone(got[0]["group"])
        self.assertIn("507종목", got[0]["note"])


class Shortfalls(unittest.TestCase):
    """갈래마다 못 채운 조건을 읽을 말로 돌려줍니다."""

    def row(self, **kw):
        base = {caps.RANK: 10, "변동성": 1.5, "추세 기울기": 2.0, "60일 전 대비": 30.0}
        return {**base, **kw}

    form = {"정배열": True, "간격": 30.0}
    good = {"외국인": 100.0, "투신": 10.0, "개인": -110.0, "끝날": "20260922"}

    def test_everything_met_is_empty(self):
        got = final_group.shortfalls(self.row(), self.form, 60.0, 2.0, self.good)
        self.assertEqual(got, {"추세 규칙": [], "정배열 추세": []})

    def test_each_missing_rule_condition_is_named(self):
        got = final_group.shortfalls(self.row(**{"변동성": 3.7, "60일 전 대비": 11.1}),
                                     self.form, 60.0, 2.0, self.good)
        self.assertEqual(len(got["추세 규칙"]), 2)
        self.assertIn("흔들림", got["추세 규칙"][0])
        self.assertIn("60일 상승", got["추세 규칙"][1])
        self.assertEqual(got["정배열 추세"], [])

    def test_the_rank_gate_counts_in_both_doors(self):
        got = final_group.shortfalls(self.row(**{caps.RANK: 150}), self.form, 60.0, 2.0, self.good)
        self.assertIn("150위", got["추세 규칙"][0])
        self.assertIn("150위", got["정배열 추세"][0])

    def test_a_thin_market_holds_the_lines_door(self):
        got = final_group.shortfalls(self.row(), self.form, 41.0, 2.0, self.good)
        self.assertEqual(got["정배열 추세"], ["시장 폭 41% (50% 이상이어야 함)"])

    def test_the_slope_threshold_is_the_rules(self):
        got = final_group.shortfalls(self.row(**{"추세 기울기": rule.SLOPE - 0.01}), self.form, 60.0, 2.0, self.good)
        self.assertIn("180일선 기울기", got["추세 규칙"][0])


class Flows(unittest.TestCase):
    """스승님 수급 조건: 전날까지 5일 합으로 외국인·투신 순매수, 개인 순매도."""

    def rows(self, n=8, f=10.0, t=1.0, p=-11.0):
        days = [f"202609{d:02d}" for d in (10, 11, 14, 15, 16, 17, 18, 21, 22, 23)][:n]
        return [{"date": d, "외국인": f, "투신": t, "개인": p} for d in days]

    def test_the_signal_day_is_left_out(self):
        rows = self.rows(n=6) + [{"date": "20260923", "외국인": -999.0, "투신": -999.0, "개인": 999.0}]
        got = final_group.flow_before(rows, "20260923")
        self.assertEqual(got["외국인"], 50.0)
        self.assertEqual(got["끝날"], "20260917")

    def test_too_few_days_is_unknown(self):
        self.assertIsNone(final_group.flow_before(self.rows(n=4), "20260923"))

    def test_stale_flows_are_unknown(self):
        self.assertIsNone(final_group.flow_before(self.rows(n=6), "20261020"))

    def test_both_doors_need_the_flow(self):
        row = {caps.RANK: 10, "변동성": 1.5, "추세 기울기": 2.0, "60일 전 대비": 30.0}
        form = {"정배열": True, "간격": 30.0}
        bad = {"외국인": 10.0, "투신": -1.0, "개인": -9.0}
        got = final_group.shortfalls(row, form, 60.0, 2.0, bad)
        self.assertIn("투신 -1", got["추세 규칙"][0])
        self.assertIn("투신 -1", got["정배열 추세"][0])
        self.assertIn("수급 자료 없음", final_group.shortfalls(row, form, 60.0, 2.0)["추세 규칙"][0])


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


@unittest.skipIf(sortie_panel is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class Panel(unittest.TestCase):
    """메인 '정시 출격 · 오늘의 결과' 판."""
    from datetime import datetime as _dt
    MORNING = _dt(2026, 10, 1, 11, 0)      # 목요일 장중
    EVENING = _dt(2026, 10, 1, 18, 0)

    def test_an_empty_day_shows_only_the_basis(self):
        html = sortie_panel({"date": "20260923", "breadth": 41.0, "picks": [],
                             "b_group": [{"name": "가", "code": "000001",
                                          "코멘트": "정배열 추세까지 1개 모자람: 시장 폭 41%"}]}, None, None, None, now=self.EVENING)
        self.assertIn("2026-09-23", html)
        self.assertNotIn("가</b>", html, "출격 대기 목록은 이 판에 싣지 않기로 했습니다")
        self.assertIn("새로 사지 않습니다", html)

    def test_listed_stocks_are_named(self):
        html = sortie_panel({"date": "20260923", "breadth": 60.0,
                             "picks": [{"name": "나<b>", "code": "000002", "갈래": ["추세 규칙"]}]}, None, None, None)
        self.assertIn("000002", html)
        self.assertIn("4칸", html)
        self.assertNotIn("나<b>", html, "이름을 그대로 넣으면 화면이 깨집니다")

    def test_missing_result_is_explained(self):
        self.assertIn("아직 없습니다", sortie_panel(None, None, None, None))

    def test_the_newest_result_wins(self):
        daily = {"date": "20260930", "breadth": 40.0, "picks": [{"name": "다", "code": "000003", "갈래": ["정배열 추세"]}]}
        old_plan = {"base": "20260929", "breadth": 45.0, "candidates": [{"name": "옛", "code": "000009"}]}
        html = sortie_panel(daily, old_plan, None, None, now=self.MORNING)
        self.assertIn("2026-09-30", html)
        self.assertIn("000003", html)
        self.assertNotIn("000009", html, "옛 저녁 계산이 새 일봉 결과를 가리면 안 됩니다")
        self.assertIn("<b>오늘</b>", html, "어제 마감 결과는 오늘 장중 후보입니다")
        new_plan = {"base": "20260930", "breadth": 40.0, "made": "2026-10-01 03:00",
                    "candidates": [{"name": "라", "code": "000004", "3일연속": True}]}
        html = sortie_panel(daily, new_plan, None, None, now=self.EVENING)
        self.assertIn("000004", html)
        self.assertIn("다음 거래일", html)

    def test_the_score_follows_the_final_conditions(self):
        self.assertEqual(stock_score({"group": "A", "comment": "정배열 추세 조건을 모두 채움"})[0], 100)
        self.assertEqual(stock_score({"group": "B", "shortfall": 1, "comment": "x"})[0], 80)
        self.assertEqual(stock_score({"group": "밖", "shortfall": 3, "comment": "x"})[0], 40)
        self.assertEqual(stock_score({"group": None, "note": "셀 수 없음"}), (0, [], "셀 수 없음"))

    def test_the_board_has_no_c_and_leaves_out_the_rest(self):
        buckets, pending = group_buckets([{"code": "1", "group": "A"}, {"code": "2", "group": "B"},
                                          {"code": "3", "group": "밖"}, {"code": "4", "group": None}])
        self.assertEqual(set(buckets), {"A", "B"})
        self.assertEqual([r["code"] for r in pending], ["4"])
        self.assertEqual([r["code"] for r in buckets["B"]], [], "조건 1~2개 미달(옛 출격 대기)은 싣지 않음")

    def test_two_rules_fill_the_two_columns(self):
        graded = [{"code": "1", "group": "A", "name": "가"}, {"code": "2", "group": "B", "name": "나"},
                  {"code": "3", "group": "밖", "name": "다"}]
        buckets, _ = group_buckets(graded, hourly={"3": "다 · 정시 출격 보유 중"}, daily={"1": "가 · 종가 출격 후보", "2": "나 · 종가 출격 보유 중"})
        self.assertEqual(sorted(r["code"] for r in buckets["A"]), ["1", "3"])
        self.assertEqual(sorted(r["code"] for r in buckets["B"]), ["1", "2"])
        self.assertTrue(all("종가 출격" in r["comment"] for r in buckets["B"]))


@unittest.skipIf(close_panel is None, "streamlit이 없어 화면 쪽은 건너뜁니다")
class DailyPanels(unittest.TestCase):
    def test_close_panel(self):
        self.assertIn("아직 없습니다", close_panel(None, None, None))
        html = close_panel({"date": "20261001", "breadth": 55.0, "made": "2026-10-01 15:33", "candidates": [{"code": "1"}],
                            "buys": [{"code": "000001", "name": "가<b>", "칸": 4, "why": "① 추세 출격"}], "sells": []},
                           {"positions": {"000001": {"code": "000001", "name": "가", "kind": "추세", "칸": 4, "price": 100.0,
                                                      "last_close": 103.0, "bought": "20261001"}}}, [])
        self.assertIn("2026-10-01", html)
        self.assertIn("+3.0%", html)
        self.assertNotIn("가<b>", html)

    def test_ledger_panel(self):
        self.assertIn("아직 끝난 매매가 없습니다", ledger_panel("종가 출격 모의투자", None, None))
        html = ledger_panel("x", {"closed": [{"판 날": "20261002", "name": "가", "code": "000001", "칸": 4, "손익": 5.0, "까닭": "익절"},
                                             {"판 날": "20261003", "name": "나", "code": "000002", "칸": 2, "손익": -5.0, "까닭": "손절"}]},
                            {"orders": [{"at": "2026-10-02 15:21", "side": "sell", "name": "가", "code": "000001", "qty": 10, "status": "접수"}]})
        self.assertIn("끝난 매매 2건", html)
        self.assertIn("+1.0%", html)          # 5 × 4/10 − 5 × 2/10
        self.assertIn("10주", html)


if __name__ == "__main__":
    unittest.main()
