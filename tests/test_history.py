"""일봉 이어붙이기. 실제 서버 대신 정해 둔 응답으로 확인합니다."""
import os
import unittest
from datetime import date, timedelta

from broker_kis import KIS, BrokerError


def day(ago):
    return (date.today() - timedelta(days=ago)).strftime("%Y%m%d")


class Fake(KIS):
    """요청한 구간에 걸치는 날짜만 돌려주는 껍데기."""

    def __init__(self, days, status="0"):
        os.environ.update({"KIS_APP_KEY": "k", "KIS_APP_SECRET": "s", "KIS_ENV": "real"})
        super().__init__(account=False)
        self.days = days
        self.status = status
        self.calls = 0

    def authorize(self):
        self.token = "t"

    def request(self, method, path, **kwargs):
        self.calls += 1
        begin = kwargs["params"]["FID_INPUT_DATE_1"]
        end = kwargs["params"]["FID_INPUT_DATE_2"]
        rows = [{"stck_bsop_date": d, "stck_clpr": str(1000 + i)}
                for i, d in enumerate(self.days) if begin <= d <= end]
        return object(), {"rt_cd": self.status, "output2": rows[-100:]}


class History(unittest.TestCase):
    def tearDown(self):
        for key in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ENV"):
            os.environ.pop(key, None)

    def test_older_days_come_first_and_nothing_repeats(self):
        days = sorted(day(n) for n in range(5, 600, 3))
        found = Fake(days).history("005930", days=900, pause=0)
        self.assertEqual([d for d, _ in found], sorted(set(d for d, _ in found)))
        self.assertGreater(len(found), 150)
        self.assertLess(found[0][0], found[-1][0])

    def test_it_stops_instead_of_looping_when_the_listing_is_short(self):
        client = Fake(sorted(day(n) for n in range(5, 40)))
        found = client.history("005930", days=900, pause=0)
        self.assertEqual(len(found), 35)
        self.assertLess(client.calls, 5)

    def test_a_refusal_is_reported(self):
        with self.assertRaises(BrokerError):
            Fake([day(5)], status="1").daily("005930", day(30), day(1))

    def test_rows_without_a_usable_close_are_dropped(self):
        client = Fake([])
        client.request = lambda *a, **k: (object(), {"rt_cd": "0", "output2": [
            {"stck_bsop_date": "20260921", "stck_clpr": "71200"},
            {"stck_bsop_date": "20260920", "stck_clpr": "0"},
            {"stck_bsop_date": "bad", "stck_clpr": "500"},
            {"stck_bsop_date": "20260919", "stck_clpr": ""}]})
        self.assertEqual(client.daily("005930", "20260901", "20260921"), [("20260921", 71200.0)])

    def test_a_bad_code_is_refused_before_calling(self):
        with self.assertRaises(BrokerError):
            Fake([]).history("12")


if __name__ == "__main__":
    unittest.main()
