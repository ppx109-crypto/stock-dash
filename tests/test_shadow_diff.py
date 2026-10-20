"""그림자 견주기(research/shadow_diff.py)의 순수 셈 시험 — 작은 가짜 자료로."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import shadow_diff as S  # noqa: E402
import idle_live as L  # noqa: E402
import overlay_live as O  # noqa: E402


class PnlTest(unittest.TestCase):
    def test_mark_pnl_hold_and_trades(self):
        # 전날 100주 들고 10원 오름 + 그날 50주를 105원에 사서 종가 110 → 1000 + 250
        self.assertEqual(S.mark_pnl({"A": 100}, [("A", "buy", 50, 105.0)], {"A": 100.0}, {"A": 110.0}), 1250.0)
        # 판 것은 체결값 − 종가
        self.assertEqual(S.mark_pnl({}, [("A", "sell", 10, 112.0)], {}, {"A": 110.0}), 20.0)

    def test_mark_pnl_missing_close(self):
        self.assertIsNone(S.mark_pnl({"A": 1}, [], {"A": 100.0}, {}))

    def test_apply_trades(self):
        self.assertEqual(S.apply_trades({"A": 10}, [("A", "sell", 10, 1), ("B", "buy", 3, 1)]), {"B": 3})


class BookTest(unittest.TestCase):
    ORDERS = [
        {"key": "20261006:buy:251340", "code": "251340", "side": "buy", "qty": 45539, "price": 2130.0,
         "status": "실패 · 모의투자 주문이 거절되었습니다 · 40250000."},
        {"key": "20261007:buy:251340", "code": "251340", "side": "buy", "qty": 36116, "price": 2180.0,
         "status": "접수 · 44,495주 중 살 수 있는 36,116주로 줄임"},
        {"key": "20261012:sell:251340", "code": "251340", "side": "sell", "qty": 36116, "price": 2325.0, "status": "접수"},
    ]

    def test_held_before_skips_failed(self):
        self.assertEqual(S.held_before(self.ORDERS, "20261007"), {})
        self.assertEqual(S.held_before(self.ORDERS, "20261012"), {"251340": 36116})
        self.assertEqual(S.held_before(self.ORDERS, "20261013"), {})

    def test_book_trades_and_failure_text(self):
        fills, notes = S.book_trades(self.ORDERS, "20261006")
        self.assertEqual(fills, [])
        self.assertIn("실패(모의투자 주문이 거절되었습니다 · 40250000)", notes[0])
        fills, notes = S.book_trades(self.ORDERS, "20261007")
        self.assertEqual(fills, [("251340", "buy", 36116, 2180.0)])
        self.assertIn("줄임", notes[0])


class VerdictTest(unittest.TestCase):
    def test_verdict(self):
        self.assertEqual(S.verdict(None, []), "자료 기다림")
        self.assertEqual(S.verdict([], None), "같음(할 일 없음 · 운영은 안 돎)")
        self.assertEqual(S.verdict([("A", "buy", 5)], None), "다름(운영 안 돎)")
        self.assertEqual(S.verdict([("A", "buy", 5, "x")], [("A", "buy", 9)]), "같음")      # 수량은 계좌 크기 차이라 안 봄
        self.assertEqual(S.verdict([("A", "buy", 5)], [("A", "sell", 5)]), "다름")

    def test_cap_room(self):
        self.assertEqual(S.cap_room(0.5, 100.0, 80.0), 0.0)
        self.assertEqual(S.cap_room(1.0, 100.0, 30.0), 70.0)


class OverlayActualTest(unittest.TestCase):
    def test_stale_when_prev_close_late(self):
        st = [{"last_day": "20261014", "signal_day": "20261008"}]
        o, why = S.overlay_actual(st, [], "20261014", "20261013", prev_seen="202610141658")
        self.assertEqual(o, [])
        self.assertIn("stale", why)

    def test_no_stale_when_prev_close_in_time(self):
        st = [{"last_day": "20261014"}]
        _, why = S.overlay_actual(st, [], "20261014", "20261013", prev_seen="202610131800", need=False)
        self.assertIn("맞출 날 아님", why)
        _, why = S.overlay_actual(st, [], "20261014", "20261013", prev_seen="202610131800", need=True, t0_missing=True)
        self.assertIn("어제 거래일 조회 실패", why)
        _, why = S.overlay_actual(st, [], "20261014", "20261013", prev_seen="202610131800")
        self.assertIn("미확인", why)

    def test_not_run_and_orders(self):
        self.assertEqual(S.overlay_actual([], [], "20261013", "20261012")[0], None)
        o, _ = S.overlay_actual([], [{"key": "20261012:buy:122630", "code": "122630", "side": "buy", "qty": 290}],
                                "20261012", "20261008")
        self.assertEqual(o, [("122630", "buy", 290)])

    def test_first_seen(self):
        vers = [("202610131700", {"closes": [["20261012", 1.0]]}), ("202610141658", {"closes": [["20261012", 1.0], ["20261013", 2.0]]})]
        self.assertEqual(S.first_seen(vers, "20261013"), "202610141658")
        self.assertIsNone(S.first_seen(vers, "20261014"))


class ReuseTest(unittest.TestCase):
    """연구 셈은 운영 순수 함수를 그대로 부름 — 인버스 익절 · 덧붙임 맞출 날이 운영과 같게 나오는지."""

    def test_idle_step_take_profit_like_1012(self):
        px = {c: np.full(80, 100.0) for c in L.CODES}
        st = {"positions": {"251340": {"kind": "인버스", "price": 2180.0, "day": "20261007", "days": 2, "take": 0.025}}, "cool": 0}
        now = {c: 100.0 for c in L.CODES}
        now["251340"] = 2325.0
        orders, new, _ = L.step(st, "20261012", px, 42.0, 0.0, 1e8, 1e7, {"251340": 36116}, now, False)
        self.assertEqual([(c, s, q) for c, s, q, _ in orders], [("251340", "sell", 36116)])
        self.assertEqual(new["positions"], {})

    def test_overlay_needs_rebalance(self):
        self.assertTrue(O.needs_rebalance({"applied": None, "rebalanced_month": None}, "상승", "20261012"))
        self.assertFalse(O.needs_rebalance({"applied": "상승", "rebalanced_month": "202610"}, "상승", "20261013"))
        self.assertTrue(O.needs_rebalance({"applied": "상승", "rebalanced_month": "202610"}, "하락", "20261014"))

    def test_render_md(self):
        rows = [{"date": "20261012", "bot": "빈칸 엔진", "research": "a", "actual": "b", "result": "접수", "match": "같음",
                 "gap": 0, "gap_pct": 0.0},
                {"date": "20261013", "bot": "덧붙임", "research": "x|y", "actual": "안 돎", "result": None, "match": "같음",
                 "gap": -2650000, "gap_pct": -2.5}]
        md = S.render_md(rows)
        self.assertLess(md.index("2026-10-13"), md.index("2026-10-12"))       # 최근 날이 위
        self.assertIn("-265만 원", md)
        self.assertIn("x/y", md)                                             # 표 칸 나눔 글자 막음


if __name__ == "__main__":
    unittest.main()
