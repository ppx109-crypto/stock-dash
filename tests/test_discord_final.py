"""최종본(MIX-0054 · 2026-10-19 연구 종료) 디스코드 문구 정리를 지키는 시험."""
import unittest

import notify_discord as N


class FinalDiscordText(unittest.TestCase):
    def test_head_icon_follows_owner(self):
        self.assertEqual(N._icon("빈칸 엔진 10월 16일 판단, 시장 폭 40%, 규칙이 쓴 몫 30%"), "🧩")
        self.assertEqual(N._icon("장부 맞춰보기 10월 16일 · 1시간봉 같은 매매 1/1 · 1일봉 2/2"), "🧾")
        self.assertEqual(N._icon("1일봉 봇 10월 16일 15시 20분 판단"), "📅")

    def test_skip_is_not_green(self):
        self.assertEqual(N._line_icon("모의 매수 건너뜀: 삼성전자 (최종본에서 이 규칙은 새 매수를 끔)"), "⏸️")
        self.assertEqual(N._line_icon("모의 매수: 삼성전자 3주 주문 거절됨"), "⏸️")
        self.assertEqual(N._line_icon("모의 매수: 삼성전자 3주 주문 들어감"), "🟢")

    def test_tidy_final_words(self):
        self.assertEqual(N.tidy("🧪 매수 KODEX 인버스 1,000주 → ✅ 접수"), "매수 KODEX 인버스 1,000주, 접수")
        self.assertNotIn("최종 판(최종 판)", N.tidy("최종 판(MIX-0054)에서 이 규칙은 새 매수를 끔"))
        self.assertIn("1일봉 모의", N.tidy("🧪 모의투자(1일봉 매수 후보) 주문 못 넣음"))
        self.assertNotIn("　", N.tidy("　까닭: 국면 상승"))

    def test_lines_have_no_bot_tag(self):
        # 바구니 · 흔들림 상한 · 레버리지 봇은 각자 따로 한 통으로 보내므로 줄 안에 봇 이름을 붙이지 않음
        self.assertEqual(N.short_line("🧪 모의투자(흔들림 상한) 매도 · 005930 10주 · 접수"), "모의 매도: 005930 10주 주문 들어감")
        self.assertEqual(N._icon("사건 바구니 10월 16일 판단"), "🧺")
        self.assertEqual(N._icon("🛡️ 계좌 흔들림 상한 · 허용 80% · 든 것 95%, 그중 16% 덜어냄(2건)"), "🛡️")
        self.assertEqual(N._icon("레버리지 봇 10월 16일"), "📈")

    def test_hourly_and_a_group_quiet(self):
        import os
        from unittest import mock
        import hourly_a
        os.environ.pop("HOURLY_DISCORD", None)
        os.environ.pop("A_GROUP_DISCORD", None)
        with mock.patch.object(N, "post", side_effect=AssertionError("보내면 안 됨")):
            self.assertTrue(hourly_a.send(["1시간봉 봇 10시 3분 판단", "🟢 매수 삼성전자 4칸"]))
        os.environ["DISCORD_WEBHOOK_URL"] = "https://example.invalid/hook"
        try:
            with mock.patch.object(N.requests, "post", side_effect=AssertionError("보내면 안 됨")):
                self.assertEqual(N.main(), 0)
        finally:
            os.environ.pop("DISCORD_WEBHOOK_URL", None)

if __name__ == "__main__":
    unittest.main()
