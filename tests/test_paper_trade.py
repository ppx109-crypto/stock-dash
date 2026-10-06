import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import broker_kis
import paper_trade as P


def bal(cash=10_000_000, positions=()):
    ps = [{"code": c, "name": c, "quantity": q, "value": v} for c, q, v in positions]
    return {"cash": cash, "value": sum(p["value"] for p in ps), "positions": ps}


class Guard(unittest.TestCase):
    def env(self, **kw):
        base = {"KIS_PAPER_APP_KEY": "paperkey", "KIS_PAPER_APP_SECRET": "s", "KIS_PAPER_ACCOUNT": "12345678-01", "KIS_APP_KEY": "realkey"}
        base.update(kw)
        return mock.patch.dict(os.environ, base, clear=False)

    def test_only_paper_server(self):
        with self.env():
            b = P.PaperBroker()
        self.assertEqual(b.base, P.PAPER_BASE)
        b.base = "https://openapi.koreainvestment.com:9443"
        with self.assertRaises(broker_kis.BrokerError):
            b.order("005930", "buy", 1)

    def test_refuses_real_key_and_bad_account(self):
        with self.env(KIS_PAPER_APP_KEY="realkey"), self.assertRaises(broker_kis.BrokerError):
            P.PaperBroker()
        with self.env(KIS_PAPER_ACCOUNT="1234"), self.assertRaises(broker_kis.BrokerError):
            P.PaperBroker()

    def test_account_forms(self):
        for text, want in (("50123456-01", ("50123456", "01")), ("5012345601", ("50123456", "01")),
                           (" 50123456 – 01 \n", ("50123456", "01")), ("50123456", ("50123456", "01"))):
            self.assertEqual(P.account_parts(text), want)
        with self.assertRaises(broker_kis.BrokerError) as e:
            P.account_parts("987-654")
        self.assertNotIn("987", str(e.exception), "번호를 찍지 않음")

    def test_bad_order_refused_before_sending(self):
        with self.env():
            b = P.PaperBroker()
        with mock.patch.object(b, "request") as req:
            for code, side, qty in (("005930", "hold", 1), ("5930", "buy", 1), ("005930", "buy", 0)):
                with self.assertRaises(broker_kis.BrokerError):
                    b.order(code, side, qty)
            req.assert_not_called()

    def test_switches(self):
        with mock.patch.dict(os.environ, {"PAPER_TRADING": "off", "KIS_PAPER_APP_KEY": "k"}):
            self.assertFalse(P.enabled()[0])
        with mock.patch.dict(os.environ, {"PAPER_TRADING": "on", "KIS_PAPER_APP_KEY": ""}):
            self.assertFalse(P.enabled()[0])


class StartDay(unittest.TestCase):
    def test_no_orders_before_the_start_day(self):
        from datetime import datetime
        env = {"PAPER_TRADING": "on", "KIS_PAPER_APP_KEY": "k", "PAPER_START": "20261002"}
        with mock.patch.dict(os.environ, env), mock.patch.object(P, "OFF", Path("/nonexistent/off")):
            self.assertFalse(P.enabled(datetime(2026, 10, 1, 15, 0, tzinfo=P.KST))[0])
            self.assertTrue(P.enabled(datetime(2026, 10, 2, 9, 1, tzinfo=P.KST))[0])


class Sizing(unittest.TestCase):
    def test_buy_uses_slots_of_total_and_cash(self):
        done = [{"type": "buy", "code": "000001", "칸": 4, "decided": "2026100110", "kind": "추세"},
                {"type": "buy", "code": "000002", "칸": 2, "decided": "2026100110", "kind": "정배열"}]
        got = P.plan_orders(done, {"positions": {}}, bal(10_000_000), {"000001": 50_000, "000002": 33_000}, "2026100111")
        self.assertEqual([(c, s, q) for _, c, s, q, _ in got], [("000001", "buy", 80), ("000002", "buy", 60)])

    def test_buy_capped_by_cash(self):
        done = [{"type": "buy", "code": "000001", "칸": 4, "decided": "d"}]
        got = P.plan_orders(done, {"positions": {}}, bal(1_000_000, [("000009", 10, 9_000_000)]), {"000001": 10_000}, "b")
        self.assertEqual(got[0][3], 98)                    # 총액 1천만의 40%는 400만이지만 현금 100만의 98%까지만

    def test_sell_all_or_part(self):
        state = {"positions": {"000002": {"칸": 2}}}       # 000001은 다 팔림, 000002는 4칸 가운데 2칸 팔고 2칸 남음
        done = [{"type": "sell", "code": "000001", "칸": 2, "decided": "d", "why": "손절"},
                {"type": "sell", "code": "000002", "칸": 2, "decided": "d", "why": "절반 익절"},
                {"type": "sell", "code": "000003", "칸": 2, "decided": "d", "why": "손절"}]   # 모의 잔고에 없음 → 안 냄
        got = P.plan_orders(done, state, bal(0, [("000001", 7, 1), ("000002", 11, 1)]), {}, "b")
        self.assertEqual([(c, s, q) for _, c, s, q, _ in got], [("000001", "sell", 7), ("000002", "sell", 6)])


class TwoRules(unittest.TestCase):
    def test_a_rule_sells_only_what_it_bought(self):
        done = [{"type": "sell", "code": "000001", "칸": 4, "decided": "d", "why": "손절"}]
        # 모의 계좌엔 30주(두 규칙 합), 이 규칙 장부엔 10주 → 10주만 팖
        got = P.plan_orders(done, {"positions": {}}, bal(0, [("000001", 30, 1)]), {}, "b", held={"000001": 10})
        self.assertEqual(got[0][3], 10)
        got = P.plan_orders(done, {"positions": {}}, bal(0, [("000001", 30, 1)]), {}, "b", held={})
        self.assertEqual(got, [], "이 규칙이 산 적 없으면 팔지 않음")

    def test_daily_book_is_separate(self):
        self.assertNotEqual(P.book_path("1h"), P.book_path("1d"))

    def test_three_books_and_shares(self):
        self.assertEqual(len({P.book_path(s) for s in ("1h", "1d", "15m")}), 3)
        self.assertAlmostEqual(sum(P.SHARES.values()), 1.0)
        self.assertEqual(P.SHARES["15m"], 0.5)          # 2026-10-03 최종: 1일봉 50 · 15분봉 50 · 1시간봉 0
        self.assertEqual(P.SHARES["1h"], 0.0)


class Execute(unittest.TestCase):
    def test_orders_once_and_books(self):
        class Fake:
            def __init__(self):
                self.sent = []

            def balance(self):
                return bal(10_000_000)

            def order(self, code, side, qty):
                self.sent.append((code, side, qty))
                return "123"
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(P, "BOOK", Path(tmp) / "book.json"), mock.patch.object(P, "OFF", Path(tmp) / "off"), \
                mock.patch.dict(os.environ, {"PAPER_TRADING": "on", "KIS_PAPER_APP_KEY": "k"}), \
                mock.patch.dict(P.SHARES, {"1h": 0.4}):        # 주문 셈 자체를 보는 시험(지금 1시간봉 몫은 0 · 모의 주문 끔)
            fake = Fake()
            done = [{"type": "buy", "code": "000001", "칸": 2, "decided": "2026100110", "name": "가"}]
            lines = P.execute(done, {"positions": {}}, {"000001": 10_000}, "2026100111", broker=fake)
            again = P.execute(done, {"positions": {}}, {"000001": 10_000}, "2026100111", broker=fake)
            self.assertEqual(fake.sent, [("000001", "buy", 80)], "몫 40%면 계좌의 40% × 2칸 / 10")
            self.assertEqual(len(lines), 1)
            self.assertEqual(again, [])
            book = json.loads((Path(tmp) / "book.json").read_text(encoding="utf-8"))
            self.assertEqual(book["held"], {"000001": 80})
            self.assertNotIn("12345678", json.dumps(book))
            (Path(tmp) / "off").write_text("")
            self.assertEqual(P.execute([dict(done[0], decided="x")], {"positions": {}}, {"000001": 1}, "b", broker=fake), [])


class Buyable(unittest.TestCase):
    """2026-10-06: 계좌 돈에 꽉 맞춘 시장가 매수가 거절됨(40250000) → 매수가능 수량으로 줄여 넣음."""
    def broker(self):
        env = {"KIS_PAPER_APP_KEY": "paperkey", "KIS_PAPER_APP_SECRET": "s", "KIS_PAPER_ACCOUNT": "12345678-01", "KIS_APP_KEY": "realkey"}
        with mock.patch.dict(os.environ, env, clear=False):
            b = P.PaperBroker()
        b.token, b.expires = "t", 9e18
        return b

    def answers(self, can, ok=True):
        sent = []

        def request(method, path, headers=None, params=None, json=None):
            if path == P.BUYABLE_PATH:
                return None, ({"rt_cd": "0", "output": {"nrcvb_buy_qty": str(can)}} if ok else {"rt_cd": "1", "msg_cd": "X"})
            sent.append(json)
            return None, {"rt_cd": "0", "output": {"ODNO": "77"}}
        return request, sent

    def test_buy_cut_to_buyable(self):
        b = self.broker()
        req, sent = self.answers(36_100)
        with mock.patch.object(b, "request", side_effect=req):
            self.assertEqual(b.order("251340", "buy", 45_539), "77")
        self.assertEqual(sent[0]["ORD_QTY"], "36100")
        self.assertEqual(b.last_qty, 36_100)

    def test_buy_within_buyable_unchanged(self):
        b = self.broker()
        req, sent = self.answers(50_000)
        with mock.patch.object(b, "request", side_effect=req):
            b.order("251340", "buy", 100)
        self.assertEqual(sent[0]["ORD_QTY"], "100")

    def test_zero_buyable_refused_before_sending(self):
        b = self.broker()
        req, sent = self.answers(0)
        with mock.patch.object(b, "request", side_effect=req), self.assertRaises(broker_kis.BrokerError):
            b.order("251340", "buy", 10)
        self.assertEqual(sent, [])

    def test_query_fails_sends_as_before(self):
        b = self.broker()
        req, sent = self.answers(0, ok=False)
        with mock.patch.object(b, "request", side_effect=req):
            b.order("251340", "buy", 10)
        self.assertEqual(sent[0]["ORD_QTY"], "10")

    def test_sell_not_asked(self):
        b = self.broker()
        req, sent = self.answers(0)
        with mock.patch.object(b, "request", side_effect=req):
            b.order("251340", "sell", 10)
        self.assertEqual(sent[0]["ORD_QTY"], "10")

    def test_execute_books_what_was_really_sent(self):
        class Fake:
            last_qty = None

            def balance(self):
                return bal(10_000_000)

            def order(self, code, side, qty):
                self.last_qty = qty - 30
                return "1"
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(P, "BOOK", Path(tmp) / "book.json"), mock.patch.object(P, "OFF", Path(tmp) / "off"), \
                mock.patch.dict(os.environ, {"PAPER_TRADING": "on", "KIS_PAPER_APP_KEY": "k"}), \
                mock.patch.dict(P.SHARES, {"1h": 0.4}):
            done = [{"type": "buy", "code": "000001", "칸": 2, "decided": "2026100110", "name": "가"}]
            lines = P.execute(done, {"positions": {}}, {"000001": 10_000}, "2026100111", broker=Fake())
            book = json.loads((Path(tmp) / "book.json").read_text(encoding="utf-8"))
            self.assertEqual(book["held"], {"000001": 50})
            self.assertIn("줄임", lines[0])


if __name__ == "__main__":
    unittest.main()
