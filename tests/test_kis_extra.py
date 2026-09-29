import unittest
from datetime import date, timedelta

import collect_kis_extra as C


def days(a, b):
    d, out = date(int(a[:4]), int(a[4:6]), int(a[6:])), []
    e = date(int(b[:4]), int(b[4:6]), int(b[6:]))
    while d <= e:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


ALL = days("20161101", "20170630")


class Cursor(unittest.TestCase):
    def fetch(self, day):
        got = [d for d in ALL if d <= day][-30:]
        return [{"date": d, "v": 1} for d in got]

    def test_backward_to_start(self):
        have = {}
        added, n, done = C.by_cursor(self.fetch, have, "20170630", start="20170101")
        self.assertTrue(done)
        self.assertEqual(min(d for d in have if d >= "20170101"), "20170102")
        self.assertIn("20170630", have)

    def test_forward_fill(self):
        have = {d: {"date": d} for d in ALL if "20170101" <= d <= "20170531"}
        added, n, done = C.by_cursor(self.fetch, have, "20170630", start="20170101")
        self.assertIn("20170630", have)
        self.assertEqual(added, len([d for d in ALL if "20170601" <= d <= "20170630"]) + len(
            [d for d in ALL if d < "20170101" and d >= min(have)]))


class Window(unittest.TestCase):
    def fetch(self, a, b):
        return [{"date": d} for d in ALL if a <= d <= b]

    def test_backward_windows(self):
        have = {}
        added, n, done = C.by_window(self.fetch, have, "20170630", start="20170101", width=30)
        self.assertTrue(done)
        self.assertEqual(sorted(have), [d for d in ALL if "20170101" <= d <= "20170630"])

    def test_forward(self):
        have = {d: {"date": d} for d in ALL if "20170101" <= d <= "20170615"}
        C.by_window(self.fetch, have, "20170630", start="20170101", width=30)
        self.assertIn("20170630", have)


if __name__ == "__main__":
    unittest.main()
