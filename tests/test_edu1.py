"""EDU-0001 합성 시험(사전등록 7절): 미래 참조 · 4분기 빼기 · 그날끼리 순위 · 사건 들어감 · NW t."""
import importlib
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import edu1 as E  # noqa: E402


def qrow(no, s, o, n, s0=None, o0=None, n0=None, eq=100.0, at=200.0):
    return {"접수번호": no, "매출": s, "영업이익": o, "순이익": n, "매출_작년": s0, "영업이익_작년": o0, "순이익_작년": n0,
            "자본": eq, "자산": at}


BODY = {"rows": {
    "2020-1분기": qrow("20200515000001", 10, 2, 1, 8, 1, 1),
    "2020-반기": qrow("20200814000001", 12, 3, 2, 9, 1, 1),
    "2020-3분기": qrow("20201116000001", 14, 4, 3, 10, 2, 1),
    "2020-사업": qrow("20210315000001", 52, 13, 9, 40, 6, 4),
    "2021-1분기": qrow("20210517000001", 15, 5, 4, 10, 2, 1),
}}


class Quarter(unittest.TestCase):
    def test_q4_is_annual_minus_three(self):
        b = dict((q, v) for _, q, v in E.quarter_book(BODY))
        self.assertEqual(b[(2020, 4)]["s"], 52 - (10 + 12 + 14))
        self.assertEqual(b[(2020, 4)]["o0"], 6 - (1 + 1 + 2))

    def test_q4_none_if_a_quarter_missing(self):
        body = {"rows": {k: v for k, v in BODY["rows"].items() if k != "2020-반기"}}
        b = dict((q, v) for _, q, v in E.quarter_book(body))
        self.assertIsNone(b[(2020, 4)]["s"])

    def test_report_on_or_after_day_not_used(self):
        book = E.quarter_book(BODY)
        seen, last = E.known(book, "20210315")          # 접수일 = 판단일 → 아직 못 씀
        self.assertEqual(last, (2020, 3))
        seen, last = E.known(book, "20210316")
        self.assertEqual(last, (2020, 4))

    def test_future_report_change_does_not_move_past(self):
        a = E.fund_feats(E.quarter_book(BODY), "20210401", 1000.0)
        body = json.loads(json.dumps(BODY))
        body["rows"]["2021-1분기"]["매출"] = 999999
        body["rows"]["2021-반기"] = qrow("20210816000001", -5, -5, -5)
        b = E.fund_feats(E.quarter_book(body), "20210401", 1000.0)
        self.assertEqual(a, b)

    def test_ttm_and_ratios(self):
        f = E.fund_feats(E.quarter_book(BODY), "20210601", 100.0)
        # 최근 네 분기 = 2020Q2 · Q3 · Q4 · 2021Q1
        s = 12 + 14 + 16 + 15                    # 4분기 매출 = 52 − (10 + 12 + 14) = 16
        o = 3 + 4 + 4 + 5                        # 4분기 영업이익 = 13 − (2 + 3 + 4) = 4
        self.assertAlmostEqual(f["margin"], o / s)
        self.assertAlmostEqual(f["ey"], o / 100.0)


class Ranks(unittest.TestCase):
    def test_pct_rank_direction_and_missing(self):
        r = E.pct_rank({"a": 1.0, "b": 3.0, "c": None, "d": 2.0})
        self.assertEqual(r, {"a": 1 / 3, "d": 2 / 3, "b": 1.0})
        r2 = E.pct_rank({"a": 1.0, "b": 3.0}, good_high=False)
        self.assertEqual(r2["a"], 1.0)

    def test_zero_is_a_value_not_missing(self):
        r = E.pct_rank({"a": 0.0, "b": -1.0})
        self.assertIn("a", r)
        self.assertEqual(r["a"], 1.0)

    def test_fifths_only_from_that_day(self):
        day1 = {f"c{i}": float(i) for i in range(50)}
        q = E.fifths(day1)
        self.assertEqual(sum(1 for v in q.values() if v == 5), 10)
        self.assertEqual(q["c49"], 5)
        self.assertEqual(q["c0"], 1)


class Stats(unittest.TestCase):
    def test_nw_t(self):
        self.assertIsNone(E.nw_t([0.01, 0.01, 0.01], 2))          # 분산 0
        self.assertIsNone(E.nw_t([0.01, 0.02], 0))                # 너무 짧음
        x = [0.01, -0.02, 0.03, 0.0, 0.02, -0.01]
        t0 = E.nw_t(x, 0)
        m = sum(x) / len(x)
        sd = math.sqrt(sum((v - m) ** 2 for v in x) / len(x))
        self.assertAlmostEqual(t0, m / (sd / math.sqrt(len(x))))

    def test_cluster_t(self):
        self.assertIsNone(E.cluster_t({"a": [1.0], "b": [1.0], "c": [1.0]}))
        self.assertIsNotNone(E.cluster_t({"a": [1.0], "b": [2.0], "c": [0.5]}))


class Events(unittest.TestCase):
    def setUp(self):
        import pandas as pd
        days = [f"2020{m:02d}{d:02d}" for m in (1, 2, 3) for d in range(1, 29) if d % 7 not in (0, 6)][:45]
        cols = [f"{i:06d}" for i in range(50)]
        self.C = pd.DataFrame({c: [100.0 + k for k in range(len(days))] for c in cols}, index=days)
        self.C["000007"] = [100.0] * len(days)
        self.inside = pd.DataFrame(True, index=days, columns=cols)
        self.days = days

    def test_entry_is_t0_plus_one_close(self):
        evs = [("000007", self.days[2], 30.0)]
        a = E.events_table(self.C, self.inside, evs, h=20)["큰 수주(≥20%)"]
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["t0"], self.days[2])
        C2 = self.C.copy()
        C2.iloc[25:, :] = C2.iloc[25:, :] * 3                    # 들어간 뒤 먼 날 값만 바꿔도 사건 고르기는 같음
        b = E.events_table(C2, self.inside, evs, h=20)["큰 수주(≥20%)"]
        self.assertEqual([e["t0"] for e in a], [e["t0"] for e in b])

    def test_filing_on_holiday_goes_to_next_trading_day(self):
        off = next(d for d in (f"202001{k:02d}" for k in range(2, 20)) if d not in self.days)   # 표에 없는 날(쉼)
        nxt = next(d for d in self.days if d > off)
        evs = [("000007", off, 30.0)]
        a = E.events_table(self.C, self.inside, evs, h=20)["큰 수주(≥20%)"]
        self.assertEqual(a[0]["t0"], nxt)

    def test_no_overlap_same_stock_20d(self):
        evs = [("000007", self.days[1], 30.0), ("000007", self.days[5], 40.0)]
        a = E.events_table(self.C, self.inside, evs, h=20)["큰 수주(≥20%)"]
        self.assertEqual(len(a), 1)

    def test_contract_filter(self):
        with tempfile.TemporaryDirectory() as d:
            body = {"filings": [
                {"rcept_dt": "20200110", "report_nm": "단일판매ㆍ공급계약체결", "kind": "원본", "fields_k2": {"매출액대비%": "25.1"}},
                {"rcept_dt": "20200111", "report_nm": "단일판매ㆍ공급계약해지", "kind": "원본", "fields_k2": {"매출액대비%": "30"}},
                {"rcept_dt": "20200112", "report_nm": "[기재정정]단일판매ㆍ공급계약체결", "kind": "정정", "fields_k2": {"매출액대비%": "30"}},
                {"rcept_dt": "20200113", "report_nm": "단일판매ㆍ공급계약체결", "kind": "원본", "fields_k2": {"매출액대비%": "-"}},
                {"rcept_dt": "20261005", "report_nm": "단일판매ㆍ공급계약체결", "kind": "원본", "fields_k2": {"매출액대비%": "40"}},
            ]}
            Path(d, "000007.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            got = E.contract_events(d)
        self.assertEqual(got, [("000007", "20200110", 25.1)])        # 해지 · 정정 · % 없음 · 2026-10-01 뒤 빠짐


if __name__ == "__main__":
    unittest.main()
