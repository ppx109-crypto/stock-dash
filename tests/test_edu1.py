"""EDU-0001 합성 시험(사전등록 판 2 · 7절): 미래 참조 · 4분기 · 결산월 · 같은 값 순위 · 사건 가격 셈 · t 식."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import edu1 as E  # noqa: E402


def qrow(no, s, o, n, s0=None, o0=None, n0=None, eq=100.0, at=200.0, per="2020.12.31 현재"):
    return {"접수번호": no, "매출": s, "영업이익": o, "순이익": n, "매출_작년": s0, "영업이익_작년": o0, "순이익_작년": n0,
            "자본": eq, "자산": at, "기간": per}


BODY = {"rows": {
    "2020-1분기": qrow("20200515000001", 10, 2, 1, 8, 1, 1, per="2020.03.31 현재"),
    "2020-반기": qrow("20200814000001", 12, 3, 2, 9, 1, 1, per="2020.06.30 현재"),
    "2020-3분기": qrow("20201116000001", 14, 4, 3, 10, 2, 1, per="2020.09.30 현재"),
    "2020-사업": qrow("20210315000001", 52, 13, 9, 40, 6, 4, per="2020.12.31 현재"),
    "2021-1분기": qrow("20210517000001", 15, 5, 4, 10, 2, 1, per="2021.03.31 현재"),
}}


class Quarter(unittest.TestCase):
    def test_q4_is_annual_minus_three(self):
        seen, _ = E.known(E.quarter_book(BODY), "20210316")
        self.assertEqual(seen[(2020, 4)]["s"], 52 - (10 + 12 + 14))
        self.assertEqual(seen[(2020, 4)]["o0"], 6 - (1 + 1 + 2))

    def test_report_on_or_after_day_not_used(self):
        book = E.quarter_book(BODY)
        self.assertEqual(E.known(book, "20210315")[1], (2020, 3))      # 접수일 = 판단일 → 아직 못 씀
        self.assertEqual(E.known(book, "20210316")[1], (2020, 4))

    def test_late_corrected_quarter_not_used_before_its_receipt(self):
        """대리 검토 높음 1: 2분기 줄이 사업보고서보다 늦게(정정) 접수된 꼴 → 그 전엔 4분기를 안 만듦 · 값을 독으로 바꿔도 같음."""
        body = json.loads(json.dumps(BODY))
        body["rows"]["2020-반기"]["접수번호"] = "20210901000001"
        a, _ = E.known(E.quarter_book(body), "20210401")
        self.assertIsNone(a[(2020, 4)]["s"])
        body["rows"]["2020-반기"]["매출"] = 999999
        b, _ = E.known(E.quarter_book(body), "20210401")
        self.assertEqual(a, b)
        c, _ = E.known(E.quarter_book(body), "20210902")
        self.assertEqual(c[(2020, 4)]["s"], 52 - (10 + 999999 + 14))

    def test_non_december_fiscal_year_no_q4(self):
        body = json.loads(json.dumps(BODY))
        body["rows"]["2020-사업"]["기간"] = "2020.03.31 현재"
        seen, _ = E.known(E.quarter_book(body), "20210316")
        self.assertIsNone(seen[(2020, 4)]["s"])

    def test_future_report_change_does_not_move_past(self):
        a = E.fund_feats(E.quarter_book(BODY), "20210401", 1000.0)
        body = json.loads(json.dumps(BODY))
        body["rows"]["2021-1분기"]["매출"] = 999999
        body["rows"]["2021-반기"] = qrow("20210816000001", -5, -5, -5)
        b = E.fund_feats(E.quarter_book(body), "20210401", 1000.0)
        self.assertEqual(a, b)

    def test_ttm_and_ratios(self):
        f = E.fund_feats(E.quarter_book(BODY), "20210601", 100.0)
        s = 12 + 14 + 16 + 15                    # 최근 네 분기 = 2020Q2 · Q3 · Q4 · 2021Q1 · 4분기 매출 52 − 36 = 16
        o = 3 + 4 + 4 + 5                        # 4분기 영업이익 13 − 9 = 4
        self.assertAlmostEqual(f["margin"], o / s)
        self.assertAlmostEqual(f["ey"], o / 100.0)


def crow(no, cfo, cfo_ni=10.0, op=20.0, at=100.0, inv=10.0, ar=10.0, sales=100.0, sales0=90.0, capex=-5.0):
    return {"접수번호": no, "순이익_누적": cfo_ni, "영업현금": cfo, "영업이익_누적": op, "자산": at, "매출_누적": sales,
            "매출_작년누적": sales0, "재고": inv, "매출채권": ar, "설비투자": capex}


class Cash(unittest.TestCase):
    BODY = {"rows": {"2019-반기": crow("20190814000001", 8.0), "2020-반기": crow("20200814000001", 12.0, inv=12.0)}}

    def test_ocf_growth_uses_last_year_same_report_and_annualizes(self):
        f = E.cash_feats(E.cash_book(self.BODY), "20200815")
        self.assertAlmostEqual(f["영업현금증가"], (12 - 8) / 8 * 100)
        self.assertAlmostEqual(f["발생액"], (10 - 12) / 100 * 100 * 2)        # 반기 = 누적 2분기 → ×4/2
        self.assertAlmostEqual(f["설비투자"], 5 / 100 * 100 * 2)
        self.assertAlmostEqual(f["재고-매출"], (12 - 10) / 10 * 100 - (100 - 90) / 90 * 100)

    def test_future_cash_report_not_used(self):
        a = E.cash_feats(E.cash_book(self.BODY), "20200814")                 # 접수일 = 판단일 → 2019 판
        body = json.loads(json.dumps(self.BODY))
        body["rows"]["2020-반기"]["영업현금"] = -999
        b = E.cash_feats(E.cash_book(body), "20200814")
        self.assertEqual(a, b)


class Ranks(unittest.TestCase):
    def test_mid_rank_ties(self):
        r = E.mid_ranks({"a": 1.0, "b": 2.0, "c": 2.0, "d": 3.0, "e": None})
        self.assertEqual(r, {"a": 1.0, "b": 2.5, "c": 2.5, "d": 4.0})

    def test_zero_is_a_value_not_missing(self):
        r = E.pct_rank({"a": 0.0, "b": -1.0})
        self.assertEqual(r, {"b": 0.5, "a": 1.0})

    def test_rename_invariance(self):
        """GPT 고칠 것 2: 종목 이름(코드)만 바꿔도 점수 · 무리가 같아야 함(같은 값 포함)."""
        vals = {f"c{i:02d}": float(i // 3) for i in range(50)}               # 셋씩 같은 값
        q = E.fifths(vals)
        renamed = {f"z{99 - int(c[1:]):02d}": v for c, v in vals.items()}
        back = {f"c{99 - int(c[1:]):02d}": g for c, g in E.fifths(renamed).items()}
        self.assertEqual(q, back)
        for v in set(vals.values()):
            self.assertEqual(len({q[c] for c in vals if vals[c] == v}), 1)  # 같은 값은 같은 무리

    def test_fifths_balanced_without_ties(self):
        q = E.fifths({f"c{i}": float(i) for i in range(50)})
        self.assertEqual(sorted(sum(1 for v in q.values() if v == j) for j in range(1, 6)), [10] * 5)
        self.assertEqual((q["c0"], q["c49"]), (1, 5))


class Stats(unittest.TestCase):
    def test_hh_t(self):
        self.assertIsNone(E.hh_t([0.01, 0.01, 0.01], 2))
        self.assertIsNone(E.hh_t([0.01, 0.02], 0))
        x = [0.01, 0.02, 0.03, 0.02, 0.0, -0.01, 0.01, 0.03]               # 양의 자기상관
        m = sum(x) / len(x)
        e = [v - m for v in x]
        g0 = sum(v * v for v in e) / len(x)
        g1 = sum(e[i] * e[i - 1] for i in range(1, len(x))) / len(x)
        self.assertGreater(g1, 0)
        self.assertAlmostEqual(E.hh_t(x, 0), m / math.sqrt(g0 / len(x)))
        self.assertAlmostEqual(E.hh_t(x, 1), m / math.sqrt((g0 + 2 * g1) / len(x)))
        self.assertIsNone(E.hh_t([0.01, -0.01, 0.01, -0.01, 0.01, -0.01], 1))   # 분산이 음수면 None(통과 못 함)

    def test_cr1_t(self):
        x = [0.1, 0.2, 0.0, 0.3, 0.1, 0.2]
        k = ["a", "a", "b", "b", "c", "c"]
        m = sum(x) / 6
        s = {"a": (0.1 - m) + (0.2 - m), "b": (0.0 - m) + (0.3 - m), "c": (0.1 - m) + (0.2 - m)}
        var = 3 / 2 * sum(v * v for v in s.values()) / 36
        self.assertAlmostEqual(E.cr1_t(x, k), m / math.sqrt(var))
        self.assertIsNone(E.cr1_t(x[:4], ["a", "a", "b", "b"]))            # 묶음 3개 미만


class Events(unittest.TestCase):
    def setUp(self):
        import pandas as pd
        self.days = [f"2020{m:02d}{d:02d}" for m in (1, 2, 3) for d in range(1, 29) if d % 7 not in (0, 6)][:45]
        cols = [f"{i:06d}" for i in range(50)]
        self.C = pd.DataFrame({c: [100.0] * len(self.days) for c in cols}, index=self.days)
        self.member = lambda d: set(cols)

    def test_entry_exit_benchmark_numbers(self):
        """들어감 t0+1 종가 · 나감 t0+1+h · 기준 = 사건 종목 뺀 대상 평균 · 비용은 판정 때만."""
        C = self.C.copy()
        i0 = 2
        C.iloc[i0 + 1:, C.columns.get_loc("000007")] = 110.0                # t0+1부터 110
        C.iloc[i0 + 1 + 20:, C.columns.get_loc("000007")] = 121.0           # 나감 날 121 → +10%
        C.iloc[i0 + 1 + 20:, C.columns.get_loc("000001")] = 102.0           # 다른 종목 하나 +2%
        C.iloc[i0, C.columns.get_loc("000007")] = 50.0                      # t0 종가(들어감이 t0이면 틀린 값이 나옴)
        e = E.events_table(C, self.member, [("000007", self.days[i0], 30.0, "N1")], h=20)["큰 수주(≥20%)"][0]
        self.assertEqual((e["t0"], e["들어감"], e["나감"]), (self.days[i0], self.days[i0 + 1], self.days[i0 + 21]))
        self.assertAlmostEqual(e["기준 평균"], 0.02 / 49)                   # 사건 종목 뺀 49종목 평균
        self.assertAlmostEqual(e["초과(비용 전)"], 0.10 - 0.02 / 49)
        st = E.event_stats([e, dict(e, 종목="000008", t0="20200301"), dict(e, 종목="000009", t0="20200401")], 0.01)
        self.assertAlmostEqual(st["평균"], 0.10 - 0.02 / 49 - 0.01)

    def test_later_prices_do_not_change_selection(self):
        evs = [("000007", self.days[2], 30.0, "N1")]
        a = E.events_table(self.C, self.member, evs, h=20)["큰 수주(≥20%)"]
        C2 = self.C.copy()
        C2.iloc[25:, :] = C2.iloc[25:, :] * 3
        b = E.events_table(C2, self.member, evs, h=20)["큰 수주(≥20%)"]
        self.assertEqual([x["t0"] for x in a], [x["t0"] for x in b])

    def test_filing_on_holiday_goes_to_next_trading_day(self):
        off = next(d for d in (f"202001{k:02d}" for k in range(2, 20)) if d not in self.days)
        nxt = next(d for d in self.days if d > off)
        a = E.events_table(self.C, self.member, [("000007", off, 30.0, "N1")], h=20)["큰 수주(≥20%)"]
        self.assertEqual(a[0]["t0"], nxt)

    def test_outside_window_and_before_data_dropped(self):
        import pandas as pd
        days = [f"2017{m:02d}{d:02d}" for m in (1, 2, 3) for d in range(1, 29) if d % 7 not in (0, 6)][:45]
        C = pd.DataFrame({f"{i:06d}": [100.0] * len(days) for i in range(50)}, index=days)
        evs = [("000007", "20170102", 30.0, "A"), ("000008", "20161201", 30.0, "B"), ("000009", "20170203", 30.0, "C")]
        got = E.events_table(C, lambda d: set(C.columns), evs, h=20)["큰 수주(≥20%)"]
        self.assertEqual([x["종목"] for x in got], ["000009"])             # 2017-01 · 자료 첫날 앞 접수는 빠짐

    def test_no_overlap_same_stock_20d(self):
        evs = [("000007", self.days[1], 30.0, "A"), ("000007", self.days[5], 40.0, "B")]
        self.assertEqual(len(E.events_table(self.C, self.member, evs, h=20)["큰 수주(≥20%)"]), 1)

    def test_contract_filter(self):
        with tempfile.TemporaryDirectory() as d:
            mk = lambda day, nm, kind, pct: {"rcept_dt": day, "rcept_no": day + "800001", "report_nm": nm, "kind": kind,
                                             "fields_k2": {"매출액대비%": pct}}
            body = {"filings": [
                mk("20200110", "단일판매ㆍ공급계약체결", "원본", "25.1"),
                mk("20200111", "단일판매ㆍ공급계약해지", "원본", "30"),
                mk("20200112", "[기재정정]단일판매ㆍ공급계약체결", "정정", "30"),
                mk("20200113", "단일판매ㆍ공급계약체결", "원본", "-"),
                mk("20200114", "단일판매ㆍ공급계약체결(자회사의 주요경영사항)", "원본", "40"),
                mk("20200115", "[첨부추가]단일판매ㆍ공급계약체결", "원본", "40"),
                mk("20261005", "단일판매ㆍ공급계약체결", "원본", "40"),
            ]}
            Path(d, "000007.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            got = E.contract_events(d)
        self.assertEqual(got, [("000007", "20200110", 25.1, "20200110800001")])


class Shares(unittest.TestCase):
    def test_unit_fix_uses_only_earlier_rows(self):
        line = E.shares_line({"날": [["20200101", 1000], ["20200601", 1000000], ["20210101", 1100]]})
        self.assertEqual([c for _, c in line], [1000, 1000.0, 1100])        # 1000배 뛴 줄만 앞 줄과 견줘 고침
        self.assertEqual(E.shares_before(line, "20200601"), 1000)            # 접수일 당일은 아직 못 씀
        self.assertEqual(E.shares_before(line, "20200602"), 1000.0)


if __name__ == "__main__":
    unittest.main()
