"""REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001 · 분할/병합 비율 방향 계약 · 합성 검산 · 코드 방향 감사(오프라인).
python3 -I ratio_contract.py <git 저장소 경로> <출력 폴더> <ref…>
- 수식은 사전등록 그대로(Fraction 정확 비교 · 허용 오차 없음). 합성 숫자는 실제 종목 아님.
- 코드 감사는 로컬 git grep만(네트워크 0)."""
import json
import math
import re
import socket
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
REPO, OUT, REFS = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]


def _num(x):
    """정수 · Fraction · '정수/정수' 문자열만 받음. float(단위 · 반올림 불명) · None · NaN · inf는 거부."""
    if x is None:
        return None, "UNKNOWN_MISSING"
    if isinstance(x, bool):
        return None, "UNKNOWN_TYPE"
    if isinstance(x, float):
        return None, "UNKNOWN_NONFINITE" if not math.isfinite(x) else "UNKNOWN_FLOAT_INPUT"
    if isinstance(x, (int, Fraction)):
        v = Fraction(x)
    elif isinstance(x, str) and re.fullmatch(r"-?\d+(/\d+)?", x.replace(",", "")):
        v = Fraction(x.replace(",", ""))
    else:
        return None, "UNKNOWN_TYPE"
    if v == 0:
        return None, "UNKNOWN_ZERO"
    if v < 0:
        return None, "UNKNOWN_NEGATIVE"
    return v, None


def ratio_contract(q0, q1, f0, f1, kind):
    vals = {}
    for k, x in (("q0", q0), ("q1", q1), ("f0", f0), ("f1", f1)):
        v, why = _num(x)
        if why:
            return {"status": why, "field": k}
        vals[k] = v
    m_qty = vals["q1"] / vals["q0"]
    m_face = vals["f0"] / vals["f1"]
    if m_qty != m_face:
        return {"status": "UNKNOWN_RATIO_MISMATCH", "m_qty": str(m_qty), "m_face": str(m_face)}
    if m_qty == 1:
        return {"status": "UNKNOWN_NO_CHANGE", "m_qty": "1"}
    if kind == "split" and not m_qty > 1 or kind == "reverse_split" and not m_qty < 1 or kind not in ("split", "reverse_split"):
        return {"status": "UNKNOWN_DIRECTION_CONTRADICTION", "kind": kind, "m_qty": str(m_qty)}
    m_price = 1 / m_qty
    assert m_price == vals["q0"] / vals["q1"] == vals["f1"] / vals["f0"]
    return {"status": "ACCEPT", "m_qty": m_qty, "m_price": m_price}


def convert(qty, price, c):
    """보유 전환(단주 · 비용 · 현금보상 전). 정수 아니면 UNKNOWN_CASH_IN_LIEU · 적용 안 함."""
    if c["status"] != "ACCEPT":
        return {"status": "NOT_APPLIED", "why": c["status"]}
    q1 = Fraction(qty) * c["m_qty"]
    p1 = Fraction(price) * c["m_price"]
    if q1.denominator != 1:
        return {"status": "UNKNOWN_CASH_IN_LIEU", "qty_after_exact": str(q1), "why": "단주 발생 — 처리 규칙 추정 안 함 · 회계/NAV 미적용"}
    return {"status": "OK", "qty_after": int(q1), "price_after": str(p1), "value_before": str(Fraction(qty) * Fraction(price)),
            "value_after": str(q1 * p1), "value_preserved": Fraction(qty) * Fraction(price) == q1 * p1}


def apply_to_ledger(c, price_basis_date_status):
    """계약이 ACCEPT여도 적용일이 BLOCKED면 어느 원장에도 적용하지 않음."""
    if price_basis_date_status != "ACCEPT":
        return "APPLY_BLOCKED_NO_PRICE_BASIS_DATE"
    return "APPLY_ALLOWED" if c["status"] == "ACCEPT" else "APPLY_BLOCKED_" + c["status"]


# ── 합성 검산(기대값 먼저) ──
CASES = [
    # (이름, q0, q1, f0, f1, kind, 보유 qty, 가격, 기대 status, 기대 m_qty, 기대 m_price, 기대 전환)
    ("split_1to5", 1_000_000, 5_000_000, 5000, 1000, "split", 37, 52300, "ACCEPT", "5", "1/5", ("OK", 185, "10460")),
    ("split_1to10", 2_400_000, 24_000_000, 500, 50, "split", 3, 812000, "ACCEPT", "10", "1/10", ("OK", 30, "81200")),
    ("reverse_10to1", 12_345_670, 1_234_567, 100, 1000, "reverse_split", 120, 1234, "ACCEPT", "1/10", "10", ("OK", 12, "12340")),
    ("reverse_5to1", 50_000_000, 10_000_000, 200, 1000, "reverse_split", 75, 905, "ACCEPT", "1/5", "5", ("OK", 15, "4525")),
    ("fail_mismatch", 1_000_000, 5_000_000, 5000, 500, "split", 10, 1000, "UNKNOWN_RATIO_MISMATCH", None, None, ("NOT_APPLIED",)),
    ("fail_reverse_rounding_1share", 12_345_678, 1_234_567, 100, 1000, "reverse_split", 10, 1000, "UNKNOWN_RATIO_MISMATCH", None, None, ("NOT_APPLIED",)),
    ("fail_zero_f1", 1_000_000, 5_000_000, 5000, 0, "split", 10, 1000, "UNKNOWN_ZERO", None, None, ("NOT_APPLIED",)),
    ("fail_negative_q0", -1_000_000, 5_000_000, 5000, 1000, "split", 10, 1000, "UNKNOWN_NEGATIVE", None, None, ("NOT_APPLIED",)),
    ("fail_missing_q1", 1_000_000, None, 5000, 1000, "split", 10, 1000, "UNKNOWN_MISSING", None, None, ("NOT_APPLIED",)),
    ("fail_nan", 1_000_000, float("nan"), 5000, 1000, "split", 10, 1000, "UNKNOWN_NONFINITE", None, None, ("NOT_APPLIED",)),
    ("fail_float_input", 1_000_000, 5_000_000.0, 5000, 1000, "split", 10, 1000, "UNKNOWN_FLOAT_INPUT", None, None, ("NOT_APPLIED",)),
    ("fail_no_change", 1_000_000, 1_000_000, 5000, 5000, "split", 10, 1000, "UNKNOWN_NO_CHANGE", None, None, ("NOT_APPLIED",)),
    ("fail_direction_split_label", 5_000_000, 1_000_000, 1000, 5000, "split", 10, 1000, "UNKNOWN_DIRECTION_CONTRADICTION", None, None, ("NOT_APPLIED",)),
    ("fail_direction_reverse_label", 1_000_000, 5_000_000, 5000, 1000, "reverse_split", 10, 1000, "UNKNOWN_DIRECTION_CONTRADICTION", None, None, ("NOT_APPLIED",)),
    ("fail_fractional_holding", 50_000_000, 5_000_000, 500, 5000, "reverse_split", 7, 1000, "ACCEPT", "1/10", "10", ("UNKNOWN_CASH_IN_LIEU",)),
]
results = []
for name, q0, q1, f0, f1, kind, hq, hp, e_st, e_mq, e_mp, e_conv in CASES:
    c = ratio_contract(q0, q1, f0, f1, kind)
    v = convert(hq, hp, c)
    got = [c["status"], str(c["m_qty"]) if "m_qty" in c and c["status"] == "ACCEPT" else None,
           str(c["m_price"]) if c.get("m_price") is not None else None,
           tuple([v["status"]] + ([v["qty_after"], v["price_after"]] if v["status"] == "OK" else []))]
    exp = [e_st, e_mq, e_mp, e_conv]
    row = {"case": name, "inputs": {"q0": str(q0), "q1": str(q1), "f0": str(f0), "f1": str(f1), "kind": kind, "hold_qty": hq, "hold_price": hp},
           "expect": [exp[0], exp[1], exp[2], list(exp[3])], "got": [got[0], got[1], got[2], list(got[3])], "pass": exp == got,
           "detail": {k: (str(x) if isinstance(x, Fraction) else x) for k, x in c.items()}, "conversion": v}
    if v.get("status") == "OK":
        row["pass"] = row["pass"] and v["value_preserved"]
    results.append(row)

# 반대 방향(가격 × 주식수 배율) 오류의 크기 — PR #94 경고 재현
c5 = ratio_contract(1_000_000, 5_000_000, 5000, 1000, "split")
wrong_p = Fraction(52300) * c5["m_qty"]
wrong = {"case": "WRONG_price_times_m_qty(PR94 경고)", "qty_after": 185, "price_after_wrong": str(wrong_p),
         "value_before": 37 * 52300, "value_after_wrong": str(185 * wrong_p), "inflation_factor": str((185 * wrong_p) / (37 * 52300))}

truth = {"split": {"m_qty": "> 1", "m_price": "0 < m_price < 1", "qty": "증가", "price": "감소"},
         "reverse_split": {"m_qty": "0 < m_qty < 1", "m_price": "> 1", "qty": "감소", "price": "증가"},
         "m_qty == 1": "UNKNOWN_NO_CHANGE(분할 · 병합으로 ACCEPT 안 함)",
         "사건명 ↔ 방향 모순": "UNKNOWN_DIRECTION_CONTRADICTION(값을 뒤집어 맞추지 않음)"}
truth_check = {r["case"]: (r["got"][0] == "ACCEPT" and ((r["inputs"]["kind"] == "split" and Fraction(r["got"][1]) > 1 and 0 < Fraction(r["got"][2]) < 1) or
                                                      (r["inputs"]["kind"] == "reverse_split" and 0 < Fraction(r["got"][1]) < 1 and Fraction(r["got"][2]) > 1)))
               for r in results if r["got"][0] == "ACCEPT"}
proof = ("qty_after × price_after = (qty × m_qty) × (price × m_price) = qty × price × (m_qty × m_price) = qty × price × 1 "
         "(m_price = 1/m_qty, 유리수 등식 · 단주 · 비용 · 현금보상 전)")
apply_demo = {"ACCEPT_contract_with_price_basis_BLOCKED": apply_to_ledger(c5, "BLOCKED_NO_OFFICIAL_EVIDENCE"),
              "current_price_basis_date_status(PR94)": "BLOCKED_NO_OFFICIAL_EVIDENCE"}
contract = {"symbols": {"q0,q1": "전/후 발행주식총수", "f0,f1": "전/후 1주당 가액", "m_qty": "q1/q0", "m_face": "f0/f1", "m_price": "1/m_qty = q0/q1 = f1/f0"},
            "accept_rule": "양수 · 정수/유리수 · 누락 없음 · m_qty == m_face(정확) · m_qty ≠ 1 · 사건명과 방향 일치",
            "truth_table": truth, "truth_check": truth_check, "value_preservation_proof": proof,
            "synthetic_cases": results, "wrong_direction_demo": wrong, "apply_gate": apply_demo,
            "fail_closed": ["UNKNOWN_MISSING", "UNKNOWN_ZERO", "UNKNOWN_NEGATIVE", "UNKNOWN_NONFINITE", "UNKNOWN_FLOAT_INPUT", "UNKNOWN_TYPE",
                            "UNKNOWN_RATIO_MISMATCH", "UNKNOWN_NO_CHANGE", "UNKNOWN_DIRECTION_CONTRADICTION", "UNKNOWN_CASH_IN_LIEU",
                            "APPLY_BLOCKED_NO_PRICE_BASIS_DATE"],
            "coverage_cost": "병합 뒤 발행주식총수가 회사 단위 단주 처리로 1주라도 어긋나면(fail_reverse_rounding_1share) 정확 비교 규칙이 UNKNOWN으로 막음 — 실제 병합 공시 상당수가 이 경로로 UNKNOWN이 될 수 있음(허용 오차는 이번에 정하지 않음)",
            "pass": all(r["pass"] for r in results) and all(truth_check.values()) and apply_demo["ACCEPT_contract_with_price_basis_BLOCKED"] == "APPLY_BLOCKED_NO_PRICE_BASIS_DATE",
            "evidence_tier": {"fields": "GPT_CAPTURED_OFFICIAL_INDEX(KIND 70128/70129 필드명)", "formula": "DERIVATION", "real_events": "UNVERIFIED"}}

# ── 코드 · 문서 방향 감사(로컬 git grep) ──
PAT = r"ratio|prtt|분할|병합|액면|split"
hits = []
for ref in REFS:
    p = subprocess.run(["git", "-C", REPO, "grep", "-n", "-I", "-i", "-E", PAT, ref, "--", "*.py"], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        hits.append((ref, line))
CLASS = [
    (r"Fraction\(q\[c\]\) \* Fraction\(str\(e\[\"ratio\"\]\)\)|q\[c\] \* e\[\"ratio\"\]", "수량 × 수량 배율(올바름)"),
    (r"\"종가\": c / 2", "가격 ÷ 2 = 가격 × 역수(2:1 분할 · 올바름)"),
    (r"목표가 ÷ 수정 종가", "경험적 재배율(분할 비율 미사용 · 무관)"),
    (r"(price|close|clpr|px|종가)[^#\n]{0,30}\*[^#\n]{0,15}(ratio|prtt|m_qty)", "가격 × 주식수 배율(반대 방향 의심)"),
]
audit = []
for ref, line in hits:
    lab = next((c for pat, c in CLASS if re.search(pat, line)), None)
    if lab:
        audit.append({"ref": ref.split("/")[-1], "where": line.split(":", 2)[1] + ":" + line.split(":", 2)[2].split(":", 1)[0], "text": line.split(":", 3)[-1].strip()[:200], "direction": lab})
opposite = [a for a in audit if "반대 방향" in a["direction"]]
code_audit = {"refs": REFS, "pattern": PAT, "raw_hits": len(hits), "classified": audit, "opposite_direction_found": len(opposite),
              "ratio_semantics_in_schema": "PR #86 · #88 스키마 ratio = '기존 1주당 효력 후 주식 수'(= m_qty) — 가격 배율 아님",
              "prtt_rate": "KIS prtt_rate('분할 비율')는 값 방향 미확인(PR #90 NEEDS_DATA) → 이 계약에 쓰지 않음"}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "ratio-direction-contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=1, default=str))
(OUT / "code-direction-audit.json").write_text(json.dumps(code_audit, ensure_ascii=False, indent=1))
print(json.dumps({"cases": {r["case"]: r["pass"] for r in results}, "truth_ok": all(truth_check.values()), "apply_gate": apply_demo["ACCEPT_contract_with_price_basis_BLOCKED"],
                  "wrong_factor": wrong["inflation_factor"], "contract_pass": contract["pass"], "audit_hits": len(hits),
                  "audit_classified": [(a["ref"], a["where"], a["direction"]) for a in audit], "opposite": len(opposite)}, ensure_ascii=False))
