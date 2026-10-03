import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import numpy as np

import idle_live as L
import paper_trade as P


def flat(n=60, v=100.0):
    return np.full(n, v)


def base_px():
    return {c: flat() for c in L.CODES}


PRICE = {c: 100.0 for c in L.CODES}


class StepTest(unittest.TestCase):
    def test_week_end_and_holiday(self):
        self.assertTrue(L.week_end("20261002"))        # 금요일
        self.assertFalse(L.week_end("20261001"))
        self.assertTrue(L.week_end("20261008"))        # 10-09(한글날 · 금) 휴장 → 목요일이 주 끝
        self.assertEqual(L.next_trading_day("20261008"), "20261012")

    def test_engine_off_when_breadth_strong(self):
        orders, st, _ = L.step({}, "20261005", base_px(), breadth=60, used=0.0, total=1e7, cash=1e7, held={},
                               now_price=PRICE, is_week_end=False)
        self.assertEqual(orders, [])

    def test_rotation_buys_two_when_engine_on(self):
        px = base_px()
        for c, g in zip(L.ROT, (0.05, 0.02, -0.01, 0.03)):
            px[c] = np.r_[flat(40), np.linspace(100, 100 * (1 + g), 20)]
        orders, st, _ = L.step({}, "20261005", px, breadth=40, used=0.1, total=1e7, cash=9e6, held={},
                               now_price=PRICE, is_week_end=False)
        bought = {c: q for c, s, q, _ in orders if s == "buy"}
        self.assertEqual(set(bought), {"133690", "148070"})
        # 엔진 몫 = 계좌 × (1 − 0.1) × 반 × 0.97 ÷ 100원
        self.assertEqual(bought["133690"], int(1e7 * 0.9 * 0.5 * 0.97 / 100))
        self.assertEqual(st["positions"]["133690"]["kind"], "돌리기")

    def test_rotation_kept_midweek_and_sold_when_engine_off(self):
        state = {"positions": {"133690": {"kind": "돌리기", "price": 100.0, "day": "20261002", "days": 1}}, "last_day": "20261002"}
        orders, _, _ = L.step(state, "20261005", base_px(), breadth=40, used=0.0, total=1e7, cash=5e6,
                              held={"133690": 1000}, now_price=PRICE, is_week_end=False)
        self.assertFalse(any(c == "133690" for c, s, q, _ in orders))       # 주 중간엔 그대로
        orders, st, _ = L.step(state, "20261005", base_px(), breadth=70, used=0.0, total=1e7, cash=5e6,
                               held={"133690": 1000}, now_price=PRICE, is_week_end=False)
        self.assertIn(("133690", "sell", 1000), [(c, s, q) for c, s, q, _ in orders])
        self.assertNotIn("133690", st["positions"])

    def test_dip_buy_then_stop_and_cool(self):
        px = base_px()
        px["069500"] = np.r_[flat(55), [100, 99, 97, 96, 95]]           # 5일 −5%
        orders, st, _ = L.step({}, "20261005", px, breadth=30, used=0.0, total=1e7, cash=1e7, held={},
                               now_price=dict(PRICE, **{"069500": 95.0}), is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("069500", "buy")])
        self.assertEqual(st["positions"]["069500"]["kind"], "급락")
        qty = orders[0][2]
        # 다음 날 −3% → 손절 · 21일 쉼(연구: j + 1 + 20) · 같은 날 다시 안 삼
        orders, st2, _ = L.step(st, "20261006", px, breadth=30, used=0.0, total=1e7, cash=0, held={"069500": qty},
                                now_price=dict(PRICE, **{"069500": 95.0 * 0.97}), is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("069500", "sell")])
        self.assertEqual(st2["cool"], L.DIP_COOL + 1)
        self.assertNotIn("069500", st2["positions"])

    def test_dip_take_profit(self):
        state = {"positions": {"069500": {"kind": "급락", "price": 100.0, "day": "20261002", "days": 1}}, "last_day": "20261002"}
        orders, st, _ = L.step(state, "20261005", base_px(), breadth=30, used=0.0, total=1e7, cash=0,
                               held={"069500": 10}, now_price=dict(PRICE, **{"069500": 103.1}), is_week_end=False)
        self.assertIn(("069500", "sell", 10), [(c, s, q) for c, s, q, _ in orders])
        self.assertEqual(st["cool"], 0)

    def test_dollar_in_downtrend_converts_rotation_dollar(self):
        px = base_px()
        px["069500"] = np.r_[flat(59), [98.0]]
        px["138230"] = np.r_[flat(40), np.linspace(100, 103, 20)]
        state = {"positions": {"138230": {"kind": "돌리기", "price": 100.0, "day": "20261002", "days": 1}}, "last_day": "20261002"}
        orders, st, _ = L.step(state, "20261005", px, breadth=40, used=0.0, total=1e7, cash=5e6,
                               held={"138230": 500}, now_price=dict(PRICE, **{"069500": 98.0, "138230": 103.0}), is_week_end=False)
        self.assertEqual(orders, [])                                       # 팔고 다시 사지 않음
        self.assertEqual(st["positions"]["138230"]["kind"], "달러")

    def test_kosdaq_inverse_uses_free_money_and_exits(self):
        px = base_px()
        px["229200"] = np.r_[flat(50), np.linspace(100, 110, 10)]
        orders, st, _ = L.step({}, "20261005", px, breadth=80, used=0.6, total=1e7, cash=4e6, held={},
                               now_price=PRICE, is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("251340", "buy")])
        self.assertEqual(orders[0][2], int(1e7 * 0.4 * 0.97 / 100))
        orders, _, _ = L.step(st, "20261006", px, breadth=80, used=0.6, total=1e7, cash=0, held={"251340": orders[0][2]},
                              now_price=dict(PRICE, **{"251340": 101.6}), is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("251340", "sell")])


class InversePriorityTest(unittest.TestCase):
    def test_inverse_first_engine_rests(self):
        # 엔진이 켜질 날(시장 폭 40)이라도 코스닥 과열이면 인버스가 비운 돈을 먼저 쓰고 엔진(돌리기)은 팖
        px = base_px()
        px["229200"] = np.r_[flat(50), np.linspace(100, 110, 10)]
        for c, g in zip(L.ROT, (0.05, 0.02, -0.01, 0.03)):
            px[c] = np.r_[flat(40), np.linspace(100, 100 * (1 + g), 20)]
        state = {"positions": {"133690": {"kind": "돌리기", "price": 100.0, "day": "20261002", "days": 1}}, "last_day": "20261002"}
        orders, st, _ = L.step(state, "20261005", px, breadth=40, used=0.0, total=1e7, cash=5e6, held={"133690": 50000},
                               now_price=PRICE, is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("133690", "sell"), ("251340", "buy")])
        self.assertEqual(orders[1][2], int(1e7 * 0.97 / 100))
        self.assertEqual(set(st["positions"]), {"251340"})


class MakeRoomTest(unittest.TestCase):
    def test_engine_sells_when_rule_needs_cash(self):
        class Fake:
            def __init__(self):
                self.sent = []

            def order(self, code, side, qty):
                self.sent.append((code, side, qty))
                return "1"

            def balance(self):
                return {"cash": 9e6, "value": 1e6, "positions": []}
        with tempfile.TemporaryDirectory() as tmp:
            book, state = Path(tmp) / "b.json", Path(tmp) / "s.json"
            book.write_text(json.dumps({"orders": [], "held": {"133690": 50}}))
            state.write_text(json.dumps({"positions": {"133690": {"kind": "돌리기"}}}))
            bal = {"cash": 1e5, "value": 9.9e6, "positions": [{"code": "133690", "quantity": 50}]}
            with mock.patch.object(P, "IDLE_BOOK", book), mock.patch.object(P, "IDLE_STATE", state), \
                    mock.patch.dict(os.environ, {"PAPER_ROOM_WAIT": "0"}):
                fake = Fake()
                new, lines = P.make_room(fake, bal, need=2e6, now=datetime(2026, 10, 5, 10, 1))
                self.assertEqual(fake.sent, [("133690", "sell", 50)])
                self.assertEqual(new["cash"], 9e6)
                self.assertEqual(json.loads(book.read_text())["held"], {})
                self.assertEqual(json.loads(state.read_text())["positions"], {})
                # 현금이 넉넉하면 안 팖
                book.write_text(json.dumps({"orders": [], "held": {"133690": 50}}))
                fake2 = Fake()
                P.make_room(fake2, {"cash": 5e6, "value": 0, "positions": []}, need=1e6, now=datetime(2026, 10, 5, 10, 1))
                self.assertEqual(fake2.sent, [])


if __name__ == "__main__":
    unittest.main()
