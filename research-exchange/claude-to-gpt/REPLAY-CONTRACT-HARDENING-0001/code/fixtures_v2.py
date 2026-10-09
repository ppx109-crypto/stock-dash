"""REPLAY-CONTRACT-HARDENING-0001 · 합성 fixture(외부 자료 없음 · 네트워크 막음).
python3 -E -P fixtures_v2.py <call_budget 계획.json> <출력 폴더>
출력: call-budget.json · pit-version-tests.json · raw-pair-tests.json · mtm-gate-tests.json · intent-mapping-tests.json · ported-fixtures-v2.json
각 시험은 기대값을 먼저 적고 실제값 · pass를 함께 냅니다."""
import json
import socket
import sys
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "pr86"))
import call_budget as CB
import raw_replay_v2 as R
import raw_replay as R86

PLAN, OUTDIR = sys.argv[1], Path(sys.argv[2])
RATE = 0.001
rate = lambda side, code, day, n: RATE
D = ["20260105", "20260106", "20260107", "20260108", "20260109"]
EARLY = "2025-12-01T09:00:00+09:00"
EP = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
GROUPS = {k: {} for k in ("call-budget", "pit-version-tests", "raw-pair-tests", "mtm-gate-tests", "intent-mapping-tests", "ported-fixtures-v2")}


def case(group, name, expect, got, **detail):
    GROUPS[group][name] = {"expect": expect, "got": got, "pass": expect == got, **detail}


def resp(basis, code, rows, over=None, fetched="2026-10-09T09:00:00+09:00"):
    ds = sorted(rows)
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_DATE_1": ds[0], "FID_INPUT_DATE_2": ds[-1],
              "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "1" if basis == "RAW" else "0"}
    params.update(over or {})
    rq = {"endpoint": EP, "tr_id": "FHKST03010100", "params": params}
    rws = [{"stck_bsop_date": d, "stck_clpr": rows[d]} for d in ds]
    body = R.canon({"output2": rws}).encode()
    return {"request": rq, "basis": basis, "request_param_sha256": R.sha(R.canon(rq)), "cache_file_sha256": R.sha(body),
            "fetched_at_kst": fetched, "rows": rws}, body


def pair(code, rawc, adjc=None, ca_dates=(), raw_over=None, adj_over=None, tamper=None, fetched="2026-10-09T09:00:00+09:00"):
    rr, rb = resp("RAW", code, rawc, raw_over, fetched)
    ar, ab = resp("ADJUSTED", code, adjc if adjc is not None else dict(rawc), adj_over, fetched)
    cache = {"RAW": rb, "ADJUSTED": ab}
    if tamper == "request":
        rr["request_param_sha256"] = "0" * 64
    if tamper == "cache":
        cache["RAW"] = rb + b" "
    if tamper == "basis_label":
        rr["basis"] = "ADJUSTED"
    return R.check_raw_pair_v2(rr, ar, cache, list(ca_dates))


def okr(closes):
    return {d: {"close": float(c), "status": "OK"} for d, c in closes.items()}


def ca(rcept, code, kind, ratio, basis, avail=EARLY, root=None, **kw):
    r = {"rcept_no": rcept, "root_rcept_no": root or rcept, "code": code, "kind": kind, "ratio": ratio,
         "effective_date": kw.pop("effective_date", basis), "price_basis_date": basis, "listing_date": kw.pop("listing_date", basis),
         "available_at_kst": avail}
    r.update(kw)
    return r


def flags_of(r):
    return [x[1] for v in r["flags"].values() for x in v]


def mtm_at(r, d):
    return next(m for m in r["mtm"] if m["date"] == d)


# ═════ A. 호출 예산 ═════
plan = json.load(open(PLAN))
ex = CB.dart_exhaustive(33)
b = CB.Budget(CB.DART_CAP, retry=0)
b.reserve("exhaustive", ex)
case("call-budget", "N1_DART_7개_전수_265_상한초과", [7, 265, 232, "BLOCKED_CALL_BUDGET"],
     [len(CB.DART_DETAIL), ex, CB.dart_exhaustive(33, n_ep=6), b.log[-1]["decision"]],
     note="1 + 33 × (1 + 7) = 265 > 250(재시도 0으로 봐도 초과) · PR #86의 232는 상세를 6개로 셈")
ev = [("c01", "bonus_issue"), ("c01", "bonus_issue"), ("c02", "capital_reduction"), ("c03", "merger"), ("c04", "split")]
p2 = CB.dart_plan(33, events=ev)
case("call-budget", "N2_목록결과로_줄인_계획_상한안", ["ALLOW", 3, 1, 4, 38, 114],
     [p2["status"], p2["stage2"]["detail_calls"], p2["stage2"]["document_calls"], p2["stage2"]["base"], p2["base_total"], p2["worst_total"]],
     note="고유 (종목, endpoint) 3 + 분할 원문 1 · 기본 1 + 33 + 4 = 38 · 재시도 2 포함 worst 114 ≤ 250")
ev3 = [(f"c{i:02d}", k) for i in range(33) for k in ("bonus_issue", "capital_reduction", "merger")]
p3 = CB.dart_plan(33, events=ev3)
case("call-budget", "N3_재시도_worst_초과_호출전_차단", ["BLOCKED_CALL_BUDGET", 99, 297, 34, 133, True],
     [p3["status"], p3["stage2"]["base"], CB.worst(p3["stage2"]["base"]), p3["log"][-1]["used_before"], 1 + 33 + p3["stage2"]["base"],
      1 + 33 + p3["stage2"]["base"] <= CB.DART_CAP],
     note="기본 성공 호출 합 133은 상한 안이지만, 2단계 worst 297 > 남은 216 → 2단계 호출 0으로 멈춤", log=p3["log"])
p1 = CB.dart_plan(33)
case("call-budget", "E1_1단계_결과없으면_2단계_숫자_안정함", ["STAGE2_PENDING_LIST", False],
     [p1["status"], "stage2" in p1], stage2_max_base_after_stage1=p1.get("stage2_max_base_after_stage1"))
p_pages = CB.dart_plan(33, stage1_pages={f"c{i:02d}": (3 if i < 20 else 1) for i in range(33)})
case("call-budget", "E1b_목록_여러쪽이면_쪽수로_다시_검사", ["STAGE2_PENDING_LIST", 73],
     [p_pages["status"], p_pages["log"][1]["base"]], log=p_pages["log"])
case("call-budget", "E1c_KIS_인증_재시도_포함", [133, 399, "ALLOW"], [plan["kis"]["base"], plan["kis"]["worst"], plan["kis"]["decision"]])

# ═════ B · C. 정정 사슬 as-of · cutoff ═════
cut = lambda d: R.cutoff_of(d, "08:00")
orig = ca("20260102000100", "A", "split", 2, D[2], avail="2026-01-02T16:00:00+09:00")
corr = ca("20260108000050", "A", "split", 5, D[2], avail="2026-01-08T07:00:00+09:00", root="20260102000100")   # 접수번호 문자열은 원본보다 작게 만들지 않음 → 아래 N6c에서 따로
v_past = R.resolve_ca_asof([orig, corr], cut(D[2]))
v_now = R.resolve_ca_asof([orig, corr], cut(D[4]))
case("pit-version-tests", "N4_효력일_뒤_정정본은_과거_as_of에서_제외", [2, ["20260102000100"], 5, ["20260102000100", "20260108000050"]],
     [v_past[0]["ratio"], v_past[0]["chain_known"], v_now[0]["ratio"], v_now[0]["chain_known"]])
rawA = {"A": okr({D[0]: 40000, D[1]: 40000, D[2]: 20000, D[3]: 20000, D[4]: 20000})}
rr = R.replay([], rawA, [orig, corr], rate, 0, D, positions0={"A": 10})
case("pit-version-tests", "N4b_재생은_그때_버전으로_수량_뒤_정정은_충돌표시", [20, True, False, ["CA_VERSION_CONFLICT_AFTER_USE"]],
     [rr["qty"]["A"], mtm_at(rr, D[2])["nav_valid"], mtm_at(rr, D[3])["nav_valid"], mtm_at(rr, D[3])["reasons"]],
     note="미래 정정본(비율 5)을 효력일 D[2]에 소급하지 않음 · 공개된 D[3]부터 NAV 무효")
c5 = [R.pit_ok("2026-01-07T07:59:00+09:00", cut(D[2])), R.pit_ok("2026-01-07T08:01:00+09:00", cut(D[2])),
      R.pit_ok("2026-01-07", cut(D[2])), R.pit_ok("2026-01-07", cut(D[3])), R.pit_ok(None, cut(D[4])),
      R.pit_ok("2026-01-07T07:59:00", cut(D[2]))]
case("pit-version-tests", "N5_cutoff_전_후_날짜만_시각없음", [True, False, False, True, False, False], c5,
     order=["07:59 ≤ 08:00", "08:01 > 08:00", "날짜만 · 당일", "날짜만 · 다음 거래일", "시각 없음", "시간대 없는 시각"])
late = ca("L1", "A", "split", 2, D[2], avail="2026-01-07")
rl = R.replay([], rawA, [late], rate, 0, D, positions0={"A": 10})
case("pit-version-tests", "N5b_날짜만_공개된_기업행동은_다음날_늦게_적용_성과차단", [200000.0, 20, ["CA_APPLIED_LATE"], "PERFORMANCE_BLOCKED_INCOMPLETE_RAW"],
     [mtm_at(rl, D[2])["inv"], rl["qty"]["A"], mtm_at(rl, D[3])["reasons"], R.performance_gate(rl)["status"]],
     note="D[2] 평가 = 10주 × 20000(당일 사용 금지라 수량 그대로) · D[3]에 20주 · 그 사이 NAV는 틀렸으므로 차단")
broken = ca("C2", "A", "split", 5, D[2], root="C1")
noav = ca("C3", "A", "split", 5, D[2], avail=None)
tie = [ca("T1", "A", "split", 2, D[2]), ca("T2", "A", "split", 5, D[2], root="T1")]
case("pit-version-tests", "N6_원접수_단절_시각없음_동시각_두버전", [["UNKNOWN_CA_VERSION_PIT", "ROOT_MISSING"], ["UNKNOWN_CA_VERSION_PIT", "AVAILABLE_AT_MISSING"], ["UNKNOWN_CA_VERSION_PIT", "SAME_TIME_VERSIONS"]],
     [[x["status"], x["why"]] for x in (R.resolve_ca_asof([broken], cut(D[4]))[0], R.resolve_ca_asof([noav], cut(D[4]))[0], R.resolve_ca_asof(tie, cut(D[4]))[0])])
rb_ = R.replay([], rawA, [broken], rate, 0, D, positions0={"A": 10})
case("pit-version-tests", "N6b_단절_사슬은_수량_안바꾸고_NAV_무효", [10, False, "PERFORMANCE_BLOCKED_INCOMPLETE_RAW"],
     [rb_["qty"]["A"], mtm_at(rb_, D[2])["nav_valid"], R.performance_gate(rb_)["status"]])
o2 = ca("20260110000900", "A", "split", 2, D[2], avail="2026-01-02T16:00:00+09:00")
c2 = ca("20260101000100", "A", "split", 5, D[2], avail="2026-01-08T07:00:00+09:00", root="20260110000900")
case("pit-version-tests", "N6c_접수번호_문자열_순서로_최신_추정안함", [2, 5], [R.resolve_ca_asof([o2, c2], cut(D[2]))[0]["ratio"], R.resolve_ca_asof([o2, c2], cut(D[4]))[0]["ratio"]],
     note="정정본 접수번호가 문자열로 더 작아도 공개 시각 순으로 고름")


# 자르기 시험: 어느 날 뒤 자료(가격 · 의도 · 그 뒤 공개 버전)를 처음부터 안 읽어도 그 앞 결과가 한 칸도 안 달라야 함
def cut_world(k, raw, intents, recs):
    d_cut = D[k]
    rawk = {c: {d: v for d, v in m.items() if d <= d_cut} for c, m in raw.items()}
    ik = [f for f in intents if f["date"] <= d_cut]
    rk = [r for r in recs if R.parse_avail(r.get("available_at_kst"))[0] is None or R.parse_avail(r["available_at_kst"])[0] <= cut(d_cut)]
    return rawk, ik, rk


poison = ca("P2", "A", "split", 100, D[2], avail="2026-01-08T09:00:00+09:00", root="P1")
p_orig = ca("P1", "A", "split", 2, D[2], avail="2026-01-05T09:00:00+09:00")
rawAB = {"A": okr({D[0]: 40000, D[1]: 40000, D[2]: 20000, D[3]: 20000, D[4]: 20000}),
         "B": okr({D[0]: 10000, D[1]: 10050, D[2]: 10100, D[3]: 10150, D[4]: 10200})}
intents = [{"intent_id": "i1", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 400000},
           {"intent_id": "i2", "sleeve": "D1", "date": D[1], "code": "B", "kind": "buy_notional", "notional": 300000},
           {"intent_id": "i3", "sleeve": "D1", "date": D[3], "code": "A", "kind": "sell_fraction", "fraction": 0.5},
           {"intent_id": "i4", "sleeve": "BASKET", "date": D[4], "code": "B", "kind": "sell_qty", "qty": 10}]
full = R.replay(intents, rawAB, [p_orig, poison], rate, 1_000_000, D)
same = []
for k in range(len(D) - 1):
    rk, ik, ck = cut_world(k, rawAB, intents, [p_orig, poison])
    part = R.replay(ik, rk, ck, rate, 1_000_000, D[:k + 1])
    same.append(part["mtm"] == full["mtm"][:k + 1] and [x for x in part["rows"] if x["date"] is None or x["date"] <= D[k]] ==
                [x for x in full["rows"] if x["date"] is None or x["date"] <= D[k]] and
                {d: v for d, v in part["flags"].items()} == {d: v for d, v in full["flags"].items() if d <= D[k]})
case("pit-version-tests", "E2_자르기_시험_미래_독정정본", [[True, True, True, True], 10, True, ["CA_VERSION_CONFLICT_AFTER_USE"]],
     [same, next(x["dq"] for x in full["rows"] if x["type"] == "CA_QTY"), mtm_at(full, D[3])["nav_valid"], mtm_at(full, D[4])["reasons"]],
     note="비율 100짜리 정정본(D[3] 09:00 공개)은 D[3] 08:00 cutoff 뒤라 D[4]부터 보임 · 그 앞 수량(분할 2 → +10주) · 현금 · MTM · 표시는 자른 세계와 한 칸도 같음")
hol = ["20260105", "20260106", "20260108", "20260109"]
rawH = okr({"20260105": 40000, "20260106": 40000, "20260108": 20000, "20260109": 20000})
r_new = R.replay([{"intent_id": "b", "sleeve": "D1", "date": hol[0], "code": "A", "kind": "buy_notional", "notional": 400000}],
                 {"A": rawH}, [ca("H1", "A", "split", 2, "20260107")], rate, 1_000_000, hol)
r_old = R86.replay([{"fill_id": "b", "sleeve": "D1", "date": hol[0], "code": "A", "side": "buy", "intent": {"notional": 400000}}],
                   {"A": rawH}, R86.resolve_ca([{"rcept_no": "H1", "code": "A", "kind": "split", "ratio": 2, "effective_date": "20260107"}]), rate, 1_000_000, hol)
case("pit-version-tests", "E4_기준일이_휴장일이면_다음거래일_적용(PR86은_건너뜀)", [20, "20260108", 10, "건너뜀"],
     [r_new["qty"]["A"], next(x["date"] for x in r_new["rows"] if x["type"] == "CA_QTY"), r_old["qty"]["A"],
      "건너뜀" if not any(x["type"] == "CA_QTY" for x in r_old["rows"]) else "적용"],
     note="10주 보유 · 분할 ×2 기준일이 휴장일(01-07) · PR #86 raw_replay.py 107줄은 effective_date가 거래일 목록에 없어 영원히 적용 안 함")
bonus = ca("BN1", "A", "bonus_issue", 1.5, D[2], listing_date=D[4], record_date=D[3], effective_date=D[3])
rawBn = okr({D[0]: 30000, D[1]: 30000, D[2]: 20000, D[3]: 20000, D[4]: 20000})
rbn = R.replay([{"intent_id": "s", "sleeve": "D1", "date": D[3], "code": "A", "kind": "sell_qty", "qty": 15}], {"A": rawBn}, [bonus], rate, 0, D, positions0={"A": 10})
case("pit-version-tests", "E5_권리락일_수량_평가_상장전_매도잠금", [300000.0, True, 5, ["SELL_LOCKED_PENDING"]],
     [mtm_at(rbn, D[2])["inv"], mtm_at(rbn, D[2])["nav_valid"], rbn["qty"]["A"], [w for w in flags_of(rbn) if w.startswith("SELL")]],
     note="권리락일(D[2])부터 15주 × 원주가로 평가 · 상장일(D[4]) 전 늘어난 5주는 못 팔아 15주 매도 요청이 10주로")

# ═════ D. 원/수정 쌍 provenance ═════
base_raw = {D[0]: 103600, D[1]: 104000, D[2]: 20900, D[3]: 21000}
base_adj = {D[0]: 20720, D[1]: 20800, D[2]: 20900, D[3]: 21000}
good = pair("A", base_raw, base_adj, [D[2]])
case("raw-pair-tests", "D0_정상_쌍_OK", ["OK"] * 4, [good[d]["status"] for d in D[:4]])
pm = pair("A", base_raw, base_adj, [D[2]], adj_over={"FID_INPUT_DATE_1": "20251201"})
pm2 = pair("A", base_raw, base_adj, [D[2]], adj_over={"FID_COND_MRKT_DIV_CODE": "NX"})
case("raw-pair-tests", "N7_원수정_요청_칸_불일치", [["UNKNOWN_PROVENANCE", ["PARAM_MISMATCH"]], ["UNKNOWN_PROVENANCE", ["PARAM_MISMATCH"]]],
     [[pm[D[0]]["status"], pm[D[0]]["why"]], [pm2[D[0]]["status"], pm2[D[0]]["why"]]])
flip = pair("A", base_raw, base_adj, [D[2]], raw_over={"FID_ORG_ADJ_PRC": "0"})
lab = pair("A", base_raw, base_adj, [D[2]], tamper="basis_label")
ident = pair("A", base_raw, dict(base_raw), [D[2]])
case("raw-pair-tests", "N8_basis_반전_또는_같은_응답", ["UNKNOWN_PROVENANCE", "UNKNOWN_PROVENANCE", "UNKNOWN_SELECTION_UNSUPPORTED", "OK"],
     [flip[D[0]]["status"], lab[D[0]]["status"], ident[D[0]]["status"], ident[D[2]]["status"]],
     flip_why=flip[D[0]]["why"], label_why=lab[D[0]]["why"],
     note="원 요청에 '0' · basis 칸만 바뀜 → 출처 실패 · 아는 기업행동 앞인데 원 = 수정 → 선택 미지원(기업행동 뒤 날은 원 = 수정이 정상)")
th = [pair("A", base_raw, base_adj, [D[2]], tamper="request")[D[0]]["why"], pair("A", base_raw, base_adj, [D[2]], tamper="cache")[D[0]]["why"],
      pair("A", base_raw, base_adj, [D[2]], fetched="2026-10-09")[D[0]]["why"]]
case("raw-pair-tests", "E9_요청해시_캐시해시_조회시각", [["REQUEST_HASH:RAW"], ["CACHE_HASH:RAW"], ["FETCHED_AT:RAW", "FETCHED_AT:ADJUSTED"]], th)
unexpl = pair("A", base_raw, base_adj, [])
case("raw-pair-tests", "E11_설명못하는_원수정_차이", ["UNKNOWN_CA_COVERAGE", "OK"], [unexpl[D[0]]["status"], unexpl[D[2]]["status"]],
     note="기업행동 목록이 비었는데 D[0] · D[1] 원 ≠ 수정 → 목록 불완전")
cutw = pair("A", {D[0]: 103600, D[1]: 104000}, {D[0]: 103600, D[1]: 104000}, [], fetched="2026-01-06T20:00:00+09:00")
case("raw-pair-tests", "E10_쌍검사_자르기_일관", [["OK", "OK"], ["OK", "OK"], [103600.0, 104000.0]],
     [[good[d]["status"] for d in D[:2]], [cutw[d]["status"] for d in D[:2]], [good[d]["close"] for d in D[:2]]],
     note="D[1] 밤에 받은 세계(기업행동 전 · 원 = 수정 · 목록 없음)와 뒤에 받은 세계(차이 + 기업행동 앎)가 앞 날 원주가 · 상태를 같게 냄")
offt = pair("A", {D[0]: 20710}, {D[0]: 20710}, [])
case("raw-pair-tests", "E9b_on_tick은_원주가_증거아님_off_tick은_INVALID", ["INVALID_OFFICIAL_RAW", "UNKNOWN_SELECTION_UNSUPPORTED"],
     [offt[D[0]]["status"], pair("A", {D[0]: 20700}, {D[0]: 20700}, [D[2]])[D[0]]["status"]],
     note="20700은 50원 배수(on-tick)지만 기업행동 앞인데 원 = 수정이라 원주가로 인정 안 함")

# ═════ E. MTM · 성과 게이트 ═════
rawM = {"A": okr({D[0]: 50000, D[1]: 50000, D[3]: 50500, D[4]: 51000})}
rm = R.replay([{"intent_id": "b", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 500000}], rawM, [], rate, 1_000_000, D)
g = R.performance_gate(rm)
case("mtm-gate-tests", "N9_하루_누락_nav_valid_false_성과차단", [False, ["UNKNOWN_MTM_STALE"], "PERFORMANCE_BLOCKED_INCOMPLETE_RAW", False, 1],
     [mtm_at(rm, D[2])["nav_valid"], mtm_at(rm, D[2])["reasons"], g["status"], "nav" in g, g.get("invalid_days")],
     diagnostic_nav_D2=mtm_at(rm, D[2])["nav_diagnostic"])
r0 = R.replay([], {"Z": okr({D[1]: 10000, D[2]: 10000, D[3]: 10000, D[4]: 10000})}, [], rate, 0, D, positions0={"Z": 5})
case("mtm-gate-tests", "E6_0원_대체는_유효_NAV_아님", [0.0, False, ["MTM_NO_PRIOR_PRICE"], "PERFORMANCE_BLOCKED_INCOMPLETE_RAW"],
     [mtm_at(r0, D[0])["inv"], mtm_at(r0, D[0])["nav_valid"], mtm_at(r0, D[0])["reasons"], R.performance_gate(r0)["status"]])
rmi = R.replay([{"intent_id": "b", "sleeve": "D1", "date": D[2], "code": "A", "kind": "buy_notional", "notional": 500000}], rawM, [], rate, 1_000_000, D)
case("mtm-gate-tests", "E6b_원주가_없어_체결못한_의도도_NAV_무효", [False, ["UNFILLED_INTENT", "UNKNOWN_MISSING_RAW"], "PERFORMANCE_BLOCKED_INCOMPLETE_RAW"],
     [mtm_at(rmi, D[2])["nav_valid"], mtm_at(rmi, D[2])["reasons"], R.performance_gate(rmi)["status"]])
rawC = {"A": okr({d: 50000 + 100 * i for i, d in enumerate(D)})}
rc = R.replay([{"intent_id": "b", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 500000},
               {"intent_id": "s", "sleeve": "D1", "date": D[3], "code": "A", "kind": "sell_fraction", "fraction": 1}], rawC, [], rate, 1_000_000, D)
gc = R.performance_gate(rc)
case("mtm-gate-tests", "E7_완전한_자료면_게이트_통과", ["PERFORMANCE_INPUT_OK", 5, True], [gc["status"], len(gc.get("nav", [])), rc["identity"]["qty_match"]])
rcf = R.replay([{"intent_id": "b", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 500000}], rawC,
               [ca("M1", "A", "merger", 0.5, D[2])], rate, 1_000_000, D)
case("mtm-gate-tests", "E7b_합병_보유중이면_수량자동조정_안하고_차단", [["CA_NO_AUTO_QTY"], "PERFORMANCE_BLOCKED_INCOMPLETE_RAW"],
     [mtm_at(rcf, D[2])["reasons"], R.performance_gate(rcf)["status"]])

# ═════ F. 의도 결정성 ═════
rawF = {"A": okr({d: 10000 for d in D}), "B": okr({d: 20000 for d in D})}
seq = [{"intent_id": "buyA", "sleeve": "D1", "date": D[1], "code": "A", "kind": "buy_notional", "notional": 300000},
       {"intent_id": "sellB", "sleeve": "D1", "date": D[1], "code": "B", "kind": "sell_fraction", "fraction": 1}]
rf1 = R.replay(seq, rawF, [], rate, 100000, D, positions0={"B": 15})
rf2 = R.replay(list(reversed(seq)), rawF, [], rate, 100000, D, positions0={"B": 15})
case("intent-mapping-tests", "N10_같은날_팔기먼저_입력순서_무관", [["SELL", "BUY"], 30, True, []],
     [[x["type"] for x in rf1["rows"] if x["date"] == D[1]], rf1["qty"].get("A"), rf1["rows"] == rf2["rows"] and rf1["mtm"] == rf2["mtm"],
      [w for w in flags_of(rf1) if w == "BUY_REDUCED"]],
     note="현금 10만 원 · B 15주(30만 원)를 먼저 팔아야 A 30주를 살 수 있음")
dup = [{"intent_id": "x1", "sleeve": "D1", "date": D[1], "code": "A", "kind": "buy_notional", "notional": 100000},
       {"intent_id": "x2", "sleeve": "BASKET", "date": D[1], "code": "A", "kind": "buy_notional", "notional": 50000}]
rd = R.replay(dup, rawF, [], rate, 1_000_000, D)
case("intent-mapping-tests", "N10b_같은날_같은종목_의도둘_차단", [0, ["BLOCKED_DUP_INTENT", "BLOCKED_DUP_INTENT"], False],
     [len([x for x in rd["rows"] if x["type"] == "BUY"]), flags_of(rd), mtm_at(rd, D[1])["nav_valid"]])
rawT = {"A": okr({D[0]: 100000, D[1]: 100500, D[2]: 101000, D[3]: 20100, D[4]: 20200})}
spl = ca("S1", "A", "split", 5, D[3])
ti = [{"intent_id": "t1", "sleeve": "D1", "date": D[1], "code": "A", "kind": "target_adj", "decided_at": D[0], "target_adj": 50, "adj_close_decided": 20000},
      {"intent_id": "t2", "sleeve": "D1", "date": D[3], "code": "A", "kind": "target_adj", "decided_at": D[2], "target_adj": 60, "adj_close_decided": 20200},
      {"intent_id": "t3", "sleeve": "D1", "date": D[4], "code": "A", "kind": "target_adj", "decided_at": D[3], "target_adj": 50, "adj_close_decided": 20100}]
rt = R.replay(ti, rawT, [spl], rate, 2_000_000, D)
case("intent-mapping-tests", "E8_목표수량_환산_분할전후_잠금창_차단", [10, 50, ["BLOCKED_CA_IN_LOCK_WINDOW"], 0],
     [next(x["qty"] for x in rt["rows"] if x["type"] == "BUY"), rt["qty"]["A"], [w for w in flags_of(rt) if w.startswith("BLOCKED")],
      len([x for x in rt["rows"] if x["date"] == D[4] and x["type"] in ("BUY", "SELL")])],
     note="t1: 50 × 20000 ÷ 100000 = 10주 · 분할 ×5 → 50 · t2(판단 D[2], 체결 D[3] 사이 분할) 차단 · t3: 50 × 20100 ÷ 20100 = 50 = 보유 → 주문 없음")
case("intent-mapping-tests", "E8b_환산_분수_정확_판단일_원주가_없으면_차단", [10, [None, "BLOCKED_NO_RAW_AT_DECISION"], [None, "BLOCKED_NO_ADJ_AT_DECISION"]],
     [R.convert_target(50, 20720, {"close": 103600.0, "status": "OK"})[0], list(R.convert_target(50, 20720, {"close": None, "status": "INVALID_OFFICIAL_RAW"})),
      list(R.convert_target(50, None, {"close": 103600.0, "status": "OK"}))],
     note="50 × 20720 ÷ 103600 = 10(부동소수 10.000000000000002 문제 없이 분수로)")

# ═════ 기존 PR #86 시험 10개를 v2로 이식 ═════
P = "ported-fixtures-v2"
r1 = R.replay([{"intent_id": "f1", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 1_000_000},
               {"intent_id": "f2", "sleeve": "D1", "date": D[2], "code": "A", "kind": "sell_fraction", "fraction": 1}],
              {"A": pair("A", {d: 50000 for d in D})}, [], rate, 2_000_000, D)
hand = 2_000_000 - 20 * 50000 * (1 + RATE) + 20 * 50000 * (1 - RATE)
case(P, "1_기업행동_없음", ["OK", True, True], [pair("A", {d: 50000 for d in D})[D[0]]["status"], abs(r1["cash"] - hand) < 1e-6 and r1["identity"]["cash_gap"] < 1e-6, r1["identity"]["qty_match"]])
p2_ = pair("A", base_raw, base_adj, [D[2]])
r2 = R.replay([{"intent_id": "f1", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 1_000_000}],
              {"A": p2_}, [ca("R1", "A", "split", 5, D[2])], rate, 2_000_000, D[:4])
case(P, "2_액면분할", ["adj_off_tick", 45, True], ["adj_off_tick" if not R.on_tick(base_adj[D[0]]) else "adj_on_tick", r2["qty"]["A"], r2["identity"]["qty_match"]])
p3_ = pair("B", {D[0]: 5000, D[1]: 5000, D[2]: 50000, D[3]: 50000}, {d: 50000 for d in D[:4]}, [D[2]])
f3 = [{"intent_id": "f1", "sleeve": "BASKET", "date": D[0], "code": "B", "kind": "buy_notional", "notional": 125000}]
r3a = R.replay(f3, {"B": p3_}, [ca("R2", "B", "capital_reduction", 0.1, D[2], cash_in_lieu_per_share=50000.0)], rate, 1_000_000, D[:4])
r3b = R.replay(f3, {"B": p3_}, [ca("R3", "B", "capital_reduction", 0.1, D[2])], rate, 1_000_000, D[:4])
case(P, "3_감자_병합", [2, 25000.0, True, True], [r3a["qty"]["B"], round(r3a["adj_cash"], 6), r3a["identity"]["cash_gap"] < 1e-6, "UNKNOWN_CASH_IN_LIEU" in flags_of(r3b)])
c4 = R.resolve_ca_asof([ca("R4", "C", "bonus_issue", 1.5, D[2], effective_date=D[2]),
                        dict(ca("R5", "C2", "rights_issue", 0.2, D[2], record_date=D[1]), effective_date=None)], cut(D[4]))
case(P, "4_유무상_칸없음", ["UNKNOWN_CA_FIELDS", "UNKNOWN_CA_FIELDS"], [x["status"] for x in sorted(c4, key=lambda x: x["rcept_no"])],
     missing=[x["missing"] for x in sorted(c4, key=lambda x: x["rcept_no"])])
sm = {D[0]: 20700, D[1]: 20800, D[2]: 20900, D[3]: 21000}
p5 = pair("A", sm, dict(sm), [D[2]])
r5 = R.replay([{"intent_id": "f1", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 500000}], {"A": p5}, [], rate, 1_000_000, D[:4])
case(P, "5_선택_미지원", ["UNKNOWN_SELECTION_UNSUPPORTED", 0], [p5[D[0]]["status"], len([x for x in r5["rows"] if x["type"] == "BUY"])])
case(P, "6_원주가_호가밖", ["INVALID_OFFICIAL_RAW"], [pair("A", {D[0]: 20710})[D[0]]["status"]])
c7o = ca("20260101000100", "A", "split", 2, D[2], avail="2026-01-01T16:00:00+09:00")
c7c = ca("20260102000200", "A", "split", 5, D[2], avail="2026-01-02T16:00:00+09:00", root="20260101000100")
v7 = R.resolve_ca_asof([c7o, c7c], cut(D[4]))
case(P, "7_정정_사슬", [1, 5, ["20260101000100", "20260102000200"], False],
     [len(v7), v7[0]["ratio"], v7[0]["chain_known"], R.pit_ok(c7c["available_at_kst"], R.cutoff_of("20260102", "08:00"))])
r8 = R.replay([{"intent_id": "b", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 700000},
               {"intent_id": "s", "sleeve": "D1", "date": D[2], "code": "A", "kind": "sell_fraction", "fraction": 0.5}],
              {"A": pair("A", {D[0]: 33350, D[1]: 34000, D[2]: 35000, D[3]: 35000})}, [], rate, 1_000_000, D[:4])
bq, sq = 700000 // 33350, (700000 // 33350) // 2
hand8 = 1_000_000 - bq * 33350 * (1 + RATE) + sq * 35000 * (1 - RATE)
case(P, "8_비용_항등식", [True, True, True], [abs(r8["cash"] - hand8) < 1e-6, r8["identity"]["cash_gap"] < 1e-6, r8["identity"]["fill_prices_on_tick"]])
r9 = R.replay([{"intent_id": "b", "sleeve": "D1", "date": D[0], "code": "A", "kind": "buy_notional", "notional": 5_000_000},
               {"intent_id": "s", "sleeve": "D1", "date": D[1], "code": "A", "kind": "sell_qty", "qty": 10_000}],
              {"A": pair("A", {d: 10000 for d in D})}, [], rate, 1_000_000, D)
case(P, "9_한도_음수", [True, True, True, 0], ["BUY_REDUCED" in flags_of(r9), "SELL_CAPPED" in flags_of(r9), r9["cash"] >= 0, r9["qty"]["A"]])
case(P, "10_15분봉_거부", ["OUT_OF_SCOPE_15M"],
     [R.replay([{"intent_id": "m", "sleeve": "M15", "date": "202601050930", "code": "A", "kind": "buy_notional", "notional": 1}], {}, [], rate, 1, D)["status"]])

# ═════ 저장 ═════
OUTDIR.mkdir(parents=True, exist_ok=True)
summary = {}
for grp, cases in GROUPS.items():
    body = {"cases": cases, "pass": all(v["pass"] for v in cases.values()), "n": len(cases), "n_pass": sum(v["pass"] for v in cases.values())}
    if grp == "call-budget":
        body = {"plan": plan, **body}
    (OUTDIR / f"{grp}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1, default=str))
    summary[grp] = {"n": body["n"], "n_pass": body["n_pass"], "fail": [k for k, v in cases.items() if not v["pass"]]}
summary["all_pass"] = all(not v["fail"] for v in summary.values() if isinstance(v, dict))
print(json.dumps(summary, ensure_ascii=False))
