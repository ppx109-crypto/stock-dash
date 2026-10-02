import json
import tempfile
import unittest
from pathlib import Path

import reconcile as R


class Bars(unittest.TestCase):
    rows = [("202610020900", 10, 12, 9, 11, 100), ("202610020915", 11, 13, 10, 12, 50),
            ("202610021500", 20, 21, 19, 20, 10), ("202610021515", 20, 22, 18, 21, 30)]

    def test_hours_merge_15_into_14_like_live(self):
        h = R.to_hours(self.rows, "20261002")
        self.assertEqual([x[0] for x in h], ["2026100209", "2026100214"])
        self.assertEqual(h[0][1:], (10, 13, 9, 12, 150))
        self.assertEqual(h[1][1:], (20, 22, 18, 21, 40), "15시 칸은 14시 봉 · 종가는 마감")

    def test_day_bar(self):
        self.assertEqual(R.to_day(self.rows), (10, 22, 9, 21, 190))
        self.assertIsNone(R.to_day([]))

    def test_m15_day_reads_only_that_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "000001").mkdir()
            (Path(tmp) / "000001" / "2026.csv").write_text(
                "202610010900,1,1,1,1,1\n202610020900,2,3,1,2,5\n", encoding="utf-8")
            self.assertEqual(R.m15_day("000001", "20261002", home=tmp), [("202610020900", 2.0, 3.0, 1.0, 2.0, 5.0)])
            self.assertEqual(R.m15_day("000002", "20261002", home=tmp), [])


class Compare(unittest.TestCase):
    def test_same_and_different_trades(self):
        back = {"closed": [{"code": "A", "산 날": "20261002", "판 날": "20261005", "칸": 4, "손익": 5.0},
                           {"code": "B", "산 날": "20261002", "판 날": "20261006", "칸": 2, "손익": -3.0}],
                "positions": {"C": {"bought": "20261006", "칸": 2, "price": 10.0}}}
        live = {"closed": [{"code": "A", "산 날": "20261002", "판 날": "20261005", "칸": 4, "손익": 4.5}],
                "positions": {"C": {"bought": "20261006", "칸": 2, "price": 10.1}, "D": {"bought": "20261006", "칸": 2, "price": 5.0}}}
        got = R.compare(back, live, "산 날", "판 날")
        self.assertEqual(got["같은 매매"], 1)
        self.assertEqual(got["백테스트에만"], [("B", "20261002")])
        self.assertEqual(got["같은 매매 손익 차이"], [("A", "20261002", 5.0, 4.5)])
        self.assertEqual(got["계좌 몫 합(백테스트 · 운영 · %)"], (1.4, 1.8))
        self.assertEqual(got["들고 있는 종목(운영)"], ["C", "D"])


if __name__ == "__main__":
    unittest.main()
