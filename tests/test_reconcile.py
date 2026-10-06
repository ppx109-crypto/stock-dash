import json
import tempfile
import unittest
from pathlib import Path

from unittest import mock

import reconcile as R


class Bars(unittest.TestCase):
    rows = [("202610020900", 10, 12, 9, 11, 100), ("202610020915", 11, 13, 10, 12, 50),
            ("202610021500", 20, 21, 19, 20, 10), ("202610021515", 20, 22, 18, 21, 30)]

    def test_hours_merge_15_into_14_like_live(self):
        h = R.to_hours(self.rows, "20261002")
        self.assertEqual([x[0] for x in h], ["2026100209", "2026100214"])
        self.assertEqual(h[0][1:], (10, 13, 9, 12, 150))
        self.assertEqual(h[1][1:], (20, 22, 18, 21, 40), "15시 칸은 14시 봉 · 종가는 마감")

    def test_day_bar(self):
        self.assertEqual(R.to_day(self.rows), (10, 22, 9, 21, 190))
        self.assertIsNone(R.to_day([]))

    def test_m15_day_reads_only_that_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "000001").mkdir()
            (Path(tmp) / "000001" / "2026.csv").write_text(
                "202610010900,1,1,1,1,1\n202610020900,2,3,1,2,5\n", encoding="utf-8")
            self.assertEqual(R.m15_day("000001", "20261002", home=tmp), [("202610020900", 2.0, 3.0, 1.0, 2.0, 5.0)])
            self.assertEqual(R.m15_day("000002", "20261002", home=tmp), [])


class Compare(unittest.TestCase):
    def test_same_and_different_trades(self):
        back = {"closed": [{"code": "A", "산 날": "20261002", "판 날": "20261005", "칸": 4, "손익": 5.0},
                           {"code": "B", "산 날": "20261002", "판 날": "20261006", "칸": 2, "손익": -3.0}],
                "positions": {"C": {"bought": "20261006", "칸": 2, "price": 10.0}}}
        live = {"closed": [{"code": "A", "산 날": "20261002", "판 날": "20261005", "칸": 4, "손익": 4.5}],
                "positions": {"C": {"bought": "20261006", "칸": 2, "price": 10.1}, "D": {"bought": "20261006", "칸": 2, "price": 5.0}}}
        got = R.compare(back, live, "산 날", "판 날")
        self.assertEqual(got["같은 매매"], 1)
        self.assertEqual(got["백테스트에만"], [("B", "20261002")])
        self.assertEqual(got["같은 매매 손익 차이"], [("A", "20261002", 5.0, 4.5)])
        self.assertEqual(got["계좌 몫 합(백테스트 · 운영 · %)"], (1.4, 1.8))
        self.assertEqual(got["들고 있는 종목(운영)"], ["C", "D"])


class Verify(unittest.TestCase):
    """저녁 일봉은 넥스트레이드 값이 섞인 임시 값 → 확정된 날까지만 검산 · 아침에 다시 셈(2026-10-06 338/424 잘못 알림)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.patches = [mock.patch.object(R, "CHECKED", t / "checked.json"), mock.patch.object(R, "HOME", t / "rec")]
        for x in self.patches:
            x.start()
        self.m15 = {"A": 100.0, "B": 200.0, "C": 300.0, "D": 400.0, "E": 500.0}
        mock.patch.object(R, "m15_day", side_effect=lambda c, d: [(d + "1515", 1, 1, 1, self.m15[c], 1)]).start()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(self.tmp.cleanup)

    def prices(self, close):
        return {c: {"rows": [("20261006", v)]} for c, v in close.items()}

    def confirm(self, day):
        R.CHECKED.write_text(json.dumps({"checked": day}), encoding="utf-8")

    def test_evening_unconfirmed_day_not_counted_nor_sent(self):
        self.confirm("20261005")
        nxt = self.prices({c: v * 1.02 for c, v in self.m15.items()})      # 저녁 일봉 = 넥스트레이드 값
        v = R.verify("20261006", nxt)
        self.assertTrue(v.get("확정 전"))
        self.assertEqual(v["다름"], [])
        out = {"date": "20261006", R.VERIFY: v,
               "1시간봉": {"운영과 견줌(START부터 누계)": {"같은 매매": 0, "운영 끝난 매매": 0}},
               "1일봉": {"운영과 견줌(START부터 누계)": {"같은 매매": 1, "운영 끝난 매매": 1}}}
        self.assertNotIn("검산", R.summary_lines(out)[0])

    def test_confirmed_day_counted(self):
        self.confirm("20261006")
        v = R.verify("20261006", self.prices({**self.m15, "A": 90.0}))
        self.assertEqual([x[0] for x in v["다름"]], ["A"])
        self.assertTrue(v["확정뒤"])

    def save_evening(self):
        R.HOME.mkdir(parents=True, exist_ok=True)
        (R.HOME / "20261006.json").write_text(json.dumps({"date": "20261006", R.VERIFY: {"종목": 0, "다름": [], "확정 전": True}}),
                                              encoding="utf-8")

    def test_recheck_waits_until_confirmed(self):
        self.save_evening()
        self.confirm("20261005")
        self.assertEqual(R.recheck(self.prices(self.m15)), [])
        self.assertTrue(json.loads((R.HOME / "20261006.json").read_text(encoding="utf-8"))[R.VERIFY]["확정 전"])

    def test_recheck_fixes_by_asking_again_then_silent(self):
        self.save_evening()
        self.confirm("20261006")
        bad = self.prices({**self.m15, "A": 90.0, "B": 190.0, "C": 290.0, "D": 390.0})
        asked = []
        alerts = R.recheck(bad, refetch=asked.append, reload=lambda: self.prices(self.m15))
        self.assertEqual(asked, [["A", "B", "C", "D"]], "다른 종목만 한 번 더 물음")
        self.assertEqual(alerts, [], "다시 물어 맞으면 알리지 않음")
        v = json.loads((R.HOME / "20261006.json").read_text(encoding="utf-8"))[R.VERIFY]
        self.assertEqual((v["다름"], v["종목"], v["확정뒤"], v["다시물음"]), ([], 5, True, 4))
        self.assertEqual(R.recheck(bad, refetch=asked.append), [], "한 번 셌으면 다시 안 셈")
        self.assertEqual(len(asked), 1)

    def test_recheck_alerts_only_when_still_many_differ(self):
        self.save_evening()
        self.confirm("20261006")
        bad = self.prices({**self.m15, "A": 90.0, "B": 190.0, "C": 290.0, "D": 390.0})
        alerts = R.recheck(bad, refetch=lambda codes: None, reload=lambda: bad)
        self.assertEqual(len(alerts), 1)
        self.assertIn("4/5", alerts[0])

    def test_recheck_one_odd_code_is_not_alerted(self):
        self.save_evening()
        self.confirm("20261006")
        self.assertEqual(R.recheck(self.prices({**self.m15, "A": 90.0})), [])


if __name__ == "__main__":
    unittest.main()
