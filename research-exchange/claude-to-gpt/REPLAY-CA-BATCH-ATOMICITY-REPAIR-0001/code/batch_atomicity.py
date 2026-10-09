"""REPLAY-CA-BATCH-ATOMICITY-REPAIR-0001 · 하루 배치 all-or-nothing 원장(합성) + 순열 불변성 + 수정 전 음성대조군.
python3 -I batch_atomicity.py <PR104 ledger_atomicity.py 고정본> <출력 폴더>
- 정확 유리수(Fraction) · 합성 종목/날짜 · 네트워크 함수 막음."""
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
PR104, OUT = Path(sys.argv[1]), Path(sys.argv[2])


def _ok_num(x):
    return not (x is None or isinstance(x, (bool, float))) and isinstance(x, (int, F)) and F(x) > 0


class BatchLedger:
    def __init__(self, cash, positions):
        self.cash = F(cash)
        self.pos = {s: [F(q), F(p)] for s, (q, p) in positions.items()}
        self.applied, self.snaps, self.blocked_from = set(), [], None

    def state_hash(self):
        body = {"cash": str(self.cash), "pos": {s: [str(q), str(p)] for s, (q, p) in sorted(self.pos.items())}, "applied": sorted(map(list, self.applied))}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def key(ev):
        return (ev.get("sym"), ev.get("kind"), str(ev.get("m_qty")), ev.get("apply_date"))

    @staticmethod
    def payload(ev):
        return (str(ev.get("m_price")), bool(ev.get("real")))

    def check(self, ev, day):                                            # S0 기준 · 상태 변경 없음
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
        h0 = self.state_hash()
        uniq, dup_count, conflict = {}, Counter(), set()
        for ev in events:                                                # ① 의미키 정규화
            k = self.key(ev)
            if k in self.applied:
                dup_count[k] += 1
                continue
            if k in uniq:
                if self.payload(uniq[k]) == self.payload(ev):
                    dup_count[k] += 1
                else:
                    conflict.add(k)
                continue
            uniq[k] = ev
        status = {}
        sym_n = Counter(ev.get("sym") for ev in uniq.values())
        for k, ev in uniq.items():                                       # ② S0 기준 선검증
            if k in conflict:
                status[k] = "BLOCKED_KEY_PAYLOAD_CONFLICT"
            elif sym_n[ev.get("sym")] > 1:
                status[k] = "BLOCKED_SAME_SYMBOL_MULTI_EVENT"
            else:
                status[k] = self.check(ev, day)
        assert self.state_hash() == h0                                   # 검증은 상태를 바꾸지 않음
        for k in dup_count:
            status.setdefault(k, "DUPLICATE_IGNORED")
        if any(v not in ("OK", "DUPLICATE_IGNORED") for v in status.values()):
            self.blocked_from = self.blocked_from or day                 # ③ 하나라도 실패 → 전체 중단
            return {"verdict": "BATCH_ABORTED", "status": status, "dup_count": dict(dup_count), "hash_before": h0, "hash_after": self.state_hash()}
        scratch, cash0 = copy.deepcopy(self.pos), self.cash              # ④ scratch에 전부 적용
        for k in sorted(uniq, key=lambda x: tuple(map(str, x))):
            ev = uniq[k]
            q, p = scratch[ev["sym"]]
            scratch[ev["sym"]] = [q * F(ev["m_qty"]), p * F(ev["m_price"])]
        for s in self.pos:                                               # ⑤ 불변식 재확인
            assert scratch[s][0] * scratch[s][1] == self.pos[s][0] * self.pos[s][1] and scratch[s][0].denominator == 1
        assert self.cash == cash0
        self.pos, self.applied = scratch, self.applied | set(uniq)       # ⑥ 한 번 커밋
        return {"verdict": "COMMITTED", "status": status, "dup_count": dict(dup_count), "hash_before": h0, "hash_after": self.state_hash()}

    def process_day(self, day, quotes, events):
        res = self.apply_batch(day, events) if events else None
        for s, px in quotes.items():
            self.pos[s][1] = F(px)
        nav = self.cash + sum(q * p for q, p in self.pos.values())
        self.snaps.append({"day": day, "nav": nav, "valid": self.blocked_from is None})
        return res


def perf(snaps):
    bad = [s["day"] for s in snaps if not s["valid"]]
    if bad:
        return {"status": "PERF_BLOCKED", "from": bad[0]}
    r = [(snaps[i]["day"], snaps[i]["nav"] / snaps[i - 1]["nav"] - 1) for i in range(1, len(snaps))]
    months = {}
    for d, x in r:
        months[d[:7]] = months.get(d[:7], F(1)) * (1 + x)
    peak, mdd = snaps[0]["nav"], F(0)
    for s in snaps:
        peak = max(peak, s["nav"])
        mdd = max(mdd, (peak - s["nav"]) / peak)
    return {"status": "OK", "all_zero": all(x == 0 for _, x in r) and all(v == 1 for v in months.values()) and mdd == 0, "mdd": str(mdd)}


POS = {"A": (37, 52300), "B": (75, 905), "D": (7, 1000)}
CASH = 1_000_000
DAYS = ["2026-01-28", "2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"]
EV = "2026-01-30"
A_OK = {"sym": "A", "kind": "split", "m_qty": F(5), "m_price": F(1, 5), "apply_date": EV, "src": "RA"}
B_OK = {"sym": "B", "kind": "reverse_split", "m_qty": F(1, 5), "m_price": F(5), "apply_date": EV, "src": "RB"}
FIX = {
    "F1_A_ok+B_ratio_bad": ([A_OK, dict(B_OK, m_price=F(4), src="RBx")], {}, "BATCH_ABORTED"),
    "F2_A_ok+D_fractional": ([A_OK, {"sym": "D", "kind": "reverse_split", "m_qty": F(1, 10), "m_price": F(10), "apply_date": EV, "src": "RD"}], {}, "BATCH_ABORTED"),
    "F3_A_ok+X_unknown": ([A_OK, {"sym": "X", "kind": "split", "m_qty": F(2), "m_price": F(1, 2), "apply_date": EV, "src": "RX"}], {}, "BATCH_ABORTED"),
    "F4_A_ok+B_ok": ([A_OK, B_OK], {}, "COMMITTED"),
    "F5_A_ok+A_dup": ([A_OK, dict(A_OK, src="RA2-다른출처")], {}, "COMMITTED"),
    "F6_same_symbol_two_events": ([A_OK, {"sym": "A", "kind": "split", "m_qty": F(2), "m_price": F(1, 2), "apply_date": EV, "src": "RA3"}], {}, "BATCH_ABORTED"),
    "F7_same_key_payload_conflict": ([A_OK, dict(A_OK, m_price=F(1, 4), src="RA4")], {}, "BATCH_ABORTED"),
    "F8_A_ok+B_redelivered": ([A_OK, dict(B_OK, apply_date="2026-01-29", src="RB-재전송")], {"2026-01-29": [dict(B_OK, apply_date="2026-01-29")]}, "COMMITTED"),
    "F9_A_ok+B_real_flag": ([A_OK, dict(B_OK, real=True)], {}, "BATCH_ABORTED"),
}
EXPECT_STATUS = {"F1_A_ok+B_ratio_bad": "BLOCKED_RATIO_PRODUCT", "F2_A_ok+D_fractional": "BLOCKED_FRACTIONAL", "F3_A_ok+X_unknown": "BLOCKED_UNKNOWN_SYMBOL",
                 "F6_same_symbol_two_events": "BLOCKED_SAME_SYMBOL_MULTI_EVENT", "F7_same_key_payload_conflict": "BLOCKED_KEY_PAYLOAD_CONFLICT",
                 "F9_A_ok+B_real_flag": "APPLY_BLOCKED_NO_PRICE_BASIS_DATE"}


def market(name):
    """시장 쪽 기준 변화(합성): 그날 실제로 일어난 것으로 둔 사건만. 사건 당일은 해당 종목 시세 없음."""
    mp = {"A": F(1, 5)}
    if name in ("F4_A_ok+B_ok", "F1_A_ok+B_ratio_bad", "F9_A_ok+B_real_flag"):
        mp["B"] = F(5)
    return mp


def run(name, order):
    events, pre, _ = FIX[name]
    L = BatchLedger(CASH, POS)
    mp = market(name)
    res_ev = None
    for d in DAYS:
        if d in pre:                                                     # F8: 전날 B 적용(시장도 그날 B 기준 변화)
            L.process_day(d, {s: POS[s][1] for s in POS if s != "B"}, pre[d])
            continue
        if d < EV:
            q = {s: POS[s][1] for s in POS}
            if name == "F8_A_ok+B_redelivered" and d > "2026-01-29":
                q["B"] = POS["B"][1] * 5
        elif d == EV:
            q = {s: POS[s][1] * (5 if (s == "B" and name == "F8_A_ok+B_redelivered") else 1) for s in POS if s not in mp}
        else:
            q = {s: POS[s][1] * mp.get(s, 1) * (5 if (s == "B" and name == "F8_A_ok+B_redelivered") else 1) for s in POS}
        r = L.process_day(d, q, [events[i] for i in order] if d == EV else [])
        if d == EV:
            res_ev = r
    st = {"|".join(map(str, k)): v for k, v in sorted(res_ev["status"].items(), key=lambda kv: tuple(map(str, kv[0])))}
    return {"verdict": res_ev["verdict"], "hash_before": res_ev["hash_before"], "hash_after_batch": res_ev["hash_after"], "final_hash": L.state_hash(),
            "status": st, "dup_count": {"|".join(map(str, k)): v for k, v in res_ev["dup_count"].items()}, "perf": perf(L.snaps),
            "qty": {s: str(q) for s, (q, _) in L.pos.items()}, "applied_n": len(L.applied)}


results = {}
for name, (events, pre, exp_verdict) in FIX.items():
    perms = list(itertools.permutations(range(len(events))))
    runs = [run(name, p) for p in perms]
    r0 = runs[0]
    inv = all((r["verdict"], r["final_hash"], r["status"], r["dup_count"]) == (r0["verdict"], r0["final_hash"], r0["status"], r0["dup_count"]) for r in runs)
    ok = r0["verdict"] == exp_verdict and inv
    if exp_verdict == "BATCH_ABORTED":
        ok = ok and all(r["hash_after_batch"] == r["hash_before"] for r in runs) and r0["perf"]["status"] == "PERF_BLOCKED" \
             and r0["qty"]["A"] == "37" and EXPECT_STATUS[name] in r0["status"].values()
    else:
        ok = ok and r0["perf"].get("all_zero") is True and r0["hash_after_batch"] != r0["hash_before"]
        if name == "F5_A_ok+A_dup":
            ok = ok and r0["qty"]["A"] == "185" and list(r0["dup_count"].values()) == [1]
        if name == "F4_A_ok+B_ok":
            ok = ok and r0["qty"]["A"] == "185" and r0["qty"]["B"] == "15"
        if name == "F8_A_ok+B_redelivered":
            ok = ok and r0["qty"]["A"] == "185" and r0["qty"]["B"] == "15" and "DUPLICATE_IGNORED" in r0["status"].values()
    results[name] = {"expect_verdict": exp_verdict, "expect_status": EXPECT_STATUS.get(name), "permutations": len(perms), "permutation_invariant": inv,
                     "first_run": r0, "pass": ok}

# ── 수정 전 음성대조군: PR #104 고정본 Ledger를 그대로 실행 ──
src = PR104.read_text(encoding="utf-8").split("\nDAYS = ")[0]
argv_keep = sys.argv[:]
sys.argv = ["pr104", "/nonexistent", "/nonexistent"]
G = {"__name__": "pr104_prefix"}
exec(compile(src, "PR104 ledger_atomicity.py(앞부분 · Ledger 클래스)", "exec"), G)
sys.argv = argv_keep
neg = {}
for name in ("F1_A_ok+B_ratio_bad", "F2_A_ok+D_fractional", "F3_A_ok+X_unknown"):
    events = FIX[name][0]
    per = []
    for order in itertools.permutations(range(len(events))):
        L = G["Ledger"](CASH, POS, "atomic")
        for d in DAYS[:2]:
            L.process_day(d, {s: POS[s][1] for s in POS}, [])
        h0 = L.state_hash()
        res = L.process_day(EV, {}, [events[i] for i in order])
        per.append({"order": list(order), "statuses": [x["status"] for x in res], "hash_changed": L.state_hash() != h0,
                    "A_qty_after": str(L.pos["A"][0]), "A_price_after": str(L.pos["A"][1])})
    neg[name] = {"runs": per, "defect_reproduced": all(p["hash_changed"] and p["A_qty_after"] == "185" for p in per)}

summary = {"fixtures_pass": all(r["pass"] for r in results.values()), "n_fixtures": len(results),
           "n_permutation_runs": sum(r["permutations"] for r in results.values()),
           "prefix_defect_reproduced": all(v["defect_reproduced"] for v in neg.values()), "real_events_applied": 0}
summary["all_pass"] = summary["fixtures_pass"] and summary["prefix_defect_reproduced"]
out = {"fixtures": results, "pre_fix_negative_control": neg, "summary": summary,
       "pr104_source_sha256": hashlib.sha256(PR104.read_bytes()).hexdigest()}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "batch-atomicity.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print(json.dumps({"summary": summary, "fixtures": {k: (v["first_run"]["verdict"], v["permutation_invariant"], v["pass"]) for k, v in results.items()},
                  "neg": {k: v["defect_reproduced"] for k, v in neg.items()}}, ensure_ascii=False))
