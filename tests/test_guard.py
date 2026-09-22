"""미래참조 검사기가 정말로 잡아내는지 봅니다.

검사가 늘 통과하기만 하면 검사가 아니라 도장입니다. 그래서 일부러 뒷날을
보는 값을 넣어 두고, 네 겹이 각각 그것을 잡아내는지 확인합니다.

넷째 겹은 가로줄입니다. 그날 온 종목을 견주어 만든 값은 한 종목만 떼어
다시 만들 수가 없어 앞의 두 겹이 닿지 않습니다. 그 면제를 악용해 뒷날을
섞어 넣으면 어떻게 되는지도 여기서 확인합니다.
"""
import unittest
from unittest.mock import patch

import guard
import lab


def series(n=400, start=100.0, step=0.004):
    return [(f"{2000 + i // 250:04d}{(i % 250) // 21 + 1:02d}{(i % 21) + 1:02d}",
             start * (1 + step) ** i) for i in range(n)]


def prices(rows=None):
    return {"005930": {"name": "테스트", "rows": rows or series()}}


class GuardCatches(unittest.TestCase):
    """일부러 넣은 미래참조를 네 겹이 각각 잡아내야 합니다."""

    def setUp(self):
        self.prices = prices()
        patcher = patch.object(lab.study, "money_timeline", return_value=[])
        patcher.start(); self.addCleanup(patcher.stop)
        patcher2 = patch.object(lab.study, "target_timeline", return_value=[])
        patcher2.start(); self.addCleanup(patcher2.stop)
        self.rows = lab.build(self.prices, warmup=120)

    def test_clean_features_pass_all_three(self):
        found = guard.verify(self.prices, self.rows, samples=5, loud=False)
        self.assertEqual(found["corruption"], 5)
        self.assertEqual(found["truncation"], 5)

    def test_a_feature_that_reads_tomorrow_is_caught_by_corruption(self):
        real = lab.build

        def peeking(prices_in, horizons=(5, 20, 60), warmup=120):
            rows = real(prices_in, horizons=horizons, warmup=warmup)
            closes = [c for _, c in list(prices_in.values())[0]["rows"]]
            for row in rows:
                spot = row["i"]
                # 딱 하루만 앞을 봅니다. 사람 눈에는 티가 나지 않습니다.
                if spot + 1 < len(closes):
                    row["엿본값"] = closes[spot + 1]
            return rows

        with patch.object(lab, "build", side_effect=peeking):
            rows = peeking(self.prices)
            with self.assertRaises(guard.LookaheadError) as caught:
                guard.check_corruption(self.prices, rows, samples=5)
        self.assertIn("엿본값", str(caught.exception))

    def test_a_feature_built_from_the_whole_series_is_caught(self):
        real = lab.build

        def whole(prices_in, horizons=(5, 20, 60), warmup=120):
            rows = real(prices_in, horizons=horizons, warmup=warmup)
            closes = [c for _, c in list(prices_in.values())[0]["rows"]]
            best = max(closes)          # 전 기간 최고가는 그날 알 수 없습니다.
            for row in rows:
                row["전고점대비"] = (row["price"] / best - 1) * 100
            return rows

        with patch.object(lab, "build", side_effect=whole):
            rows = whole(self.prices)
            with self.assertRaises(guard.LookaheadError) as caught:
                guard.check_corruption(self.prices, rows, samples=5)
        self.assertIn("전고점대비", str(caught.exception))

    def test_truncation_catches_it_too(self):
        real = lab.build

        def whole(prices_in, horizons=(5, 20, 60), warmup=120):
            rows = real(prices_in, horizons=horizons, warmup=warmup)
            closes = [c for _, c in list(prices_in.values())[0]["rows"]]
            best = max(closes)
            for row in rows:
                row["전고점대비"] = (row["price"] / best - 1) * 100
            return rows

        with patch.object(lab, "build", side_effect=whole):
            rows = whole(self.prices)
            with self.assertRaises(guard.LookaheadError):
                guard.check_truncation(self.prices, rows, samples=5)

    def test_the_forward_return_itself_is_not_flagged(self):
        # ahead는 뒷날을 보라고 만든 값입니다. 여기에 걸리면 안 됩니다.
        guard.check_corruption(self.prices, self.rows, samples=5)


class DateCheck(unittest.TestCase):
    """발표일보다 앞선 날에 실적이 붙어 있으면 잡아야 합니다."""

    def test_financials_before_any_filing_are_caught(self):
        rows = [{"code": "005930", "date": "20200101", "매출성장": 10.0}]
        with patch.object(guard.study, "money_timeline",
                          return_value=[("20250311", {"매출성장": 10.0})]):
            with self.assertRaises(guard.LookaheadError):
                guard.check_dates(rows)

    def test_targets_before_any_opinion_are_caught(self):
        rows = [{"code": "005930", "date": "20200101", "목표가괴리": 20.0}]
        with patch.object(guard.study, "money_timeline", return_value=[]), \
             patch.object(guard.study, "target_timeline",
                          return_value=[("20250311", {"목표가": 100.0})]):
            with self.assertRaises(guard.LookaheadError):
                guard.check_dates(rows)

    def test_a_filing_on_or_before_the_day_is_fine(self):
        rows = [{"code": "005930", "date": "20260101", "매출성장": 10.0}]
        with patch.object(guard.study, "money_timeline",
                          return_value=[("20250311", {"매출성장": 10.0})]):
            self.assertEqual(guard.check_dates(rows), 1)


def many(count=6, n=400):
    """가로로 견주려면 같은 날에 여러 종목이 있어야 합니다."""
    found = {}
    for k in range(count):
        found[f"00{k}930"] = {"name": f"테스트{k}",
                              "rows": series(n, start=100.0 + k, step=0.003 + k / 5000)}
    return found


class CrossSectionGuard(unittest.TestCase):
    """가로줄 값은 넷째 겹이 맡습니다. 면제만 해 주고 끝나면 안 됩니다."""

    def setUp(self):
        self.prices = many()
        patcher = patch.object(lab.study, "money_timeline", return_value=[])
        patcher.start(); self.addCleanup(patcher.stop)
        patcher2 = patch.object(lab.study, "target_timeline", return_value=[])
        patcher2.start(); self.addCleanup(patcher2.stop)
        self.rows = lab.build(self.prices, warmup=120)

    def test_the_real_market_gap_passes(self):
        lab.market_relative(self.rows)
        found = guard.check_cross_section(self.rows, samples=2)
        for name in guard.CROSS:
            self.assertGreater(found[name], 0, f"{name}을 아무도 짚지 않았습니다")

    def test_a_market_gap_that_reads_tomorrow_is_caught(self):
        """그날이 아니라 그다음 날의 가로 중앙값을 쓰면 잡혀야 합니다."""
        lab.market_relative(self.rows)
        days = sorted({row["date"] for row in self.rows})
        after = {day: days[k + 1] for k, day in enumerate(days[:-1])}
        middle = {}
        for row in self.rows:
            middle.setdefault(row["date"], []).append(row.get("중기 이격") or 0.0)
        middle = {day: sorted(vals)[len(vals) // 2] for day, vals in middle.items()}
        for row in self.rows:
            tomorrow = after.get(row["date"])
            if tomorrow is not None:
                row["시장 이격"] = middle[tomorrow]
        with self.assertRaises(guard.LookaheadError) as caught:
            guard.check_cross_section(self.rows, samples=2)
        self.assertIn("시장 이격", str(caught.exception))

    def test_an_unchecked_cross_column_stops_verify(self):
        """CROSS에 이름만 올리고 검사를 지나지 않으면 verify가 멈춰야 합니다."""
        for row in self.rows:
            row["시장 이격"] = 1.0
            row["상대 이격"] = 1.0
        with patch.object(guard, "check_cross_section",
                          return_value={name: 0 for name in guard.CROSS}):
            with self.assertRaises(guard.LookaheadError) as caught:
                guard.verify(self.prices, self.rows, samples=2, loud=False)
        self.assertIn("어느 검사도 지나지 않았습니다", str(caught.exception))


class FilingGuard(unittest.TestCase):
    """공시는 접수일에 공개됩니다. 그 뒤의 것을 붙이면 멈춰야 합니다."""

    def setUp(self):
        patcher = patch.object(guard.events, "timeline",
                               return_value=(("20200110", "자사주취득"),
                                             ("20200320", "유상증자")))
        patcher.start(); self.addCleanup(patcher.stop)

    def test_a_filing_from_before_the_day_is_fine(self):
        rows = [{"code": "005930", "date": "20200115",
                 guard.events.MARK: ["자사주취득"], guard.events.AGE: 5}]
        self.assertGreater(guard.check_filings(rows), 0)

    def test_a_filing_from_after_the_day_is_caught(self):
        """3월 공시를 1월의 신호에 붙여 놓으면 잡아야 합니다."""
        rows = [{"code": "005930", "date": "20200115",
                 guard.events.MARK: ["유상증자"], guard.events.AGE: 5}]
        with self.assertRaises(guard.LookaheadError) as caught:
            guard.check_filings(rows)
        self.assertIn("유상증자", str(caught.exception))

    def test_a_filing_too_far_back_is_caught(self):
        """창 밖의 공시를 '최근'이라고 붙여도 잡아야 합니다."""
        rows = [{"code": "005930", "date": "20200601",
                 guard.events.MARK: ["자사주취득"], guard.events.AGE: 3}]
        with self.assertRaises(guard.LookaheadError):
            guard.check_filings(rows)

    def test_a_negative_age_is_caught(self):
        rows = [{"code": "005930", "date": "20200115",
                 guard.events.MARK: [], guard.events.AGE: -2}]
        with self.assertRaises(guard.LookaheadError):
            guard.check_filings(rows)

    def test_an_unchecked_filing_column_stops_verify(self):
        rows = [{"code": "005930", "date": "20200115", "i": 200,
                 guard.events.MARK: ["자사주취득"], guard.events.AGE: 5}]
        with patch.object(guard, "check_filings", return_value=0), \
             patch.object(guard, "check_corruption", return_value=0), \
             patch.object(guard, "check_truncation", return_value=0), \
             patch.object(guard, "check_dates", return_value=0), \
             patch.object(guard, "check_cross_section", return_value={}):
            with self.assertRaises(guard.LookaheadError) as caught:
                guard.verify({}, rows, samples=1, loud=False)
        self.assertIn("공시", str(caught.exception))




class CapGuard(unittest.TestCase):
    """시가총액은 그날까지 접수된 주식수로만 만들어야 합니다."""

    def setUp(self):
        patcher = patch.object(guard.caps, "timeline",
                               return_value=(("20200110", 1000), ("20200710", 2000)))
        patcher.start(); self.addCleanup(patcher.stop)

    def row(self, day, size, place=1):
        return {"code": "005930", "date": day, "price": 100.0,
                guard.caps.SIZE: size, guard.caps.RANK: place}

    def test_the_count_known_that_day_is_fine(self):
        got = guard.check_caps([self.row("20200315", 100000.0)])
        self.assertGreater(got[guard.caps.SIZE], 0)

    def test_a_later_split_is_caught(self):
        """7월에 늘어난 주식수로 3월의 시가총액을 만들면 잡아야 합니다."""
        with self.assertRaises(guard.LookaheadError) as caught:
            guard.check_caps([self.row("20200315", 200000.0)])
        self.assertIn("뒷날 주식수", str(caught.exception))

    def test_a_day_before_any_filing_is_caught(self):
        with self.assertRaises(guard.LookaheadError):
            guard.check_caps([self.row("20200105", 100000.0)])

    def test_a_wrong_rank_is_caught(self):
        """그날 줄만으로 다시 세운 순위와 다르면 잡아야 합니다."""
        # 둘 다 주식수 1,000주. 값이 큰 쪽이 1등이어야 하는데 뒤집어 붙였습니다.
        rows = [self.row("20200315", 100000.0, place=1),
                {"code": "000660", "date": "20200315", "price": 900.0,
                 guard.caps.SIZE: 900000.0, guard.caps.RANK: 2}]
        with patch.object(guard.caps, "known_by", return_value=1000):
            with self.assertRaises(guard.LookaheadError) as caught:
                guard.check_caps(rows)
        self.assertIn("등이 붙어 있습니다", str(caught.exception))

    def test_an_unchecked_cap_column_stops_verify(self):
        rows = [{"code": "005930", "date": "20200315", "i": 200, "price": 100.0,
                 guard.caps.SIZE: 100000.0, guard.caps.RANK: 1}]
        with patch.object(guard, "check_caps",
                          return_value={n: 0 for n in guard.CAPPED}), \
             patch.object(guard, "check_corruption", return_value=0), \
             patch.object(guard, "check_truncation", return_value=0), \
             patch.object(guard, "check_dates", return_value=0), \
             patch.object(guard, "check_filings", return_value=0), \
             patch.object(guard, "check_cross_section", return_value={}):
            with self.assertRaises(guard.LookaheadError) as caught:
                guard.verify({}, rows, samples=1, loud=False)
        self.assertIn(guard.caps.SIZE, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
