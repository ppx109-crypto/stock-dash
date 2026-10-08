"""BASELINE-KIS-DART-AUDIT-0001 · 고정 대상 목록(비식별 해시) 만들기 — 네트워크 없음.
python3 -E -P targets.py <PR80 실행에 쓴 입력: control_trades.json> <PR76 원장> <옛 nrl-cache.pkl> <b2> <b3> <출력 폴더>
대상: PR #80 '체결 종목 39개'(D1 · 바구니 통제/후보 체결) · 그중 기업행동 공시 8종목 · 15분봉 통제 매수 체결일 82건 중 봉 마지막 종가 ≠ 일봉 종가 4건.
해시 = sha256(salt + 코드 + 날짜) · salt는 로컬에만(공개는 salt의 sha256만)."""
import bisect, hashlib, json, os, pickle, secrets, sys
from pathlib import Path
CT, L76, OLD, B2, B3, OUT = sys.argv[1:7]
OUT = Path(OUT); OUT.mkdir(parents=True, exist_ok=True)
LO, HI = "20250918", "20260331"
salt_p = OUT / "salt_local_only.txt"
if not salt_p.exists():
    salt_p.write_text(secrets.token_hex(16))
salt = salt_p.read_text().strip()
h = lambda *x: hashlib.sha256((salt + "|" + "|".join(x)).encode()).hexdigest()[:16]
ct = json.load(open(CT)); l76 = json.load(open(L76))
CL = {c: dict(v["rows"]) for c, v in pickle.load(open(OLD, "rb"))[0].items()}
traded = sorted({c for k in ("D1", "BASKET") for t, c, *_ in ct[k] if LO <= str(t)[:8] <= HI} |
                {c for k in ("D1", "BASKET") for d, c, s, n in l76[k]["trades"]})
CA = ("감자", "분할", "합병", "무상증자", "유상증자", "유무상증자")
ca_codes = []
for c in traded:
    p = Path(B2, "dart-events", f"{c}.json")
    if p.exists():
        rows = json.load(open(p))["rows"]
        if any(LO <= str(r.get("rcept_no", ""))[:8] <= "20261007" for k in CA for r in rows.get(k) or []):
            ca_codes.append(c)
# 15분봉 불일치: 통제 M15 매수 체결일의 그날 마지막 15분봉 종가 대 일봉 종가(옛 캐시)
def bars(code, day):
    out = []
    for f in sorted(Path(B3, "m15-kis", code).glob("*.csv")):
        for ln in f.read_text(encoding="utf-8").splitlines():
            p = ln.split(",")
            if len(p) == 6 and p[0][:8] == day:
                out.append((p[0], float(p[1]), float(p[2]), float(p[3]), float(p[4]), float(p[5])))
    return sorted(out)
mm, n82 = [], 0
for t, c, s, n, px in ct["M15"]:
    if s != "buy" or not (LO <= t[:8] <= HI):
        continue
    n82 += 1
    b = bars(c, t[:8])
    dc = CL.get(c, {}).get(t[:8])
    if b and dc and abs(b[-1][4] - dc) >= 1e-6:
        mm.append((c, t[:8]))
tg = {"traded_codes": len(traded), "ca_codes": len(ca_codes), "m15_buy_fill_days": n82, "m15_mismatch_cases": len(mm),
      "salt_sha256": hashlib.sha256(salt.encode()).hexdigest(),
      "hash_traded": sorted(h(c) for c in traded), "hash_ca": sorted(h(c) for c in ca_codes),
      "hash_m15_mismatch(code|date)": sorted(h(c, d) for c, d in mm)}
(OUT / "targets_public.json").write_text(json.dumps(tg, ensure_ascii=False, indent=1))
(OUT / "targets_local_only.json").write_text(json.dumps({"traded": traded, "ca": ca_codes, "mismatch": mm}, ensure_ascii=False))
print(json.dumps({k: v for k, v in tg.items() if not k.startswith("hash")}, ensure_ascii=False))
