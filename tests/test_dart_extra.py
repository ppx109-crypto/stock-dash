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


class CashCompact(unittest.TestCase):
    def test_picks_by_id_then_name(self):
        rows = [
            {"sj_div": "CF", "account_id": "ifrs-full_CashFlowsFromUsedInOperatingActivities", "account_nm": "영업활동 현금흐름",
             "thstrm_amount": "100", "frmtrm_amount": "80", "rcept_no": "20240814000001"},
            {"sj_div": "CF", "account_id": "-표준계정코드 미사용-", "account_nm": "유형자산의 취득", "thstrm_amount": "-30", "frmtrm_amount": "-20"},
            {"sj_div": "BS", "account_id": "ifrs-full_Inventories", "account_nm": "재고자산", "thstrm_amount": "50", "frmtrm_amount": "40"},
            {"sj_div": "CIS", "account_id": "dart_OperatingIncomeLoss", "account_nm": "영업이익",
             "thstrm_amount": "12", "thstrm_add_amount": "25", "frmtrm_amount": "10", "frmtrm_add_amount": "20"},
        ]
        got = C.cash_compact(rows, "CFS")
        self.assertEqual((got["기준"], got["접수번호"]), ("CFS", "20240814000001"))
        self.assertEqual((got["영업현금"], got["영업현금_작년"]), ("100", "80"))
        self.assertEqual(got["설비투자"], "-30")
        self.assertEqual((got["재고"], got["재고_작년"]), ("50", "40"))
        self.assertEqual((got["영업이익"], got["영업이익_누적"], got["영업이익_작년누적"]), ("12", "25", "20"))
        self.assertNotIn("매출채권", got)

    def test_empty(self):
        self.assertIsNone(C.cash_compact([], "CFS"))


class CashFlowJob(unittest.TestCase):
    def test_falls_back_to_separate_and_skips_done(self):
        import os
        import tempfile
        asked = []

        class Fake:
            def ask(self, ep, **kw):
                asked.append((kw["bsns_year"], kw["reprt_code"], kw["fs_div"]))
                if kw["fs_div"] == "CFS":
                    return []
                return [{"sj_div": "BS", "account_id": "ifrs-full_Assets", "account_nm": "자산총계", "thstrm_amount": "9", "rcept_no": "r"}]
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                n = C.cashflow(Fake(), "corp", "000001", "20170630")
                first = len(asked)
                C.cashflow(Fake(), "corp", "000001", "20170630")
            finally:
                os.chdir(here)
        self.assertEqual(n, 8)                       # 2016 · 2017 네 보고서씩
        self.assertEqual(first, 16)                  # 연결 없음 → 별도로 한 번 더
        self.assertEqual(len(asked), first)          # 다 받은 것은 다시 묻지 않음


if __name__ == "__main__":
    unittest.main()
