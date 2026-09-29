import unittest

import broker_kis
import collect_opinion_history as C


class Spans(unittest.TestCase):
    def test_years(self):
        self.assertEqual(C.spans("20170101", "20190315"),
                         [("20170101", "20171231"), ("20180101", "20181231"), ("20190101", "20190315")])


class Gather(unittest.TestCase):
    def fake(self, days):
        """days: 의견이 나온 날들. 한 번에 3줄까지만 줌."""
        asked = []

        def ask(a, b):
            asked.append((a, b))
            hit = [d for d in days if a <= d <= b]
            return [{"date": d, "member": "x", "target": 1.0} for d in hit[:3]], min(len(hit), 3)
        return ask, asked

    def test_splits_until_everything_fits(self):
        days = ["20170105", "20170106", "20170110", "20170301", "20170601", "20171201", "20171202"]
        ask, asked = self.fake(days)
        rows, n = C.gather(ask, "20170101", "20171231", page=3)
        self.assertEqual(sorted(r["date"] for r in rows), days)
        self.assertEqual(n, len(asked))
        self.assertGreater(n, 1)

    def test_one_ask_when_small(self):
        ask, asked = self.fake(["20170105"])
        rows, n = C.gather(ask, "20170101", "20171231", page=3)
        self.assertEqual((len(rows), n), (1, 1))

    def test_budget(self):
        ask, _ = self.fake(["20170105"] * 5)       # 하루에 3줄 넘게 → 하루짜리에서 멈춤
        rows, n = C.gather(ask, "20170105", "20170105", page=3)
        self.assertEqual(n, 1)
        with self.assertRaises(broker_kis.BrokerError):
            C.gather(ask, "20170101", "20171231", page=3, budget=[2])


if __name__ == "__main__":
    unittest.main()
