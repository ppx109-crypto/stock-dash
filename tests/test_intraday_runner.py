"""intraday_runner — 시각표 · 늦게 시작했을 때 따라잡기 · 창 나누기 · 창 끝 멈춤 · 합치기 실패 시 건너뜀."""
import unittest
from datetime import datetime, timedelta
from unittest import mock

import intraday_runner as R


class Plan(unittest.TestCase):
    def test_slots(self):
        jobs = R.plan("0000", "2400")
        self.assertEqual(len([j for j in jobs if j[1] == "m15"]), 28)
        self.assertEqual([t for t, b in jobs if b == "hourly"], R.HOURLY)
        self.assertEqual(jobs[:3], [("0903", "m15"), ("0903", "hourly"), ("0918", "m15")], "같은 회차면 주문하는 15분봉 먼저")

    def test_windows_split_without_gap_or_overlap(self):
        am, pm = R.plan("0855", "1200"), R.plan("1200", "1600")
        self.assertEqual(sorted(am + pm), sorted(R.plan("0000", "2400")))
        self.assertEqual(am[-1], ("1148", "m15"))
        self.assertEqual(pm[0], ("1203", "m15"))
        self.assertEqual(pm[-1], ("1548", "m15"))

    def test_late_start_catches_up_once_per_bot(self):
        catch_up, later = R.due(R.plan("0855", "1200"), "0950")
        self.assertEqual(catch_up, [("0903", "hourly"), ("0948", "m15")])
        self.assertEqual(later[0], ("1003", "m15"))

    def test_on_time_start_nothing_to_catch(self):
        catch_up, later = R.due(R.plan("0855", "1200"), "0820")
        self.assertEqual(catch_up, [])
        self.assertEqual(len(later), 3 * 4 + 3)


class Main(unittest.TestCase):
    def clock_at(self, h, m):
        t = [datetime(2026, 10, 7, h, m, tzinfo=R.KST)]

        def clock():
            return t[0]

        def sleep(s):
            t[0] = t[0] + timedelta(seconds=s)
        return t, clock, sleep

    def test_runs_in_order_and_waits(self):
        t, clock, sleep = self.clock_at(11, 40)
        ran = []
        with mock.patch.object(R, "run_bot", side_effect=lambda b: ran.append((clock().strftime("%H%M"), b)) or True):
            self.assertEqual(R.main("0855", "1200", clock=clock, sleep=sleep), 0)
        self.assertEqual(ran, [("1140", "hourly"), ("1140", "m15"), ("1148", "m15")])

    def test_stops_at_window_end_even_if_running_late(self):
        t, clock, sleep = self.clock_at(11, 47)
        ran = []

        def slow(bot):                    # 한 번에 14분 걸리는 날 → 창 끝(12:00)을 넘기면 멈춤
            ran.append((clock().strftime("%H%M"), bot))
            t[0] = t[0] + timedelta(minutes=14)
            return True
        with mock.patch.object(R, "run_bot", side_effect=slow):
            R.main("0855", "1200", clock=clock, sleep=sleep)
        self.assertEqual(ran, [("1147", "hourly")], "12:01에 이미 창이 끝나 다음 회차를 오후 작업에 넘김")

    def test_after_window_exits(self):
        with mock.patch.object(R, "run_bot") as rb:
            R.main("0855", "1200", clock=lambda: datetime(2026, 10, 7, 12, 5, tzinfo=R.KST), sleep=lambda s: None)
            rb.assert_not_called()

    def test_one_slot_crash_does_not_stop_the_day(self):
        t, clock, sleep = self.clock_at(11, 40)
        calls = []

        def boom(bot):
            calls.append(bot)
            if len(calls) == 1:
                raise RuntimeError("x")
            return True
        with mock.patch.object(R, "run_bot", side_effect=boom):
            self.assertEqual(R.main("0855", "1200", clock=clock, sleep=sleep), 1)
        self.assertEqual(len(calls), 3)


class Sync(unittest.TestCase):
    def test_failed_pull_skips_the_slot(self):
        with mock.patch.object(R, "sync", return_value=False), mock.patch.object(R.subprocess, "run") as run, \
                mock.patch.object(R, "push") as push:
            self.assertFalse(R.run_bot("m15"))
            run.assert_not_called()
            push.assert_not_called()

    def test_sync_aborts_rebase_and_retries(self):
        codes = iter([1, 0])
        with mock.patch.object(R, "_sh", side_effect=lambda c, timeout=300: next(codes)), \
                mock.patch.object(R, "_undo_rebase") as undo, mock.patch.object(R.time, "sleep"):
            self.assertTrue(R.sync())
            undo.assert_called_once()


if __name__ == "__main__":
    unittest.main()
