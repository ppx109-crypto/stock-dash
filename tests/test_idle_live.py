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

    @mock.patch.object(L, "DIP_ON", True)       # 2026-10-04 뺀 규칙 · 되살릴 때를 위해 시험은 남김
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

    def test_dip_off_by_default(self):
        # 2026-10-04 사용자 "급락되돌림만 빼줘": 급락 신호가 떠도 069500을 안 사고, 엔진이 켜졌으면 다른 단계(달러 · 돌리기)로
        px = base_px()
        px["069500"] = np.r_[flat(55), [100, 99, 97, 96, 95]]
        orders, _, why = L.step({}, "20261005", px, breadth=30, used=0.6, total=1e7, cash=4e6, held={},
                                now_price=dict(PRICE, **{"069500": 95.0}), is_week_end=False)
        self.assertEqual(orders, [])
        self.assertTrue(any("급락 되돌림은 2026-10-04부터 안 씀" in w for w in why))
        orders, _, _ = L.step({}, "20261005", px, breadth=30, used=0.0, total=1e7, cash=1e7, held={},
                              now_price=dict(PRICE, **{"069500": 95.0}), is_week_end=False)
        self.assertNotIn(("069500", "buy"), [(c, s) for c, s, q, _ in orders])

    @mock.patch.object(L, "DIP_ON", True)
    def test_dip_buys_even_when_rules_use_money(self):
        # 2026-10-04(점검 A11 · 사용자 결정): 규칙이 돈을 60% 써도 시장 폭 < 50이면 남은 40%로 급락 되돌림(연구 i013과 같게)
        px = base_px()
        px["069500"] = np.r_[flat(55), [100, 99, 97, 96, 95]]
        orders, st, _ = L.step({}, "20261005", px, breadth=30, used=0.6, total=1e7, cash=4e6, held={},
                               now_price=dict(PRICE, **{"069500": 95.0}), is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("069500", "buy")])
        self.assertEqual(orders[0][2], int(1e7 * 0.4 * 0.97 / 95))
        # 시장 폭 50 이상이면 안 삼
        orders, _, _ = L.step({}, "20261005", px, breadth=60, used=0.6, total=1e7, cash=4e6, held={},
                              now_price=dict(PRICE, **{"069500": 95.0}), is_week_end=False)
        self.assertEqual(orders, [])

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


class InverseTakeTest(unittest.TestCase):
    """D11b(2026-10-04): 익절 = clip(0.25 × 코스닥150 앞 60일 σ(어제까지) × √10, 1.5%, 2.5%) · 산 날 정해 그 매매 내내."""

    def test_take_bounds_and_ignores_today(self):
        calm = flat(80)
        self.assertEqual(L.inv_take(calm), L.INV_TAKE)                    # 조용하면 바닥 1.5%
        wild = 100 * np.cumprod(np.r_[1, np.tile([1.05, 0.95], 40)])
        self.assertEqual(L.inv_take(wild), L.INV_TAKE_HI)                 # 거칠면 천장 2.5%
        mid = 100 * np.cumprod(np.r_[1, np.tile([1.012, 0.988], 40)])     # σ ≈ 1.2% → 0.25 × 1.2 × √10 ≈ 0.95% → 바닥
        self.assertEqual(L.inv_take(mid), L.INV_TAKE)
        mid2 = 100 * np.cumprod(np.r_[1, np.tile([1.025, 0.975], 40)])   # σ ≈ 2.5% → ≈ 1.98%
        self.assertAlmostEqual(L.inv_take(mid2), 0.25 * 0.025 * np.sqrt(10), places=3)
        # 마지막 값(오늘 15:10)은 재지 않음: 오늘 값을 크게 바꿔도 같음
        self.assertEqual(L.inv_take(np.r_[mid2[:-1], 999.0]), L.inv_take(mid2))
        self.assertEqual(L.inv_take(flat(30)), L.INV_TAKE)                # 자료 모자라면 1.5%

    def test_take_stored_at_buy_and_used_at_exit(self):
        px = base_px()
        wild = 100 * np.cumprod(np.r_[1, np.tile([1.025, 0.975], 40)])
        px["229200"] = np.r_[wild[:-11], wild[-11] * np.linspace(1.0, 1.11, 11)]
        orders, st, _ = L.step({}, "20261005", px, breadth=80, used=0.6, total=1e7, cash=4e6, held={},
                               now_price=PRICE, is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("251340", "buy")])
        take = st["positions"]["251340"]["take"]
        self.assertGreater(take, L.INV_TAKE)
        self.assertLessEqual(take, L.INV_TAKE_HI)
        qty = orders[0][2]
        # +1.6%: 예전(1.5%)이면 익절이지만 이 매매의 폭이 더 넓어 들고 감
        orders, st2, _ = L.step(st, "20261006", px, breadth=80, used=0.6, total=1e7, cash=0, held={"251340": qty},
                                now_price=dict(PRICE, **{"251340": 101.6}), is_week_end=False)
        self.assertEqual(orders, [])
        self.assertEqual(st2["positions"]["251340"]["take"], take)
        # 폭을 넘으면 익절
        orders, _, _ = L.step(st2, "20261007", px, breadth=80, used=0.6, total=1e7, cash=0, held={"251340": qty},
                              now_price=dict(PRICE, **{"251340": 100 * (1 + take) + 0.01}), is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("251340", "sell")])
        # 손절은 그대로 −1.5%
        orders, _, _ = L.step(st2, "20261007", px, breadth=80, used=0.6, total=1e7, cash=0, held={"251340": qty},
                              now_price=dict(PRICE, **{"251340": 98.4}), is_week_end=False)
        self.assertEqual([(c, s) for c, s, q, _ in orders], [("251340", "sell")])

    def test_old_position_without_take_uses_15(self):
        state = {"positions": {"251340": {"kind": "인버스", "price": 100.0, "day": "20261002", "days": 1}}, "last_day": "20261002"}
        orders, _, _ = L.step(state, "20261005", base_px(), breadth=80, used=0.6, total=1e7, cash=0,
                              held={"251340": 10}, now_price=dict(PRICE, **{"251340": 101.6}), is_week_end=False)
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
                # 시장가는 약 1.36배를 묶음 → 현금 500만에 400만을 사려면(544만 필요) 엔진이 비켜야 함(2026-10-06 검토)
                fake3 = Fake()
                P.make_room(fake3, {"cash": 5e6, "value": 0, "positions": [{"code": "133690", "quantity": 50}]}, need=4e6,
                            now=datetime(2026, 10, 5, 10, 1))
                self.assertEqual(fake3.sent, [("133690", "sell", 50)])


if __name__ == "__main__":
    unittest.main()
