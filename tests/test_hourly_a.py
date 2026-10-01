import unittest

import hourly_a as A


def cand(code, trend=False, steady=False, flow5=0.1, r20=0.1):
    return {"code": code, "name": "종목" + code, "추세문": trend, "3일연속": steady, "flow5": flow5, "r20": r20}


def rising(n, start=100.0, step=0.2):
    return [start + i * step for i in range(n)]


class Parts(unittest.TestCase):
    def test_ema_waits_span(self):
        got = A.ema([1.0] * 10, 5)
        self.assertEqual(got[:5], [None] * 5)
        self.assertAlmostEqual(got[9], 1.0)

    def test_aligned_needs_history_and_order(self):
        up = A.aligned_series(rising(300))
        self.assertFalse(up[100])          # 180봉 선이 아직 없음
        self.assertTrue(up[-1])
        self.assertFalse(A.aligned_series(list(reversed(rising(300))))[-1])

    def test_order_tiers_prefers_weak_flow_and_strong_return(self):
        got = A.order_tiers({"a": {"flow5": 0.1, "r20": 0.3}, "b": {"flow5": 0.5, "r20": 0.2}, "c": {"flow5": 0.9, "r20": 0.1}})
        self.assertEqual(got["a"], 4)
        self.assertEqual(got["c"], 0)
        self.assertEqual(A.order_tiers({"a": {"flow5": None, "r20": None}}), {"a": 2})

    def test_exits(self):
        base = {"price": 100.0, "peak": 100.0, "칸": 4, "처음칸": 4, "bars": 3, "kind": "추세"}
        self.assertEqual(A.exit_decision(base, 105.5, 103.0)[0], 2)       # +5% 처음 → 절반
        self.assertEqual(A.exit_decision(base, 105.5, 106.0)[0], 0)       # 이미 +5%를 넘었던 뒤
        self.assertEqual(A.exit_decision(base, 113.5, 110.0)[0], 4)       # +13% 전량
        self.assertEqual(A.exit_decision(base, 94.9, 100.0)[0], 4)        # −5%
        self.assertEqual(A.exit_decision({**base, "bars": 60}, 101.0, 102.0)[0], 4)
        line = {"price": 100.0, "peak": 109.0, "칸": 2, "처음칸": 2, "bars": 20, "kind": "정배열"}
        self.assertEqual(A.exit_decision(line, 100.5, 108.0)[0], 2)       # 본전 지키기
        self.assertEqual(A.exit_decision({**line, "peak": 103.0}, 89.9, 103.0)[0], 2)   # −10%
        self.assertEqual(A.exit_decision({**line, "peak": 103.0}, 95.0, 103.0)[0], 0)

    def test_stale(self):
        p = {"bars": 8, "price": 100.0}
        self.assertTrue(A.stale(p, 102.0, 60))
        self.assertFalse(A.stale(p, 105.0, 60))
        self.assertFalse(A.stale(p, 102.0, 95))
        self.assertFalse(A.stale({**p, "bars": 5}, 102.0, 60))


class Flow(unittest.TestCase):
    def bars(self, codes, n=300):
        day = "20260105"
        t = [f"2025{(i // 6) % 12 + 1:02d}{(i // 72) + 1:02d}{A.HOURS[i % 6]}" for i in range(n - 6)]
        t += [day + hh for hh in A.HOURS]
        return {c: {"t": t, "c": list(reversed(rising(n)))} for c in codes}, day      # 내려가는 흐름 → 정배열 신호 없음

    def test_noon_fallback_buys_by_order_and_marks_day_seen(self):
        bars, day = self.bars(["000001", "000002"])
        plan = {"breadth": 60, "candidates": [cand("000001", flow5=0.9, r20=0.0), cand("000002", flow5=0.1, r20=0.3)]}
        state, logs = {"positions": {}, "pending": []}, []
        for hh in ("09", "10"):
            A.step(state, plan, bars, day + hh, {}, lambda k, t, e: logs.append(k))
        self.assertEqual(state["pending"], [])
        A.step(state, plan, bars, day + "11", {"000001": 100.0, "000002": 50.0}, lambda k, t, e: logs.append(k))
        buys = [x for x in state["pending"] if x["type"] == "buy"]
        self.assertEqual([x["code"] for x in buys], ["000002", "000001"])      # 덜 몰리고 오른 것 먼저
        self.assertEqual(sorted(state["seen"][day]), ["000001", "000002"])
        A.fill(state, day + "12", {"000001": 100.0, "000002": 50.0})
        self.assertEqual(set(state["positions"]), {"000001", "000002"})
        self.assertEqual(state["positions"]["000001"]["bars"], -1)             # 산 봉이 닫히면 0

    def test_swap_when_full(self):
        bars, day = self.bars(["000009", "000001"])
        state = {"positions": {}, "pending": []}
        for i in range(5):
            code = f"10000{i}"
            state["positions"][code] = {"code": code, "name": code, "kind": "정배열", "price": 100.0, "peak": 101.0,
                                        "칸": 2, "처음칸": 2, "bars": 10, "last_close": 100.0 + i, "max_close": 101.0, "bought": "2025123111"}
        plan = {"breadth": 60, "candidates": [cand("000009", trend=True)]}
        logs = []
        A.step(state, plan, bars, day + "11", {}, lambda k, t, e: logs.append((k, t)))
        kinds = [k for k, _ in logs]
        self.assertIn("자리 바꾸기", kinds)
        sells = [x for x in state["pending"] if x["type"] == "sell"]
        self.assertEqual([x["code"] for x in sells], ["100000", "100001"])   # 손익 나쁜 것부터 4칸만큼
        self.assertEqual([x["칸"] for x in state["pending"] if x["type"] == "buy"], [4])
        A.fill(state, day + "12", {"100000": 99.0, "100001": 99.0, "000009": 10.0})
        self.assertNotIn("100000", state["positions"])
        self.assertIn("000009", state["positions"])
        self.assertEqual(len(state["closed"]), 2)

    def test_half_take_then_rest(self):
        bars, day = self.bars(["000001"])
        bars["000001"]["c"][-6] = 106.0          # 09시 봉 종가 +6%
        state = {"positions": {"000001": {"code": "000001", "name": "a", "kind": "추세", "price": 100.0, "peak": 100.0,
                                          "칸": 4, "처음칸": 4, "bars": 1, "max_close": 101.0, "bought": "2025123111"}}, "pending": []}
        logs = []
        A.step(state, {"candidates": []}, bars, day + "09", {}, lambda k, t, e: logs.append(k))
        self.assertEqual(logs, ["절반 익절"])
        self.assertEqual(state["pending"][0]["칸"], 2)
        A.fill(state, day + "10", {"000001": 106.0})
        self.assertEqual(state["positions"]["000001"]["칸"], 2)
        self.assertEqual(state["closed"][0]["칸"], 2)


if __name__ == "__main__":
    unittest.main()


class LivePaper(unittest.TestCase):
    """장중 실행(run_live)이 체결된 매매를 모의투자 주문으로 넘기는지 — 09:01(전날 정한 매도) · 11:01(앞 봉 매수)."""

    def run_at(self, hhmm, state, plan, bars):
        import json
        import tempfile
        from datetime import datetime
        from pathlib import Path
        from unittest import mock
        import broker_kis
        import collect_kis_intraday
        import hlab
        import paper_trade
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            (home / "state.json").write_text(json.dumps(state), encoding="utf-8")
            now = datetime(2026, 10, 2, int(hhmm[:2]), int(hhmm[2:]), tzinfo=A.KST)
            with mock.patch.object(A, "PLAN", home / "plan.json"), mock.patch.object(A, "STATE", home / "state.json"), \
                    mock.patch.object(A, "ALERTS", home / "alerts.json", create=True), \
                    mock.patch.object(broker_kis, "market", return_value=object()), \
                    mock.patch.object(collect_kis_intraday, "market_open_today", return_value=True), \
                    mock.patch.object(A, "today_bars", side_effect=lambda client, c, day: bars.get(c, [])), \
                    mock.patch.object(hlab, "load", return_value={}), mock.patch.object(A, "kis_history", return_value=None), \
                    mock.patch.object(A, "send"), mock.patch.object(A, "_log_alerts", create=True), \
                    mock.patch.object(paper_trade, "execute", side_effect=lambda done, st, px, bar, now=None: calls.append((bar, [x["code"] for x in done], px)) or []):
                A.run_live(now)
                after = json.loads((home / "state.json").read_text(encoding="utf-8"))
        return calls, after

    def test_0901_fills_yesterdays_sell_at_open(self):
        state = {"positions": {"000001": {"code": "000001", "name": "가", "kind": "정배열", "price": 100.0, "peak": 100.0, "칸": 2,
                                          "처음칸": 2, "bars": 5, "bought": "2026093011", "max_close": 101.0}},
                 "pending": [{"type": "sell", "code": "000001", "칸": 2, "why": "정배열 깨짐", "decided": "2026100114"}],
                 "last_bar": "2026100114"}
        plan = {"base": "20261001", "candidates": []}
        bars = {"000001": [("2026100209", 97.0, 98.0, 96.0, 97.5, 10)]}
        calls, after = self.run_at("0901", state, plan, bars)
        self.assertEqual(calls, [("2026100209", ["000001"], {"000001": 97.0})])
        self.assertEqual(after["positions"], {})
        self.assertEqual(after["pending"], [])

    def test_nothing_due_at_0901_means_no_orders(self):
        plan = {"base": "20261001", "candidates": []}
        state = {"positions": {"000001": {"code": "000001", "name": "가", "kind": "정배열", "price": 100.0, "peak": 100.0, "칸": 2,
                                          "처음칸": 2, "bars": 5, "bought": "2026093011", "max_close": 101.0}},
                 "pending": [], "last_bar": "2026100114"}
        calls, after = self.run_at("0901", state, plan, {"000001": [("2026100209", 97.0, 98.0, 96.0, 97.5, 10)]})
        self.assertEqual(calls, [])
        self.assertIn("000001", after["positions"])


class FillAlerts(unittest.TestCase):
    """진입 · 청산 체결은 모두 디스코드 줄이 됨(사용자 요청 2026-10-01)."""

    def test_buy_and_sell_fills_become_lines(self):
        state = {"positions": {"000002": {"code": "000002", "name": "나", "kind": "추세", "price": 100.0, "peak": 110.0,
                                          "칸": 4, "처음칸": 4, "bars": 9, "bought": "2026093010", "max_close": 110.0}},
                 "pending": [{"type": "sell", "code": "000002", "칸": 4, "why": "익절 +13% 닿음", "decided": "2026100110"},
                             {"type": "buy", "code": "000001", "칸": 2, "decided": "2026100110", "kind": "정배열",
                              "name": "가", "why": "1시간봉 EMA 정배열이 됨"}]}
        px = {"000001": 50000.0, "000002": 113.0}
        done = A.fill(state, "2026100111", px)
        lines = A.fill_lines([("2026100111", done, px)])
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("매수 체결" in x and "가(000001)" in x and "11:00" in x and "50,000원" in x for x in lines))
        self.assertTrue(any("매도 체결" in x and "나(000002)" in x and "+12.7%" in x for x in lines))
