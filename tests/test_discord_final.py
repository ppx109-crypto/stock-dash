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

    def test_bot_tag_kept(self):
        self.assertEqual(N.short_line("🧪 모의투자(흔들림 상한) 매도 · 005930 10주 · 접수"), "흔들림 상한 모의 매도: 005930 10주 주문 들어감")
        self.assertTrue(N.short_line("🧪 모의투자(사건 바구니) 매도 · 268280 3주 · 규칙에 자리 내줌 · 접수").startswith("바구니 모의 매도"))


if __name__ == "__main__":
    unittest.main()
