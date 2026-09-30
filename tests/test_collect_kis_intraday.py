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

    def test_program_pages_by_continuation(self):
        def row(t):
            return {"bsop_hour": t, "arbt_smtn_ntby_tr_pbmn": "1", "nabt_smtn_ntby_tr_pbmn": "1",
                    "whol_smtn_ntby_tr_pbmn": "2", "bstp_nmix_prpr": "1"}

        class Fake:
            def __init__(self):
                self.asked = []

            def _market_page(self, path, tr_id, params, what, key=None, continuation=""):
                self.asked.append(continuation)
                pages = [(["153000", "152900"], True), (["152800", "090000"], True), (["085900"], False)]
                times, more = pages[len(self.asked) - 1]
                return [row(t) for t in times], more

        fake = Fake()
        C.GAP = 0
        got = C.program_day(fake, "K")
        self.assertEqual(fake.asked, ["", "N"])
        self.assertEqual([r[0] for r in got], ["090000", "152800", "152900", "153000"])

    def test_program_stops_on_repeat(self):
        class Same:
            calls = 0

            def _market_page(self, *a, **k):
                Same.calls += 1
                return [{"bsop_hour": "153000", "whol_smtn_ntby_tr_pbmn": "1"}], True

        C.GAP = 0
        self.assertEqual(len(C.program_day(Same(), "K")), 1)
        self.assertEqual(Same.calls, 2)


if __name__ == "__main__":
    unittest.main()
