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

    def test_half_take_matches_research(self):
        """연구(nrl.half_rule · lab.run): 4칸의 절반 = 2칸을 들고 있는 칸보다 하나 적게까지 · 1칸이면 안 나눔 · 한 번만."""
        self.assertEqual(D.exit_decision(pos(칸=3), 105, None)[0], 2)
        self.assertEqual(D.exit_decision(pos(칸=2), 105, None)[0], 1)
        self.assertEqual(D.exit_decision(pos(칸=1), 105, None), (0, None))
        halved = dict(pos(칸=2), 처음칸=4)
        self.assertEqual(D.exit_decision(halved, 105, None), (0, None), "15:20 값과 종가가 갈려도 두 번 팔지 않음")


class Kin(unittest.TestCase):
    def test_held_window_ends_on_buy_day_like_research(self):
        import random
        rnd = random.Random(7)
        a = [rnd.gauss(0, 0.02) for _ in range(200)]
        b = [rnd.gauss(0, 0.02) for _ in range(120)] + a[120:]          # 최근 80일은 똑같이 움직임
        steps = {"000001": a, "000002": b}
        idx = {"000001": 199, "000002": 199}
        days = {c: [f"2026{n:04d}" for n in range(200)] for c in steps}
        ok_research = D.kin_checker(steps, idx, days, {"000002": days["000002"][100]})
        ok_today = D.kin_checker(steps, idx, days, {})
        self.assertTrue(ok_research("000001", ["000002"]), "산 날(100번째) 창은 서로 무관 → 담음")
        self.assertFalse(ok_today("000001", ["000002"]), "오늘 창이면 똑같이 움직여 거름")


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

    def test_only_as_many_candidates_as_free_slots_are_looked_at(self):
        """연구(lab.run)처럼 빈 칸 수만큼 위 후보만 봄 — 그중 든 · 상한가면 그 칸은 비워 두고 아래로 내려가지 않음(새 94회차)."""
        state = {"positions": {"000001": pos(칸=4, price=100.0), "000005": dict(pos(kind="정배열", 칸=4), code="000005")}}
        cands = [{"code": "000001", "name": "가", "추세문": True, "추세 기울기": 9},
                 {"code": "000002", "name": "나", "추세 기울기": 8},
                 {"code": "000003", "name": "다", "추세 기울기": 7}]
        sells, buys = D.decide(state, cands, {"000001": 101.0, "000005": 101.0}, {"000005": True}, {"000002": 29.9},
                               lambda c, h: True)
        self.assertEqual(sells, [])
        self.assertEqual(buys, [], "빈 칸 2 → 위 2개(든 것 · 상한가)만 보고 000003까지 내려가지 않음")

    def test_sold_today_can_be_bought_again_like_research(self):
        state = {"positions": {"000001": pos(칸=4, days=9)}}
        cands = [{"code": "000001", "name": "가", "추세문": True, "추세 기울기": 9}]
        sells, buys = D.decide(state, cands, {"000001": 101.0}, {}, {}, lambda c, h: True)
        self.assertEqual([x["code"] for x in sells], ["000001"], "10거래일 기간 청산")
        self.assertEqual([(x["code"], x["칸"]) for x in buys], [("000001", 4)], "다 판 날 종가에 다시 삼(연구와 같음)")

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


class Alerts(unittest.TestCase):
    def test_decision_lines_like_hourly(self):
        sells = [{"type": "sell", "code": "000001", "칸": 2, "why": "절반 익절 +5% 처음 닿음(오늘 +5.2%)", "name": "가", "kind": "추세"}]
        buys = [{"type": "buy", "code": "000002", "칸": 3, "name": "나", "kind": "정배열", "why": "② 정배열 조건"}]
        lines = D.decision_lines("20261002", 55.0, [{}, {}], sells, buys, {"000001": 105.2, "000002": 50000.0}, {"000001": {}})
        self.assertIn("15:20 판단", lines[0])
        self.assertTrue(lines[1].startswith("🟡 절반 익절"))
        self.assertTrue(lines[2].startswith("🟢 매수") and "3칸(30%)" in lines[2] and "50,000원" in lines[2])
        self.assertIn("사고팔 것이 없어요", D.decision_lines("20261002", 40.0, [], [], [], {}, {})[-1])


if __name__ == "__main__":
    unittest.main()
