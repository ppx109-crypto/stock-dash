"""MPOS-0019 감사 표본 뽑기(AUDIT-PLAN §2 · 판 2 · GPT #444 round 4 반영) — 수익률 · 연결 풀이 결과를 보지 않음.

두 단계 확률 설계(포함 확률을 정확히 적을 수 있게):
1) 적격 공급사(state == '받음' 보고서가 1개 이상) M개에서 최종 60개 공급사를 단순무작위로 뽑음.
2) 뽑힌 공급사 i의 적격 보고서 R_i개 가운데 1개를 균등하게 뽑음.
   → 보고서 포함 확률 π = (60 / M) × (1 / R_i) · 가중치 = 1 / π.
3) 최종 공급사를 뺀 M − 60개에서 개발 40개 공급사를 같은 방식으로 뽑음: π = (40 / (M − 60)) × (1 / R_i).
4) 독립 감사 20: 최종 60개 공급사에서 단순무작위 20개(그 공급사의 최종 보고서).
- 층(해 묶음 × 원본/정정 × 문단 유무)은 배분에 쓰지 않고, 표본이 층마다 몇 개인지 '범위'로만 보고함.
- 문단 유무는 정답 음성 근거가 아님. 미해결 · 자료 없음 · 첨부(제외)는 모집단 밖으로 따로 셈.
- --seal 이면 research/customer_sample.json에 씀(최종 · 개발 목록과 지문 · 포함 확률). 봉인은 수집이 끝난 뒤 한 번.
"""
import hashlib
import json
import random
import sys
from pathlib import Path

SEED = 20261016
FINAL, DEV, AUDIT = 60, 40, 20
GROUPS = (("2017-2019", 2017, 2019), ("2020-2022", 2020, 2022), ("2023-2026", 2023, 2026))


def group_of(dt):
    y = int(dt[:4])
    for name, a, b in GROUPS:
        if a <= y <= b:
            return name
    return "해 묶음 밖"


def frame():
    by, other = {}, {}
    for p in sorted(Path("customer-data").glob("[0-9]*.json")):
        body = json.loads(p.read_text(encoding="utf-8"))
        for f in body.get("filings", []):
            st = f.get("state", "")
            if st != "받음":
                key = st.split(" · ")[0]
                other[key] = other.get(key, 0) + 1
                continue
            stratum = f"{group_of(f['rcept_dt'])}|{f['kind']}|{'문단있음' if f.get('passages') else '문단없음'}"
            by.setdefault(body["code"], []).append(
                {"code": body["code"], "rcept_no": f["rcept_no"], "rcept_dt": f["rcept_dt"], "stratum": stratum})
    for code in by:
        by[code].sort(key=lambda r: r["rcept_no"])
    return by, other


def pick(by, codes, n, tag):
    pool = sorted(codes)
    random.Random(f"{SEED}|{tag}|suppliers").shuffle(pool)
    chosen = sorted(pool[:n])
    rows = []
    for code in chosen:
        reports = by[code]
        r = random.Random(f"{SEED}|{tag}|report|{code}").choice(reports)
        pi = (n / len(codes)) * (1 / len(reports))
        rows.append({**r, "R_i": len(reports), "pi": pi, "weight": 1 / pi})
    return rows


def digest(rows):
    return hashlib.sha256(json.dumps([[r["code"], r["rcept_no"]] for r in rows]).encode()).hexdigest()


def coverage(rows):
    out = {}
    for r in rows:
        out[r["stratum"]] = out.get(r["stratum"], 0) + 1
    return dict(sorted(out.items()))


def main():
    by, other = frame()
    M = len(by)
    if M < FINAL + DEV:
        raise SystemExit(f"적격 공급사 {M}개 < {FINAL + DEV}개")
    final = pick(by, list(by), FINAL, "final")
    rest = [c for c in by if c not in {r["code"] for r in final}]
    dev = pick(by, rest, DEV, "dev")
    audit_codes = sorted(r["code"] for r in final)
    random.Random(f"{SEED}|audit").shuffle(audit_codes)
    audit = sorted(audit_codes[:AUDIT])
    assert not ({r["code"] for r in final} & {r["code"] for r in dev}), "공급사 겹침"
    pop_strata = {}
    for reports in by.values():
        for r in reports:
            pop_strata[r["stratum"]] = pop_strata.get(r["stratum"], 0) + 1
    out = {
        "seed": SEED, "design": "공급사 단순무작위 → 공급사 안 보고서 1개 균등", "M": M,
        "population_reports": sum(len(v) for v in by.values()), "not_in_frame": other,
        "population_strata": dict(sorted(pop_strata.items())),
        "final": final, "dev": dev, "independent_audit_codes": audit,
        "final_coverage": coverage(final), "dev_coverage": coverage(dev),
        "final_sha256": digest(final), "dev_sha256": digest(dev),
    }
    print(json.dumps({k: out[k] for k in ("M", "population_reports", "not_in_frame", "final_sha256", "dev_sha256")},
                     ensure_ascii=False))
    print("최종 범위", json.dumps(out["final_coverage"], ensure_ascii=False))
    print("최종", len(final), "개발", len(dev), "독립 감사", len(audit))
    if "--seal" in sys.argv:
        Path("research/customer_sample.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("봉인 파일 씀")
    return 0


if __name__ == "__main__":
    sys.exit(main())
