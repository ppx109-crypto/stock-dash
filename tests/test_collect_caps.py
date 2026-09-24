"""날마다의 시가총액 수집기. 그날의 100등 자름을 만드는 자료입니다.

DART 주식총수는 2016사업연도부터라, 그것으로 만든 순위는 앞이 비어 있습니다
(59회차에 삼성전자가 2017-03-31에야 순위를 받는 것을 확인했습니다). 공공
데이터포털은 날짜별 시가총액을 통째로 주므로 그 구멍이 없습니다.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import collect_caps


def row(code, cap):
    return {"srtnCd": f"A{code}", "mrktTotAmt": str(cap)}


class OneDay(unittest.TestCase):

    def test_the_cuts_are_the_market_wide_places(self):
        board = [row(f"{k:06d}", 1_000_000 - k) for k in range(300)]
        with mock.patch.object(collect_caps, "board", return_value=board):
            got = collect_caps.one_day("key", "20240102", {"000000", "000005"})
        self.assertEqual(got["셈"], 300)
        self.assertEqual(got["자름"]["50"], 1_000_000 - 49)
        self.assertEqual(got["자름"]["100"], 1_000_000 - 99)

    def test_a_short_market_leaves_the_deep_cuts_empty(self):
        with mock.patch.object(collect_caps, "board",
                               return_value=[row("000001", 500)]):
            got = collect_caps.one_day("key", "20240102", {"000001"})
        self.assertEqual(got["자름"]["50"], None)
        self.assertEqual(got["값"], {"000001": 500})

    def test_only_our_codes_are_written_down(self):
        board = [row("000001", 900), row("000002", 800), row("000003", 700)]
        with mock.patch.object(collect_caps, "board", return_value=board):
            got = collect_caps.one_day("key", "20240102", {"000002"})
        self.assertEqual(got["값"], {"000002": 800})

    def test_a_holiday_gives_nothing_rather_than_an_empty_ranking(self):
        with mock.patch.object(collect_caps, "board", return_value=[]):
            self.assertIsNone(collect_caps.one_day("key", "20240101", {"000001"}))

    def test_junk_rows_are_stepped_over(self):
        board = [row("000001", 900), {"srtnCd": "A000002", "mrktTotAmt": "-"},
                 {"srtnCd": "없음", "mrktTotAmt": "5"}]
        with mock.patch.object(collect_caps, "board", return_value=board):
            got = collect_caps.one_day("key", "20240102", {"000001", "000002"})
        self.assertEqual(got["값"], {"000001": 900})


class Resuming(unittest.TestCase):
    """서른 해치를 한 번에 못 받습니다. 이미 받은 날은 건너뛰어야 합니다."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.spot = mock.patch.object(collect_caps, "OUT", self.folder)
        self.spot.start()

    def tearDown(self):
        self.spot.stop()
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_what_was_saved_comes_back(self):
        collect_caps.save("2015", {"20150102": {"셈": 3, "자름": {}, "값": {}}})
        self.assertIn("20150102", collect_caps.kept("2015"))

    def test_a_year_never_touched_is_empty_not_an_error(self):
        self.assertEqual(collect_caps.kept("1999"), {})

    def test_a_broken_file_is_treated_as_empty(self):
        (self.folder / "2016.json").write_text("{못 읽는 것", encoding="utf-8")
        self.assertEqual(collect_caps.kept("2016"), {})
