"""ETF-RULE-PACK-0001 시험(합성 예제 12개 · 코드 계약 시험이지 전략 성과 시험 아님 · 네트워크 0).
python3 -I tests/test_rules.py <원본 폴더>
<원본 폴더>에는 PR #36 고정 head(841b657e)의 idle_live.py와 research/idle_signal.py를 `git show`로 꺼내 둡니다."""
import ast
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ORIG = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(HERE))
import rules as R  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


O = load("idle_live_orig", ORIG / "idle_live.py")          # 원본이 research/idle_signal.py를 스스로 붙임
OS = sys.modules["idle_signal"]
RES = []


def record(name, fn):
    try:
        fn()
        RES.append({"case": name, "result": "PASS"})
    except Exception as e:  # noqa: BLE001
        RES.append({"case": name, "result": "FAIL", "why": f"{type(e).__name__}: {str(e)[:200]}"})


# ── 원본 보존(예제 아님): 함수 몸통 AST · 상수 ──
def _body(path, name, rename=None):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(getattr(fn.body[0], "value", None), ast.Constant):
        fn.body = fn.body[1:]
    s = ast.dump(fn)
    return s.replace(rename[0], rename[1]) if rename else s


def t_source_preserved():
    rp = HERE / "rules.py"
    for name in ("_ret", "decide"):
        assert _body(rp, name) == _body(ORIG / "research/idle_signal.py", name), name
    for name in ("inv_take", "next_trading_day", "week_end"):
        assert _body(rp, name) == _body(ORIG / "idle_live.py", name), name
    a = _body(rp, "step")
    b = _body(ORIG / "idle_live.py", "step",
              ("Attribute(value=Name(id='idle_signal', ctx=Load()), attr='decide', ctx=Load())", "Name(id='decide', ctx=Load())"))
    assert a == b, "step 몸통 다름"
    for k in ("DECIDE_AT", "LAST_ORDER", "DIP", "DOL", "INV", "K200", "Q150", "CODES", "DIP_TAKE", "DIP_STOP", "DIP_DAYS",
              "DIP_COOL", "DIP_ON", "INV_TAKE", "INV_STOP", "INV_DAYS", "INV_TAKE_K", "INV_TAKE_HI", "INV_SIG_N", "HOLIDAYS"):
        assert getattr(R, k) == getattr(O, k), k
    assert R.ROT == OS.ROT


def t_no_network_imports():
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import rules; "
            "bad=[m for m in ('requests','broker_kis','paper_trade','socket','http.client','urllib.request','ssl') if m in sys.modules]; "
            "print(bad); sys.exit(1 if bad else 0)")
    p = subprocess.run([sys.executable, "-I", "-c", code, str(HERE)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr


# ── 합성 입력 ──
def series(n, start, daily, tail=None):
    a = start * (1 + daily) ** np.arange(n)
    if tail:
        for i, x in enumerate(tail):
            a[n - len(tail) + i] = x
    return list(map(float, a))


def px_base(k_daily=0.001, q_last10=0.0, dol=0.0005, rot=(0.002, 0.0005, -0.001, -0.002)):
    n = 80
    q = series(n - 10, 10000, 0.0)
    q = q + [q[-1] * (1 + q_last10) ** (i + 1) for i in range(10)]
    px = {"069500": series(n, 30000, k_daily), "229200": q, "138230": series(n, 12000, dol)}
    for c, d in zip(R.ROT, rot):
        if c != "138230":
            px[c] = series(n, 10000, d)
    return px


def now_of(px, inv=5000.0):
    d = {c: a[-1] for c, a in px.items()}
    d["251340"] = inv
    return d


def both(state, day, px, breadth, used, total, cash, held, now, wk, reserve=0.0):
    a = R.step(copy.deepcopy(state), day, px, breadth, used, total, cash, held, now, wk, reserve)
    b = O.step(copy.deepcopy(state), day, px, breadth, used, total, cash, held, now, wk, reserve)
    assert a == b, "원본과 결과 다름"
    return a


DAY = "20261008"
TOTAL, CASH = 100_000_000.0, 100_000_000.0


def e01_engine_boundary():
    px = px_base()
    o, st, why = both({}, DAY, px, 40.0, 0.2, TOTAL, CASH, {}, now_of(px), True)
    assert o == [] and "끔(쓴 몫 20% 넘음)" in why[0]
    o, st, why = both({}, DAY, px, 50.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    assert o == [] and "시장 폭 50 이상" in why[0]


def e02_rotation_two():
    px = px_base(rot=(0.002, 0.0005, 0.001, -0.002))
    o, st, _ = both({}, DAY, px, 40.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    buys = {c for c, s, q, r in o if s == "buy"}
    assert buys == {"133690", "132030"}, o
    assert all(st["positions"][c]["kind"] == "돌리기" for c in buys)


def e03_rotation_one():
    px = px_base(dol=-0.0005, rot=(0.002, -0.0005, -0.001, -0.002))
    o, st, _ = both({}, DAY, px, 40.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    assert [c for c, s, q, r in o] == ["133690"]
    q = o[0][2]
    assert q == int(TOTAL * 0.5 * 0.97 // now_of(px)["133690"]), q          # 1개면 몫 0.5


def e04_rotation_zero_cash():
    px = px_base(dol=-0.0005, rot=(-0.002, -0.0005, -0.001, -0.002))
    o, st, why = both({}, DAY, px, 40.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    assert o == [] and any("현금(모두 −)" in w for w in why)


def e05_dollar_downtrend():
    px = px_base(k_daily=-0.002, dol=0.0015)
    o, st, why = both({}, DAY, px, 40.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    assert [(c, s) for c, s, q, r in o] == [("138230", "buy")] and st["positions"]["138230"]["kind"] == "달러"


def e06_inverse_priority_take_fixed():
    px = px_base(q_last10=0.0095, rot=(0.002, 0.0005, 0.001, -0.002))
    o, st, why = both({}, DAY, px, 40.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    assert [(c, s) for c, s, q, r in o] == [("251340", "buy")], o              # 엔진은 쉼(인버스 먼저)
    assert any("인버스 먼저" in w for w in why)
    assert st["positions"]["251340"]["take"] == round(R.inv_take(px["229200"]), 5) == 0.015   # 평평한 60일 → 바닥 1.5%


def e07_inverse_take_exit_no_reentry():
    px = px_base(q_last10=0.0095)
    state = {"positions": {"251340": {"kind": "인버스", "price": 5000.0, "day": "20261006", "days": 1, "take": 0.02}}, "cool": 0,
             "last_day": "20261007"}
    now = now_of(px, inv=5000 * 1.019)                                             # +1.9% < 산 날 고정 익절 2.0% → 안 팖
    o, st, _ = both(state, DAY, px, 40.0, 0.0, TOTAL, CASH, {"251340": 100}, now, True)
    assert o == [] and st["positions"]["251340"]["days"] == 2
    now = now_of(px, inv=5000 * 1.021)                                             # +2.1% ≥ 2.0% → 팖 · 신호 그대로여도 같은 날 다시 안 삼
    o, st, _ = both(state, DAY, px, 40.0, 0.0, TOTAL, CASH, {"251340": 100}, now, True)
    assert ("251340", "sell") in [(c, s) for c, s, q, r in o] and ("251340", "buy") not in [(c, s) for c, s, q, r in o]
    assert "251340" not in st["positions"]
    # 원본 그대로의 동작: 인버스를 판 그날은 '인버스 먼저'가 풀려 엔진(돌리기)이 같은 날 삼
    assert {c for c, s, q, r in o if s == "buy"} == {"133690", "138230"}, o


def e08_inverse_hold_days():
    px = px_base()
    state = {"positions": {"251340": {"kind": "인버스", "price": 5000.0, "day": "20260924", "days": 9, "take": 0.02}}, "cool": 0,
             "last_day": "20261007"}
    o, st, _ = both(state, DAY, px, 40.0, 0.0, TOTAL, CASH, {"251340": 100}, now_of(px, inv=5000.0), True)
    assert o[0][:2] == ("251340", "sell") and "10일 지남" in o[0][3]
    assert all(c != "251340" for c, s, q, r in o if s == "buy")


def e09_same_day_rerun():
    px = px_base(rot=(0.002, 0.0005, 0.001, -0.002))
    o1, st1, _ = both({}, DAY, px, 40.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    held = {c: q for c, s, q, r in o1}
    o2, st2, _ = both(st1, DAY, px, 40.0, 0.0, TOTAL, CASH / 2, held, now_of(px), True)
    assert o2 == [] and all(p["days"] == 0 for p in st2["positions"].values())   # 같은 날 다시 돌려도 날짜 안 늘고 다시 안 삼


def e10_cash_short():
    px = px_base(q_last10=0.0095)
    o, st, why = both({}, DAY, px, 40.0, 0.0, TOTAL, 1000.0, {}, now_of(px), True)
    assert o == [] and any("비운 돈이 없음" in w for w in why)


# ── 계약(원본에는 없는 입력 검증) ──
def snap(px, **over):
    dec = "2026-10-08T15:10:00+09:00"
    meta = {"as_of": "2026-10-08T15:10:00+09:00", "available_at": "2026-10-08T15:10:05+09:00", "provenance": "합성 시험"}
    dec = over.pop("decision_at", "2026-10-08T15:11:00+09:00")
    inp = {"px": {**meta, "value": {c: {"closes": a, "last_date": DAY} for c, a in px.items()}},
           "breadth": {**meta, "value": 40.0}, "used": {**meta, "value": 0.0},
           "total": {**meta, "value": TOTAL, "measure": "SYNTHETIC"}, "cash": {**meta, "value": CASH, "measure": "SYNTHETIC"},
           "held": {**meta, "value": {}, "measure": "SYNTHETIC"}, "now_price": {**meta, "value": now_of(px)},
           "is_week_end": {**meta, "value": True, "provenance": "외부 시장 달력(합성)"}}
    for k, v in over.items():
        inp[k] = v
    return {"decision_at": dec, "day": DAY, "inputs": inp}


def e11_future_input_rejected():
    px = px_base(rot=(0.002, 0.0005, 0.001, -0.002))
    ok = R.evaluate(snap(px), {})
    exp, _, _ = O.step({}, DAY, px, 40.0, 0.0, TOTAL, CASH, {}, now_of(px), True)
    assert ok["status"] == "OK" and [(i["code"], i["side"], i["qty"]) for i in ok["signal_intents"]] == [(c, s, q) for c, s, q, r in exp]
    assert all(i["kind"] == "SIGNAL_INTENT_NOT_ORDER_NOT_FILL" for i in ok["signal_intents"])
    assert ok["proposed_state_kind"] == "ASIS_PROPOSAL_NOT_FILL_CONFIRMED"
    s = snap(px)
    s["inputs"]["breadth"]["available_at"] = "2026-10-08T15:20:00+09:00"
    bad = R.evaluate(s, {})
    assert bad["status"] == "UNKNOWN_DATA" and bad["signal_intents"] == [] and bad["proposed_state"] is None
    assert any("breadth" in m and "미래" in m for m in bad["missing_inputs"])
    s = snap(px)
    s["inputs"]["px"]["value"]["229200"]["last_date"] = "20261007"
    assert R.evaluate(s, {})["status"] == "UNKNOWN_DATA"


def e12_missing_provenance_rejected():
    px = px_base()
    s = snap(px)
    s["inputs"]["used"]["provenance"] = ""
    del s["inputs"]["now_price"]
    s["inputs"]["cash"].pop("measure")
    r = R.evaluate(s, {})
    m = " | ".join(r["missing_inputs"])
    assert r["status"] == "UNKNOWN_DATA" and "used: provenance 없음" in m and "now_price: 없음" in m and "cash: measure 없음" in m
    s = snap(px, decision_at="2026-10-08T15:11:00")                               # 시간대 없음
    assert R.evaluate(s, {})["status"] == "UNKNOWN_DATA"


record("원본 보존(함수 몸통 AST · 상수)", t_source_preserved)
record("네트워크 · 증권사 모듈 import 없음", t_no_network_imports)
EX = [("E01 엔진 경계(used 0.2 · 폭 50)", e01_engine_boundary), ("E02 돌리기 양수 2개", e02_rotation_two),
      ("E03 돌리기 양수 1개(몫 0.5)", e03_rotation_one), ("E04 돌리기 양수 0개 → 현금", e04_rotation_zero_cash),
      ("E05 하락 추세 달러", e05_dollar_downtrend), ("E06 인버스 우선 · 익절 폭 산 날 고정", e06_inverse_priority_take_fixed),
      ("E07 인버스 익절(고정 폭) · 같은 날 재진입 없음", e07_inverse_take_exit_no_reentry), ("E08 인버스 10일 보유 청산", e08_inverse_hold_days),
      ("E09 같은 날 재실행(중복일)", e09_same_day_rerun), ("E10 현금 부족", e10_cash_short),
      ("E11 미래 입력 · 당일 값 아닌 가격 거부(계약)", e11_future_input_rejected), ("E12 출처 · 입력 · 측정 종류 누락 거부(계약)", e12_missing_provenance_rejected)]
assert len(EX) <= 12
for n, f in EX:
    record(n, f)
out = {"kind": "code_contract_test(합성 · 전략 성과 아님)", "examples": len(EX), "cases": RES,
       "passed": sum(r["result"] == "PASS" for r in RES), "total": len(RES)}
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if out["passed"] == out["total"] else 1)
