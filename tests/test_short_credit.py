"""공매도·신용잔고 모으기: 거슬러 가다 처음에 닿으면 멈추고, 다시 돌리면 새 날만 붙입니다."""
import tempfile
import unittest
from datetime import date
from pathlib import Path

import collect_short_credit as C
from tests.test_investor_history import trading_days


class Fake:
    def __init__(self, days):
        self.days = days

    def short_daily(self, code, start, end):
        return [{"date": d, "공매도량": 1.0, "공매도비중": 0.5, "거래량": 100.0, "종가": 10.0}
                for d in self.days if start <= d <= end]

    def credit_daily(self, code, day):
        upto = [d for d in self.days if d <= day] or self.days[:30]
        return [{"date": d, "잔고율": 0.3, "잔고주수": 5.0, "공여율": 1.0, "신규주수": 1.0, "상환주수": 1.0}
                for d in upto[-30:]]


class Fill(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = dict(C.KINDS)
        for kind, (_, cols) in self.old.items():
            C.KINDS[kind] = (Path(self.tmp.name) / kind, cols)
        C.START = "20170101"

    def tearDown(self):
        C.KINDS.update(self.old)
        self.tmp.cleanup()

    def test_short_walks_back_to_listing(self):
        days = trading_days(date(2019, 3, 4), date(2020, 6, 30))
        C.fill_short(Fake(days), "000001", "20200630")
        body = C._load("short", "000001")
        self.assertTrue(body["처음까지"])
        self.assertEqual([r[0] for r in body["rows"]], days)

    def test_credit_walks_back_and_adds_new_days(self):
        days = trading_days(date(2016, 6, 1), date(2017, 9, 29))
        C.fill_credit(Fake([d for d in days if d <= "20170630"]), "000002", "20170630")
        added, asks = C.fill_credit(Fake(days), "000002", "20170929")
        body = C._load("credit", "000002")
        self.assertTrue(body["처음까지"])
        self.assertEqual(body["rows"][0][0], min(d for d in days if d >= "20170101"))
        self.assertEqual(body["rows"][-1][0], "20170929")
        self.assertEqual(added, len([d for d in days if d > "20170630"]))


if __name__ == "__main__":
    unittest.main()
