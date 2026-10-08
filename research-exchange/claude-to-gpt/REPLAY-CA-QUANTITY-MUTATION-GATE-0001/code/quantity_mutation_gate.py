"""REPLAY-CA-QUANTITY-MUTATION-GATE-0001 · kind와 무관한 수량변경 게이트 · K1~K3/Q1~Q4 회귀 · 경로/반복 불변 · PR112 음성대조군(합성).
python3 -I quantity_mutation_gate.py <PR112 kind_flip_quarantine.py 고정본> <PR112 증거 JSON 고정본> <출력 폴더>
정확 유리수 · 합성 종목/날짜 · 네트워크 함수 막음. 게이트는 동일성 증명이 아니라 임시 fail-closed.
kind 목록 없음. 결과 사유를 미리 적은 설명 글자 없음 — 회귀 · I1 기대는 PR112 증거 JSON 구조화 값을 실행 중에 읽음."""
import copy
import hashlib
import json
import socket
import sys
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PR112, PR112_EV, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PR112_SHA = {"code": "14317e97ee289279b56a1d6ec10550e41b78fa0234726ecaf531b7f67ed9e553",      # PR112 manifest file_sha256
             "evidence": "b9956807229b579519bcbbc04f6fa503919ad840ce9b1dbf0956c4bdd8122ed8"}


def _ok_num(x):
    return not (x is None or isinstance(x, (bool, float))) and isinstance(x, (int, F)) and F(x) > 0


def canon_price(x):
    return str(F(x)) if isinstance(x, (int, F)) and not isinstance(x, bool) else "RAW:" + repr(x)


class GateLedger:
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
            "status": {GateLedger._k(k): v for k, v in sorted(r["status"].items(), key=lambda kv: GateLedger._k(kv[0]))}}


K = GateLedger._k
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
                         "prov_A": sorted(L.prov.get(GateLedger.key(A1), [])), "perf": perf(L.snaps), "cut_test": cut_ok, **blobs})
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


# ── 고정본 확인 ──
raw112, ev112_raw = PR112.read_bytes(), PR112_EV.read_bytes()
sha_ok = {"code": hashlib.sha256(raw112).hexdigest() == PR112_SHA["code"], "evidence": hashlib.sha256(ev112_raw).hexdigest() == PR112_SHA["evidence"]}
EV112 = json.loads(ev112_raw)
I1_IN = parse_in(EV112["informational"]["I1_bonus_issue_outside_family"]["input"])     # 정확 입력: PR112 증거에서 읽음

# ── M1~M4 ──
MFIX = {
    "M1_bonus_issue": (POS, "2026-02-02", [I1_IN, B_on("2026-02-02")]),
    "M2_unknown_kind": (POS, "2026-02-02", [dict(I1_IN, kind="unknown_qty_event", src="RU"), B_on("2026-02-02")]),
    "M3_later_legit_looking_second_qm": (POS, "2026-02-03", [dict(I1_IN, apply_date="2026-02-03", src="R7"), B_on("2026-02-03")]),
    "M4_new_symbol_first_qm": (POS_C, "2026-01-30", [{"sym": "C", "kind": "bonus_issue", "m_qty": F(2), "m_price": F(1, 2), "apply_date": "2026-01-30", "src": "RC"},
                                                     B_on("2026-01-30")]),
}
results = {}
for name, (pos, bday, evs) in MFIX.items():
    res = full(GateLedger, pos, bday, evs)
    repeat_same = canon(full(GateLedger, pos, bday, evs)) == canon(res)            # 반복 실행
    r0, keys = res["runs"][0], [K(GateLedger.key(e)) for e in evs]
    if name.startswith("M4"):
        ok = r0["verdict"] == "COMMITTED" and r0["status"] == {k: "OK" for k in keys} \
             and r0["qty"] == {"A": "185", "B": "15", "C": "80"} and r0["perf"].get("all_zero") is True
    else:
        ok = r0["verdict"] == "BATCH_ABORTED" and r0["status"] == {keys[0]: "BLOCKED_AMBIGUOUS_EVENT_IDENTITY", keys[1]: "OK"} \
             and r0["qty"] == {"A": "185", "B": "75"} and r0["applied_keys"] == [K(GateLedger.key(A1))] and r0["prov_A"] == ["R1"] \
             and all(x["state_hash_after_batch"] == x["state_hash_before"] and x["prov_hash_after_batch"] == x["prov_hash_before"] for x in res["runs"]) \
             and r0["perf"] == {"status": "PERF_BLOCKED", "from": bday} \
             and all(m["verdict"] == "BATCH_ABORTED" and m["changed_fields"] == [] for m in res["batch_field_mutations"])
    results[name] = {"batch_day": bday, "start_pos": {s: [str(q), str(p)] for s, (q, p) in pos.items()}, "inputs": [ev_str(e) for e in evs],
                     "expect_pass": ok, **res, "repeat_identical": repeat_same,
                     "pass": ok and res["order_and_reload_invariant"] and res["bytes_stable"] and res["cut_test"] and repeat_same}
results["M3_later_legit_looking_second_qm"]["needs_data"] = True

# ── K1~K3 · Q1~Q4 회귀: 입력과 기대 모두 PR112 증거 JSON에서 읽음 ──
RCMP = ("verdict", "status", "state_hash_before", "state_hash_after_batch", "prov_hash_before", "prov_hash_after_batch",
        "final_state_hash", "final_prov_hash", "qty", "applied_keys", "prov_A", "perf")
regress = {}
for group in ("fixtures", "q_regression"):
    for name, old in EV112[group].items():
        pos = {s: (F(q), F(p)) for s, (q, p) in old["start_pos"].items()} if "start_pos" in old else POS
        evs = [parse_in(e) for e in old["inputs"]]
        res = full(GateLedger, pos, old["batch_day"], evs)
        repeat_same = canon(full(GateLedger, pos, old["batch_day"], evs)) == canon(res)
        oldruns = {(tuple(x["order"]), x["reload"]): x for x in old["runs"]}
        diffs = [{"order": x["order"], "reload": x["reload"], "field": c, "pr112": oldruns[(tuple(x["order"]), x["reload"])][c], "now": x[c]}
                 for x in res["runs"] for c in RCMP if x[c] != oldruns[(tuple(x["order"]), x["reload"])][c]]
        mut_same = [m["changed_fields"] for m in res["batch_field_mutations"]] == [m["changed_fields"] for m in old["batch_field_mutations"]]
        regress[name] = {"pr112_group": group, "batch_day": old["batch_day"], "inputs": old["inputs"], **res, "repeat_identical": repeat_same,
                         "diffs_vs_pr112_evidence": diffs, "mutations_same_as_pr112": mut_same,
                         "pass": not diffs and mut_same and res["order_and_reload_invariant"] and res["bytes_stable"] and res["cut_test"] and repeat_same}

# ── 음성대조군: PR112 고정본 FamilyLedger ──
src = raw112.decode("utf-8").split("\nPOS = ")[0]
keep = sys.argv[:]
sys.argv = ["pr112", "/nonexistent", "/nonexistent", "/nonexistent"]
G = {"__name__": "pr112_prefix"}
exec(compile(src, "PR112 kind_flip_quarantine.py(앞부분 · FamilyLedger)", "exec"), G)
sys.argv = keep
FL = G["FamilyLedger"]
i1_ev = EV112["informational"]["I1_bonus_issue_outside_family"]                # 기대 출처: 구조화 증거
iL, ir, _, _ = run(FL, POS, "2026-02-02", [I1_IN], (0,), False)
neg = {"I1_exact": {"expect_from_pr112_evidence": {k: i1_ev[k] for k in ("verdict", "status", "A_qty")},
                    "observed": {"verdict": ir["verdict"], "status": {K(k): v for k, v in ir["status"].items()}, "A_qty": str(iL.pos["A"][0])}}}
neg["I1_exact"]["match"] = neg["I1_exact"]["observed"] == neg["I1_exact"]["expect_from_pr112_evidence"]
NEG_EXP = {"M1_bonus_issue": {"A": "370", "B": "15"}, "M2_unknown_kind": {"A": "370", "B": "15"},
           "M3_later_legit_looking_second_qm": {"A": "370", "B": "15"}, "M4_new_symbol_first_qm": {"A": "185", "B": "15", "C": "80"}}   # 유도
for name, (pos, bday, evs) in MFIX.items():
    per = []
    for order in ORDERS:
        L, r, _, _ = run(FL, pos, bday, evs, order, False)
        per.append({"order": list(order), "verdict": r["verdict"], "status": {K(k): v for k, v in sorted(r["status"].items(), key=lambda kv: K(kv[0]))},
                    "qty": {s: str(q) for s, (q, _) in sorted(L.pos.items())}})
    neg[name] = {"runs": per, "expect_derived": {"verdict": "COMMITTED", "all_status_OK": True, "qty": NEG_EXP[name]},
                 "match": all(p["verdict"] == "COMMITTED" and set(p["status"].values()) == {"OK"} and p["qty"] == NEG_EXP[name] for p in per)}

# ── 참고(판정 제외): QM이 아닌 후보 ──
info = {}
for name, ev in {"N1_non_qm_identity_ratio": dict(A1, kind="name_change", m_qty=F(1), m_price=F(1), apply_date="2026-02-02", src="RN"),
                 "N2_bad_ratio_not_qm": dict(A1, kind="bonus_issue", m_qty=F(2), m_price=F(1, 4), apply_date="2026-02-02", src="RX")}.items():
    nL, nr, _, _ = run(GateLedger, POS, "2026-02-02", [ev], (0,), False)
    info[name] = {"input": ev_str(ev), "verdict": nr["verdict"], "status": {K(k): v for k, v in nr["status"].items()}, "A_qty": str(nL.pos["A"][0])}

summary = {"pr112_sha_ok": sha_ok, "m_fixtures_pass": all(v["pass"] for v in results.values()),
           "regression_pass": all(v["pass"] for v in regress.values()),
           "regression_diff_count": sum(len(v["diffs_vs_pr112_evidence"]) for v in regress.values()),
           "neg_I1_match": neg["I1_exact"]["match"], "neg_derived_match": all(neg[n]["match"] for n in MFIX),
           "m3_false_positive_blocked": results["M3_later_legit_looking_second_qm"]["runs"][0]["verdict"] == "BATCH_ABORTED",
           "actual_events": 0, "external_calls": 0, "performance_verified": False, "paper_validation_ready": False}
summary["all_pass"] = all(sha_ok.values()) and summary["m_fixtures_pass"] and summary["regression_pass"] and summary["neg_I1_match"] and summary["neg_derived_match"]
out = {"fixtures": results, "regression_vs_pr112": regress, "pre_fix_negative_control": neg, "informational": info, "summary": summary,
       "gate": "qm(m_qty, m_price) = 유효 양의 유리수 · m_qty*m_price == 1 · m_qty != 1 (kind 무관)"}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "quantity-mutation-gate.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))

# ── 보고서용 표: 증거 값에서 바로 만듦 ──
def row(name, v):
    r0 = v["runs"][0]
    st = " · ".join(f"`{k}` {s}" for k, s in r0["status"].items())
    hs = "같음" if r0["state_hash_before"] == r0["state_hash_after_batch"] and r0["prov_hash_before"] == r0["prov_hash_after_batch"] else "바뀜"
    mu = " / ".join(",".join(m["changed_fields"]) or "0" for m in v["batch_field_mutations"])
    qt = " · ".join(f"{s} {q}" for s, q in r0["qty"].items())
    pf = r0["perf"]["status"] + (f"({r0['perf']['from']})" if "from" in r0["perf"] else (" · 0" if r0["perf"].get("all_zero") else ""))
    return (f"| {name} | {v['batch_day']} | {r0['verdict']} | {st} | {qt} | {hs} | {mu} | {pf} | "
            f"{v['order_and_reload_invariant']} · {v['repeat_identical']} · {v['bytes_stable']} · {v['cut_test']} | {v['pass']} |")


hdr = ("| # | 배치 | 판정 | 키별 status | 수량 | 배치 전후 state·prov 해시 | 바뀐 칸(순서 1 / 2) | 성과 | 4경로 · 반복 · 바이트 · 자르기 | 통과 |\n"
       "|---|---|---|---|---|---|---|---|---|---|")
neg_rows = [f"| I1 그대로 | {neg['I1_exact']['observed']['verdict']} | " + " · ".join(f"`{k}` {s}" for k, s in neg['I1_exact']['observed']['status'].items())
            + f" | A {neg['I1_exact']['observed']['A_qty']} | PR112 증거 | {neg['I1_exact']['match']} |"]
for name in MFIX:
    p = neg[name]["runs"][0]
    neg_rows.append(f"| {name} | {p['verdict']} | " + " · ".join(f"`{k}` {s}" for k, s in p["status"].items()) + " | "
                    + " · ".join(f"{s} {q}" for s, q in p["qty"].items()) + f" | 유도 | {neg[name]['match']} |")
tables = ("## M1~M4\n" + hdr + "\n" + "\n".join(row(n, v) for n, v in results.items())
          + "\n\n## K1~K3 · Q1~Q4 회귀(PR112 증거와 칸별 비교)\n" + hdr + "\n" + "\n".join(row(n, v) for n, v in regress.items())
          + "\n\nPR112 증거와 다른 칸 수: " + ", ".join(f"{n} {len(v['diffs_vs_pr112_evidence'])}" for n, v in regress.items())
          + "\n\n## 음성대조군(PR112 고정본 · 순서 1)\n| 입력 | 판정 | 키별 status | 수량 | 기대 출처 | 일치 |\n|---|---|---|---|---|---|\n" + "\n".join(neg_rows)
          + "\n\n## 참고 N1 · N2(판정 제외)\n" + json.dumps(info, ensure_ascii=False) + "\n")
(OUT / "tables.md").write_text(tables)
print(json.dumps({"summary": summary}, ensure_ascii=False))
print(tables)
