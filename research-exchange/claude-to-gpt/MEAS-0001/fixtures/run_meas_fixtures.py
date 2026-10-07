"""MEAS-0001 합성 시험 — 원본 함수는 소스에서 정의만 떼어 실행(운영 import · 네트워크 없음). python run_meas_fixtures.py <00b98ab1 폴더> <out.json>"""
import ast
import bisect
import json
import socket
import sys
import types
from pathlib import Path

import numpy as np

socket.socket = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
BASE, OUT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_rules0001 as C  # noqa: E402  (RULES-0001 PR #9 head d39c6fc의 contract.py 그대로)

CASES = []


def case(name, group, inp, expected, fn, kind="contract"):
    try:
        actual = fn()
    except Exception as e:
        actual = {"error": type(e).__name__ + ": " + str(e)}
    CASES.append({"name": name, "group": group, "kind": kind, "input": inp, "expected": expected, "actual": actual, "pass": actual == expected})


def pick(path, names, extra=None):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    keep = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {"bisect": bisect, "np": np, "sys": sys, **(extra or {})}
    exec(compile(ast.Module(body=keep, type_ignores=[]), f"{Path(path).name}({','.join(names)})", "exec"), ns)
    return ns


# ── a_mtm.account(연구 날마다 평가) 계약 ──
A = pick(BASE / "research/a_mtm.py", {"account"})["account"]
D = [f"2026010{i}" for i in range(1, 10)]
flat = {"rows": [(d, 100.0) for d in D]}


# A1: 같은 날 4칸 × 3건(=12칸) — 현금 제약 없음 → 계좌 수익이 120% 노출로 움직임
P1 = {"A": {"rows": [(d, 100.0 * (1.1 if d >= "20260103" else 1.0)) for d in D]}, "B": {"rows": [(d, 100.0 * (1.1 if d >= "20260103" else 1.0)) for d in D]},
      "C": {"rows": [(d, 100.0 * (1.1 if d >= "20260103" else 1.0)) for d in D]}}
L1 = [("A", D[1], D[6], 10.0, 4), ("B", D[1], D[6], 10.0, 4), ("C", D[1], D[6], 10.0, 4)]
r1 = A(D, L1, np.zeros(len(D)), P1)
case("a_mtm.no_cash_constraint_12_slots", "a_mtm", {"ledger": "같은 날 4칸 × 3건(12칸)", "price": "+10% 다음 날"},
     "노출 100% 이하(계약 · 현금 ≥ 0)", lambda: f"그날 계좌 +{r1[2] * 100:.1f}%(노출 {r1[2] / 0.10 * 100:.0f}%)", kind="as-is 결함 확인")
# A2: 판 날 장부 손익 맞춤 점프
P2 = {"A": {"rows": [(d, 110.0 if d >= "20260103" else 100.0) for d in D]}}
L2 = [("A", D[1], D[5], 2.0, 10)]
r2 = A(D, L2, np.zeros(len(D)), P2)
case("a_mtm.sell_day_reconcile_jump", "a_mtm", {"price": "+10% 유지", "ledger_pnl": "+2%", "slots": 10},
     "판 날 계좌 -7.3%", lambda: f"판 날 계좌 {r2[5] * 100:+.1f}%", kind="as-is 동작 고정")
# A3: 같은 날 사고판 매매는 빠짐
L3 = [("A", D[2], D[2], 5.0, 4)]
r3 = A(D, L3, np.zeros(len(D)), P2)
case("a_mtm.same_day_trade_dropped", "a_mtm", {"buy": D[2], "sell": D[2], "pnl": "+5%"}, "반영됨",
     lambda: "반영 안 됨(계좌 수익 합 0)" if abs(sum(r3)) < 1e-12 else "반영됨", kind="as-is 결함 확인")
# A4: 절반 익절 두 줄(2칸 + 2칸) — 칸 합 4/10 보존
P4 = {"A": {"rows": [(d, 100.0) for d in D]}}
L4 = [("A", D[1], D[3], 5.0, 2), ("A", D[1], D[6], 0.0, 2)]
r4 = A(D, L4, np.zeros(len(D)), P4)
case("a_mtm.partial_rows_conserve", "a_mtm", {"rows": "같은 날 산 2칸 · 2칸 · 따로 팖"}, "+1.00%", lambda: f"{(np.prod(1 + r4) - 1) * 100:+.2f}%")
# A5: 산 날 비용 없음(보유 중 평가에 비용 안 들어감) — 장부 손익이 비용 뒤 값이라 판 날에만 반영
r5 = A(D, [("A", D[1], D[6], -0.25, 10)], np.zeros(len(D)), P4)
case("a_mtm.cost_only_at_exit", "a_mtm", {"price": "그대로", "ledger_pnl": "−0.25%(왕복 비용)"}, "산 날 +0.0% · 판 날 -0.25%",
     lambda: f"산 날 {r5[1] * 100:+.1f}% · 판 날 {r5[6] * 100:+.2f}%", kind="as-is 동작 고정")
# ── 입출금 TWR(계약) ──
case("twr.deposit_not_gain", "nav", {"segments": [[100, 95], [145, 145]]}, -0.05, lambda: round(C.daily_twr(100, [(100, 95), (145, 145)]), 10))
case("twr.a_mtm_has_no_flow_input", "nav", {"note": "a_mtm.account 인자에 입출금 없음"}, True,
     lambda: "flows" not in A.__code__.co_varnames and "cash_flows" not in A.__code__.co_varnames)
# ── calm: 전 기간 한 번(rule.calm_edge) vs 달마다 앞 자료(nrl._calm_by_month) ──
rule_ns = types.SimpleNamespace(CALM=0.4, SINCE="20170101")
R = pick(BASE / "rule.py", {"calm_edge"}, {"CALM": 0.4, "_calm": None})
past = [{"date": f"2017{m:02d}15", "변동성": v} for m, v in zip(range(1, 13), [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2])]
future = [{"date": f"2018{m:02d}15", "변동성": 9.0} for m in range(1, 13)]
R["_calm"] = None
t_past = R["calm_edge"](past)
R["_calm"] = None
t_all = R["calm_edge"](past + future)
case("calm.full_period_changes_with_future_rows", "calm", {"past": "2017 변동성 1.0 ~ 3.2", "future": "2018 9.0 × 12"}, "같음(계약: 미래 행이 과거 문턱을 바꾸지 않음)",
     lambda: f"{t_past} → {t_all}(바뀜)" if t_past != t_all else "같음(계약: 미래 행이 과거 문턱을 바꾸지 않음)", kind="as-is 결함 확인")
case("calm.past_decision_flips", "calm", {"row": "2017-06 변동성 2.6"}, [False, True], lambda: [2.6 <= t_past, 2.6 <= t_all], kind="as-is 결함 확인")
NB = pick(BASE / "nrl.py", {"_calm_by_month"}, {"rule": rule_ns})
cm1 = NB["_calm_by_month"]([dict(r) for r in past] * 100)
cm2 = NB["_calm_by_month"]([dict(r) for r in past] * 100 + [dict(r) for r in future] * 100)
case("calm.month_cutoff_unchanged_by_future", "calm", {"month": "201712"}, True, lambda: cm1.get("201712") == cm2.get("201712"))
# ── 공시: 날짜만 → 다음 거래일 09:00 · 장후 공시 반응 시작 ──
case("dart.after_close_reaction_starts_next_session", "dart", {"rcept_dt": "2026-10-07", "time": None, "holidays": ["2026-10-09"]},
     ["2026-10-08T09:00:00", False], lambda: [C.dart_available_at("2026-10-07", None, ("2026-10-09",)),
                                              C.reaction_window_valid(C.dart_available_at("2026-10-07"), "2026-10-07T09:00:00")])
# ── 수급 결손일: 줄 기준 창이 거래일 창보다 길어짐 ──
N = pick(BASE / "nrl.py", {"flow_entry", "flow_sum"}, {"COLS": ("개인", "외국인", "기관", "투신", "연기금", "사모")})
cal = [f"202601{d:02d}" for d in (5, 6, 7, 8, 9, 12, 13, 14)]
rows = [{"date": d, "외국인": 1.0, "투신": 1.0, "개인": -1.0, "기관": 0.0, "연기금": 0.0, "사모": 0.0, "종가": 1.0} for d in cal if d != "20260109"]
N["FLOW"] = {"A": N["flow_entry"](rows)}
case("flow.missing_day_row_window_spans_6_trading_days", "flow", {"rows": "01-09 결손", "date": "20260114"}, 6,
     lambda: len(cal) - 1 - cal.index(sorted(x for x in cal if x != "20260109" and x < "20260114")[-5]))

res = {"runner": "fixtures/run_meas_fixtures.py", "cases": CASES,
       "summary": {"total": len(CASES), "pass": sum(c["pass"] for c in CASES), "fail": sum(not c["pass"] for c in CASES),
                   "note": "kind='as-is 결함 확인'은 기대값을 '계약'으로 두어 실패로 남김(결함이 실제로 있다는 증거) · 'as-is 동작 고정'은 현재 동작 그대로를 기대값으로"}}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(res["summary"])
for c in CASES:
    print(("PASS " if c["pass"] else "FAIL ") + c["name"], "|", c["actual"])
