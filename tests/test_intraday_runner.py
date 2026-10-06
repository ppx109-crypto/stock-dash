"""intraday_runner — 시각표 · 늦게 시작했을 때 따라잡기 · 창 나누기."""
import unittest
from datetime import datetime
from unittest import mock

import intraday_runner as R


class Plan(unittest.TestCase):
    def test_slots(self):
        jobs = R.plan("0000", "2400")
        self.assertEqual(len([j for j in jobs if j[1] == "m15"]), 28)
        self.assertEqual([t for t, b in jobs if b == "hourly"], R.HOURLY)
        self.assertEqual(jobs[0], ("0901", "hourly"))
        self.assertEqual(jobs[1], ("0903", "m15"))

    def test_windows_split_without_gap_or_overlap(self):
        am, pm = R.plan("0855", "1300"), R.plan("1300", "1600")
        self.assertEqual(sorted(am + pm), R.plan("0000", "2400"))
        self.assertEqual(am[-1], ("1248", "m15"))
        self.assertEqual(pm[0], ("1301", "hourly"))
        self.assertEqual(pm[-1], ("1548", "m15"))

    def test_late_start_catches_up_once_per_bot(self):
        catch_up, later = R.due(R.plan("0855", "1300"), "0950")
        self.assertEqual(catch_up, [("0901", "hourly"), ("0948", "m15")])
        self.assertEqual(later[0], ("1001", "hourly"))

    def test_on_time_start_nothing_to_catch(self):
        catch_up, later = R.due(R.plan("0855", "1300"), "0820")
        self.assertEqual(catch_up, [])
        self.assertEqual(len(later), 4 * 4 + 4)


class Main(unittest.TestCase):
    def test_runs_in_order_and_waits(self):
        t = [datetime(2026, 10, 7, 12, 40, tzinfo=R.KST)]
        waited, ran = [], []

        def clock():
            return t[0]

        def sleep(s):
            waited.append(s)
            t[0] = t[0].replace(minute=t[0].minute + int(s // 60), second=0) if s < 3600 else t[0]

        with mock.patch.object(R, "run_bot", side_effect=lambda b: ran.append((clock().strftime("%H%M"), b)) or True):
            self.assertEqual(R.main("0855", "1300", clock=clock, sleep=sleep), 0)
        self.assertEqual(ran, [("1240", "hourly"), ("1240", "m15"), ("1248", "m15")])  # 12:01 · 12:33 따라잡기 → 12:48 기다려 돌림
        self.assertEqual(waited, [480.0])

    def test_after_window_exits(self):
        with mock.patch.object(R, "run_bot") as rb:
            R.main("0855", "1300", clock=lambda: datetime(2026, 10, 7, 13, 5, tzinfo=R.KST), sleep=lambda s: None)
            rb.assert_not_called()


if __name__ == "__main__":
    unittest.main()
