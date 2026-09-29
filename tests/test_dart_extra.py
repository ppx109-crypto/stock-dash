import unittest

import collect_dart_extra as C


class Compact(unittest.TestCase):
    def test_prefers_consolidated(self):
        rows = [{"fs_div": "OFS", "account_nm": "매출액", "thstrm_amount": "1", "rcept_no": "r"},
                {"fs_div": "CFS", "account_nm": "매출액", "thstrm_amount": "10", "frmtrm_amount": "8", "rcept_no": "20170515000"},
                {"fs_div": "CFS", "account_nm": "영업이익", "thstrm_amount": "3", "rcept_no": "20170515000"}]
        got = C.compact(rows)
        self.assertEqual((got["기준"], got["매출"], got["매출_작년"], got["영업이익"]), ("CFS", "10", "8", "3"))

    def test_separate_when_no_consolidated(self):
        got = C.compact([{"fs_div": "OFS", "account_nm": "당기순이익(손실)", "thstrm_amount": "5", "rcept_no": "x"}])
        self.assertEqual((got["기준"], got["순이익"]), ("OFS", "5"))

    def test_empty(self):
        self.assertIsNone(C.compact([]))


if __name__ == "__main__":
    unittest.main()
