import importlib
import json
import math
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import overlay_live as O

ROOT = Path(__file__).resolve().parents[1]
KST = O.KST


class FakeBroker:
    """모의 계좌 흉내: 시장가는 지금 값에 바로 체결 · 비용 0.05% · 살 수 있는 수량 = 현금 ÷ (값 × 1.36)."""

    def __init__(self, cash, positions=None, prices=None):
        self.cash = float(cash)
        self.pos = dict(positions or {})
        self.px = dict(prices or {})
        self.orders = []
        self.fill = 1.0                     # 매도 체결 비율(0 = 접수만 · 0.5 = 절반)

    def raw(self):
        ps = [{"code": c, "name": c, "quantity": q, "price": self.px[c], "value": q * self.px[c]} for c, q in self.pos.items() if q > 0]
        return {"cash": self.cash, "value": sum(p["value"] for p in ps), "positions": ps}

    def balance(self, raw=False):
        return self.raw() if raw else O.base_view(self.raw())

    def buyable(self, code):
        return max(0, math.floor(self.cash / (self.px[code] * 1.36)))

    def order(self, code, side, qty):
        if side == "buy":
            O.yield_for(self, code, qty, now=self.now, quote=self.px.get)
            qty = min(qty, self.buyable(code))
            if qty < 1:
                raise RuntimeError("0주")
            self.cash -= qty * self.px[code] * (1 + O.COST_ETF)
            self.pos[code] = self.pos.get(code, 0) + qty
        else:
            qty = min(qty, self.pos.get(code, 0))
            got = int(qty * self.fill)
            self.cash += got * self.px[code] * (1 - O.COST_ETF)
            self.pos[code] -= got
        self.last_qty = qty
        self.orders.append((code, side, qty))
        return "1"


def rows_for(kind, n=60, end="20261008"):
    """끝날까지 국면이 kind가 되는 069500 종가 줄(날짜는 이어진 가짜 날 · 마지막 = end)."""
    if kind == "상승":
        xs = [100 + i for i in range(n)]
    elif kind == "하락":
        xs = [100.0] * (n - 12) + [100 - 1.5 * i for i in range(1, 13)]
    else:
        xs = [100.0 + (1 if i % 2 else -1) * 0.0 for i in range(n)]
    ds = [f"2026{(i // 28) + 1:02d}{(i % 28) + 1:02d}" for i in range(n - 1)] + [end]
    return list(zip(ds, xs))


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"MIX54": "on", "MIX54_START": "20261001", "PAPER_ROOM_WAIT": "0"})
        self.env.start()
        self.sleep = mock.patch.object(O.time, "sleep")
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.env.stop()
        os.chdir(self.old)
        self.tmp.cleanup()


class States(unittest.TestCase):
    def test_same_as_research_every_day(self):
        """연구 regime_dev.features · states(MIX-0054 최종 규칙)로 만든 기준표와 5,919일 모두 같음."""
        fx = json.loads((ROOT / "tests/fixtures/overlay_states.json").read_text(encoding="utf-8"))
        rows = [(str(d), float(c)) for d, c in fx["closes"]]           # 얼린 종가(실제 자료 파일이 바뀌어도 봇 앞 시험이 멈추지 않게)
        got = O.states(rows)
        self.assertEqual(len(fx["states"]), len(got))
        bad = [d for d, s in fx["states"].items() if got.get(d) != s]
        self.assertEqual(bad, [])

    def test_raw_state_rules(self):
        self.assertEqual(O.raw_state([100.0] * 10, 9), "횡보", "24일선 전에는 횡보")
        up = [100.0] * 30 + [110.0]
        self.assertEqual(O.raw_state(up, 30), "상승")
        down = [100.0] * 30 + [94.0]                      # 24일선 아래 · 10일 −6%
        self.assertEqual(O.raw_state(down, 30), "하락")
        soft = [100.0] * 30 + [97.0]                      # 24일선 아래 · 10일 −3% → 횡보
        self.assertEqual(O.raw_state(soft, 30), "횡보")

    def test_persist_three_days(self):
        xs = [100.0] * 30 + [110.0, 110.0]               # 그날 판정 '상승' 이틀 → 아직 횡보
        rows = [(f"d{i:03d}", x) for i, x in enumerate(xs)]
        self.assertEqual(O.states(rows)[rows[-1][0]], "횡보")
        rows.append(("d999", 111.0))                     # 사흘째 → 상승
        self.assertEqual(O.states(rows)["d999"], "상승")


class BaseView(Env):
    def test_identity_without_overlay(self):
        b = {"cash": 100.0, "value": 50.0, "positions": [{"code": "005930", "quantity": 1, "value": 50.0}]}
        self.assertIs(O.base_view(b), b)

    def test_contract(self):
        """NAV_b = 계좌 NAV − 덧붙임 평가액 + B · 바탕 현금 = 실제 현금 + B · 수량 단위로 뺌(다른 장부의 같은 종목은 남김)."""
        O.save_state({"held": {"122630": 100}, "B": 3800.0})
        b = {"cash": 1000.0, "value": 6000.0, "positions": [
            {"code": "122630", "quantity": 150, "price": 40.0, "value": 6000.0 - 1000.0},
            {"code": "005930", "quantity": 10, "price": 100.0, "value": 1000.0}]}
        v = O.base_view(b)
        self.assertAlmostEqual(v["cash"], 1000.0 + 3800.0)
        ov = 5000.0 * 100 / 150
        self.assertAlmostEqual(v["value"], 6000.0 - ov)
        self.assertAlmostEqual(v["cash"] + v["value"], (1000.0 + 6000.0) - ov + 3800.0)
        q = {p["code"]: p["quantity"] for p in v["positions"]}
        self.assertEqual(q, {"122630": 50, "005930": 10})

    def test_target_and_rebalance_rule(self):
        code, qty, f = O.target_qty("상승", 1000.0, 600.0, 1000.0, 0.0, 10.0)
        self.assertEqual((code, qty, f), ("122630", 40, 0.4))
        code, qty, f = O.target_qty("횡보", 1000.0, 300.0, 1000.0, 100.0, 10.0)   # 남는 바탕 현금 (300 − 100) ÷ 1000 = 0.2 < 0.4
        self.assertEqual((code, qty), ("114800", 20))
        self.assertAlmostEqual(f, 0.2)
        self.assertEqual(O.target_qty("하락", 1000.0, 600.0, 1000.0, 0.0, 10.0)[1], 0)
        st = {"applied": "상승", "rebalanced_month": "202610"}
        self.assertFalse(O.needs_rebalance(st, "상승", "20261015"))
        self.assertTrue(O.needs_rebalance(st, "횡보", "20261015"))
        self.assertTrue(O.needs_rebalance(st, "상승", "20261102"), "달 첫 맞춤")


class Run(Env):
    NOW = datetime(2026, 10, 12, 15, 12, tzinfo=KST)

    def go(self, broker, kind, day="20261012", prev="20261008", reserve=0.0):
        broker.now = self.NOW
        with mock.patch.object(O, "closes", lambda before=None, code=O.SIGNAL: rows_for(kind, end=prev)):
            return O.run(broker, None, day, reserve=reserve, now=self.NOW, quote=broker.px.get, prev_day=prev)

    def test_off_does_nothing(self):
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        with mock.patch.dict(os.environ, {"MIX54": "off"}):
            self.assertEqual(self.go(b, "상승"), [])
        with mock.patch.dict(os.environ, {"MIX54_START": "20261101"}):
            self.assertEqual(self.go(b, "상승"), [])
        Path("overlay-live").mkdir()
        Path("overlay-live/off").write_text("")
        self.assertEqual(self.go(b, "상승"), [])
        self.assertEqual(b.orders, [])

    def test_first_rebalance_up(self):
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        lines = self.go(b, "상승")
        self.assertEqual(b.orders, [("122630", "buy", 4000)])            # 0.4 × 1,000,000 ÷ 100
        st = O.load_state()
        self.assertEqual(st["held"], {"122630": 4000})
        self.assertAlmostEqual(st["B"], 4000 * 100.0)                     # B = 맞춘 뒤 덧붙임 평가액
        self.assertEqual((st["applied"], st["rebalanced_month"]), ("상승", "202610"))
        v = b.balance()                                                   # 바탕은 덧붙임 없을 때와 같은 NAV(비용만큼 빼고)
        self.assertAlmostEqual(v["cash"] + v["value"], b.cash + 4000 * 100.0)
        self.assertTrue(any("덧붙임" in x for x in lines))
        self.assertEqual(self.go(b, "상승"), [], "같은 날 두 번 안 함")

    def test_room_caps_size(self):
        b = FakeBroker(300_000, positions={"005930": 7}, prices={"005930": 100_000.0, "122630": 100.0, "114800": 50.0})
        self.go(b, "상승", reserve=100_000 / 1.36)
        # 바탕 현금 300,000 − 1일봉 몫 100,000 = 200,000 · ÷ NAV 1,000,000 = 0.2 → 2,000주
        self.assertEqual(b.orders, [("122630", "buy", 2000)])

    def test_switch_up_to_side_and_down(self):
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        self.go(b, "상승")
        st = O.load_state()
        st["last_day"] = "20261012"
        O.save_state(st)
        b.orders.clear()
        self.go(b, "횡보", day="20261013", prev="20261012")
        self.assertEqual(b.orders[0], ("122630", "sell", 4000))
        self.assertEqual(b.orders[1][:2], ("114800", "buy"))
        st = O.load_state()
        self.assertEqual(list(st["held"]), ["114800"])
        self.assertAlmostEqual(st["B"], st["held"]["114800"] * 50.0)
        b.orders.clear()
        self.go(b, "하락", day="20261014", prev="20261013")
        self.assertEqual(b.orders, [("114800", "sell", st["held"]["114800"])])
        st = O.load_state()
        self.assertEqual((st["held"], st["B"]), ({}, 0.0))                 # 다 팔면 B = 0
        v = b.balance()
        self.assertIs(type(v), dict)
        self.assertAlmostEqual(v["cash"], b.cash)

    def test_stale_data_no_rebalance(self):
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        b.now = self.NOW
        with mock.patch.object(O, "closes", lambda before=None, code=O.SIGNAL: rows_for("상승", end="20261007")):
            lines = O.run(b, None, "20261012", now=self.NOW, quote=b.px.get, prev_day="20261008")
        self.assertEqual(b.orders, [])
        self.assertTrue(any("종가가 아직 없어" in x for x in lines))

    def test_yield_for_base_buy_and_auction(self):
        """바탕 봇이 사는데 현금이 모자라면 덧붙임을 먼저 팖 · B는 순수입만큼 줄어듦 · 15:20(동시호가)부터는 안 팖."""
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0, "005930": 1000.0})
        self.go(b, "상승")
        B0, cash0 = O.load_state()["B"], b.cash
        want = b.buyable("005930") + 100                                    # 실제 현금으로는 100주 모자람(바탕 현금으로는 넉넉)
        self.assertLess(want, math.floor(b.balance()["cash"] / (1000.0 * 1.36)))
        b.order("005930", "buy", want)
        sold = [o for o in b.orders if o[0] == "122630" and o[1] == "sell"]
        self.assertEqual(len(sold), 1)
        n = sold[0][2]
        st = O.load_state()
        self.assertAlmostEqual(st["B"], B0 - n * 100.0 * (1 - O.COST_ETF))
        self.assertEqual(st["held"]["122630"], 4000 - n)
        self.assertEqual(b.pos["005930"], want, "바탕 매수는 다 들어감")
        b.now = datetime(2026, 10, 12, 15, 21, tzinfo=KST)
        before = len(b.orders)
        b.order("005930", "buy", 10_000)
        self.assertFalse(any(o[0] == "122630" for o in b.orders[before:]), "동시호가에서는 덧붙임을 안 팖")

    def test_prepare_reserve(self):
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        self.go(b, "상승")
        cash = b.cash                                                       # 약 599,800
        sold = O.prepare(b, reserve=600_000, now=self.NOW, quote=b.px.get)  # 15:20 1일봉 몫 × 1.36 = 816,000이 실제 현금으로 있어야 함
        self.assertGreater(sold, 0)
        self.assertGreaterEqual(b.cash * 0.98 + 1e-6, 600_000 * 1.36)
        self.assertGreater(b.cash, cash)


class OffAndFills(Env):
    NOW = Run.NOW
    go = Run.go

    def setup_held(self):
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0, "005930": 1000.0})
        self.go(b, "상승")
        b.orders.clear()
        return b

    def test_off_blocks_new_yield_sells(self):
        """덧붙임을 든 채로 꺼도(MIX54 off · 시작 전 · off 파일) 바탕 매수 때 덧붙임 매도가 새로 나가지 않음 · prepare도 0."""
        for case in ("off", "before", "file"):
            with self.subTest(case=case):
                b = self.setup_held() if case == "off" else b
                st0 = O.load_state()
                patch = {"off": {"MIX54": "off"}, "before": {"MIX54_START": "20261101"}, "file": {}}[case]
                if case == "file":
                    Path("overlay-live/off").write_text("")
                with mock.patch.dict(os.environ, patch):
                    want = b.buyable("005930") + 100
                    b.order("005930", "buy", want)
                    self.assertFalse(any(o[0] == "122630" for o in b.orders), case)
                    self.assertEqual(O.prepare(b, reserve=900_000, now=self.NOW, quote=b.px.get), 0.0)
                    self.assertEqual(O.sell_for(b, 1e9, now=self.NOW, quote=b.px.get), 0.0)
                self.assertEqual(O.load_state()["held"], st0["held"])
                b.orders.clear()
        Path("overlay-live/off").unlink()

    def test_accepted_but_not_filled(self):
        b = self.setup_held()
        st0 = O.load_state()
        b.fill = 0.0
        got = O.sell_for(b, 100_000, now=self.NOW, quote=b.px.get)
        st = O.load_state()
        self.assertEqual(got, 0.0)
        self.assertEqual((st["held"], st["B"]), (st0["held"], st0["B"]), "0주 체결이면 장부 그대로")
        self.assertEqual(st["unconfirmed"]["code"], "122630")
        book = json.loads(Path("overlay-live/paper-orders.json").read_text(encoding="utf-8"))
        self.assertEqual(book["orders"][-1]["filled"], 0)

    def test_partial_fill(self):
        b = self.setup_held()
        st0 = O.load_state()
        b.fill = 0.5
        O.sell_for(b, 100_000, now=self.NOW, quote=b.px.get)
        st = O.load_state()
        asked = math.ceil(100_000 / (100.0 * (1 - O.COST_ETF)))
        got = int(asked * 0.5)
        self.assertEqual(st["held"]["122630"], 4000 - got)
        self.assertAlmostEqual(st["B"], st0["B"] - got * 100.0 * (1 - O.COST_ETF))
        self.assertEqual(st["unconfirmed"]["qty"], asked - got)

    def test_reconcile_with_real_balance(self):
        """미확인 매도가 나중에 체결돼 실제 잔고가 줄었으면, 다음 실행 앞에서 장부를 실제 수량으로 줄이고 B도 순수입만큼 줄임."""
        b = self.setup_held()
        st = O.load_state()
        b.pos["122630"] = 3000
        st2 = O.reconcile(dict(st, unconfirmed={"code": "122630", "qty": 1000}), b.raw(), quote=b.px.get)
        self.assertEqual(st2["held"], {"122630": 3000})
        self.assertAlmostEqual(st2["B"], st["B"] - 1000 * 100.0 * (1 - O.COST_ETF))
        self.assertNotIn("unconfirmed", st2)


class SwitchFills(Env):
    """국면 바뀌는 날 옛 ETF 매도가 0주 · 일부만 체결돼도 실제 잔량을 장부에 남기고(B 포함) 다음 날 다시 맞춤(GPT #230 round 2)."""
    NOW = Run.NOW
    go = Run.go

    def start_up(self):
        b = FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        self.go(b, "상승")
        b.orders.clear()
        return b

    def check_view(self, b):
        v, raw = b.balance(), b.raw()
        st = O.load_state()
        ov = sum(q * b.px[c] for c, q in st["held"].items())
        self.assertAlmostEqual(v["cash"] + v["value"], raw["cash"] + raw["value"] - ov + st["B"], places=4)
        self.assertAlmostEqual(st["B"], ov, places=4, msg="맞춘 날 B = 덧붙임 평가액(남은 옛 종목 포함)")

    def test_up_to_side_zero_fill_then_retry(self):
        b = self.start_up()
        b.fill = 0.0
        lines = self.go(b, "횡보", day="20261013", prev="20261012")
        st = O.load_state()
        self.assertEqual(st["held"]["122630"], 4000, "못 판 옛 종목은 장부에 그대로")
        self.assertIn("114800", st["held"])
        self.assertIsNone(st["applied"])
        self.assertTrue(any("다 체결되지 않음" in x for x in lines))
        self.check_view(b)
        b.fill = 1.0
        b.orders.clear()
        self.go(b, "횡보", day="20261014", prev="20261013")
        st = O.load_state()
        self.assertEqual(b.orders[0], ("122630", "sell", 4000))
        self.assertEqual(list(st["held"]), ["114800"])
        self.assertEqual(st["applied"], "횡보")
        self.check_view(b)

    def test_up_to_side_partial(self):
        b = self.start_up()
        b.fill = 0.5
        self.go(b, "횡보", day="20261013", prev="20261012")
        st = O.load_state()
        self.assertEqual(st["held"]["122630"], 2000)
        self.assertIsNone(st["applied"])
        self.check_view(b)

    def test_up_to_down_zero_fill_then_retry(self):
        b = self.start_up()
        b.fill = 0.0
        self.go(b, "하락", day="20261013", prev="20261012")
        st = O.load_state()
        self.assertEqual(st["held"], {"122630": 4000})
        self.assertAlmostEqual(st["B"], 4000 * 100.0)
        self.assertIsNone(st["applied"])
        self.check_view(b)
        b.fill = 1.0
        self.go(b, "하락", day="20261014", prev="20261013")
        st = O.load_state()
        self.assertEqual((st["held"], st["B"], st["applied"]), ({}, 0.0, "하락"))

    def test_reconcile_pending_adds_bought(self):
        b = FakeBroker(100_000, positions={"114800": 500}, prices={"114800": 50.0})
        st = O.reconcile({"held": {}, "B": 0.0, "pending": ["114800"]}, b.raw(), quote=b.px.get)
        self.assertEqual(st["held"], {"114800": 500})
        self.assertAlmostEqual(st["B"], 500 * 50.0)
        self.assertNotIn("pending", st)


class SkipNote(unittest.TestCase):
    def test_zero_share_rule_says_turned_off(self):
        """15분봉 몫이 0(최종 판)이면 매수 신호를 '살 돈이 모자람'이 아니라 '새 매수를 끔'으로 알림."""
        import paper_trade as P

        class B:
            def balance(self, raw=False):
                return {"cash": 1_000_000.0, "value": 0.0, "positions": []}

        tmp = tempfile.TemporaryDirectory()
        old = os.getcwd()
        os.chdir(tmp.name)
        try:
            with mock.patch.dict(os.environ, {"PAPER_TRADING": "on", "KIS_PAPER_APP_KEY": "k", "PAPER_START": ""}), \
                    mock.patch.dict(P.SHARES, {"15m": 0.0}):
                lines = P.execute([{"type": "buy", "code": "005930", "칸": 2, "name": "삼성전자"}], {"positions": {}}, {"005930": 70000.0},
                                  "b1", broker=B(), strategy="15m")
        finally:
            os.chdir(old)
            tmp.cleanup()
        self.assertTrue(any("새 매수를 끔" in x for x in lines), lines)


class NavWatch(unittest.TestCase):
    def test_day_and_month(self):
        st = {}
        lines, st = O.nav_watch(st, "20261001", 100.0)
        self.assertEqual((lines, st["month_start_nav"]), ([], 100.0))
        lines, st = O.nav_watch(st, "20261002", 89.0)
        self.assertTrue(any("하루 손실" in x for x in lines))
        self.assertFalse(any("그달" in x for x in lines))                 # −11% < 12%
        lines, st = O.nav_watch(st, "20261005", 86.0)
        self.assertTrue(any("그달 손실" in x for x in lines))
        lines, st = O.nav_watch(st, "20261102", 85.0)                      # 달이 바뀌면 그달 시작 = 전달 마지막(86)
        self.assertEqual(st["month_start_nav"], 86.0)


class PaperHooks(unittest.TestCase):
    def test_shares_switch(self):
        import paper_trade as P
        with mock.patch.dict(os.environ, {"MIX54": "on", "MIX54_START": "20000101", "PAPER_SHARE_15M": "0.5"}):
            P2 = importlib.reload(P)
            self.assertEqual((P2.SHARES["15m"], P2.BASKET_SHARE), (0.0, 0.3))
        with mock.patch.dict(os.environ, {"MIX54": "off"}):
            P2 = importlib.reload(P)
            self.assertEqual((P2.SHARES["15m"], P2.BASKET_SHARE), (0.5, 0.5))
        with mock.patch.dict(os.environ, {"MIX54": "on", "MIX54_START": "29991231"}):
            P2 = importlib.reload(P)
            self.assertEqual(P2.SHARES["15m"], 0.5, "시작 날 전에는 그대로")
        importlib.reload(P)

    def test_order_calls_yield_before_buyable_and_balance_view(self):
        import paper_trade as P
        env = {"KIS_PAPER_APP_KEY": "pk", "KIS_PAPER_APP_SECRET": "s", "KIS_PAPER_ACCOUNT": "12345678-01", "KIS_APP_KEY": "rk"}
        with mock.patch.dict(os.environ, env):
            b = P.PaperBroker()
        b.token = "t"
        calls = []
        with mock.patch.object(O, "yield_for", lambda br, c, q: calls.append(("yield", c, q))), \
                mock.patch.object(b, "buyable", lambda c: calls.append(("buyable", c)) or 5), \
                mock.patch.object(b, "authorize"), mock.patch.object(b, "request", return_value=(None, {"rt_cd": "0", "output": {"ODNO": "1"}})):
            b.order("005930", "buy", 3)
            b.order("005930", "sell", 3)
        self.assertEqual(calls, [("yield", "005930", 3), ("buyable", "005930")], "매수만 · 매수가능 조회보다 먼저")
        raw = {"cash": 10.0, "value": 0.0, "positions": [], "cash_d2": 10.0}
        with mock.patch("broker_kis.KIS.balance", return_value=dict(raw)), mock.patch.object(O, "base_view", lambda x: dict(x, view=True)):
            self.assertTrue(b.balance()["view"])
            self.assertNotIn("view", b.balance(raw=True))


if __name__ == "__main__":
    unittest.main()
