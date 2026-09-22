"""이어받기. 도중에 끊긴 뒤 다시 돌릴 때 끝난 종목을 또 받지 않아야 합니다."""
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import collect_daily
import collect_prices


class DartResume(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        patcher = patch.object(collect_daily, "FOLDER", self.folder)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.today = date.today().isoformat()

    def write(self, code, **fields):
        (self.folder / f"{code}.json").write_text(
            json.dumps({"code": code, **fields}), encoding="utf-8")

    def test_a_stock_finished_today_is_skipped(self):
        self.write("005930", since=2015, fetched=self.today)
        self.assertTrue(collect_daily.already_done("005930", 2015, self.today))

    def test_a_shallower_collection_is_done_again(self):
        # 다른 깊이로 받아 둔 파일은 다시 받아야 합니다.
        self.write("005930", since=2023, fetched=self.today)
        self.assertFalse(collect_daily.already_done("005930", 2015, self.today))

    def test_a_file_from_today_without_the_mark_counts_as_done(self):
        # 표시를 남기기 전에 받은 파일입니다. 오늘 같은 깊이로 이미 물었습니다.
        self.write("005930", years=[1] * 11, fetched=self.today)
        self.assertTrue(collect_daily.already_done("005930", 2015, self.today))

    def test_an_unmarked_file_from_another_day_is_done_again(self):
        self.write("005930", years=[1] * 11, fetched="2020-01-01")
        self.assertFalse(collect_daily.already_done("005930", 2015, self.today))

    def test_yesterdays_collection_is_done_again(self):
        self.write("005930", since=2015, fetched="2020-01-01")
        self.assertFalse(collect_daily.already_done("005930", 2015, self.today))

    def test_a_missing_file_is_not_treated_as_done(self):
        self.assertFalse(collect_daily.already_done("999999", 2015, self.today))

    def test_a_broken_file_is_not_treated_as_done(self):
        (self.folder / "005930.json").write_text("망가짐", encoding="utf-8")
        self.assertFalse(collect_daily.already_done("005930", 2015, self.today))


class PriceResume(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        patcher = patch.object(collect_prices, "OUT", self.folder)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, code, closes, fetched):
        (self.folder / f"{code}.json").write_text(
            json.dumps({"code": code, "closes": closes, "fetched": fetched}),
            encoding="utf-8")

    def test_a_full_series_from_today_is_skipped(self):
        self.write("005930", [["20260101", 100.0]] * 200, "2026-09-22")
        self.assertTrue(collect_prices.done_today("005930", "2026-09-22"))

    def test_a_short_series_is_collected_again(self):
        self.write("005930", [["20260101", 100.0]] * 10, "2026-09-22")
        self.assertFalse(collect_prices.done_today("005930", "2026-09-22"))

    def test_an_older_day_is_collected_again(self):
        self.write("005930", [["20260101", 100.0]] * 200, "2026-09-01")
        self.assertFalse(collect_prices.done_today("005930", "2026-09-22"))


if __name__ == "__main__":
    unittest.main()
