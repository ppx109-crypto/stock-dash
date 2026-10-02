import unittest

import m15_live as L


def bars(rows):
    return {"t": [r[0] for r in rows], "o": [r[1] for r in rows], "c": [r[2] for r in rows]}


class Clock(unittest.TestCase):
    def test_bars_and_close_times(self):
        self.assertEqual(len(L.BARS), 26)
        self.assertEqual((L.BARS[0], L.BARS[-1]), ("0900", "1515"))
        self.assertEqual(L.close_at("0900"), "0915")
        self.assertEqual(L.close_at("1045"), "1100")
        self.assertEqual(L.close_at("1515"), "1530")


class Parts(unittest.TestCase):
    def test_day_ret_from_first_open(self):
        b = bars([("202610010900", 90, 95), ("202610020900", 100, 101), ("202610020915", 101, 103)])
        self.assertAlmostEqual(L.day_ret(b, "202610020915"), 0.03)

    def test_exits_scale_by_four(self):
        p = {"price": 100.0, "peak": 100.0, "칸": 4, "처음칸": 4, "bars": 239, "kind": "추세"}
        self.assertEqual(L.exit_decision(p, 101, 101)[0], 0)
        self.assertEqual(L.exit_decision(dict(p, bars=240), 101, 101)[0], 4)
        self.assertTrue(L.stale(dict(p, bars=28), 102, 50))
        self.assertFalse(L.stale(dict(p, bars=27), 102, 50))


class Step(unittest.TestCase):
    def setUp(self):
        self.plan = {"candidates": [{"code": "000001", "name": "가", "추세문": True}], "breadth": 60}
        closes = [100 + i * 0.1 for i in range(400)]
        t = [f"20260930{h:02d}{m:02d}" for h in range(9, 16) for m in (0, 15, 30, 45) if (h, m) <= (15, 15)]
        self.t = (t * 20)[:399] + ["202610021045"]
        self.closes = closes

    def run_bar(self, dr_up=False, market=None):
        b = {"t": self.t, "o": [100.0] * 399 + [100.0], "c": self.closes[:399] + [103.0 if dr_up else 100.5]}
        state = {"positions": {}, "pending": []}
        L.step(state, self.plan, {"000001": b}, "202610021045", {}, lambda *a: None, market=market)
        return state

    def test_noon_bar_buys_next_open(self):
        st = self.run_bar()
        self.assertEqual([(x["code"], x["칸"]) for x in st["pending"]], [("000001", 4)])

    def test_filters_skip_without_using_the_day(self):
        st = self.run_bar(dr_up=True)
        self.assertEqual(st["pending"], [], "그날 +2% 넘게 오르면 안 삼")
        self.assertEqual(st["seen"]["20261002"], [], "걸러진 신호는 그날 기회를 쓰지 않음")
        self.assertEqual(self.run_bar(market=-0.02)["pending"], [], "시장 −1% 아래면 안 삼")

    def test_fill_at_next_open(self):
        st = self.run_bar()
        done = L.fill(st, "202610021100", {"000001": 101.0})
        self.assertEqual(len(done), 1)
        self.assertEqual(st["positions"]["000001"]["price"], 101.0)


if __name__ == "__main__":
    unittest.main()
