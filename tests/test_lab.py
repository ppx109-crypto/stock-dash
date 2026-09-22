"""매매 시뮬레이터가 시킨 대로 하는지 봅니다.

재진입 금지와 매매 장부는 이번 회차에 붙인 것입니다. 장부가 실제 매매와
어긋나면 뒤의 모든 분석이 어긋나므로, 둘이 같은 것을 세는지 확인합니다.
"""
import unittest

import lab


def wave(n=1400, tilt=0.03):
    """오르내림이 반복되어 같은 종목이 여러 번 걸리는 흐름입니다."""
    found = []
    price = 100.0
    for i in range(n):
        price *= (1 + tilt) if (i // 10) % 2 else (1 - tilt + 0.001)
        found.append((f"{2000 + i // 250:04d}{(i % 250) // 21 + 1:02d}{(i % 21) + 1:02d}",
                      price))
    return found


def board(count=6):
    return {f"00000{k}": {"name": f"종목{k}", "rows": wave(tilt=0.025 + k / 400)}
            for k in range(count)}


def plan(prices, **kw):
    rows = lab.build(prices, warmup=120)
    return rows, lab.run(rows, prices, lambda r: (r.get("중기 이격") or 0) <= -3.0,
                         lab.exit_fixed(15.0, 7.0, 15), slots=2, **kw)


class Ledger(unittest.TestCase):

    def setUp(self):
        self.prices = board()

    def test_the_ledger_counts_the_same_trades(self):
        rows, out = plan(self.prices, detail=True)
        if out is None:
            self.skipTest("60건 미만이라 시뮬레이터가 결론을 내지 않았습니다")
        self.assertEqual(len(out["매매목록"]), out["매매"])
        self.assertAlmostEqual(
            round(sum(g["손익"] for g in out["매매목록"]) / out["매매"], 1),
            round(out["평균"], 1), places=1)

    def test_no_ledger_unless_asked(self):
        rows, out = plan(self.prices)
        if out is None:
            self.skipTest("60건 미만")
        self.assertNotIn("매매목록", out)

    def test_the_ledger_sells_after_it_buys(self):
        rows, out = plan(self.prices, detail=True)
        if out is None:
            self.skipTest("60건 미만")
        for got in out["매매목록"]:
            self.assertGreater(got["판 날"], got["산 날"])
            self.assertGreater(got["들고"], 0)


class Cooldown(unittest.TestCase):

    def setUp(self):
        self.prices = board()

    def test_a_rest_period_keeps_the_stock_out(self):
        """나간 뒤 쉬게 하면 같은 종목을 곧바로 다시 사지 않습니다."""
        rows, plain = plan(self.prices, detail=True)
        rows, rested = plan(self.prices, detail=True, cooldown=40)
        if plain is None or rested is None:
            self.skipTest("60건 미만")
        def gaps(out):
            seen = {}
            found = []
            for got in sorted(out["매매목록"], key=lambda g: g["산 날"]):
                if got["code"] in seen:
                    found.append(got["행"]["i"] - seen[got["code"]])
                seen[got["code"]] = got["행"]["i"] + got["들고"]
            return found
        self.assertTrue(gaps(plain), "다시 산 적이 없어 시험이 되지 않습니다")
        self.assertTrue(all(gap >= 40 for gap in gaps(rested)),
                        f"쉬어야 할 기간 안에 다시 샀습니다: {gaps(rested)}")

    def test_resting_only_after_a_loss_still_lets_winners_back(self):
        rows, out = plan(self.prices, detail=True, cooldown=40, cooldown_after="손실")
        if out is None:
            self.skipTest("60건 미만")
        seen, broke = {}, []
        for got in sorted(out["매매목록"], key=lambda g: g["산 날"]):
            was = seen.get(got["code"])
            if was and was["손익"] <= 0 and got["행"]["i"] - (was["행"]["i"] + was["들고"]) < 40:
                broke.append(got)
            seen[got["code"]] = got
        self.assertEqual(broke, [], "잃고 나온 뒤인데 쉬지 않고 다시 샀습니다")


if __name__ == "__main__":
    unittest.main()
