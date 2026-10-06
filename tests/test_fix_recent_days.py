"""fix_recent_days — 최근 줄만 확정 값으로 바꾸고, 오래된 날은 건드리지 않는지(2026-10-02 넥스트레이드 종가 사고)."""
import json
import unittest

import fix_recent_days as F


class FixRecentDays(unittest.TestCase):
    def test_price_recent_row_fixed(self):
        body = {"closes": [["20260930", 1.0], ["20261001", 199400.0], ["20261002", 210000.0]]}
        changed, older = F.fix_price(body, {"20261001": {"종가": 199400.0}, "20261002": {"종가": 207000.0}})
        self.assertEqual(changed, [("20261002", 210000.0, 207000.0)])
        self.assertFalse(older)
        self.assertEqual(body["closes"][-1], ["20261002", 207000.0])

    def test_price_older_row_left_for_collector(self):
        body = {"closes": [["20250101", 5.0]] + [[f"2026100{i}", 1.0] for i in range(1, 8)]}
        changed, older = F.fix_price(body, {"20250101": {"종가": 6.0}})
        self.assertEqual(changed, [])
        self.assertTrue(older)
        self.assertEqual(body["closes"][0], ["20250101", 5.0])

    def test_tiny_gap_ignored(self):
        body = {"closes": [["20261002", 100000.0]]}
        self.assertEqual(F.fix_price(body, {"20261002": {"종가": 100001.0}})[0], [])

    def test_kosdaq_all_columns(self):
        kq = {"cols": ["date", "시가", "고가", "저가", "종가", "거래량", "거래대금"],
              "rows": [["20261002", 198000.0, 219500.0, 194300.0, 210000.0, 296279.0, 6.0]]}
        new = {"시가": 198000.0, "고가": 219500.0, "저가": 194300.0, "종가": 207000.0, "거래량": 281000.0, "거래대금": 5.0}
        self.assertEqual(F.fix_kosdaq(kq, {"20261002": new}), [("20261002", 210000.0, 207000.0)])
        self.assertEqual(kq["rows"][0], ["20261002", 198000.0, 219500.0, 194300.0, 207000.0, 281000.0, 5.0])

    def test_flow_close_only(self):
        fl = {"cols": ["date", "개인", "종가"], "rows": [["20261002", 5.0, 210000.0]]}
        self.assertEqual(F.fix_flow(fl, {"20261002": {"종가": 207000.0}}), [("20261002", 210000.0, 207000.0)])
        self.assertEqual(fl["rows"][0], ["20261002", 5.0, 207000.0])

    def test_adjusted_price_code_untouched(self):
        """오래된 날까지 다르면(수정주가) 최근 줄도 고치지 않음 — 앞뒤 기준이 섞이지 않게."""
        rows = [[f"202609{d:02d}", 200.0] for d in range(1, 11)]
        body = {"closes": [list(r) for r in rows]}
        fresh = {d: {"종가": c / 2} for d, c in rows}           # 액면분할: 모든 날이 반으로
        changed, older = F.fix_price(body, fresh)
        self.assertEqual((changed, older), ([], True))
        self.assertEqual(body["closes"], rows)

    def test_volume_recent_rows(self):
        v = {"칸": ["날짜", "거래량", "거래대금", "고가", "저가"], "날": [["20261001", 1.0, 2.0, 3.0, 4.0], ["20261002", 296279.0, 6.0, 219500.0, 194300.0]]}
        got = F.fix_volume(v, {"20261002": {"거래량": 281000.0, "거래대금": 5.0, "고가": 219500.0, "저가": 194300.0}})
        self.assertEqual(got, [("20261002", 296279.0, 281000.0)])
        self.assertEqual(v["날"][1], ["20261002", 281000.0, 5.0, 219500.0, 194300.0])
        self.assertEqual(v["날"][0], ["20261001", 1.0, 2.0, 3.0, 4.0])

    def test_kosdaq_only_adjusted_untouched(self):
        kq = {"cols": ["date", "시가", "고가", "저가", "종가", "거래량", "거래대금"],
              "rows": [[f"202609{d:02d}", 1.0, 1.0, 1.0, 200.0, 1.0, 1.0] for d in range(1, 11)]}
        fresh = {r[0]: {"종가": 100.0} for r in kq["rows"]}
        self.assertEqual(F.fix_kosdaq(kq, fresh), [])
        self.assertEqual(kq["rows"][-1][4], 200.0)

    def test_marks_confirmed_day_only_when_all_asked(self):
        import tempfile
        from datetime import datetime
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(F, "CHECKED", Path(tmp) / "checked.json"):
                F.mark("20261006", datetime(2026, 10, 7, 7, 5))
                F.mark("20261005", datetime(2026, 10, 7, 7, 6))          # 뒤로 가지 않음
                self.assertEqual(json.loads(F.CHECKED.read_text(encoding="utf-8"))["checked"], "20261006")
                home = Path(tmp)
                (home / "price").mkdir()
                (home / "price" / "000001.json").write_text(json.dumps({"closes": [["20261006", 100.0]]}), encoding="utf-8")
                client = mock.Mock()
                client.daily.return_value = [("20261006", {"종가": 100.0}), ("20261007", {"종가": 101.0})]
                now = mock.Mock(wraps=datetime)
                now.now.return_value = datetime(2026, 10, 7, 7, 5, tzinfo=F.KST)
                with mock.patch.object(F, "PRICE", home / "price"), mock.patch.object(F, "VOLUME", home / "v"), \
                        mock.patch.object(F, "KOSDAQ", home / "k"), mock.patch.object(F, "FLOW", home / "f"), \
                        mock.patch.object(F.broker_kis, "market", return_value=client), mock.patch.object(F, "datetime", now):
                    F.CHECKED.unlink()
                    self.assertEqual(F.main(), 0)
                    self.assertEqual(json.loads(F.CHECKED.read_text(encoding="utf-8"))["checked"], "20261006", "오늘 줄은 확정 아님")
                    F.CHECKED.unlink()
                    F.main(["000001"])
                    self.assertFalse(F.CHECKED.exists(), "몇 종목만 물을 땐 확정 표시 안 함")
                    now.now.return_value = datetime(2026, 10, 7, 1, 0, tzinfo=F.KST)
                    F.main()
                    self.assertFalse(F.CHECKED.exists(), "새벽(밤 정리 전일 수 있음)엔 확정 표시 안 함")


if __name__ == "__main__":
    unittest.main()
