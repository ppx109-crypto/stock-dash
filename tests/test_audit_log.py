"""판단 기록장(audit_log · BOOST-0001-A) 시험: 기록이 매매를 바꾸지 않음 · 실패해도 멈추지 않음(구조로 보장) ·
기록으로 판단을 다시 돌릴 수 있음 · 비밀이 안 들어감."""
import ast
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import audit_log as A
import overlay_live  # noqa: F401  (저장소 맨 위에서 먼저 불러 둠 · 코드 판 경로가 지금 폴더에 흔들리지 않는지도 봄)

ROOT = Path(__file__).resolve().parents[1]
BOTS = ("daily_live.py", "idle_live.py", "basket_live.py", "overlay_live.py")


class Plain(unittest.TestCase):
    def test_kinds(self):
        x = {"a": np.array([1.5, 2.0]), "b": np.float64(0.1), "c": {3, 1, 2}, "d": float("nan"), "e": Path("x/y"),
             "f": (1, [2, (3,)]), 7: None, "g": np.int64(4), "h": object(), "i": np.float64("nan")}
        p = A.plain(x)
        self.assertEqual(p["a"], [1.5, 2.0])
        self.assertEqual(p["b"], 0.1)
        self.assertEqual(p["c"], [1, 2, 3])
        self.assertTrue(math.isnan(p["d"]) and math.isnan(p["i"]))     # nan은 실수 그대로(JSON NaN으로 왕복)
        self.assertEqual(p["e"], "x/y")
        self.assertEqual(p["f"], [1, [2, [3]]])
        self.assertIsNone(p["7"])
        self.assertEqual(p["g"], 4)
        self.assertTrue(p["h"].startswith("<object"))
        back = json.loads(json.dumps(p))
        self.assertEqual(A.canon(back), A.canon(p))

    def test_digest_order_free_and_safe(self):
        self.assertEqual(A.digest({"a": 1, "b": [1, 2]}), A.digest({"b": [1, 2], "a": 1}))
        self.assertNotEqual(A.digest({"a": 1}), A.digest({"a": 1.0000001}))
        self.assertEqual(A.digest({"x": float("nan")}), A.digest({"x": float("nan")}))

        class Bad:
            def __repr__(self):
                raise ValueError("x")
        self.assertIsNone(A.digest(Bad()))              # 못 떠도 예외 없음

    def test_capture_copy_and_safe(self):
        st = {"positions": {"A": {"칸": 2}}}
        got = A.capture({"state": st})
        st["positions"]["A"]["칸"] = 0                  # 판단 함수가 입력을 고쳐도
        self.assertEqual(got["state"]["positions"]["A"]["칸"], 2)

        class Bad:
            def __repr__(self):
                raise ValueError("x")
        with mock.patch("builtins.print"):
            self.assertIsNone(A.safe(lambda: A.capture({"x": Bad()})))
            self.assertIsNone(A.safe(lambda: {}["없는 열쇠"]))            # 인자 만들기에서 난 예외도 삼킴
        self.assertEqual(A.safe(lambda: 3), 3)

    def test_file_ids(self):
        ids = A.file_ids(ROOT / "idle_live.py", ROOT / "research" / "idle_signal.py")
        self.assertEqual(sorted(ids), ["idle_live.py", "research/idle_signal.py"])
        blob = subprocess.run(["git", "hash-object", str(ROOT / "idle_live.py")], capture_output=True, text=True).stdout.strip()
        self.assertEqual(ids["idle_live.py"], blob)     # git 블롭 id와 같음(감사가 git에서 같은 판을 꺼냄)
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                self.assertEqual(A.file_ids(ROOT / "idle_live.py"), {"idle_live.py": blob})    # 지금 폴더와 상관없음
            finally:
                os.chdir(old)
        self.assertEqual(overlay_live._CODE, {"overlay_live.py": A.blob_id(ROOT / "overlay_live.py")})


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "idle-live"
        self.dir.mkdir()
        self.state = self.dir / "state.json"
        self.state.write_text('{"positions": {}}', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_then_after(self):
        inp = A.capture({"day": "20261109", "px": {"069500": np.array([1.0, 2.0])}})
        p = A.record(self.state, "20261109", "engine", inp, {"orders": [("069500", "buy", 3, "까닭")]},
                     ledgers=(self.state, self.dir / "없는.json"), extra={"cap": None}, code={"idle_live.py": "a" * 40})
        self.assertEqual(p, self.dir / "audit" / "20261109-engine.json")
        body = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(body["입력"], inp)
        self.assertEqual(body["결과"], {"orders": [["069500", "buy", 3, "까닭"]]})
        self.assertEqual(body["입력 지문"], A.digest(inp))
        self.assertEqual(body["결과 지문"], A.digest(body["결과"]))
        self.assertEqual(body["장부 지문(판단 앞)"][str(self.state)], A.file_digest(self.state))
        self.assertIsNone(body["장부 지문(판단 앞)"][str(self.dir / "없는.json")])
        self.assertEqual((body["곁"], body["코드"]), ({"cap": None}, {"idle_live.py": "a" * 40}))
        for k in ("기록 시각(한국)", "작업 번호", "작업 시도", "부른 까닭", "작업 코드 커밋", "판단 때 저장소 HEAD"):
            self.assertIn(k, body)
        self.state.write_text('{"positions": {"069500": 3}}', encoding="utf-8")
        A.after(self.state, "20261109", "engine", {"late": False}, ledgers=(self.state,))
        body = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(body["주문 결과"], {"late": False})
        self.assertEqual(body["장부 지문(판단 뒤)"][str(self.state)], A.file_digest(self.state))
        self.assertNotEqual(body["장부 지문(판단 뒤)"][str(self.state)], body["장부 지문(판단 앞)"][str(self.state)])
        self.assertIn("결과", body)                     # 덧붙여도 판단 기록은 그대로
        self.assertNotIn("오늘 장부 주문", body)

    def test_after_books(self):
        """오늘 장부 주문: 그날 열쇠만 · 못 읽는 장부는 '읽기 실패'로 적고 나머지는 그대로."""
        book = self.dir / "paper-orders.json"
        book.write_text(json.dumps({"orders": [{"key": "20261108:buy:A", "status": "접수"}, {"key": "20261109:buy:B", "status": "접수"},
                                               {"key": "202611091512:room:C", "status": "실패 · x"}]}), encoding="utf-8")
        bad = self.dir / "bad.json"
        bad.write_text("[1, 2]", encoding="utf-8")
        p = A.after(self.state, "20261109", "engine", {"x": 1}, books=(book, bad, self.dir / "없음.json"))
        body = json.loads(p.read_text(encoding="utf-8"))
        got = body["오늘 장부 주문"]
        self.assertEqual([o["key"] for o in got[str(book)]], ["20261109:buy:B", "202611091512:room:C"])
        self.assertTrue(got[str(bad)].startswith("읽기 실패"))
        self.assertEqual(got[str(self.dir / "없음.json")], [])
        self.assertEqual(body["주문 결과"], {"x": 1})

    def test_after_without_record(self):
        p = A.after(self.state, "20261109", "overlay", {"rebalance": False})
        body = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual((body["날"], body["봇"], body["주문 결과"]), ("20261109", "overlay", {"rebalance": False}))

    def test_failures_never_raise(self):
        (self.dir / "audit").write_text("파일이라 폴더를 못 만듦")
        with mock.patch("builtins.print") as pr:
            self.assertIsNone(A.record(self.state, "20261109", "engine", {}, {}))
            self.assertIsNone(A.after(self.state, "20261109", "engine", {}))
        self.assertEqual(pr.call_count, 2)


class Recorder(unittest.TestCase):
    def test_passes_answer_and_records(self):
        calls = []
        f = A.recorder(lambda code, holding: code not in holding, calls)
        h = ["A"]
        self.assertTrue(f("B", h))
        h.append("B")                                   # 판단 함수가 목록을 뒤에 고쳐도 기록은 그때 값
        self.assertFalse(f("A", h))
        self.assertEqual(calls, [["B", ["A"], True], ["A", ["A", "B"], False]])

    def test_error_passes_through(self):
        def boom(x):
            raise KeyError(x)
        with self.assertRaises(KeyError):               # 원래 함수가 내던 예외는 그대로(행동 같음)
            A.recorder(boom, [])("x")


class Structure(unittest.TestCase):
    """기록 줄이 매매를 멈출 수 없음을 구조로 확인: `_audit.` 은 ① 모듈 맨 위 try 안 file_ids ② `if _audit` 아래의 safe · recorder
    ③ safe(lambda: …) 안에서만 씀. 판단 · 주문 줄에서 바뀐 것은 recorder로 감싼 인자뿐."""

    def parents(self, tree):
        par = {}
        for node in ast.walk(tree):
            for ch in ast.iter_child_nodes(node):
                par[ch] = node
        return par

    @staticmethod
    def is_audit(node):
        return isinstance(node, ast.Name) and node.id == "_audit"

    def guarded(self, node, par):
        """`if _audit:` 몸통 · `… if _audit else …`의 앞쪽 · `_audit and …`의 뒤쪽 안에 있는지."""
        cur = node
        while cur in par:
            up = par[cur]
            if isinstance(up, ast.If) and cur in up.body and (self.is_audit(up.test) or (
                    isinstance(up.test, ast.BoolOp) and isinstance(up.test.op, ast.And) and self.is_audit(up.test.values[0]))):
                return True
            if isinstance(up, ast.IfExp) and self.is_audit(up.test) and cur is up.body:
                return True
            if isinstance(up, ast.BoolOp) and isinstance(up.op, ast.And) and self.is_audit(up.values[0]) and cur is not up.values[0]:
                return True
            cur = up
        return False

    def in_safe_lambda(self, node, par):
        cur = node
        while cur in par:
            up = par[cur]
            if isinstance(up, ast.Lambda):
                call = par.get(up)
                if isinstance(call, ast.Call) and call.args and call.args[0] is up and isinstance(call.func, ast.Attribute) \
                        and call.func.attr == "safe" and isinstance(call.func.value, ast.Name) and call.func.value.id == "_audit":
                    return True
            cur = up
        return False

    def test_every_use_is_guarded(self):
        for name in BOTS:
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            par = self.parents(tree)
            uses = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "_audit"]
            self.assertTrue(uses, name)
            for n in uses:
                where = f"{name}:{n.lineno} _audit.{n.attr}"
                if self.in_safe_lambda(n, par):
                    continue
                if n.attr in ("safe", "recorder"):
                    self.assertTrue(self.guarded(n, par), where + " — `if _audit` 없이 씀")
                    continue
                if n.attr == "file_ids":
                    top = n
                    while par.get(top) is not None and not isinstance(par[top], ast.Module):
                        top = par[top]
                    self.assertIsInstance(top, ast.Try, where + " — 모듈 맨 위 try 밖")
                    continue
                self.fail(where + " — safe(lambda) 밖")
            self.assertNotIn("import audit_log", (ROOT / name).read_text(encoding="utf-8").replace("import audit_log as _audit", ""))

    def test_import_failure_keeps_bots(self):
        """기록장 모듈을 못 불러와도 봇은 불러와지고 기록만 건너뜀(_audit = None)."""
        code = ("import sys; sys.modules['audit_log'] = None\n"
                "import daily_live, idle_live, basket_live, overlay_live\n"
                "print([m._audit for m in (daily_live, idle_live, basket_live, overlay_live)])")
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[None, None, None, None]", out.stderr[-500:])

    def test_decision_calls(self):
        """판단을 부르는 줄: 1일봉 · 바구니는 원래 인자를 recorder로만 감쌈(기록장이 없으면 원래 함수) · 엔진은 그대로 ·
        덧붙임은 원래 `if stale or not needs_rebalance(...)`와 같은 값(낡은 날 needs_rebalance를 안 부르는 것까지)."""
        text = {n: (ROOT / n).read_text(encoding="utf-8") for n in BOTS}
        self.assertIn("sells, buys = decide(state, cands, now_price, aligned, rate, _audit.recorder(kin_ok, kin_calls) if _audit else kin_ok)",
                      text["daily_live.py"])
        self.assertIn("step(state, day, t0, _audit.recorder(days_since, ds_calls) if _audit else days_since, ev, react, inside,",
                      text["basket_live.py"])
        self.assertIn("orders, new_state, why = step(state, day, px, breadth if breadth is not None else 100.0, used, total, cash_for_engine, held,",
                      text["idle_live.py"])
        self.assertIn("reb = (not stale) and needs_rebalance(st, state, day)", text["overlay_live.py"])
        self.assertIn("if stale or not reb:", text["overlay_live.py"])
        calls = []

        def nr(st, state, day):                          # needs_rebalance 흉내(부른 횟수까지 셈)
            calls.append(1)
            return st.get("applied") != state
        for stale in (True, False):
            for applied in ("상승", "횡보"):
                st = {"applied": applied}
                calls.clear()
                reb = (not stale) and nr(st, "상승", "20261109")
                got = (stale or not reb, len(calls))
                calls.clear()
                want = (stale or not nr(st, "상승", "20261109"), len(calls))
                self.assertEqual(got, want, (stale, applied))


class DailyReplay(unittest.TestCase):
    """1일봉: 기록한 입력 + 닮음 질문 답으로 decide를 다시 돌리면 같은 결정."""

    def test_replay_equals(self):
        import daily_live as D
        rng = random.Random(7)
        for trial in range(200):
            codes = [f"{i:06d}" for i in range(30)]
            held = {}
            for c in rng.sample(codes, rng.randint(0, 5)):
                px = rng.uniform(1000, 5000)
                held[c] = {"code": c, "name": c, "kind": rng.choice(["추세", "정배열"]), "price": px, "peak": px * rng.uniform(1, 1.3),
                           "max_close": px * rng.uniform(1, 1.3), "last_close": px, "칸": rng.randint(1, 2), "처음칸": 2,
                           "days": rng.randint(0, 30), "bought": "20261020"}
            state = {"positions": held, "closed": [{"x": 1}] * 3}
            cands = [{"code": c, "name": c, "추세문": rng.random() < 0.5, "3일연속": rng.random() < 0.5,
                      "거래량비": rng.uniform(0.5, 3), "정배열일수": rng.randint(1, 30), "추세 기울기": rng.uniform(-1, 3)}
                     for c in rng.sample(codes, rng.randint(0, 12))]
            now_price = {c: rng.uniform(800, 6000) for c in codes if rng.random() < 0.95}
            aligned = {c: rng.random() < 0.6 for c in held}
            rate = {c: rng.uniform(-30, 30) for c in codes}
            answers = {}

            def kin_ok(code, holding):
                return answers.setdefault((code, tuple(holding)), rng.random() < 0.7)
            inp = A.capture(dict(state={"positions": state.get("positions", {})}, cands=cands, now_price=now_price,
                                 aligned=aligned, rate=rate))
            calls = []
            out = D.decide(state, cands, now_price, aligned, rate, A.recorder(kin_ok, calls))
            body = json.loads(json.dumps({"입력": inp, "결과": A.plain({"sells": out[0], "buys": out[1]}), "calls": calls}))
            asked = {(c, tuple(h)): r for c, h, r in body["calls"]}
            i = body["입력"]
            again = D.decide(i["state"], i["cands"], i["now_price"], i["aligned"], i["rate"],
                             lambda code, holding: asked[(code, tuple(holding))])
            self.assertEqual(A.canon({"sells": again[0], "buys": again[1]}), A.canon(body["결과"]), trial)


class EngineTail(unittest.TestCase):
    """엔진 가격 이력을 끝 PX_TAIL개만 적어도 판단이 같음(etf-data 마지막 1,500거래일 · 신호 · 익절 폭 매일 · step은 10일마다)."""

    def test_tail_same_decision(self):
        import idle_live as I
        sys.path.insert(0, str(ROOT / "research"))
        import idle_signal
        series = {}
        for code in I.CODES:
            body = json.loads((ROOT / "etf-data" / f"{code}.json").read_text(encoding="utf-8"))
            series[code] = [(str(d), float(c)) for d, c in body.get("closes", []) if c]
        days = [d for d, _ in series[I.K200]][-1500:]
        checked = 0
        for n, day in enumerate(days):
            px = {}
            for code, rows in series.items():
                h = [c for d, c in rows if d < day]
                now = dict(rows).get(day)
                if now is not None and len(h) >= 25:
                    px[code] = np.array(h + [now])
            if any(c not in px for c in (I.K200, I.Q150, I.DOL)):
                continue
            tail = {c: a[-A.PX_TAIL:] for c, a in px.items()}
            for breadth, used in ((30.0, 0.1), (70.0, 0.1), (30.0, 0.5)):
                self.assertEqual(idle_signal.decide(px, breadth, used, at_1515=True),
                                 idle_signal.decide(tail, breadth, used, at_1515=True), day)
            self.assertEqual(I.inv_take(px[I.Q150]), I.inv_take(tail[I.Q150]), day)
            if n % 10 == 0:
                now_price = {c: float(a[-1]) for c, a in px.items()}
                inv = {"kind": "인버스", "price": now_price.get(I.INV, 1.0) * 1.01, "days": 3, "take": 0.02}
                for state, held in (({"positions": {}, "cool": 0}, {}),
                                    ({"positions": {I.INV: inv}, "cool": 0}, {I.INV: 10})):
                    for breadth, used in ((30.0, 0.1), (70.0, 0.5)):
                        a = I.step(json.loads(json.dumps(state)), day, px, breadth, used, 1e8, 5e7, held, now_price, n % 50 == 0, 0.0)
                        b = I.step(json.loads(json.dumps(state)), day, tail, breadth, used, 1e8, 5e7, held, now_price, n % 50 == 0, 0.0)
                        self.assertEqual(A.canon(a), A.canon(b), day)
            checked += 1
        self.assertGreater(checked, 1000)


class OverlayReceipt(unittest.TestCase):
    """덧붙임 봇 실제 실행(가짜 증권사)에서 기록이 남고 · 기록이 막히거나 기록장이 없어도 주문 · 알림 · 장부가 같음 ·
    환경에 비밀 값이 있어도 기록에 안 들어감."""
    SECRETS = {"KIS_APP_KEY": "SEKRETKEY111", "KIS_APP_SECRET": "SEKRETSEC222", "KIS_PAPER_APP_KEY": "SEKRETKEY333",
               "KIS_PAPER_APP_SECRET": "SEKRETSEC444", "KIS_PAPER_ACCOUNT": "98765432-01", "DISCORD_WEBHOOK_URL": "https://hook.example/SEKRET555"}

    def _run(self, block=False, audit_off=False):
        from tests import test_overlay_live as T
        import overlay_live as O
        tmp = tempfile.TemporaryDirectory()
        old = os.getcwd()
        os.chdir(tmp.name)
        try:
            with mock.patch.dict(os.environ, {"MIX54": "on", "MIX54_START": "20261001", "PAPER_ROOM_WAIT": "0", **self.SECRETS}), \
                    mock.patch.object(O.time, "sleep"), \
                    mock.patch.object(O, "closes", lambda before=None, code=O.SIGNAL: T.rows_for("상승", end="20261008")), \
                    mock.patch.object(O, "_audit", None if audit_off else O._audit), \
                    mock.patch("builtins.print"):
                if block:
                    Path("overlay-live").mkdir(parents=True, exist_ok=True)
                    Path("overlay-live/audit").write_text("막음")
                b = T.FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
                b.now = T.Run.NOW
                lines = O.run(b, None, "20261012", now=T.Run.NOW, quote=b.px.get, prev_day="20261008")
                p = Path("overlay-live/audit/20261012-overlay.json")
                body = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
                book = Path("overlay-live/paper-orders.json").read_text(encoding="utf-8")
                return b.orders, lines, O.load_state(), body if not block else None, book
        finally:
            os.chdir(old)
            tmp.cleanup()

    def test_receipt_and_same_orders(self):
        orders, lines, st, body, book = self._run()
        self.assertEqual(orders, [("122630", "buy", 4000)])
        self.assertEqual(body["결과"], {"rebalance": True})
        self.assertEqual(body["입력"]["state"], "상승")
        self.assertEqual(body["주문 결과"]["sent"][0]["status"], "접수")
        self.assertEqual(body["주문 결과"]["target"]["want"], 4000)
        self.assertTrue(body["주문 결과"]["complete"])
        self.assertEqual([o["key"] for o in body["오늘 장부 주문"]["overlay-live/paper-orders.json"]], ["20261012:buy:122630"])
        text = json.dumps(body, ensure_ascii=False)
        for v in self.SECRETS.values():
            self.assertNotIn(v, text)
        for v in ("98765432",):
            self.assertNotIn(v, text)
        for kw in (dict(block=True), dict(audit_off=True)):
            o2, l2, s2, _, b2 = self._run(**kw)
            self.assertEqual((o2, l2, s2), (orders, lines, st), kw)
            self.assertEqual(json.loads(b2)["orders"][0]["qty"], json.loads(book)["orders"][0]["qty"])


if __name__ == "__main__":
    unittest.main()
