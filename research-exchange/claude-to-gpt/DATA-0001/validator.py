"""DATA-0001 시점별 연구증거 오프라인 검증기(규칙 세트 1개 — PREREG-LOCK 3 · 4장).

표준 라이브러리만 씁니다. 네트워크 · 파일 쓰기 · 운영 모듈을 쓰지 않는 순수 함수입니다.
- Store.append(record): 들어온 순서대로 검사하고 받거나 거부합니다(append-only, 받은 레코드는 바꾸지 않음).
- Store.query(...): 시점 질의. 자료가 없으면 UNKNOWN · NONE_KNOWN을 돌려주며 추정하지 않습니다.
mutations(시험용 결함 목록)는 변이 시험에서만 넘깁니다. 기본은 빈 집합입니다.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

ENVELOPE = ("record_id", "record_type", "schema_version", "security_id", "market", "source_system",
            "source_endpoint_or_report", "source_mode", "as_of", "available_at", "fetched_at", "version",
            "revision_of", "is_correction", "normalized_sha256", "ingest_run_id", "collector_version",
            "created_at", "public_ok", "evidence_ref", "payload")
PRIVACY_KEYS = {"account_no", "acct_no", "cano", "broker_order_no", "odno", "raw_response", "appkey", "appsecret",
                "access_token", "session_url"}
SOURCE_MODES = {"OBSERVED_MARKET", "HISTORICAL_MODEL", "OBSERVED_KIS_PAPER", "SYNTHETIC"}
TYPES = {"PRICE_BAR_RAW", "PRICE_BAR_ADJ", "UNIVERSE_SNAPSHOT", "SECURITY_EVENT", "TRADING_STATUS", "CORP_ACTION",
         "DART_FILING", "INVESTOR_FLOW", "FINANCIAL", "SIGNAL", "ORDER_EVENT", "FILL", "COST_SCHEDULE", "ACCOUNT_STATE"}
SEC_EVENT_KINDS = {"LISTING", "DELISTING", "MARKET_MOVE", "CODE_CHANGE"}
EVIDENCE_RE = re.compile(r"^ev_[0-9a-f]{16}$")
MODEL_KEYS = ("bar", "price_field", "rule_id", "slippage_in_price")
ADJ_KEYS = ("adj_basis", "adj_factor")
KST = timedelta(hours=9)


def norm_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def cutoff_hash(inputs):
    return hashlib.sha256("\n".join(sorted(inputs)).encode("utf-8")).hexdigest()


class Reject(Exception):
    pass


def parse_ts(s, mut):
    if not isinstance(s, str):
        raise Reject("NO_TZ")
    try:
        x = datetime.fromisoformat(s)
    except ValueError:
        raise Reject("NO_TZ")
    if "M02" in mut:                      # 변이: 시간대가 없거나 달라도 그냥 KST로 봄
        return x.replace(tzinfo=timezone(KST)) if x.tzinfo is None else x
    if x.tzinfo is None:
        raise Reject("NO_TZ")
    if x.utcoffset() != KST:
        raise Reject("NOT_KST")
    return x


def day_start(d, plus=0):
    return datetime.fromisoformat(d + "T00:00:00+09:00") + timedelta(days=plus)


def has_key_deep(x, keys):
    if isinstance(x, dict):
        return any(k in keys or has_key_deep(v, keys) for k, v in x.items())
    if isinstance(x, list):
        return any(has_key_deep(v, keys) for v in x)
    return False


class Store:
    def __init__(self, mutations=()):
        self.mut = set(mutations)
        self.acc = {}           # (record_id, version) -> record
        self.ts = {}            # (record_id, version) -> {"as_of","available_at"}
        self.log = []           # [{"index","record_id","version","verdict","rule"}]
        self.duplicates = 0
        self.orders = {}        # order_id -> [(event, at, seq)]

    # ---------- 공통 ----------
    def _times(self, r):
        out = {}
        for k in ("as_of", "available_at", "fetched_at", "created_at"):
            out[k] = parse_ts(r[k], self.mut)
        for k, v in r["payload"].items():
            if (k == "at" or k.endswith("_at")) and v is not None:
                out["p." + k] = parse_ts(v, self.mut)
        return out

    def _ref(self, ref):
        rid, _, v = ref.rpartition("@")
        key = (rid, int(v)) if v.isdigit() else None
        return key if key in self.acc else None

    def append(self, r, index=None):
        try:
            verdict, rule = self._check(r)
        except Reject as x:
            verdict, rule = "REJECTED", str(x)
        self.log.append({"index": index, "record_id": r.get("record_id"), "version": r.get("version"),
                         "verdict": verdict, "rule": rule})
        return verdict, rule

    def _check(self, r):
        m = self.mut
        if any(k not in r for k in ENVELOPE) or not (r.get("raw_payload_sha256") or r.get("raw_ref")):
            raise Reject("ENVELOPE_MISSING")
        if r["record_type"] not in TYPES or r["source_mode"] not in SOURCE_MODES:
            raise Reject("ENVELOPE_MISSING")
        if "M16" not in m and has_key_deep(r, PRIVACY_KEYS):
            raise Reject("PRIVACY_FIELD")
        tm = self._times(r)
        p = r["payload"]
        if "M08" not in m and norm_hash(p) != r["normalized_sha256"]:
            raise Reject("HASH_MISMATCH")
        if "M03" not in m and tm["available_at"] < tm["as_of"]:
            raise Reject("AVAILABLE_BEFORE_ASOF")
        if "M04" not in m and tm["fetched_at"] < tm["available_at"]:
            raise Reject("FETCHED_BEFORE_AVAILABLE")
        rid, ver = r["record_id"], r["version"]
        key = (rid, ver)
        if key in self.acc:
            if self.acc[key]["normalized_sha256"] == r["normalized_sha256"]:
                self.duplicates += 1
                return "DUPLICATE_IGNORED", None
            if "M01" not in m:
                raise Reject("OVERWRITE_REJECTED")
        if "M06" not in m:
            self._lineage(r)
        getattr(self, "_t_" + r["record_type"].lower())(r, tm, p)
        self.acc[key] = r
        self.ts[key] = {"as_of": tm["as_of"], "available_at": tm["available_at"], "t": tm}
        return "ACCEPTED", None

    def _lineage(self, r):
        rid, ver, rev = r["record_id"], r["version"], r["revision_of"]
        if not isinstance(ver, int) or ver < 1:
            raise Reject("LINEAGE_BROKEN")
        if ver == 1:
            if rev is not None or r["is_correction"]:
                raise Reject("LINEAGE_BROKEN")
            return
        if isinstance(rev, str):
            prid, _, pv = rev.rpartition("@")
            if prid == rid and pv.isdigit() and int(pv) >= ver:
                raise Reject("LINEAGE_CYCLE")
        if rev != f"{rid}@{ver - 1}" or not r["is_correction"]:
            raise Reject("LINEAGE_BROKEN")
        parent = self.acc.get((rid, ver - 1))
        if parent is None or parent["record_type"] != r["record_type"]:
            raise Reject("LINEAGE_BROKEN")

    # ---------- 종류별 ----------
    def _t_price_bar_raw(self, r, tm, p):
        if "M07" not in self.mut and (p.get("adjusted") is not False or any(k in p for k in ADJ_KEYS)):
            raise Reject("ADJUSTED_AS_RAW")

    def _t_price_bar_adj(self, r, tm, p):
        if p.get("adjusted") is not True:
            raise Reject("RAW_AS_ADJUSTED")

    def _t_universe_snapshot(self, r, tm, p):
        if not isinstance(p.get("members"), list) or "complete" not in p or not p.get("date"):
            raise Reject("ENVELOPE_MISSING")

    def _t_security_event(self, r, tm, p):
        if p.get("kind") not in SEC_EVENT_KINDS or not p.get("effective_at"):
            raise Reject("BAD_SECURITY_EVENT")

    def _t_trading_status(self, r, tm, p):
        if p.get("status") not in ("TRADING", "HALTED") or "p.effective_at" not in tm:
            raise Reject("BAD_TRADING_STATUS")

    def _t_corp_action(self, r, tm, p):
        if "M13" not in self.mut and any(p.get(k) in (None, "") for k in
                                         ("kind", "ratio", "record_date", "effective_date", "rcept_no", "rcept_at")):
            raise Reject("CORP_ACTION_INCOMPLETE")

    def _t_dart_filing(self, r, tm, p):
        if p.get("time_known"):
            if "p.rcept_at" not in tm:
                raise Reject("AVAILABLE_BEFORE_RCEPT")
            if tm["available_at"] < tm["p.rcept_at"]:
                raise Reject("AVAILABLE_BEFORE_RCEPT")
        elif "M14" not in self.mut and tm["available_at"] < day_start(p["rcept_dt"], 1):
            raise Reject("DATE_ONLY_TOO_EARLY")

    def _t_investor_flow(self, r, tm, p):
        if "M20" not in self.mut and tm["available_at"] < day_start(p["trade_date"]) + timedelta(hours=15, minutes=30):
            raise Reject("FLOW_TOO_EARLY")

    def _t_financial(self, r, tm, p):
        k = self._ref(p.get("filing_record") or "")
        if k is None:
            raise Reject("INPUT_UNKNOWN")
        if tm["available_at"] < self.ts[k]["available_at"]:
            raise Reject("FINANCIAL_BEFORE_FILING")

    def _cutoff_ok(self, avail, limit):
        if "M05" in self.mut:
            return avail <= limit + timedelta(days=1)
        return avail <= limit

    def _t_signal(self, r, tm, p):
        sa, da, ea = tm.get("p.signal_at"), tm.get("p.decision_at"), tm.get("p.earliest_order_at")
        if None in (sa, da, ea) or not (sa <= da <= ea):
            raise Reject("SIGNAL_TIME_ORDER")
        for ref in p.get("inputs") or []:
            k = self._ref(ref)
            if k is None:
                raise Reject("INPUT_UNKNOWN")
            if not self._cutoff_ok(self.ts[k]["available_at"], da):
                raise Reject("INPUT_AFTER_DECISION")
            if "M21" not in self.mut and p.get("price_basis") == "RAW" and self.acc[k]["record_type"] == "PRICE_BAR_ADJ":
                raise Reject("BASIS_MIX")
        if p.get("cutoff_hash") != cutoff_hash(p.get("inputs") or []):
            raise Reject("CUTOFF_HASH_MISMATCH")

    def _t_account_state(self, r, tm, p):
        for ref in p.get("inputs") or []:
            k = self._ref(ref)
            if k is None:
                raise Reject("INPUT_UNKNOWN")
            if not self._cutoff_ok(self.ts[k]["available_at"], tm["as_of"]):
                raise Reject("INPUT_AFTER_ASOF")

    def _t_order_event(self, r, tm, p):
        oid, ev, at, seq = p.get("order_id"), p.get("event"), tm.get("p.at"), p.get("seq")
        prev = self.orders.get(oid, [])
        if "M19" not in self.mut:
            for (e0, a0, s0) in prev:
                if a0 == at and (s0 is None or seq is None or s0 == seq):
                    raise Reject("AMBIGUOUS_ORDER_SEQ")
        seen = [e for e, _, _ in prev]
        ok = {"INTENT": not seen,
              "ACCEPTED": seen == ["INTENT"],
              "REJECTED": seen == ["INTENT"],
              "FILLED": "ACCEPTED" in seen and "CANCELLED" not in seen and "REJECTED" not in seen,
              "CANCELLED": "ACCEPTED" in seen and "CANCELLED" not in seen}.get(ev, False)
        if not ok:
            raise Reject("BAD_ORDER_TRANSITION")
        self.orders.setdefault(oid, []).append((ev, at, seq))

    def _t_fill(self, r, tm, p):
        mode, ev = r["source_mode"], r["evidence_ref"]
        if mode == "OBSERVED_KIS_PAPER" and "M15" not in self.mut:
            if not ev:
                raise Reject("OBSERVED_NO_EVIDENCE")
            if not EVIDENCE_RE.match(ev):
                raise Reject("EVIDENCE_REF_NOT_PSEUDONYMOUS")
        if mode == "HISTORICAL_MODEL":
            mdl = p.get("model") or {}
            if any(mdl.get(k) is None for k in MODEL_KEYS):
                raise Reject("MODEL_FILL_INCOMPLETE")
            if ev:
                raise Reject("SOURCE_MODE_MIX")

    def _t_cost_schedule(self, r, tm, p):
        if not p.get("source_ref") or not p.get("valid_from") or p.get("component") not in ("FEE", "TAX", "SLIPPAGE"):
            raise Reject("COST_SOURCE_MISSING")

    # ---------- 시점 질의 ----------
    def _latest(self, rtype, t, ignore_avail=False):
        best = {}
        for (rid, v), r in self.acc.items():
            if r["record_type"] != rtype:
                continue
            if not ignore_avail and self.ts[(rid, v)]["available_at"] > t:
                continue
            if rid not in best or v > best[rid][0]:
                best[rid] = (v, r)
        return [r for _, r in best.values()]

    def query(self, q):
        t = datetime.fromisoformat(q["t"])
        kind = q["q"]
        if kind == "asof":
            vs = [v for (rid, v) in self.acc if rid == q["record_id"] and self.ts[(rid, v)]["available_at"] <= t]
            return f"{q['record_id']}@{max(vs)}" if vs else "NONE"
        if kind == "universe":
            snaps = [r for r in self._latest("UNIVERSE_SNAPSHOT", t)
                     if r["payload"]["market"] == q["market"]
                     and ("M09" in self.mut or r["payload"]["date"] == q["date"])]
            if not snaps:
                return "UNKNOWN:NO_SNAPSHOT"
            s = max(snaps, key=lambda r: (r["payload"]["date"], r["version"]))
            if not s["payload"]["complete"] and "M10" not in self.mut:
                return "UNKNOWN:INCOMPLETE"
            return sorted(m["security_id"] for m in s["payload"]["members"])
        if kind == "status":
            recs = [r for r in self._latest("TRADING_STATUS", t, ignore_avail="M12" in self.mut)
                    if r["security_id"] == q["security"]
                    and datetime.fromisoformat(r["payload"]["effective_at"]) <= t]
            if not recs:
                return "TRADING" if "M11" in self.mut else "UNKNOWN"
            return max(recs, key=lambda r: (r["payload"]["effective_at"], r["version"]))["payload"]["status"]
        if kind == "corp":
            recs = [r for r in self._latest("CORP_ACTION", t) if r["security_id"] == q["security"]
                    and r["payload"]["effective_date"] <= q["date"]]
            return sorted(r["payload"]["kind"] for r in recs) if recs else "NONE_KNOWN"
        if kind == "cost":
            allc = [r for r in self._latest("COST_SCHEDULE", t) if r["payload"]["component"] == q["component"]]
            hit = [r for r in allc if r["payload"]["valid_from"] <= q["date"]
                   and (r["payload"]["valid_to"] is None or q["date"] <= r["payload"]["valid_to"])]
            if not hit:
                if not allc:
                    return "UNKNOWN:NONE"
                if "M17" in self.mut:
                    before = [r for r in allc if r["payload"]["valid_from"] <= q["date"]]
                    if before:
                        return max(before, key=lambda r: r["payload"]["valid_from"])["payload"]["rate"]
                return "UNKNOWN:GAP"
            if len(hit) > 1:
                if "M18" in self.mut:
                    return min(hit, key=lambda r: r["payload"]["valid_from"])["payload"]["rate"]
                return "UNKNOWN:OVERLAP"
            return hit[0]["payload"]["rate"]
        raise ValueError("unknown query")


def run_fixture(fx, mutations=()):
    """fixture 하나를 돌려 (거부 목록, 중복 수, 질의 결과, 받은 레코드) 반환."""
    st = Store(mutations)
    for i, r in enumerate(fx["records"]):
        st.append(r, i)
    rejected = [[e["index"], e["rule"]] for e in st.log if e["verdict"] == "REJECTED"]
    answers = [st.query(q) for q in fx["queries"]]
    return {"rejected": rejected, "duplicates": st.duplicates, "answers": answers,
            "accepted": [st.acc[k] for k in sorted(st.acc, key=lambda k: (str(k[0]), k[1]))], "store": st}
