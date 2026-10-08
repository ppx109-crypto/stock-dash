"""REPLAY-CA-PRICE-BASIS-GATE-0001 · 가격기준 fail-closed 게이트(PR114 게이트 합성 복사본 + 첫 문장 검사) · P1~P5 고정 케이스(합성).
python3 -I price_basis_gate.py <PR114 quantity_mutation_gate.py 고정본> <PR114 증거 JSON 고정본> <출력 폴더>
RAW_UNADJUSTED만 기존 수량·가격 배수 경로로 들어감. 그 밖은 BLOCKED_PRICE_BASIS로 배치 전체 중단(변경 전).
정확 유리수 · 합성 종목/날짜 · 네트워크 함수 막음 · 라벨 추론 없음. 기대 문자열을 설명문에서 가져오지 않음 — P5 기대는 PR114 증거를 실행 중에 읽음."""
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
PR114, PR114_EV, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PR114_SHA = {"code": "babf0963aab966cdcb7f37f1f65a202534246af0b17797c3d79ca1d908acee74",      # PR114 manifest file_sha256
             "evidence": "ecfb7a757e8de81a06027c39d2119b2bcf4c46bbaf090f4226df23b0c9fe2ace"}
RAW = "RAW_UNADJUSTED"


def _ok_num(x):
    return not (x is None or isinstance(x, (bool, float))) and isinstance(x, (int, F)) and F(x) > 0


def canon_price(x):
    return str(F(x)) if isinstance(x, (int, F)) and not isinstance(x, bool) else "RAW:" + repr(x)


class BasisLedger:
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
        res = self.apply_batch(day, events) if events else None
        for s, px in quotes.items():
            self.pos[s][1] = F(px)
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
    return q


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
            "status": {BasisLedger._k(k): v for k, v in sorted(r["status"].items(), key=lambda kv: BasisLedger._k(kv[0]))}}


K = BasisLedger._k
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
                         "prov_A": sorted(L.prov.get(BasisLedger.key(A1), [])), "perf": perf(L.snaps), "cut_test": cut_ok, **blobs})
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


class Traced(BasisLedger):
    """시험용: apply_batch 동안 WATCH 속성 대입 횟수를 셈(동작은 BasisLedger 그대로)."""
    def __setattr__(self, k, v):
        if getattr(self, "_tracing", False) and k in WATCH:
            object.__setattr__(self, "_assign", self._assign + 1)
        object.__setattr__(self, k, v)

    def apply_batch(self, day, events):
        object.__setattr__(self, "_assign", 0)
        object.__setattr__(self, "_tracing", True)
        try:
            return super().apply_batch(day, events)
        finally:
            object.__setattr__(self, "_tracing", False)


# ── 코드 근거(정적): 가격기준 검사의 중단 return이 WATCH 속성 대입보다 앞 ──
tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
fn = next(n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "BasisLedger"
          for n in c.body if isinstance(n, ast.FunctionDef) and n.name == "apply_batch")
first_if = fn.body[1]
gate_return = next(n.lineno for n in ast.walk(first_if) if isinstance(n, ast.Return))


def _targets(n):
    ts = n.targets if isinstance(n, ast.Assign) else [n.target]
    for t in ts:
        for x in ([*t.elts] if isinstance(t, ast.Tuple) else [t]):
            if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == "self":
                yield x.attr


mut_lines = sorted(n.lineno for n in ast.walk(fn) if isinstance(n, (ast.Assign, ast.AugAssign)) and set(_targets(n)) & set(WATCH))
code_order = {"gate_is_first_statement": isinstance(fn.body[0], ast.Assign) and fn.body[0].targets[0].id == "bad" and isinstance(first_if, ast.If),
              "gate_return_line": gate_return, "first_watch_assign_line": mut_lines[0] if mut_lines else None, "watch_assign_lines": mut_lines}
code_order["gate_before_all_mutation"] = code_order["gate_is_first_statement"] and bool(mut_lines) and gate_return < mut_lines[0]

# ── 고정본 확인 · PR114 고정본 GateLedger(음성대조) ──
raw114, ev114_raw = PR114.read_bytes(), PR114_EV.read_bytes()
sha_ok = {"code": hashlib.sha256(raw114).hexdigest() == PR114_SHA["code"], "evidence": hashlib.sha256(ev114_raw).hexdigest() == PR114_SHA["evidence"]}
EV114 = json.loads(ev114_raw)
keep = sys.argv[:]
sys.argv = ["pr114", "/nonexistent", "/nonexistent", "/nonexistent"]
G = {"__name__": "pr114_prefix"}
exec(compile(raw114.decode("utf-8").split("\nPOS = ")[0], "PR114 quantity_mutation_gate.py(앞부분 · GateLedger)", "exec"), G)
sys.argv = keep
OLD = G["GateLedger"]

# ── P1~P4 ──
D0, D1 = "2026-01-28", "2026-01-29"
SPLIT = {"sym": "A", "kind": "split", "m_qty": F(5), "m_price": F("0.2"), "apply_date": D1, "src": "P"}


def look(L):
    return {"state_hash": L.state_hash(), "prov_hash": L.prov_hash(),
            "snaps_hash": hashlib.sha256(canon([[s["day"], str(s["nav"]), s["valid"]] for s in L.snaps]).encode()).hexdigest(),
            "applied_n": len(L.applied), "cash": str(L.cash), "pos": {s: [str(q), str(p)] for s, (q, p) in sorted(L.pos.items())},
            "qp": {s: str(q * p) for s, (q, p) in sorted(L.pos.items())}, "nav": str(L.cash + sum(q * p for q, p in L.pos.values()))}


def case(Ledger, start, evs, d1_quote):
    L = Ledger(0, start)
    L.process_day(D0, {s: p for s, (q, p) in start.items()}, [])
    before, deep0 = look(L), copy.deepcopy({k: getattr(L, k) for k in WATCH})
    r = L.apply_batch(D1, evs)
    after, deep1 = look(L), {k: getattr(L, k) for k in WATCH}
    changed = [k for k in WATCH if deep0[k] != deep1[k]]
    for s, px in d1_quote.items():                                           # process_day 꼬리와 같음: 시세 → 스냅숏
        L.pos[s][1] = F(px)
    L.snaps.append({"day": D1, "nav": L.cash + sum(q * p for q, p in L.pos.values()), "valid": L.blocked_from is None})
    return {"verdict": r["verdict"], "status": {BasisLedger._k(k): v for k, v in sorted(r["status"].items(), key=lambda kv: BasisLedger._k(kv[0]))},
            "before_batch": before, "after_batch": after, "changed_fields": changed,
            "watch_assignments": getattr(L, "_assign", None), "blocked_from": L.blocked_from, "d1_nav": str(L.snaps[-1]["nav"]),
            "d0_nav": str(L.snaps[0]["nav"])}


def unchanged(c):
    b, a = c["before_batch"], c["after_batch"]
    return all(b[k] == a[k] for k in ("state_hash", "prov_hash", "snaps_hash", "applied_n", "cash", "pos")) and c["changed_fields"] == [] \
        and c["watch_assignments"] == 0


KA = "A|split|5|2026-01-29"
KB = "B|reverse_split|1/5|2026-01-29"
P = {}
c = case(Traced, {"A": (37, 52300)}, [dict(SPLIT, price_basis=RAW)], {"A": 10460})
P["P1_raw_commit"] = {"result": c, "pass": c["verdict"] == "COMMITTED" and c["status"] == {KA: "OK"} and c["after_batch"]["pos"] == {"A": ["185", "10460"]}
                      and c["before_batch"]["qp"] == c["after_batch"]["qp"] == {"A": "1935100"} and c["after_batch"]["applied_n"] == 1
                      and c["d1_nav"] == "1935100"}
neg = case(OLD, {"A": (37, 10460)}, [dict(SPLIT, price_basis="ADJUSTED")], {"A": 10460})
new = case(Traced, {"A": (37, 10460)}, [dict(SPLIT, price_basis="ADJUSTED")], {"A": 10460})
P["P2_adjusted"] = {"negative_control_pr114": neg, "new_gate": new,
                    "negative_distortion": {"nav_before": neg["d0_nav"], "nav_after_adjusted_quote": neg["d1_nav"]},
                    "pass": neg["verdict"] == "COMMITTED" and neg["after_batch"]["pos"] == {"A": ["185", "2092"]}
                    and neg["d0_nav"] == "387020" and neg["d1_nav"] == "1935100"
                    and new["verdict"] == "BATCH_ABORTED" and new["status"] == {KA: "BLOCKED_PRICE_BASIS"} and unchanged(new)
                    and new["after_batch"]["pos"] == {"A": ["37", "10460"]} and new["d1_nav"] == "387020"}
sub = {}
for name, ev in (("P3a_missing", dict(SPLIT)), ("P3b_empty", dict(SPLIT, price_basis="")), ("P3c_other_string", dict(SPLIT, price_basis="raw_unadjusted"))):
    c = case(Traced, {"A": (37, 52300)}, [ev], {})
    sub[name] = {"result": c, "pass": c["verdict"] == "BATCH_ABORTED" and c["status"] == {KA: "BLOCKED_PRICE_BASIS"} and unchanged(c)
                 and c["after_batch"]["pos"] == {"A": ["37", "52300"]}}
P["P3_unknown"] = {"cases": sub, "pass": all(v["pass"] for v in sub.values())}
pair = [dict(SPLIT, price_basis=RAW), {"sym": "B", "kind": "reverse_split", "m_qty": F(1, 5), "m_price": F(5), "apply_date": D1, "src": "PB", "price_basis": "ADJUSTED"}]
p4 = {}
for order in ((0, 1), (1, 0)):
    c = case(Traced, {"A": (37, 52300), "B": (75, 905)}, [pair[i] for i in order], {})
    p4[str(list(order))] = {"result": c, "pass": c["verdict"] == "BATCH_ABORTED" and c["status"] == {KA: "NOT_EVALUATED", KB: "BLOCKED_PRICE_BASIS"}
                            and unchanged(c) and c["after_batch"]["pos"] == {"A": ["37", "52300"], "B": ["75", "905"]}}
P["P4_mixed_atomic"] = {"orders": p4, "pass": all(v["pass"] for v in p4.values())}

# ── P5: PR114 고정 fixture 11개 · 모든 사건 RAW_UNADJUSTED · PR114 증거와 칸별 비교 ──
A1 = dict(A1, price_basis=RAW)                                                   # 하네스 공통 첫 사건(01-29 A 분할)에도 라벨(의미키 · 해시 무관)
RCMP = ("verdict", "status", "state_hash_before", "state_hash_after_batch", "prov_hash_before", "prov_hash_after_batch",
        "final_state_hash", "final_prov_hash", "qty", "applied_keys", "prov_A", "perf")
p5 = {}
for group in ("fixtures", "regression_vs_pr112"):
    for name, old in EV114[group].items():
        evs = [dict(parse_in(e), price_basis=RAW) for e in old["inputs"]]
        if "start_pos" in old:
            pos = {s: (F(q), F(p)) for s, (q, p) in old["start_pos"].items()}
        else:
            pos = POS_C if any(e["sym"] == "C" for e in evs) else POS
        res = full(BasisLedger, pos, old["batch_day"], evs)
        repeat_same = canon(full(BasisLedger, pos, old["batch_day"], evs)) == canon(res)
        oldruns = {(tuple(x["order"]), x["reload"]): x for x in old["runs"]}
        diffs = [{"order": x["order"], "reload": x["reload"], "field": f, "pr114": oldruns[(tuple(x["order"]), x["reload"])][f], "now": x[f]}
                 for x in res["runs"] for f in RCMP if x[f] != oldruns[(tuple(x["order"]), x["reload"])][f]]
        mut_same = [m["changed_fields"] for m in res["batch_field_mutations"]] == [m["changed_fields"] for m in old["batch_field_mutations"]]
        p5[name] = {"pr114_group": group, "batch_day": old["batch_day"], "verdict": res["runs"][0]["verdict"], "status": res["runs"][0]["status"],
                    "qty": res["runs"][0]["qty"], "diffs_vs_pr114_evidence": diffs, "mutations_same_as_pr114": mut_same,
                    "invariant": res["order_and_reload_invariant"], "bytes_stable": res["bytes_stable"], "cut_test": res["cut_test"],
                    "repeat_identical": repeat_same,
                    "pass": not diffs and mut_same and res["order_and_reload_invariant"] and res["bytes_stable"] and res["cut_test"] and repeat_same}
P["P5_raw_regression"] = {"fixtures": p5, "diff_count": sum(len(v["diffs_vs_pr114_evidence"]) for v in p5.values()), "pass": all(v["pass"] for v in p5.values())}

summary = {"pr114_sha_ok": sha_ok, "code_order_gate_before_mutation": code_order["gate_before_all_mutation"],
           **{k: v["pass"] for k, v in P.items()}, "official_runs": 1, "actual_events": 0, "external_calls": 0,
           "performance_verified": False, "nav_verified": False, "paper_validation_ready": False}
summary["all_pass"] = all(sha_ok.values()) and code_order["gate_before_all_mutation"] and all(v["pass"] for v in P.values())
out = {"cases": P, "code_order": code_order, "summary": summary, "price_basis_allowed": [RAW]}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "price-basis-gate.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))


def brief(c):
    b, a = c["before_batch"], c["after_batch"]
    st = " · ".join(f"`{k}` {v}" for k, v in c["status"].items())
    same = "같음" if all(b[k] == a[k] for k in ("state_hash", "prov_hash", "snaps_hash", "applied_n", "cash")) else "바뀜"
    pos = " · ".join(f"{s} {q}@{p}" for s, (q, p) in a["pos"].items())
    return f"{c['verdict']} | {st} | {pos} | {same} | {','.join(c['changed_fields']) or '0'} | {c['watch_assignments']} | {c['d0_nav']} → {c['d1_nav']}"


rows = [("P1", P["P1_raw_commit"]["result"], P["P1_raw_commit"]["pass"]), ("P2 음성(PR114)", neg, P["P2_adjusted"]["pass"]),
        ("P2 새 게이트", new, P["P2_adjusted"]["pass"])] + [(k, v["result"], v["pass"]) for k, v in sub.items()] \
       + [(f"P4 순서 {k}", v["result"], v["pass"]) for k, v in p4.items()]
tables = ("## P1~P4(D1 배치)\n| # | 판정 | 키별 status | 배치 직후 수량@가격 | 배치 전후 state·prov·snap 해시 | 바뀐 칸 | 대입 횟수 | NAV D0 → D1 | 통과 |\n"
          "|---|---|---|---|---|---|---|---|---|\n" + "\n".join(f"| {n} | {brief(c)} | {ok} |" for n, c, ok in rows)
          + "\n\n## P5 RAW 회귀(PR114 증거와 칸별 비교)\n| fixture | 판정 | 수량 | 다른 칸 | 바뀐 칸 목록 같음 | 4경로 · 바이트 · 자르기 · 반복 | 통과 |\n|---|---|---|---|---|---|---|\n"
          + "\n".join(f"| {k} | {v['verdict']} | {' · '.join(f'{s} {q}' for s, q in v['qty'].items())} | {len(v['diffs_vs_pr114_evidence'])} | "
                      f"{v['mutations_same_as_pr114']} | {v['invariant']} · {v['bytes_stable']} · {v['cut_test']} · {v['repeat_identical']} | {v['pass']} |"
                      for k, v in p5.items())
          + f"\n\n## 코드 순서\n{json.dumps(code_order, ensure_ascii=False)}\n")
(OUT / "tables.md").write_text(tables)
print(json.dumps({"summary": summary}, ensure_ascii=False))
print(tables)
