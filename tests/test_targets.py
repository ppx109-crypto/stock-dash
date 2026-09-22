"""증권사 목표가를 날짜와 함께 쓰는 부분. 그날 나온 것만 써야 합니다."""
import json
import tempfile
import unittest
from pathlib import Path

import study
from collect_opinions import merge


class Merging(unittest.TestCase):
    """API는 한 해치만 줍니다. 받을 때마다 합쳐야 기간이 길어집니다."""

    def row(self, day, member, target):
        return {"date": day, "member": member, "target": target}

    def test_old_and_new_are_kept_together(self):
        old = [self.row("20250601", "가증권", 100)]
        fresh = [self.row("20260601", "가증권", 120)]
        found = merge(old, fresh)
        self.assertEqual([r["date"] for r in found], ["20250601", "20260601"])

    def test_the_same_broker_on_the_same_day_counts_once(self):
        found = merge([self.row("20260601", "가증권", 100)],
                      [self.row("20260601", "가증권", 100)])
        self.assertEqual(len(found), 1)

    def test_a_later_reading_of_the_same_day_wins(self):
        found = merge([self.row("20260601", "가증권", 100)],
                      [self.row("20260601", "가증권", 130)])
        self.assertEqual(found[0]["target"], 130)

    def test_rows_without_a_target_or_a_date_are_dropped(self):
        found = merge([], [self.row("20260601", "가증권", 0),
                           self.row("bad", "나증권", 100),
                           self.row("20260602", "다증권", 100)])
        self.assertEqual([r["member"] for r in found], ["다증권"])


class Timeline(unittest.TestCase):
    def folder(self, rows):
        place = Path(tempfile.mkdtemp())
        (place / "005930.json").write_text(
            json.dumps({"code": "005930", "rows": rows}), encoding="utf-8")
        return str(place)

    def test_only_what_was_out_by_then_is_used(self):
        place = self.folder([{"date": "20260301", "member": "가증권", "target": 100},
                             {"date": "20260601", "member": "나증권", "target": 200}])
        found = study.target_timeline("005930", folder=place)
        self.assertEqual(study.known_by(found, "20260401")["목표가"], 100)
        self.assertEqual(study.known_by(found, "20260215"), {})

    def test_several_brokers_give_a_middle_value(self):
        place = self.folder([{"date": "20260301", "member": "가증권", "target": 100},
                             {"date": "20260302", "member": "나증권", "target": 300}])
        found = study.target_timeline("005930", folder=place)
        block = study.known_by(found, "20260401")
        self.assertEqual(block["목표가"], 200)
        self.assertEqual(block["목표가곳수"], 2)

    def test_an_old_target_falls_out_of_the_window(self):
        place = self.folder([{"date": "20250101", "member": "가증권", "target": 100},
                             {"date": "20260601", "member": "나증권", "target": 300}])
        found = study.target_timeline("005930", folder=place)
        self.assertEqual(study.known_by(found, "20260701")["목표가곳수"], 1)

    def test_a_missing_file_is_simply_empty(self):
        self.assertEqual(study.target_timeline("999999", folder=tempfile.mkdtemp()), [])


class Gap(unittest.TestCase):
    def test_the_gap_is_measured_against_that_day_close(self):
        found = study._gap_to_target({"목표가": 120.0, "목표가곳수": 3}, 100.0)
        self.assertAlmostEqual(found["목표가괴리"], 20.0)
        self.assertEqual(found["목표가곳수"], 3)

    def test_no_target_means_no_gap(self):
        self.assertEqual(study._gap_to_target({}, 100.0), {})
        self.assertEqual(study._gap_to_target({"목표가": 120.0}, None), {})


if __name__ == "__main__":
    unittest.main()
