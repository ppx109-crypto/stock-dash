"""RULES-0001 합성 fixture 실행기 — 네트워크를 막고(socket 차단) contract.py 순수 함수만 시험 → test-result.json.
python run_fixtures.py [out.json]"""
import json
import socket
import sys
from pathlib import Path

def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지(합성 fixture)")
socket.socket = _blocked                      # 부작용 차단: 어떤 연결도 못 열게
socket.create_connection = _blocked

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C  # noqa: E402

CASES = []


def case(name, group, inp, expected, fn, cmp=None):
    try:
        actual = fn()
        err = None
    except Exception as e:  # 기대한 오류도 결과로 남김
        actual, err = {"error": type(e).__name__ + ": " + str(e)}, True
    if cmp:
        ok = cmp(actual, expected)
    else:
        ok = actual == expected
    CASES.append({"name": name, "group": group, "input": inp, "expected": expected, "actual": actual, "pass": bool(ok)})


approx = lambda a, b, t=1e-9: (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= t)

# 1. 자료 사용 가능 시각 · 정정 버전
V = [{"value": 100.0, "available_at": "2026-10-02T22:28:00", "version": 1},       # 저녁 수집(넥스트레이드 섞임)
     {"value": 97.0, "available_at": "2026-10-06T08:36:00", "version": 2}]         # 아침 교정
case("avail.before_any", "availability", {"versions": V, "decision_at": "2026-10-02T15:20:00"}, [None, None],
     lambda: list(C.usable_value(V, "2026-10-02T15:20:00")))
case("avail.evening_provisional", "availability", {"versions": V, "decision_at": "2026-10-05T15:20:00"}, [100.0, 1],
     lambda: list(C.usable_value(V, "2026-10-05T15:20:00")))
case("avail.after_correction_no_overwrite", "availability", {"versions": V, "decision_at": "2026-10-06T15:20:00"}, [97.0, 2],
     lambda: list(C.usable_value(V, "2026-10-06T15:20:00")))
case("avail.equal_time_inclusive", "availability", {"versions": V, "decision_at": "2026-10-06T08:36:00"}, [97.0, 2],
     lambda: list(C.usable_value(V, "2026-10-06T08:36:00")))
# 미래봉
case("bar.open_bar_rejected", "future_bar", {"bar_close": "2026-10-07T10:45:00", "observed_at": "2026-10-07T10:44:59"}, False,
     lambda: C.bar_usable("2026-10-07T10:45:00", "2026-10-07T10:44:59"))
case("bar.closed_bar_ok", "future_bar", {"bar_close": "2026-10-07T10:45:00", "observed_at": "2026-10-07T10:48:00"}, True,
     lambda: C.bar_usable("2026-10-07T10:45:00", "2026-10-07T10:48:00"))
case("fill.past_open_forbidden", "future_bar", {"submitted": "2026-10-07T11:03:00", "price_time": "2026-10-07T11:00:00"}, False,
     lambda: C.fill_price_allowed("2026-10-07T11:03:00", "2026-10-07T11:00:00"))
case("fill.after_submit_ok", "future_bar", {"submitted": "2026-10-07T11:03:00", "price_time": "2026-10-07T11:03:05"}, True,
     lambda: C.fill_price_allowed("2026-10-07T11:03:00", "2026-10-07T11:03:05"))
# DART 날짜만
HOL = ("2026-10-05",)
case("dart.date_only_next_session_over_weekend_holiday", "dart", {"rcept_dt": "2026-10-02", "time": None, "holidays": HOL},
     "2026-10-06T09:00:00", lambda: C.dart_available_at("2026-10-02", None, HOL))
case("dart.with_time", "dart", {"rcept_dt": "2026-10-07", "time": "16:05:00"}, "2026-10-07T16:05:00",
     lambda: C.dart_available_at("2026-10-07", "16:05:00"))
case("dart.same_day_reaction_not_post_event", "dart",
     {"event_available_at": "2026-10-07T16:05:00", "reaction_window_start": "2026-10-07T09:00:00"}, False,
     lambda: C.reaction_window_valid("2026-10-07T16:05:00", "2026-10-07T09:00:00"))
case("dart.date_only_same_day_reaction_invalid", "dart",
     {"event_available_at": C.dart_available_at("2026-10-07"), "reaction_window_start": "2026-10-07T09:00:00"}, False,
     lambda: C.reaction_window_valid(C.dart_available_at("2026-10-07"), "2026-10-07T09:00:00"))

# 2. 주문 · 체결
case("order.accepted_but_unfilled", "fills", {"order": {"side": "buy", "qty": 100}, "fills": []},
     [0, 1_000_000.0, "unfilled", 100], lambda: (lambda r: [r[0], r[1], r[2]["status"], r[2]["unfilled"]])(
         C.apply_order(0, 1_000_000.0, {"side": "buy", "qty": 100}, [], 0.00015, 0.0)))
case("order.partial_fill", "fills", {"order": {"side": "buy", "qty": 100}, "fills": [{"qty": 40, "price": 1000.0}, {"qty": 20, "price": 1010.0}]},
     {"pos": 60, "status": "partial", "unfilled": 40},
     lambda: (lambda r: {"pos": r[0], "status": r[2]["status"], "unfilled": r[2]["unfilled"]})(
         C.apply_order(0, 1_000_000.0, {"side": "buy", "qty": 100}, [{"qty": 40, "price": 1000.0, "time": "t"}, {"qty": 20, "price": 1010.0, "time": "t"}], 0.00015, 0.0)))
case("order.sell_tax_only_on_sell", "fills", {"order": {"side": "sell", "qty": 10}, "fills": [{"qty": 10, "price": 1000.0}], "fee": 0.00015, "tax": 0.0015},
     {"cash": 10000 - 1.5 - 15.0}, lambda: {"cash": round(C.apply_order(10, 0.0, {"side": "sell", "qty": 10}, [{"qty": 10, "price": 1000.0, "time": "t"}], 0.00015, 0.0015)[1], 6)})
case("order.overfill_rejected", "fills", {"order": {"qty": 5}, "fills": [{"qty": 6}]}, {"error": "ValueError: 체결 수량이 주문 수량보다 큼"},
     lambda: C.apply_order(0, 1e6, {"side": "buy", "qty": 5}, [{"qty": 6, "price": 1.0, "time": "t"}], 0, 0))
case("order.oversell_rejected", "fills", {"position": 3, "sell": 4}, {"error": "ValueError: 가진 것보다 많이 팖"},
     lambda: C.apply_order(3, 0, {"side": "sell", "qty": 4}, [{"qty": 4, "price": 1.0, "time": "t"}], 0, 0))
# 같은 봉 익절 · 손절
case("bar.tp_and_sl_same_bar_conservative", "same_bar", {"bar": {"open": 100, "high": 114, "low": 94}, "entry": 100, "tp": 0.13, "sl": 0.05},
     {"exit": "SL", "ambiguous": True}, lambda: {k: v for k, v in C.same_bar_tp_sl({"open": 100, "high": 114, "low": 94}, 100, 0.13, 0.05).items() if k != "price"})
case("bar.gap_down_below_sl_fills_at_open", "same_bar", {"bar": {"open": 90, "high": 92, "low": 88}, "entry": 100, "sl": 0.05},
     90, lambda: C.same_bar_tp_sl({"open": 90, "high": 92, "low": 88}, 100, 0.13, 0.05)["price"])
case("bar.tp_only", "same_bar", {"bar": {"open": 101, "high": 114, "low": 99}}, "TP",
     lambda: C.same_bar_tp_sl({"open": 101, "high": 114, "low": 99}, 100, 0.13, 0.05)["exit"])
# 칸 · 수량
case("slots.partial_assign", "slots", {"requested": 4, "free": 3}, 3, lambda: C.allocate_slots(4, 3))
case("slots.none_free", "slots", {"requested": 2, "free": 0}, 0, lambda: C.allocate_slots(2, 0))
case("qty.below_one_share", "slots", {"money": 999.0, "price": 1000.0}, 0, lambda: C.qty_for(999.0, 1000.0))
case("qty.floor", "slots", {"money": 2_500.0, "price": 1000.0}, 2, lambda: C.qty_for(2_500.0, 1000.0))
case("dedup.20_trading_days", "slots", {"events": [["A", "자사주", 0], ["A", "자사주", 19], ["A", "자사주", 20], ["A", "무상", 5]], "window": 20},
     [["A", "자사주", 0], ["A", "무상", 5], ["A", "자사주", 20]],
     lambda: [list(e) for e in C.dedup_events([("A", "자사주", 0), ("A", "자사주", 19), ("A", "자사주", 20), ("A", "무상", 5)], 20)])

# 3. NAV · 현금흐름 · 날짜 경계
case("nav.no_double_count_settlement", "nav", {"cash": 1000.0, "pos": {"X": 10}, "px": {"X": 50.0}, "receivable": 300.0, "cash_includes_settlement": True},
     1500.0, lambda: C.nav(1000.0, {"X": 10}, {"X": 50.0}, 300.0, 0.0, True))
case("nav.add_settlement_when_not_in_cash", "nav", {"cash": 1000.0, "receivable": 300.0, "payable": 100.0, "cash_includes_settlement": False},
     1700.0, lambda: C.nav(1000.0, {"X": 10}, {"X": 50.0}, 300.0, 100.0, False))
case("twr.no_flow", "nav", {"segments": [[100.0, 90.0]]}, -0.10, lambda: C.daily_twr(100.0, [(100.0, 90.0)]), lambda a, b: approx(a, b))
case("twr.deposit_not_counted_as_gain", "nav", {"prev": 100.0, "deposit_midday": 50.0, "segments": [[100.0, 95.0], [145.0, 145.0]]},
     -0.05, lambda: C.daily_twr(100.0, [(100.0, 95.0), (145.0, 145.0)]), lambda a, b: approx(a, b))
case("twr.withdrawal_not_counted_as_loss", "nav", {"segments": [[100.0, 100.0], [40.0, 40.0]], "withdraw": 60.0},
     0.0, lambda: C.daily_twr(100.0, [(100.0, 100.0), (40.0, 40.0)]), lambda a, b: approx(a, b))
case("twr.zero_start_rejected", "nav", {"segments": [[0.0, 10.0]]}, {"error": "ValueError: 구간 시작 NAV ≤ 0"},
     lambda: C.daily_twr(0.0, [(0.0, 10.0)]))
R = [("2026-05-29", 0.10), ("2026-06-01", -0.10), ("2026-06-30", -0.10), ("2026-07-01", 0.05)]
case("month.calendar_boundary", "nav", {"days": R}, {"2026-05": [0.10, True], "2026-06": [-0.19, False], "2026-07": [0.05, False]},
     lambda: {m: [round(v[0], 10), v[1]] for m, v in C.calendar_months(R, month_first_trading_days=("2026-06-01", "2026-07-01")).items()})
case("mdd.mtm", "nav", {"r": [0.1, -0.2, 0.05, -0.1]}, -0.244, lambda: round(C.mtm_mdd([0.1, -0.2, 0.05, -0.1]), 6))
case("gate.month_limit_blocks_new_risk", "nav", {"day": -0.02, "month": -0.151}, {"block_new_risk": True, "guarantee": False},
     lambda: C.loss_gate(-0.02, -0.151))
case("gate.exact_limit_inclusive", "nav", {"day": -0.15, "month": 0.0}, {"block_new_risk": True, "guarantee": False},
     lambda: C.loss_gate(-0.15, 0.0))
case("gate.no_block", "nav", {"day": -0.149, "month": -0.149}, {"block_new_risk": False, "guarantee": False},
     lambda: C.loss_gate(-0.149, -0.149))
case("attr.sum_matches", "nav", {"strategies": {"1d": 10.0, "15m": -3.0, "engine": 1.0}, "account": 8.0}, True,
     lambda: C.attribute({"1d": 10.0, "15m": -3.0, "engine": 1.0}, 8.0)["ok"])
case("attr.double_cost_detected", "nav", {"strategies": {"1d": 10.0, "15m": -3.0}, "account": 6.5, "note": "계좌 비용 0.5를 전략에서 안 뺌"}, False,
     lambda: C.attribute({"1d": 10.0, "15m": -3.0}, 6.5)["ok"])

# 4. 실측 schema(합성 레코드만)
try:
    import jsonschema
    SCH = json.loads((Path(__file__).resolve().parent.parent / "measurement.schema.json").read_text(encoding="utf-8"))
    def valid(doc):
        try:
            jsonschema.validate(doc, SCH)
            return True
        except jsonschema.ValidationError:
            return False
    SIG = {"pseudonymous_account_id": "acct-SYN-1", "strategy_id": "1d_new82", "rule_version": "R1D-ASIS@00b98ab1", "data_version": "close@provisional",
           "signal_id": "s1", "decision_at": "2026-10-07T15:20:00", "max_feature_available_at": "2026-10-07T15:20:00",
           "signal_quote_at": "2026-10-07T15:20:00", "code": "000001", "side": "buy", "requested_slots": 4, "assigned_slots": 3}
    DAY = {"date": "2026-10-07", "valuation_at": "2026-10-08T07:30:00", "price_source": "KRX_close_finalized", "cash": 1.0,
           "positions": [{"code": "000001", "qty": 1, "price": 1.0, "strategy_id": "1d_new82"}], "nav": 2.0, "external_cashflows": []}
    case("schema.valid_synthetic", "schema", {"signals": [SIG], "daily": [DAY]}, True, lambda: valid({"signals": [SIG], "daily": [DAY]}))
    bad = dict(SIG); bad.pop("max_feature_available_at")
    case("schema.missing_available_at_rejected", "schema", {"signals": ["SIG without max_feature_available_at"]}, False, lambda: valid({"signals": [bad]}))
    bad2 = dict(DAY, price_source="naver")
    case("schema.unknown_price_source_rejected", "schema", {"daily": ["price_source=naver"]}, False, lambda: valid({"daily": [bad2]}))
    bad3 = dict(SIG, strategy_id="f5")
    case("schema.unknown_strategy_rejected", "schema", {"signals": ["strategy_id=f5"]}, False, lambda: valid({"signals": [bad3]}))
except ImportError:
    CASES.append({"name": "schema.*", "group": "schema", "input": None, "expected": None, "actual": "미실행(jsonschema 없음)", "pass": False})

# 네트워크 차단 확인
case("sandbox.network_blocked", "sandbox", {}, {"error": "RuntimeError: 네트워크 금지(합성 fixture)"}, lambda: socket.socket())

out = sys.argv[1] if len(sys.argv) > 1 else "test-result.json"
res = {"runner": "fixtures/run_fixtures.py", "network": "blocked", "cases": CASES,
       "summary": {"total": len(CASES), "pass": sum(c["pass"] for c in CASES), "fail": sum(not c["pass"] for c in CASES)}}
Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(res["summary"])
for c in CASES:
    if not c["pass"]:
        print("FAIL", c["name"], c["actual"])
