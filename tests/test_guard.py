"""미래참조 검사기가 정말로 잡아내는지 봅니다.

검사가 늘 통과하기만 하면 검사가 아니라 도장입니다. 그래서 일부러 뒷날을
보는 값을 넣어 두고, 네 겹이 각각 그것을 잡아내는지 확인합니다.

넷째 겹은 가로줄입니다. 그날 온 종목을 견주어 만든 값은 한 종목만 떼어
다시 만들 수가 없어 앞의 두 겹이 닿지 않습니다. 그 면제를 악용해 뒷날을
섞어 넣으면 어떻게 되는지도 여기서 확인합니다.
"""
import unittest
from unittest.mock import patch

import caps
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


class Anchor(unittest.TestCase):
    """표에 적힌 자리가 지금 일봉에서 정말 그날인지.

    표를 굽고 나서 일봉을 다시 받으면 종목에 따라 앞쪽 날이 하나씩 떨어져
    나갑니다. 그러면 자리가 밀리는데, 매매 시뮬은 그 자리로 종가를 찾습니다.
    값 차이가 1e-8뿐이라 눈으로는 안 보입니다.
    """

    def prices(self, days):
        return {"005930": {"name": "삼성전자",
                           "rows": [(d, 100.0 + k) for k, d in enumerate(days)]}}

    def test_a_row_that_still_points_at_its_day_passes(self):
        days = ["2024010%d" % k for k in range(1, 6)]
        rows = [{"code": "005930", "date": days[2], "i": 2}]
        self.assertEqual(guard.check_anchor(self.prices(days), rows), 1)

    def test_a_day_dropped_from_the_front_is_caught(self):
        days = ["2024010%d" % k for k in range(1, 6)]
        rows = [{"code": "005930", "date": days[2], "i": 3}]   # 하루 밀렸다
        with self.assertRaises(guard.LookaheadError) as caught:
            guard.check_anchor(self.prices(days), rows)
        self.assertIn("자리", str(caught.exception))

    def test_a_row_past_the_end_is_caught(self):
        days = ["2024010%d" % k for k in range(1, 6)]
        rows = [{"code": "005930", "date": days[4], "i": 99}]
        with self.assertRaises(guard.LookaheadError):
            guard.check_anchor(self.prices(days), rows)

    def test_a_stock_with_no_prices_is_skipped(self):
        days = ["2024010%d" % k for k in range(1, 6)]
        rows = [{"code": "000660", "date": days[1], "i": 1}]
        self.assertEqual(guard.check_anchor(self.prices(days), rows), 1)


class ShallowPool(unittest.TestCase):
    """'100등 안'이 정말 100등 안인지. 54회차에 199종목으로 줄을 세우고

    있었던 것을 쉰 회차 만에 알았습니다. 자료가 모자라 문턱이 느슨해진 것은
    미래참조가 아니지만 수치를 똑같이 부풀립니다.
    """

    def rows(self, ranked, total, days=5):
        found = []
        for day in range(days):
            for spot in range(total):
                row = {"code": f"{spot:06d}", "date": f"2024010{day + 1}"}
                if spot < ranked:
                    row[caps.RANK] = spot + 1
                found.append(row)
        return found

    def test_a_full_pool_passes(self):
        count, share = guard.check_pool(self.rows(100, 100))
        self.assertEqual(count, 100)
        self.assertEqual(share, 1.0)

    def test_a_thin_pool_stops_everything(self):
        with self.assertRaises(guard.ShallowPoolError) as caught:
            guard.check_pool(self.rows(199, 507))
        self.assertIn("39%", str(caught.exception))

    def test_the_floor_is_where_it_is_asked_to_be(self):
        guard.check_pool(self.rows(199, 507), floor=0.3)

    def test_nothing_at_all_is_not_an_error(self):
        self.assertEqual(guard.check_pool([]), (0, 1.0))

    def test_days_before_the_share_data_begins_are_left_out(self):
        """주식수 자료는 2015년부터입니다. 그 앞의 날까지 세면 몫이

        '문턱이 느슨한가'가 아니라 '자료가 언제 시작하나'를 재게 됩니다.
        """
        old = [{"code": f"{k:06d}", "date": "19990102"} for k in range(100)]
        new = self.rows(90, 100, days=2)
        count, share = guard.check_pool(old + new)
        self.assertEqual(count, 90)
        self.assertEqual(share, 0.9)


    def test_a_table_with_no_ranks_at_all_is_left_alone(self):
        """순위를 안 붙인 표는 그 문턱을 안 쓰는 것입니다. 아무것도 안 사집니다."""
        self.assertEqual(guard.check_pool(self.rows(0, 50)), (0, 0.0))


class GateHoles(unittest.TestCase):
    """문턱 안에 들었을 종목이 순위를 못 받고 있나(58회차).

    55회차의 check_pool은 "몇 %가 순위를 받았나"를 물었고, 그 수치 하나로
    56·57회차에 두 번 잘못 읽었습니다. 이 겹은 위쪽만 봅니다.
    """

    def day(self, n):
        return f"2024{n // 28 + 1:02d}{n % 28 + 1:02d}"

    def test_a_small_stock_with_no_rank_is_not_a_hole(self):
        """순위를 못 받았지만 다음에 받은 등수가 문턱 밖이면 상관없습니다."""
        rows = []
        for n in range(4):
            rows.append({"code": "000001", "date": self.day(n), caps.RANK: 5})
            rows.append({"code": "000002", "date": self.day(n)})
        rows.append({"code": "000002", "date": self.day(9), caps.RANK: 400})
        count, share = guard.check_gate(rows, top=100)
        self.assertEqual(count, 0)

    def test_a_big_stock_with_no_rank_stops_everything(self):
        rows = []
        for n in range(4):
            rows.append({"code": "000001", "date": self.day(n), caps.RANK: 5})
            rows.append({"code": "000002", "date": self.day(n)})
        rows.append({"code": "000002", "date": self.day(9), caps.RANK: 20})
        with self.assertRaises(guard.ShallowPoolError):
            guard.check_gate(rows, top=100)

    def test_a_stock_never_ranked_at_all_cannot_be_judged(self):
        """한 번도 순위를 안 받은 종목은 크기를 어림할 길이 없어 넘어갑니다."""
        rows = [{"code": "000001", "date": self.day(0), caps.RANK: 5},
                {"code": "000009", "date": self.day(0)}]
        self.assertEqual(guard.check_gate(rows, top=100), (0, 0.0))

    def test_only_later_ranks_are_used_not_earlier_ones(self):
        """뒤에 받은 등수로만 어림합니다. 앞의 등수는 이미 지난 일입니다."""
        rows = [{"code": "000001", "date": self.day(0), caps.RANK: 10},
                {"code": "000002", "date": self.day(0), caps.RANK: 20},
                {"code": "000002", "date": self.day(1)},
                {"code": "000001", "date": self.day(1), caps.RANK: 10}]
        # 000002는 그 뒤로 순위를 받은 날이 없으니 어림할 수 없습니다.
        self.assertEqual(guard.check_gate(rows, top=100), (0, 0.0))

    def test_years_the_study_does_not_use_are_not_counted(self):
        """60회차에 2015·2016년을 조사에서 뺐습니다. 안 쓰는 구간이 비어

        있다고 멈추면 쓰지도 않는 자료 때문에 일을 못 합니다.
        """
        rows = []
        # 옛 구간: 한 종목만 순위가 있고 나머지 열은 비어 있습니다.
        for k in range(10):
            rows.append({"code": f"01{k:04d}", "date": "20150102"})
        rows.append({"code": "000001", "date": "20150102", caps.RANK: 5})
        # 새 구간: 그 열 종목이 모두 순위를 받습니다.
        for k in range(10):
            rows.append({"code": f"01{k:04d}", "date": self.day(0),
                         caps.RANK: 20 + k})
        rows.append({"code": "000001", "date": self.day(0), caps.RANK: 5})
        with self.assertRaises(guard.ShallowPoolError):
            guard.check_gate(rows, top=100)
        self.assertEqual(guard.check_gate(rows, top=100, since="20240101"),
                         (0, 0.0))
