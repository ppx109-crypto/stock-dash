import tempfile
import unittest
from datetime import date
from pathlib import Path

import collect_fut_1min as C


class FrontCode(unittest.TestCase):
    def test_roll_on_expiry_day(self):
        # 사용자 키움 파일이 바뀐 날: 08-13 · 09-10 · 10-08(둘째 목요일 당일부터 다음 월물)
        self.assertEqual(C.front_code("A05", date(2026, 8, 12), False), "A0568000")
        self.assertEqual(C.front_code("A05", date(2026, 8, 13), False), "A0569000")
        self.assertEqual(C.front_code("A05", date(2026, 9, 10), False), "A056A000")
        self.assertEqual(C.front_code("A05", date(2026, 10, 7), False), "A056A000")
        self.assertEqual(C.front_code("A05", date(2026, 10, 8), False), "A056B000")

    def test_quarterly(self):
        self.assertEqual(C.front_code("A01", date(2026, 9, 9), True), "A0169000")
        self.assertEqual(C.front_code("A01", date(2026, 9, 10), True), "A016C000")
        self.assertEqual(C.front_code("A06", date(2026, 12, 10), True), "A0673000")

    def test_kis_code_from_standard_code(self):
        rows = [["B", "A05611", "KR4A056B0006", "미니F 202611"], ["3", "A06612", "KR4A066C0003", "코스닥150F 202612"]]
        self.assertEqual(C.kis_code(rows, "A056B000"), "A05611")
        self.assertEqual(C.kis_code(rows, "A066C000"), "A06612")
        self.assertIsNone(C.kis_code(rows, "A016C000"))


class Append(unittest.TestCase):
    def test_same_day_replaced_not_doubled(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            a = [["2026-10-12 08:45:00", "A056B000", "1", "2", "0.5", "1.5", "3"]]
            b = [["2026-10-13 08:45:00", "A056B000", "1", "2", "0.5", "1.5", "3"],
                 ["2026-10-13 08:46:00", "A056B000", "1", "2", "0.5", "1.5", "4"]]
            C.append(p, a)
            C.append(p, b[:1])
            self.assertEqual(C.append(p, b), 3)
            self.assertTrue(p.read_text(encoding="utf-8-sig").startswith("datetime,code,open,high,low,close,volume\n"))


if __name__ == "__main__":
    unittest.main()
