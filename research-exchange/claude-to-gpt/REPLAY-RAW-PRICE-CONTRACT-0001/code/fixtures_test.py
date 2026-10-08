"""REPLAY-RAW-PRICE-CONTRACT-0001 · 합성 fixture 10건(외부 자료 없음 · 네트워크 막음).
python3 -E -P fixtures_test.py <출력.json>
각 사례는 기대 판정을 미리 적고, 어댑터 결과와 손으로 쓴 식(두 번째 경로)을 함께 견줌."""
import json, socket, sys
from pathlib import Path
socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import raw_replay as R
OUT = sys.argv[1]
RATE = 0.001
rate = lambda side, code, day, n: RATE
D = ["20260105", "20260106", "20260107", "20260108"]
res = {}


def ok_pair(raw, adj=None, eff=()):
    return R.check_raw_pair(raw, adj if adj is not None else dict(raw), eff)


def case(name, expect, got, detail):
    res[name] = {"expect": expect, "got": got, "pass": expect == got, **detail}


# 1. 기업행동 없음: 원 = 수정
raw = {"A": ok_pair({d: 50000.0 for d in D})}
f = [{"fill_id": "f1", "sleeve": "D1", "date": D[0], "code": "A", "side": "buy", "intent": {"notional": 1_000_000}},
     {"fill_id": "f2", "sleeve": "D1", "date": D[2], "code": "A", "side": "sell", "intent": {"fraction": 1}}]
r = R.replay(f, raw, [], rate, 2_000_000, D)
hand_cash = 2_000_000 - 20 * 50000 * (1 + RATE) + 20 * 50000 * (1 - RATE)
case("1_기업행동_없음", ["OK", True, True], [raw["A"][D[0]]["status"], r["identity"]["cash_gap"] < 1e-6 and abs(r["cash"] - hand_cash) < 1e-6, r["identity"]["qty_match"]],
     {"hand_cash_eq_adapter": abs(r["cash"] - hand_cash) < 1e-6})
# 2. 액면분할 1 → 5(효력일 D[2]): 과거 수정주가 off-tick · 효력일 수량 ×5
rawc = {D[0]: 103500.0, D[1]: 104000.0, D[2]: 20900.0, D[3]: 21000.0}
adjc = {D[0]: 103500.0 / 5, D[1]: 104000.0 / 5, D[2]: 20900.0, D[3]: 21000.0}
ca = R.resolve_ca([{"rcept_no": "R1", "code": "A", "kind": "split", "ratio": 5, "effective_date": D[2]}])
pair = R.check_raw_pair(rawc, adjc, [D[2]])
f = [{"fill_id": "f1", "sleeve": "D1", "date": D[0], "code": "A", "side": "buy", "intent": {"notional": 1_000_000}}]
r = R.replay(f, {"A": pair}, ca, rate, 2_000_000, D)
qa = [x for x in r["rows"] if x["type"] == "CA_QTY"]
case("2_액면분할", ["adj_off_tick", 45, True], ["adj_off_tick" if not R.on_tick(adjc[D[0]]) else "adj_on_tick", r["qty"]["A"], r["identity"]["qty_match"]],
     {"buy_qty_raw": 9, "ca_qty_rows": len(qa), "raw_on_tick": R.on_tick(rawc[D[0]])})
# 3. 감자 10 → 1: 25주 → 2주 + 단주 0.5주 현금(칸 있음) / 칸 없으면 UNKNOWN_CASH_IN_LIEU
rawc = {D[0]: 5000.0, D[1]: 5000.0, D[2]: 50000.0, D[3]: 50000.0}
pair = R.check_raw_pair(rawc, {D[0]: 50000.0, D[1]: 50000.0, D[2]: 50000.0, D[3]: 50000.0}, [D[2]])
f = [{"fill_id": "f1", "sleeve": "BASKET", "date": D[0], "code": "B", "side": "buy", "intent": {"qty_note": "", "notional": 125000}}]
ca_a = R.resolve_ca([{"rcept_no": "R2", "code": "B", "kind": "capital_reduction", "ratio": 0.1, "effective_date": D[2], "cash_in_lieu_per_share": 50000.0}])
ra = R.replay(f, {"B": pair}, ca_a, rate, 1_000_000, D)
ca_b = R.resolve_ca([{"rcept_no": "R3", "code": "B", "kind": "capital_reduction", "ratio": 0.1, "effective_date": D[2]}])
rb = R.replay(f, {"B": pair}, ca_b, rate, 1_000_000, D)
case("3_감자_병합", [2, 25000.0, True, True], [ra["qty"]["B"], round(ra["adj_cash"], 6), ra["identity"]["cash_gap"] < 1e-6,
                                            any(x[1] == "UNKNOWN_CASH_IN_LIEU" for v in rb["flags"].values() for x in v)],
     {"no_cash_field_qty": rb["qty"]["B"]})
# 4. 유상 · 무상: 칸 하나라도 없으면 UNKNOWN_CA_FIELDS · 수량 안 바꿈
c4 = R.resolve_ca([{"rcept_no": "R4", "code": "C", "kind": "bonus_issue", "ratio": 1.5, "effective_date": D[2]},
                   {"rcept_no": "R5", "code": "C2", "kind": "rights_issue", "ratio": 0.2, "record_date": D[1]}])
case("4_유무상_칸없음", ["UNKNOWN_CA_FIELDS", "UNKNOWN_CA_FIELDS"], [x["status"] for x in sorted(c4, key=lambda x: x["rcept_no"])],
     {"missing": [x["missing"] for x in sorted(c4, key=lambda x: x["rcept_no"])]})
# 5. 원/수정 선택이 같은 응답(기업행동 영향 구간) → UNKNOWN_SELECTION_UNSUPPORTED · 그날 체결 안 함
same = {D[0]: 20700.0, D[1]: 20800.0, D[2]: 20900.0, D[3]: 21000.0}
pair = R.check_raw_pair(same, dict(same), [D[2]])
r = R.replay([{"fill_id": "f1", "sleeve": "D1", "date": D[0], "code": "A", "side": "buy", "intent": {"notional": 500000}}],
             {"A": pair}, [], rate, 1_000_000, D)
case("5_선택_미지원", ["UNKNOWN_SELECTION_UNSUPPORTED", 0], [pair[D[0]]["status"], len([x for x in r["rows"] if x["type"] == "BUY"])], {})
# 6. 원주가가 호가 밖 → INVALID_OFFICIAL_RAW
pair = R.check_raw_pair({D[0]: 20710.0}, {D[0]: 20710.0}, [])
case("6_원주가_호가밖", ["INVALID_OFFICIAL_RAW"], [pair[D[0]]["status"]], {})
# 7. 정정공시: 최신 정정본 · 원 접수 사슬 보존
c7 = R.resolve_ca([{"rcept_no": "20260101000100", "code": "A", "kind": "split", "ratio": 2, "effective_date": D[2]},
                   {"rcept_no": "20260102000200", "original_rcept_no": "20260101000100", "code": "A", "kind": "split", "ratio": 5, "effective_date": D[2]}])
case("7_정정_사슬", [1, 5, ["20260101000100", "20260102000200"], False], [len(c7), c7[0]["ratio"], c7[0]["chain"], c7[0]["same_day_pit"]], {})
# 8. 비용 · 세금 raw notional · 현금 항등식(손으로 쓴 식과 어댑터)
raw = {"A": ok_pair({D[0]: 33350.0, D[1]: 34000.0, D[2]: 35000.0, D[3]: 35000.0})}
f = [{"fill_id": "b", "sleeve": "D1", "date": D[0], "code": "A", "side": "buy", "intent": {"notional": 700000}},
     {"fill_id": "s", "sleeve": "D1", "date": D[2], "code": "A", "side": "sell", "intent": {"fraction": 0.5}}]
r = R.replay(f, raw, [], rate, 1_000_000, D)
bq = 700000 // 33350
sq = bq // 2
hand = 1_000_000 - bq * 33350 * (1 + RATE) + sq * 35000 * (1 - RATE)
case("8_비용_항등식", [True, True, True], [abs(r["cash"] - hand) < 1e-6, r["identity"]["cash_gap"] < 1e-6, r["identity"]["fill_prices_on_tick"]],
     {"buy_qty": bq, "sell_qty": sq, "cost_total_eq": abs((r["totals"]["buy_c"] + r["totals"]["sell_c"]) - (bq * 33350 + sq * 35000) * RATE) < 1e-6})
# 9. 주문 가능 수량 초과 · 음수 차단
raw = {"A": ok_pair({d: 10000.0 for d in D})}
f = [{"fill_id": "b", "sleeve": "D1", "date": D[0], "code": "A", "side": "buy", "intent": {"notional": 5_000_000}},
     {"fill_id": "s", "sleeve": "D1", "date": D[1], "code": "A", "side": "sell", "intent": {"qty": 10_000}}]
r = R.replay(f, raw, [], rate, 1_000_000, D)
fl = [x[1] for v in r["flags"].values() for x in v]
case("9_한도_음수", [True, True, True, 0], ["BUY_REDUCED" in fl, "SELL_CAPPED" in fl, r["cash"] >= 0, r["qty"]["A"]], {})
# 10. 15분봉 입력 거부
r = R.replay([{"fill_id": "m", "sleeve": "M15", "date": "202601050930", "code": "A", "side": "buy", "intent": {"notional": 1}}], {}, [], rate, 1, D)
case("10_15분봉_거부", ["OUT_OF_SCOPE_15M"], [r["status"]], {})
res["pass"] = all(v["pass"] for k, v in res.items() if isinstance(v, dict))
Path(OUT).write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({k: (v["pass"] if isinstance(v, dict) else v) for k, v in res.items()}, ensure_ascii=False))
