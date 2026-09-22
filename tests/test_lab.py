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


class Slots(unittest.TestCase):
    """자리를 어떻게 쓰는지. 여기가 바뀌면 지난 회차 수치가 전부 흔들립니다."""

    def setUp(self):
        self.prices = board()

    def test_the_default_leaves_the_slot_empty(self):
        """1등 후보를 이미 들고 있으면 그 자리는 그날 비워 둡니다.

        자리 둘, 후보 둘입니다. 1등은 어제 이미 산 종목이라 살 수 없습니다.
        기본은 남은 한 자리를 비워 두고, greedy는 2등으로 마저 채웁니다.
        이 한 줄 차이가 확인 구간 연수익을 +23.51%에서 +13.22%로 바꿉니다.
        """
        days = [f"2020{(k // 21) + 1:02d}{(k % 21) + 1:02d}" for k in range(200)]
        prices = {code: {"name": code, "rows": [(d, 100.0) for d in days]}
                  for code in ("000001", "000002", "000003")}
        rows = [{"code": "000001", "date": days[150], "i": 150, "price": 100.0, "값": 1},
                {"code": "000001", "date": days[151], "i": 151, "price": 100.0, "값": 1},
                {"code": "000002", "date": days[151], "i": 151, "price": 100.0, "값": 2},
                # 하루 더 돌게 하는 들러리입니다. 이날 열린 자리를 세어 봅니다.
                {"code": "000003", "date": days[160], "i": 160, "price": 100.0, "값": 3}]

        def held(greedy):
            """마지막 날에 실제로 들고 있던 종목을 모읍니다."""
            seen = set()

            def exit_at(lane, start, price, step, peak, row=None):
                seen.add(row["code"])
                return False

            lab.run(rows, prices, lambda r: True, exit_at, slots=2,
                    rank=lambda r: r["값"], greedy=greedy)
            return seen

        self.assertEqual(held(False), {"000001"}, "기본인데 2등까지 샀습니다")
        self.assertEqual(held(True), {"000001", "000002"},
                         "greedy인데 빈 자리를 채우지 않았습니다")

    def test_a_bigger_position_takes_more_room(self):
        """한 종목에 두 자리를 주면 같은 때 들고 있는 종목 수가 줄어듭니다."""
        rows, plain = plan(self.prices, detail=True)
        rows, doubled = plan(self.prices, detail=True, size=lambda r: 2)
        if plain is None or doubled is None:
            self.skipTest("60건 미만")
        self.assertTrue(all(g["자리"] == 2 for g in doubled["매매목록"]))
        self.assertLess(doubled["매매"], plain["매매"])

    def test_two_slots_count_double_in_the_yearly_number(self):
        """자리를 둘 쓴 매매는 손익도 두 몫으로 셉니다. 매매당은 그대로입니다."""
        rows, out = plan(self.prices, detail=True, size=lambda r: 2)
        if out is None:
            self.skipTest("60건 미만")
        gains = [g["손익"] for g in out["매매목록"]]
        self.assertAlmostEqual(out["평균"], round(sum(gains) / len(gains), 2), places=1)
        years = int(max(g["판 날"] for g in out["매매목록"])[:4]) - \
            int(min(g["산 날"] for g in out["매매목록"])[:4]) + 1
        self.assertAlmostEqual(out["연수익"], round(sum(gains) * 2 / 2 / years, 2),
                               places=1)

    def test_a_position_never_takes_more_room_than_there_is(self):
        rows, out = plan(self.prices, detail=True, size=lambda r: 5)
        if out is None:
            self.skipTest("60건 미만")
        self.assertTrue(all(g["자리"] <= 2 for g in out["매매목록"]))


if __name__ == "__main__":
    unittest.main()
