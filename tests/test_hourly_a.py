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

    def test_stale_plan_blocks_new_buys_but_keeps_sells(self):
        """후보 기준일이 어제 거래일이 아니면(낡은 후보) 새로 사지 않음 · 정해 둔 매도는 그대로(사용자 요청 2026-10-02)."""
        from unittest import mock
        import data_guard
        state = {"positions": {"000001": {"code": "000001", "name": "가", "kind": "정배열", "price": 100.0, "peak": 100.0, "칸": 2,
                                          "처음칸": 2, "bars": 5, "bought": "2026093011", "max_close": 101.0}},
                 "pending": [{"type": "sell", "code": "000001", "칸": 2, "why": "정배열 깨짐", "decided": "2026093014"},
                             {"type": "buy", "code": "000009", "칸": 2, "why": "옛 매수", "decided": "2026093014"}],
                 "last_bar": "2026093014"}
        plan = {"base": "20260930", "candidates": [{"code": "000002", "name": "나", "추세문": True}]}
        bars = {"000001": [("2026100209", 97.0, 98.0, 96.0, 97.5, 10)],
                "000002": [("2026100209", 50.0, 60.0, 50.0, 60.0, 10), ("2026100210", 61.0, 61.0, 61.0, 61.0, 10)]}
        with mock.patch.object(data_guard, "prev_trading_day", return_value="20261001"):
            calls, after = self.run_at("1101", state, plan, bars)
        self.assertNotIn("000002", after["positions"])
        self.assertNotIn("000001", after["positions"], "정해 둔 매도는 체결")
        self.assertEqual(after.get("자료 멈춤"), "20261002")

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


class KisHistory(unittest.TestCase):
    """야후 1시간봉이 없는 종목: 한투 1시간봉 + 한투 15분봉(1시간으로 묶음)을 함께 읽음(2026-10-02 · 1시간봉 따로 받기 멈춤)."""

    def test_reads_hourly_and_m15_together(self):
        import os
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "hourly-kis" / "000001").mkdir(parents=True)
            (Path(tmp) / "m15-kis" / "000001").mkdir(parents=True)
            (Path(tmp) / "hourly-kis" / "000001" / "2026.csv").write_text(
                "2026092914,1,1,1,100,1\n2026092915,1,1,1,101,1\n", encoding="utf-8")
            (Path(tmp) / "m15-kis" / "000001" / "2026.csv").write_text(
                "202609300900,1,1,1,102,1\n202609300945,1,1,1,103,1\n202609301500,1,1,1,104,1\n202609301515,1,1,1,105,1\n",
                encoding="utf-8")
            here = os.getcwd()
            os.chdir(tmp)
            try:
                got = A.kis_history("000001")
            finally:
                os.chdir(here)
        self.assertEqual(got["t"], ["2026092914", "2026093009", "2026093014"])
        self.assertEqual(got["c"], [101.0, 103.0, 105.0], "그 시간 마지막 봉 · 15시는 14시에 합쳐 마감 종가")


class History(unittest.TestCase):
    def test_yahoo_then_kis_fills_days_after_yahoo_ends(self):
        yahoo = {"t": ["2026092913", "2026092914"], "c": [1.0, 2.0]}
        kis = {"t": ["2026092914", "2026093009", "2026100114", "2026100209"], "c": [9.0, 3.0, 4.0, 5.0]}
        t, c = A.history_bars(yahoo, kis, "20261002")
        self.assertEqual(t, ["2026092913", "2026092914", "2026093009", "2026100114"], "야후 뒤 날만 한투로 · 오늘 봉은 뺌")
        self.assertEqual(c, [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(A.history_bars(None, kis, "20261002")[0], ["2026092914", "2026093009", "2026100114"])
        self.assertEqual(A.history_bars(None, None, "20261002"), ([], []))

    def test_live_load_is_not_cut_by_research_holdout(self):
        import os
        import hlab
        old = os.environ.pop("HLAB_OPEN_HOLDOUT", None)
        try:
            os.environ["HLAB_OPEN_HOLDOUT"] = "1"
            self.assertIsNone(hlab.bar_limit())
        finally:
            os.environ.pop("HLAB_OPEN_HOLDOUT", None)
            if old is not None:
                os.environ["HLAB_OPEN_HOLDOUT"] = old


class NearNow(unittest.TestCase):
    """장중 매시 '조건이 1개만 모자란 종목'을 지금 값으로 다시 세어 판정 시각과 남김(사용자 요청 2026-10-02)."""

    def test_outside_market_hours_does_nothing(self):
        from datetime import datetime
        from unittest import mock

        class NoCall:
            def __getattr__(self, name):
                raise AssertionError("장 밖에서는 증권사에 묻지 않음")
        with mock.patch.object(A, "_save") as save:
            self.assertEqual(A.refresh_near(datetime(2026, 10, 2, 18, 0, tzinfo=A.KST), client=NoCall()), 0)
            self.assertEqual(A.refresh_near(datetime(2026, 10, 3, 10, 0, tzinfo=A.KST), client=NoCall()), 0)   # 토요일
            save.assert_not_called()

    def test_saves_near_with_judged_time(self):
        import tempfile
        from datetime import datetime
        from pathlib import Path
        from unittest import mock
        import caps
        import collect_kis_intraday as I
        import final_group
        import study

        class Client:
            def quote(self, code):
                return {"price": 110.0}
        prices = {"000001": {"name": "가", "rows": [("20261001", 100.0)]}, "000002": {"name": "나", "rows": [("20261001", 50.0)]}}
        seen = {}

        def compute(live, calm=None):
            seen["live"] = live
            return {"date": "20261002", "breadth": 55.0, "picks": [{"code": "000001", "name": "가", "갈래": ["정배열"]}],
                    "b_group": [{"code": "000002", "name": "나", "모자란 수": 1, "가까운 갈래": "정배열", "모자란 것": {"정배열": ["간격"]}},
                                {"code": "000003", "name": "다", "모자란 수": 2}]}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(A, "NEAR_NOW", Path(tmp) / "near-now.json"), \
                mock.patch.object(study, "load_prices", return_value=prices), \
                mock.patch.object(caps, "tag", side_effect=lambda rows, n: [r.update({caps.RANK: 1}) for r in rows]), \
                mock.patch.object(I, "market_open_today", return_value=True), \
                mock.patch.object(final_group, "compute", side_effect=compute):
            self.assertEqual(A.refresh_near(datetime(2026, 10, 2, 11, 1, tzinfo=A.KST), client=Client()), 0)
            body = A._load(Path(tmp) / "near-now.json", None)
        self.assertEqual(body["at"], "2026-10-02 11:01")
        self.assertEqual(body["date"], "20261002")
        self.assertEqual([r["code"] for r in body["near"]], ["000002"], "1개만 모자란 것만")
        self.assertEqual([r["code"] for r in body["picks"]], ["000001"])
        self.assertEqual(seen["live"]["000001"]["rows"][-1], ("20261002", 110.0), "지금 값을 오늘 값으로 붙여 셈")


class NearDaily(unittest.TestCase):
    def test_target_cut_moves_pick_to_daily_near(self):
        import tempfile
        from datetime import datetime
        from pathlib import Path
        from unittest import mock
        import caps
        import collect_kis_intraday as I
        import daily_live
        import final_group
        import study

        class Client:
            def quote(self, code):
                return {"price": 110.0}
        prices = {"000001": {"name": "가", "rows": [("20261001", 100.0)]}, "000002": {"name": "나", "rows": [("20261001", 50.0)]}}
        found = {"date": "20261002", "breadth": 55.0, "picks": [{"code": "000001", "name": "가", "갈래": ["정배열"]},
                                                                 {"code": "000002", "name": "나", "갈래": ["정배열"]}], "b_group": []}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(study, "load_prices", return_value=prices), \
                mock.patch.object(caps, "tag", side_effect=lambda rows, n: [r.update({caps.RANK: 1}) for r in rows]), \
                mock.patch.object(I, "market_open_today", return_value=True), \
                mock.patch.object(final_group, "compute", return_value=found), \
                mock.patch.object(daily_live, "target_cut", side_effect=lambda c, d: c == "000002"):
            out = Path(tmp) / "near-now.json"
            A.refresh_near(datetime(2026, 10, 2, 10, 18, tzinfo=A.KST), client=Client(), out=out)
            body = A._load(out, None)
        self.assertEqual([p["code"] for p in body["picks"]], ["000001", "000002"])
        self.assertEqual([p["code"] for p in body["picks_daily"]], ["000001"])
        self.assertEqual([r["code"] for r in body["near_daily"]], ["000002"])
