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


class FakeClient:
    """분봉 서버 흉내: 요청 시각부터 뒤로 100줄 · 첫 요청 다음 쪽에서 12:39 ~ 13:07을 한 번 빼먹음(2026-10-15 일)."""
    def __init__(self, drop_once=True):
        self.minutes = [h * 60 + m for h in range(8, 16) for m in range(60) if 8 * 60 + 45 <= h * 60 + m <= 15 * 60 + 34] + [15 * 60 + 45]
        self.drop_once = drop_once

    def _market_rows(self, path, tr, params, what, key=None):
        hour = params["FID_INPUT_HOUR_1"]
        cut = int(hour[:2]) * 60 + int(hour[2:4])
        ms = [m for m in self.minutes if m <= cut][-100:]
        if self.drop_once and any(12 * 60 + 39 <= m <= 13 * 60 + 7 for m in ms) and cut < 15 * 60:
            ms = [m for m in ms if not 12 * 60 + 39 <= m <= 13 * 60 + 7]
            self.drop_once = False
        return [{"stck_bsop_date": params["FID_INPUT_DATE_1"], "stck_cntg_hour": f"{m // 60:02d}{m % 60:02d}00"} for m in reversed(ms)]


class FetchDay(unittest.TestCase):
    def test_hole_refilled(self):
        logs = []
        got = C.fetch_day(FakeClient(), "A05611", date(2026, 10, 15), log=logs.append)
        self.assertEqual(len(got), 411)
        self.assertEqual(C.gaps([r["stck_cntg_hour"] for r in got]), [])
        self.assertTrue(any("빈 곳 1238~1308(29분)" in l for l in logs))

    def test_auction_gap_is_not_a_hole(self):
        self.assertEqual(C.gaps(["153400", "154500"]), [])
        self.assertEqual(C.gaps(["123800", "130800"]), [("123800", "130800", 29)])


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
