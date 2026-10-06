import unittest

import notify_discord as N


class Message(unittest.TestCase):
    def test_picks_and_b(self):
        found = {"date": "20260928", "breadth": 41.0, "align_open": False, "slots": 5, "counted": ["1"] * 494,
                 "picks": [{"code": "005930", "name": "삼성전자", "갈래": ["추세 규칙"], "종가": 285500, "시총순위": 1,
                            "팔기": "종가 +10% 익절 · −5% 손절 · 최대 10거래일"}],
                 "b_group": [{"code": "000660", "name": "SK하이닉스", "모자란 수": 1, "코멘트": "추세 규칙까지 1개 모자람: 60일 상승 12%"}]}
        text = "\n".join(N.lines(found))
        self.assertIn("09-28", text)
        self.assertNotIn("005930", text)   # 짧은 글: 종목코드 · 팔기 설명은 뺌(2026-10-06)
        self.assertNotIn("팔기", text)
        self.assertIn("삼성전자", text)
        self.assertIn("285,500원", text)
        self.assertNotIn("SK하이닉스", text)   # B그룹은 보내지 않음

    def test_empty_day(self):
        text = "\n".join(N.lines({"date": "20260928", "picks": [], "b_group": []}))
        self.assertIn("0종목", text)
        self.assertEqual(len(text.splitlines()), 1)

    def test_short_lines(self):
        self.assertEqual(N.short_item("🟢", "매수", "삼성전자(005930) · 10:00 시가 약 276,000원에 4칸(40%) 사기 · 추세 · 순서 무리 2/4"),
                         "🟢 매수 삼성전자 4칸")
        self.assertEqual(N.short_line("✅ 매도 체결 · LG전자(066570) · 2칸 · 10:00 시가 98,000원 · 손익 -3.1%(비용 뺌) · 손절"),
                         "✅ 매도 LG전자 2칸 -3.1%")
        self.assertEqual(N.short_line("🧪 모의투자(15분봉) 매수 · 삼성전자(005930) 36주 · 시장가 · 접수"), "🧪 매수 삼성전자 36주 ✅")
        self.assertEqual(N.brief(["※ 안내", ""]), [])

    def test_chunks_under_limit(self):
        rows = ["가" * 300] * 20
        parts = N.chunks(rows)
        self.assertTrue(all(len(p) <= N.LIMIT + 1 for p in parts))
        self.assertEqual(sum(p.count("가") for p in parts), 6000)

    def test_no_url_sends_nothing(self):
        import os
        os.environ.pop("DISCORD_WEBHOOK_URL", None)
        self.assertEqual(N.main(), 0)


if __name__ == "__main__":
    unittest.main()
