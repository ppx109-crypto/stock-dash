import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import basket_live as B
import paper_trade as P

DAYS = [f"2026{m:02d}{d:02d}" for m in (8, 9, 10) for d in range(1, 29)]


def since(today):
    pos = {d: i for i, d in enumerate(DAYS)}
    return lambda d: pos[today] - pos[d]


def run_step(state=None, day="20261006", t0="20261005", ev=(), react=None, inside=None, held=None, price=None,
             capital=1e7, avail=1e7):
    return B.step(state or {}, day, t0, since(day), list(ev), react or {}, inside if inside is not None else {"A", "B", "C"},
                  held or {}, price or {"A": 1000.0, "B": 1000.0, "C": 1000.0}, capital, avail)


class StepTest(unittest.TestCase):
    def test_buyback_needs_drop_bonus_always(self):
        orders, st, why = run_step(ev=[("A", "자사주취득"), ("B", "자사주취득"), ("C", "무상증자")],
                                   react={"A": -0.03, "B": -0.01, "C": 0.05})
        self.assertEqual([(c, s) for c, s, *_ in orders], [("A", "buy"), ("C", "buy")])
        self.assertEqual(orders[0][2], 1940)                 # 1천만 ÷ 5칸 × 0.97 ÷ 1000원
        self.assertIn("A", st["positions"])
        self.assertTrue(any("−2% 아래만" in w for w in why))

    def test_outside_top200_and_missing_reaction_skip(self):
        orders, st, _ = run_step(ev=[("A", "자사주취득"), ("B", "무상증자")], react={"A": -0.05}, inside={"B"})
        self.assertEqual(orders, [])
        self.assertNotIn("A:자사주취득", st["last"])         # 200위 밖 사건은 '앞 사건'으로 안 남김

    def test_sell_after_20_days(self):
        st = {"positions": {"A": {"day": "20260901", "price": 900.0, "kind": "무상증자"}}}
        orders, new, _ = run_step(state=st, day="20260921", held={"A": 10})     # 20거래일째
        self.assertEqual(orders[0][:3], ("A", "sell", 10))
        self.assertEqual(new["positions"], {})
        orders, new, _ = run_step(state=st, day="20260920", held={"A": 10})     # 19거래일째는 들고 있음
        self.assertEqual(orders, [])

    def test_five_slots_and_no_double(self):
        st = {"positions": {c: {"day": "20261001", "price": 1.0, "kind": "무상증자"} for c in ("P", "Q", "R", "S", "T")}}
        held = {c: 1 for c in "PQRST"}
        orders, _, why = run_step(state=st, held=held, ev=[("C", "무상증자")], react={"C": 0.0})
        self.assertEqual(orders, [])
        self.assertTrue(any("5칸" in w for w in why))

    def test_same_event_within_20_days_skipped(self):
        st = {"last": {"C:무상증자": "20260920"}}
        orders, _, _ = run_step(state=st, ev=[("C", "무상증자")], react={"C": 0.0})
        self.assertEqual(orders, [])
        st = {"last": {"C:무상증자": "20260901"}}
        orders, _, _ = run_step(state=st, ev=[("C", "무상증자")], react={"C": 0.0})
        self.assertEqual(len(orders), 1)

    def test_cash_limits_buy(self):
        orders, _, why = run_step(ev=[("C", "무상증자")], react={"C": 0.0}, avail=500.0)
        self.assertEqual(orders, [])
        self.assertTrue(any("모자람" in w for w in why))

    def test_dropped_from_book_leaves_state(self):
        st = {"positions": {"A": {"day": "20261001", "price": 1.0, "kind": "무상증자"}}}
        _, new, _ = run_step(state=st, held={})
        self.assertEqual(new["positions"], {})

    def test_events_window_includes_weekend_filing(self):
        ev = {"A": [("20261003", "무상증자"), ("20261001", "자사주취득")], "B": [("20261005", "자사주취득"), ("20261005", "배당")]}
        self.assertEqual(B.todays_events(ev, "20261005", "20261002"), [("A", "무상증자"), ("B", "자사주취득")])

    def test_reactions_subtract_top_median(self):
        prices = {f"{i:06d}": {"rows": [("20261002", 100.0), ("20261005", 100.0 + i)]} for i in range(50)}
        with mock.patch("caps.known_by", return_value=1000):
            react, inside = B.reactions(prices, "20261005", "20261002", top=200)
        self.assertEqual(len(inside), 50)
        self.assertAlmostEqual(react["000049"], 0.49 - 0.245, places=6)


class RoomTest(unittest.TestCase):
    def test_engine_first_then_basket_oldest(self):
        class Fake:
            def __init__(self, cash_after):
                self.sent, self.cash_after = [], cash_after

            def order(self, code, side, qty):
                self.sent.append((code, side, qty))
                return "1"

            def balance(self):
                return {"cash": self.cash_after, "value": 0, "positions": [{"code": "X", "quantity": 5, "price": 1e5},
                                                                          {"code": "Y", "quantity": 5, "price": 1e5}]}
        with tempfile.TemporaryDirectory() as tmp:
            ib, is_, bb, bs = (Path(tmp) / n for n in ("ib.json", "is.json", "bb.json", "bs.json"))
            ib.write_text(json.dumps({"orders": [], "held": {"133690": 50}}))
            is_.write_text(json.dumps({"positions": {"133690": {"kind": "돌리기"}}}))
            bb.write_text(json.dumps({"orders": [], "held": {"X": 5, "Y": 5}}))
            bs.write_text(json.dumps({"positions": {"X": {"day": "20261002"}, "Y": {"day": "20260930"}}}))
            with mock.patch.object(P, "IDLE_BOOK", ib), mock.patch.object(P, "IDLE_STATE", is_), \
                    mock.patch.object(P, "BASKET_BOOK", bb), mock.patch.object(P, "BASKET_STATE", bs), \
                    mock.patch.dict(os.environ, {"PAPER_ROOM_WAIT": "0"}):
                # 엔진을 판 뒤 현금 100만 → 규칙이 80만(×1.36 = 108.8만)이 필요 → 바구니 가장 오래된 Y(50만)만 팖
                fake = Fake(1e6)
                bal = {"cash": 1e5, "value": 0, "positions": [{"code": "133690", "quantity": 50},
                                                              {"code": "X", "quantity": 5, "price": 1e5},
                                                              {"code": "Y", "quantity": 5, "price": 1e5}]}
                _, lines = P.make_room(fake, bal, need=8e5, now=datetime(2026, 10, 7, 15, 20))
                self.assertEqual(fake.sent, [("133690", "sell", 50), ("Y", "sell", 5)])
                self.assertEqual(json.loads(bb.read_text())["held"], {"X": 5})
                self.assertEqual(list(json.loads(bs.read_text())["positions"]), ["X"])
                self.assertTrue(any("사건 바구니" in x for x in lines))
                # 엔진을 판 돈으로 넉넉하면 바구니는 안 팖
                ib.write_text(json.dumps({"orders": [], "held": {"133690": 50}}))
                fake2 = Fake(5e6)
                P.make_room(fake2, bal, need=8e5, now=datetime(2026, 10, 7, 15, 20))
                self.assertEqual(fake2.sent, [("133690", "sell", 50)])


if __name__ == "__main__":
    unittest.main()
