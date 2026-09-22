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


if __name__ == "__main__":
    unittest.main()
