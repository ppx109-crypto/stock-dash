"""BASELINE-KIS-DART-AUDIT-0001 · 추가 로컬 실측(사전등록 밖 · 네트워크 없음): 저장 종가가 그 가격대 호가 단위의 배수인가.
공식 원주가 종가는 호가 단위 배수여야 함(2023-01-25 뒤 유가 · 코스닥 같은 표). 배수가 아니면 '원주가 아님'이 증명됨(수정주가 · 반올림 계열).
배수이면 원주가일 수도, 우연히 맞은 수정주가일 수도 있어 UNKNOWN.
python3 -E -P tick_check.py <옛 nrl-cache.pkl> <control_trades.json> <signals_old.json> <PR76 원장> <targets 폴더> <b3> <출력.json>"""
import json, pickle, sys
from pathlib import Path
OLD, CT, SG, L76, TG, B3, OUTF = sys.argv[1:8]
LO, HI = "20250918", "20260331"
def tick(p):
    for lim, t in ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)):
        if p < lim:
            return t
    return 1000
CL = {c: dict(v["rows"]) for c, v in pickle.load(open(OLD, "rb"))[0].items()}
ct, sg, l76 = json.load(open(CT)), json.load(open(SG)), json.load(open(L76))
need = set()
for d, v in sg["picks"].items():
    if LO <= d <= HI:
        need.update((c, d) for c, _ in v)
for k in ("D1", "BASKET"):
    need.update((c, str(t)[:8]) for t, c, *_ in ct[k] if LO <= str(t)[:8] <= HI)
    need.update((c, d) for d, c, s, n in l76[k]["trades"])
on = off = miss = 0
off_codes, on_codes = set(), set()
for c, d in need:
    p = CL.get(c, {}).get(d)
    if p is None:
        miss += 1
        continue
    if abs(p / tick(p) - round(p / tick(p))) < 1e-9:
        on += 1; on_codes.add(c)
    else:
        off += 1; off_codes.add(c)
L = json.load(open(Path(TG, "targets_local_only.json")))
def last_bar(c, d):
    last = None
    for f in sorted(Path(B3, "m15-kis", c).glob("*.csv")):
        for ln in f.read_text(encoding="utf-8").splitlines():
            q = ln.split(",")
            if len(q) == 6 and q[0][:8] == d:
                last = float(q[4])
    return last
mm = []
for c, d in L["mismatch"]:
    dc, lc = CL[c][d], last_bar(c, d)
    mm.append({"abs_diff_won": round(abs(lc - dc), 6), "daily_on_tick": dc % tick(dc) == 0, "bar_on_tick": lc % tick(lc) == 0})
ca_off = sum(1 for c in L["ca"] if c in off_codes)
res = {"denominator_records": len(need), "price_missing": miss, "on_tick(UNKNOWN: 원 또는 수정)": on, "off_tick(원주가 아님 증명)": off,
       "codes": len({c for c, _ in need}), "codes_with_any_off_tick": len(off_codes), "codes_all_on_tick": len(on_codes - off_codes),
       "ca_codes_with_off_tick": f"{ca_off}/{len(L['ca'])}", "m15_mismatch_4": mm,
       "rule": "호가 단위 <2천 1 · <5천 5 · <2만 10 · <5만 50 · <20만 100 · <50만 500 · 그 위 1000(2023-01-25 뒤). 저장값 기준으로 구간을 정함."}
Path(OUTF).write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False))
