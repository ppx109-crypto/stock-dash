import json
import unittest
from pathlib import Path

import kiwoom_ui as K

ROOT = Path(__file__).resolve().parents[1]


class KiwoomLab(unittest.TestCase):
    def test_summary_file_renders(self):
        s = json.loads((ROOT / K.SUMMARY).read_text(encoding="utf-8"))
        out = K.lab_html(s)
        self.assertIn("−12p", out)
        self.assertIn("KMF-0001", out)
        self.assertIn("pull/273", out)
        self.assertIn("아직 없음", out)            # 인정한 결과가 없으면 빈칸이라고 적음

    def test_results_table_and_escape(self):
        out = K.lab_html({"results": [{"bot": "추세<b>", "rule": "mid", "total": -3.25, "per_day": 0.5, "worst_day": -12.0, "test": "통과"}]})
        self.assertIn("추세&lt;b&gt;", out)
        self.assertIn("−3.2p", out)
        self.assertIn("+0.5p", out)
        self.assertNotIn("아직 없음", out)
        self.assertIn("pxb", K.lab_html(None))

    def test_menu_order(self):
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('NAV_ITEMS = ["오늘의 투자판단", "키움 개발실", "PreDash 교실", "설정"]', src)


if __name__ == "__main__":
    unittest.main()
