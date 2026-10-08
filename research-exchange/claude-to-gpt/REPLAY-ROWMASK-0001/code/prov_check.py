"""출처 확인: 고정 엔진 코드(b2) + 2026-09-25 저장소 자료(V)로 일부 종목 줄을 만들어 옛 캐시(PR68 입력) 줄과 견줌. 읽기만."""
import json, pickle, sys, os
from collections import Counter
B2, V, OLD = sys.argv[1:4]
sys.path.insert(0, B2)
os.chdir(V)
import lab, study, caps, rule
o = pickle.load(open(OLD, "rb"))
oi = {(r["code"], r["date"]): r for r in o[4] if "20250801" <= r["date"] <= "20260916"}
codes = sorted({c for c, _ in oi})
P = study.load_prices()
diff, same, miss = Counter(), 0, 0
dcodes = Counter()
for s in range(0, len(codes), 25):
    part = {c: P[c] for c in codes[s:s + 25] if c in P}
    rows = [r for r in lab.build(part, horizons=(5, 10, 20, 60)) if "20250801" <= r["date"] <= "20260916"]
    got = {(r["code"], r["date"]): r for r in rows}
    for k, a in oi.items():
        if k[0] not in part:
            continue
        b = got.get(k)
        if b is None:
            miss += 1
            continue
        bad = [f for f in (set(a) | set(b)) - {"ahead", "i", caps.SIZE, caps.RANK} if a.get(f) != b.get(f)]
        if bad:
            for f in bad:
                diff[f] += 1
            dcodes[k[0]] += 1
        else:
            same += 1
print(json.dumps({"compared_rows": len(oi), "same_rows": same, "missing_in_V_build": miss, "field_diffs": dict(diff),
                  "diff_codes": dict(dcodes)}, ensure_ascii=False))
