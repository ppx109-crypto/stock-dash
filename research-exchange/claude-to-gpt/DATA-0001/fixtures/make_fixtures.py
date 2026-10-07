"""DATA-0001 합성 fixture 42개를 손으로 정한 입력 · 기대 판정 그대로 적는 도우미.
계산은 payload hash · cutoff_hash(입력 모양 만들기)뿐이며 기대 판정은 모두 손으로 적은 문자열입니다.
사용: python3 -I fixtures/make_fixtures.py fixtures/fixtures.json"""
import hashlib, json, sys

D, D2 = "2026-01-05", "2026-01-06"
def t(day, hm): return f"{day}T{hm}:00+09:00"
def nh(p): return hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
def cut(inputs): return hashlib.sha256("\n".join(sorted(inputs)).encode()).hexdigest()

def rec(rid, rtype, payload, as_of, avail, fetched=None, version=1, rev=None, corr=False, sec="S001", market="KOSPI",
        system="KIS", mode="OBSERVED_MARKET", evidence=None, drop=(), extra=None, bad_hash=False):
    r = {"record_id": rid, "record_type": rtype, "schema_version": 1, "security_id": sec, "market": market,
         "source_system": system, "source_endpoint_or_report": "synthetic-fixture", "source_mode": mode,
         "as_of": as_of, "available_at": avail, "fetched_at": fetched or avail, "version": version,
         "revision_of": rev, "is_correction": corr, "raw_payload_sha256": nh({"raw": payload}),
         "normalized_sha256": "0" * 64 if bad_hash else nh(payload), "ingest_run_id": "run_synth_0001",
         "collector_version": "synthetic-1", "created_at": fetched or avail, "public_ok": True,
         "evidence_ref": evidence, "payload": payload}
    if extra:
        r.update(extra)
    for k in drop:
        r.pop(k)
    return r

def bar(rid="bar", close=100, adjusted=False, extra_p=None, rtype="PRICE_BAR_RAW", day=D, **kw):
    p = {"date": day, "session": "REGULAR", "open": 99, "high": 101, "low": 98, "close": close, "volume": 1000,
         "adjusted": adjusted}
    if extra_p:
        p.update(extra_p)
    kw.setdefault("as_of", t(day, "15:30")); kw.setdefault("avail", t(day, "15:40"))
    return rec(rid, rtype, p, **kw)

def sig(rid, inputs, signal_at, decision_at, earliest, basis="RAW", bad_cut=False):
    p = {"strategy_id": "SYN_STRAT", "strategy_hash": "a" * 64, "signal_id": rid, "signal_at": signal_at,
         "decision_at": decision_at, "earliest_order_at": earliest, "price_basis": basis, "inputs": inputs,
         "cutoff_hash": "f" * 64 if bad_cut else cut(inputs)}
    return rec(rid, "SIGNAL", p, signal_at, decision_at, system="STRATEGY", mode="HISTORICAL_MODEL")

def filing(rid, rcept_no, rcept_dt, rcept_at, avail, time_known=True, version=1, rev=None, corr=False, orig=None, as_of=None):
    p = {"rcept_no": rcept_no, "rcept_dt": rcept_dt, "rcept_at": rcept_at, "time_known": time_known,
         "report_nm": "합성 공시", "original_rcept_no": orig}
    return rec(rid, "DART_FILING", p, as_of or rcept_at or t(rcept_dt, "00:00"), avail, version=version, rev=rev,
               corr=corr, system="DART")

def status(rid, st, eff, avail, sec="S001"):
    return rec(rid, "TRADING_STATUS", {"status": st, "effective_at": eff}, eff, avail, sec=sec, system="KRX")

def order(rid, oid, ev, at, seq=None):
    p = {"order_id": oid, "event": ev, "at": at}
    if seq is not None:
        p["seq"] = seq
    return rec(rid, "ORDER_EVENT", p, at, at, system="KIS_PAPER", mode="OBSERVED_KIS_PAPER")

def fill(rid, mode, evidence=None, model=None):
    p = {"order_id": "o1", "side": "BUY", "qty": 10, "price": 100}
    if model is not None:
        p["model"] = model
    return rec(rid, "FILL", p, t(D, "09:01"), t(D, "09:01"), system="KIS_PAPER" if mode == "OBSERVED_KIS_PAPER" else "MODEL",
               mode=mode, evidence=evidence)

def cost(rid, comp, rate, vf, vt, src="synthetic-schedule-doc-v1"):
    p = {"component": comp, "rate": rate, "valid_from": vf, "valid_to": vt, "source_ref": src}
    return rec(rid, "COST_SCHEDULE", p, "2025-12-31T00:00:00+09:00", "2025-12-31T09:00:00+09:00", sec="ALL",
               market="ALL", system="DOC")

MODEL = {"bar": "D+1 REGULAR", "price_field": "open", "rule_id": "R4", "slippage_in_price": True}
FX = []
def fx(i, note, records, rejected=(), dup=0, queries=()):
    FX.append({"id": f"FX{i:02d}", "note": note, "records": records,
               "expect": {"rejected": [list(x) for x in rejected], "duplicates": dup},
               "queries": [dict(q) for q in queries]})

fx(1, "정상 원주가 봉", [bar()], queries=[{"q": "asof", "record_id": "bar", "t": t(D, "15:45"), "expect": "bar@1"}])
fx(2, "최초판+정정판", [bar(), bar(close=101, version=2, rev="bar@1", corr=True, avail=t(D2, "08:00"))],
   queries=[{"q": "asof", "record_id": "bar", "t": t(D, "16:00"), "expect": "bar@1"},
            {"q": "asof", "record_id": "bar", "t": t(D2, "09:00"), "expect": "bar@2"}])
fx(3, "덮어쓰기", [bar(), bar(close=101)], [(1, "OVERWRITE_REJECTED")],
   queries=[{"q": "asof", "record_id": "bar", "t": t(D, "16:00"), "expect": "bar@1"}])
fx(4, "같은 레코드 재전달", [bar(), bar()], dup=1)
fx(5, "시간대 없음", [bar(avail="2026-01-05T15:40:00")], [(0, "NO_TZ")])
fx(6, "KST 아님", [bar(avail="2026-01-05T06:40:00+00:00")], [(0, "NOT_KST")])
fx(7, "available<as_of", [bar(avail=t(D, "15:00"))], [(0, "AVAILABLE_BEFORE_ASOF")])
fx(8, "fetched<available", [bar(fetched=t(D, "15:35"))], [(0, "FETCHED_BEFORE_AVAILABLE")])
fx(9, "결정 뒤 공개 입력", [bar(), sig("sig", ["bar@1"], t(D, "15:10"), t(D, "15:15"), t(D, "15:20"))],
   [(1, "INPUT_AFTER_DECISION")])
fx(10, "정정판은 결정 뒤 공개", [bar(), bar(close=101, version=2, rev="bar@1", corr=True, avail=t(D2, "10:00")),
                           sig("sig1", ["bar@1"], t(D2, "08:50"), t(D2, "09:00"), t(D2, "09:00")),
                           sig("sig2", ["bar@2"], t(D2, "08:50"), t(D2, "09:00"), t(D2, "09:00"))],
   [(3, "INPUT_AFTER_DECISION")])
fx(11, "v1 없이 v2", [bar(version=2, rev="bar@1", corr=True)], [(0, "LINEAGE_BROKEN")])
fx(12, "자기 참조", [bar(), bar(close=101, version=2, rev="bar@2", corr=True, avail=t(D2, "08:00"))], [(1, "LINEAGE_CYCLE")])
fx(13, "정정 표시 없음", [bar(), bar(close=101, version=2, rev="bar@1", corr=False, avail=t(D2, "08:00"))],
   [(1, "LINEAGE_BROKEN")])
fx(14, "수정주가를 원주가로", [bar(adjusted=True)], [(0, "ADJUSTED_AS_RAW")])
fx(15, "원주가에 조정 필드", [bar(extra_p={"adj_basis": "KIS_ADJ"})], [(0, "ADJUSTED_AS_RAW")])
fx(16, "hash 틀림", [bar(bad_hash=True)], [(0, "HASH_MISMATCH")])
snap = lambda complete: rec("uni", "UNIVERSE_SNAPSHOT", {"date": D, "market": "KOSPI", "complete": complete,
     "members": [{"security_id": "S002", "status": "LISTED"}, {"security_id": "S001", "status": "LISTED"}]},
     t(D, "08:00"), t(D, "08:30"), sec="ALL", system="KRX")
fx(17, "Universe 스냅숏", [snap(True)], queries=[
   {"q": "universe", "date": D, "market": "KOSPI", "t": t(D, "09:00"), "expect": ["S001", "S002"]},
   {"q": "universe", "date": D2, "market": "KOSPI", "t": t(D2, "09:00"), "expect": "UNKNOWN:NO_SNAPSHOT"},
   {"q": "universe", "date": D, "market": "KOSPI", "t": t(D, "08:00"), "expect": "UNKNOWN:NO_SNAPSHOT"}])
fx(18, "불완전 스냅숏", [snap(False)], queries=[
   {"q": "universe", "date": D, "market": "KOSPI", "t": t(D, "09:00"), "expect": "UNKNOWN:INCOMPLETE"}])
fx(19, "거래정지 · 재개", [status("st0", "TRADING", t(D, "08:00"), t(D, "08:00")),
                     status("st1", "HALTED", t(D, "10:00"), t(D, "10:00")),
                     status("st2", "TRADING", t(D, "14:00"), t(D, "14:00"))], queries=[
   {"q": "status", "security": "S001", "t": t(D, "09:30"), "expect": "TRADING"},
   {"q": "status", "security": "S001", "t": t(D, "11:00"), "expect": "HALTED"},
   {"q": "status", "security": "S001", "t": t(D, "15:00"), "expect": "TRADING"},
   {"q": "status", "security": "S002", "t": t(D, "11:00"), "expect": "UNKNOWN"}])
fx(20, "정지 공개가 늦음", [status("st0", "TRADING", t(D, "08:00"), t(D, "08:00")),
                     status("st1", "HALTED", t(D, "10:00"), t(D, "10:05"))], queries=[
   {"q": "status", "security": "S001", "t": t(D, "10:02"), "expect": "TRADING"},
   {"q": "status", "security": "S001", "t": t(D, "10:06"), "expect": "HALTED"}])
ca = lambda ratio: rec("ca", "CORP_ACTION", {"kind": "SPLIT", "ratio": ratio, "record_date": D2, "effective_date": "2026-01-08",
                       "rcept_no": "R0001", "rcept_at": t(D, "16:10")}, t(D, "16:10"), t(D, "16:10"), system="DART")
fx(21, "기업행동 효력시점", [ca("1:5")], queries=[
   {"q": "corp", "security": "S001", "date": "2026-01-08", "t": t(D, "15:00"), "expect": "NONE_KNOWN"},
   {"q": "corp", "security": "S001", "date": "2026-01-08", "t": t(D2, "09:00"), "expect": ["SPLIT"]},
   {"q": "corp", "security": "S001", "date": "2026-01-07", "t": t(D2, "09:00"), "expect": "NONE_KNOWN"}])
fx(22, "기업행동 비율 없음", [ca(None)], [(0, "CORP_ACTION_INCOMPLETE")])
fx(23, "장중 공시", [filing("f", "R1", D, t(D, "11:20"), t(D, "11:20")),
                 sig("sig", ["f@1"], t(D, "15:10"), t(D, "15:15"), t(D, "15:20"))])
fx(24, "장후 공시", [filing("f", "R1", D, t(D, "17:30"), t(D, "17:30")),
                 sig("sigA", ["f@1"], t(D, "15:10"), t(D, "15:15"), t(D, "15:20")),
                 sig("sigB", ["f@1"], t(D2, "15:10"), t(D2, "15:15"), t(D2, "15:20"))], [(1, "INPUT_AFTER_DECISION")])
fx(25, "날짜만 아는 공시", [filing("f1", "R1", D, None, t(D, "09:00"), time_known=False),
                      filing("f2", "R2", D, None, t(D2, "00:00"), time_known=False)], [(0, "DATE_ONLY_TOO_EARLY")])
fx(26, "정정공시", [filing("f", "R1", D, t(D, "12:00"), t(D, "12:00")),
                filing("f", "R2", D2, t(D2, "08:30"), t(D2, "08:30"), version=2, rev="f@1", corr=True, orig="R1")],
   queries=[{"q": "asof", "record_id": "f", "t": t(D, "13:00"), "expect": "f@1"},
            {"q": "asof", "record_id": "f", "t": t(D2, "09:00"), "expect": "f@2"}])
fx(27, "관측 체결 증거 없음", [fill("fl", "OBSERVED_KIS_PAPER")], [(0, "OBSERVED_NO_EVIDENCE")])
fx(28, "증거가 주문번호 모양", [fill("fl1", "OBSERVED_KIS_PAPER", evidence="0001234567"),
                         fill("fl2", "OBSERVED_KIS_PAPER", evidence="ev_0123456789abcdef")],
   [(0, "EVIDENCE_REF_NOT_PSEUDONYMOUS")])
p29 = {"order_id": "o1", "side": "BUY", "qty": 1, "price": 100, "broker_order_no": "X"}
fx(29, "개인정보 키", [rec("fl1", "FILL", p29, t(D, "09:01"), t(D, "09:01"), mode="OBSERVED_KIS_PAPER",
                         evidence="ev_0123456789abcdef"),
                     bar(rid="b2", extra=None, **{}) | {"account_no": "X"}],
   [(0, "PRIVACY_FIELD"), (1, "PRIVACY_FIELD")])
fx(30, "모형 체결 불완전 · 모드 섞임", [fill("fl1", "HISTORICAL_MODEL", model={k: v for k, v in MODEL.items() if k != "price_field"}),
                               fill("fl2", "HISTORICAL_MODEL", evidence="ev_0123456789abcdef", model=MODEL)],
   [(0, "MODEL_FILL_INCOMPLETE"), (1, "SOURCE_MODE_MIX")])
fx(31, "비용 공백", [cost("feeA", "FEE", "0.00015", "2026-01-01", "2026-06-30"),
                 cost("feeB", "FEE", "0.00015", "2026-07-02", None)], queries=[
   {"q": "cost", "component": "FEE", "date": "2026-03-02", "t": t(D, "09:00"), "expect": "0.00015"},
   {"q": "cost", "component": "FEE", "date": "2026-07-01", "t": t(D, "09:00"), "expect": "UNKNOWN:GAP"},
   {"q": "cost", "component": "TAX", "date": "2026-03-02", "t": t(D, "09:00"), "expect": "UNKNOWN:NONE"}])
fx(32, "비용 중첩 · 출처 없음", [cost("feeA", "FEE", "0.00015", "2026-01-01", "2026-06-30"),
                          cost("feeC", "FEE", "0.0002", "2026-03-01", "2026-12-31"),
                          cost("feeD", "FEE", "0.0003", "2027-01-01", None, src=None)], [(2, "COST_SOURCE_MISSING")],
   queries=[{"q": "cost", "component": "FEE", "date": "2026-03-02", "t": t(D, "09:00"), "expect": "UNKNOWN:OVERLAP"},
            {"q": "cost", "component": "FEE", "date": "2026-02-02", "t": t(D, "09:00"), "expect": "0.00015"}])
fx(33, "같은 시각 순서 충돌", [order("e1", "o1", "INTENT", t(D, "09:00"), 1), order("e2", "o1", "ACCEPTED", t(D, "09:00"), 2),
                         order("e3", "o1", "FILLED", t(D, "09:05")), order("e4", "o1", "CANCELLED", t(D, "09:05"))],
   [(3, "AMBIGUOUS_ORDER_SEQ")])
fx(34, "접수 없이 체결", [order("e1", "o1", "INTENT", t(D, "09:00")), order("e2", "o1", "FILLED", t(D, "09:05"))],
   [(1, "BAD_ORDER_TRANSITION")])
flow = lambda rid, av: rec(rid, "INVESTOR_FLOW", {"trade_date": D, "외국인": 10, "기관": -5, "개인": -5},
                           t(D, "00:00"), av, system="KIS")
fx(35, "수급 공개 시각", [flow("fw1", t(D, "15:00")), flow("fw2", t(D, "18:00"))], [(0, "FLOW_TOO_EARLY")])
fin = lambda rid, av: rec(rid, "FINANCIAL", {"period_end": "2025-12-31", "filing_record": "f@1", "values": {"매출": 1}},
                          "2025-12-31T00:00:00+09:00", av, system="DART")
fx(36, "재무가 공시보다 먼저", [filing("f", "R1", D, t(D, "16:00"), t(D, "16:00")), fin("fin1", t(D, "15:00")),
                         fin("fin2", t(D, "16:30"))], [(1, "FINANCIAL_BEFORE_FILING")])
fx(37, "cutoff hash 틀림", [bar(), sig("sig", ["bar@1"], t(D, "15:50"), t(D, "16:00"), t(D2, "09:00"), bad_cut=True)],
   [(1, "CUTOFF_HASH_MISMATCH")])
fx(38, "주문 시각이 결정보다 앞", [bar(), sig("sig", ["bar@1"], t(D, "15:50"), t(D, "16:00"), t(D, "15:55"))],
   [(1, "SIGNAL_TIME_ORDER")])
acct = lambda rid, at: rec(rid, "ACCOUNT_STATE", {"cash": 1000000, "nav": 1000000, "alloc_won": 100000, "inputs": ["bar@1"]},
                           at, at, sec="ALL", system="LEDGER", mode="HISTORICAL_MODEL")
fx(39, "계좌 상태 입력 시각", [bar(), acct("ac1", t(D, "15:35")), acct("ac2", t(D, "16:00"))], [(1, "INPUT_AFTER_ASOF")])
fx(40, "RAW 신호에 ADJ 봉", [bar(rid="adj", rtype="PRICE_BAR_ADJ", adjusted=True, extra_p={"adj_basis": "KIS_ADJ"}),
                         sig("sig", ["adj@1"], t(D, "15:50"), t(D, "16:00"), t(D2, "09:00"))], [(1, "BASIS_MIX")])
sev = lambda rid, kind: rec(rid, "SECURITY_EVENT", {"kind": kind, "effective_at": t(D2, "09:00")}, t(D, "18:00"),
                            t(D, "18:00"), system="KRX")
fx(41, "상장 사건", [sev("se1", "DELISTING"), sev("se2", "RENAME_X")], [(1, "BAD_SECURITY_EVENT")])
fx(42, "봉투 필드 없음", [bar(drop=("ingest_run_id",))], [(0, "ENVELOPE_MISSING")])
assert len(FX) == 42
json.dump({"task": "DATA-0001", "note": "비식별 합성 fixture. 기대 판정은 PREREG-LOCK 5장과 같음(손으로 적음).",
           "fixtures": FX}, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(FX), sum(len(f["records"]) for f in FX))
