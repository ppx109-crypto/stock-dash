"""BOOST-0001-A 감사 셈(research/boost_audit.py) 시험.
- 임시 git 저장소에 봇과 같은 길(audit_log.record · after)로 기록 · 장부를 커밋해 끝점 커밋에서 읽고 셈(실제 git).
- 고친 기록 · 장부 · 저장소(돌연변이)를 감사가 잡는지 먼저 확인(점검표 33)."""
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import audit_log as A

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import boost_audit as B        # noqa: E402


def real_closes(code):
    body = json.loads((ROOT / "etf-data" / f"{code}.json").read_text(encoding="utf-8"))
    return body


def kst(day, hm):
    return f"{day[:4]}-{day[4:6]}-{day[6:]} {hm}"


_REPOS = []


def tearDownModule():
    for r in _REPOS:
        r.tmp.cleanup()


class Repo:
    """임시 git 저장소(커밋 시각을 정해서 남김 · 모듈 끝에 지움)."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        _REPOS.append(self)
        self.root = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")

    def git(self, *a, when=None):
        env = dict(os.environ)
        if when:
            env.update(GIT_AUTHOR_DATE=when + " +0900", GIT_COMMITTER_DATE=when + " +0900")
        return subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True, check=True, env=env).stdout.strip()

    def write(self, rel, body):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")

    def commit(self, msg, when):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg, when=when)
        return self.git("rev-parse", "HEAD")

    def etf(self, before):
        """etf-data를 그날 앞 줄만으로(판단 때 판 흉내)."""
        import idle_live as I
        for code in I.CODES:
            b = real_closes(code)
            b["closes"] = [r for r in b["closes"] if str(r[0]) < before]
            self.write(f"etf-data/{code}.json", b)


def engine_record(repo, day, head, run, extra_ledger=True, breadth=70.0):
    """idle_live.run과 같은 꼴로 엔진 기록(판단 앞 · 판단 · 판단 뒤)을 repo에 씀. cwd = repo."""
    import idle_live as I
    old = os.getcwd()
    os.chdir(repo.root)
    try:
        px, now_price = {}, {}
        for code in I.CODES:
            rows = [(str(d), float(c)) for d, c in real_closes(code)["closes"] if c]
            h = [c for d, c in json.loads(Path(f"etf-data/{code}.json").read_text(encoding="utf-8"))["closes"] if c and str(d) < day]
            now = dict(rows).get(day)
            if now is not None and len(h) >= 25:
                px[code] = np.array([float(x) for x in h] + [now])
                now_price[code] = now
        state = json.loads(Path("idle-live/state.json").read_text(encoding="utf-8"))
        ledgers = ["idle-live/paper-orders.json", "idle-live/state.json"] + (["idle-live/extra.json"] if extra_ledger else [])
        meta = {"기록 시각(한국)": kst(day, "15:11:00"), "작업 번호": run, "작업 시도": "1", "부른 까닭": "schedule",
                "작업 코드 커밋": head, "판단 때 저장소 HEAD": head}
        code_ids = {"idle_live.py": A.blob_id(ROOT / "idle_live.py"), "research/idle_signal.py": A.blob_id(ROOT / "research/idle_signal.py")}
        inp = A.capture(dict(state=state, day=day, px={c: a[-A.PX_TAIL:] for c, a in px.items()}, breadth=breadth, used=0.5,
                             total=1e8, cash=5e7, held={}, now_price=now_price, is_week_end=False, reserve=0.0))
        o, st, why = I.step(state, day, px, breadth, 0.5, 1e8, 5e7, {}, now_price, False, reserve=0.0)
        with mock.patch.object(A, "meta", lambda: dict(meta)):
            A.record("idle-live/state.json", day, "engine", inp, {"orders": o, "new_state": st, "why": why}, ledgers=ledgers,
                     code=code_ids, extra={"px_len": {c: len(a) for c, a in px.items()}, "px_digest": {c: A.digest(a) for c, a in px.items()},
                                           "px_missing": [c for c in I.CODES if c not in px], "etf_asof": A.etf_asof(I.CODES, day),
                                           "breadth_raw": breadth, "room_note": [], "late_at_decision": False})
            book = json.loads(Path("idle-live/paper-orders.json").read_text(encoding="utf-8"))
            for c, side, q, r in o:
                book["orders"].append({"key": f"{day}:{side}:{c}", "code": c, "side": side, "qty": q, "status": "접수"})
            Path("idle-live/paper-orders.json").write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
            Path("idle-live/state.json").write_text(json.dumps(dict(st, last_day=day), ensure_ascii=False, indent=1), encoding="utf-8")
            A.after("idle-live/state.json", day, "engine", {"late": False}, ledgers=ledgers, books=("idle-live/paper-orders.json",))
        return o
    finally:
        os.chdir(old)


class EngineRepo(unittest.TestCase):
    """두 거래일 엔진 기록을 실제 git 흐름(아침 판 → 판단 · 커밋 → 저녁 자료 → 다음 날)으로 만들고 감사."""

    def build(self, stale_next=False, tamper_after=False):
        r = Repo()
        cal = sorted({str(d) for d, c in real_closes("069500")["closes"] if c})
        d1, d2 = [d for d in cal if d >= "20261027"][:2]
        r.etf(d1)
        r.write("idle-live/state.json", {"positions": {}, "cool": 0})
        r.write("idle-live/paper-orders.json", {"orders": [], "held": {}})
        r.write("idle-live/extra.json", {"그대로": 1})
        r.write("event-data/000000.json", {"rows": []})
        a = r.commit("아침", kst(d1, "09:00:00"))
        engine_record(r, d1, a, "11111111")
        c1 = r.commit("Idle engine live", kst(d1, "15:13:00"))
        r.etf(d2)
        e1 = r.commit("Collect ETF", kst(d1, "19:30:00"))
        head2 = e1
        if stale_next:                                   # 다음 판단이 앞 판단 커밋을 못 받은 옛 저장소에서 돎
            r.git("checkout", "-q", "-b", "old", a)
            r.etf(d2)
            r.write("idle-live/state.json", {"positions": {}, "cool": 0})
            head2 = r.commit("옛 판", kst(d1, "20:00:00"))
        engine_record(r, d2, head2, "22222222")
        if tamper_after:                                 # 판단 뒤 장부를 적은 다음 다른 값으로 올림
            r.write("idle-live/state.json", {"positions": {}, "cool": 99})
        c2 = r.commit("Idle engine live", kst(d2, "15:13:00"))
        if stale_next:
            r.git("checkout", "-q", "main")
            r.git("merge", "-q", "--no-edit", "-X", "theirs", "old", when=kst(d2, "15:14:00"))
        r.etf("29991231")
        r.commit("Collect ETF", kst(d2, "19:30:00"))
        return r, d1, d2, c1, c2

    def run_audit(self, r, d1, d2):
        with mock.patch.object(B, "ROOT", r.root):
            return B.audit(d1, d2)

    def engine_rows(self, res):
        return [x for x in res["줄들"] if x["봇"] == "engine"]

    def test_clean_two_days(self):
        r, d1, d2, c1, c2 = self.build()
        res = self.run_audit(r, d1, d2)
        self.assertEqual(res["요약"]["불완전"], [])
        for row in self.engine_rows(res):
            self.assertEqual(row["문제"], [], row)                   # 안 바뀐 장부(extra.json)도 문제 아님(H1)
            self.assertEqual(row["재현"], "같음")
        fails = res["요약"]["즉시 실패"]
        self.assertTrue(fails and all(t == "빠짐" and not k.endswith(":engine") for k, t, _ in fails))
        self.assertEqual(res["요약"]["판정"], "실패")               # 다른 세 봇 기록이 없음

    def test_tampered_ledger_and_stale_head(self):
        r, d1, d2, *_ = self.build(tamper_after=True)
        rows = self.engine_rows(self.run_audit(r, d1, d2))
        self.assertIn(("LEDGER", "idle-live/state.json 올린 장부가 판단 뒤 장부와 다름"), [tuple(p) for p in rows[1]["문제"]])
        r, d1, d2, *_ = self.build(stale_next=True)
        rows = self.engine_rows(self.run_audit(r, d1, d2))
        self.assertIn(("LEDGER", "앞 판단 뒤 저장소를 못 받고 판단함(옛 장부)"), [tuple(p) for p in rows[1]["문제"]])

    def test_tampered_inputs(self):
        r, d1, d2, *_ = self.build()
        p = r.root / "idle-live" / "audit" / f"{d2}-engine.json"
        body = json.loads(p.read_text(encoding="utf-8"))
        body["입력"]["breadth"] = 30.0                              # 입력을 고치면 재현 실패
        body["곁"]["etf_asof"]["069500"]["last"] = d2                # 판단 날 자료가 섞였다고 적힌 기록 → 미래
        r.write(f"idle-live/audit/{d2}-engine.json", body)
        r.commit("고침", kst(d2, "20:00:00"))
        rows = self.engine_rows(self.run_audit(r, d1, d2))
        tags = [t for t, _ in rows[1]["문제"]]
        self.assertIn("미래", tags)
        self.assertIn("재현", tags)
        self.assertIn("기록 고장", tags)                             # 판단한 작업이 올린 기록과 끝점 기록이 다름(나중에 고침)

    def test_late_input(self):
        """판단 때 HEAD에 어제 KODEX 200 줄이 없었다면: 지문은 같고(그 판으로 셈) 늦은 입력 꼬리표."""
        r = Repo()
        cal = sorted({str(d) for d, c in real_closes("069500")["closes"] if c})
        d1 = [d for d in cal if d >= "20261027"][0]
        pd = B.prev_day(cal, d1)
        r.etf(d1)
        b = real_closes("069500")
        b["closes"] = [x for x in b["closes"] if str(x[0]) < pd]
        r.write("etf-data/069500.json", b)
        r.write("idle-live/state.json", {"positions": {}, "cool": 0})
        r.write("idle-live/paper-orders.json", {"orders": [], "held": {}})
        r.write("event-data/000000.json", {"rows": []})
        a = r.commit("아침", kst(d1, "09:00:00"))
        engine_record(r, d1, a, "33333333", extra_ledger=False)
        r.commit("Idle engine live", kst(d1, "15:13:00"))
        r.etf("29991231")
        r.commit("Collect ETF", kst(d1, "19:30:00"))
        rows = self.engine_rows(self.run_audit(r, d1, d1))
        self.assertEqual([t for t, _ in rows[0]["문제"]], ["LATE_INPUT"], rows[0]["문제"])


class Basket(unittest.TestCase):
    def body(self):
        import basket_live as BL
        days = [f"2026{m:02d}{d:02d}" for m in (9, 10) for d in range(1, 29)]
        day, t0 = days[-1], days[-2]
        pos = {d: i for i, d in enumerate(days)}

        def days_since(d):
            return len(days) - 1 - pos[d] if d in pos else sum(1 for x in days if x > d)
        state = {"positions": {"000001": {"day": days[-21], "price": 100.0, "kind": "무상증자", "react": 0.0}},
                 "last": {"000002:자사주취득": days[-10], "000003:무상증자": days[-45]}}
        ev = [("000002", "자사주취득"), ("000004", "자사주취득"), ("000005", "무상증자")]
        react = {"000002": -0.05, "000004": -0.03, "000005": 0.01}
        inside = {"000002", "000004", "000005"}
        held, now_price = {"000001": 10}, {"000001": 110.0, "000004": 5000.0, "000005": 2000.0}
        inp = A.capture(dict(state=state, day=day, t0=t0, events_t0=ev, react=react, inside=inside, held=held,
                             now_price=now_price, capital=1e7, avail=5e6, names={"000004": "넷"}, others=set()))
        calls = []
        o, st, why = BL.step(state, day, t0, A.recorder(days_since, calls), ev, react, inside, held, now_price,
                             capital=1e7, avail=5e6, names={"000004": "넷"}, others=set())
        self.assertTrue(any(s == "buy" for _, s, _, _ in o) and any(s == "sell" for _, s, _, _ in o))
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        body = {"날": day, "봇": "basket", "판단 때 저장소 HEAD": head, "코드": {"basket_live.py": A.blob_id(ROOT / "basket_live.py")},
                "입력": inp, "결과": A.plain({"orders": o, "new_state": st, "why": why}),
                "곁": A.plain({"days_since_calls": calls, "days_tail": days[-A.DAYS_TAIL:], "before": days[-3]})}
        ctx = {"main_events": {"000002": [(t0, "자사주취득")], "000004": [(t0, "자사주취득")], "000005": [(t0, "무상증자")]},
               "basket_inputs": lambda h, t, b: {"react": A.plain(react), "inside": A.plain(inside), "events": A.plain(ev)}}
        return body, days, ctx

    def test_replay_inputs_and_mutations(self):
        body, days, ctx = self.body()
        self.assertEqual(B.replay_any("basket", body), (True, "같음"))
        probs, info = B.inputs_check("basket", body, days, ctx)
        self.assertEqual(probs, [])
        self.assertEqual(info, ["사건 종목 000002 지금 값 없음(결정과 무관)"])     # 앞 사건과 20거래일 안이라 어차피 셈 안 함
        nop = json.loads(json.dumps(body))                                          # 값이 없어 못 산 경우는 BROKER
        del nop["입력"]["now_price"]["000004"]
        nop["결과"]["why"].append("넷 자사주 취득 · 반응 -3.0% — 살 돈이 모자람")
        self.assertIn(("BROKER", "사건 종목 000004 지금 값 없음 → 안 삼"), B.inputs_check("basket", nop, days, ctx)[0])
        bad = json.loads(json.dumps(body))
        bad["곁"]["days_since_calls"] = bad["곁"]["days_since_calls"][1:]      # 물은 질문이 기록에 없으면 재현 실패
        self.assertFalse(B.replay("basket", bad)[0])
        bad = json.loads(json.dumps(body))
        bad["곁"]["days_since_calls"][0][1] += 1
        self.assertIn("재현", [t for t, _ in B.inputs_check("basket", bad, days, ctx)[0]])
        ctx2 = dict(ctx, basket_inputs=lambda h, t, b: {"react": {"000002": -0.06}, "inside": [], "events": []})
        self.assertEqual([t for t, _ in B.inputs_check("basket", body, days, ctx2)[0]], ["재현"] * 3)     # 판단 때 판과 다른 입력
        self.assertIn("LATE_INPUT", [t for t, _ in B.inputs_check("basket", body, days[:-2] + days[-1:], ctx)[0]])   # 목록 ≠ 달력

    def test_late_events_material_only(self):
        body, days, ctx = self.body()
        t0 = body["입력"]["t0"]
        body["입력"]["inside"] = body["입력"]["inside"] + ["000009", "000010"]
        body["입력"]["react"] = dict(body["입력"]["react"], **{"000009": -0.04, "000010": 0.03})
        ev2 = dict(ctx["main_events"], **{"000010": [(t0, "자사주취득")]})        # 반응 +3% → 결정 무관
        ctx2 = dict(ctx, main_events=ev2, basket_inputs=lambda h, t, b: None)
        probs, info = B.inputs_check("basket", body, days, ctx2)
        self.assertEqual([t for t, _ in probs], [])
        self.assertTrue(any("결정과 무관" in s for s in info))
        ev3 = dict(ev2, **{"000009": [(t0, "자사주취득")]})                      # 반응 −4% → 결정이 달랐을 수 있음
        probs, _ = B.inputs_check("basket", body, days, dict(ctx2, main_events=ev3))
        self.assertEqual([t for t, _ in probs], ["LATE_INPUT"])


class Daily(unittest.TestCase):
    def body(self, module=None):
        import daily_live as D
        D = module or D
        held = {"000001": {"code": "000001", "name": "가", "kind": "추세", "price": 1000.0, "peak": 1300.0, "max_close": 1300.0,
                           "last_close": 1200.0, "칸": 2, "처음칸": 2, "days": 5, "bought": "20261020"}}
        cands = [{"code": c, "name": c, "추세문": True, "3일연속": False, "거래량비": 1.0, "정배열일수": 3, "추세 기울기": s}
                 for c, s in (("000002", 2.0), ("000003", 1.0), ("000004", float("nan")))]
        now_price = {"000001": 1100.0, "000002": 500.0, "000003": 700.0, "000004": 900.0}
        aligned, rate = {"000001": False}, {"000002": 1.0, "000003": 2.0}
        inp = A.capture(dict(state={"positions": held}, cands=cands, now_price=now_price, aligned=aligned, rate=rate))
        calls = []
        s, b = D.decide({"positions": held, "closed": []}, cands, now_price, aligned, rate, A.recorder(lambda c, h: c != "000003", calls))
        body = json.loads(json.dumps({"날": "20261030", "판단 때 저장소 HEAD": "h", "입력": inp, "결과": A.plain({"sells": s, "buys": b}),
                                      "곁": A.plain({"kin_calls": calls, "ready": True, "expect": "20261029", "quotes": 4, "pool": 4,
                                                    "data_asof": {"max": "20261029", "today_or_later": 0, "codes": 4}})}))
        return body

    def test_replay_nan_future_missing(self):
        body = self.body()
        self.assertEqual(B.replay("daily", body)[:1], (True,))       # 후보의 nan도 재현(JSON NaN 왕복 · canon 비교)
        cal = ["20261028", "20261029", "20261030"]
        self.assertEqual(B.inputs_check("daily", body, cal, None), ([], []))
        fut = json.loads(json.dumps(body))
        fut["곁"]["data_asof"] = {"max": "20261030", "today_or_later": 3, "codes": 4}
        self.assertEqual([t for t, _ in B.inputs_check("daily", fut, cal, None)[0]], ["미래"])
        late = json.loads(json.dumps(body))
        late["곁"]["ready"] = False
        late["곁"]["quotes"] = 3
        del late["입력"]["now_price"]["000001"]
        self.assertEqual([t for t, _ in B.inputs_check("daily", late, cal, None)[0]], ["LATE_INPUT", "BROKER", "BROKER"])
        broken = json.loads(json.dumps(body))
        del broken["곁"]["data_asof"]
        broken["판단 때 저장소 HEAD"] = None
        self.assertEqual([t for t, _ in B.inputs_check("daily", broken, cal, None)[0]], ["기록 고장", "기록 고장"])

    def test_recorded_code_version(self):
        """기록한 코드 판이 지금과 다르면 그 판(git 블롭)을 꺼내 하위 작업으로 재현(M2)."""
        src = (ROOT / "daily_live.py").read_text(encoding="utf-8").replace('"① 추세 조건"', '"① 추세 조건(옛 판)"')
        self.assertIn("(옛 판)", src)
        mod = types.ModuleType("daily_old")
        mod.__file__ = str(ROOT / "daily_live.py")
        exec(compile(src, "daily_old", "exec"), mod.__dict__)
        body = self.body(module=mod)
        self.assertIn("(옛 판)", json.dumps(body["결과"], ensure_ascii=False))
        r = Repo()
        r.write("daily_live.py", src)
        r.commit("옛 판", "2026-10-30 09:00:00")
        body["코드"] = {"daily_live.py": r.git("rev-parse", "HEAD:daily_live.py")}
        self.assertFalse(B.replay("daily", body)[0])                 # 지금 코드로는 다름
        with mock.patch.object(B, "ROOT", r.root):
            same, why = B.replay_any("daily", body)
        self.assertTrue(same, why)
        self.assertIn("기록한 코드 판", why)
        body["코드"] = {"daily_live.py": "0" * 40}                   # 꺼낼 수 없는 판 → 불완전(봇 탓 아님)
        B.ERRS.clear()
        with mock.patch.object(B, "ROOT", r.root):
            self.assertIsNone(B.replay_any("daily", body)[0])
        self.assertTrue(B.ERRS)
        B.ERRS.clear()
        self.assertEqual(B.replay_any("daily", dict(body, 코드=None)), (False, "기록 고장(코드 판 없음)"))


class Overlay(unittest.TestCase):
    def test_real_run_receipt_replays(self):
        from tests import test_audit_log as T
        orders, lines, st, body, _ = T.OverlayReceipt()._run(block=False)
        self.assertEqual(B.replay_any("overlay", body), (True, "같음"))
        ok, why = B.replay_overlay_target(body)
        self.assertTrue(ok, why)
        self.assertEqual(B.orders_check("overlay", body), [])
        self.assertEqual(B.broker_check("overlay", body), [])
        bad = json.loads(json.dumps(body))
        bad["주문 결과"]["target"]["price"] = 50.0
        self.assertFalse(B.replay_overlay_target(bad)[0])
        bad = json.loads(json.dumps(body))
        bad["주문 결과"]["sent"] = []
        bad["오늘 장부 주문"] = {}
        self.assertEqual([t for t, _ in B.orders_check("overlay", bad)], ["주문 빠짐"])


class Checks(unittest.TestCase):
    def test_timing(self):
        b = {"기록 시각(한국)": "2026-11-09 15:11:00", "부른 까닭": "schedule", "곁": {"late_at_decision": False}, "주문 결과": {"late": False}}
        self.assertEqual(B.timing("engine", b), ([], []))
        late = dict(b, **{"기록 시각(한국)": "2026-11-09 15:31:00", "부른 까닭": "workflow_dispatch", "주문 결과": {"late": True}})
        probs, info = B.timing("daily", late)
        self.assertEqual([t for t, _ in probs], ["SCHEDULER"])        # 손으로 불렀어도 늦으면 설명 필요(M1)
        self.assertTrue(info and info[0].startswith("MANUAL"))
        self.assertEqual([t for t, _ in B.timing("overlay", dict(b, **{"기록 시각(한국)": "2026-11-09 15:21:00"}))[0]], ["SCHEDULER"])
        self.assertTrue(B.timing("engine", dict(b, **{"부른 까닭": None}))[1][0].endswith("작업 흐름 밖"))

    def test_broker_and_orders(self):
        body = {"날": "20261109", "결과": {"orders": [["133690", "buy", 3, "r"], ["138230", "sell", 2, "r"]]}, "주문 결과": {"late": False},
                "오늘 장부 주문": {"idle-live/paper-orders.json": [
                    {"key": "20261109:buy:133690", "code": "133690", "side": "buy", "status": "접수 · 3주 중 살 수 있는 2주로 줄임"},
                    {"key": "202611091512:room:229200", "code": "229200", "side": "sell", "status": "실패 · x"}],
                    "x.json": "읽기 실패 · AttributeError"}}
        self.assertEqual(sorted(t for t, _ in B.broker_check("engine", body)), ["BROKER", "BROKER", "LEDGER"])
        self.assertEqual(B.orders_check("engine", body), [("주문 빠짐", "138230 sell 판단했으나 장부에 없음")])
        self.assertEqual(B.orders_check("engine", dict(body, **{"주문 결과": {"late": True}})), [])
        daily = {"날": "20261109", "결과": {"sells": [{"code": "000001", "type": "sell"}], "buys": [{"code": "000002", "type": "buy"}]},
                 "주문 결과": {"late": False, "paper": ["🧪 모의투자(1일봉) 매수 건너뜀 · 둘(000002) · 살 돈이 모자람(1주 미만)"]},
                 "오늘 장부 주문": {"daily-live/paper-orders.json": [{"key": "202611091520:sell:000001:20261109", "status": "접수"}]}}
        self.assertEqual(B.orders_check("daily", daily), [])
        daily["주문 결과"]["paper"] = []
        self.assertEqual([t for t, _ in B.orders_check("daily", daily)], ["주문 빠짐"])

    def test_causes_format(self):
        c = {"20261109:basket": {"빠짐": {"원인": "SCHEDULER", "근거": "작업 19283746501 · 15:31 시작"}, "BROKER": "근거 없음",
                                 "LEDGER": {"근거": "커밋 a1b2c3d4e5"}},
             "20261110:basket": {"빠짐": ""}, "20261111:basket": {"빠짐": {"원인": "모름", "근거": "작업 19283746501"}}}
        self.assertTrue(B.explained(c, "20261109:basket", "빠짐"))
        self.assertFalse(B.explained(c, "20261109:basket", "BROKER"))
        self.assertTrue(B.explained(c, "20261109:basket", "LEDGER"))
        self.assertFalse(B.explained(c, "20261110:basket", "빠짐"))      # 빈 글로는 못 덮음(M6)
        self.assertFalse(B.explained(c, "20261111:basket", "빠짐"))      # 원인 꼬리표가 정해진 것이 아님

    def test_new_buys(self):
        self.assertTrue(B.new_buys("engine", {"결과": {"orders": [["a", "buy", 1, "r"]]}}))
        self.assertFalse(B.new_buys("basket", {"결과": {"orders": [["a", "sell", 1, "r"]]}}))
        self.assertTrue(B.new_buys("overlay", {"결과": {"rebalance": True}, "주문 결과": {"orders": [["a", "buy", 3]]}}))
        self.assertTrue(B.new_buys("daily", {"결과": {"sells": [], "buys": [{"code": "a"}]}}))

    def test_scheduler_skip_and_verdict(self):
        """엔진이 마감 뒤에 돈 날 바구니 · 덧붙임이 없는 것은 빠짐이 아니라 SCHEDULER · 재현 실패는 설명으로 못 덮음."""
        r = Repo()
        b = real_closes("069500")
        b["closes"] = [x for x in b["closes"] if str(x[0]) <= "20261030"]
        r.write("etf-data/069500.json", b)
        r.write("event-data/000000.json", {"rows": []})
        head = r.commit("아침", "2026-10-30 09:00:00")
        body = {"날": "20261030", "봇": "engine", "기록 시각(한국)": "2026-10-30 15:25:00", "작업 번호": "1", "작업 시도": "1",
                "부른 까닭": "schedule", "판단 때 저장소 HEAD": head, "코드": None, "입력": None, "결과": {},
                "주문 결과": {"late": True}, "덧붙인 시각(한국)": "2026-10-30 15:26:00"}
        r.write("idle-live/audit/20261030-engine.json", body)
        r.commit("Idle engine live", "2026-10-30 15:27:00")
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261030", "20261030", causes={"20261030:engine": {"기록 고장": "작업 12345678"}})
        rows = {x["봇"]: x for x in res["줄들"]}
        self.assertEqual([t for t, _ in rows["basket"]["문제"]], ["SCHEDULER"])
        self.assertEqual([t for t, _ in rows["overlay"]["문제"]], ["SCHEDULER"])
        self.assertIn("빠짐", [t for t, _ in rows["daily"]["문제"]])
        self.assertIn("SCHEDULER", [t for t, _ in rows["engine"]["문제"]])
        self.assertIn(("20261030:engine", "기록 고장"), [(k, t) for k, t, _ in res["요약"]["즉시 실패"]])
        self.assertEqual(res["요약"]["판정"], "실패")

    def test_end_commit_unreadable(self):
        r = Repo()
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261030", "20261030", end_commit="없는커밋")
        self.assertEqual(res["요약"]["판정"], "불완전(다시 셈)")


if __name__ == "__main__":
    unittest.main()
