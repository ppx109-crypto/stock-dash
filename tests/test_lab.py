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


class Wobble(unittest.TestCase):
    """오차 막대. 이 자가 헐거우면 앞으로의 모든 비교가 헐거워집니다."""

    def setUp(self):
        self.prices = board()
        self.rows = lab.build(self.prices, warmup=120)
        self.holds = lambda r: (r.get("중기 이격") or 0) <= -3.0
        self.exit = lab.exit_fixed(15.0, 7.0, 15)

    def test_the_first_run_is_the_untouched_one(self):
        """흔들지 않은 값도 함께 남깁니다. 그것이 지난 회차와 견줄 수치입니다."""
        plain = lab.run(self.rows, self.prices, self.holds, self.exit, slots=2)
        got = lab.wobble(self.rows, self.prices, self.holds, self.exit,
                         tries=3, slots=2)
        if plain is None or got is None:
            self.skipTest("60건 미만")
        self.assertEqual(got["그대로"], plain["연수익"])

    def test_it_reports_a_spread(self):
        got = lab.wobble(self.rows, self.prices, self.holds, self.exit,
                         tries=4, slots=2)
        if got is None:
            self.skipTest("60건 미만")
        self.assertEqual(got["돌린 수"], 4)
        self.assertLessEqual(got["가장 낮음"], got["연수익"])
        self.assertLessEqual(got["연수익"], got["가장 높음"])
        self.assertAlmostEqual(got["폭"], round(got["가장 높음"] - got["가장 낮음"], 2))

    def test_nudging_by_nothing_changes_nothing(self):
        """흔드는 폭이 0이면 여섯 번 모두 같은 값이어야 합니다."""
        got = lab.wobble(self.rows, self.prices, self.holds, self.exit,
                         tries=4, size=0.0, slots=2)
        if got is None:
            self.skipTest("60건 미만")
        self.assertEqual(got["폭"], 0.0)

    def test_the_nudge_keeps_the_tier_in_front(self):
        """앞자리(층)는 건드리지 않고 마지막 자리만 흔듭니다."""
        rank = lambda r: (2, 0.0)
        nudged = lab.jitter(rank, size=0.5, seed=1)
        got = nudged({"code": "000001", "date": "20200101"})
        self.assertEqual(got[0], 2)
        self.assertNotEqual(got[1], 0.0)
        self.assertLessEqual(abs(got[1]), 0.5)

    def test_the_same_seed_nudges_the_same_way(self):
        row = {"code": "000001", "date": "20200101"}
        first = lab.jitter(lambda r: 0.0, size=0.5, seed=7)(row)
        again = lab.jitter(lambda r: 0.0, size=0.5, seed=7)(row)
        self.assertEqual(first, again)


class Portfolio(unittest.TestCase):
    """앱 화면이 읽는 수치를 내는 함수입니다. 돌아가기만 해도 시험할 값이 있습니다.

    17회차에 이 함수가 깨진 채로 이틀을 갔습니다. 고친 것이 옆 함수에 묻어
    들어갔는데, 아무 시험도 이 함수를 부르지 않아 통과해 버렸습니다.
    """

    def setUp(self):
        self.prices = board()
        self.rows = lab.build(self.prices, warmup=120)

    def test_it_runs_and_counts_trades(self):
        out = lab.portfolio(self.rows, self.prices,
                            lambda r: (r.get("중기 이격") or 0) <= -3.0,
                            slots=2, take=15.0, stop=7.0, limit=15)
        if out is None:
            self.skipTest("60건 미만")
        self.assertGreater(out["매매"], 0)
        self.assertIn("연수익", out)
        self.assertIn("가동률", out)

    def test_nothing_to_buy_gives_nothing(self):
        self.assertIsNone(lab.portfolio(self.rows, self.prices,
                                        lambda r: False, slots=2))


class Drawdown(unittest.TestCase):
    """가장 깊은 골. 한 번의 손실보다 이어지는 손실이 사람을 그만두게 합니다."""

    def setUp(self):
        self.prices = board()
        self.rows = lab.build(self.prices, warmup=120)
        self.holds = lambda r: (r.get("중기 이격") or 0) <= -3.0

    def test_it_is_never_positive(self):
        out = lab.run(self.rows, self.prices, self.holds,
                      lab.exit_fixed(15.0, 7.0, 15), slots=2)
        if out is None:
            self.skipTest("60건 미만")
        self.assertLessEqual(out["최대낙폭"], 0.0)

    def test_it_is_at_least_as_deep_as_the_worst_single_trade(self):
        """한 번의 최악보다 얕을 수는 없습니다. 자리 몫으로 나눈 값입니다."""
        out = lab.run(self.rows, self.prices, self.holds,
                      lab.exit_fixed(15.0, 7.0, 15), slots=2)
        if out is None:
            self.skipTest("60건 미만")
        self.assertLessEqual(out["최대낙폭"], round(out["최악"] / 2, 1) + 0.1)

    def test_winners_only_never_dip(self):
        self.assertEqual(lab.deepest([3.0, 1.0, 5.0], slots=1), 0.0)

    def test_it_measures_from_the_peak_not_from_zero(self):
        """올랐다가 파인 것을 재야 합니다. 처음보다 높아도 골은 골입니다."""
        # 1.10 → 1.056 → 1.02432. 꼭대기 1.10에서 -6.88%입니다.
        self.assertAlmostEqual(lab.deepest([10.0, -4.0, -3.0, 20.0], slots=1),
                               -6.88, places=2)

    def test_a_run_of_losses_is_deeper_than_any_one_of_them(self):
        one = min(lab.deepest([g], slots=1) for g in (-5.0, -6.0, -4.0))
        many = lab.deepest([-5.0, -6.0, -4.0], slots=1)
        self.assertLess(many, one)
        # 0.95 × 0.94 × 0.96 = 0.85728
        self.assertAlmostEqual(many, -14.27, places=2)

    def test_the_slots_divide_it(self):
        """자리를 셋으로 나눴으면 한 매매의 −9%는 지갑의 −3%입니다."""
        self.assertAlmostEqual(lab.deepest([-9.0], slots=3), -3.0)

    def test_the_same_loss_hurts_less_after_a_gain(self):
        """더해 가는 셈이면 같게 나오지만, 지갑에 견주면 뒤의 −10%가 덜 아픕니다."""
        early = lab.deepest([-10.0, 50.0], slots=1)
        late = lab.deepest([50.0, -10.0], slots=1)
        self.assertAlmostEqual(early, -10.0, places=2)
        self.assertAlmostEqual(late, -10.0, places=2)
        self.assertAlmostEqual(lab.deepest([100.0, -10.0], slots=2), -5.0, places=2)

    def test_it_can_never_pass_minus_one_hundred(self):
        """아무리 잃어도 지갑이 0보다 아래로 가지는 않습니다."""
        self.assertGreaterEqual(lab.deepest([-99.0] * 20, slots=1), -100.0)

    def test_order_matters(self):
        """같은 매매라도 진 것이 몰려 오면 더 깊이 파입니다."""
        spread = lab.deepest([-5.0, 6.0, -5.0, 6.0], slots=1)
        bunched = lab.deepest([-5.0, -5.0, 6.0, 6.0], slots=1)
        self.assertLess(bunched, spread)

    def test_the_run_reports_it(self):
        out = lab.run(self.rows, self.prices, self.holds,
                      lab.exit_fixed(15.0, 7.0, 15), slots=2)
        if out is None:
            self.skipTest("60건 미만")
        self.assertLessEqual(out["최대낙폭"], 0.0)
        self.assertLessEqual(out["최대낙폭"], round(out["최악"] / 2, 1) + 0.1)


class Paired(unittest.TestCase):
    """같은 신호에 청산만 갈아 끼우는 셈. 17회차부터 청산 비교의 기본입니다."""

    def setUp(self):
        self.prices = board()
        self.rows = [r for r in lab.build(self.prices, warmup=120)
                     if (r.get("중기 이격") or 0) <= -3.0]

    def test_every_way_sees_the_same_signals(self):
        got = lab.paired(self.rows, self.prices,
                         {"빨리": lab.exit_fixed(5.0, 3.0, 5),
                          "늦게": lab.exit_fixed(30.0, 20.0, 40)})
        if len(got) < 2:
            self.skipTest("60건 미만")
        counts = {one["건수"] for one in got.values()}
        self.assertEqual(len(counts), 1, f"청산마다 건수가 다릅니다: {counts}")

    def test_a_thin_set_gets_no_number(self):
        self.assertEqual(
            lab.paired(self.rows[:59], self.prices,
                       {"아무거나": lab.exit_fixed(15.0, 7.0, 15)}), {})

    def test_holding_longer_shows_up_in_the_days(self):
        got = lab.paired(self.rows, self.prices,
                         {"빨리": lab.exit_fixed(5.0, 3.0, 5),
                          "늦게": lab.exit_fixed(30.0, 20.0, 40)})
        if len(got) < 2:
            self.skipTest("60건 미만")
        self.assertLess(got["빨리"]["보유"], got["늦게"]["보유"])

    def test_the_per_day_number_is_the_mean_over_the_days(self):
        got = lab.paired(self.rows, self.prices,
                         {"하나": lab.exit_fixed(15.0, 7.0, 15)})
        if not got:
            self.skipTest("60건 미만")
        one = got["하나"]
        self.assertAlmostEqual(one["하루당"], round(one["평균"] / one["보유"], 3),
                               places=2)

    def test_the_cost_is_taken_off_once(self):
        """신호 당일에 바로 걸리는 청산으로 왕복 비용이 빠졌는지 봅니다."""
        always = lambda lane, start, price, step, peak, row=None: True
        got = lab.paired(self.rows, self.prices, {"바로": always})
        if not got:
            self.skipTest("60건 미만")
        self.assertEqual(got["바로"]["보유"], 1.0)


class Locked(unittest.TestCase):
    """상한가·하한가에 붙은 날. 실제로는 할 수 없는 매매입니다."""

    def test_the_limit_widened_in_2015(self):
        self.assertEqual(lab.limit_of("20150612"), 0.15)
        self.assertEqual(lab.limit_of("20150615"), 0.30)

    def test_a_jump_to_the_ceiling_counts(self):
        closes = [100.0, 130.0]
        self.assertTrue(lab.locked(closes, ["20200102", "20200103"], 1, 1))
        self.assertFalse(lab.locked(closes, ["20200102", "20200103"], 1, -1))

    def test_a_drop_to_the_floor_counts(self):
        closes = [100.0, 70.0]
        self.assertTrue(lab.locked(closes, ["20200102", "20200103"], 1, -1))
        self.assertFalse(lab.locked(closes, ["20200102", "20200103"], 1, 1))

    def test_an_ordinary_day_does_not(self):
        closes = [100.0, 105.0]
        self.assertFalse(lab.locked(closes, ["20200102", "20200103"], 1, 1))

    def test_the_older_narrower_limit_is_used_before_2015(self):
        closes = [100.0, 118.0]
        self.assertTrue(lab.locked(closes, ["20100102", "20100103"], 1, 1))
        self.assertFalse(lab.locked(closes, ["20200102", "20200103"], 1, 1))

    def test_the_first_day_has_nothing_to_compare(self):
        self.assertFalse(lab.locked([100.0], ["20200102"], 0, 1))


class Kinship(unittest.TestCase):
    """닮은 정도. 그날까지의 수익률만 보고 재야 합니다."""

    def setUp(self):
        self.prices = board()
        self.steps = lab.moves(self.prices)

    def test_a_stock_is_its_own_twin(self):
        row = {"code": "000001", "i": 300}
        self.assertAlmostEqual(lab.kinship(self.steps, row, row), 1.0, places=6)

    def test_it_never_reads_past_the_day(self):
        """그날 뒤의 수익률을 엉뚱하게 바꿔도 값이 같아야 합니다."""
        row = {"code": "000001", "i": 300}
        other = {"code": "000002", "i": 300}
        before = lab.kinship(self.steps, row, other)
        dirty = {code: list(vals) for code, vals in self.steps.items()}
        for code in dirty:
            for k in range(301, len(dirty[code])):
                dirty[code][k] = -7.0 if k % 2 else 3.0
        self.assertAlmostEqual(lab.kinship(dirty, row, other), before, places=9)

    def test_too_early_to_tell_counts_as_not_alike(self):
        row = {"code": "000001", "i": 5}
        other = {"code": "000002", "i": 5}
        self.assertEqual(lab.kinship(self.steps, row, other), 0.0)

    def test_an_unknown_stock_is_not_alike(self):
        self.assertEqual(lab.kinship(self.steps, {"code": "없음", "i": 300},
                                     {"code": "000001", "i": 300}), 0.0)

    def test_nothing_held_means_anything_may_be_bought(self):
        self.assertTrue(lab.unlike(self.steps)({"code": "000001", "i": 300}, []))

    def test_a_twin_is_turned_away(self):
        row = {"code": "000001", "i": 300}
        self.assertFalse(lab.unlike(self.steps, edge=0.6)(row, [row]))


if __name__ == "__main__":
    unittest.main()
