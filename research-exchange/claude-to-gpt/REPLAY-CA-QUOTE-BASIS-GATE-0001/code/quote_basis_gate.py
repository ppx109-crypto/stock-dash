"""REPLAY-CA-QUOTE-BASIS-GATE-0001 · 시세 배치 가격기준 게이트(PR118 합성 복사본 · process_day 첫 문장) · Q1~Q8 고정 케이스(합성).
python3 -I quote_basis_gate.py <PR118 price_basis_gate.py 고정본> <PR118 증거 JSON> <PR114 증거 JSON> <출력 폴더>
시세 배치의 모든 항목이 RAW_UNADJUSTED일 때만 사건 → 시세 → 스냅숏. 그 밖은 DAY_BLOCKED(BLOCKED_QUOTE_PRICE_BASIS)로 하루 전체 중단.
정확 유리수 · 합성 종목/날짜 · 네트워크 함수 막음 · 라벨 추론 없음. Q7 기대는 고정 증거를 실행 중에 읽음."""
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
PR118, PR118_EV, PR114_EV, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
SHA = {"pr118_code": "e819ab86121564bef751c2ab5b767d2815b52caa938bdaad39492ed11c04676e",      # PR118 · PR114 manifest file_sha256
       "pr118_evidence": "7ba23f09aae5184ff56ca765e6591a26d94ce5fd0bcdec0f1987f192705de420",
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


def perf(snaps):
    bad = [s["day"] for s in snaps if not s["valid"]]
    if bad:
        return {"status": "PERF_BLOCKED", "from": bad[0]}
    r = [snaps[i]["nav"] / snaps[i - 1]["nav"] - 1 for i in range(1, len(snaps))]
    peak, mdd = snaps[0]["nav"], F(0)
    for s in snaps:
        peak = max(peak, s["nav"])
        mdd = max(mdd, (peak - s["nav"]) / peak)
    return {"status": "OK", "all_zero": all(x == 0 for x in r) and mdd == 0}



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
                         "prov_A": sorted(L.prov.get(QuoteLedger.key(A1), [])), "perf": perf(L.snaps), "cut_test": cut_ok, **blobs})
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





def parse_in(d):
    return {k: (F(v) if k in ("m_qty", "m_price") else v) for k, v in d.items()}


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)


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


# ── 코드 근거(ast): process_day 첫 두 문장이 검사 · 중단 return이 apply_batch · 시세 대입 · 스냅숏보다 앞 ──
tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
fn = next(n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "QuoteLedger"
          for n in c.body if isinstance(n, ast.FunctionDef) and n.name == "process_day")
gate_if = fn.body[1]
gate_return = next(n.lineno for n in ast.walk(gate_if) if isinstance(n, ast.Return))
apply_lines = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "apply_batch"]
quote_lines = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Assign) and any(
    isinstance(t, ast.Subscript) and isinstance(t.value, ast.Subscript) and isinstance(t.value.value, ast.Attribute) and t.value.value.attr == "pos"
    for t in n.targets)]
snap_lines = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
              and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == "snaps"]
code_order = {"gate_is_first_two_statements": isinstance(fn.body[0], ast.Assign) and getattr(fn.body[0].targets[0], "id", "") == "bad"
              and isinstance(gate_if, ast.If), "gate_return_line": gate_return, "apply_batch_lines": apply_lines, "quote_assign_lines": quote_lines,
              "snapshot_append_lines": snap_lines}
code_order["gate_before_all"] = code_order["gate_is_first_two_statements"] and bool(apply_lines and quote_lines and snap_lines) \
    and gate_return < min(apply_lines + quote_lines + snap_lines)

# ── 고정본 확인 · PR118 고정본(음성대조) ──
raw118, ev118_raw, ev114_raw = PR118.read_bytes(), PR118_EV.read_bytes(), PR114_EV.read_bytes()
sha_ok = {"pr118_code": hashlib.sha256(raw118).hexdigest() == SHA["pr118_code"], "pr118_evidence": hashlib.sha256(ev118_raw).hexdigest() == SHA["pr118_evidence"],
          "pr114_evidence": hashlib.sha256(ev114_raw).hexdigest() == SHA["pr114_evidence"]}
EV118, EV114 = json.loads(ev118_raw), json.loads(ev114_raw)
keep = sys.argv[:]
sys.argv = ["pr118", "/nonexistent", "/nonexistent", "/nonexistent"]
G = {"__name__": "pr118_prefix"}
exec(compile(raw118.decode("utf-8").split("\nPOS = ")[0], "PR118 price_basis_gate.py(앞부분 · BasisLedger)", "exec"), G)
sys.argv = keep
OLD = G["BasisLedger"]

# ── Q1~Q6: 하루(D1) 처리 ──
D0, D1 = "2026-01-28", "2026-01-29"
SPLIT = {"sym": "A", "kind": "split", "m_qty": F(5), "m_price": F("0.2"), "apply_date": D1, "src": "P", "price_basis": RAW}
KA = "A|split|5|2026-01-29"


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


def blocked_zero(c, bad):
    b, a = c["before"], c["after"]
    return c["day_result"] == {"verdict": "DAY_BLOCKED", "reason": "BLOCKED_QUOTE_PRICE_BASIS", "bad_quote_syms": bad} \
        and all(b[k] == a[k] for k in ("state_hash", "prov_hash", "snaps_hash", "applied_n", "cash", "pos", "snaps_n", "prov_n")) \
        and c["changed_fields"] == [] and c["apply_batch_calls"] == 0 and c["watch_assignments"] == 0 and c["price_fields_changed"] == 0 \
        and c["snaps_delta"] == 0 and c["blocked_from"] == D1


A_RAW = {"A": (37, 52300)}
A_ADJ = {"A": (37, 10460)}
AB = {"A": (37, 52300), "B": (75, 905)}
CASES = {   # 이름: (장부, 시작, 사건, 시세 배치, 막힐 종목)
    "Q1_raw": (Traced, A_RAW, [SPLIT], [qi("A", 10460, RAW)], None),
    "Q3_adjusted_quote": (Traced, A_ADJ, [SPLIT], [qi("A", 10460, "ADJUSTED")], ["A"]),
    "Q4a_missing": (Traced, A_RAW, [SPLIT], [qi("A", 10460)], ["A"]),
    "Q4b_empty": (Traced, A_RAW, [SPLIT], [qi("A", 10460, "")], ["A"]),
    "Q4c_other_string": (Traced, A_RAW, [SPLIT], [qi("A", 10460, "raw_unadjusted")], ["A"]),
    "Q5_mixed_order_AB": (Traced, AB, [], [qi("A", 52400, RAW), qi("B", 910, "ADJUSTED")], ["B"]),
    "Q5_mixed_order_BA": (Traced, AB, [], [qi("B", 910, "ADJUSTED"), qi("A", 52400, RAW)], ["B"]),
    "Q6_valid_event_bad_quote": (Traced, AB, [SPLIT], [qi("A", 10460, RAW), qi("B", 905, "ADJUSTED")], ["B"]),
}
R = {}
for name, (Lg, start, evs, qb, bad) in CASES.items():
    c = day_case(Lg, start, evs, qb)
    c_reload = day_case(Lg, start, evs, qb, reload=True)
    c_repeat = day_case(Lg, start, evs, qb)
    key = lambda x: canon([x["day_result"], x["after"]["state_hash"], x["after"]["prov_hash"], x["after"]["snaps_hash"], x["bytes_sha256"]])
    det = key(c) == key(c_reload) == key(c_repeat) and c_reload["reload_bytes_equal"] is True
    if bad is None:
        ok = c["day_result"] == {"verdict": "COMMITTED", "status": {KA: "OK"}} and c["after"]["pos"] == {"A": ["185", "10460"]} \
             and c["nav_d0"] == "1935100" and c["nav_d1"] == "1935100" and c["snaps_delta"] == 1 and c["after"]["applied_n"] == 1
    else:
        ok = blocked_zero(c, bad)
    R[name] = {"input_quotes": [{k: str(v) for k, v in it.items()} for it in qb], "input_events": len(evs), "result": c,
               "determinism": {"reload_and_repeat_identical": det}, "expect_pass": ok, "pass": ok and det}
r = R
r["Q3_adjusted_quote"]["pass"] &= r["Q3_adjusted_quote"]["result"]["after"]["pos"] == {"A": ["37", "10460"]} and r["Q3_adjusted_quote"]["result"]["nav_d1"] == "387020"
for n in ("Q4a_missing", "Q4b_empty", "Q4c_other_string"):
    r[n]["pass"] &= r[n]["result"]["after"]["pos"] == {"A": ["37", "52300"]}
for n in ("Q5_mixed_order_AB", "Q5_mixed_order_BA", "Q6_valid_event_bad_quote"):
    r[n]["pass"] &= r[n]["result"]["after"]["pos"] == {"A": ["37", "52300"], "B": ["75", "905"]}
r["Q6_valid_event_bad_quote"]["pass"] &= r["Q6_valid_event_bad_quote"]["result"]["after"]["applied_n"] == 0 and r["Q6_valid_event_bad_quote"]["result"]["after"]["prov_n"] == 0
q5_same = canon(R["Q5_mixed_order_AB"]["result"]["after"]) == canon(R["Q5_mixed_order_BA"]["result"]["after"]) \
    and R["Q5_mixed_order_AB"]["result"]["day_result"] == R["Q5_mixed_order_BA"]["result"]["day_result"]

# Q2 음성대조: PR118 고정본 · 사건 RAW · 시세는 (의도 ADJUSTED) 라벨 없는 dict
neg = day_case(OLD, A_ADJ, [SPLIT], {"A": 10460})
Q2 = {"intended_quote_label": "ADJUSTED", "result": neg, "nav_before": neg["nav_d0"], "nav_d1": neg["nav_d1"],
      "pass": neg["day_result"] == {"verdict": "COMMITTED", "status": {KA: "OK"}} and neg["nav_d0"] == "387020" and neg["nav_d1"] == "1935100"}

# ── Q7: PR118 P1 재실행(같은 방식) + PR114 fixture 11개 ──
p1old = EV118["cases"]["P1_raw_commit"]["result"]
L = Traced(0, A_RAW)
L.process_day(D0, [qi("A", 52300, RAW)], [])
b7, d7 = look(L), copy.deepcopy({k: getattr(L, k) for k in WATCH})
r7 = L.apply_batch(D1, [SPLIT])
a7 = look(L)
ch7 = [k for k in WATCH if d7[k] != getattr(L, k)]
L.pos["A"][1] = F(10460)
L.snaps.append({"day": D1, "nav": L.cash + sum(x * y for x, y in L.pos.values()), "valid": L.blocked_from is None})
p1new = {"verdict": r7["verdict"], "status": {QuoteLedger._k(k): v for k, v in r7["status"].items()},
         "before_batch": {k: b7[k] for k in p1old["before_batch"]}, "after_batch": {k: a7[k] for k in p1old["after_batch"]},
         "changed_fields": ch7, "d0_nav": str(L.snaps[0]["nav"]), "d1_nav": str(L.snaps[-1]["nav"])}
p1diff = [k for k in p1new if p1new[k] != p1old[k]]
A1 = dict(A1, price_basis=RAW)                                                   # 하네스 공통 첫 사건에도 라벨(의미키 · 해시 무관)
RCMP = ("verdict", "status", "state_hash_before", "state_hash_after_batch", "prov_hash_before", "prov_hash_after_batch",
        "final_state_hash", "final_prov_hash", "qty", "applied_keys", "prov_A", "perf")
q7 = {}
for group in ("fixtures", "regression_vs_pr112"):
    for name, old in EV114[group].items():
        evs = [dict(parse_in(e), price_basis=RAW) for e in old["inputs"]]
        pos = {s: (F(a), F(b)) for s, (a, b) in old["start_pos"].items()} if "start_pos" in old else (POS_C if any(e["sym"] == "C" for e in evs) else POS)
        res = full(QuoteLedger, pos, old["batch_day"], evs)
        rep = canon(full(QuoteLedger, pos, old["batch_day"], evs)) == canon(res)
        oldruns = {(tuple(x["order"]), x["reload"]): x for x in old["runs"]}
        diffs = [{"order": x["order"], "reload": x["reload"], "field": f} for x in res["runs"] for f in RCMP if x[f] != oldruns[(tuple(x["order"]), x["reload"])][f]]
        ms = [m["changed_fields"] for m in res["batch_field_mutations"]] == [m["changed_fields"] for m in old["batch_field_mutations"]]
        q7[name] = {"verdict": res["runs"][0]["verdict"], "qty": res["runs"][0]["qty"], "diffs_vs_pr114_evidence": diffs, "mutations_same": ms,
                    "invariant": res["order_and_reload_invariant"], "bytes_stable": res["bytes_stable"], "cut_test": res["cut_test"], "repeat_identical": rep,
                    "pass": not diffs and ms and res["order_and_reload_invariant"] and res["bytes_stable"] and res["cut_test"] and rep}
Q7 = {"pr118_P1": {"now": p1new, "diff_fields": p1diff, "pass": not p1diff}, "pr114_fixtures": q7,
      "diff_count": len(p1diff) + sum(len(v["diffs_vs_pr114_evidence"]) for v in q7.values()),
      "pass": not p1diff and all(v["pass"] for v in q7.values())}
Q8 = {"day_cases_reload_repeat": {k: v["determinism"]["reload_and_repeat_identical"] for k, v in R.items()}, "q5_order_independent": q5_same,
      "q7_fixture_invariants": {k: (v["invariant"], v["bytes_stable"], v["cut_test"], v["repeat_identical"]) for k, v in q7.items()}}
Q8["pass"] = all(Q8["day_cases_reload_repeat"].values()) and q5_same and all(all(t) for t in Q8["q7_fixture_invariants"].values())

summary = {"fixed_sha_ok": sha_ok, "code_order_gate_before_all": code_order["gate_before_all"],
           "Q1": R["Q1_raw"]["pass"], "Q2_negative": Q2["pass"], "Q3": R["Q3_adjusted_quote"]["pass"],
           "Q4": all(R[n]["pass"] for n in ("Q4a_missing", "Q4b_empty", "Q4c_other_string")),
           "Q5": R["Q5_mixed_order_AB"]["pass"] and R["Q5_mixed_order_BA"]["pass"] and q5_same, "Q6": R["Q6_valid_event_bad_quote"]["pass"],
           "Q7": Q7["pass"], "Q8": Q8["pass"], "official_runs": 1, "actual_events": 0, "external_calls": 0,
           "performance_verified": False, "nav_verified": False, "paper_validation_ready": False}
summary["all_pass"] = all(sha_ok.values()) and code_order["gate_before_all"] and all(summary[k] for k in ("Q1", "Q2_negative", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"))
out = {"day_cases": R, "Q2_negative_control_pr118": Q2, "Q7_raw_regression": Q7, "Q8_determinism": Q8, "code_order": code_order,
       "summary": summary, "ledger_price_basis": LEDGER_PRICE_BASIS}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "quote-basis-gate.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))


def row(n, c, ok):
    b, a = c["before"], c["after"]
    dr = c["day_result"]
    v = dr["verdict"] + (f" · {dr['reason']} · 막힌 {','.join(dr['bad_quote_syms'])}" if dr["verdict"] == "DAY_BLOCKED" else "")
    same = "같음" if all(b[k] == a[k] for k in ("state_hash", "prov_hash", "snaps_hash", "applied_n", "prov_n")) else "바뀜"
    pos = " · ".join(f"{s} {x}@{y}" for s, (x, y) in a["pos"].items())
    return (f"| {n} | {v} | {pos} | {same} | {','.join(c['changed_fields']) or '0'} | {c['apply_batch_calls']} | {c['watch_assignments']} | "
            f"{c['price_fields_changed']} | {c['snaps_delta']} | {c['nav_d0']} → {c['nav_d1']} | {ok} |")


tables = ("## Q1~Q6(D1 하루 처리)\n| # | 하루 판정 | 처리 뒤 수량@가격 | state·prov·snap 해시 | 바뀐 칸 | apply_batch 호출 | 대입 | 가격 변경 칸 | 스냅숏 증가 | NAV D0 → D1 | 통과 |\n"
          "|---|---|---|---|---|---|---|---|---|---|---|\n"
          + "\n".join([row("Q1", R["Q1_raw"]["result"], R["Q1_raw"]["pass"]), row("Q2 음성(PR118)", neg, Q2["pass"])]
                      + [row(k, v["result"], v["pass"]) for k, v in R.items() if k != "Q1_raw"])
          + f"\n\nQ5 두 순서 결과 같음: {q5_same}\n\n## Q7 RAW 회귀\n- PR118 P1: 다른 칸 {p1diff or '0'} · 통과 {not p1diff}\n\n"
          "| PR114 fixture | 판정 | 수량 | 다른 칸 | 바뀐 칸 목록 같음 | 4경로 · 바이트 · 자르기 · 반복 | 통과 |\n|---|---|---|---|---|---|---|\n"
          + "\n".join(f"| {k} | {v['verdict']} | {' · '.join(f'{s} {x}' for s, x in v['qty'].items())} | {len(v['diffs_vs_pr114_evidence'])} | {v['mutations_same']} | "
                      f"{v['invariant']} · {v['bytes_stable']} · {v['cut_test']} · {v['repeat_identical']} | {v['pass']} |" for k, v in q7.items())
          + f"\n\n## Q8 결정성\n{json.dumps({k: v for k, v in Q8.items() if k != 'q7_fixture_invariants'}, ensure_ascii=False)}\n\n## 코드 순서\n{json.dumps(code_order, ensure_ascii=False)}\n")
(OUT / "tables.md").write_text(tables)
print(json.dumps({"summary": summary}, ensure_ascii=False))
print(tables)
