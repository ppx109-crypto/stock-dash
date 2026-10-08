"""REPLAY-CA-APPLIED-PAYLOAD-PROVENANCE-0001 · 적용 레지스트리 key→payload · provenance · 직렬화 왕복 · 순서 불변(합성).
python3 -I payload_registry.py <PR106 batch_atomicity.py 고정본> <출력 폴더>
정확 유리수 · 합성 종목/날짜 · 네트워크 함수 막음."""
import copy
import hashlib
import itertools
import json
import socket
import sys
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PR106, OUT = Path(sys.argv[1]), Path(sys.argv[2])


def _ok_num(x):
    return not (x is None or isinstance(x, (bool, float))) and isinstance(x, (int, F)) and F(x) > 0


def canon_price(x):
    return str(F(x)) if isinstance(x, (int, F)) and not isinstance(x, bool) else "RAW:" + repr(x)


class PayloadLedger:
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
        uniq, obs, same_conf, applied_conf = {}, {}, set(), set()
        for ev in events:                                                   # ① 정규화
            k, pl = self.key(ev), self.payload(ev)
            if k in self.applied:                                           # 이미 적용된 키: 내용 비교(수정 핵심)
                if self.applied[k] == pl:
                    obs.setdefault(k, set()).add(ev.get("src"))
                else:
                    applied_conf.add(k)
                continue
            if k in uniq:
                if self.payload(uniq[k]) == pl:
                    obs.setdefault(k, set()).add(ev.get("src"))
                else:
                    same_conf.add(k)
                continue
            uniq[k] = ev
        status = {k: "BLOCKED_APPLIED_PAYLOAD_CONFLICT" for k in applied_conf}
        sym_n = Counter(ev.get("sym") for ev in uniq.values())
        for k, ev in uniq.items():                                          # ② S0 기준 선검증
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
DAYS = ["2026-01-28", "2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"]
A1 = {"sym": "A", "kind": "split", "m_qty": F(5), "m_price": F(1, 5), "apply_date": "2026-01-29", "src": "R1"}
B1 = {"sym": "B", "kind": "reverse_split", "m_qty": F(1, 5), "m_price": F(5), "apply_date": "2026-01-30", "src": "RB"}
VAR = {"P1_same_payload_other_src": dict(A1, src="R2"), "P2_changed_m_price": dict(A1, m_price=F(1, 4), src="R3"),
       "P3_changed_real": dict(A1, real=True, src="R4")}
EXPECT = {"P1_same_payload_other_src": "COMMITTED", "P2_changed_m_price": "BATCH_ABORTED", "P3_changed_real": "BATCH_ABORTED"}


def quotes(d, a_applied=True):
    q = {}
    if d != "2026-01-29":
        q["A"] = 52300 if d < "2026-01-29" else 10460
    if d != "2026-01-30":
        q["B"] = 905 if d < "2026-01-30" else 4525
    return q


def run(Ledger, var, order, reload, extra=None):
    L = Ledger(1_000_000, POS)
    res, blobs = None, {}
    for d in DAYS:
        evs = []
        if d == "2026-01-29":
            evs = [A1]
        if d == "2026-01-30" and var is not None:
            pair = [var, B1]
            evs = [pair[i] for i in order]
        if extra and d in extra:
            evs = extra[d]
        r = L.process_day(d, quotes(d), evs)
        if d == "2026-01-29" and reload:                                     # 직렬화 → 다시 읽기 → 계속
            s1 = L.to_json()
            L = Ledger.from_json(s1)
            blobs = {"bytes_equal_after_reload": L.to_json() == s1, "sha256": hashlib.sha256(s1.encode()).hexdigest()}
        if d == "2026-01-30" and var is not None:
            res = r
        if extra and d in extra:
            res = r
    return L, res, blobs


results = {}
for name, var in VAR.items():
    runs = []
    for order in ((0, 1), (1, 0)):
        for reload in (False, True):
            L, r, blobs = run(PayloadLedger, var, order, reload)
            runs.append({"order": list(order), "reload": reload, "verdict": r["verdict"],
                         "status": {PayloadLedger._k(k): v for k, v in sorted(r["status"].items(), key=lambda kv: PayloadLedger._k(kv[0]))},
                         "state_hash_before": r["h0"], "state_hash_after_batch": r["h1"], "prov_hash_before": r["p0"], "prov_hash_after_batch": r["p1"],
                         "final_state_hash": L.state_hash(), "final_prov_hash": L.prov_hash(), "qty": {s: str(q) for s, (q, _) in L.pos.items()},
                         "prov_A": sorted(L.prov.get(PayloadLedger.key(A1), [])), "perf": perf(L.snaps), **blobs})
    r0 = runs[0]
    same = all((x["verdict"], x["status"], x["state_hash_after_batch"], x["prov_hash_after_batch"], x["final_state_hash"], x["final_prov_hash"], x["perf"]) ==
               (r0["verdict"], r0["status"], r0["state_hash_after_batch"], r0["prov_hash_after_batch"], r0["final_state_hash"], r0["final_prov_hash"], r0["perf"]) for x in runs)
    reload_bytes = all(x.get("bytes_equal_after_reload", True) for x in runs)
    akey = PayloadLedger._k(PayloadLedger.key(A1))
    if EXPECT[name] == "COMMITTED":
        ok = r0["verdict"] == "COMMITTED" and r0["status"][akey] == "DUPLICATE_IGNORED" and r0["qty"] == {"A": "185", "B": "15"} \
             and r0["prov_A"] == ["R1", "R2"] and r0["perf"].get("all_zero") is True
    else:
        ok = r0["verdict"] == "BATCH_ABORTED" and r0["status"][akey] == "BLOCKED_APPLIED_PAYLOAD_CONFLICT" and r0["qty"]["B"] == "75" \
             and all(x["state_hash_after_batch"] == x["state_hash_before"] and x["prov_hash_after_batch"] == x["prov_hash_before"] for x in runs) \
             and r0["perf"] == {"status": "PERF_BLOCKED", "from": "2026-01-30"} and r0["prov_A"] == ["R1"]
    results[name] = {"expect": EXPECT[name], "runs": runs, "order_and_reload_invariant": same, "reload_bytes_stable": reload_bytes,
                     "pass": ok and same and reload_bytes}

# ── 수정 전 음성대조군: PR #106 고정본 BatchLedger ──
src = PR106.read_text(encoding="utf-8").split("\nPOS = ")[0]
keep = sys.argv[:]
sys.argv = ["pr106", "/nonexistent", "/nonexistent"]
G = {"__name__": "pr106_prefix"}
exec(compile(src, "PR106 batch_atomicity.py(앞부분 · BatchLedger)", "exec"), G)
sys.argv = keep
neg = {}
for name in ("P2_changed_m_price", "P3_changed_real"):
    per = []
    for order in ((0, 1), (1, 0)):
        L, r, _ = run(G["BatchLedger"], VAR[name], order, False)
        akey = ("A", "split", "5", "2026-01-29")
        per.append({"order": list(order), "verdict": r["verdict"], "A_status": r["status"].get(akey), "B_qty": str(L.pos["B"][0])})
    neg[name] = {"runs": per, "defect_reproduced": all(p["A_status"] == "DUPLICATE_IGNORED" and p["verdict"] == "COMMITTED" and p["B_qty"] == "15" for p in per)}

# ── 참고 시험(판정 제외) ──
g1L, g1r, _ = run(PayloadLedger, None, (0,), False, extra={"2026-02-02": [dict(A1, apply_date="2026-02-02", src="R9-일정정정")]})
g2L, g2r, _ = run(PayloadLedger, None, (0,), False, extra={"2026-01-30": [dict(A1, m_qty=F(10), m_price=F(1, 10), src="R8-비율정정")]})
gaps = {"G1_apply_date_changed": {"verdict": g1r["verdict"], "status": {PayloadLedger._k(k): v for k, v in g1r["status"].items()}, "A_qty": str(g1L.pos["A"][0]),
                                  "note": "의미키에 apply_date가 있어 새 사건으로 보임 → 두 번 적용(남은 위험)"},
        "G2_m_qty_changed": {"verdict": g2r["verdict"], "status": {PayloadLedger._k(k): v for k, v in g2r["status"].items()}, "A_qty": str(g2L.pos["A"][0]),
                             "note": "새 키지만 지난 날짜라 BLOCKED_ORDER로 우연히 막힘"}}
summary = {"fixtures_pass": all(v["pass"] for v in results.values()), "neg_defect_reproduced": all(v["defect_reproduced"] for v in neg.values()),
           "real_events_applied": 0, "gap_G1_double_applied": gaps["G1_apply_date_changed"]["A_qty"] == "925"}
summary["all_pass"] = summary["fixtures_pass"] and summary["neg_defect_reproduced"]
out = {"fixtures": results, "pre_fix_negative_control": neg, "informational_gaps": gaps, "summary": summary,
       "pr106_source_sha256": hashlib.sha256(PR106.read_bytes()).hexdigest()}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "applied-payload-provenance.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print(json.dumps({"summary": summary, "fixtures": {k: (v["runs"][0]["verdict"], v["order_and_reload_invariant"], v["reload_bytes_stable"], v["pass"]) for k, v in results.items()},
                  "neg": {k: [(p["verdict"], p["A_status"], p["B_qty"]) for p in v["runs"]] for k, v in neg.items()},
                  "gaps": {k: (v["verdict"], v["A_qty"]) for k, v in gaps.items()}}, ensure_ascii=False))
