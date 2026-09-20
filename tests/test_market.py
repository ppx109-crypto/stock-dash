"""여러 종목의 시세를 겹쳐 받아도 결과가 달라지지 않아야 합니다."""
import os
import threading
import time
import unittest

import market
from providers import DataError


class GradeAllFetching(unittest.TestCase):
    def setUp(self):
        self.real = market.daily_closes
        self.calls = []
        self.lock = threading.Lock()
        os.environ["DATA_GO_KR_SERVICE_KEY"] = "test-key"

        def fake(code, key, span_days=260):
            with self.lock:
                self.calls.append(code)
            time.sleep(0.02)
            if code == "000003":
                raise DataError("이 종목은 자료가 없습니다")
            return [(f"2026090{i % 9 + 1}", 100.0 + i) for i in range(70)]

        market.daily_closes = fake

    def tearDown(self):
        market.daily_closes = self.real
        os.environ.pop("DATA_GO_KR_SERVICE_KEY", None)

    def test_rows_come_back_in_the_order_asked_for(self):
        codes = [str(i).zfill(6) for i in range(1, 13)]
        rows = market.grade_all(codes, {})
        self.assertEqual([r["code"] for r in rows], codes)

    def test_each_stock_is_asked_for_exactly_once(self):
        codes = [str(i).zfill(6) for i in range(1, 13)]
        market.grade_all(codes, {})
        self.assertEqual(sorted(self.calls), sorted(codes))

    def test_one_stock_failing_leaves_the_others_alone(self):
        rows = market.grade_all(["000001", "000003", "000004"], {})
        failed = next(r for r in rows if r["code"] == "000003")
        self.assertIn("자료가 없습니다", failed["note"])
        self.assertEqual(failed["closes"], [])
        self.assertTrue(all(r["closes"] for r in rows if r["code"] != "000003"))

    def test_no_key_means_no_calls_and_a_stated_reason(self):
        os.environ.pop("DATA_GO_KR_SERVICE_KEY", None)
        rows = market.grade_all(["000001"], {})
        self.assertEqual(self.calls, [])
        self.assertIn("인증키", rows[0]["note"])


if __name__ == "__main__":
    unittest.main()
