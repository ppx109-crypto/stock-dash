"""BOOST-0001-A 감사 셈(research/boost_audit.py · 판 3) 시험.
- 임시 git 저장소에 코드 트리 · 자료 · 기록 · 장부를 봇과 같은 길로 커밋하고 끝점 커밋에서 읽어 셈(실제 git · 하위 작업 재현).
- 고친 기록 · 장부 · 저장소 · 코드 판 · 분모(돌연변이)를 감사가 잡는지 먼저 확인(점검표 33)."""
import json
import os
import shutil
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

SESS = json.loads((ROOT / "research-exchange/claude-to-gpt/BOOST-0001-A/run_days.json").read_text(encoding="utf-8"))["세션"]
_REPOS = []


def tearDownModule():
    for r in _REPOS:
        r.tmp.cleanup()


def real_closes(code):
    return json.loads((ROOT / "etf-data" / f"{code}.json").read_text(encoding="utf-8"))


def real_cal():
    return sorted({str(d) for d, c in real_closes("069500")["closes"] if c})


def kst(day, hm):
    return f"{day[:4]}-{day[4:6]}-{day[6:]} {hm}"


def rd(run, trading=None, off=None):
    """시험용 고정 분모."""
    return {"거래일": trading or run, "기대 실행일": run, "예정 무실행": off or {}, "세션": SESS}


class Repo:
    """임시 git 저장소(코드 트리 포함 · 커밋 시각을 정해서 남김 · 모듈 끝에 지움)."""

    def __init__(self, code=True):
        self.tmp = tempfile.TemporaryDirectory()
        _REPOS.append(self)
        self.root = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        if code:                                          # 판단 때 HEAD의 코드 트리(지금 작업 나무와 같은 판)
            for p in list(ROOT.glob("*.py")) + list((ROOT / "research").glob("*.py")):
                q = self.root / p.relative_to(ROOT)
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, q)
        self.write("event-data/000000.json", {"rows": []})

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

    def etf(self, before, drop=()):
        """etf-data를 그날 앞 줄만으로(판단 때 판 흉내) · drop = 빼 둘 (코드, 날)."""
        import idle_live as I
        for code in I.CODES:
            b = real_closes(code)
            b["closes"] = [r for r in b["closes"] if str(r[0]) < before and (code, str(r[0])) not in drop]
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
            h = I.history(code, day)
            now = dict(rows).get(day)
            if now is not None and len(h) >= 25:
                px[code] = np.array(h + [now])
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
        cal = real_cal()
        d1, d2 = [d for d in cal if d >= "20261027"][:2]
        r.etf(d1)
        r.write("idle-live/state.json", {"positions": {}, "cool": 0})
        r.write("idle-live/paper-orders.json", {"orders": [], "held": {}})
        r.write("idle-live/extra.json", {"그대로": 1})
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
        self.days = rd([d1, d2], trading=[d for d in cal if d <= d2][-30:])
        return r, d1, d2, c1, c2

    def run_audit(self, r, d1, d2, run_days=None):
        with mock.patch.object(B, "ROOT", r.root):
            return B.audit(d1, d2, run_days=run_days or self.days)

    def engine_rows(self, res):
        return [x for x in res["줄들"] if x["봇"] == "engine"]

    def test_clean_two_days(self):
        r, d1, d2, c1, c2 = self.build()
        res = self.run_audit(r, d1, d2)
        self.assertEqual(res["요약"]["불완전"], [])
        for row in self.engine_rows(res):
            self.assertEqual(row["문제"], [], row)                   # 안 바뀐 장부(extra.json)도 문제 아님
            self.assertEqual(row["재현"], "같음")
            self.assertRegex(row["재현 트리"]["트리 지문"], r"^[0-9a-f]{64}$")
        self.assertEqual(len(res["요약"]["재현 트리 지문"]), 1)        # 두 날 모두 같은 코드 트리
        fails = res["요약"]["즉시 실패"]
        self.assertTrue(fails and all(t == "빠짐" and not k.endswith(":engine") for k, t, _ in fails))
        self.assertEqual((res["요약"]["판정"], res["요약"]["기록 수"]), ("실패", "2/8"))
        self.assertEqual(res["요약"]["범위"], "G2(결정 · 장부 · 주문 일치) · 원천 수집 시각 증명 아님")

    def test_fixed_denominator(self):
        """d2의 KODEX 200 줄과 엔진 기록을 모두 지워도 고정 분모라 d2 네 칸이 모두 빠짐(분모가 감사 대상 자료에 안 기댐)."""
        r, d1, d2, *_ = self.build()
        (r.root / "idle-live" / "audit" / f"{d2}-engine.json").unlink()
        b = real_closes("069500")
        b["closes"] = [x for x in b["closes"] if str(x[0]) != d2]
        r.write("etf-data/069500.json", b)
        r.commit("지움", kst(d2, "20:00:00"))
        res = self.run_audit(r, d1, d2)
        miss = sorted(k for k, t, _ in res["요약"]["즉시 실패"] if t == "빠짐" and k.startswith(d2))
        self.assertEqual(miss, [f"{d2}:{b}" for b in sorted(B.BOTS)])

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
        tags = [t for t, _ in self.engine_rows(self.run_audit(r, d1, d2))[1]["문제"]]
        for t in ("미래", "재현", "기록 고장"):                       # 기록 고장 = 판단한 작업이 올린 기록과 끝점 기록이 다름
            self.assertIn(t, tags)

    def test_late_input(self):
        """판단 때 HEAD에 어제 KODEX 200 줄이 없었다면: 다시 만들기는 같고(그 판으로 셈) 늦은 입력 꼬리표만."""
        r = Repo()
        cal = real_cal()
        d1 = [d for d in cal if d >= "20261027"][0]
        pd = B.prev_day(cal, d1)
        r.etf(d1, drop={("069500", pd)})
        r.write("idle-live/state.json", {"positions": {}, "cool": 0})
        r.write("idle-live/paper-orders.json", {"orders": [], "held": {}})
        a = r.commit("아침", kst(d1, "09:00:00"))
        engine_record(r, d1, a, "33333333", extra_ledger=False)
        r.commit("Idle engine live", kst(d1, "15:13:00"))
        r.etf("29991231")
        r.commit("Collect ETF", kst(d1, "19:30:00"))
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit(d1, d1, run_days=rd([d1], trading=[d for d in cal if d <= d1][-30:]))
        rows = self.engine_rows(res)
        self.assertEqual([t for t, _ in rows[0]["문제"]], ["LATE_INPUT"], rows[0]["문제"])


class CodeVersion(unittest.TestCase):
    """재현은 판단 때 HEAD의 코드 트리(+ 기록 블롭)에서만: 기록 뒤 코드가 바뀌어도 그 판 재현은 통과 · 지금 판은 실패 ·
    그 트리에 없는 모듈을 작업 나무에서 끌어오지 않음."""

    def old_module(self, name, src):
        mod = types.ModuleType(name + "_old")
        mod.__file__ = str(ROOT / f"{name}.py")
        exec(compile(src, name + "_old", "exec"), mod.__dict__)
        return mod

    def daily_body(self, D):
        held = {"000001": {"code": "000001", "name": "가", "kind": "추세", "price": 1000.0, "peak": 1300.0, "max_close": 1300.0,
                           "last_close": 1200.0, "칸": 2, "처음칸": 2, "days": 5, "bought": "20261020"}}
        cands = [{"code": c, "name": c, "추세문": True, "3일연속": False, "거래량비": 1.0, "정배열일수": 3, "추세 기울기": s}
                 for c, s in (("000002", 2.0), ("000003", 1.0))]
        now_price = {"000001": 1100.0, "000002": 500.0, "000003": 700.0}
        inp = A.capture(dict(state={"positions": held}, cands=cands, now_price=now_price, aligned={"000001": False}, rate={}))
        calls = []
        s, b = D.decide({"positions": held}, cands, now_price, {"000001": False}, {}, A.recorder(lambda c, h: True, calls))
        return {"날": "20261030", "봇": "daily", "입력": inp, "결과": A.plain({"sells": s, "buys": b}), "곁": {"kin_calls": calls}}

    def test_daily_and_overlay_old_versions(self):
        src_d = (ROOT / "daily_live.py").read_text(encoding="utf-8").replace('"① 추세 조건"', '"① 추세 조건(옛 판)"')
        src_o = (ROOT / "overlay_live.py").read_text(encoding="utf-8").replace('"상승": ("122630", 0.4)', '"상승": ("122630", 0.3)')
        self.assertIn("(옛 판)", src_d)
        self.assertIn('("122630", 0.3)', src_o)
        D, O = self.old_module("daily_live", src_d), self.old_module("overlay_live", src_o)
        r = Repo()
        r.write("daily_live.py", src_d)
        r.write("overlay_live.py", src_o)
        r.etf("20261031")
        head = r.commit("옛 판", "2026-10-30 09:00:00")
        daily = dict(self.daily_body(D), **{"판단 때 저장소 HEAD": head, "코드": {"daily_live.py": r.git("rev-parse", "HEAD:daily_live.py")}})
        rows = [(str(d), float(c)) for d, c in real_closes("069500")["closes"] if c and str(d) < "20261030"]
        state = O.states(rows)[rows[-1][0]]
        st = {"applied": None, "rebalanced_month": None}
        _, want, f = O.target_qty("상승", 1e7, 8e6, 1e7, 0.0, 100.0)
        overlay = {"날": "20261030", "봇": "overlay", "판단 때 저장소 HEAD": head,
                   "코드": {"overlay_live.py": r.git("rev-parse", "HEAD:overlay_live.py")},
                   "입력": {"st": st, "day": "20261030", "prev_day": rows[-1][0], "stale": False, "state": state, "nav": 1e7,
                            "rows_len": len(rows), "rows_last": [list(x) for x in rows[-3:]]},
                   "결과": {"rebalance": O.needs_rebalance(st, state, "20261030")}, "곁": {"rows_digest": A.digest(rows)},
                   "주문 결과": {"rebalance": True, "orders": [["122630", "buy", want]],
                               "target": {"state": "상승", "nav_total": 1e7, "cash_b": 8e6, "nav_b": 1e7, "reserve": 0.0, "price": 100.0,
                                          "cur": {}, "want": want, "f": f}}}
        self.assertFalse(B.replay("daily", daily)[0])               # 지금 판(작업 나무)으로는 다름
        self.assertFalse(B.replay_overlay_target(overlay)[0])
        found = {("20261030", "daily"): ("daily-live/audit/20261030-daily.json", daily),
                 ("20261030", "overlay"): ("overlay-live/audit/20261030-overlay.json", overlay)}
        B.ERRS.clear()
        with mock.patch.object(B, "ROOT", r.root):
            got = B.check_groups(found)
        self.assertEqual(B.ERRS, [])
        d, o = got[("20261030", "daily")], got[("20261030", "overlay")]
        self.assertTrue(d["same"] and d["isolated"], d)               # 판단 때 HEAD 판으로는 같음 · 모듈은 그 트리에서
        self.assertTrue(o["same"] and o["target_ok"] and o["isolated"] and o["rebuild"] == [], o)
        self.assertRegex(d["tree"], r"^[0-9a-f]{64}$")             # 격리 재현 트리 지문(같은 묶음이면 같음)
        self.assertEqual(d["tree"], o["tree"])

    def test_missing_module_not_borrowed(self):
        """판단 때 HEAD 트리에 daily_live.py가 없으면 작업 나무 것을 쓰지 않고 '재현 못 함(불완전)'."""
        r = Repo()
        (r.root / "daily_live.py").unlink()
        head = r.commit("daily 없음", "2026-10-30 09:00:00")
        import daily_live as D
        body = dict(self.daily_body(D), **{"판단 때 저장소 HEAD": head, "코드": {"audit_log.py": r.git("rev-parse", "HEAD:audit_log.py")}})
        B.ERRS.clear()
        with mock.patch.object(B, "ROOT", r.root):
            got = B.check_groups({("20261030", "daily"): ("x", body)})
        self.assertEqual(got, {})
        self.assertTrue(B.ERRS and "하위 작업" in B.ERRS[0])
        B.ERRS.clear()


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
        body = {"날": day, "봇": "basket", "판단 때 저장소 HEAD": head, "입력": inp, "결과": A.plain({"orders": o, "new_state": st, "why": why}),
                "곁": A.plain({"days_since_calls": calls, "days_tail": days[-A.DAYS_TAIL:], "before": days[-3]})}
        ctx = {"main_events": {"000002": [(t0, "자사주취득")], "000004": [(t0, "자사주취득")], "000005": [(t0, "무상증자")]}}
        return body, days, ctx

    def test_replay_inputs_and_mutations(self):
        body, days, ctx = self.body()
        self.assertEqual(B.replay("basket", body)[::2], (True, "같음"))
        probs, info = B.inputs_check("basket", body, days, ctx)
        self.assertEqual(probs, [])
        self.assertIn("사건 종목 000002 지금 값 없음(결정과 무관)", info)          # 앞 사건과 20거래일 안이라 어차피 셈 안 함
        self.assertTrue(any(s.startswith("참고 · 판단 앞 마지막 공시 커밋") for s in info))   # 커밋 시각은 참고만(인증 아님)
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
        self.assertIn("LATE_INPUT", [t for t, _ in B.inputs_check("basket", body, days[:-2] + days[-1:], ctx)[0]])   # 목록 ≠ 분모 거래일

    def test_late_events_material_only(self):
        body, days, ctx = self.body()
        t0 = body["입력"]["t0"]
        body["입력"]["inside"] = body["입력"]["inside"] + ["000009", "000010"]
        body["입력"]["react"] = dict(body["입력"]["react"], **{"000009": -0.04, "000010": 0.03})
        ev2 = dict(ctx["main_events"], **{"000010": [(t0, "자사주취득")]})        # 반응 +3% → 결정 무관
        probs, info = B.inputs_check("basket", body, days, {"main_events": ev2})
        self.assertEqual([t for t, _ in probs], [])
        self.assertTrue(any("결정과 무관" in s for s in info))
        ev3 = dict(ev2, **{"000009": [(t0, "자사주취득")]})                      # 반응 −4% → 결정이 달랐을 수 있음
        probs, _ = B.inputs_check("basket", body, days, {"main_events": ev3})
        self.assertEqual([t for t, _ in probs], ["LATE_INPUT"])

    def test_rebuild_real_data(self):
        """판단 때 판 자료로 반응 · 200위 안 · t0 사건을 다시 셈(실제 자료 · 작업 나무 = 판단 때 판 흉내)."""
        import basket_live as BL
        import study
        t0, before = "20261105", "20261104"
        react, inside = BL.reactions(study.load_prices(), t0, before)
        ev = BL.todays_events(BL.load_events(), t0, before)
        body = {"날": "20261106", "입력": A.plain({"t0": t0, "react": react, "inside": inside, "events_t0": ev}), "곁": {"before": before}}
        self.assertEqual(B.rebuild("basket", body), {"rebuild": []})
        body["입력"]["react"] = dict(body["입력"]["react"], **{next(iter(react)): 0.5})
        self.assertEqual(B.rebuild("basket", body), {"rebuild": ["바구니 react"]})


class Daily(unittest.TestCase):
    def body(self):
        import daily_live as D
        held = {"000001": {"code": "000001", "name": "가", "kind": "추세", "price": 1000.0, "peak": 1300.0, "max_close": 1300.0,
                           "last_close": 1200.0, "칸": 2, "처음칸": 2, "days": 5, "bought": "20261020"}}
        cands = [{"code": c, "name": c, "추세문": True, "3일연속": False, "거래량비": 1.0, "정배열일수": 3, "추세 기울기": s}
                 for c, s in (("000002", 2.0), ("000003", 1.0), ("000004", float("nan")))]
        now_price = {"000001": 1100.0, "000002": 500.0, "000003": 700.0, "000004": 900.0}
        aligned, rate = {"000001": False}, {"000002": 1.0, "000003": 2.0}
        inp = A.capture(dict(state={"positions": held}, cands=cands, now_price=now_price, aligned=aligned, rate=rate))
        calls = []
        s, b = D.decide({"positions": held, "closed": []}, cands, now_price, aligned, rate, A.recorder(lambda c, h: c != "000003", calls))
        return json.loads(json.dumps({"날": "20261030", "판단 때 저장소 HEAD": "h", "입력": inp, "결과": A.plain({"sells": s, "buys": b}),
                                      "곁": A.plain({"kin_calls": calls, "ready": True, "expect": "20261029", "quotes": 4, "pool": 4,
                                                    "data_asof": {"max": "20261029", "today_or_later": 0, "codes": 4}})}))

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
        self.assertEqual([t for t, _ in B.inputs_check("daily", broken, cal, None)[0]], ["기록 고장"])
        self.assertEqual(B.code_problems(dict(body, 코드=None)), "기록 고장(코드 판 없음)")
        self.assertEqual(B.code_problems(dict(body, **{"판단 때 저장소 HEAD": None})), "기록 고장(판단 때 HEAD 없음)")


class Overlay(unittest.TestCase):
    def test_real_run_receipt_replays(self):
        from tests import test_audit_log as T
        orders, lines, st, body, _ = T.OverlayReceipt()._run(block=False)
        self.assertEqual(B.replay("overlay", body)[::2], (True, "같음"))
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
    S = SESS["보통"]

    def test_timing(self):
        b = {"기록 시각(한국)": "2026-11-09 15:11:00", "부른 까닭": "schedule", "곁": {"late_at_decision": False}, "주문 결과": {"late": False}}
        self.assertEqual(B.timing("engine", b, self.S), ([], []))
        late = dict(b, **{"기록 시각(한국)": "2026-11-09 15:31:00", "부른 까닭": "workflow_dispatch", "주문 결과": {"late": True}})
        probs, info = B.timing("daily", late, self.S)
        self.assertEqual([t for t, _ in probs], ["SCHEDULER"])        # 손으로 불렀어도 늦으면 설명 필요
        self.assertTrue(info and info[0].startswith("MANUAL"))
        self.assertEqual([t for t, _ in B.timing("overlay", dict(b, **{"기록 시각(한국)": "2026-11-09 15:21:00"}), self.S)[0]], ["SCHEDULER"])
        self.assertTrue(B.timing("engine", dict(b, **{"부른 까닭": None}), self.S)[1][0].endswith("작업 흐름 밖"))

    def test_broker_and_orders(self):
        body = {"날": "20261109", "결과": {"orders": [["133690", "buy", 3, "r"], ["138230", "sell", 2, "r"]]}, "주문 결과": {"late": False},
                "오늘 장부 주문": {"idle-live/paper-orders.json": [
                    {"key": "20261109:buy:133690", "code": "133690", "side": "buy", "status": "접수 · 3주 중 살 수 있는 2주로 줄임"},
                    {"key": "202611091512:room:229200", "code": "229200", "side": "sell", "status": "실패 · x"}],
                    "x.json": "읽기 실패 · AttributeError"}}
        self.assertEqual(sorted(t for t, _ in B.broker_check("engine", body)), ["BROKER", "BROKER", "LEDGER"])
        self.assertEqual(B.orders_check("engine", body), [("주문 빠짐", "138230 sell 판단했으나 장부에 없음")])
        self.assertEqual(B.orders_check("engine", dict(body, **{"주문 결과": {"late": True}})), [])
        # 판 3 고침 8: 흔들림 상한이 막힌 날(곁 stop_buys True)은 엔진이 기록 뒤 매수를 빼므로 매수는 대조 밖 · 팔기는 그대로 대조
        blocked = dict(body, **{"결과": {"orders": [["251340", "buy", 5, "r"], ["138230", "sell", 2, "r"]]}, "곁": {"stop_buys": True}})
        self.assertEqual([t for t, _ in B.orders_check("engine", blocked)], ["주문 빠짐", "금지 주문"])   # 장부의 133690 매수 줄은 막힌 날 금지
        self.assertEqual([t for t, _ in B.orders_check("engine", dict(blocked, **{"곁": {"stop_buys": False}}))], ["주문 빠짐", "주문 빠짐"])
        self.assertEqual(len(B.orders_check("engine", dict(blocked, **{"곁": {}}))), 2)                 # 칸 없으면 예전 그대로
        self.assertEqual(len(B.orders_check("basket", dict(blocked, **{"곁": {"stop_buys": True}}))), 2)  # 바구니는 막힘 칸과 무관(판단 앞에 돈으로 막음)
        # 반대 방향(GPT #491): 막힌 날 엔진 장부에 매수 줄이 있으면(접수든 실패든) '금지 주문' 즉시 실패
        sold = {"key": "20261109:sell:138230", "code": "138230", "side": "sell", "status": "접수"}
        ok_day = dict(blocked, **{"오늘 장부 주문": {"idle-live/paper-orders.json": [sold]}})
        self.assertEqual(B.orders_check("engine", ok_day), [])                                            # 1: 매수 없음 · 팔기 있음
        for st in ("접수", "실패 · x"):
            bad = dict(blocked, **{"오늘 장부 주문": {"idle-live/paper-orders.json": [
                sold, {"key": "20261109:buy:251340", "code": "251340", "side": "buy", "status": st}]}})
            self.assertEqual([t for t, _ in B.orders_check("engine", bad)], ["금지 주문"], st)               # 2: 금지 매수
        self.assertIn("금지 주문", B.MISSING)                                                               # 면책 없는 즉시 실패 묶음
        no_sell = dict(blocked, **{"오늘 장부 주문": {"idle-live/paper-orders.json": []}})
        self.assertEqual([t for t, _ in B.orders_check("engine", no_sell)], ["주문 빠짐"])                  # 3: 팔기 빠짐
        daily = {"날": "20261109", "결과": {"sells": [{"code": "000001", "type": "sell"}], "buys": [{"code": "000002", "type": "buy"}]},
                 "주문 결과": {"late": False, "paper": ["🧪 모의투자(1일봉) 매수 건너뜀 · 둘(000002) · 살 돈이 모자람(1주 미만)"]},
                 "오늘 장부 주문": {"daily-live/paper-orders.json": [{"key": "202611091520:sell:000001:20261109", "status": "접수"}]}}
        self.assertEqual(B.orders_check("daily", daily), [])
        daily["주문 결과"]["paper"] = []
        self.assertEqual([t for t, _ in B.orders_check("daily", daily)], ["주문 빠짐"])

    def test_gate_closed_engine_two_ways(self):
        """BOOST-0001-D 문(곁 gates · 판단 id engine · open False): 고침 8과 같은 양방향 — 판단 원본 매수 부재는 정상 ·
        그날 엔진 장부 매수 줄은 금지 주문 · 팔기 빠짐은 주문 빠짐 · 칸이 없거나 꼴이 이상하면 예전 대조."""
        shut = {"decision": "engine", "open": False, "reasons": ["저장소를 최신으로 맞추지 못함"]}
        sold = {"key": "20261109:sell:138230", "code": "138230", "side": "sell", "status": "접수"}
        body = {"날": "20261109", "결과": {"orders": [["133690", "buy", 3, "r"], ["138230", "sell", 2, "r"]]}, "주문 결과": {"late": False},
                "오늘 장부 주문": {"idle-live/paper-orders.json": [sold]}, "곁": {"stop_buys": False, "gates": shut}}
        self.assertEqual(B.orders_check("engine", body), [])                                               # 1: 매수 없음 · 팔기 있음 → 0
        for st in ("접수", "실패 · x"):
            bad = dict(body, **{"오늘 장부 주문": {"idle-live/paper-orders.json": [
                sold, {"key": "20261109:buy:133690", "code": "133690", "side": "buy", "status": st}]}})
            got = B.orders_check("engine", bad)
            self.assertEqual([t for t, _ in got], ["금지 주문"], st)                                       # 2: 금지 매수(접수든 실패든)
            self.assertIn("문(BOOST-0001-D)이 막힌 날", got[0][1])
        no_sell = dict(body, **{"오늘 장부 주문": {"idle-live/paper-orders.json": []}})
        self.assertEqual([t for t, _ in B.orders_check("engine", no_sell)], ["주문 빠짐"])                  # 3: 팔기 빠짐
        both = dict(bad, **{"곁": {"stop_buys": True, "gates": shut}})
        got = B.orders_check("engine", both)
        self.assertEqual([t for t, _ in got], ["금지 주문"], "흔들림 상한 · 문이 함께 막아도 줄 하나에 하나")
        self.assertIn("흔들림 상한이 · 문(BOOST-0001-D)이", got[0][1])
        opened = dict(body, **{"곁": {"gates": dict(shut, open=True)}})
        self.assertEqual([t for t, _ in B.orders_check("engine", opened)], ["주문 빠짐"], "문이 열렸으면 매수 부재는 주문 빠짐")
        for broken in ({}, {"gates": None}, {"gates": "닫힘"}, {"gates": dict(shut, open="false")}, {"gates": dict(shut, open=None)},
                       {"gates": dict(shut, decision="basket")}, {"gates": {"open": False}}):
            self.assertEqual([t for t, _ in B.orders_check("engine", dict(body, **{"곁": broken}))], ["주문 빠짐"], broken)   # 4: 예전대로

    def test_gate_closed_basket_and_daily_unchanged(self):
        """바구니 · 1일봉은 문이 닫히면 판단에 매수가 없으므로 그대로(문 칸으로 면제하지 않음)."""
        rows = [{"key": "20261109:sell:000020", "code": "000020", "side": "sell", "status": "접수"}]
        basket = {"날": "20261109", "결과": {"orders": [["000020", "sell", 200, "r"]]}, "주문 결과": {"late": False},
                  "오늘 장부 주문": {"basket-live/paper-orders.json": rows}, "곁": {"gates": {"decision": "basket", "open": False}}}
        self.assertEqual(B.orders_check("basket", basket), [])
        self.assertEqual([t for t, _ in B.orders_check("basket", dict(basket, **{"오늘 장부 주문": {}}))], ["주문 빠짐"])
        odd = dict(basket, **{"결과": {"orders": [["000040", "buy", 5, "r"], ["000020", "sell", 200, "r"]]}})
        self.assertEqual([t for t, _ in B.orders_check("basket", odd)], ["주문 빠짐"], "바구니 판단에 매수가 있으면 문 칸과 상관없이 대조")
        daily = {"날": "20261109", "결과": {"sells": [{"code": "000010", "type": "sell"}], "buys": []}, "주문 결과": {"late": False, "paper": []},
                 "오늘 장부 주문": {"daily-live/paper-orders.json": [{"key": "202611091520:sell:000010:20261109", "status": "접수"}]},
                 "곁": {"gates": {"decision": "daily", "open": False}}}
        self.assertEqual(B.orders_check("daily", daily), [])
        self.assertEqual([t for t, _ in B.orders_check("daily", dict(daily, **{"오늘 장부 주문": {}}))], ["주문 빠짐"])

    def test_overlay_gate_dropped_two_ways(self):
        """덧붙임: 주문 결과 gate_dropped의 매수 다리(곁 buy_ok False)는 장부 부재 정상 · 그 종목 매수 줄(장부 · 보낸 주문)은 금지 주문."""
        sell = {"key": "20261109:sell:122630", "code": "122630", "side": "sell", "status": "접수"}
        body = {"날": "20261109", "곁": {"buy_ok": False, "gates": {"decision": "overlay", "open": False}},
                "주문 결과": {"late": False, "orders": [["122630", "sell", 1000], ["114800", "buy", 500]],
                            "sent": [{"code": "122630", "side": "sell", "status": "접수"}], "gate_dropped": [["114800", "buy", 500]]},
                "오늘 장부 주문": {"overlay-live/paper-orders.json": [sell]}}
        self.assertEqual(B.orders_check("overlay", body), [])
        bought = {"key": "20261109:buy:114800", "code": "114800", "side": "buy", "status": "접수"}
        bad = dict(body, **{"오늘 장부 주문": {"overlay-live/paper-orders.json": [sell, bought]}})
        self.assertEqual([t for t, _ in B.orders_check("overlay", bad)], ["금지 주문"])
        res = dict(body["주문 결과"], sent=body["주문 결과"]["sent"] + [{"code": "114800", "side": "buy", "status": "접수"}])
        self.assertEqual([t for t, _ in B.orders_check("overlay", dict(body, **{"주문 결과": res}))], ["금지 주문"], "보낸 주문에만 있어도")
        no_sell = dict(body, **{"주문 결과": dict(body["주문 결과"], sent=[]), "오늘 장부 주문": {}})
        self.assertEqual([t for t, _ in B.orders_check("overlay", no_sell)], ["주문 빠짐"], "팔기 빠짐은 그대로")
        for broken_res, broken_side in ((dict(body["주문 결과"], gate_dropped=None), body["곁"]),
                                        (dict(body["주문 결과"], gate_dropped="114800"), body["곁"]),
                                        (dict(body["주문 결과"], gate_dropped=[["114800"]]), body["곁"]),
                                        (dict(body["주문 결과"], gate_dropped=[[114800, "buy", 500]]), body["곁"]),
                                        (dict(body["주문 결과"], gate_dropped=[["114800", "sell", 500]]), body["곁"]),
                                        (body["주문 결과"], {"buy_ok": True}), (body["주문 결과"], {})):
            got = B.orders_check("overlay", dict(body, **{"주문 결과": broken_res, "곁": broken_side}))
            self.assertEqual([t for t, _ in got], ["주문 빠짐"], (broken_res.get("gate_dropped"), broken_side))       # 예전대로

    HEAD = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    RAW = json.loads((ROOT / "tests" / "fixtures" / "boost_run_42227497428.json").read_text(encoding="utf-8"))  # 실제 API 응답 원문

    @classmethod
    def receipt(cls, rid, wf, created, repo="ppx109-crypto/stock-dash", head_sha=None, drop=(), **over):
        """실제 응답 원문의 꼴을 그대로 두고 값만 바꾼 뒤 변환기(receipt_from_api)를 거친 영수증 · over / drop은 변환 뒤 변조."""
        raw = json.loads(json.dumps(cls.RAW))
        raw.update(id=int(rid), url=f"https://api.github.com/repos/{repo}/actions/runs/{rid}", path=f".github/workflows/{wf}",
                   html_url=f"https://github.com/{repo}/actions/runs/{rid}", created_at=created, head_sha=head_sha or cls.HEAD)
        raw["repository"]["full_name"] = raw["head_repository"]["full_name"] = repo
        rec = B.receipt_from_api(raw, f"https://api.github.com/repos/{repo}/actions/runs/{rid}")
        rec.update(over)
        for k in drop:
            rec.pop(k)
        return rec

    @property
    def RUNS(self):
        R, d = self.receipt, ("daily-live.yml", "2026-11-09T06:31:00Z")
        bad = {"42250000004": dict(head_sha="0" * 40), "42250000005": dict(drop=("head_sha",)), "42250000006": dict(drop=("conclusion",)),
               "42250000007": dict(id=42250000008), "42250000009": dict(html_url=self.html("42250000009") + "/attempts/1"),
               "42250000010": dict(status="in_progress"), "42250000011": dict(head_branch="claude/x"),
               "42250000012": dict(schema_version="boost-run-receipt/0"), "42250000013": dict(raw_sha256="0" * 63),
               "42250000014": dict(path=".github/workflows/daily-live.yml@main"),
               "42250000015": dict(repository_full_name="ppx109-crypto/stock-dash2"),
               "42250000016": dict(url="https://api.github.com/repos/ppx109-crypto/stock-dash/actions/runs/42250000017"),
               "42250000017": dict(head_repository_full_name="someone/stock-dash"),
               "42250000018": dict(html_url=self.html("42250000018") + "0"),
               "42250000019": dict(request_url="https://api.github.com/repos/someone/other/actions/runs/42250000019")}
        runs = {"42259467975": R("42259467975", *d),
                "42250000001": R("42250000001", "etf-prices.yml", "2026-11-06T10:40:00Z", conclusion="failure"),
                "42250000002": R("42250000002", *d, repo="someone/other"),
                "42250000003": R("42250000003", "daily-live.yml", "2026-11-12T06:31:00Z")}
        runs.update({k: R(k, *d, **v) for k, v in bad.items()})
        return runs
    BAD_RUNS = (9999999999, 42259467976, 42250000002, 42250000003) + tuple(range(42250000004, 42250000020))
    CAL = ["20261106", "20261109", "20261110", "20261111", "20261112"]

    @staticmethod
    def html(rid):
        return f"https://github.com/ppx109-crypto/stock-dash/actions/runs/{rid}"

    def ok(self, e, tag, key="20261109:basket", runs=None, root=ROOT, end=None):
        with mock.patch.object(B, "ROOT", root), mock.patch.object(B, "END", end or self.HEAD):  # 앞 시험이 끝점을 바꿔 두었어도 같게
            return B.receipt_matches(e, key, tag, self.RUNS if runs is None else runs, self.CAL)

    def test_receipt_note_format(self):
        """상황 기록의 작업 영수증 대조(참고만): run_id는 영수증 파일에 있고 판 3 고침 5 꼴 · 이 저장소 main의 끝난 작업 · 주소 정확히 ·
        작업 흐름 · 그 날(또는 앞 거래일)이어야 '맞음' · commit만 · 자유 글 · 날짜 · 형식만 맞는 번호 · 다른 저장소 · 다른 날은 '안 맞음'."""
        self.assertTrue(self.ok({"원인": "SCHEDULER", "run_id": 42259467975, "근거": "15:31 시작"}, "빠짐"))
        self.assertTrue(self.ok({"run_id": "42259467975"}, "BROKER"))
        self.assertTrue(self.ok({"run_id": 42250000001}, "LATE_INPUT"))           # 앞 거래일(11-06) ETF 수집 실패 작업
        self.assertFalse(self.ok({"run_id": 42250000001}, "SCHEDULER"))           # 작업 흐름이 안 맞음
        others = ({"근거": "20261109"}, {"근거": "날짜 20261109 · 작업 42259467975"}, {"run_id": "20261109"}, {"run_id": 12345678},
                  {"run_id": "작업 42259467975"}, {"commit": "abcdef1"}, {"commit": "deadbeefcafe"}, {"commit": "날짜20261109"},
                  {"commit": self.HEAD}, {"commit": self.HEAD[:10]}, "작업 42259467975", "", None)
        for e in tuple({"run_id": x} for x in self.BAD_RUNS) + others:
            self.assertFalse(self.ok(e, "BROKER"), e)                               # 변조 · 없는 번호 · 다른 저장소 · 다른 날 · commit만 · 자유 글
            self.assertFalse(self.ok(dict(e, 원인="SCHEDULER") if isinstance(e, dict) else e, "빠짐"), e)
        self.assertFalse(self.ok({"run_id": 42259467975}, "BROKER", key="20261111:basket"))   # 그 날 · 앞 거래일 작업이 아님

    def test_real_api_receipt(self):
        """실제 작업 API 응답 원문(tests/fixtures · 2026-11-06 daily-live 작업)이 변환기를 거쳐 통과 · 저장소 묶음 · 주소 변조는 거부.
        작업 커밋 대조는 CI의 얕은 가져오기에 그 커밋이 없어 이 시험에서만 참으로 두고, 실제 git 대조는 test_bare_commit_never_exempts에서 함."""
        rid = str(self.RAW["id"])

        def ok(raw=None, rec=None, key="20261106:daily", tag="SCHEDULER"):
            rec = B.receipt_from_api(raw, B.api_url(rid)) if rec is None else rec
            with mock.patch.object(B, "commit_exists", return_value=True), mock.patch.object(B, "is_ancestor", return_value=True):
                return B.receipt_matches({"run_id": rid}, key, tag, {rid: rec}, self.CAL)

        def raw_with(fn):
            raw = json.loads(json.dumps(self.RAW))
            fn(raw)
            return raw
        rec = B.receipt_from_api(self.RAW, B.api_url(rid))
        self.assertEqual((rec["repository_full_name"], rec["raw_sha256"]), ("ppx109-crypto/stock-dash", A.digest(self.RAW)))
        self.assertTrue(ok(self.RAW))
        self.assertTrue(ok(self.RAW, key="20261109:daily"))                     # 앞 거래일 작업
        self.assertTrue(ok(self.RAW, tag="LATE_INPUT"))
        self.assertTrue(ok(rec=json.loads(json.dumps(rec))))                     # 파일로 썼다 읽어도(온라인 API 없이) 같음
        self.assertFalse(ok(self.RAW, key="20261110:daily"))
        self.assertFalse(ok(raw_with(lambda r: r["repository"].update(full_name="someone/stock-dash"))))
        self.assertFalse(ok(raw_with(lambda r: r["head_repository"].update(full_name="someone/stock-dash"))))
        for broken in (lambda r: r.update(repository="ppx109-crypto/stock-dash"), lambda r: r.pop("repository"),
                       lambda r: r["head_repository"].pop("full_name")):
            with self.assertRaises((TypeError, KeyError)):                     # 묶음이 아니거나 칸이 없으면 영수증을 못 만듦
                B.receipt_from_api(raw_with(broken), B.api_url(rid))
        flat = {k: self.RAW[k] for k in ("id", "path", "head_sha", "event", "run_attempt", "status", "conclusion", "created_at", "html_url")}
        self.assertFalse(ok(rec=dict(flat, repository="ppx109-crypto/stock-dash")))   # 고침 4의 자체 요약 꼴은 거부
        for k, v in (("html_url", rec["html_url"] + "/attempts/1"), ("html_url", rec["html_url"] + "0"), ("url", rec["url"] + "0"),
                     ("request_url", rec["request_url"].replace("ppx109-crypto", "someone"))):
            self.assertFalse(ok(rec=dict(rec, **{k: v})), (k, v))                # 주소는 정확히 같아야 함

    def test_receipt_note_commit(self):
        """commit만으로는 작업 영수증 '맞음'이 아님(바탕 · 무관 문서만 고친 · 다른 날 · 끝점 자신 · 가지 · 없는 커밋 모두) ·
        작업 영수증은 작업 커밋이 끝점 조상일 때만 '맞음' · commit 칸은 결과에 참고로만."""
        r = Repo(code=False)
        r.write("a.txt", "1")
        base = r.commit("바탕", "2026-11-01 09:00:00")
        r.write("notes.md", "x")
        doc = r.commit("문서만", "2026-11-09 09:30:00")
        r.git("checkout", "-q", "-b", "side")
        r.write("b.txt", "2")
        side = r.commit("가지", "2026-11-09 10:00:00")
        r.git("checkout", "-q", "main")
        r.write("c.txt", "3")
        tip = r.commit("끝", "2026-11-09 11:00:00")
        at = dict(root=r.root, end=tip)
        for com in (base, base[:12], doc, tip, side, "0" * 40):
            self.assertFalse(self.ok({"commit": com}, "LEDGER", **at), com)
            self.assertFalse(self.ok({"원인": "LEDGER", "commit": com}, "주문 빠짐", **at), com)
        runs = {"42259467975": self.receipt("42259467975", "daily-live.yml", "2026-11-09T06:31:00Z", head_sha=base),
                "42259467976": self.receipt("42259467976", "daily-live.yml", "2026-11-09T06:31:00Z", head_sha=side)}
        self.assertTrue(self.ok({"run_id": 42259467975, "commit": side}, "BROKER", runs=runs, **at))
        self.assertFalse(self.ok({"run_id": 42259467976}, "BROKER", runs=runs, **at))                 # 작업 커밋이 합쳐지지 않은 가지
        with mock.patch.object(B, "ROOT", r.root), mock.patch.object(B, "END", tip):
            self.assertEqual((B.commit_ok(base), B.commit_ok(side)), (True, False))                     # 결과의 참고 칸

    def test_no_exemption(self):
        """면책 없음(판 3 고침 6): 모든 꼬리표에 맞는 작업 영수증(그 날 정상 성공 daily-live 예약 작업)과 원인을 적어도
        즉시 실패 · 남은 꼬리표 · 판정 · 보강 칸이 설명이 없을 때와 똑같음 · 상황 기록에는 '맞음'으로 적힘."""
        off = {"20261119": {"까닭": "수능날"}}
        r = Repo()
        r.etf("29991231")
        b = {"날": "20261119", "봇": "daily", "기록 시각(한국)": "2026-11-19 15:21:00", "판단 때 저장소 HEAD": None, "입력": None}
        r.write("daily-live/audit/20261119-daily.json", b)
        sha_ = r.commit("기록", "2026-11-20 19:30:00")
        ev = "42259467975"
        runs = {ev: self.receipt(ev, "daily-live.yml", "2026-11-18T06:21:00Z", head_sha=sha_)}   # 정상 성공 예약 작업
        days = rd(["20261118", "20261120"], trading=["20261118", "20261119", "20261120"], off=off)
        with mock.patch.object(B, "ROOT", r.root):
            bare = B.audit("20261118", "20261120", causes={}, runs=runs, run_days=days)
            tags = {(f"{x['날']}:{x['봇']}", t) for x in bare["줄들"] for t, _ in x["문제"]}
            causes = {}
            for k, t in tags:
                causes.setdefault(k, {})[t] = {"원인": "SCHEDULER" if t in B.MISSING else t, "run_id": ev, "근거": "정상 작업"}
            res = B.audit("20261118", "20261120", causes=causes, runs=runs, run_days=days)
        S0, S1 = bare["요약"], res["요약"]
        for k in ("즉시 실패", "남은 꼬리표", "판정", "보강 칸", "실행 보강 필요"):
            self.assertEqual(S1[k], S0[k], k)
        self.assertEqual(S1["판정"], "실패")
        fails, needs = {(k, t) for k, t, _ in S1["즉시 실패"]}, {(k, t) for k, t, _ in S1["남은 꼬리표"]}
        self.assertIn(("20261118:daily", "빠짐"), fails)
        self.assertIn(("20261119:daily", "예정 무실행 날 실행"), fails)
        for k, t in tags:                                                        # 모든 꼬리표가 판정에 그대로 남음
            self.assertIn((k, t), needs if t in B.CODES else fails, (k, t))
        self.assertTrue(any(t in B.CODES for _, t in tags) and any(t in B.MISSING for _, t in tags))   # 두 갈래가 다 시험됨
        notes = S1["상황 기록(참고 · 판정에 안 씀)"]
        self.assertTrue(any(n[0] == "20261118:daily" and n[6] and n[6].startswith("작업 영수증 맞음") for n in notes))

    def test_strain_fixed_80(self):
        """실행 보강률 분모는 언제나 고정 칸(20일 × 4 = 80): 8/80 아님 · 9/80 필요 · 부분 기간 4문제 = 4/80 · 예정 무실행 날 기록 하나 더 = 5/80."""
        def rows(n, tag="SCHEDULER"):
            return [{"날": f"d{i // 4}", "봇": f"b{i % 4}", "문제": [(tag, ""), ("빠짐", "")]} for i in range(n)]
        self.assertEqual(B.strain(rows(8), 80), (8, 80, False))
        self.assertEqual(B.strain(rows(9), 80), (9, 80, True))
        self.assertEqual(B.strain(rows(3) + [{"날": "x", "봇": "y", "문제": [("LATE_INPUT", "")]}], 80)[0], 3)   # 대상 아닌 꼬리표는 안 셈
        self.assertEqual(B.strain(rows(3) + [{"날": "z", "봇": "y", "문제": [("OFF_CALENDAR", "")]}], 80)[0], 4)  # 분모 밖 기록 칸은 +1
        run = [f"202611{d:02d}" for d in (9, 10, 11, 12, 13, 16, 17, 18, 20, 23, 24, 25, 26, 27, 30)] + ["20261201", "20261202", "20261203",
                                                                                                       "20261204", "20261207"]
        trading = sorted(set(run) | {"20261106", "20261119"})
        off = {"20261119": {"까닭": "수능날"}}
        r = Repo()
        r.etf("29991231")
        r.commit("자료", "2026-11-09 19:30:00")
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261109", "20261109", run_days=rd(run, trading=trading, off=off))
        self.assertEqual((res["요약"]["보강 칸"], res["요약"]["실행 보강 필요"], res["요약"]["기록 수"]), ("4/80", False, "0/4"))
        r.write("daily-live/audit/20261119-daily.json", {"날": "20261119", "봇": "daily", "기록 시각(한국)": "2026-11-19 15:21:00",
                                                        "판단 때 저장소 HEAD": None, "입력": None})
        r.commit("기록", "2026-11-19 19:30:00")
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261109", "20261119", run_days=rd(run, trading=trading, off=off))
        days_in = len([d for d in run if d <= "20261119"])
        self.assertEqual(res["요약"]["보강 칸"], f"{days_in * 4 + 1}/80")      # 기대 실행일 빠짐 칸들 + 예정 무실행 날 실행 1칸

    def test_scheduler_skip_strain_and_verdict(self):
        """엔진이 마감 뒤에 돈 날 바구니 · 덧붙임 기록이 없으면 각 칸에 빠짐(사실)과 SCHEDULER(원인 정황)가 함께 · 빠짐은 즉시 실패 ·
        설명 · 맞는 작업 영수증이 있어도 같음 · 엔진이 제때면 SCHEDULER 없이 빠짐만 · 기록 고장은 즉시 실패 · 보강 칸은 고유 칸 수."""
        r = Repo()
        r.etf("29991231")
        head = r.commit("아침", "2026-10-30 09:00:00")

        def engine(day, at, late):
            return {"날": day, "봇": "engine", "기록 시각(한국)": f"{day[:4]}-{day[4:6]}-{day[6:]} {at}:00", "작업 번호": "1", "작업 시도": "1",
                    "부른 까닭": "schedule", "판단 때 저장소 HEAD": head, "코드": None, "입력": None, "결과": {},
                    "주문 결과": {"late": late}, "덧붙인 시각(한국)": f"{day[:4]}-{day[4:6]}-{day[6:]} {at}:30"}
        r.write("idle-live/audit/20261030-engine.json", engine("20261030", "15:25", True))      # 마감 뒤
        r.write("idle-live/audit/20261102-engine.json", engine("20261102", "15:11", False))     # 제때
        tip = r.commit("Idle engine live", "2026-11-02 15:27:00")
        ev = "42259467975"
        runs = {ev: self.receipt(ev, "daily-live.yml", "2026-10-30T06:21:00Z", head_sha=tip)}
        days = rd(["20261030", "20261102", "20261103"], trading=["20261030", "20261102", "20261103"])
        results = []
        for causes in ({}, {"20261030:basket": {"빠짐": {"원인": "SCHEDULER", "run_id": ev}, "SCHEDULER": {"run_id": ev}},
                            "20261030:overlay": {"빠짐": {"원인": "SCHEDULER", "run_id": ev}, "SCHEDULER": {"run_id": ev}},
                            "20261030:engine": {"기록 고장": {"run_id": ev}}}):
            with mock.patch.object(B, "ROOT", r.root):
                results.append(B.audit("20261030", "20261103", causes=causes, runs=runs, run_days=days))
        res = results[0]
        for k in ("즉시 실패", "남은 꼬리표", "판정", "보강 칸", "실행 보강 필요"):
            self.assertEqual(results[1]["요약"][k], res["요약"][k], k)                  # 설명 · 맞는 영수증이 있어도 같음
        self.assertTrue(any(n[6] and n[6].startswith("작업 영수증 맞음") for n in results[1]["요약"]["상황 기록(참고 · 판정에 안 씀)"]))
        rows = {(x["날"], x["봇"]): [t for t, _ in x["문제"]] for x in res["줄들"]}
        for bot in ("basket", "overlay"):
            self.assertEqual(rows[("20261030", bot)], ["빠짐", "SCHEDULER"])           # 엔진 늦음: 사실 + 원인 정황
            self.assertEqual(rows[("20261102", bot)], ["빠짐"])                        # 엔진 제때: 빠짐만
        for bot in B.BOTS:
            self.assertEqual(rows[("20261103", bot)], ["빠짐"])                        # 아무 기록 없는 날: 네 봇 모두 빠짐
        self.assertIn("빠짐", rows[("20261030", "daily")])
        self.assertGreaterEqual(rows[("20261030", "engine")].count("SCHEDULER"), 1)
        for x in res["줄들"]:                                                            # 부재 불변식: 기록이 없으면 언제나 빠짐
            if "기록 시각" not in x:
                self.assertIn("빠짐", [t for t, _ in x["문제"]], (x["날"], x["봇"]))
        fails = {(k, t) for k, t, _ in res["요약"]["즉시 실패"]}
        for key in ("20261030:basket", "20261030:overlay", "20261102:basket", "20261102:overlay"):
            self.assertIn((key, "빠짐"), fails)
        self.assertIn(("20261030:engine", "기록 고장"), fails)
        self.assertIn(("20261030:basket", "SCHEDULER"), {(k, t) for k, t, _ in res["요약"]["남은 꼬리표"]})
        self.assertEqual(res["요약"]["판정"], "실패")
        self.assertEqual(res["요약"]["보강 칸"], "11/12")   # 10-30 넷 + 11-02 셋(제때 엔진은 보강 꼬리표 없음) + 11-03 넷 · 분모 = 고정 3일 × 4
        self.assertTrue(res["요약"]["실행 보강 필요"])

    def test_planned_off_day_and_off_calendar(self):
        """예정 무실행 날(수능날)은 분모 밖 · 빠짐 아님 · 그날 기록이 있으면 '예정 무실행 날 실행' · 분모 밖 다른 날 기록은 OFF_CALENDAR."""
        off = {"20261119": {"까닭": "수능날"}}
        trading = ["20261118", "20261119", "20261120"]
        r = Repo()
        r.etf("29991231")
        r.commit("자료", "2026-11-20 19:30:00")
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261118", "20261120", run_days=rd(["20261118", "20261120"], trading=trading, off=off))
        self.assertEqual(sorted({x["날"] for x in res["줄들"]}), ["20261118", "20261120"])
        self.assertEqual(res["요약"]["예정 무실행"], {"20261119": "수능날"})
        self.assertEqual((res["요약"]["기대 실행일"], res["요약"]["기록 수"], res["요약"]["불완전"]), (2, "0/8", []))
        b = {"날": "20261119", "봇": "daily", "기록 시각(한국)": "2026-11-19 15:21:00", "판단 때 저장소 HEAD": None, "입력": None}
        r.write("daily-live/audit/20261119-daily.json", b)
        r.write("daily-live/audit/20261121-daily.json", dict(b, 날="20261121"))
        r.commit("기록", "2026-11-21 19:30:00")
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261118", "20261121", run_days=rd(["20261118", "20261120"], trading=trading, off=off))
        tags = {x["날"]: [t for t, _ in x["문제"]] for x in res["줄들"] if x["봇"] == "daily"}
        self.assertIn("예정 무실행 날 실행", tags["20261119"])
        self.assertIn("OFF_CALENDAR", tags["20261121"])
        self.assertEqual(res["요약"]["기대 실행일"], 2)               # 분모 밖 기록은 분모를 늘리지 않음
        self.assertEqual(res["요약"]["분모 밖 기록 날"], ["20261119", "20261121"])

    def test_special_hours_mismatch_incomplete(self):
        """봇 코드의 쉬는 날(SPECIAL_HOURS)과 분모 파일의 예정 무실행이 다르면 불완전(빠짐 4칸 때문에 판정은 실패가 앞섬)."""
        r = Repo()
        r.etf("29991231")
        r.commit("자료", "2026-11-20 19:30:00")
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261118", "20261120", run_days=rd(["20261118", "20261119", "20261120"]))
        self.assertEqual(res["요약"]["판정"], "실패")
        self.assertTrue(any("예정 무실행" in e for e in res["요약"]["불완전"]))

    def test_run_days_pinned_and_end_commit(self):
        B.ERRS.clear()
        rd0 = B.load_run_days()
        self.assertEqual(B.ERRS, [])
        self.assertEqual(len(rd0["기대 실행일"]), 20)
        self.assertNotIn("20261119", rd0["기대 실행일"])
        self.assertEqual((rd0["기대 실행일"][0], rd0["기대 실행일"][-1]), ("20261109", "20261207"))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.json"
            p.write_text(json.dumps(dict(rd0, 기대실행일=[])), encoding="utf-8")
            B.ERRS.clear()
            B.load_run_days(p)
            self.assertTrue(B.ERRS and "지문" in B.ERRS[0])           # 고정 분모를 바꾸면 불완전
        B.ERRS.clear()
        r = Repo(code=False)
        with mock.patch.object(B, "ROOT", r.root):
            res = B.audit("20261030", "20261030", end_commit="없는커밋", run_days=rd(["20261030"]))
        self.assertEqual(res["요약"]["판정"], "불완전(다시 셈)")


if __name__ == "__main__":
    unittest.main()
