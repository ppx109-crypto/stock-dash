"""REPLAY-CA-AMBIGUOUS-IDENTITY-QUARANTINE-0001 · (sym, kind) anchor 격리 · 배치 전체 중단 · 경로 불변 · PR108 음성대조군(합성).
python3 -I identity_quarantine.py <PR108 payload_registry.py 고정본> <출력 폴더>
정확 유리수 · 합성 종목/날짜 · 네트워크 함수 막음. anchor 격리는 동일성 증명이 아니라 임시 fail-closed."""
import copy
import hashlib
import json
import socket
import sys
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PR108, OUT = Path(sys.argv[1]), Path(sys.argv[2])
PR108_SHA = "adb5ceccb7d5bd536c18d3f3069550b6b6c5205245f54e1c66b51ee05d18d2c0"   # PR108 manifest file_sha256


def _ok_num(x):
    return not (x is None or isinstance(x, (bool, float))) and isinstance(x, (int, F)) and F(x) > 0


def canon_price(x):
    return str(F(x)) if isinstance(x, (int, F)) and not isinstance(x, bool) else "RAW:" + repr(x)


class IdentityLedger:
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

    def anchors(self):                                                      # 이미 커밋된 레지스트리에서만
        return {(k[0], k[1]) for k in self.applied}

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
        anc = self.anchors()
        uniq, obs, same_conf, applied_conf, ambiguous = {}, {}, set(), set(), set()
        for ev in events:                                                   # ① 정규화 · 우선순위 1→2→3→4
            k, pl = self.key(ev), self.payload(ev)
            if k in self.applied:                                           # 1 · 2: 같은 키
                if self.applied[k] == pl:
                    obs.setdefault(k, set()).add(ev.get("src"))
                else:
                    applied_conf.add(k)
                continue
            if (k[0], k[1]) in anc:                                         # 3: 다른 키 + 적용된 같은 anchor(수정 핵심)
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
DAYS = ["2026-01-28", "2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"]
A1 = {"sym": "A", "kind": "split", "m_qty": F(5), "m_price": F(1, 5), "apply_date": "2026-01-29", "src": "R1"}


def B_on(d):
    return {"sym": "B", "kind": "reverse_split", "m_qty": F(1, 5), "m_price": F(5), "apply_date": d, "src": "RB"}


# 배치 날짜 · 배치 안의 A · 기대
FIX = {
    "Q1_apply_date_changed": ("2026-02-02", dict(A1, apply_date="2026-02-02", src="R9"), "BATCH_ABORTED"),
    "Q2_m_qty_changed": ("2026-01-30", dict(A1, m_qty=F(10), m_price=F(1, 10), src="R8"), "BATCH_ABORTED"),
    "Q3_legit_looking_second_split": ("2026-02-03", dict(A1, m_qty=F(2), m_price=F(1, 2), apply_date="2026-02-03", src="R5"), "BATCH_ABORTED"),
    "Q4_same_key_same_payload": ("2026-01-30", dict(A1, src="R2"), "COMMITTED"),
}


def quotes(d, bday):
    q = {}
    if d != "2026-01-29":
        q["A"] = 52300 if d < "2026-01-29" else 10460
    if bday is None or d != bday:
        q["B"] = 905 if bday is None or d < bday else 4525
    return q


def run(Ledger, bday, avar, order, reload, days=DAYS, a_only=False):
    """bday: 배치 날짜. avar: 배치 안의 A. a_only: B 없이 A만(G1 그대로 재현용)."""
    L = Ledger(1_000_000, POS)
    res, blobs, trace = None, {}, []
    for d in days:
        evs = [A1] if d == "2026-01-29" else []
        if d == bday:
            pair = [avar] if a_only else [avar, B_on(bday)]
            evs = [pair[i] for i in order] if not a_only else pair
        snap_pos, snap_app, snap_prov = copy.deepcopy(L.pos), dict(L.applied), {k: set(v) for k, v in L.prov.items()}
        r = L.process_day(d, quotes(d, None if a_only else bday), evs)
        if d == bday:
            res = dict(r, pos_before=snap_pos, app_before=snap_app, prov_before=snap_prov)
        if d == "2026-01-29" and reload:                                     # 직렬화 → 다시 읽기 → 계속
            s1 = L.to_json()
            L = Ledger.from_json(s1)
            blobs = {"bytes_equal_after_reload": L.to_json() == s1, "reload_sha256": hashlib.sha256(s1.encode()).hexdigest()}
        trace.append({"day": d, "state_hash": L.state_hash(), "prov_hash": L.prov_hash(), "snap": [str(L.snaps[-1]["nav"]), L.snaps[-1]["valid"]]})
    end = L.to_json()
    blobs["end_bytes_stable"] = Ledger.from_json(end).to_json() == end
    return L, res, blobs, trace


def field_mutations(Ledger, bday, avar, order):
    """배치만 따로: 전날까지 돌린 장부에 apply_batch 한 번 → pos/applied/prov 칸 단위 비교(시세 반영 전)."""
    L = Ledger(1_000_000, POS)
    for d in DAYS:
        if d == bday:
            break
        L.process_day(d, quotes(d, bday), [A1] if d == "2026-01-29" else [])
    pos0, app0, prov0 = copy.deepcopy(L.pos), dict(L.applied), {k: set(v) for k, v in L.prov.items()}
    pair = [avar, B_on(bday)]
    r = L.apply_batch(bday, [pair[i] for i in order])
    diffs = [f"pos.{s}.{i}" for s in pos0 for i in (0, 1) if pos0[s][i] != L.pos[s][i]]
    diffs += ["applied"] * (app0 != L.applied) + ["prov"] * (prov0 != L.prov)
    return {"verdict": r["verdict"], "changed_fields": diffs, "B_own_status": r["status"].get(IdentityLedger.key(B_on(bday))),
            "blocked_from": L.blocked_from}


K = IdentityLedger._k
results = {}
for name, (bday, avar, expect) in FIX.items():
    runs = []
    for order in ((0, 1), (1, 0)):
        for reload in (False, True):
            L, r, blobs, trace = run(IdentityLedger, bday, avar, order, reload)
            cut_ok = True                                                    # 자르기: d까지만 읽은 실행 == 전체 실행의 d 시점
            for i, d in enumerate(DAYS):
                _, _, _, tr = run(IdentityLedger, bday, avar, order, reload, days=DAYS[:i + 1])
                cut_ok &= tr == trace[:i + 1]
            runs.append({"order": list(order), "reload": reload, "verdict": r["verdict"],
                         "status": {K(k): v for k, v in sorted(r["status"].items(), key=lambda kv: K(kv[0]))},
                         "state_hash_before": r["h0"], "state_hash_after_batch": r["h1"], "prov_hash_before": r["p0"], "prov_hash_after_batch": r["p1"],
                         "final_state_hash": L.state_hash(), "final_prov_hash": L.prov_hash(),
                         "qty": {s: str(q) for s, (q, _) in sorted(L.pos.items())}, "applied_keys": sorted(K(k) for k in L.applied),
                         "prov_A": sorted(L.prov.get(IdentityLedger.key(A1), [])), "perf": perf(L.snaps), "cut_test": cut_ok, **blobs})
    muts = [field_mutations(IdentityLedger, bday, avar, o) for o in ((0, 1), (1, 0))]
    r0 = runs[0]
    cmp = ("verdict", "status", "state_hash_before", "state_hash_after_batch", "prov_hash_before", "prov_hash_after_batch",
           "final_state_hash", "final_prov_hash", "qty", "perf")
    same = all(all(x[c] == r0[c] for c in cmp) for x in runs)
    stable = all(x.get("bytes_equal_after_reload", True) and x["end_bytes_stable"] for x in runs)
    cut = all(x["cut_test"] for x in runs)
    akey, bkey = K(IdentityLedger.key(avar)), K(IdentityLedger.key(B_on(bday)))
    if expect == "COMMITTED":
        ok = r0["verdict"] == "COMMITTED" and r0["status"] == {akey: "DUPLICATE_IGNORED", bkey: "OK"} and r0["qty"] == {"A": "185", "B": "15"} \
             and r0["prov_A"] == ["R1", "R2"] and r0["perf"].get("all_zero") is True and r0["applied_keys"] == sorted([K(IdentityLedger.key(A1)), bkey])
    else:
        ok = r0["verdict"] == "BATCH_ABORTED" and r0["status"] == {akey: "BLOCKED_AMBIGUOUS_EVENT_IDENTITY", bkey: "OK"} \
             and r0["qty"] == {"A": "185", "B": "75"} and r0["applied_keys"] == [K(IdentityLedger.key(A1))] and r0["prov_A"] == ["R1"] \
             and all(x["state_hash_after_batch"] == x["state_hash_before"] and x["prov_hash_after_batch"] == x["prov_hash_before"] for x in runs) \
             and r0["perf"] == {"status": "PERF_BLOCKED", "from": bday} \
             and all(m["verdict"] == "BATCH_ABORTED" and m["changed_fields"] == [] and m["B_own_status"] == "OK" for m in muts)
    results[name] = {"batch_day": bday, "input_A": {k: str(v) for k, v in avar.items()}, "input_B": {k: str(v) for k, v in B_on(bday).items()},
                     "expect": expect, "runs": runs, "batch_field_mutations": muts, "order_and_reload_invariant": same,
                     "bytes_stable": stable, "cut_test": cut, "pass": ok and same and stable and cut}
results["Q3_legit_looking_second_split"]["needs_data"] = \
    "합법적으로 보이는 두 번째 독립 분할도 차단(보수적 오탐). 출처 사건 ID/정정 사슬 없이는 새 사건과 정정을 가를 수 없음. 자동 허용 규칙 없음."

# ── 음성대조군: PR #108 고정본 PayloadLedger ──
raw = PR108.read_bytes()
src = raw.decode("utf-8").split("\nPOS = ")[0]
keep = sys.argv[:]
sys.argv = ["pr108", "/nonexistent", "/nonexistent"]
G = {"__name__": "pr108_prefix"}
exec(compile(src, "PR108 payload_registry.py(앞부분 · PayloadLedger)", "exec"), G)
sys.argv = keep
PL = G["PayloadLedger"]
neg = {"pr108_source_sha256": hashlib.sha256(raw).hexdigest()}
neg["sha_matches_pr108_manifest"] = neg["pr108_source_sha256"] == PR108_SHA
gL, gr, _, gtr = run(PL, "2026-02-02", FIX["Q1_apply_date_changed"][1], (0,), False, a_only=True)
neg["G1_exact"] = {"verdict": gr["verdict"], "status": {K(k): v for k, v in gr["status"].items()},
                   "A_qty_path": ["37", "185", str(gL.pos["A"][0])], "B_qty": str(gL.pos["B"][0])}
for name, (bday, avar, _) in FIX.items():
    per = []
    for order in ((0, 1), (1, 0)):
        L, r, _, _ = run(PL, bday, avar, order, False)
        per.append({"order": list(order), "verdict": r["verdict"], "status": {K(k): v for k, v in sorted(r["status"].items(), key=lambda kv: K(kv[0]))},
                    "qty": {s: str(q) for s, (q, _) in sorted(L.pos.items())}})
    neg[name] = per
akq = lambda n: K(IdentityLedger.key(FIX[n][1]))
neg_expect = {
    "G1_exact": neg["G1_exact"]["verdict"] == "COMMITTED" and neg["G1_exact"]["A_qty_path"] == ["37", "185", "925"],
    "Q1": all(p["verdict"] == "COMMITTED" and p["qty"] == {"A": "925", "B": "15"} for p in neg["Q1_apply_date_changed"]),
    "Q2": all(p["verdict"] == "BATCH_ABORTED" and p["status"][akq("Q2_m_qty_changed")] == "BLOCKED_ORDER" for p in neg["Q2_m_qty_changed"]),
    "Q3": all(p["verdict"] == "COMMITTED" and p["qty"] == {"A": "370", "B": "15"} for p in neg["Q3_legit_looking_second_split"]),
    "Q4": all(p["verdict"] == "COMMITTED" and p["qty"] == {"A": "185", "B": "15"} for p in neg["Q4_same_key_same_payload"]),
}
neg["expectations_met"] = neg_expect

# ── 참고(판정 제외): 같은 종목 다른 kind ──
R1ev = {"sym": "A", "kind": "reverse_split", "m_qty": F(1, 5), "m_price": F(5), "apply_date": "2026-02-02", "src": "RK"}
rL, rr, _, _ = run(IdentityLedger, "2026-02-02", R1ev, (0,), False, a_only=True)
info = {"R1_same_sym_other_kind": {"verdict": rr["verdict"], "status": {K(k): v for k, v in rr["status"].items()}, "A_qty": str(rL.pos["A"][0]),
                                   "note": "anchor가 (sym, kind)라 kind가 바뀐 입력은 격리되지 않음(남은 위험)"}}

summary = {"fixtures_pass": all(v["pass"] for k, v in results.items()),
           "neg_sha_ok": neg["sha_matches_pr108_manifest"], "neg_expectations_met": all(neg_expect.values()),
           "q3_false_positive_blocked": results["Q3_legit_looking_second_split"]["runs"][0]["verdict"] == "BATCH_ABORTED",
           "real_events_applied": 0}
summary["all_pass"] = summary["fixtures_pass"] and summary["neg_sha_ok"] and summary["neg_expectations_met"]
out = {"fixtures": results, "pre_fix_negative_control": neg, "informational": info, "summary": summary}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ambiguous-identity-quarantine.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print(json.dumps({"summary": summary,
                  "fixtures": {k: (v["runs"][0]["verdict"], v["runs"][0]["status"], v["runs"][0]["qty"], v["order_and_reload_invariant"], v["bytes_stable"],
                                   v["cut_test"], [m["changed_fields"] for m in v["batch_field_mutations"]], v["pass"]) for k, v in results.items()},
                  "neg": neg_expect, "neg_G1": neg["G1_exact"]["A_qty_path"],
                  "neg_Q2_reason": neg["Q2_m_qty_changed"][0]["status"], "info": {k: (v["verdict"], v["A_qty"]) for k, v in info.items()}}, ensure_ascii=False))
