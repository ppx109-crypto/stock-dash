import unittest

import hourly_a as A


def cand(code, trend=False, steady=False, flow5=0.1, r20=0.1):
    return {"code": code, "name": "종목" + code, "추세문": trend, "3일연속": steady, "flow5": flow5, "r20": r20}


def rising(n, start=100.0, step=0.2):
    return [start + i * step for i in range(n)]


class Parts(unittest.TestCase):
    def test_ema_waits_span(self):
        got = A.ema([1.0] * 10, 5)
        self.assertEqual(got[:5], [None] * 5)
        self.assertAlmostEqual(got[9], 1.0)

    def test_aligned_needs_history_and_order(self):
        up = A.aligned_series(rising(300))
        self.assertFalse(up[100])          # 180봉 선이 아직 없음
        self.assertTrue(up[-1])
        self.assertFalse(A.aligned_series(list(reversed(rising(300))))[-1])

    def test_order_tiers_prefers_weak_flow_and_strong_return(self):
        got = A.order_tiers({"a": {"flow5": 0.1, "r20": 0.3}, "b": {"flow5": 0.5, "r20": 0.2}, "c": {"flow5": 0.9, "r20": 0.1}})
        self.assertEqual(got["a"], 4)
        self.assertEqual(got["c"], 0)
        self.assertEqual(A.order_tiers({"a": {"flow5": None, "r20": None}}), {"a": 2})

    def test_exits(self):
        base = {"price": 100.0, "peak": 100.0, "칸": 4, "처음칸": 4, "bars": 3, "kind": "추세"}
        self.assertEqual(A.exit_decision(base, 105.5, 103.0)[0], 2)       # +5% 처음 → 절반
        self.assertEqual(A.exit_decision(base, 105.5, 106.0)[0], 0)       # 이미 +5%를 넘었던 뒤
        self.assertEqual(A.exit_decision(base, 113.5, 110.0)[0], 4)       # +13% 전량
        self.assertEqual(A.exit_decision(base, 94.9, 100.0)[0], 4)        # −5%
        self.assertEqual(A.exit_decision({**base, "bars": 60}, 101.0, 102.0)[0], 4)
        line = {"price": 100.0, "peak": 109.0, "칸": 2, "처음칸": 2, "bars": 20, "kind": "정배열"}
        self.assertEqual(A.exit_decision(line, 100.5, 108.0)[0], 2)       # 본전 지키기
        self.assertEqual(A.exit_decision({**line, "peak": 103.0}, 89.9, 103.0)[0], 2)   # −10%
        self.assertEqual(A.exit_decision({**line, "peak": 103.0}, 95.0, 103.0)[0], 0)

    def test_stale(self):
        p = {"bars": 8, "price": 100.0}
        self.assertTrue(A.stale(p, 102.0, 60))
        self.assertFalse(A.stale(p, 105.0, 60))
        self.assertFalse(A.stale(p, 102.0, 95))
        self.assertFalse(A.stale({**p, "bars": 5}, 102.0, 60))


class Flow(unittest.TestCase):
    def bars(self, codes, n=300):
        day = "20260105"
        t = [f"2025{(i // 6) % 12 + 1:02d}{(i // 72) + 1:02d}{A.HOURS[i % 6]}" for i in range(n - 6)]
        t += [day + hh for hh in A.HOURS]
        return {c: {"t": t, "c": list(reversed(rising(n)))} for c in codes}, day      # 내려가는 흐름 → 정배열 신호 없음

    def test_noon_fallback_buys_by_order_and_marks_day_seen(self):
        bars, day = self.bars(["000001", "000002"])
        plan = {"breadth": 60, "candidates": [cand("000001", flow5=0.9, r20=0.0), cand("000002", flow5=0.1, r20=0.3)]}
        state, logs = {"positions": {}, "pending": []}, []
        for hh in ("09", "10"):
            A.step(state, plan, bars, day + hh, {}, lambda k, t, e: logs.append(k))
        self.assertEqual(state["pending"], [])
        A.step(state, plan, bars, day + "11", {"000001": 100.0, "000002": 50.0}, lambda k, t, e: logs.append(k))
        buys = [x for x in state["pending"] if x["type"] == "buy"]
        self.assertEqual([x["code"] for x in buys], ["000002", "000001"])      # 덜 몰리고 오른 것 먼저
        self.assertEqual(sorted(state["seen"][day]), ["000001", "000002"])
        A.fill(state, day + "12", {"000001": 100.0, "000002": 50.0})
        self.assertEqual(set(state["positions"]), {"000001", "000002"})
        self.assertEqual(state["positions"]["000001"]["bars"], -1)             # 산 봉이 닫히면 0

    def test_swap_when_full(self):
        bars, day = self.bars(["000009", "000001"])
        state = {"positions": {}, "pending": []}
        for i in range(5):
            code = f"10000{i}"
            state["positions"][code] = {"code": code, "name": code, "kind": "정배열", "price": 100.0, "peak": 101.0,
                                        "칸": 2, "처음칸": 2, "bars": 10, "last_close": 100.0 + i, "max_close": 101.0, "bought": "2025123111"}
        plan = {"breadth": 60, "candidates": [cand("000009", trend=True)]}
        logs = []
        A.step(state, plan, bars, day + "11", {}, lambda k, t, e: logs.append((k, t)))
        kinds = [k for k, _ in logs]
        self.assertIn("자리 바꾸기", kinds)
        sells = [x for x in state["pending"] if x["type"] == "sell"]
        self.assertEqual([x["code"] for x in sells], ["100000", "100001"])   # 손익 나쁜 것부터 4칸만큼
        self.assertEqual([x["칸"] for x in state["pending"] if x["type"] == "buy"], [4])
        A.fill(state, day + "12", {"100000": 99.0, "100001": 99.0, "000009": 10.0})
        self.assertNotIn("100000", state["positions"])
        self.assertIn("000009", state["positions"])
        self.assertEqual(len(state["closed"]), 2)

    def test_half_take_then_rest(self):
        bars, day = self.bars(["000001"])
        bars["000001"]["c"][-6] = 106.0          # 09시 봉 종가 +6%
        state = {"positions": {"000001": {"code": "000001", "name": "a", "kind": "추세", "price": 100.0, "peak": 100.0,
                                          "칸": 4, "처음칸": 4, "bars": 1, "max_close": 101.0, "bought": "2025123111"}}, "pending": []}
        logs = []
        A.step(state, {"candidates": []}, bars, day + "09", {}, lambda k, t, e: logs.append(k))
        self.assertEqual(logs, ["절반 익절"])
        self.assertEqual(state["pending"][0]["칸"], 2)
        A.fill(state, day + "10", {"000001": 106.0})
        self.assertEqual(state["positions"]["000001"]["칸"], 2)
        self.assertEqual(state["closed"][0]["칸"], 2)


if __name__ == "__main__":
    unittest.main()
