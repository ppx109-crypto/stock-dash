"""RULES-0001 as-is 확인 — 운영 판단 함수를 합성 입력으로만 부름(네트워크 차단 · 임시 폴더에서 실행 · 파일 쓰기 없음).
python run_asis.py <코드 기준점 폴더(00b98ab1 worktree)> <out.json>"""
import json
import os
import socket
import sys
import tempfile
from pathlib import Path


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지(합성 fixture)")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):                     # 키 · 계좌 환경변수가 있어도 쓰지 못하게
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)

BASE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(BASE))
os.chdir(tempfile.mkdtemp(prefix="rules0001-"))     # 상대 경로 파일(basket-live/ 등)이 저장소에 생기지 않게
import basket_live as B  # noqa: E402

CASES = []


def case(name, group, inp, expected, fn):
    try:
        actual = fn()
    except Exception as e:
        actual = {"error": type(e).__name__ + ": " + str(e)}
    CASES.append({"name": name, "group": group, "rule_id": "BASKET-C-ASIS", "input": inp, "expected": expected, "actual": actual, "pass": actual == expected})


# 합성 달력: 거래일 번호 = 날짜 문자열 'd000' ~ (days_since = 오늘 번호 − 산 날 번호)
TODAY = 30
num = lambda d: int(d[1:])
since = lambda d: TODAY - num(d)
T0, DAY = "d029", "d030"
INS = {"A", "B", "C", "D", "E", "F", "G"}
PX = {c: 1000.0 for c in INS}


def run(events, react, state=None, held=None, capital=5_000_000.0, avail=5_000_000.0, others=()):
    orders, st, why = B.step(state or {}, DAY, T0, since, events, react, INS, held or {}, PX, capital, avail, others=others)
    return {"orders": [[c, s, q] for c, s, q, _ in orders], "last": st.get("last", {}), "why_n": len(why)}


case("const.slots_hold_gap_th_top", "basket", {}, [5, 20, 20, -0.02, 200, ["자사주취득", "무상증자"]],
     lambda: [B.SLOTS, B.HOLD, B.GAP, B.TH, B.TOP, list(B.KINDS)])
case("events.kind_only_title_not_seen", "basket",
     {"events": {"A": [["d029", "자사주취득"]], "B": [["d029", "기타"]]}, "note": "입력에 제목 칸이 없음 → 정정 · 거래정지 안내도 갈래만 맞으면 사건"},
     [["A", "자사주취득"]], lambda: [list(x) for x in B.todays_events({"A": [("d029", "자사주취득")], "B": [("d029", "기타")]}, "d029", "d028")])
case("events.weekend_rollup_before_lt_d_le_t0", "basket", {"events": {"A": [["d027", "무상증자"], ["d028", "무상증자"]]}, "t0": "d029", "before": "d027"},
     [["A", "무상증자"]], lambda: [list(x) for x in B.todays_events({"A": [("d027", "무상증자"), ("d028", "무상증자")]}, "d029", "d027")])
case("buy.treasury_react_below_minus2", "basket", {"event": ["A", "자사주취득"], "react": -0.021}, [["A", "buy", 970]],
     lambda: run([("A", "자사주취득")], {"A": -0.021})["orders"])
case("skip.treasury_react_exactly_minus2_strict_lt", "basket", {"event": ["A", "자사주취득"], "react": -0.02}, [],
     lambda: run([("A", "자사주취득")], {"A": -0.02})["orders"])
case("buy.bonus_issue_any_reaction", "basket", {"event": ["A", "무상증자"], "react": 0.05}, [["A", "buy", 970]],
     lambda: run([("A", "무상증자")], {"A": 0.05})["orders"])
case("skip.no_reaction_value", "basket", {"event": ["A", "무상증자"], "react": "없음(200위 표본 < 40 등)"}, [],
     lambda: run([("A", "무상증자")], {})["orders"])
case("quirk.last_recorded_even_when_not_bought", "basket",
     {"event": ["A", "자사주취득"], "react": -0.01, "note": "반응이 −2%에 못 미쳐 안 삼 → 그래도 last에 기록"},
     {"orders": [], "last": {"A:자사주취득": "d029"}},
     lambda: {k: v for k, v in run([("A", "자사주취득")], {"A": -0.01}).items() if k != "why_n"})
case("dedup.blocks_within_20_after_unbought_event", "basket",
     {"state.last": {"A:자사주취득": "d015"}, "event": ["A", "자사주취득"], "react": -0.05, "gap": "14거래일"}, [],
     lambda: run([("A", "자사주취득")], {"A": -0.05}, state={"last": {"A:자사주취득": "d015"}})["orders"])
case("dedup.allows_at_20", "basket", {"state.last": {"A:자사주취득": "d009"}, "gap": "20거래일"}, [["A", "buy", 970]],
     lambda: run([("A", "자사주취득")], {"A": -0.05}, state={"last": {"A:자사주취득": "d009"}})["orders"])
case("exit.hold_20_trading_days_buy_day0", "basket", {"pos": {"A": {"day": "d010"}}, "days_since": 20}, [["A", "sell", 7]],
     lambda: run([], {}, state={"positions": {"A": {"day": "d010", "price": 1000.0, "kind": "무상증자"}}}, held={"A": 7})["orders"])
case("exit.not_before_20", "basket", {"pos": {"A": {"day": "d011"}}, "days_since": 19}, [],
     lambda: run([], {}, state={"positions": {"A": {"day": "d011", "price": 1000.0, "kind": "무상증자"}}}, held={"A": 7})["orders"])
case("state.position_dropped_if_ledger_empty", "basket", {"pos": {"A": {}}, "held": {}}, {"orders": [], "positions": {}},
     lambda: (lambda o, st, w: {"orders": o, "positions": st["positions"]})(*B.step({"positions": {"A": {"day": "d025", "price": 1.0, "kind": "무상증자"}}}, DAY, T0, since, [], {}, INS, {}, PX, 1.0, 1.0)))
FULL = {"positions": {c: {"day": "d025", "price": 1000.0, "kind": "무상증자"} for c in "BCDEF"}}
case("slots.five_full_no_buy", "basket", {"held": "5종목"}, [],
     lambda: run([("A", "무상증자")], {"A": 0.0}, state=FULL, held={c: 1 for c in "BCDEF"})["orders"])
case("others.held_by_other_bot_skip", "basket", {"others": ["A"]}, [],
     lambda: run([("A", "무상증자")], {"A": 0.0}, others={"A"})["orders"])
case("money.slot_is_capital_div5_times_0.97", "basket", {"capital": 5_000_000, "avail": 5_000_000, "price": 1000}, 970,
     lambda: run([("A", "무상증자")], {"A": 0.0})["orders"][0][2])
case("money.avail_limits_qty", "basket", {"capital": 5_000_000, "avail": 300_000, "note": "left = avail × 0.97"}, 291,
     lambda: run([("A", "무상증자")], {"A": 0.0}, avail=300_000.0)["orders"][0][2])
case("money.below_one_share", "basket", {"avail": 500}, [],
     lambda: run([("A", "무상증자")], {"A": 0.0}, avail=500.0)["orders"])


# 사건 분류(collect_events.kind_of · 제목 부분 일치 · 위에서부터 첫 일치)
import ast  # noqa: E402
import re  # noqa: E402
import types  # noqa: E402
_src = (BASE / "collect_events.py").read_text(encoding="utf-8")
_tree = ast.parse(_src)
_keep = [n for n in _tree.body if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "KINDS" for t in n.targets))
         or (isinstance(n, ast.FunctionDef) and n.name == "kind_of")]
E = types.SimpleNamespace()
_ns = {"re": re}
exec(compile(ast.Module(body=_keep, type_ignores=[]), "collect_events.py(KINDS+kind_of만)", "exec"), _ns)
E.kind_of = _ns["kind_of"]
for title, exp, note in (("유무상증자결정", "무상증자", "제목에 '유상증자' 연속 글자가 없어 무상증자로 잡힘 → 바구니 대상(유상 섞인 공시)"),
                         ("무상증자결정", "무상증자", "본 공시"),
                         ("[기재정정]무상증자결정", "무상증자", "정정 공시도 같은 갈래"),
                         ("주권매매거래정지(무상증자)", "무상증자", "거래정지 안내도 같은 갈래"),
                         ("주요사항보고서(자기주식취득결정)", "자사주취득", "본 공시"),
                         ("자기주식취득신탁계약체결결정", "자사주취득", "신탁 계약도 같은 갈래"),
                         ("[기재정정]주요사항보고서(자기주식취득결정)", "자사주취득", "정정 공시도 같은 갈래"),
                         ("자기주식처분결정", "자사주처분", "처분은 다른 갈래")):
    CASES.append({"name": "kind_of." + title, "group": "event_kind", "rule_id": "EVENT-KIND-ASIS", "input": {"title": title, "note": note},
                  "expected": exp, "actual": E.kind_of(title), "pass": E.kind_of(title) == exp})


# 15분봉 · 1시간봉 청산 · EMA(m15_live · hourly_a · 순수 함수)
import hourly_a as H  # noqa: E402
import m15_live as M  # noqa: E402


def ex(mod, kind, price, close, slots=4, first=4, bars=1, peak=None, prevmax=None):
    pos = {"kind": kind, "price": price, "칸": slots, "처음칸": first, "bars": bars, "peak": peak if peak is not None else max(price, close)}
    n, why = mod.exit_decision(pos, close, prevmax)
    return n


def c2(name, rule_id, inp, expected, fn, note=""):
    try:
        actual = fn()
    except Exception as e:
        actual = {"error": type(e).__name__ + ": " + str(e)}
    CASES.append({"name": name, "group": "intraday_exit", "rule_id": rule_id, "input": dict(inp, note=note) if note else inp,
                  "expected": expected, "actual": actual, "pass": actual == expected})


for mod, rid, hold in ((M, "M15-ASIS", 240), (H, "H1-ASIS(실주문 몫 0)", 60)):
    tag = "m15" if mod is M else "h1"
    c2(f"{tag}.trend_tp_13_clear", rid, {"price": 1000, "close": 1131}, 4, lambda mod=mod: ex(mod, "추세", 1000, 1131))
    c2(f"{tag}.trend_tp_13_exact_tick", rid, {"price": 1000, "close": 1130, "spec": "now >= 13"}, 4,
       lambda mod=mod: ex(mod, "추세", 1000, 1130), "부동소수점: (1130/1000−1)×100 = 12.99999999999999 → as-is는 안 팖(경계 결함)")
    c2(f"{tag}.trend_sl_5_exact", rid, {"price": 1000, "close": 950}, 4, lambda mod=mod: ex(mod, "추세", 1000, 950))
    c2(f"{tag}.trend_time_exit", rid, {"bars": hold}, 4, lambda mod=mod, hold=hold: ex(mod, "추세", 1000, 1000, bars=hold))
    c2(f"{tag}.trend_time_not_yet", rid, {"bars": hold - 1}, 0, lambda mod=mod, hold=hold: ex(mod, "추세", 1000, 1000, bars=hold - 1))
    c2(f"{tag}.trend_half_first_touch", rid, {"close": 1051, "prevmax": 1040, "slots": 4}, 2,
       lambda mod=mod: ex(mod, "추세", 1000, 1051, prevmax=1040))
    c2(f"{tag}.trend_half_not_again", rid, {"close": 1060, "prevmax": 1051}, 0, lambda mod=mod: ex(mod, "추세", 1000, 1060, prevmax=1051))
    c2(f"{tag}.trend_half_one_slot_min1", rid, {"slots": 1, "first": 1}, 1, lambda mod=mod: ex(mod, "추세", 1000, 1051, slots=1, first=1, prevmax=1000))
    c2(f"{tag}.trend_half_skipped_if_already_split", rid, {"slots": 2, "first": 4}, 0, lambda mod=mod: ex(mod, "추세", 1000, 1051, slots=2, first=4, prevmax=1000))
    c2(f"{tag}.trend_tp_and_sl_order_close_only", rid, {"close": 1200, "note": "종가로만 판단 → 같은 봉 익절·손절 동시 불가"}, 4,
       lambda mod=mod: ex(mod, "추세", 1000, 1200))
    c2(f"{tag}.aligned_sl_10_clear", rid, {"close": 899}, 4, lambda mod=mod: ex(mod, "정배열", 1000, 899))
    c2(f"{tag}.aligned_sl_10_exact_tick", rid, {"close": 900, "spec": "now <= -10"}, 4,
       lambda mod=mod: ex(mod, "정배열", 1000, 900), "부동소수점: −9.999999999999998 → as-is는 안 팖(경계 결함)")
    c2(f"{tag}.aligned_breakeven_peak8_now1_exact", rid, {"peak": 1080, "close": 1010, "spec": "peak >= 8 and now <= 1"}, 4,
       lambda mod=mod: ex(mod, "정배열", 1000, 1010, peak=1080), "부동소수점: now = 1.0000000000000009 → as-is는 안 팖(경계 결함)")
    c2(f"{tag}.aligned_breakeven_below1", rid, {"peak": 1081, "close": 1009}, 4, lambda mod=mod: ex(mod, "정배열", 1000, 1009, peak=1081))
    c2(f"{tag}.aligned_no_time_exit", rid, {"bars": 10000}, 0, lambda mod=mod: ex(mod, "정배열", 1000, 1000, bars=10000))
c2("m15.stale_boundary", "M15-ASIS", {"bars": 28, "ret": "3.9%", "breadth": 89.9}, True,
   lambda: M.stale({"bars": 28, "price": 1000}, 1039, 89.9))
c2("m15.stale_bars27", "M15-ASIS", {"bars": 27}, False, lambda: M.stale({"bars": 27, "price": 1000}, 1000, 50))
c2("m15.stale_breadth_missing_means_100", "M15-ASIS", {"breadth": None}, False, lambda: M.stale({"bars": 30, "price": 1000}, 1000, None))
c2("h1.stale_7bars", "H1-ASIS(실주문 몫 0)", {"bars": 7, "ret": 0, "breadth": 50}, True, lambda: H.stale({"bars": 7, "price": 1000}, 1000, 50))
c2("ema.seed_first_value_none_before_span", "EMA-ASIS", {"values": [10, 20, 30, 40], "span": 2, "k": "2/(span+1)"}, [None, None, 25.5556, 35.1852],
   lambda: [None if v is None else round(v, 4) for v in H.ema([10, 20, 30, 40], 2)], "씨앗 = 첫 값(SMA 씨앗이면 15 → 25 · 35) · 앞 span개 None")
c2("ema.aligned_strict_equal_false", "EMA-ASIS", {"closes": "같은 값 200개"}, False, lambda: H.aligned_series([100.0] * 200)[-1],
   "모든 EMA가 같으면 엄격한 > 라 정배열 아님")
c2("ema.aligned_rising", "EMA-ASIS", {"closes": "꾸준히 오르는 200개"}, True, lambda: H.aligned_series([100.0 * 1.01 ** i for i in range(200)])[-1])
c2("ema.not_enough_bars", "EMA-ASIS", {"closes": "180개"}, False, lambda: H.aligned_series([100.0 * 1.01 ** i for i in range(180)])[-1],
   "EMA180은 181번째 값부터 → 180개면 판단 못 함")


# 1일봉 크기 · 청산(daily_live 순수 함수)
import daily_live as DL  # noqa: E402
c2("d1.size_trend4", "D1-ASIS", {"추세문": True}, 4, lambda: DL.size_of({"추세문": True}))
c2("d1.size_3day4", "D1-ASIS", {"3일연속": True}, 4, lambda: DL.size_of({"3일연속": True}))
c2("d1.size_fresh3", "D1-ASIS", {"거래량비": 2.0, "정배열일수": 10}, 3, lambda: DL.size_of({"거래량비": 2.0, "정배열일수": 10}))
c2("d1.size_age0_quirk", "D1-ASIS", {"거래량비": 3.0, "정배열일수": 0, "spec(의도 추정)": "나이 0 ≤ 10 → 3칸"}, 3,
   lambda: DL.size_of({"거래량비": 3.0, "정배열일수": 0}), "as-is: (0 or 999) → 999 > 10 → 2칸(의도와 다름 · 결함 후보)")
c2("d1.size_default2", "D1-ASIS", {"거래량비": 1.99, "정배열일수": 1}, 2, lambda: DL.size_of({"거래량비": 1.99, "정배열일수": 1}))


def dx(kind, price, close, slots=4, first=4, days=1, max_close=None, peak=None, aligned=True):
    pos = {"kind": kind, "price": price, "칸": slots, "처음칸": first, "days": days,
           "max_close": max_close if max_close is not None else price, "peak": peak if peak is not None else price}
    return DL.exit_decision(pos, close, aligned)[0]


c2("d1.trend_tp_13_exact_tick", "D1-ASIS", {"price": 1000, "close": 1130, "spec": "now >= 13"}, 4, lambda: dx("추세", 1000, 1130),
   "부동소수점 12.99999999999999 → as-is 안 팖")
c2("d1.trend_tp_13_clear", "D1-ASIS", {"close": 1131}, 4, lambda: dx("추세", 1000, 1131))
c2("d1.trend_sl_5_exact", "D1-ASIS", {"close": 950}, 4, lambda: dx("추세", 1000, 950))
c2("d1.trend_time_10", "D1-ASIS", {"days": 10}, 4, lambda: dx("추세", 1000, 1000, days=10))
c2("d1.trend_half_min2_slots_minus1", "D1-ASIS", {"slots": 3, "first": 3}, 2, lambda: dx("추세", 1000, 1051, slots=3, first=3, max_close=1000))
c2("d1.trend_half_2slots_gives1", "D1-ASIS", {"slots": 2, "first": 2}, 1, lambda: dx("추세", 1000, 1051, slots=2, first=2, max_close=1000))
c2("d1.trend_half_1slot_none", "D1-ASIS", {"slots": 1, "first": 1}, 0, lambda: dx("추세", 1000, 1051, slots=1, first=1, max_close=1000))
c2("d1.aligned_sl_10_exact_tick", "D1-ASIS", {"close": 900, "spec": "now <= -10"}, 4, lambda: dx("정배열", 1000, 900),
   "부동소수점 −9.999999999999998 → as-is 안 팖(다만 정배열 깨짐으로 팔릴 수는 있음)")
c2("d1.aligned_peak_includes_today", "D1-ASIS", {"peak(어제까지)": 1000, "close": 1005, "note": "오늘 값 포함 고점"}, 0,
   lambda: dx("정배열", 1000, 1005, peak=1000))
c2("d1.aligned_breakeven_exact_1", "D1-ASIS", {"peak": 1080, "close": 1010, "spec": "now <= 1"}, 4, lambda: dx("정배열", 1000, 1010, peak=1080),
   "부동소수점 1.0000000000000009 → as-is 안 팖")
c2("d1.aligned_broken_sells", "D1-ASIS", {"aligned_now": False}, 4, lambda: dx("정배열", 1000, 1000, aligned=False))
c2("d1.aligned_unknown_none_holds", "D1-ASIS", {"aligned_now": None, "note": "함수 자체는 None이면 안 팖 — 부르는 쪽이 None을 False로 바꾸는지는 RULES-LOCK 참고"}, 0,
   lambda: dx("정배열", 1000, 1000, aligned=None))

for c in CASES:
    inp = c.get("input") or {}
    if not c["pass"] and isinstance(inp, dict) and any(k.startswith("spec") for k in inp):
        c["finding"] = "as-is 결함 후보(규칙 글과 코드 출력이 다름)" if "의도" not in " ".join(inp) else "의도 미확인(글자 그대로 읽은 규칙과 다름)"
res = {"runner": "fixtures/run_asis.py", "code_base": str(BASE.name), "network": "blocked", "cases": CASES,
       "summary": {"total": len(CASES), "pass": sum(c["pass"] for c in CASES), "fail": sum(not c["pass"] for c in CASES)}}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(res["summary"])
for c in CASES:
    if not c["pass"]:
        print("FAIL", c["name"], c["actual"])
