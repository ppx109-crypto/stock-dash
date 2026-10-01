import unittest

import collect_kis_m15 as M


def row(day, t, o, h, l, c, v):
    return {"stck_bsop_date": day, "stck_cntg_hour": t, "stck_oprc": str(o), "stck_hgpr": str(h),
            "stck_lwpr": str(l), "stck_prpr": str(c), "cntg_vol": str(v)}


class Slots(unittest.TestCase):
    def test_minute_end_to_slot_start(self):
        self.assertEqual(M.slot("090100"), 540)
        self.assertEqual(M.slot("091500"), 540)
        self.assertEqual(M.slot("091600"), 555)
        self.assertEqual(M.slot("153000"), 915)       # 마감 동시호가는 15:15 칸에

    def test_aggregate_and_skip_other_day(self):
        rows = [row("20260925", "090100", 100, 101, 99, 100, 10), row("20260925", "091500", 100, 105, 98, 104, 5),
                row("20260925", "091600", 104, 104, 103, 103, 7), row("20260924", "153000", 90, 90, 90, 90, 1),
                row("20260925", "152100", 109, 111, 108, 110, 3), row("20260925", "153000", 110, 110, 110, 110, 50)]
        got = M.to_bars(rows, "20260925")
        self.assertEqual(got[0], ("202609250900", 100.0, 105.0, 98.0, 104.0, 15))
        self.assertEqual(got[1], ("202609250915", 104.0, 104.0, 103.0, 103.0, 7))
        self.assertEqual(got[-1], ("202609251515", 109.0, 111.0, 108.0, 110.0, 53))
        self.assertEqual(len(got), 3)

    def test_main_points_hourly_collector_at_m15(self):
        from unittest import mock
        seen = []
        with mock.patch.object(M.K, "main", side_effect=lambda codes: seen.append((M.K.HOME, M.K.to_hours, codes)) or 0):
            self.assertEqual(M.main(["005930"]), 0)
        self.assertEqual(seen, [(M.HOME, M.to_bars, ["005930"])])
        self.assertNotEqual(M.K.HOME, M.HOME)                 # 끝나면 되돌려 둠
        self.assertIsNot(M.K.to_hours, M.to_bars)


if __name__ == "__main__":
    unittest.main()
