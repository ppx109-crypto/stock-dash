import unittest

import collect_kis_hourly as K


def row(day, t, o, h, l, c, v):
    return {"stck_bsop_date": day, "stck_cntg_hour": t, "stck_oprc": str(o), "stck_hgpr": str(h),
            "stck_lwpr": str(l), "stck_prpr": str(c), "cntg_vol": str(v)}


class Bucket(unittest.TestCase):
    def test_minute_end_to_start_hour(self):
        self.assertEqual(K.bucket("090100"), 9)
        self.assertEqual(K.bucket("100000"), 9)
        self.assertEqual(K.bucket("100100"), 10)
        self.assertEqual(K.bucket("153000"), 15)


class ToHours(unittest.TestCase):
    def test_aggregate_and_skip_other_day(self):
        rows = [row("20260925", "090100", 100, 101, 99, 100, 10), row("20260925", "100000", 100, 105, 98, 104, 5),
                row("20260925", "100100", 104, 104, 103, 103, 7), row("20260924", "153000", 90, 90, 90, 90, 1),
                row("20260925", "153000", 110, 110, 110, 110, 50)]
        got = K.to_hours(rows, "20260925")
        self.assertEqual(got[0], ("2026092509", 100.0, 105.0, 98.0, 104.0, 15))
        self.assertEqual(got[1], ("2026092510", 104.0, 104.0, 103.0, 103.0, 7))
        self.assertEqual(got[-1], ("2026092515", 110.0, 110.0, 110.0, 110.0, 50))
        self.assertEqual(len(got), 3)


if __name__ == "__main__":
    unittest.main()
