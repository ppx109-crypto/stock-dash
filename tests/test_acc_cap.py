"""계좌 흔들림 상한(acc_cap) 시험 — 연구 셈(research/z086.py)과 같은 식인지 · 사기 한도 · 덜어내기 · 끄기."""
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import acc_cap as A
import paper_trade as P


def cal(n, start=20260801):
    out, d = [], start
    while len(out) < n:
        out.append(str(d))
        d += 1
    return out


def bal(cash, pos=()):
    ps = [{"code": c, "quantity": q, "price": p} for c, q, p in pos]
    return {"cash": cash, "value": sum(q * p for _, q, p in pos), "positions": ps}


def z086_sigma(win, srcs, wv):
    """research/z086.py 157~193줄과 같은 셈(전날까지 LOOK+1날 · 앞 값 채움 · 전날 평가액 비중 · 표본 표준편차)."""
    held = sum(wv.values())
    rets = []
    for c, src in srcs.items():
        seq, last = [], None
        for x in win:
            v = src.get(x)
            v = float(v) if v else last
            seq.append(v)
            last = v
        rets.append((wv[c] / held, [seq[j] / seq[j - 1] - 1 for j in range(1, len(win))]))
    look = len(win) - 1
    port = [sum(w * r[t] for w, r in rets) for t in range(look)]
    m = sum(port) / look
    return math.sqrt(sum((x - m) ** 2 for x in port) / (look - 1))


class Sigma(unittest.TestCase):
    def setUp(self):
        days = cal(30)
        self.days = days
        a = {d: 100 * (1.02 if i % 2 else 0.99) ** i for i, d in enumerate(days)}
        b = {d: 50 + (i % 3) for i, d in enumerate(days) if i != 25}          # 하루 빠진 종목(앞 값으로 채움)
        self.data = {"000001": a, "000002": b, A.CAL_CODE: {d: 1.0 for d in days}}

    def get(self, c):
        return self.data.get(c, {})

    def test_same_as_research(self):
        day = self.days[28]
        qty = {"000001": 10, "000002": 30}
        sd, _ = A.sigma(day, qty, self.get)
        win = [d for d in self.days if d < day][-(A.LOOK + 1):]
        srcs = {c: self.data[c] for c in qty}
        last = {c: [srcs[c].get(x) for x in win if srcs[c].get(x)][-1] for c in qty}
        wv = {c: qty[c] * last[c] for c in qty}
        self.assertAlmostEqual(sd, z086_sigma(win, srcs, wv), places=12)

    def test_uses_only_days_before_today(self):
        day = self.days[28]
        sd1, _ = A.sigma(day, {"000001": 5}, self.get)
        self.data["000001"][day] = 1e9            # 오늘 값이 미쳐도(미래 참조 시험) 같아야 함
        self.data["000001"][self.days[29]] = 1e-9
        sd2, _ = A.sigma(day, {"000001": 5}, self.get)
        self.assertEqual(sd1, sd2)

    def test_missing_first_day_means_no_cap(self):
        self.data["000003"] = {d: 10.0 for d in self.days[20:]}
        sd, why = A.sigma(self.days[28], {"000001": 5, "000003": 5}, self.get)
        self.assertIsNone(sd)
        self.assertIn("첫날", why)
        self.assertEqual(A.allowed_from(sd), 1.0)

    def test_allowed(self):
        self.assertEqual(A.allowed_from(0.005), 1.0)
        self.assertAlmostEqual(A.allowed_from(0.02), A.TARGET / 0.02)


class Trim(unittest.TestCase):
    def test_same_fraction_from_every_book(self):
        b = bal(0, [("000001", 100, 1000), ("000002", 50, 2000)])          # 든 것 20만 · 현금 0
        plan, f = A.plan_trim(b, 0.6, {"1d": {"000001": 100}, "15m": {"000002": 50}})
        self.assertAlmostEqual(f, 0.4)
        self.assertEqual(sorted(plan), [("15m", "000002", 20), ("1d", "000001", 40)])

    def test_no_trim_under_cap(self):
        b = bal(100_000, [("000001", 100, 1000)])                           # 든 것 50%
        self.assertEqual(A.plan_trim(b, 0.6, {"1d": {"000001": 100}}), ([], 0.0))

    def test_never_sells_more_than_account(self):
        b = bal(0, [("000001", 10, 1000)])
        plan, _ = A.plan_trim(b, 0.0, {"1d": {"000001": 10}, "idle": {"000001": 10}})
        self.assertEqual(sum(q for _, _, q in plan), 10)


class Room(unittest.TestCase):
    def test_off_means_no_limit(self):
        with mock.patch.dict(os.environ, {"ACC_CAP": ""}):
            self.assertIsNone(A.room(bal(1000), "20261012"))

    def test_before_start_means_no_limit(self):
        with mock.patch.dict(os.environ, {"ACC_CAP": "on", "ACC_CAP_START": "20261012"}):
            self.assertIsNone(A.room(bal(1000), "20261009"))

    def test_room_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(A, "TODAY", Path(tmp) / "t.json"), \
                mock.patch.dict(os.environ, {"ACC_CAP": "on", "ACC_CAP_START": ""}), \
                mock.patch.object(A, "sigma", lambda day, qty, get=None: (A.TARGET / 0.5, "시험")):
            b = bal(600_000, [("000001", 400, 1000)])                       # 계좌 100만 · 든 것 40만 · E 0.5
            self.assertAlmostEqual(A.room(b, "20261012"), 100_000)
            t = json.loads((Path(tmp) / "t.json").read_text(encoding="utf-8"))
            self.assertEqual((t["date"], t["E"]), ("20261012", 0.5))
            t["trimmed_value"] = 50_000                                       # 오늘 덜어내려고 판 것은 든 것에서 뺌
            (Path(tmp) / "t.json").write_text(json.dumps(t), encoding="utf-8")
            self.assertAlmostEqual(A.room(b, "20261012"), 150_000)


class PlanOrdersRoom(unittest.TestCase):
    def test_buy_capped_by_room_plus_freed(self):
        done = [{"type": "buy", "code": "000001", "칸": 4, "decided": "d"}]
        b = bal(10_000_000)
        free = P.plan_orders(done, {"positions": {}}, b, {"000001": 1000}, "x", held={}, share=0.5)
        capped = P.plan_orders(done, {"positions": {}}, b, {"000001": 1000}, "x", held={}, share=0.5, room=300_000)
        self.assertEqual(free[0][3], 2000)
        self.assertEqual(capped[0][3], 300)
        none = P.plan_orders(done, {"positions": {}}, b, {"000001": 1000}, "x", held={}, share=0.5, room=0)
        self.assertEqual(none, [])


class RunTrim(unittest.TestCase):
    def test_trims_books_once_and_logs_ratios_only(self):
        class Fake:
            def __init__(self):
                self.sent = []

            def balance(self):
                return bal(0, [("000001", 100, 1000), ("069500", 10, 10_000)])

            def order(self, code, side, qty):
                self.sent.append((code, side, qty))
                return "1"
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            books = {"DAILY_BOOK": t / "d.json", "M15_BOOK": t / "m.json", "BOOK": t / "h.json",
                     "IDLE_BOOK": t / "i.json", "BASKET_BOOK": t / "b.json", "IDLE_STATE": t / "is.json",
                     "BASKET_STATE": t / "bs.json", "OFF": t / "off"}
            (t / "d.json").write_text(json.dumps({"orders": [], "held": {"000001": 100}}), encoding="utf-8")
            (t / "i.json").write_text(json.dumps({"orders": [], "held": {"069500": 10}}), encoding="utf-8")
            (t / "is.json").write_text(json.dumps({"positions": {"069500": {"day": "x"}}}), encoding="utf-8")
            with mock.patch.multiple(P, **books), mock.patch.object(A, "TODAY", t / "today.json"), \
                    mock.patch.object(A, "LOG", t / "log.json"), \
                    mock.patch.dict(os.environ, {"ACC_CAP": "on", "ACC_CAP_START": "", "PAPER_TRADING": "on", "KIS_PAPER_APP_KEY": "k",
                                                 "PAPER_START": ""}), \
                    mock.patch.object(A, "sigma", lambda day, qty, get=None: (A.TARGET / 0.5, "시험")):
                fake = Fake()
                lines = A.run_trim("20261012", broker=fake)
                again = A.run_trim("20261012", broker=fake)
            self.assertEqual(sorted(fake.sent), [("000001", "sell", 50), ("069500", "sell", 5)])
            self.assertEqual(again, [], "하루 한 번만")
            self.assertTrue(lines)
            self.assertEqual(json.loads((t / "d.json").read_text())["held"], {"000001": 50})
            self.assertEqual(json.loads((t / "i.json").read_text())["held"], {"069500": 5})
            log = json.loads((t / "log.json").read_text())
            self.assertEqual(log[0]["trim_f"], 0.5)
            self.assertNotIn("total", log[0])                 # 금액은 기록에 안 남김(비율만)
            self.assertNotIn("qty", log[0]["orders"][0])


if __name__ == "__main__":
    unittest.main()
