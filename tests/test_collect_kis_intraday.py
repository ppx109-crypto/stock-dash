import unittest

import collect_kis_intraday as C


class Parse(unittest.TestCase):
    def test_estimate_sorted_and_numbers(self):
        rows = [{"bsop_hour_gb": "2", "frgn_fake_ntby_qty": "1,200", "orgn_fake_ntby_qty": "-5", "sum_fake_ntby_qty": "1195"},
                {"bsop_hour_gb": "1", "frgn_fake_ntby_qty": "10", "orgn_fake_ntby_qty": "0", "sum_fake_ntby_qty": "10"},
                {"bsop_hour_gb": "", "frgn_fake_ntby_qty": "9"}]
        self.assertEqual(C.parse_estimate(rows), [[1, 10.0, 0.0, 10.0], [2, 1200.0, -5.0, 1195.0]])

    def test_program_rows(self):
        rows = [{"bsop_hour": "153000", "arbt_smtn_ntby_tr_pbmn": "1", "nabt_smtn_ntby_tr_pbmn": "2",
                 "whol_smtn_ntby_tr_pbmn": "3", "bstp_nmix_prpr": "2500.5"}, {"bsop_hour": "bad"}]
        self.assertEqual(C.parse_program(rows), [["153000", 1.0, 2.0, 3.0, 2500.5]])

    def test_earlier(self):
        self.assertEqual(C.earlier("151700"), "151600")
        self.assertEqual(C.earlier("100000"), "095900")


if __name__ == "__main__":
    unittest.main()
