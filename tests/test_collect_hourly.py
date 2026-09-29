import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import collect_hourly as H


def payload(stamps, closes):
    n = len(stamps)
    return {"chart": {"result": [{"timestamp": stamps, "indicators": {"quote": [
        {"open": closes, "high": closes, "low": closes, "close": closes, "volume": [100] * n}]}}]}}


class Parse(unittest.TestCase):
    def test_kst_hour_and_skip_empty(self):
        # 2026-09-25 00:00 UTC = 09:00 KST, 06:00 UTC = 15:00 KST, 07:00 UTC = 16:00 KST(장 밖)
        base = 1790294400
        got = H.parse(payload([base, base + 6 * 3600, base + 7 * 3600, base + 3600], [100.0, 101.0, 102.0, None]))
        self.assertEqual([g[0] for g in got], ["2026092509", "2026092515"])
        self.assertEqual(H.parse({}), [])


class ClosedOnly(unittest.TestCase):
    bars = [("2026092409", 1, 1, 1, 1, 1), ("2026092514", 1, 1, 1, 1, 1)]

    def test_before_close_drops_today(self):
        now = datetime(2026, 9, 25, 15, 10, tzinfo=H.KST)
        self.assertEqual([b[0] for b in H.closed_only(self.bars, now)], ["2026092409"])

    def test_after_close_keeps_today(self):
        now = datetime(2026, 9, 25, 16, 5, tzinfo=H.KST)
        self.assertEqual(len(H.closed_only(self.bars, now)), 2)


class Merge(unittest.TestCase):
    def test_append_and_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "005930"
            H.merge(folder, [("2025123115", 1, 1, 1, 1, 1), ("2026010209", 2, 2, 2, 2, 2)])
            H.merge(folder, [("2026010209", 3, 3, 3, 3, 3), ("2026010210", 4, 4, 4, 4, 4)])
            lines = (folder / "2026.csv").read_text().splitlines()
            self.assertEqual(lines, ["2026010209,3,3,3,3,3", "2026010210,4,4,4,4,4"])
            self.assertTrue((folder / "2025.csv").exists())
            # 같은 날을 다시 받으면 그날 봉을 통째로 바꿈(낡은 봉이 남지 않음)
            H.merge(folder, [("2026010209", 5, 5, 5, 5, 5)])
            lines = (folder / "2026.csv").read_text().splitlines()
            self.assertEqual(lines, ["2026010209,5,5,5,5,5"])
            self.assertEqual(H.merge(folder, [("2026010209", 5, 5, 5, 5, 5)]), 0)


if __name__ == "__main__":
    unittest.main()
