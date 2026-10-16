"""MPOS-0017 round 2(GPT #442): 쉬는 현금을 단기채권 ETF(153130)에 — **덧붙임 계좌의 최종 잔여 현금에만**(park17.py).
칸: BASE = REPRO_G 바탕 + 덧붙임(OFF · 원판 NAV와 날마다 같음) · PARK · ZERO(153130 수익 0 · 비용만 · 기전 대조).
python3 mpos17.py check | run"""
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos17")
sys.path.insert(0, str(HERE))
import park17 as P  # noqa: E402

M, X = P.M, P.M.X
BASE_CSV = M.WORK / "base_REPRO_G.csv"
CUTS = ("20211231", "20240628", "20200303")


def verify():
    lock = M.verify()
    lock.update({"mpos17.py": X.sha(str(HERE / "mpos17.py")), "park17.py": X.sha(str(HERE / "park17.py")),
                 "153130.json": X.sha(str(P.BOND_PATH)), "base_REPRO_G.csv": X.sha(str(BASE_CSV))})
    rb12 = json.load(open(P.M12 / "receipt_build.json"))
    assert lock["base_REPRO_G.csv"] == rb12["REPRO_G"]["바탕 지문"]
    if not (HERE / "lock.json").exists():
        sys.exit("lock.json 없음 → 중단")
    bad = [f for f, v in json.load(open(HERE / "lock.json")).items() if lock.get(f) != v]
    if bad:
        sys.exit(f"잠금 불일치 → 중단 {bad}")
    return lock


def check():
    """성과 출력 없음: OFF 재현 · 153130 빈 날 · 독 시험(자른 날 뒤 153130 × 0.9 → 그날까지 NAV 같음 · 뒤는 달라짐) · 빚 없음."""
    lock = verify()
    off = M.account(BASE_CSV)
    o2, oi = P.run_park(BASE_CSV, "OFF")
    full, fi = P.run_park(BASE_CSV, "PARK")
    rec = {"OFF 재현(날마다 같음)": o2 == off, "날 수": len(off), "PARK 153130 빈 날(두 날 중 하나 없음)": fi["miss"], "PARK 셈한 날": fi["days"],
           "PARK 빚 없음(min_slack ≥ 0)": fi["min_slack"] >= -1e-12, "독": []}
    for ct in CUTS:
        part, _ = P.run_park(BASE_CSV, "PARK", poison=ct)
        dd = [d for d in full if d <= ct]
        same = all(part[d] == full[d] for d in dd)
        diff_after = any(part[d] != full[d] for d in full if d > ct)
        rec["독"].append({"자른 날": ct, "날": len(dd), "그날까지 같음": same, "뒤는 달라짐": diff_after, "판정": "PASS" if same and diff_after else "FAIL"})
    ok = rec["OFF 재현(날마다 같음)"] and rec["PARK 빚 없음(min_slack ≥ 0)"] and all(x["판정"] == "PASS" for x in rec["독"])
    rec["판정"] = "PASS" if ok else "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_check.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rec.items()}, ensure_ascii=False))
    if not ok:
        sys.exit(3)


def run():
    lock = verify()
    r = json.load(open(HERE / "receipt_check.json"))
    if r["잠금"]["mpos17.py"] != lock["mpos17.py"] or r["잠금"]["park17.py"] != lock["park17.py"] or r["행"]["판정"] != "PASS":
        sys.exit("검사 영수증 문제 → 중단")
    navs = {"BASE": M.account(BASE_CSV)}
    info = {}
    for c, mode in (("PARK", "PARK"), ("ZERO", "ZERO")):
        navs[c], info[c] = P.run_park(BASE_CSV, mode)
    R = {c: M.mstats(v) for c, v in navs.items()}
    b, x, z = R["BASE"], R["PARK"], R["ZERO"]
    assert b["손실"] == 40 and b["앞손실"] == 20 and b["뒤손실"] == 20 and abs(b["최악달"] + 13.756) < 1e-3 and abs(b["연_거래일"] - 35.02) < 0.01, b
    why = {"①": x["최악날"] >= -15 and x["최악달"] >= -15, "②": x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"],
           "③": x["손실"] < b["손실"], "④": x["연_거래일"] >= 30.702, "⑥깊이": x["최악달"] >= b["최악달"],
           "기전(PARK가 ZERO보다 손실 달 ≤ · 연 >)": x["손실"] <= z["손실"] and M.gt(x["연_거래일"], z["연_거래일"])}
    ok = all(why.values())
    bm, pm = b["달"], x["달"]
    out = {"cells": R, "잣대": why, "판정": "SELECTED(작은 기계적 개선 · 이웃 없는 켬/끔 칸)" if ok else "NO_IMPROVEMENT",
           "부호 바뀐 달(BASE → PARK)": {"손실→이익": [m for m in bm if bm[m] < 0 and pm[m] > 0], "이익→손실": [m for m in bm if bm[m] > 0 and pm[m] < 0]},
           "달 평균 차 %p(PARK − BASE)": round(sum(pm[m] - bm[m] for m in bm) / len(bm) * 100, 4),
           "주차 합계(계좌 1 시작 · 이자 · 비용 · 빈 날 · 빚 없음)": info, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in R:
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False))
    print(why, out["판정"], out["부호 바뀐 달(BASE → PARK)"], out["달 평균 차 %p(PARK − BASE)"], info)


if __name__ == "__main__":
    {"check": check, "run": run}[sys.argv[1]]()
