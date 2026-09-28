"""과거 수급 모으기: 거슬러 올라가다 처음에 닿으면 멈추고, 다시 돌리면 이어 갑니다."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import collect_investor_history as C


def trading_days(first, last):
    d, out = first, []
    while d <= last:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


class Fake:
    """날짜를 주면 그날까지 서른 거래일을 주는 증권사 흉내. 상장일 앞은 가장 이른 서른 날을 줍니다."""

    def __init__(self, days):
        self.days, self.asks = days, 0

    def investor_daily(self, code, day):
        self.asks += 1
        upto = [d for d in self.days if d <= day] or self.days[:30]
        return [{"date": d, "개인": -1.0, "외국인": 1.0, "기관": 0.0, "투신": 2.0, "연기금": None,
                 "사모": 0.0, "종가": 100.0} for d in upto[-30:]]


class Fill(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = C.OUT
        C.OUT = Path(self.tmp.name)

    def tearDown(self):
        C.OUT = self.old
        self.tmp.cleanup()

    def test_walks_back_to_the_start(self):
        days = trading_days(date(2016, 6, 1), date(2017, 6, 30))
        C.START = "20170101"
        fake = Fake(days)
        C.fill(fake, "000001", "20170630")
        body = C.load("000001")
        self.assertTrue(body["처음까지"])
        self.assertEqual(body["rows"][0][0], min(d for d in days if d >= "20170101"))
        self.assertEqual(body["rows"][-1][0], "20170630")
        self.assertEqual(len(body["rows"]), len([d for d in days if d >= "20170101"]))
        self.assertEqual(body["cols"][4], "투신")

    def test_stops_at_listing(self):
        days = trading_days(date(2020, 3, 2), date(2020, 6, 30))
        C.START = "20170101"
        C.fill(Fake(days), "000002", "20200630")
        body = C.load("000002")
        self.assertTrue(body["처음까지"])
        self.assertEqual(body["rows"][0][0], "20200302")

    def test_a_later_run_only_adds_new_days(self):
        days = trading_days(date(2020, 3, 2), date(2020, 9, 30))
        C.START = "20170101"
        C.fill(Fake([d for d in days if d <= "20200630"]), "000003", "20200630")
        fake = Fake(days)
        added, asks = C.fill(fake, "000003", "20200930")
        self.assertEqual(added, len([d for d in days if d > "20200630"]))
        self.assertLessEqual(asks, 3)
        self.assertEqual(C.load("000003")["rows"][-1][0], "20200930")


if __name__ == "__main__":
    unittest.main()
