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
                         "레버리지 봇 모의 매수, KODEX 레버리지(122630) 120주, 접수")
        self.assertEqual(N.tidy("계좌 그달 손실 -9.2%(15:1x 값)"), "계좌 그달 손실 -9.2%(장 마감 직전 값)")
        self.assertEqual(N.tidy("⚠️ 주문 중 문제 · ConnectionError"), "주문 중 문제, 오류")
        self.assertEqual(N.tidy("거절(APBK0919)"), "거절")
        self.assertEqual(N.tidy("LG전자 · SK하이닉스 · NAVER"), "LG전자, SK하이닉스, NAVER")   # 종목 이름 영어는 그대로(사용자 2026-10-12)
        self.assertEqual(N.tidy("ETF 몫 × 0.4 → 0.2 −3.1%"), "지수펀드 몫 곱하기 0.4 다음 0.2 -3.1%")
        self.assertEqual(N.tidy("※ 안내"), "")
        for line in ["🔄 자리 바꾸기 가 → 나", "⏭️ 매수 건너뜀", "• 한 줄 ─── ★", "**굵게** · `코드`"]:
            out = N.tidy(line)
            self.assertFalse(any(ch in "🔄⏭️•─★→·*`" for ch in out), out)

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

    def test_a_group_and_hourly_one_message(self):
        """저녁 작업: A그룹 알림과 1시간봉 후보가 모음 파일로 들어가 끝에 한 통으로 감(사용자 2026-10-15)."""
        import os, tempfile, json
        from pathlib import Path
        from unittest import mock
        sent = []
        with tempfile.TemporaryDirectory() as td:
            buf = os.path.join(td, "b.json")
            os.environ.update(DISCORD_WEBHOOK_URL="https://example.invalid/hook", DISCORD_BUFFER=buf)
            try:
                with mock.patch.object(N.requests, "post", side_effect=lambda url, json, timeout: sent.append(json["content"]) or mock.Mock(status_code=204)), \
                     mock.patch.object(N, "Path", side_effect=lambda q: Path(td) / "a.json" if q == "study/a_group.json" else Path(q)):
                    (Path(td) / "a.json").write_text(json.dumps({"date": "2026-10-14", "picks": [], "breadth": 42.0}), encoding="utf-8")
                    self.assertEqual(N.main(), 0)
                    N.post(["1시간봉 봇 다음 거래일 후보 0개, 시장 폭 42.0%"])
                    self.assertEqual(sent, [])
                    self.assertTrue(N.flush(buf, "저녁 A그룹 · 1시간봉 후보 10-14"))
            finally:
                os.environ.pop("DISCORD_WEBHOOK_URL", None); os.environ.pop("DISCORD_BUFFER", None)
        self.assertEqual(len(sent), 1)
        self.assertIn("A그룹", sent[0]); self.assertIn("1시간봉", sent[0])

    def test_digest_two_a_day(self):
        """한투 알림은 모음 폴더에 쌓였다가 한 통(이모지 붙음)으로 나가고, ⚠️ 급한 알림만 바로 감(사용자 2026-10-15)."""
        import os, tempfile, json
        from pathlib import Path
        from unittest import mock
        sent = []
        with tempfile.TemporaryDirectory() as td:
            os.environ.update(DISCORD_WEBHOOK_URL="https://example.invalid/hook", DISCORD_DIGEST=td)
            try:
                with mock.patch.object(N.requests, "post", side_effect=lambda url, json, timeout: sent.append(json["content"]) or mock.Mock(status_code=204)):
                    N.post(["1일봉 봇 오늘 판단", "삼성전자 매수 10주"])
                    N.post(["15분봉 봇", "SK하이닉스 손절"])
                    N.post(["15분봉 봇", "SK하이닉스 손절"])          # 같은 줄은 한 번만
                    self.assertEqual(sent, [])
                    self.assertEqual(len(list(Path(td).glob("*/*.json"))), 3)
                    N.post(["⚠️ 장부를 올리지 못했습니다"])             # 급한 것은 바로
                    self.assertEqual(len(sent), 1)
                    self.assertTrue(N.digest_flush(td, "한투 모의투자 10-15 장 마감 모음"))
                    self.assertEqual(list(Path(td).glob("*/*.json")), [])
                    self.assertTrue(N.digest_flush(td, "빈 모음"))      # 쌓인 것이 없으면 보내지 않음
            finally:
                os.environ.pop("DISCORD_WEBHOOK_URL", None); os.environ.pop("DISCORD_DIGEST", None)
        self.assertEqual(len(sent), 2)
        msg = sent[1]
        self.assertIn("한투 모의투자 10-15 장 마감 모음", msg)       # 2026-11-20부터 짧게: 📬 · 시각 · 줄 그림 없음
        self.assertNotIn("📬", msg)
        self.assertIn("· 1일봉 봇 오늘 판단", msg); self.assertIn("  삼성전자 매수 10주", msg)
        self.assertEqual(msg.count("SK하이닉스 손절"), 1)

    def test_digest_short_20261120(self):
        """모음은 아주 짧게(사용자 2026-11-20 «불필요한 말이 너무 많고 말이 어렵고 길어») — 그날 봇 먼저, 장부 대조 · 검산은 뒤에."""
        items = [
            {"t": "2026-11-20 11:18", "rows": ["장부 맞춰보기 11월 19일 · 1시간봉 같은 매매 0/0 · 1일봉 0/0 · 엔진 주문 0"]},
            {"t": "2026-11-20 12:07", "rows": ["검산 11월 19일, 확정 일봉과도 종가 다름 397/424 · 000080 000120 000150 000210 000240"]},
            {"t": "2026-11-20 15:23", "rows": ["1일봉 봇 11월 20일 15시 20분 판단, 시장 폭 29.0%, 들고 있는 종목 0개",
                                              "1일봉은 오늘 사고팔 것 없음(다른 봇 주문은 각 봇 줄에)"]},
        ]
        self.assertEqual(N.digest_text(items, "11/20 마감"),
                         ["11/20 마감", "· 1일봉: 매매 없음 (보유 0)", "· 11/19 장부 대조: 매매 0건 · 이상 없음", "· ⚠️ 11/19 종가 검산: 397/424 다름"])
        more = [
            {"t": "2026-11-18 15:20", "rows": ["빈칸 엔진 11월 18일 판단, 시장 폭 모름%, 규칙이 쓴 몫 0%",
                                              "🧪 매도 KOSEF 국고채10년 57주 → ✅ 접수", "\u3000까닭: 돌리기 멈춤(엔진 끔)"]},
            {"t": "2026-11-12 15:20", "rows": ["레버리지 봇 11월 12일, 국면 하락(어제 장 끝 기준), 목표 없음 0%",
                                              "🧪 모의투자(덧붙임) 매도 · KODEX 인버스(114800) 12,653주 · 접수"]},
            {"t": "2026-11-12 11:00", "rows": ["장부 맞춰보기 11월 11일 · 1시간봉 같은 매매 1/2 · 1일봉 2/2"]},
            {"t": "2026-11-12 15:21", "rows": ["1일봉 봇 11월 12일 15시 20분 판단, 시장 폭 55.0%, 들고 있는 종목 3개", "매수: 삼성전자 2칸 사기",
                                              "손절: SK하이닉스 1칸 팔기"]},
            {"t": "2026-11-12 15:22", "rows": ["15분봉 봇 주문 실패", "삼성전자 매수 거절"]},
        ]
        out = N.digest_text(more, "t")
        self.assertEqual(out[1:3], ["· 레버리지: 국면 하락", "  매도 KODEX 인버스(114800) 12,653주"])
        self.assertIn("· 빈칸 엔진: 주문 1건", out); self.assertIn("  매도 KOSEF 국고채10년 57주", out)
        self.assertIn("  까닭: 돌리기 멈춤(엔진 끔)", out)
        self.assertIn("· 1일봉: 주문 2건 (보유 3)", out); self.assertIn("  매수: 삼성전자 2칸 사기", out)
        self.assertIn("  ⚠️ 삼성전자 매수 거절", out)
        self.assertEqual(out[-1], "· 11/11 장부 대조: ⚠️ 다름 1시간봉 1/2")      # 장부 대조 · 검산은 뒤에

    def test_digest_flush_keeps_files_when_send_fails(self):
        """보내기에 실패하면 파일을 지우지 않아 다음 모음에 다시 실림."""
        import os, tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            N.digest_add(td, ["1일봉 봇", "삼성전자 매수"])
            os.environ["DISCORD_WEBHOOK_URL"] = "https://example.invalid/hook"
            try:
                with mock.patch.object(N.requests, "post", return_value=mock.Mock(status_code=500)):
                    self.assertFalse(N.digest_flush(td, "모음"))
            finally:
                os.environ.pop("DISCORD_WEBHOOK_URL", None)
            self.assertEqual(len(list(Path(td).glob("*/*.json"))), 1)

    def test_workflows_two_digests(self):
        """하루 두 번: 16:10 봇 지킴이(장 마감 모음) · 저녁 A그룹(저녁 모음). 봇 작업은 모두 모음 폴더로 보냄."""
        from pathlib import Path
        w = Path(__file__).resolve().parent.parent / ".github" / "workflows"
        self.assertIn("--digest-flush discord-digest", (w / "run-watch.yml").read_text(encoding="utf-8"))
        self.assertIn("--digest-flush discord-digest", (w / "a-group.yml").read_text(encoding="utf-8"))
        for f in ["daily-live.yml", "hourly-a-live.yml", "m15-live.yml", "reconcile.yml", "intraday.yml", "daily-close-check.yml", "a-group.yml"]:
            t = (w / f).read_text(encoding="utf-8")
            self.assertIn("DISCORD_DIGEST: discord-digest", t, f)
            self.assertNotIn("DISCORD_BUFFER", t, f)


if __name__ == "__main__":
    unittest.main()


class Bundle(unittest.TestCase):
    """종가 작업 알림 한 번에(사용자 2026-10-14 "한번으로 정리해서")."""
    def test_buffer_then_flush_once(self):
        import os, tempfile
        from unittest import mock
        sent = []
        buf = os.path.join(tempfile.mkdtemp(), "bundle.json")
        with mock.patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://example.invalid/hook", "DISCORD_BUFFER": buf}), \
                mock.patch.object(N.requests, "post", side_effect=lambda url, json, timeout: sent.append(json["content"]) or mock.Mock(status_code=204)):
            self.assertTrue(N.post(["빈칸 엔진 오늘 쉼"]))
            self.assertTrue(N.post(["1일봉 판단 · 사고팔 것 없음", "빈칸 엔진 오늘 쉼"]))
            self.assertEqual(sent, [])                       # 모으는 동안은 안 보냄
            self.assertTrue(N.flush(buf, "종가 작업 10-14 모음"))
        self.assertEqual(len(sent), 1)                       # 한 번만
        self.assertEqual(sent[0].count("빈칸 엔진 오늘 쉼"), 1)  # 같은 줄은 한 번
        self.assertTrue(sent[0].startswith("☆한투 종가 작업 10-14 모음"))
        self.assertFalse(os.path.exists(buf))

    def test_flush_without_anything(self):
        import os, tempfile
        self.assertTrue(N.flush(os.path.join(tempfile.mkdtemp(), "none.json"), "머리말"))


class UrgentNotBuffered(unittest.TestCase):
    def test_warning_sent_at_once(self):
        import os, tempfile
        from unittest import mock
        sent = []
        buf = os.path.join(tempfile.mkdtemp(), "b.json")
        with mock.patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://example.invalid/hook", "DISCORD_BUFFER": buf}), \
                mock.patch.object(N.requests, "post", side_effect=lambda url, json, timeout: sent.append(json["content"]) or mock.Mock(status_code=204)):
            N.post(["⚠️ 계좌 흔들림 상한 단계 문제"])
            N.post(["빈칸 엔진 오늘 쉼"])
        self.assertEqual(len(sent), 1)
        self.assertFalse(any("빈칸" in x for x in sent))
