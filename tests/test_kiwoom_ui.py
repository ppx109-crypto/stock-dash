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
        self.assertIn("pull/275", out)
        self.assertIn("개발 순서", out)
        self.assertIn("아직 없음", out)            # 인정한 결과가 없으면 빈칸이라고 적음

    def test_results_table_and_escape(self):
        out = K.lab_html({"results": [{"bot": "추세<b>", "rule": "mid", "total": -3.25, "per_day": 0.5, "worst_day": -12.0, "test": "통과"}]})
        self.assertIn("추세&lt;b&gt;", out)
        self.assertIn("−3.2p", out)
        self.assertIn("+0.5p", out)
        self.assertNotIn("아직 없음", out)
        self.assertIn("pxb", K.lab_html(None))

    def test_trio_board(self):
        """세 버전 카드 · 독립 창 셈(10-15부터) · 참고 날은 셈에서 뺌 · 20일 전에는 판정 표시 안 함."""
        t = json.loads((ROOT / K.TRIO).read_text(encoding="utf-8"))
        out = K.trio_html(t)
        for name in ("신뢰형", "균형형", "v12a 4봇"):
            self.assertIn(name, out)
        self.assertIn("참고", out)
        st = K.trio_stats({"20261014": 9.0, "20261015": 5.0, "20261016": -8.0, "20261019": 2.0}, "20261015")
        self.assertEqual((st["n"], st["sum"], st["worst"], st["mdd"]), (3, -1.0, -8.0, -8.0))
        t2 = {**t, "days": {"신뢰형": {f"202611{d:02d}": 1.0 for d in range(1, 21)}}}
        self.assertIn("✅", K.trio_html(t2))
        self.assertEqual(K.trio_html({}), "")
        self.assertEqual(K.trio_stats({"20261015": -5.0, "20261016": 2.0}, "20261015", {"20261015"})["n"], 1)   # 불완전한 날은 뺌

    def test_menu_order(self):
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('NAV_ITEMS = ["오늘의 투자판단", "키움 개발실", "PreDash 교실", "설정"]', src)


if __name__ == "__main__":
    unittest.main()
