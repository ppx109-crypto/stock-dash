import unittest
from unittest import mock

import broker_kis


class IndexNowTest(unittest.TestCase):
    def client(self, out):
        c = broker_kis.KIS.__new__(broker_kis.KIS)
        c.token, c.key, c.secret = "t", "k", "s"
        c.authorize = lambda: None
        c.request = lambda *a, **k: (200, {"rt_cd": "0", "output": out})
        return c

    def test_down_sign(self):
        got = self.client({"bstp_nmix_prpr": "2,650.12", "bstp_nmix_prdy_vrss": "13.90", "bstp_nmix_prdy_ctrt": "0.53",
                           "prdy_vrss_sign": "5"}).index_now("0001")
        self.assertEqual(got, {"value": 2650.12, "diff": -13.9, "rate": -0.53})

    def test_up_and_negative_rate_text(self):
        got = self.client({"bstp_nmix_prpr": "812.5", "bstp_nmix_prdy_vrss": "4.1", "bstp_nmix_prdy_ctrt": "0.51",
                           "prdy_vrss_sign": "2"}).index_now("1001")
        self.assertEqual(got["diff"], 4.1)
        got = self.client({"bstp_nmix_prpr": "812.5", "bstp_nmix_prdy_vrss": "-4.1", "bstp_nmix_prdy_ctrt": "-0.51",
                           "prdy_vrss_sign": "5"}).index_now("1001")
        self.assertEqual((got["diff"], got["rate"]), (-4.1, -0.51))

    def test_bad(self):
        with self.assertRaises(broker_kis.BrokerError):
            self.client({}).index_now("0001")
        with self.assertRaises(broker_kis.BrokerError):
            self.client({"bstp_nmix_prpr": "1"}).index_now("01")


if __name__ == "__main__":
    unittest.main()
