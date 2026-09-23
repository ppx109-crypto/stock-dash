"""거래대금 자. '실제로 살 수 있었나'를 가리는 데 씁니다.

그날까지의 거래만 봐야 합니다. 뒷날 거래가 한 날만 섞여도 그날의 유동성을
실제보다 좋게 보게 됩니다.
"""
import json
import unittest
from unittest.mock import patch

import money


def book(rows):
    return {"code": "005930", "칸": ["날짜", "거래량", "거래대금", "고가", "저가"],
            "날": [[day, 10.0, value, 1.0, 1.0] for day, value in rows]}


class Rolling(unittest.TestCase):

    def setUp(self):
        money.timeline.cache_clear()
        money._rolling.cache_clear()
        self.rows = [(f"2020{(k // 21) + 1:02d}{(k % 21) + 1:02d}", float(k + 1))
                     for k in range(60)]
        patcher = patch.object(money, "timeline",
                               return_value=tuple(self.rows))
        patcher.start(); self.addCleanup(patcher.stop)
        self.addCleanup(money._rolling.cache_clear)

    def test_it_is_the_median_of_the_last_twenty(self):
        """서른째 날이면 열한째~서른째(11~30)의 중앙값입니다.

        짝수 개일 때는 위쪽 가운데를 씁니다(이 저장소가 쓰는 방식입니다).
        """
        day = self.rows[29][0]
        self.assertEqual(money.known_by("005930", day), 21.0)

    def test_it_never_reads_past_the_day(self):
        day = self.rows[29][0]
        before = money.known_by("005930", day)
        money._rolling.cache_clear()
        longer = self.rows[:30] + [(d, 9e9) for d, _ in self.rows[30:]]
        with patch.object(money, "timeline", return_value=tuple(longer)):
            self.assertEqual(money.known_by("005930", day), before)

    def test_too_early_to_tell_gives_nothing(self):
        self.assertIsNone(money.known_by("005930", self.rows[3][0]))

    def test_a_day_that_is_not_there_gives_nothing(self):
        self.assertIsNone(money.known_by("005930", "19990101"))

    def test_one_burst_does_not_lift_the_median(self):
        """하루 터진 거래대금이 평소 실력으로 보이면 안 됩니다."""
        money._rolling.cache_clear()
        spiked = list(self.rows)
        spiked[29] = (spiked[29][0], 9e9)
        with patch.object(money, "timeline", return_value=tuple(spiked)):
            self.assertLess(money.known_by("005930", spiked[29][0]), 100.0)


class Floor(unittest.TestCase):

    def test_a_row_without_the_number_is_not_enough(self):
        """'모름'을 '충분함'으로 세면 안 됩니다."""
        self.assertFalse(money.enough({"code": "005930"}, 1e8))

    def test_at_the_floor_counts(self):
        self.assertTrue(money.enough({money.MONEY: 1e8}, 1e8))

    def test_below_the_floor_does_not(self):
        self.assertFalse(money.enough({money.MONEY: 1e8 - 1}, 1e8))


class Share(unittest.TestCase):

    def test_the_slot_share_is_the_purse_over_the_turnover(self):
        rows = [{"code": "005930", "date": "20200301"}]
        with patch.object(money, "covered", return_value=True), \
             patch.object(money, "known_by", return_value=1e9):
            money.tag(rows, purse=3e8, slots=3)
        self.assertAlmostEqual(rows[0][money.SHARE], 10.0, places=3)

    def test_no_purse_means_no_share(self):
        rows = [{"code": "005930", "date": "20200301"}]
        with patch.object(money, "covered", return_value=True), \
             patch.object(money, "known_by", return_value=1e9):
            money.tag(rows)
        self.assertNotIn(money.SHARE, rows[0])


if __name__ == "__main__":
    unittest.main()
