"""REPLAY-BLOCKED-DAY-METRIC-GATE-0001 · 차단일 지표 게이트(PR120 합성 복사본 · perf(snaps) → perf_gate(ledger)) · M1~M8 고정 케이스(합성).
python3 -I blocked_day_metric_gate.py <PR120 quote_basis_gate.py 고정본> <PR120 증거 JSON> <PR114 증거 JSON> <출력 폴더>
성과 함수는 장부 전체를 받고 첫 문장에서 blocked_from을 읽음 → 있으면 PERF_BLOCKED(LEDGER_BLOCKED) · 지표 null.
정확 유리수 · 합성 종목/날짜 · 네트워크 함수 막음. 실제 TWR · MDD · 비용후수익률 산출 아님. 회귀 기대는 고정 증거를 실행 중에 읽음."""
import ast
import copy
import hashlib
import json
import socket
import sys
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PR120, PR120_EV, PR114_EV, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
SHA = {"pr120_code": "049342e8fa545f5092498eba8d19bc90cf1d850962f805bd0df61ba439384e93",      # PR120 · PR114 manifest file_sha256
       "pr120_evidence": "b7308516c2036cbcbc5f50cac3959f7713ea046e364d943eb39b90bae8945f70",
       "pr114_evidence": "ecfb7a757e8de81a06027c39d2119b2bcf4c46bbaf090f4226df23b0c9fe2ace"}
RAW = "RAW_UNADJUSTED"
LEDGER_PRICE_BASIS = RAW                                                         # 합성 장부 기준(고정)


def _ok_num(x):
    return not (x is None or isinstance(x, (bool, float))) and isinstance(x, (int, F)) and F(x) > 0


def canon_price(x):
    return str(F(x)) if isinstance(x, (int, F)) and not isinstance(x, bool) else "RAW:" + repr(x)


class QuoteLedger:
    def __init__(self, cash, positions):
        self.cash = F(cash)
        self.pos = {s: [F(q), F(p)] for s, (q, p) in positions.items()}
        self.applied, self.prov, self.snaps, self.blocked_from = {}, {}, [], None

    @staticmethod
    def key(ev):
        return (ev.get("sym"), ev.get("kind"), str(ev.get("m_qty")), ev.get("apply_date"))

    @staticmethod
    def payload(ev):
        return (canon_price(ev.get("m_price")), bool(ev.get("real")))

    @staticmethod
    def _k(k):
        return "|".join(map(str, k))

    @staticmethod
    def is_qm(m_qty, m_price):                                              # 수량변경 의미: 유효 역수 쌍 · m_qty ≠ 1 · kind 안 봄
        return _ok_num(m_qty) and _ok_num(m_price) and F(m_qty) * F(m_price) == 1 and F(m_qty) != 1

    def qm_syms(self):                                                      # 커밋된 레지스트리에서만 · 키의 m_qty + payload의 m_price
        return {k[0] for k, v in self.applied.items() if self.is_qm(F(k[2]), F(v[0]))}

    def state_hash(self):
        body = {"cash": str(self.cash), "pos": {s: [str(q), str(p)] for s, (q, p) in sorted(self.pos.items())},
                "applied": {self._k(k): list(v) for k, v in sorted(self.applied.items(), key=lambda kv: self._k(kv[0]))}}
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def prov_hash(self):
        body = {self._k(k): sorted(v) for k, v in self.prov.items()}
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def check(self, ev, day):
        if ev.get("real"):
            return "APPLY_BLOCKED_NO_PRICE_BASIS_DATE"
        if not ev.get("apply_date"):
            return "BLOCKED_APPLY_DATE_MISSING"
        if self.snaps and ev["apply_date"] < self.snaps[-1]["day"]:
            return "BLOCKED_ORDER"
        if ev["apply_date"] != day:
            return "BLOCKED_APPLY_DATE_MISMATCH"
        if not (_ok_num(ev.get("m_qty")) and _ok_num(ev.get("m_price"))):
            return "BLOCKED_INPUT"
        if ev.get("sym") not in self.pos:
            return "BLOCKED_UNKNOWN_SYMBOL"
        if F(ev["m_qty"]) * F(ev["m_price"]) != 1:
            return "BLOCKED_RATIO_PRODUCT"
        if (self.pos[ev["sym"]][0] * F(ev["m_qty"])).denominator != 1:
            return "BLOCKED_FRACTIONAL"
        return "OK"

    def apply_batch(self, day, events):
        bad = [ev for ev in events if ev.get("price_basis") != RAW]         # ⓪ 가격기준: 모든 계산 · 변경보다 먼저(수정 핵심)
        if bad:
            status = {self.key(ev): "BLOCKED_PRICE_BASIS" if ev.get("price_basis") != RAW else "NOT_EVALUATED" for ev in events}
            self.blocked_from = self.blocked_from or day
            h = self.state_hash(), self.prov_hash()
            return {"verdict": "BATCH_ABORTED", "status": status, "h0": h[0], "p0": h[1], "h1": h[0], "p1": h[1]}
        h0, p0 = self.state_hash(), self.prov_hash()
        qsyms = self.qm_syms()
        uniq, obs, same_conf, applied_conf, ambiguous = {}, {}, set(), set(), set()
        for ev in events:                                                   # ① 정규화 · 우선순위 1→2→3→4
            k, pl = self.key(ev), self.payload(ev)
            if k in self.applied:                                           # 1 · 2: 같은 키
                if self.applied[k] == pl:
                    obs.setdefault(k, set()).add(ev.get("src"))
                else:
                    applied_conf.add(k)
                continue
            if ev.get("sym") in qsyms and self.is_qm(ev.get("m_qty"), ev.get("m_price")):   # 3: prior QM 종목 + 다른 키 QM(수정 핵심)
                ambiguous.add(k)
                continue
            if k in uniq:
                if self.payload(uniq[k]) == pl:
                    obs.setdefault(k, set()).add(ev.get("src"))
                else:
                    same_conf.add(k)
                continue
            uniq[k] = ev
        status = {k: "BLOCKED_APPLIED_PAYLOAD_CONFLICT" for k in applied_conf}
        status.update({k: "BLOCKED_AMBIGUOUS_EVENT_IDENTITY" for k in ambiguous})
        sym_n = Counter(ev.get("sym") for ev in uniq.values())
        for k, ev in uniq.items():                                          # ② 4: S0 기준 선검증
            if k in same_conf:
                status[k] = "BLOCKED_KEY_PAYLOAD_CONFLICT"
            elif sym_n[ev.get("sym")] > 1:
                status[k] = "BLOCKED_SAME_SYMBOL_MULTI_EVENT"
            else:
                status[k] = self.check(ev, day)
        for k in obs:
            status.setdefault(k, "DUPLICATE_IGNORED")
        assert (self.state_hash(), self.prov_hash()) == (h0, p0)
        if any(v not in ("OK", "DUPLICATE_IGNORED") for v in status.values()):
            self.blocked_from = self.blocked_from or day                    # ③ 전체 중단
            return {"verdict": "BATCH_ABORTED", "status": status, "h0": h0, "p0": p0, "h1": self.state_hash(), "p1": self.prov_hash()}
        pos, app, prov = copy.deepcopy(self.pos), dict(self.applied), {k: set(v) for k, v in self.prov.items()}
        for k in sorted(uniq, key=self._k):                                 # ④ scratch: 수량 · 가격 · 레지스트리 · provenance 함께
            ev = uniq[k]
            q, p = pos[ev["sym"]]
            pos[ev["sym"]] = [q * F(ev["m_qty"]), p * F(ev["m_price"])]
            app[k] = self.payload(ev)
            prov.setdefault(k, set()).add(ev.get("src"))
        for k, srcs in obs.items():
            prov.setdefault(k, set()).update(srcs)
        for s in self.pos:
            assert pos[s][0] * pos[s][1] == self.pos[s][0] * self.pos[s][1] and pos[s][0].denominator == 1
        self.pos, self.applied, self.prov = pos, app, prov                  # ⑤ 한 번 커밋
        return {"verdict": "COMMITTED", "status": status, "h0": h0, "p0": p0, "h1": self.state_hash(), "p1": self.prov_hash()}

    def process_day(self, day, quotes, events):
        bad = sorted({str(it.get("sym")) for it in quotes if it.get("price_basis") != LEDGER_PRICE_BASIS})  # ⓪ 시세 기준: 하루의 첫 문장(수정 핵심)
        if not quotes or bad:
            self.blocked_from = self.blocked_from or day                    # 감사 표시(유일한 변경)
            return {"verdict": "DAY_BLOCKED", "reason": "BLOCKED_QUOTE_PRICE_BASIS", "bad_quote_syms": bad}
        res = self.apply_batch(day, events) if events else None
        for it in quotes:
            self.pos[it["sym"]][1] = F(it["price"])
        self.snaps.append({"day": day, "nav": self.cash + sum(q * p for q, p in self.pos.values()), "valid": self.blocked_from is None})
        return res

    def to_json(self):
        return json.dumps({"cash": str(self.cash), "pos": {s: [str(q), str(p)] for s, (q, p) in sorted(self.pos.items())},
                           "applied": [[list(k), list(v)] for k, v in sorted(self.applied.items(), key=lambda kv: self._k(kv[0]))],
                           "prov": [[list(k), sorted(v)] for k, v in sorted(self.prov.items(), key=lambda kv: self._k(kv[0]))],
                           "snaps": [{"day": s["day"], "nav": str(s["nav"]), "valid": s["valid"]} for s in self.snaps],
                           "blocked_from": self.blocked_from}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, s):
        d = json.loads(s)
        L = cls(F(d["cash"]), {})
        L.pos = {k: [F(q), F(p)] for k, (q, p) in d["pos"].items()}
        L.applied = {tuple(k): (v[0], bool(v[1])) for k, v in d["applied"]}
        L.prov = {tuple(k): set(v) for k, v in d["prov"]}
        L.snaps = [{"day": x["day"], "nav": F(x["nav"]), "valid": x["valid"]} for x in d["snaps"]]
        L.blocked_from = d["blocked_from"]
        return L


CALLS = Counter()                                                               # 지표 함수 호출 수(실행 근거)
NULL_METRICS = {"daily_returns": None, "monthly_twr": None, "mdd": None, "cost_after_return": None}


def _daily_returns(snaps):
    CALLS["daily_returns"] += 1
    return [snaps[i]["nav"] / snaps[i - 1]["nav"] - 1 for i in range(1, len(snaps))]


def _monthly_twr(snaps, r):
    CALLS["monthly_twr"] += 1
    acc = {}
    for i, x in enumerate(r, 1):
        m = snaps[i]["day"][:7]
        acc[m] = acc.get(m, F(1)) * (1 + x)
    return {m: v - 1 for m, v in acc.items()}


def _mdd(snaps):
    CALLS["mdd"] += 1
    peak, mdd = snaps[0]["nav"], F(0)
    for s in snaps:
        peak = max(peak, s["nav"])
        mdd = max(mdd, (peak - s["nav"]) / peak)
    return mdd


def perf_gate(ledger):
    blocked = ledger.blocked_from                                               # ⓪ 장부 차단 표식: 첫 문장(수정 핵심)
    if blocked is not None:
        return {"status": "PERF_BLOCKED", "from": blocked, "reason": "LEDGER_BLOCKED", **NULL_METRICS}
    bad = [s["day"] for s in ledger.snaps if not s["valid"]]
    if bad:
        return {"status": "PERF_BLOCKED", "from": bad[0], "reason": "INVALID_SNAPSHOT", **NULL_METRICS}
    snaps = ledger.snaps
    r = _daily_returns(snaps)
    mdd = _mdd(snaps)
    return {"status": "OK", "all_zero": all(x == 0 for x in r) and mdd == 0, "daily_returns": [str(x) for x in r],
            "monthly_twr": {m: str(v) for m, v in _monthly_twr(snaps, r).items()}, "mdd": str(mdd),
            "cost_after_return": None, "cost_model": "NOT_MODELED"}



POS = {"A": (37, 52300), "B": (75, 905)}
POS_C = {"A": (37, 52300), "B": (75, 905), "C": (40, 1000)}
DAYS = ["2026-01-28", "2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"]
A1 = {"sym": "A", "kind": "split", "m_qty": F(5), "m_price": F(1, 5), "apply_date": "2026-01-29", "src": "R1"}
AFTER = {"B": 4525, "C": 500}                                                   # 배치 뒤 합성 시세(값 보존)


def B_on(d):
    return {"sym": "B", "kind": "reverse_split", "m_qty": F(1, 5), "m_price": F(5), "apply_date": d, "src": "RB"}


def quotes(d, bday, in_batch, pos):
    q = {}
    if d != "2026-01-29":
        q["A"] = 52300 if d < "2026-01-29" else 10460
    for s in ("B", "C"):
        if s not in pos:
            continue
        if s not in in_batch:
            q[s] = pos[s][1]
        elif d != bday:
            q[s] = pos[s][1] if d < bday else AFTER[s]
    return [{"sym": s, "price": px, "price_basis": RAW} for s, px in q.items()]   # 하네스: 같은 값 · 같은 순서에 RAW 라벨


def run(Ledger, pos, bday, evs, order, reload, days=DAYS):
    L = Ledger(1_000_000, pos)
    res, blobs, trace = None, {}, []
    in_batch = {e["sym"] for e in evs} - {"A"}
    for d in days:
        today = [A1] if d == "2026-01-29" else []
        if d == bday:
            today = [evs[i] for i in order]
        r = L.process_day(d, quotes(d, bday, in_batch, pos), today)
        if d == bday:
            res = r
        if d == "2026-01-29" and reload:                                     # 직렬화 → 다시 읽기 → 계속
            s1 = L.to_json()
            L = Ledger.from_json(s1)
            blobs = {"bytes_equal_after_reload": L.to_json() == s1, "reload_sha256": hashlib.sha256(s1.encode()).hexdigest()}
        trace.append({"day": d, "state_hash": L.state_hash(), "prov_hash": L.prov_hash(), "snap": [str(L.snaps[-1]["nav"]), L.snaps[-1]["valid"]]})
    end = L.to_json()
    blobs["end_bytes_stable"] = Ledger.from_json(end).to_json() == end
    return L, res, blobs, trace


def field_mutations(Ledger, pos, bday, evs, order):
    """전날까지 돌린 장부에 apply_batch 한 번 → pos/applied/prov 칸 단위 비교(시세 반영 전)."""
    L = Ledger(1_000_000, pos)
    in_batch = {e["sym"] for e in evs} - {"A"}
    for d in DAYS:
        if d == bday:
            break
        L.process_day(d, quotes(d, bday, in_batch, pos), [A1] if d == "2026-01-29" else [])
    pos0, app0, prov0 = copy.deepcopy(L.pos), dict(L.applied), {k: set(v) for k, v in L.prov.items()}
    r = L.apply_batch(bday, [evs[i] for i in order])
    diffs = [f"pos.{s}.{i}" for s in pos0 for i in (0, 1) if pos0[s][i] != L.pos[s][i]]
    diffs += ["applied"] * (app0 != L.applied) + ["prov"] * (prov0 != L.prov)
    return {"order": list(order), "verdict": r["verdict"], "changed_fields": diffs, "blocked_from": L.blocked_from,
            "status": {QuoteLedger._k(k): v for k, v in sorted(r["status"].items(), key=lambda kv: QuoteLedger._k(kv[0]))}}


K = QuoteLedger._k
ORDERS = ((0, 1), (1, 0))


def full(Ledger, pos, bday, evs):
    runs = []
    for order in ORDERS:
        for reload in (False, True):
            L, r, blobs, trace = run(Ledger, pos, bday, evs, order, reload)
            cut_ok = all(run(Ledger, pos, bday, evs, order, reload, days=DAYS[:i + 1])[3] == trace[:i + 1] for i in range(len(DAYS)))
            runs.append({"order": list(order), "reload": reload, "verdict": r["verdict"],
                         "status": {K(k): v for k, v in sorted(r["status"].items(), key=lambda kv: K(kv[0]))},
                         "state_hash_before": r["h0"], "state_hash_after_batch": r["h1"], "prov_hash_before": r["p0"], "prov_hash_after_batch": r["p1"],
                         "final_state_hash": L.state_hash(), "final_prov_hash": L.prov_hash(),
                         "qty": {s: str(q) for s, (q, _) in sorted(L.pos.items())}, "applied_keys": sorted(K(k) for k in L.applied),
                         "prov_A": sorted(L.prov.get(QuoteLedger.key(A1), [])), "perf": perf_gate(L), "cut_test": cut_ok, **blobs})
    muts = [field_mutations(Ledger, pos, bday, evs, o) for o in ORDERS]
    r0 = runs[0]
    cmp = ("verdict", "status", "state_hash_before", "state_hash_after_batch", "prov_hash_before", "prov_hash_after_batch",
           "final_state_hash", "final_prov_hash", "qty", "perf")
    return {"runs": runs, "batch_field_mutations": muts,
            "order_and_reload_invariant": all(all(x[c] == r0[c] for c in cmp) for x in runs),
            "bytes_stable": all(x.get("bytes_equal_after_reload", True) and x["end_bytes_stable"] for x in runs),
            "cut_test": all(x["cut_test"] for x in runs)}


def ev_str(e):
    return {k: str(v) for k, v in e.items()}






# ── PR120 하네스 조각(글자 그대로 복사) ──
WATCH = ("pos", "applied", "prov", "cash", "snaps")


class Traced(QuoteLedger):
    """시험용: process_day 동안 apply_batch 호출 수 · WATCH 속성 대입 수를 셈(동작은 QuoteLedger 그대로)."""
    def __setattr__(self, k, v):
        if getattr(self, "_tracing", False) and k in WATCH:
            object.__setattr__(self, "_assign", self._assign + 1)
        object.__setattr__(self, k, v)

    def apply_batch(self, day, events):
        object.__setattr__(self, "_calls", self._calls + 1)
        return super().apply_batch(day, events)

    def process_day(self, day, quotes, events):
        object.__setattr__(self, "_assign", 0)
        object.__setattr__(self, "_calls", 0)
        object.__setattr__(self, "_tracing", True)
        try:
            return super().process_day(day, quotes, events)
        finally:
            object.__setattr__(self, "_tracing", False)



def look(L):
    return {"state_hash": L.state_hash(), "prov_hash": L.prov_hash(),
            "snaps_hash": hashlib.sha256(canon([[s["day"], str(s["nav"]), s["valid"]] for s in L.snaps]).encode()).hexdigest(),
            "applied_n": len(L.applied), "cash": str(L.cash), "pos": {s: [str(q), str(p)] for s, (q, p) in sorted(L.pos.items())},
            "qp": {s: str(q * p) for s, (q, p) in sorted(L.pos.items())}, "nav": str(L.cash + sum(q * p for q, p in L.pos.values())),
            "snaps_n": len(L.snaps), "prov_n": sum(len(v) for v in L.prov.values())}


def qi(sym, price, basis="__none__"):
    it = {"sym": sym, "price": price}
    if basis != "__none__":
        it["price_basis"] = basis
    return it


def day_case(Ledger, start, evs, quote_batch, reload=False):
    L = Ledger(0, start)
    rb = None
    if reload:
        s0 = L.to_json()
        L = Ledger.from_json(s0)
        rb = L.to_json() == s0
    before, deep0 = look(L), copy.deepcopy({k: getattr(L, k) for k in WATCH})
    r = L.process_day(D1, quote_batch, evs)
    after, deep1 = look(L), {k: getattr(L, k) for k in WATCH}
    if r is not None and r.get("verdict") in ("COMMITTED", "BATCH_ABORTED"):
        r = {"verdict": r["verdict"], "status": {QuoteLedger._k(k): v for k, v in sorted(r["status"].items(), key=lambda kv: QuoteLedger._k(kv[0]))}}
    return {"day_result": r, "before": before, "after": after, "changed_fields": [k for k in WATCH if deep0[k] != deep1[k]],
            "apply_batch_calls": getattr(L, "_calls", None), "watch_assignments": getattr(L, "_assign", None),
            "price_fields_changed": sum(before["pos"][s][1] != after["pos"][s][1] for s in before["pos"]),
            "snaps_delta": after["snaps_n"] - before["snaps_n"], "blocked_from": L.blocked_from,
            "nav_d0": before["nav"], "nav_d1": str(L.snaps[-1]["nav"]) if after["snaps_n"] > before["snaps_n"] else after["nav"],
            "bytes_sha256": hashlib.sha256(L.to_json().encode()).hexdigest(), "reload_bytes_equal": rb}



def parse_in(d):
    return {k: (F(v) if k in ("m_qty", "m_price") else v) for k, v in d.items()}


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)


# ── M8 정적 근거(ast) ──
tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
fdefs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
pg = fdefs["perf_gate"]
gate_ret = next(n.lineno for n in ast.walk(pg.body[1]) if isinstance(n, ast.Return))
metric_calls = [n.lineno for n in ast.walk(pg) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("_daily_returns", "_monthly_twr", "_mdd")]
pg_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "perf_gate"]
first = pg.body[0]
M8_static = {
    "no_perf_function": "perf" not in fdefs,
    "no_snapshot_only_perf": not [n for n, f in fdefs.items() if n.startswith("perf") and any(a.arg == "snaps" for a in f.args.args)],
    "signature_single_ledger": [a.arg for a in pg.args.args] == ["ledger"] and not pg.args.defaults and not pg.args.kwonlyargs
                               and pg.args.vararg is None and pg.args.kwarg is None,
    "first_statement_reads_blocked_from": isinstance(first, ast.Assign) and isinstance(first.value, ast.Attribute)
                                          and first.value.attr == "blocked_from" and getattr(first.value.value, "id", "") == "ledger",
    "gate_return_line": gate_ret, "metric_call_lines": sorted(metric_calls),
    "gate_before_metrics": bool(metric_calls) and gate_ret < min(metric_calls),
    "all_calls_single_arg": bool(pg_calls) and all(len(c.args) == 1 and not c.keywords for c in pg_calls), "perf_gate_call_sites": len(pg_calls)}
M8_static["pass"] = all(v for k, v in M8_static.items() if k not in ("gate_return_line", "metric_call_lines", "perf_gate_call_sites"))

# ── 고정본 · PR120 고정본(음성대조) ──
raw120, ev120_raw, ev114_raw = PR120.read_bytes(), PR120_EV.read_bytes(), PR114_EV.read_bytes()
sha_ok = {"pr120_code": hashlib.sha256(raw120).hexdigest() == SHA["pr120_code"], "pr120_evidence": hashlib.sha256(ev120_raw).hexdigest() == SHA["pr120_evidence"],
          "pr114_evidence": hashlib.sha256(ev114_raw).hexdigest() == SHA["pr114_evidence"]}
EV120, EV114 = json.loads(ev120_raw), json.loads(ev114_raw)
keep = sys.argv[:]
sys.argv = ["pr120", "/nonexistent", "/nonexistent", "/nonexistent", "/nonexistent"]
G = {"__name__": "pr120_prefix"}
exec(compile(raw120.decode("utf-8").split("\nPOS = ")[0], "PR120 quote_basis_gate.py(앞부분 · QuoteLedger · perf)", "exec"), G)
sys.argv = keep
OLD_LEDGER, OLD_PERF = G["QuoteLedger"], G["perf"]

D0, D1 = "2026-01-28", "2026-01-29"
SPLIT = {"sym": "A", "kind": "split", "m_qty": F(5), "m_price": F("0.2"), "apply_date": D1, "src": "P", "price_basis": RAW}
A_RAW = {"A": (37, 52300)}
BLOCK = lambda d, why: {"status": "PERF_BLOCKED", "from": d, "reason": why, **NULL_METRICS}


def gate(L):
    CALLS.clear()
    out = perf_gate(L)
    return out, sum(CALLS.values())


def reload_same(L):
    s = L.to_json()
    L2 = QuoteLedger.from_json(s)
    o1, _ = gate(L)
    o2, _ = gate(L2)
    return {"output_same": canon(o1) == canon(o2), "bytes_same": L2.to_json() == s, "bytes_sha256": hashlib.sha256(s.encode()).hexdigest()}


def build_last_day_block(Ledger):
    L = Ledger(0, A_RAW)
    L.process_day(D0, [qi("A", 52300, RAW)], [])
    r = L.process_day(D1, [qi("A", 10460, "ADJUSTED")], [])
    return L, r


M = {}
L1, r1 = build_last_day_block(OLD_LEDGER)
m1 = OLD_PERF(L1.snaps)
M["M1_negative_snapshot_only"] = {"day1": r1, "blocked_from": L1.blocked_from, "snaps": [[s["day"], s["valid"]] for s in L1.snaps], "old_perf": m1,
                                  "pass": m1 == {"status": "OK", "all_zero": True} and L1.blocked_from == D1 and [[s["day"], s["valid"]] for s in L1.snaps] == [[D0, True]]
                                  and r1.get("verdict") == "DAY_BLOCKED"}
L2, r2 = build_last_day_block(QuoteLedger)
o2, c2 = gate(L2)
M["M2_last_day_blocked"] = {"blocked_from": L2.blocked_from, "snaps": [[s["day"], s["valid"]] for s in L2.snaps], "perf_gate": o2, "metric_calls": c2,
                            "reload": reload_same(L2), "pass": o2 == BLOCK(D1, "LEDGER_BLOCKED") and c2 == 0}
L3 = QuoteLedger(0, A_RAW)
r3 = L3.process_day(D0, [qi("A", 52300, "ADJUSTED")], [])
o3, c3 = gate(L3)
try:
    old3 = OLD_PERF(L3.snaps)
except Exception as e:                                                          # 참고: 옛 함수는 스냅숏 0개에서 예외
    old3 = {"exception": type(e).__name__}
M["M3_first_day_blocked"] = {"day0": r3, "snaps_n": len(L3.snaps), "perf_gate": o3, "metric_calls": c3, "old_perf_info": old3, "reload": reload_same(L3),
                             "pass": o3 == BLOCK(D0, "LEDGER_BLOCKED") and c3 == 0 and len(L3.snaps) == 0}
L5 = QuoteLedger(0, A_RAW)
L5.process_day(D0, [qi("A", 52300, RAW)], [])
L5.process_day(D1, [qi("A", 52300, RAW)], [])
j = json.loads(L5.to_json())
j["snaps"][1]["valid"] = False
L5b = QuoteLedger.from_json(json.dumps(j, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
o5, c5 = gate(L5b)
M["M5_invalid_snapshot_without_flag"] = {"blocked_from": L5b.blocked_from, "snaps": [[s["day"], s["valid"]] for s in L5b.snaps], "perf_gate": o5, "metric_calls": c5,
                                         "reload": reload_same(L5b), "pass": o5 == BLOCK(D1, "INVALID_SNAPSHOT") and c5 == 0 and L5b.blocked_from is None}

# M4 · M6②: PR114 fixture(차단 8 · 정상 3) · 입력과 기대는 PR114 증거에서 읽음
A1 = dict(A1, price_basis=RAW)                                                   # 하네스 공통 첫 사건 라벨(PR118 · PR120과 같음)
RCMP = ("verdict", "status", "state_hash_before", "state_hash_after_batch", "prov_hash_before", "prov_hash_after_batch",
        "final_state_hash", "final_prov_hash", "qty", "applied_keys", "prov_A", "perf")
fx = {}
for group in ("fixtures", "regression_vs_pr112"):
    for name, old in EV114[group].items():
        evs = [dict(parse_in(e), price_basis=RAW) for e in old["inputs"]]
        pos = {s: (F(a), F(b)) for s, (a, b) in old["start_pos"].items()} if "start_pos" in old else (POS_C if any(e["sym"] == "C" for e in evs) else POS)
        CALLS.clear()
        res = full(QuoteLedger, pos, old["batch_day"], evs)
        calls = sum(CALLS.values())
        rep = canon(full(QuoteLedger, pos, old["batch_day"], evs)) == canon(res)
        oldruns = {(tuple(x["order"]), x["reload"]): x for x in old["runs"]}
        diffs = []
        for x in res["runs"]:
            o = oldruns[(tuple(x["order"]), x["reload"])]
            for f in RCMP:
                now = {k: x["perf"].get(k) for k in o["perf"]} if f == "perf" else x[f]
                if now != o[f]:
                    diffs.append({"order": x["order"], "reload": x["reload"], "field": f})
        ms = [m["changed_fields"] for m in res["batch_field_mutations"]] == [m["changed_fields"] for m in old["batch_field_mutations"]]
        blocked = oldruns[((0, 1), False)]["perf"]["status"] == "PERF_BLOCKED"
        if blocked:
            want = all(x["perf"] == BLOCK(old["batch_day"], "LEDGER_BLOCKED") for x in res["runs"]) and calls == 0
        else:
            want = all(x["perf"]["status"] == "OK" and x["perf"]["all_zero"] is True and x["perf"]["daily_returns"] is not None
                       and x["perf"]["monthly_twr"] is not None and x["perf"]["mdd"] is not None for x in res["runs"]) and calls > 0
        fx[name] = {"kind": "M4_blocked" if blocked else "M6_normal", "batch_day": old["batch_day"], "perf_gate_first_path": res["runs"][0]["perf"],
                    "metric_calls_in_full": calls, "diffs_vs_pr114_evidence": diffs, "mutations_same": ms, "invariant": res["order_and_reload_invariant"],
                    "bytes_stable": res["bytes_stable"], "cut_test": res["cut_test"], "repeat_identical": rep,
                    "pass": want and not diffs and ms and res["order_and_reload_invariant"] and res["bytes_stable"] and res["cut_test"] and rep}
m4 = {k: v for k, v in fx.items() if v["kind"] == "M4_blocked"}
m6b = {k: v for k, v in fx.items() if v["kind"] == "M6_normal"}
M["M4_event_batch_blocked_regression"] = {"fixtures": m4, "count": len(m4), "pass": len(m4) == 8 and all(v["pass"] for v in m4.values())}

# M6①: PR120 Q1_raw 같은 방식 재실행 · PR120 증거와 칸별 비교 + 같은 장부의 perf_gate
q1old = EV120["day_cases"]["Q1_raw"]["result"]
q1new = json.loads(canon(day_case(Traced, A_RAW, [SPLIT], [qi("A", 10460, RAW)])))
q1diff = sorted(k for k in set(q1old) | set(q1new) if q1old.get(k) != q1new.get(k))
L6 = QuoteLedger(0, A_RAW)
L6.process_day(D1, [qi("A", 10460, RAW)], [SPLIT])
o6, c6 = gate(L6)
m6a_ok = not q1diff and o6["status"] == "OK" and o6["all_zero"] is True and c6 == 3 and o6["daily_returns"] == [] and o6["monthly_twr"] == {} and o6["mdd"] == "0"
M["M6_raw_normal"] = {"pr120_Q1_raw": {"diff_fields": q1diff, "perf_gate": o6, "metric_calls": c6, "reload": reload_same(L6), "pass": m6a_ok},
                      "pr114_normal_fixtures": m6b, "pass": m6a_ok and len(m6b) == 3 and all(v["pass"] for v in m6b.values())}
M7 = {k: M[k]["reload"] for k in ("M2_last_day_blocked", "M3_first_day_blocked", "M5_invalid_snapshot_without_flag")}
M7["M6_pr120_Q1_raw"] = M["M6_raw_normal"]["pr120_Q1_raw"]["reload"]
M["M7_serialization"] = {"single_ledgers": M7, "fixture_invariants": {k: (v["invariant"], v["bytes_stable"], v["cut_test"], v["repeat_identical"]) for k, v in fx.items()},
                         "pass": all(v["output_same"] and v["bytes_same"] for v in M7.values()) and all(all(t) for t in
                                 [(v["invariant"], v["bytes_stable"], v["cut_test"], v["repeat_identical"]) for v in fx.values()])}
exec_zero = c2 == 0 and c3 == 0 and c5 == 0 and all(v["metric_calls_in_full"] == 0 for v in m4.values())
M["M8_call_boundary"] = {"static": M8_static, "blocked_metric_calls_zero": exec_zero, "pass": M8_static["pass"] and exec_zero}

summary = {"fixed_sha_ok": sha_ok, **{k: v["pass"] for k, v in M.items()}, "official_runs": 1, "actual_events": 0, "external_calls": 0,
           "performance_verified": False, "nav_verified": False, "paper_validation_ready": False}
summary["all_pass"] = all(sha_ok.values()) and all(v["pass"] for v in M.values())
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "blocked-day-metric-gate.json").write_text(json.dumps({"cases": M, "summary": summary}, ensure_ascii=False, indent=1, default=str))


def pg_txt(o):
    if o["status"] == "PERF_BLOCKED":
        return f"PERF_BLOCKED · from {o['from']} · {o['reason']} · 지표 " + ("모두 null" if all(o[k] is None for k in NULL_METRICS) else "값 있음")
    return f"OK · all_zero {o['all_zero']} · 일별 {o['daily_returns']} · 월 {o['monthly_twr']} · MDD {o['mdd']} · 비용후 {o['cost_after_return']}({o['cost_model']})"


rows = [("M1 음성(PR120 perf(snaps))", f"blocked_from {L1.blocked_from} · 스냅숏 {M['M1_negative_snapshot_only']['snaps']}", f"{m1}", "—", M["M1_negative_snapshot_only"]["pass"]),
        ("M2 마지막 날 차단", f"blocked_from {L2.blocked_from} · 스냅숏 {M['M2_last_day_blocked']['snaps']}", pg_txt(o2), c2, M["M2_last_day_blocked"]["pass"]),
        ("M3 첫날 차단", f"blocked_from {L3.blocked_from} · 스냅숏 0 · 옛 함수 {old3}", pg_txt(o3), c3, M["M3_first_day_blocked"]["pass"]),
        ("M5 표식 없음 + invalid", f"blocked_from {L5b.blocked_from} · 스냅숏 {M['M5_invalid_snapshot_without_flag']['snaps']}", pg_txt(o5), c5, M["M5_invalid_snapshot_without_flag"]["pass"]),
        ("M6 PR120 Q1_raw", f"PR120 증거와 다른 칸 {q1diff or 0}", pg_txt(o6), c6, m6a_ok)]
tables = ("## 단일 장부 케이스\n| # | 장부 상태 | 성과 출력 | 지표 함수 호출 | 통과 |\n|---|---|---|---|---|\n"
          + "\n".join(f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows)
          + "\n\n## M4 · M6 PR114 fixture(4경로)\n| fixture | 구분 | 성과 출력(경로 1) | 지표 호출 | PR114 증거와 다른 칸 | 4경로 · 바이트 · 자르기 · 반복 | 통과 |\n|---|---|---|---|---|---|---|\n"
          + "\n".join(f"| {k} | {v['kind']} | {pg_txt(v['perf_gate_first_path'])} | {v['metric_calls_in_full']} | {len(v['diffs_vs_pr114_evidence'])} | "
                      f"{v['invariant']} · {v['bytes_stable']} · {v['cut_test']} · {v['repeat_identical']} | {v['pass']} |" for k, v in fx.items())
          + f"\n\n## M7 직렬화(단일 장부)\n{json.dumps({k: (v['output_same'], v['bytes_same']) for k, v in M7.items()}, ensure_ascii=False)}\n"
          + f"\n## M8 호출 경계\n{json.dumps(M8_static, ensure_ascii=False)}\n차단 케이스 지표 호출 0: {exec_zero}\n")
(OUT / "tables.md").write_text(tables)
print(json.dumps({"summary": summary}, ensure_ascii=False))
print(tables)
