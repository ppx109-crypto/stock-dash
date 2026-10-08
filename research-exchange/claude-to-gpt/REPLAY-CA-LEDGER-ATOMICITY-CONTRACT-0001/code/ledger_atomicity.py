"""REPLAY-CA-LEDGER-ATOMICITY-CONTRACT-0001 · 합성 일별 원장 원자성 · 멱등성 검산 + 코드 경로 감사(오프라인).
python3 -I ledger_atomicity.py <git 저장소> <출력 폴더>
- 모든 수는 Fraction(정확 유리수). 합성 종목 · 합성 날짜(실제 시장 아님). 네트워크 함수 막음."""
import copy
import hashlib
import json
import math
import re
import socket
import subprocess
import sys
from fractions import Fraction as F
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
REPO, OUT = sys.argv[1], Path(sys.argv[2])


def _ok_num(x):
    if x is None or isinstance(x, bool) or isinstance(x, float):     # float = 단위 · 반올림 불명 또는 비유한
        return False
    return isinstance(x, (int, F)) and F(x) > 0


class Ledger:
    """mode: atomic(계약) · partial(수량 먼저, 가격은 다음 snapshot) · reverse(가격 × m_qty)"""

    def __init__(self, cash, positions, mode="atomic"):
        self.cash = F(cash)
        self.pos = {s: [F(q), F(p)] for s, (q, p) in positions.items()}
        self.applied, self.snaps, self.invalid, self.log, self.mode, self.pending = set(), [], set(), [], mode, {}

    def state_hash(self):
        body = {"cash": str(self.cash), "pos": {s: [str(q), str(p)] for s, (q, p) in sorted(self.pos.items())},
                "applied": sorted(map(list, self.applied))}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def key(ev):
        return (ev.get("sym"), ev.get("kind"), str(ev.get("m_qty")), ev.get("apply_date"))   # 출처 접수번호는 키에 없음

    def check(self, ev, day, pos, applied):
        if ev.get("real"):
            return "APPLY_BLOCKED_NO_PRICE_BASIS_DATE"
        if not ev.get("apply_date"):
            return "BLOCKED_APPLY_DATE_MISSING"
        if self.key(ev) in applied:                                      # 1회차 결함 수정: 중복을 날짜 · 순서 검사보다 먼저
            return "BLOCKED_DUPLICATE_EVENT"
        if self.snaps and ev["apply_date"] < self.snaps[-1]["day"]:
            return "BLOCKED_ORDER"
        if ev["apply_date"] != day:
            return "BLOCKED_APPLY_DATE_MISMATCH"
        if not (_ok_num(ev.get("m_qty")) and _ok_num(ev.get("m_price"))) or ev.get("sym") not in pos:
            return "BLOCKED_INPUT"
        if F(ev["m_qty"]) * F(ev["m_price"]) != 1:
            return "BLOCKED_RATIO_PRODUCT"
        if (pos[ev["sym"]][0] * F(ev["m_qty"])).denominator != 1:
            return "BLOCKED_FRACTIONAL"
        return "OK"

    def try_apply(self, ev, day, pos=None, applied=None):
        """pos/applied를 주면 그 복사본에, 아니면 커밋된 상태에 직접(멱등 검사용)."""
        tgt_pos = self.pos if pos is None else pos
        tgt_app = self.applied if applied is None else applied
        st = self.check(ev, day, tgt_pos, tgt_app)
        if st != "OK":
            return st
        s, mq, mp = ev["sym"], F(ev["m_qty"]), F(ev["m_price"])
        q, p = tgt_pos[s]
        if self.mode == "atomic":
            tgt_pos[s] = [q * mq, p * mp]
        elif self.mode == "partial":
            tgt_pos[s] = [q * mq, p]
            self.pending[s] = mp
        elif self.mode == "reverse":
            tgt_pos[s] = [q * mq, p * mq]
        tgt_app.add(self.key(ev))
        return "OK"

    def process_day(self, day, quotes, events):
        if self.mode == "partial":                                      # 지난 snapshot에서 미룬 가격 갱신
            for s, mp in self.pending.items():
                self.pos[s][1] *= mp
            self.pending = {}
        new_pos, new_app = copy.deepcopy(self.pos), set(self.applied)   # ① 복사본에서 모두 처리
        res = []
        for ev in events:
            st = self.try_apply(ev, day, new_pos, new_app)
            res.append({"key": list(self.key(ev)), "src": ev.get("src"), "status": st})
            if st not in ("OK", "BLOCKED_DUPLICATE_EVENT") and ev.get("sym") in new_pos:
                self.invalid.add(ev["sym"])                             # 막힌 사건이 걸린 종목은 그날부터 NAV 무효
        self.pos, self.applied = new_pos, new_app                       # ② 한 번에 커밋
        for s, px in quotes.items():                                    # ③ 그날 시세(있으면)
            self.pos[s][1] = F(px)
        nav = self.cash + sum(q * p for q, p in self.pos.values())      # ④ snapshot
        valid = not any(s in self.invalid and self.pos[s][0] > 0 for s in self.pos)
        self.snaps.append({"day": day, "nav": nav, "valid": valid, "cash": self.cash,
                           "pos": {s: [str(q), str(p)] for s, (q, p) in self.pos.items()}, "events": res})
        return res


def perf(snaps):
    bad = [s["day"] for s in snaps if not s["valid"]]
    if bad:
        return {"status": "PERF_BLOCKED", "invalid_days": bad}
    r = [(snaps[i]["day"], snaps[i]["nav"] / snaps[i - 1]["nav"] - 1) for i in range(1, len(snaps))]
    months = {}
    for d, x in r:
        months.setdefault(d[:7], F(1))
        months[d[:7]] *= 1 + x
    peak, mdd = snaps[0]["nav"], F(0)
    for s in snaps:
        peak = max(peak, s["nav"])
        mdd = max(mdd, (peak - s["nav"]) / peak)
    return {"status": "OK", "daily_r": {d: str(x) for d, x in r}, "monthly_twr": {m: str(v - 1) for m, v in months.items()}, "mdd": str(mdd),
            "all_zero": all(x == 0 for _, x in r) and all(v == 1 for v in months.values()) and mdd == 0}


DAYS = ["2026-01-28", "2026-01-29", "2026-01-30", "2026-02-02", "2026-02-03"]     # 합성 · 달을 넘김
EV_DAY = "2026-01-30"                                                         # 사건 당일 = 시세 없음(정지 가정)
NORMAL = [("split_1to5", "split", 37, 52300, F(5)), ("split_1to10", "split", 3, 812000, F(10)),
          ("reverse_10to1", "reverse_split", 120, 1234, F(1, 10)), ("reverse_5to1", "reverse_split", 75, 905, F(1, 5))]
CASH0 = 1_000_000


def run(case, mode="atomic", ev_over=None, events_extra=None):
    name, kind, q, p, mq = case
    L = Ledger(CASH0, {"SYN": (q, p)}, mode)
    ev = {"sym": "SYN", "kind": kind, "m_qty": mq, "m_price": 1 / mq, "apply_date": EV_DAY, "src": "R1"}
    ev.update(ev_over or {})
    new_px = F(p) / mq
    hashes = {}
    for d in DAYS:
        quotes = {} if d == EV_DAY else {"SYN": p if d < EV_DAY else new_px}
        if d == EV_DAY:
            hashes["before"] = L.state_hash()
        L.process_day(d, quotes, ([ev] if d == EV_DAY else []) + (events_extra(d) if events_extra else []))
        if d == EV_DAY:
            hashes["after"] = L.state_hash()
    return L, ev, hashes


out = {"normal": [], "idempotency": [], "negative_controls": [], "fail_closed": []}
# ── 정상 4건 ──
for case in NORMAL:
    L, ev, h = run(case)
    pf = perf(L.snaps)
    navs = [s["nav"] for s in L.snaps]
    q_after = F(case[2]) * case[4]
    row = {"case": case[0], "m_qty": str(case[4]), "m_price": str(1 / case[4]), "m_qty_x_m_price": str(case[4] * (1 / case[4])),
           "qty": [case[2], str(q_after)], "price": [case[3], str(F(case[3]) / case[4])],
           "nav_series": [str(x) for x in navs], "cash_series": [str(s["cash"]) for s in L.snaps],
           "value_before_after": [str(F(case[2]) * case[3]), str(q_after * F(case[3]) / case[4])],
           "perf": pf,
           "expect": {"nav_constant": True, "cash_constant": True, "twr_mtwr_mdd_zero": True, "event_status": "OK"},
           "got": {"nav_constant": len(set(navs)) == 1, "cash_constant": all(s["cash"] == CASH0 for s in L.snaps),
                   "twr_mtwr_mdd_zero": pf.get("all_zero") is True, "event_status": L.snaps[2]["events"][0]["status"]}}
    row["pass"] = row["expect"] == row["got"]
    out["normal"].append(row)

# ── 멱등성: 같은 event_key 두 번 · 다른 출처 번호로 같은 사건 ──
for case in NORMAL[:2]:
    L, ev, h = run(case)
    h1 = L.state_hash()
    st_same = L.try_apply(ev, EV_DAY)                                        # 같은 사건 다시
    h2 = L.state_hash()
    st_src = L.try_apply(dict(ev, src="R2-다른접수"), EV_DAY)                 # 다른 출처, 같은 의미
    h3 = L.state_hash()
    L2, _, _ = run(case, events_extra=lambda d: ([{"sym": "SYN", "kind": case[1], "m_qty": case[4], "m_price": 1 / case[4], "apply_date": EV_DAY, "src": "R1"}] if d == EV_DAY else []))
    # 회귀 시험(1회차 결함): 이미 적용된 사건이 뒤 날짜(2026-02-02)에 다시 들어와도 중복으로 막히고 NAV를 무효로 만들지 않아야 함
    L3, _, _ = run(case, events_extra=lambda d: ([{"sym": "SYN", "kind": case[1], "m_qty": case[4], "m_price": 1 / case[4], "apply_date": EV_DAY, "src": "R3-재전송"}] if d == "2026-02-02" else []))
    redeliver = {"status": L3.snaps[3]["events"][0]["status"], "perf_all_zero": perf(L3.snaps).get("all_zero")}
    out["idempotency"].append({"case": case[0], "second_apply": st_same, "redelivered_later_day": redeliver, "other_src_apply": st_src, "hash_after_first": h1,
                               "hash_after_second": h2, "hash_after_other_src": h3,
                               "same_day_double_listed": [e["status"] for e in L2.snaps[2]["events"]], "same_day_double_perf_all_zero": perf(L2.snaps).get("all_zero"),
                               "pass": st_same == "BLOCKED_DUPLICATE_EVENT" and st_src == "BLOCKED_DUPLICATE_EVENT" and h1 == h2 == h3
                               and [e["status"] for e in L2.snaps[2]["events"]] == ["OK", "BLOCKED_DUPLICATE_EVENT"] and perf(L2.snaps).get("all_zero") is True
                               and redeliver == {"status": "BLOCKED_DUPLICATE_EVENT", "perf_all_zero": True}})

# ── 음성대조군: 부분 업데이트 · 반대 방향 ──
for mode in ("partial", "reverse"):
    for case in NORMAL:
        L, ev, h = run(case, mode=mode)
        pf = perf(L.snaps)
        base = L.snaps[1]["nav"]
        ev_nav = L.snaps[2]["nav"]
        out["negative_controls"].append({"mode": mode, "case": case[0], "nav_event_day": str(ev_nav), "nav_prev": str(base),
                                         "distortion_r_event_day": str(ev_nav / base - 1), "invested_distortion_factor": str((ev_nav - CASH0) / (base - CASH0)),
                                         "mdd": pf.get("mdd"), "detected": pf.get("status") == "OK" and pf.get("all_zero") is False})

# ── fail-closed ──
FAILS = [("apply_date_missing", {"apply_date": None}, "BLOCKED_APPLY_DATE_MISSING"),
         ("apply_date_future_mismatch", {"apply_date": "2026-02-02"}, "BLOCKED_APPLY_DATE_MISMATCH"),
         ("order_inversion_past", {"apply_date": "2026-01-28"}, "BLOCKED_ORDER"),
         ("ratio_product_ne_1", {"m_price": F(1, 4)}, "BLOCKED_RATIO_PRODUCT"),
         ("zero", {"m_qty": 0}, "BLOCKED_INPUT"), ("negative", {"m_qty": F(-5)}, "BLOCKED_INPUT"),
         ("missing", {"m_qty": None}, "BLOCKED_INPUT"), ("nan", {"m_qty": float("nan")}, "BLOCKED_INPUT"),
         ("float", {"m_qty": 5.0}, "BLOCKED_INPUT"), ("real_event_flag", {"real": True}, "APPLY_BLOCKED_NO_PRICE_BASIS_DATE")]
for name, over, expect in FAILS:
    L, ev, h = run(NORMAL[0], ev_over=over)
    pf = perf(L.snaps)
    st = L.snaps[2]["events"][0]["status"]
    out["fail_closed"].append({"case": name, "expect": expect, "got": st, "state_unchanged_by_event": h["before"] == h["after"] or st == "OK",
                               "qty_after_event_day": L.snaps[2]["pos"]["SYN"][0], "perf": pf["status"],
                               "nav_if_not_blocked_would_be": str(L.snaps[3]["nav"]),
                               "pass": st == expect and pf["status"] == "PERF_BLOCKED" and L.snaps[2]["pos"]["SYN"][0] == "37"})
Lf, evf, hf = run(("frac_reverse_10to1", "reverse_split", 7, 1000, F(1, 10)))
pff = perf(Lf.snaps)
out["fail_closed"].append({"case": "fractional_result", "expect": "BLOCKED_FRACTIONAL", "got": Lf.snaps[2]["events"][0]["status"],
                           "qty_after_event_day": Lf.snaps[2]["pos"]["SYN"][0], "perf": pff["status"],
                           "pass": Lf.snaps[2]["events"][0]["status"] == "BLOCKED_FRACTIONAL" and pff["status"] == "PERF_BLOCKED" and hf["before"] == hf["after"]})

summary = {"normal_pass": all(r["pass"] for r in out["normal"]), "idempotency_pass": all(r["pass"] for r in out["idempotency"]),
           "negative_detected": all(r["detected"] for r in out["negative_controls"]), "fail_closed_pass": all(r["pass"] for r in out["fail_closed"]),
           "real_events_applied": 0}
summary["all_pass"] = all(v for k, v in summary.items() if k != "real_events_applied")
out["summary"] = summary
out["formulas"] = {"nav": "NAV_t = cash + Σ qty × 표시가격(그날 시세 있으면 시세, 없으면 앞 표시가격)", "r": "r_t = NAV_t/NAV_{t-1} − 1(외부 현금흐름 0)",
                   "monthly": "달력월 TWR = Π(1 + r_t) − 1", "mdd": "max_t (peak_t − NAV_t)/peak_t",
                   "atomic": "사건 당일: 복사본에서 (qty × m_qty, 표시가격 × m_price)를 함께 바꾼 뒤 한 번에 커밋 → 그 뒤 snapshot",
                   "invariance": "qty·m_qty × price·m_price = qty × price (m_qty·m_price = 1)"}

# ── 코드 경로 감사(로컬 git · 읽기 전용) ──
TARGETS = [("origin/pr86", "research-exchange/claude-to-gpt/REPLAY-RAW-PRICE-CONTRACT-0001/code/raw_replay.py"),
           ("origin/pr88", "research-exchange/claude-to-gpt/REPLAY-CONTRACT-HARDENING-0001/code/raw_replay_v2.py"),
           ("origin/main", "paper_trade.py"), ("origin/main", "paper_check.py"), ("origin/main", "predash/paper.py"), ("origin/main", "portfolio_ui.py")]
PAT = r"ratio|CA_QTY|applied|분할|병합|split\(|reverse_split|rcept"
audit = []
for ref, path in TARGETS:
    p = subprocess.run(["git", "-C", REPO, "grep", "-n", "-I", "-E", PAT, ref, "--", path], capture_output=True, text=True)
    lines = p.stdout.splitlines()
    audit.append({"ref": ref, "path": path, "hits": len(lines), "lines": [l.split(":", 2)[2][:180] if l.count(":") >= 2 else l for l in lines][:40]})
classified = [
    {"where": "PR #86 raw_replay.py:77 · 106~119", "text": "chains[r.get(\"original_rcept_no\") or r[\"rcept_no\"]] · 적용 조건 effective_date == d",
     "risk": "사건 키 = 원 접수번호. 원 접수 연결이 없는 정정(DART는 원 접수 칸이 없음 · PR #90)은 별개 사슬이 되어 같은 분할이 두 번 적용될 수 있음. 적용 기록 집합 없음"},
    {"where": "PR #88 raw_replay_v2.py applied[root]", "text": "applied[root] = (회계 칸, touched) · root = root_rcept_no",
     "risk": "적용 기록은 있으나 키가 root_rcept_no. 수집기가 원 접수를 모를 때 root=자기 접수번호로 넣으면 같은 사건이 두 root로 두 번 적용될 수 있음(PR #88은 root 없으면 UNKNOWN으로 막지만, root=self는 막지 못함)"},
    {"where": "origin/main paper_trade.py · paper_check.py · predash/paper.py · portfolio_ui.py", "text": "기업행동 수량/가격 조정 코드 없음(검색 일치 0 또는 무관)",
     "risk": "운영 모의 장부는 분할 · 병합을 스스로 반영하지 않음 → 이중 적용 경로는 없지만, 반영 자체가 없으므로 실제 분할 종목 보유 시 수량 · 가격 불일치가 날 수 있음(이번 범위 밖 · 관찰만)"}]
code_audit = {"scope": TARGETS, "pattern": PAT, "raw": audit, "classified": classified,
              "fix_proposal": "event_key를 출처 번호가 아닌 의미 키(종목, 종류, m_qty, apply_date)로 두고, 같은 키 두 번째는 BLOCKED_DUPLICATE_EVENT(이 계약)",
              "may_miss": ["간접 호출(다른 모듈에서 수량을 바꾸는 함수)", "동적 키 · 문자열 조립", "브로커 잔고 동기화로 수량이 바뀌는 경로(paper_trade가 증권사 잔고를 다시 읽는 경우)", "정규식에 없는 이름(예: adjust, rebase)"]}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ledger-atomicity.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
(OUT / "code-path-audit.json").write_text(json.dumps(code_audit, ensure_ascii=False, indent=1))
print(json.dumps({"summary": summary, "normal": {r["case"]: r["pass"] for r in out["normal"]}, "idem": {r["case"]: r["pass"] for r in out["idempotency"]},
                  "neg": [(r["mode"], r["case"], r["invested_distortion_factor"], r["mdd"], r["detected"]) for r in out["negative_controls"]],
                  "fail": {r["case"]: (r["got"], r["pass"]) for r in out["fail_closed"]},
                  "audit_hits": {a["path"].split("/")[-1]: a["hits"] for a in audit}}, ensure_ascii=False))
