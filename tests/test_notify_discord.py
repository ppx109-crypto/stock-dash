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
                         "매도 체결: LG전자 2칸 -3.1%")
        self.assertEqual(N.short_line("🧪 모의투자(15분봉) 매수 · 삼성전자(005930) 36주 · 시장가 · 접수"), "모의 매수: 삼성전자 36주 주문 들어감")
        self.assertEqual(N.short_line("🧪 모의투자(1일봉) 매도 · 카카오(035720) 5주 · 시장가 · 거절 · APBK0919"), "모의 매도: 카카오 5주 주문 거절됨")
        self.assertEqual(N.brief(["※ 안내", ""]), [])

    def test_tidy_no_english_no_shapes(self):
        # 사용자 2026-10-12: 영어 다 빼고 · 이상한 모양 전부 빼 · 알기 쉽게
        self.assertEqual(N.tidy("🟢 매수 삼성전자 4칸"), "매수 삼성전자 4칸")
        self.assertEqual(N.tidy("✅ **1일봉 체결 10-12** · 보유 3"), "1일봉 체결 10-12, 보유 3")
        self.assertEqual(N.tidy("🧪 모의투자(덧붙임) 매수 · KODEX 레버리지(122630) 120주 · 접수"),
                         "레버리지 봇 모의 매수, 코덱스 레버리지(122630) 120주, 접수")
        self.assertEqual(N.tidy("계좌 그달 손실 -9.2%(15:1x 값)"), "계좌 그달 손실 -9.2%(장 마감 직전 값)")
        self.assertEqual(N.tidy("⚠️ 주문 중 문제 · ConnectionError"), "주문 중 문제, 오류")
        self.assertEqual(N.tidy("거절(APBK0919)"), "거절")
        self.assertEqual(N.tidy("LG전자 · SK하이닉스 · NAVER"), "엘지전자, 에스케이하이닉스, 네이버")
        self.assertEqual(N.tidy("ETF 몫 × 0.4 → 0.2 −3.1%"), "지수펀드 몫 곱하기 0.4 다음 0.2 -3.1%")
        self.assertEqual(N.tidy("※ 안내"), "")
        for line in ["🔄 자리 바꾸기 A → B", "⏭️ 매수 건너뜀", "• 한 줄 ─── ★"]:
            out = N.tidy(line)
            self.assertFalse(any("a" <= ch.lower() <= "z" for ch in out), out)
            self.assertFalse(any(ch in "🔄⏭️•─★→·*" for ch in out), out)

    def test_messages_prefix(self):
        msgs = N.messages(["🌇 **1일봉 10-12 15:20** · 폭 45%", "", "※ 안내", "🟢 매수 삼성전자 2칸"])
        self.assertEqual(msgs, ["☆한투 1일봉 10-12 15:20, 폭 45%\n매수 삼성전자 2칸\n"])
        long = N.messages(["가" * 300] * 20)
        self.assertTrue(len(long) > 1 and all(m.startswith("☆한투 ") for m in long))
        self.assertTrue(all(len(m) <= 2000 for m in long))
        self.assertFalse(N.messages(["A그룹 10-12"], paper=False)[0].startswith("☆한투"))

    def test_post_uses_prefix(self):
        import os
        from unittest import mock
        sent = []
        os.environ["DISCORD_WEBHOOK_URL"] = "https://example.invalid/hook"
        try:
            with mock.patch.object(N.requests, "post", side_effect=lambda url, json, timeout: sent.append(json["content"]) or mock.Mock(status_code=204)):
                self.assertTrue(N.post(["✅ 매수 체결 · 삼성전자(005930) · 2칸 · 종가 70,000원"]))
        finally:
            os.environ.pop("DISCORD_WEBHOOK_URL", None)
        self.assertEqual(sent, ["☆한투 매수 체결, 삼성전자(005930), 2칸, 종가 70,000원\n"])

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
