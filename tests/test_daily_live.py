import unittest

import daily_live as D


def pos(kind="추세", price=100.0, 칸=4, days=0, max_close=None, peak=None):
    return {"code": "000001", "name": "가", "kind": kind, "price": price, "칸": 칸, "처음칸": 칸, "days": days,
            "max_close": max_close or price, "peak": peak or price, "bought": "20261001"}


class Size(unittest.TestCase):
    def test_sizes_follow_round_82(self):
        self.assertEqual(D.size_of({"추세문": True}), 4)
        self.assertEqual(D.size_of({"3일연속": True}), 4)
        self.assertEqual(D.size_of({"거래량비": 2.1, "정배열일수": 5}), 3)
        self.assertEqual(D.size_of({"거래량비": 2.1, "정배열일수": 11}), 2)
        self.assertEqual(D.size_of({"거래량비": 1.5, "정배열일수": 3}), 2)


class Exits(unittest.TestCase):
    def test_trend_exits(self):
        self.assertEqual(D.exit_decision(pos(), 113.5, None)[0], 4)
        self.assertEqual(D.exit_decision(pos(), 95, None)[0], 4)
        self.assertEqual(D.exit_decision(pos(days=10), 101, None)[0], 4)
        n, why = D.exit_decision(pos(), 105, None)
        self.assertEqual((n, "절반" in why), (2, True))
        self.assertEqual(D.exit_decision(pos(max_close=106), 105, None), (0, None), "+5%는 처음 닿을 때만 절반")
        self.assertEqual(D.exit_decision(pos(), 103, False), (0, None), "추세 쪽은 정배열 깨짐으로 팔지 않음")

    def test_aligned_exits(self):
        p = pos(kind="정배열", 칸=2)
        self.assertEqual(D.exit_decision(p, 89.5, True)[0], 2)
        self.assertEqual(D.exit_decision(p, 103, False)[0], 2)
        self.assertEqual(D.exit_decision(pos(kind="정배열", peak=109), 100.5, True)[0], 4, "한때 +8% 뒤 +1% 아래")
        self.assertEqual(D.exit_decision(pos(kind="정배열", peak=107), 100.5, True), (0, None), "+8%까지 못 갔으면 아님")
        self.assertEqual(D.exit_decision(p, 140, True), (0, None), "정해진 익절 가격 없음")


class Decide(unittest.TestCase):
    def test_sells_free_slots_and_buys_in_slope_order(self):
        state = {"positions": {"000001": pos(칸=4), "000009": dict(pos(kind="정배열", 칸=4), code="000009")}}
        cands = [{"code": "000002", "name": "나", "추세문": True, "추세 기울기": 1.5},
                 {"code": "000003", "name": "다", "추세 기울기": 3.0, "3일연속": True},
                 {"code": "000004", "name": "라", "추세 기울기": 2.0}]
        sells, buys = D.decide(state, cands, {"000001": 94.0, "000009": 101.0}, {"000009": True}, {}, lambda c, h: True)
        self.assertEqual([x["code"] for x in sells], ["000001"])
        # 남은 칸 = 10 − 4(000009) = 6 → 000003(4칸) · 000004(2칸) · 000002는 칸 없음
        self.assertEqual([(x["code"], x["칸"]) for x in buys], [("000003", 4), ("000004", 2)])

    def test_limit_up_and_kin_and_held_are_skipped(self):
        state = {"positions": {"000001": pos(칸=2)}}
        cands = [{"code": "000001", "name": "가", "추세문": True, "추세 기울기": 9},
                 {"code": "000002", "name": "나", "추세 기울기": 3},
                 {"code": "000003", "name": "다", "추세 기울기": 2},
                 {"code": "000004", "name": "라", "추세 기울기": 1}]
        sells, buys = D.decide(state, cands, {"000001": 101.0}, {}, {"000002": 29.9},
                               lambda c, h: c != "000003")
        self.assertEqual([x["code"] for x in buys], ["000004"])

    def test_limit_down_cannot_sell(self):
        state = {"positions": {"000001": pos(칸=4)}}
        sells, _ = D.decide(state, [], {"000001": 70.0}, {}, {"000001": -30.0}, lambda c, h: True)
        self.assertEqual(sells, [])


class Settle(unittest.TestCase):
    def test_fills_at_close_and_records(self):
        state = {"positions": {"000001": pos(칸=4)}, "closed": []}
        sells = [{"type": "sell", "code": "000001", "칸": 2, "why": "절반 익절", "name": "가", "kind": "추세"}]
        buys = [{"type": "buy", "code": "000002", "칸": 3, "name": "나", "kind": "정배열", "why": "② 정배열 조건"}]
        lines = D.settle(state, "20261002", sells, buys, {"000001": 106.0, "000002": 50_000.0})
        self.assertEqual(state["positions"]["000001"]["칸"], 2)
        self.assertEqual(state["positions"]["000001"]["max_close"], 106.0)
        self.assertEqual(state["positions"]["000001"]["days"], 1)
        self.assertEqual(state["positions"]["000002"]["price"], 50_000.0)
        self.assertEqual(state["closed"][0]["손익"], round(6 - D.COST, 2))
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
