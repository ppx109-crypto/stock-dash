"""REPLAY-RAW-PRICE-CONTRACT-0001 · 현재 후보(PR #76 고친 일봉) D1 + BASKET 체결 148건 대상 재구성 — 네트워크 없음.
python3 -E -P targets148.py <PR76 fixed_local_only.json> <옛 nrl-cache.pkl> <salt 파일> <공개 출력.json> <로컬 대상 출력.json>
- 체결 = PR #76 원장 trades(날, 종목, 방향, 수량) 그대로 · 체결가 = 그날 저장 종가(PR #76 재생 규칙).
- 호가 판정 = PR #82 tick_check.py · PR #84 pa_audit.py와 같은 표.
- 공개: 개수 · salted hash. 로컬 전용(커밋 안 함): 실제 종목 · 날짜 · 방향 · 수량 · 저장 종가."""
import hashlib, json, pickle, sys
from collections import Counter
from pathlib import Path
L76, OLD, SALT, PUB, LOC = sys.argv[1:6]
salt = Path(SALT).read_text().strip()
H = lambda *x: hashlib.sha256((salt + "|" + "|".join(x)).encode()).hexdigest()[:16]
def tick(p):
    for lim, t in ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)):
        if p < lim:
            return t
    return 1000
on_tick = lambda p: abs(p / tick(p) - round(p / tick(p))) < 1e-9
CL = {c: dict(v["rows"]) for c, v in pickle.load(open(OLD, "rb"))[0].items()}
l76 = json.load(open(L76))
rows = []
for sleeve in ("D1", "BASKET"):
    for i, (d, c, s, n) in enumerate(l76[sleeve]["trades"]):
        p = CL.get(c, {}).get(d)
        cls = "UNKNOWN_MISSING_MAPPING" if p is None else ("UNKNOWN_RAW_OR_ADJUSTED" if on_tick(p) else "IMPOSSIBLE_RAW_FILL")
        rows.append({"fill_id": f"{sleeve}-{i:04d}", "sleeve": sleeve, "date": d, "code": c, "side": s, "qty_adjusted": n,
                     "stored_close": p, "class": cls})
by = Counter(f"{r['sleeve']}_{r['side']}" for r in rows)
cls = Counter(r["class"] for r in rows)
pub = {"fills": len(rows), "by_sleeve_side": dict(by), "classes": dict(cls),
       "unique_code_date": len({(r["code"], r["date"]) for r in rows}), "unique_codes": len({r["code"] for r in rows}),
       "unique_dates": len({r["date"] for r in rows}),
       "off_tick_unique_code_date": len({(r["code"], r["date"]) for r in rows if r["class"] == "IMPOSSIBLE_RAW_FILL"}),
       "salt_sha256": hashlib.sha256(salt.encode()).hexdigest(),
       "target_hashes(fill_id: sha(code|date|side))": {r["fill_id"]: H(r["code"], r["date"], r["side"]) for r in rows},
       "date_range": [min(r["date"] for r in rows), max(r["date"] for r in rows)],
       "scope": "현재 후보(PR #76 일봉 고침) D1 + BASKET만 · 통제는 비교 메타데이터 · 15분봉 제외"}
Path(PUB).write_text(json.dumps(pub, ensure_ascii=False, indent=1))
Path(LOC).write_text(json.dumps(rows, ensure_ascii=False))
print(json.dumps({k: v for k, v in pub.items() if not k.startswith("target_hashes")}, ensure_ascii=False))
