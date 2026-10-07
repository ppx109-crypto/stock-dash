import gzip
import os
import tempfile
import unittest
from pathlib import Path

import collect_krx_daily as K


class RowTest(unittest.TestCase):
    def test_short_code_and_numbers(self):
        r = K.row_of("20170102", "KOSPI", {"ISU_CD": "5930", "ISU_NM": "삼성전자", "TDD_CLSPRC": "1,805,000",
                                            "ACC_TRDVOL": "93,012", "ACC_TRDVAL": "1", "MKTCAP": "2", "LIST_SHRS": "3"})
        self.assertEqual(r[2], "005930")
        self.assertEqual(r[4], 1805000.0)

    def test_standard_code(self):
        r = K.row_of("20170102", "KOSDAQ", {"ISU_CD": "KR7035720002", "TDD_CLSPRC": "x"})
        self.assertEqual(r[2], "035720")
        self.assertIsNone(r[4])

    def test_save_and_load_year(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                K.save_year(2017, [["20170103", "KOSPI", "000020", "a", 1, 2, 3, 4, 5], ["20170102", "KOSPI", "000010", "b", 1, 2, 3, 4, 5]])
                rows = K.load_year(2017)
                self.assertEqual([r[0] for r in rows], ["20170102", "20170103"])
                self.assertTrue(Path("krx-data/2017.csv.gz").exists())
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
