import importlib
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))


class CutLoadsNoFuture(unittest.TestCase):
    """I_CUT이면 itools가 그날 뒤 값을 처음부터 안 읽는지(미래 참조 원천 차단의 바탕)."""

    def tearDown(self):
        os.environ.pop("I_CUT", None)
        sys.modules.pop("itools", None)

    def test_cut_drops_later_days(self):
        os.environ["I_CUT"] = "20200320"
        sys.modules.pop("itools", None)
        import itools
        importlib.reload(itools)
        self.assertTrue(itools.DAYS)
        self.assertLessEqual(itools.DAYS[-1], "20200320")
        self.assertEqual(len(itools.K200), len(itools.DAYS))
        rows = itools.series("market-data/index_KOSPI.json", "종가")
        self.assertEqual(len(rows), len(itools.DAYS))


if __name__ == "__main__":
    unittest.main()
