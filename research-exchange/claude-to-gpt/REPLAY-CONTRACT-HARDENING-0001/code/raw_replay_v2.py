"""REPLAY-CONTRACT-HARDENING-0001 · 원주가 재생 어댑터 v2(PR #86 raw_replay.py 보강 · 연구 복사본 · 네트워크 안 씀).

PR #86 대비 보강
B. 정정 사슬 as-of: resolve_ca_asof(records, as_of) — 그 시각까지 공개된 버전만, 공개 시각 순(접수번호 문자열 순 아님).
   원 접수 없음 · available_at 없음 · 같은 시각 두 버전 → UNKNOWN_CA_VERSION_PIT(사슬 전체 사용 안 함).
C. cutoff 집행: pit_ok(available_at, cutoff)를 replay가 기업행동 적용 전에 날마다 호출. 날짜만 있으면 그날 23:59:59로 보아 당일 사용 금지.
   적용 뒤 나온 정정본이 회계 칸을 바꾸면 그 공개 날부터 CA_VERSION_CONFLICT_AFTER_USE(NAV 무효).
D. 원/수정 쌍 provenance: check_pair_provenance — basis 칸 · FID_ORG_ADJ_PRC · 나머지 요청 칸 같음 · 요청 해시 · 캐시 해시 · 조회 시각.
   날짜마다: 아는 기업행동 앞인데 원 = 수정 → UNKNOWN_SELECTION_UNSUPPORTED, 원 ≠ 수정인데 설명할 기업행동 없음 → UNKNOWN_CA_COVERAGE.
E. MTM 게이트: 날마다 nav_valid · reasons. performance_gate()는 하나라도 무효면 PERFORMANCE_BLOCKED_INCOMPLETE_RAW(NAV를 넘기지 않음).
F. 목표 수량 의도(target_adj): 판단일 t의 목표(수정 기준 정수) × F_t(= 저장 수정종가_t ÷ 공식 원주가_t, 분수 정확 계산) → floor.
   같은 날 팔기 먼저 · 종목 코드 오름차순 · 같은 날 같은 종목 의도 둘이면 BLOCKED_DUP_INTENT · 판단일과 체결일 사이 기업행동이면 BLOCKED_CA_IN_LOCK_WINDOW.
추가(GPT 검토에 없던 결함)
X1. PR #86은 효력일이 거래일 목록에 없으면 기업행동을 조용히 건너뜀(raw_replay.py 107줄) → 기준일 이후 첫 거래일에 적용.
X2. 수량 조정 기준일 = price_basis_date(원주가 기준이 바뀌는 첫 거래일 · 권리락일 · 변경상장 뒤 거래 재개일).
    신주 상장일(listing_date) 전에는 늘어난 수량을 평가에는 넣되 팔 수 없음(SELL_LOCKED_PENDING)."""
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from fractions import Fraction

KST = timezone(timedelta(hours=9))

UNKNOWN = {
    "UNKNOWN_SELECTION_UNSUPPORTED": "아는 기업행동 앞 날인데 원 = 수정 — 원주가 선택이 먹혔는지 모름",
    "UNKNOWN_CA_COVERAGE": "원 ≠ 수정인데 설명할 기업행동이 목록에 없음 — 기업행동 목록 불완전",
    "UNKNOWN_PROVENANCE": "원/수정 요청 칸 · basis · 요청 해시 · 캐시 해시 · 조회 시각 검증 실패",
    "INVALID_OFFICIAL_RAW": "원주가 종가가 호가 배수 아님",
    "UNKNOWN_MISSING_RAW": "그날 원주가 없음",
    "UNKNOWN_CA_FIELDS": "그 시각 버전에 필수 칸 없음",
    "UNKNOWN_CA_VERSION_PIT": "원 접수 없음 · available_at 없음 · 같은 시각 두 버전 — 그때 어느 버전이었는지 모름",
    "CA_VERSION_CONFLICT_AFTER_USE": "적용 뒤 공개된 정정본이 비율 · 날짜를 바꿈 — 그 공개 날부터 NAV 무효",
    "CA_APPLIED_LATE": "기준일 뒤에야 공개돼 늦게 적용 — 그 사이 NAV는 틀렸고 성과 차단",
    "CA_NO_AUTO_QTY": "유상 · 합병 · 분할 — 수량 자동 조정 안 함(보유 중이면 NAV 무효)",
    "UNKNOWN_CASH_IN_LIEU": "단주 현금 칸 없음",
    "UNKNOWN_MTM_STALE": "평가일 원주가 없음 — 앞 값(진단용)",
    "MTM_NO_PRIOR_PRICE": "평가할 원주가가 한 번도 없음 — 0원 대체는 유효 NAV 아님",
    "UNFILLED_INTENT": "원주가 · 상태 때문에 그날 의도를 체결 못 함",
    "BLOCKED_DUP_INTENT": "같은 날 같은 종목 의도 둘 이상",
    "BLOCKED_NO_RAW_AT_DECISION": "목표 환산에 쓸 판단일 공식 원주가 없음",
    "BLOCKED_NO_ADJ_AT_DECISION": "목표 환산에 쓸 판단일 저장 수정종가 없음",
    "BLOCKED_CA_IN_LOCK_WINDOW": "판단일과 체결일 사이 기업행동 — 잠근 목표의 기준이 바뀜",
    "SELL_LOCKED_PENDING": "상장 전 신주라 그만큼 못 팜",
    "SELL_CAPPED": "매도 요청이 팔 수 있는 보유보다 많음",
    "BUY_REDUCED": "현금 한도로 매수 축소",
    "OUT_OF_SCOPE_15M": "15분봉 입력 — 범위 밖",
}
# 날마다 NAV를 무효로 만드는 사유(체결 축소 · 매도 제한은 실제 체결 결과라 무효 아님)
NAV_INVALIDATING = {"UNKNOWN_SELECTION_UNSUPPORTED", "UNKNOWN_CA_COVERAGE", "UNKNOWN_PROVENANCE", "INVALID_OFFICIAL_RAW",
                    "UNKNOWN_MISSING_RAW", "UNKNOWN_CA_FIELDS", "UNKNOWN_CA_VERSION_PIT", "CA_VERSION_CONFLICT_AFTER_USE",
                    "CA_APPLIED_LATE", "CA_NO_AUTO_QTY", "UNKNOWN_CASH_IN_LIEU", "UNKNOWN_MTM_STALE", "MTM_NO_PRIOR_PRICE", "UNFILLED_INTENT",
                    "BLOCKED_DUP_INTENT", "BLOCKED_NO_RAW_AT_DECISION", "BLOCKED_NO_ADJ_AT_DECISION", "BLOCKED_CA_IN_LOCK_WINDOW"}


def tick(p):
    for lim, t in ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)):
        if p < lim:
            return t
    return 1000


def on_tick(p):
    return p is not None and p > 0 and abs(p / tick(p) - round(p / tick(p))) < 1e-9


# ── 시각 ──
def parse_avail(s):
    """'YYYY-MM-DDTHH:MM[:SS]+09:00' → (시각, 'time') · 'YYYY-MM-DD'/'YYYYMMDD' → (그날 23:59:59 KST, 'date') · 없음 → (None, None)."""
    if s in (None, ""):
        return None, None
    s = str(s)
    if len(s) in (8, 10) and "T" not in s:
        d = s.replace("-", "")
        return datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), 23, 59, 59, tzinfo=KST), "date"
    t = datetime.fromisoformat(s)
    if t.tzinfo is None:
        return None, None                                                   # 시간대 없는 시각은 믿지 않음
    return t.astimezone(KST), "time"


def cutoff_of(day, hhmm):
    return datetime(int(day[:4]), int(day[4:6]), int(day[6:8]), int(hhmm[:2]), int(hhmm[3:]), tzinfo=KST)


def pit_ok(available_at, cutoff):
    """same_day_pit의 정의: available_at ≤ cutoff. 시각 없음 → False. 날짜만 → 그날 23:59:59라 당일 cutoff는 못 넘음."""
    t, _ = parse_avail(available_at)
    return t is not None and t <= cutoff


# ── B. 정정 사슬 as-of ──
REQ = {"split": ("ratio", "effective_date", "price_basis_date", "listing_date"),
       "reverse_split": ("ratio", "effective_date", "price_basis_date", "listing_date"),
       "capital_reduction": ("ratio", "effective_date", "price_basis_date", "listing_date"),
       "bonus_issue": ("ratio", "record_date", "effective_date", "price_basis_date", "listing_date"),
       "rights_issue": ("ratio", "record_date", "effective_date"), "rights_bonus_issue": ("ratio", "record_date", "effective_date"),
       "merger": ("ratio", "effective_date"), "spinoff": ("ratio", "effective_date"), "spinoff_merger": ("ratio", "effective_date")}
QTY_CHANGING = {"split", "reverse_split", "capital_reduction", "bonus_issue"}
ACCOUNTING = ("ratio", "price_basis_date", "listing_date", "cash_in_lieu_per_share")


def resolve_ca_asof(records, as_of):
    """as_of(KST 시각)까지 공개된 버전만으로 사슬마다 하나를 고름. 미래 정정본은 읽지 않음."""
    chains = defaultdict(list)
    for r in records:
        chains[r.get("root_rcept_no")].append(r)
    out = []
    for root, rs in chains.items():
        code = rs[0].get("code")
        ids = {x.get("rcept_no") for x in rs}
        if root in (None, "") or root not in ids:
            out.append({"root_rcept_no": root, "code": code, "status": "UNKNOWN_CA_VERSION_PIT", "why": "ROOT_MISSING"})
            continue
        if any(parse_avail(x.get("available_at_kst"))[0] is None for x in rs):
            out.append({"root_rcept_no": root, "code": code, "status": "UNKNOWN_CA_VERSION_PIT", "why": "AVAILABLE_AT_MISSING"})
            continue
        known = sorted(((parse_avail(x["available_at_kst"])[0], x) for x in rs if parse_avail(x["available_at_kst"])[0] <= as_of),
                       key=lambda z: z[0])
        if not known:
            out.append({"root_rcept_no": root, "code": code, "status": "NOT_YET_AVAILABLE"})
            continue
        if len(known) > 1 and known[-1][0] == known[-2][0]:
            out.append({"root_rcept_no": root, "code": code, "status": "UNKNOWN_CA_VERSION_PIT", "why": "SAME_TIME_VERSIONS"})
            continue
        v = dict(known[-1][1])
        v["chain_known"] = [x["rcept_no"] for _, x in known]
        v["version_available_at"] = known[-1][0].isoformat()
        v["as_of"] = as_of.isoformat()
        v["missing"] = [f for f in REQ.get(v.get("kind"), ("ratio", "effective_date")) if v.get(f) in (None, "")]
        v["status"] = "UNKNOWN_CA_FIELDS" if v["missing"] else "OK"
        out.append(v)
    return out


# ── D. 원/수정 쌍 provenance ──
def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


PAIR_FLAG = "FID_ORG_ADJ_PRC"


def check_pair_provenance(raw_resp, adj_resp, cache_bytes):
    """raw_resp/adj_resp: {"request": {"endpoint","tr_id","params"}, "basis", "request_param_sha256", "cache_file_sha256", "fetched_at_kst"}.
    cache_bytes: {"RAW": bytes, "ADJUSTED": bytes}(로컬 캐시 원문). 돌려줌: 실패 사유 목록(비면 통과)."""
    why = []
    for resp, basis, flag in ((raw_resp, "RAW", "1"), (adj_resp, "ADJUSTED", "0")):
        rq = resp.get("request", {})
        if resp.get("basis") != basis or rq.get("params", {}).get(PAIR_FLAG) != flag:
            why.append(f"BASIS_MISMATCH:{basis}")
        if resp.get("request_param_sha256") != sha(canon(rq)):
            why.append(f"REQUEST_HASH:{basis}")
        if cache_bytes.get(basis) is None or resp.get("cache_file_sha256") != sha(cache_bytes[basis]):
            why.append(f"CACHE_HASH:{basis}")
        t, prec = parse_avail(resp.get("fetched_at_kst"))
        if t is None or prec != "time":
            why.append(f"FETCHED_AT:{basis}")
    a, b = raw_resp.get("request", {}), adj_resp.get("request", {})
    pa = {k: v for k, v in a.get("params", {}).items() if k != PAIR_FLAG}
    pb = {k: v for k, v in b.get("params", {}).items() if k != PAIR_FLAG}
    if (a.get("endpoint"), a.get("tr_id"), pa) != (b.get("endpoint"), b.get("tr_id"), pb):
        why.append("PARAM_MISMATCH")
    return why


def check_raw_pair_v2(raw_resp, adj_resp, cache_bytes, ca_basis_dates):
    """ca_basis_dates: 그 종목의 아는 수량 · 가격 기준 변경 날(price_basis_date) 목록(공식 기업행동 전체).
    돌려줌: {date: {"close", "status"}} — OK만 체결 · 평가에 씀."""
    prov = check_pair_provenance(raw_resp, adj_resp, cache_bytes)
    rawc = {r["stck_bsop_date"]: r["stck_clpr"] for r in raw_resp.get("rows", [])}
    adjc = {r["stck_bsop_date"]: r["stck_clpr"] for r in adj_resp.get("rows", [])}
    out = {}
    for d, c in rawc.items():
        before_ca = any(d < e for e in ca_basis_dates)
        a = adjc.get(d)
        if prov:
            out[d] = {"close": None, "status": "UNKNOWN_PROVENANCE", "why": prov}
        elif c is None:
            out[d] = {"close": None, "status": "UNKNOWN_MISSING_RAW"}
        elif a is None:
            out[d] = {"close": None, "status": "UNKNOWN_PROVENANCE", "why": ["ADJ_ROW_MISSING"]}
        elif before_ca and a == c:
            out[d] = {"close": None, "status": "UNKNOWN_SELECTION_UNSUPPORTED"}
        elif (not before_ca) and a != c:
            out[d] = {"close": None, "status": "UNKNOWN_CA_COVERAGE"}
        elif not on_tick(c):
            out[d] = {"close": None, "status": "INVALID_OFFICIAL_RAW"}
        else:
            out[d] = {"close": float(c), "status": "OK"}
    return out


# ── F. 목표 수량 환산 ──
def convert_target(target_adj, adj_close_t, raw_rec_t):
    """target_raw = floor(target_adj × 저장 수정종가_t ÷ 공식 원주가_t). 둘 다 판단일 t 종가라 t 종가 뒤에 알 수 있음."""
    if adj_close_t in (None, 0):
        return None, "BLOCKED_NO_ADJ_AT_DECISION"
    if not raw_rec_t or raw_rec_t.get("status") != "OK":
        return None, "BLOCKED_NO_RAW_AT_DECISION"
    f = Fraction(str(adj_close_t)) / Fraction(str(raw_rec_t["close"]))
    return math.floor(Fraction(int(target_adj)) * f), None


# ── 재생 ──
def replay(intents, raw, ca_records, rate, cash0, days, ca_cutoff="08:00", positions0=None):
    """intents: [{intent_id, sleeve, date, code, kind, ...}]
      kind 'target_adj': target_adj · decided_at · adj_close_decided(저장 수정종가, 로컬) → 그날 목표 원수량으로 맞춤
      kind 'buy_notional'(notional) · 'sell_qty'(qty) · 'sell_fraction'(fraction): PR #86 합성 시험 이식용
    raw: {code: check_raw_pair_v2 결과} · ca_records: 공개 시각 붙은 버전 전체(날마다 as-of로 자름).
    positions0: 시작 보유 {code: 원수량}(이어 받은 보유 · OPEN 레코드로 남김)."""
    for f in intents:
        if len(str(f["date"])) != 8 or f.get("sleeve") not in ("D1", "BASKET"):
            return {"status": "OUT_OF_SCOPE_15M", "intent_id": f.get("intent_id")}
    dset = sorted(days)
    q, pend = defaultdict(int), defaultdict(list)                         # pend[c] = [(상장일, 수량)]
    cash = float(cash0)
    rows, flags, mtm = [], defaultdict(list), []
    tot, adj_qty = defaultdict(float), defaultdict(int)
    adj_cash = 0.0
    lastp, applied, bad_code = {}, {}, defaultdict(set)                   # applied[root] = 적용한 버전 회계 칸
    for c, n in sorted((positions0 or {}).items()):
        q[c] += int(n)
        rows.append({"type": "OPEN", "date": None, "code": c, "qty": int(n)})
    by_day = defaultdict(list)
    for f in intents:
        by_day[f["date"]].append(f)
    first_on_or_after = lambda x: next((d for d in dset if d >= x), None)
    ca_day = {}                                                           # 종목 → 마지막 기업행동 적용일
    for i, d in enumerate(dset):
        as_of = cutoff_of(d, ca_cutoff)
        view = resolve_ca_asof(ca_records, as_of)                         # C. 그날 cutoff까지 공개된 버전만
        for e in view:                                                    # ① 장 시작 전 기업행동
            c, root = e.get("code"), e.get("root_rcept_no")
            if root in applied:                                           # 이미 적용 → 뒤 정정본이 회계 칸을 바꿨는지(수량을 실제로 바꾼 사건만)
                acct, touched = applied[root]
                if touched and e.get("status") == "OK" and tuple(e.get(k) for k in ACCOUNTING) != acct:
                    if "CA_VERSION_CONFLICT_AFTER_USE" not in bad_code[c]:
                        flags[d].append((c, "CA_VERSION_CONFLICT_AFTER_USE"))
                    bad_code[c].add("CA_VERSION_CONFLICT_AFTER_USE")
                continue
            if e["status"] in ("NOT_YET_AVAILABLE",):
                continue
            if e["status"] != "OK":                                       # 버전 PIT 모름 · 칸 없음: 보유 중이면 그 종목 NAV 무효
                if q.get(c, 0) > 0 and e["status"] not in bad_code[c]:
                    flags[d].append((c, e["status"]))
                    bad_code[c].add(e["status"])
                continue
            anchor = first_on_or_after(e.get("price_basis_date") or e.get("effective_date"))
            if anchor is None or anchor > d:
                continue
            applied[root] = (tuple(e.get(k) for k in ACCOUNTING), False)
            if e["kind"] in QTY_CHANGING:
                ca_day[c] = d                                             # 보유 없어도 잠근 목표의 기준은 바뀜
            if q.get(c, 0) <= 0:
                continue
            if e["kind"] not in QTY_CHANGING:
                flags[d].append((c, "CA_NO_AUTO_QTY"))
                bad_code[c].add("CA_NO_AUTO_QTY")
                continue
            new = Fraction(q[c]) * Fraction(str(e["ratio"]))
            whole = math.floor(new)
            frac = new - whole
            dq = whole - q[c]
            q[c] = whole
            adj_qty[c] += dq
            applied[root] = (applied[root][0], True)
            if anchor < d:                                                # 기준일 뒤에야 공개된 사건 — 그 사이 NAV는 틀렸음
                flags[d].append((c, "CA_APPLIED_LATE"))
            if dq > 0 and e.get("listing_date") and e["listing_date"] > d:
                pend[c].append((e["listing_date"], dq))
            rows.append({"type": "CA_QTY", "date": d, "code": c, "dq": dq, "rcept": e["rcept_no"], "late": anchor < d})
            if frac > 0:
                if e.get("cash_in_lieu_per_share") is None:
                    flags[d].append((c, "UNKNOWN_CASH_IN_LIEU"))
                    bad_code[c].add("UNKNOWN_CASH_IN_LIEU")
                else:
                    amt = float(frac * Fraction(str(e["cash_in_lieu_per_share"])))
                    cash += amt
                    adj_cash += amt
                    rows.append({"type": "CA_CASH", "date": d, "code": c, "amount": amt, "rcept": e["rcept_no"]})
        locked = lambda c: sum(n for until, n in pend[c] if until > d)
        todays = by_day.get(d, [])
        cnt = Counter(f["code"] for f in todays)
        plan = []
        for f in todays:                                                  # ② 의도 → 그날 주문(결정적)
            c = f["code"]
            if cnt[c] > 1:
                flags[d].append((f["intent_id"], "BLOCKED_DUP_INTENT"))
                continue
            rec = raw.get(c, {}).get(d)
            if not rec or rec["status"] != "OK":
                flags[d].append((f["intent_id"], "UNFILLED_INTENT"))
                flags[d].append((f["intent_id"], rec["status"] if rec else "UNKNOWN_MISSING_RAW"))
                continue
            px = rec["close"]
            assert on_tick(px)
            if f["kind"] == "target_adj":
                if ca_day.get(c) and f["decided_at"] < ca_day[c] <= d:
                    flags[d].append((f["intent_id"], "BLOCKED_CA_IN_LOCK_WINDOW"))
                    continue
                tgt, why = convert_target(f["target_adj"], f.get("adj_close_decided"), raw.get(c, {}).get(f["decided_at"]))
                if why:
                    flags[d].append((f["intent_id"], why))
                    continue
                if tgt < q[c]:
                    plan.append(("sell", c, q[c] - tgt, px, f["intent_id"]))
                elif tgt > q[c]:
                    plan.append(("buy", c, tgt - q[c], px, f["intent_id"]))
            elif f["kind"] == "sell_qty":
                plan.append(("sell", c, int(f["qty"]), px, f["intent_id"]))
            elif f["kind"] == "sell_fraction":
                plan.append(("sell", c, q[c] if f["fraction"] >= 1 else math.floor(q[c] * f["fraction"]), px, f["intent_id"]))
            elif f["kind"] == "buy_notional":
                plan.append(("buy", c, math.floor(f["notional"] / px), px, f["intent_id"]))
        plan.sort(key=lambda x: (x[0] != "sell", x[1]))                   # 팔기 먼저 · 종목 코드 오름차순
        for side, c, want, px, iid in plan:
            if side == "sell":
                can = q[c] - locked(c)
                if want > can:
                    flags[d].append((iid, "SELL_LOCKED_PENDING" if want <= q[c] else "SELL_CAPPED"))
                    want = max(can, 0)
                if want <= 0:
                    continue
                n = want * px
                cost = n * rate("sell", c, d, n)
                cash += n - cost
                q[c] -= want
                tot["sell_n"] += n
                tot["sell_c"] += cost
                rows.append({"type": "SELL", "date": d, "code": c, "qty": want, "price": px, "cost": cost, "intent_id": iid})
            else:
                total = lambda k: k * px * (1 + rate("buy", c, d, k * px))
                k = want
                if total(k) > cash:
                    lo, hi = 0, want
                    while lo < hi:
                        mid = (lo + hi + 1) // 2
                        if total(mid) <= cash:
                            lo = mid
                        else:
                            hi = mid - 1
                    k = lo
                    flags[d].append((iid, "BUY_REDUCED"))
                if k <= 0:
                    continue
                n = k * px
                cost = n * rate("buy", c, d, n)
                cash -= n + cost
                q[c] += k
                tot["buy_n"] += n
                tot["buy_c"] += cost
                rows.append({"type": "BUY", "date": d, "code": c, "qty": k, "price": px, "cost": cost, "intent_id": iid})
            assert cash >= -1e-6 and q[c] >= 0, "현금 · 수량 음수"
        inv, reasons = 0.0, [w for _, w in flags.get(d, []) if w in NAV_INVALIDATING]
        for c, n in sorted(q.items()):                                    # ③ 일별 MTM(원주가) + 유효성
            if n <= 0:
                continue
            reasons += sorted(bad_code[c])
            rec = raw.get(c, {}).get(d)
            if rec and rec["status"] == "OK":
                lastp[c] = rec["close"]
            elif c in lastp:
                reasons.append("UNKNOWN_MTM_STALE")
            else:
                reasons.append("MTM_NO_PRIOR_PRICE")
            inv += n * lastp.get(c, 0.0)
        mtm.append({"date": d, "cash": cash, "inv": inv, "nav_diagnostic": cash + inv,
                    "nav_valid": not reasons, "reasons": sorted(set(reasons))})
    cash_b = cash0 - tot["buy_n"] - tot["buy_c"] + tot["sell_n"] - tot["sell_c"] + adj_cash
    qty_b = defaultdict(int)
    for r in rows:
        if r["type"] in ("OPEN", "BUY", "SELL", "CA_QTY"):
            qty_b[r["code"]] += r["qty"] if r["type"] in ("OPEN", "BUY") else -r["qty"] if r["type"] == "SELL" else r["dq"]
    ident = {"cash_gap": abs(cash - cash_b), "qty_match": all(qty_b.get(c, 0) == v for c, v in q.items()) and all(v >= 0 for v in q.values()),
             "fill_prices_on_tick": all(on_tick(r["price"]) for r in rows if r["type"] in ("BUY", "SELL"))}
    return {"status": "DONE", "rows": rows, "flags": {d: v for d, v in flags.items()}, "mtm": mtm, "cash": cash, "qty": dict(q),
            "identity": ident, "totals": dict(tot), "adj_cash": adj_cash, "adj_qty": dict(adj_qty)}


# ── E. 성과 게이트 ──
def performance_gate(res):
    """성과 · MDD · 일/월 TWR에 들어갈 NAV는 이 함수만 내줌. 하나라도 무효면 NAV 없이 차단."""
    if res.get("status") != "DONE":
        return {"status": "PERFORMANCE_BLOCKED_INCOMPLETE_RAW", "why": res.get("status")}
    bad = [m for m in res["mtm"] if not m["nav_valid"]]
    idn = res["identity"]
    if bad or idn["cash_gap"] > 1e-6 or not idn["qty_match"] or not idn["fill_prices_on_tick"]:
        return {"status": "PERFORMANCE_BLOCKED_INCOMPLETE_RAW", "invalid_days": len(bad),
                "reasons": dict(Counter(r for m in bad for r in m["reasons"])), "identity_ok": not (idn["cash_gap"] > 1e-6 or not idn["qty_match"])}
    return {"status": "PERFORMANCE_INPUT_OK", "nav": [(m["date"], m["nav_diagnostic"]) for m in res["mtm"]]}
