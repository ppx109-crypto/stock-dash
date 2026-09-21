"""같은 잣대로만 견주는지 봅니다. 누적과 석 달을 섞으면 적자 판정이 뒤집힙니다."""
import unittest
from unittest.mock import patch

import collect_public_dart
from build_research_bundle import pair


def row(name, account_id, add, amount):
    return {"sj_div": "IS", "account_id": account_id, "account_nm": name,
            "thstrm_nm": "제 7 기 반기", "rcept_no": "20260814000001",
            "thstrm_add_amount": add, "thstrm_amount": amount}


def collect(rows):
    class Fake:
        def dart(self, *args, **kwargs):
            return {"list": rows}
    return collect_public_dart.half(Fake(), "corp", 2026, "CFS")


REVENUE = "ifrs-full_Revenue"
PROFIT = "dart_OperatingIncomeLoss"


class Half(unittest.TestCase):
    def test_the_cumulative_column_is_used_when_it_is_there(self):
        found = collect([row("매출액", REVENUE, "14115216000000", "7560249000000"),
                         row("영업이익", PROFIT, "-94453000000", "113302000000")])
        self.assertEqual(round(found["profit"]), -945)      # 누적 기준 적자
        self.assertEqual(found["measure"], "cumulative")

    def test_a_zero_cumulative_is_a_number_not_a_blank(self):
        # 0을 빈 칸으로 보면 석 달 값으로 내려가 기준이 바뀝니다.
        found = collect([row("매출액", REVENUE, "100000000", "50000000"),
                         row("영업이익", PROFIT, "0", "500000000")])
        self.assertEqual(found["profit"], 0)

    def test_a_half_with_two_different_columns_is_dropped(self):
        found = collect([row("매출액", REVENUE, "14115216000000", "7560249000000"),
                         row("영업이익", PROFIT, "", "113302000000")])
        self.assertIsNone(found)

    def test_the_quarter_column_alone_still_works(self):
        found = collect([row("매출액", REVENUE, "", "7560249000000"),
                         row("영업이익", PROFIT, "", "113302000000")])
        self.assertEqual(found["measure"], "quarter")


class Pairing(unittest.TestCase):
    def half(self, period, measure):
        return {"period": period, "measure": measure, "revenue": 1, "profit": 1}

    def test_the_same_month_a_year_apart_is_the_pair(self):
        prior, now = pair([self.half("2025-06", "cumulative"),
                           self.half("2026-06", "cumulative")])
        self.assertEqual((prior["period"], now["period"]), ("2025-06", "2026-06"))

    def test_a_cumulative_is_never_compared_with_a_quarter(self):
        prior, now = pair([self.half("2025-06", "cumulative"),
                           self.half("2026-06", "quarter")])
        self.assertIsNone(now)

    def test_a_different_month_is_not_a_pair(self):
        prior, now = pair([self.half("2025-03", "cumulative"),
                           self.half("2026-06", "cumulative")])
        self.assertIsNone(now)


if __name__ == "__main__":
    unittest.main()
