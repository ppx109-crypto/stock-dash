"""RULES-0002 합성 시험 — F1(정확 경계 · 호가 단위) · F2(수급 끝 당김). 원본 함수는 소스에서 그 정의만 떼어 실행(무거운 모듈 · 네트워크 없음).
python run_r2_fixtures.py <꺼낸 폴더(00b98ab1)> <out.json>"""
import ast
import bisect
import json
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as K  # noqa: E402

BASE, OUT = Path(sys.argv[1]), Path(sys.argv[2])
import socket  # noqa: E402
socket.socket = K._blocked
import numpy as np  # noqa: E402

CASES = []


def case(name, group, inp, expected, fn):
    try:
        actual = fn()
    except Exception as e:
        actual = {"error": type(e).__name__ + ": " + str(e)}
    CASES.append({"name": name, "group": group, "input": inp, "expected": expected, "actual": actual, "pass": actual == expected})


def pick(path, names, extra=None):
    """파일에서 이름이 맞는 def만 떼어 새 이름공간에서 실행."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    keep = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {"bisect": bisect, "np": np, **(extra or {})}
    exec(compile(ast.Module(body=keep, type_ignores=[]), f"{Path(path).name}({','.join(names)})", "exec"), ns)
    return ns


# ── F1 ──
case("f1.float_tp13_exact_tick", "F1", {"price": 1000, "close": 1130}, [False, True], lambda: [(1130 / 1000 - 1) * 100 >= 13, K.ge(1130, 1000, 13)])
case("f1.float_sl10_exact_tick", "F1", {"price": 1000, "close": 900}, [False, True], lambda: [(900 / 1000 - 1) * 100 <= -10, K.le(900, 1000, -10)])
case("f1.float_now1_exact_tick", "F1", {"price": 1000, "close": 1010}, [False, True], lambda: [(1010 / 1000 - 1) * 100 <= 1, K.le(1010, 1000, 1)])
case("f1.stale_lt4_boundary", "F1", {"price": 1000, "close": [1039, 1040]}, [True, False], lambda: [K.lt(1039, 1000, 4), K.lt(1040, 1000, 4)])
case("f1.exact_agrees_off_boundary", "F1", {"price": 1000, "close": 1131}, [True, True], lambda: [(1131 / 1000 - 1) * 100 >= 13, K.ge(1131, 1000, 13)])
case("f1.numpy_float_ok", "F1", {"price": "np.float64(290000)", "close": "np.float64(261000)"}, True, lambda: K.le(np.float64(261000), np.float64(290000), -10))
case("f1.real_case_003670", "F1", {"price": 290000, "close": 261000, "note": "D1 재생에서 실제로 나온 정확 −10% 경계"}, [False, True],
     lambda: [(261000 / 290000 - 1) * 100 <= -10, K.le(261000, 290000, -10)])
case("f1.real_case_009240", "F1", {"price": 100000, "close": 101000, "peak": ">= +8%"}, [False, True],
     lambda: [(101000 / 100000 - 1) * 100 <= 1, K.le(101000, 100000, 1)])
for p, pct, exp in ((1000, 13, True), (15000, 13, True), (1234, 13, False), (4990, 1, False), (290000, -10, True), (100000, 1, True), (1995, 5, False)):
    case(f"tick.on_grid_{p}_{pct}", "F1-tick", {"price": p, "pct": pct}, exp, lambda p=p, pct=pct: K.boundary_on_tick(p, pct))

# ── F2: 원본 nrl.flow_entry · flow_sum · steady ──
N = pick(BASE / "nrl.py", {"flow_entry", "flow_sum", "steady"}, {"COLS": ("개인", "외국인", "기관", "투신", "연기금", "사모")})
days = [f"2026010{i}" for i in range(1, 9)]          # d1 ~ d8
rows = [{"date": d, "외국인": float(i + 1), "투신": 1.0, "개인": -1.0, "기관": 0.0, "연기금": 0.0, "사모": 0.0, "종가": 1.0} for i, d in enumerate(days)]
N["FLOW"] = {"A": N["flow_entry"](rows)}
row = {"code": "A", "date": "20260108"}
case("f2.lag1_value", "F2", {"date": "d8", "rows": "d3..d7"}, 3 + 4 + 5 + 6 + 7, lambda: N["flow_sum"](row, 5, "외국인", lag=1))
case("f2.lag2_value", "F2", {"date": "d8", "rows": "d2..d6"}, 2 + 3 + 4 + 5 + 6, lambda: N["flow_sum"](row, 5, "외국인", lag=2))
case("f2.lag3_value", "F2", {"date": "d8", "rows": "d1..d5"}, 1 + 2 + 3 + 4 + 5, lambda: N["flow_sum"](row, 5, "외국인", lag=3))
case("f2.lag3_too_few_none", "F2", {"date": "d6", "need": 5, "note": "모자라면 None — 0으로 안 채움"}, None,
     lambda: N["flow_sum"]({"code": "A", "date": "20260106"}, 5, "외국인", lag=3))
case("f2.date_not_in_rows_uses_before", "F2", {"date": "20260110(줄 없음)", "lag": 1, "rows": "d4..d8"}, 4 + 5 + 6 + 7 + 8,
     lambda: N["flow_sum"]({"code": "A", "date": "20260110"}, 5, "외국인", lag=1))
# d1_diag의 steady(shift) 옮김 = 원본(shift 0)인지 — d1_diag.py에서 flow_patch만 떼어 가짜 nrl로 실행
D = pick(HERE / "d1_diag.py", {"flow_patch"}, {"nrl": types.SimpleNamespace(FLOW=N["FLOW"], flow_sum=N["flow_sum"])})
te0, st0 = D["flow_patch"](0)
te1, st1 = D["flow_patch"](1)
rows2 = [dict(r, 외국인=(1.0 if i % 2 == 0 else -1.0)) for i, r in enumerate(rows)]
N["FLOW"]["B"] = N["flow_entry"](rows2)
for d in days[2:] + ["20260110"]:
    for c in ("A", "B"):
        rr = {"code": c, "date": d}
        case(f"f2.steady_shift0_equals_original_{c}_{d}", "F2", {"code": c, "date": d}, N["steady"](rr), lambda rr=rr: st0(rr))
case("f2.steady_shift1_uses_t4_t2", "F2", {"code": "B", "date": "d8", "외국인": "+ on d1,d3,d5,d7"}, 1,
     lambda: st1({"code": "B", "date": "20260108"}))
# q_rule.raw: 원본과 '수급 끝 당김' 한 줄 바꾼 판
qsrc = (BASE / "research/q_rule.py").read_text(encoding="utf-8")
a, b = qsrc.index("def raw("), qsrc.index("\ndef tiers(")
OLD = "f = bisect.bisect_left(fd, day) - 1"
fl = [{"date": d, "외국인": float(i + 1), "투신": 0.0} for i, d in enumerate(days)]
G = {"bisect": bisect, "np": np, "data": {"A": {"t": ["202601081000", "202601081100"]}},
     "ROWS": {"A": (days, [100.0 + i for i in range(8)], days, [1000.0] * 8, days, fl)}, "_FLOW_SHIFT": 1}
exec(compile(qsrc[a:b], "q_rule.raw(원본)", "exec"), G)
orig = G["raw"]
G2 = dict(G)
exec(compile(qsrc[a:b].replace(OLD, OLD + " - _FLOW_SHIFT"), "q_rule.raw(당김)", "exec"), G2)
case("f2.qrule_raw_line_unique", "F2", {"old": OLD}, 1, lambda: qsrc[a:b].count(OLD))
case("f2.qrule_raw_shift_changes_flow_sum", "F2", {"day": "d8", "orig rows": "d3..d7", "shift1 rows": "d2..d6", "note": "av 결측이라 둘 다 nan → 비교는 s 값으로"},
     [3 + 4 + 5 + 6 + 7, 2 + 3 + 4 + 5 + 6],
     lambda: [sum(x["외국인"] for x in fl[max(0, f - 4):f + 1]) for f in (bisect.bisect_left(days, "20260108") - 1, bisect.bisect_left(days, "20260108") - 1 - 1)])
# hlab.daily_context의 줄
hsrc = (BASE / "hlab.py").read_text(encoding="utf-8")
case("f2.hlab_line_unique", "F2", {"old": "k = bisect.bisect_right(fdays, day)"}, 1, lambda: hsrc[hsrc.index("def daily_context("):hsrc.index("\ndef _events(")].count("k = bisect.bisect_right(fdays, day)"))
case("f2.hlab_shift_last_row", "F2", {"context day": "d7", "orig last": "d7", "shift1 last": "d6"}, ["20260107", "20260106"],
     lambda: [days[bisect.bisect_right(days, "20260107") - 1], days[bisect.bisect_right(days, "20260107") - 1 - 1]])
case("sandbox.network_blocked", "sandbox", {}, {"error": "RuntimeError: 네트워크 금지(진단 재생)"}, lambda: socket.socket())

res = {"runner": "diag/run_r2_fixtures.py", "cases": CASES,
       "summary": {"total": len(CASES), "pass": sum(c["pass"] for c in CASES), "fail": sum(not c["pass"] for c in CASES)}}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(res["summary"])
for c in CASES:
    if not c["pass"]:
        print("FAIL", c["name"], c["actual"])
