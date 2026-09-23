"""이미 받아 둔 종목을 날마다 통째로 다시 받지 않는지 봅니다.

서른 해치를 140일씩 거슬러 오르면 종목 하나에 일흔여덟 번을 묻습니다.
243종목이면 만 구천 번이고, 그것만으로 두 시간이 넘습니다. 그러는 동안
아직 없는 종목은 하나도 못 받습니다. 그래서 이어받기가 실제로 이어받는지,
그리고 이어 붙이면 안 되는 자리에서 제대로 손을 떼는지 확인합니다.
"""
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import collect_prices
import collect_volumes


def day(back):
    stamp = datetime.now(ZoneInfo("Asia/Seoul")).date() - timedelta(days=back)
    return stamp.strftime("%Y%m%d")


def history(count=200, first=400, price=100.0):
    """오래된 날이 먼저인 일봉입니다."""
    return [(day(first - k), price + k) for k in range(count)]


class CatchUp(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.was = collect_prices.OUT
        collect_prices.OUT = self.folder
        self.addCleanup(setattr, collect_prices, "OUT", self.was)
        self.addCleanup(shutil.rmtree, self.folder, True)

    def keep(self, code, rows):
        (self.folder / f"{code}.json").write_text(
            json.dumps({"code": code, "name": code,
                        "closes": [[d, c] for d, c in rows], "fetched": "2020-01-01"}),
            encoding="utf-8")

    def test_it_asks_once_instead_of_seventy_eight_times(self):
        have = history(count=200, first=205)
        fresh = [(d, c) for d, c in have[-10:]] + [(day(3), 500.0), (day(2), 501.0)]
        client = Mock()
        client.daily.return_value = fresh
        rows, how = collect_prices.catch_up(client, "005930", have)
        self.assertEqual(client.daily.call_count, 1)
        client.history.assert_not_called()
        self.assertIn("이어받음", how)
        self.assertEqual(rows[-1], (day(2), 501.0))
        self.assertEqual(len(rows), len(have) + 2)

    def test_a_changed_past_price_means_start_over(self):
        """액면분할이 있으면 지난 수정주가가 통째로 다시 매겨집니다."""
        have = history(count=200, first=205)
        halved = [(d, c / 2) for d, c in have[-10:]]
        client = Mock()
        client.daily.return_value = halved
        rows, why = collect_prices.catch_up(client, "005930", have)
        self.assertIsNone(rows)
        self.assertEqual(why, "지난 값이 바뀜")

    def test_a_long_silence_cannot_be_stitched(self):
        have = history(count=200, first=900)
        client = Mock()
        rows, why = collect_prices.catch_up(client, "005930", have)
        self.assertIsNone(rows)
        self.assertEqual(why, "너무 오래 비었음")
        client.daily.assert_not_called()

    def test_a_stock_we_never_had_is_fetched_whole(self):
        client = Mock()
        rows, why = collect_prices.catch_up(client, "005930", [])
        self.assertIsNone(rows)
        self.assertEqual(why, "받아 둔 것이 모자람")
        client.daily.assert_not_called()

    def test_no_overlap_means_we_cannot_trust_the_join(self):
        have = history(count=200, first=205)
        client = Mock()
        client.daily.return_value = [(day(2), 900.0)]
        rows, why = collect_prices.catch_up(client, "005930", have)
        self.assertIsNone(rows)
        self.assertEqual(why, "겹치는 날이 없음")

    def test_a_quiet_day_keeps_what_we_had(self):
        have = history(count=200, first=205)
        client = Mock()
        client.daily.return_value = []
        rows, how = collect_prices.catch_up(client, "005930", have)
        self.assertEqual(rows, have)
        self.assertEqual(how, "새로 나온 날 없음")

    def test_it_reads_back_what_was_written(self):
        have = history(count=130, first=140)
        self.keep("005930", have)
        self.assertEqual(collect_prices.kept_rows("005930"), have)

    def test_a_missing_file_reads_as_nothing(self):
        self.assertEqual(collect_prices.kept_rows("999999"), [])



class VolumeCatchUp(unittest.TestCase):
    """거래량 수집기도 같은 셈입니다. 둘 다 같은 줄에 서 있어, 한쪽이 하루를
    다 쓰면 다른 쪽이 못 돕니다."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.was = collect_volumes.OUT
        collect_volumes.OUT = self.folder
        self.addCleanup(setattr, collect_volumes, "OUT", self.was)
        self.addCleanup(shutil.rmtree, self.folder, True)

    def bars(self, count=200, first=205):
        return [(day(first - k), {"거래량": 1000 + k, "거래대금": 2000 + k,
                                 "고가": 110.0, "저가": 90.0}) for k in range(count)]

    def test_it_appends_the_new_days(self):
        have = self.bars()
        fresh = have[-5:] + [(day(2), {"거래량": 7, "거래대금": 8,
                                       "고가": 1.0, "저가": 1.0})]
        client = Mock()
        client.daily.return_value = fresh
        rows, how = collect_volumes.catch_up(client, "005930", have)
        self.assertEqual(client.daily.call_count, 1)
        self.assertTrue(client.daily.call_args.kwargs["detail"])
        client.history.assert_not_called()
        self.assertIn("이어받음", how)
        self.assertEqual(rows[-1][1]["거래량"], 7)

    def test_a_changed_past_volume_means_start_over(self):
        have = self.bars()
        bent = [(d, {**got, "거래량": got["거래량"] * 2}) for d, got in have[-5:]]
        client = Mock()
        client.daily.return_value = bent
        rows, why = collect_volumes.catch_up(client, "005930", have)
        self.assertIsNone(rows)
        self.assertEqual(why, "지난 거래량이 바뀜")

    def test_it_reads_back_what_was_written(self):
        have = self.bars(count=130, first=140)
        collect_volumes.save("005930", have)
        back = collect_volumes.kept_rows("005930")
        self.assertEqual([d for d, _ in back], [d for d, _ in have])
        self.assertEqual(back[0][1]["거래량"], have[0][1]["거래량"])


if __name__ == "__main__":
    unittest.main()
