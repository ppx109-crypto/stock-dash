"""MPOS-0019 감사 표본 뽑기(AUDIT-PLAN §2 · 수익률 · 연결 풀이 결과를 보지 않음 · 건수 · 상태 · 문단 유무만 읽음).

- 모집단: customer-data/의 state == '받음' 보고서(원본 · 정정). 미해결 · 자료 없음 · 첨부(제외)는 따로 셈.
- 층: 해 묶음(접수 연도 2017~2019 · 2020~2022 · 2023~2026) × 판(원본/정정) × 문단(있음/없음). 문단 유무는 뽑기 층일 뿐 정답 음성 근거가 아님.
- 배분: 비례(가장 큰 나머지 반올림) · 비어 있지 않은 층은 최종 최소 2 · 개발 최소 1.
- 순서: 최종 60을 먼저(층 안 씨앗 섞기 · 이미 쓴 공급사 건너뜀 · 한 공급사 한 보고서) → 최종 공급사를 뺀 채 개발 40.
  층이 모자라면 같은 해 묶음의 이웃 층에서 채우고 기록.
- 독립 감사 20: 최종 60 가운데 씨앗으로 미리 고정.
- 출력: 층별 N_h · n_h · 추출 확률 · 표본 목록 · 최종 목록 지문. --seal 이면 research/customer_sample.json에 씀(봉인 커밋용).
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
    return None


def frame():
    pop, other = [], {}
    for p in sorted(Path("customer-data").glob("[0-9]*.json")):
        body = json.loads(p.read_text(encoding="utf-8"))
        for f in body.get("filings", []):
            st = f.get("state", "")
            if st != "받음":
                key = st.split(" · ")[0]
                other[key] = other.get(key, 0) + 1
                continue
            g = group_of(f["rcept_dt"])
            if g is None:
                other["해 묶음 밖"] = other.get("해 묶음 밖", 0) + 1
                continue
            stratum = f"{g}|{f['kind']}|{'문단있음' if f.get('passages') else '문단없음'}"
            pop.append({"code": body["code"], "rcept_no": f["rcept_no"], "rcept_dt": f["rcept_dt"], "stratum": stratum})
    return pop, other


def allocate(sizes, total, floor):
    keys = [k for k in sorted(sizes) if sizes[k] > 0]
    n = {k: floor for k in keys}
    rest = total - floor * len(keys)
    if rest < 0:
        raise SystemExit("최소 배분이 전체 표본보다 큽니다.")
    big = sum(sizes[k] for k in keys)
    share = {k: rest * sizes[k] / big for k in keys}
    for k in keys:
        n[k] += int(share[k])
    left = total - sum(n.values())
    for k in sorted(keys, key=lambda k: (-(share[k] - int(share[k])), k))[:left]:
        n[k] += 1
    return n


def draw(pop, sizes, want, used, rng_tag):
    by = {}
    for r in pop:
        by.setdefault(r["stratum"], []).append(r)
    for k in by:
        by[k].sort(key=lambda r: (r["code"], r["rcept_no"]))
        random.Random(f"{SEED}|{rng_tag}|{k}").shuffle(by[k])
    picked, borrow = [], []
    for k in sorted(want):
        need = want[k]
        for r in by.get(k, []):
            if need == 0:
                break
            if r["code"] in used:
                continue
            picked.append(r)
            used.add(r["code"])
            need -= 1
        if need:
            g = k.split("|")[0]
            for k2 in sorted(x for x in by if x.startswith(g + "|") and x != k):
                for r in by[k2]:
                    if need == 0:
                        break
                    if r["code"] in used:
                        continue
                    picked.append({**r, "borrowed_for": k})
                    used.add(r["code"])
                    need -= 1
            borrow.append({"stratum": k, "short_after_borrow": need})
    return picked, borrow


def digest(rows):
    return hashlib.sha256(json.dumps([[r["code"], r["rcept_no"]] for r in rows]).encode()).hexdigest()


def main():
    pop, other = frame()
    sizes = {}
    for r in pop:
        sizes[r["stratum"]] = sizes.get(r["stratum"], 0) + 1
    used = set()
    want_f = allocate(sizes, FINAL, 2)
    final, borrow_f = draw(pop, sizes, want_f, used, "final")
    want_d = allocate(sizes, DEV, 1)
    dev, borrow_d = draw(pop, sizes, want_d, used, "dev")
    audit = sorted(final, key=lambda r: (r["code"], r["rcept_no"]))
    random.Random(f"{SEED}|audit").shuffle(audit)
    audit = audit[:AUDIT]
    out = {
        "seed": SEED, "population": len(pop), "not_in_frame": other,
        "strata": {k: {"N": sizes[k], "final_n": want_f.get(k, 0), "dev_n": want_d.get(k, 0),
                       "final_p": round(want_f.get(k, 0) / sizes[k], 6), "dev_p": round(want_d.get(k, 0) / sizes[k], 6)}
                   for k in sorted(sizes)},
        "final": final, "dev": dev, "independent_audit": [[r["code"], r["rcept_no"]] for r in audit],
        "borrow": {"final": borrow_f, "dev": borrow_d},
        "final_sha256": digest(final), "dev_sha256": digest(dev),
    }
    assert not ({r["code"] for r in final} & {r["code"] for r in dev}), "공급사 겹침"
    print(json.dumps({k: out[k] for k in ("population", "not_in_frame", "final_sha256", "dev_sha256")}, ensure_ascii=False))
    print("층", json.dumps({k: (v["N"], v["final_n"], v["dev_n"]) for k, v in out["strata"].items()}, ensure_ascii=False))
    print("최종", len(final), "개발", len(dev), "독립 감사", len(audit), "채움", borrow_f + borrow_d)
    if "--seal" in sys.argv:
        Path("research/customer_sample.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("봉인 파일 씀")
    return 0


if __name__ == "__main__":
    sys.exit(main())
