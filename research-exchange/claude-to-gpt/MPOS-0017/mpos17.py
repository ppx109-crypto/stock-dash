"""MPOS-0017: 쉬는 현금을 단기채권 ETF(153130)에 두기(z100의 기존 Z_PARK 기능 · 엔진 수정 없음).
칸: PARK = MPOS-0012 REPRO_G(원 장부 · z100g 같은 날 비율 배정)에 Z_PARK=1만 켬 · 기준선 = REPRO_G(바이트 같은지 재현 확인).
z100 PARK: 그날 끝 현금을 153130에 둠 → 다음 날 그 ETF 하루 수익 · 둔 금액 변화에 편도 0.065% 비용. 덧붙임(regime_dev)은 바탕 csv의 현금 칸을 보며, PARK는 현금 칸을 바꾸지 않음(이자만 NAV에 더함).
python3 mpos17.py build | cutacct | run"""
import csv
import json
import math
import os
import sys
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos17")
M12 = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8/research-exchange/claude-to-gpt/MPOS-0012")
sys.path.insert(0, str(M12))
import mpos12 as M  # noqa: E402

X = M.X
CELLS = {"BASE": {}, "PARK": {"Z_PARK": "1"}}


def verify():
    lock = M.verify()
    lock["mpos17.py"] = X.sha(str(HERE / "mpos17.py"))
    if not (HERE / "lock.json").exists():
        sys.exit("lock.json 없음 → 중단")
    bad = [f for f, v in json.load(open(HERE / "lock.json")).items() if lock.get(f) != v]
    if bad:
        sys.exit(f"잠금 불일치 → 중단 {bad}")
    return lock


def build():
    lock = verify()
    rb12 = json.load(open(M12 / "receipt_build.json"))
    led = M.WORK / "led_REPRO_G.json"
    assert X.sha(str(led)) == rb12["REPRO_G"]["장부 지문"]
    jobs = {}
    for c, extra in CELLS.items():
        env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
        env.update(M.ENV)
        env.update(Z_D1_LED=str(led), Z_OUT=str(HERE / f"base_{c}.csv"), **extra)
        jobs[c] = dict(cmd=[sys.executable, str(M.TREE_RUN), str(HERE / f"base_{c}.mods.json"), str(M.Z100G)], env=env, cwd=str(M.TREE),
                       out=str(HERE / f"base_{c}.log"), clean=[str(HERE / f"base_{c}.csv")])
    bad = X.dry({"z100g": lambda: jobs})
    if bad:
        sys.exit(f"마른 실행 FAIL {bad}")
    rc = X.run_dag(jobs, workers=2, log=lambda m: print(m, flush=True))
    rec = {}
    for c in jobs:
        f = HERE / f"base_{c}.csv"
        mods = json.load(open(HERE / f"base_{c}.mods.json")) if (HERE / f"base_{c}.mods.json").exists() else {"바깥": ["없음"]}
        rec[c] = {"rc": rc[c], "바탕 지문": X.sha(str(f)) if f.exists() else None, "판정": "PASS" if rc[c] == 0 and f.exists() and not mods["바깥"] else "FAIL"}
    rec["BASE"]["REPRO_G와 같음"] = rec["BASE"]["바탕 지문"] == rb12["REPRO_G"]["바탕 지문"]
    if not rec["BASE"]["REPRO_G와 같음"]:
        rec["BASE"]["판정"] = "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_build.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rec, ensure_ascii=False))
    if any(r["판정"] != "PASS" for r in rec.values()):
        sys.exit(3)


def cutacct():
    lock = verify()
    rb = json.load(open(HERE / "receipt_build.json"))["행"]
    out = []
    for c in CELLS:
        f = HERE / f"base_{c}.csv"
        assert X.sha(str(f)) == rb[c]["바탕 지문"]
        full = M.account(f)
        for ct in M.CUTS:
            M.Dv.CUT = ct
            part = M.account(f)
            M.Dv.CUT, M.Dv.DATA, M.Dv.FEAT = "", None, None
            dd = [d for d in full if d <= ct]
            ok = bool(dd) and max(part) <= ct and all(part.get(d) == full[d] for d in dd)
            out.append({"칸": c, "자른 날": ct, "판정": "PASS" if ok else "FAIL"})
    json.dump({"잠금": lock, "행": out}, open(HERE / "receipt_cutacct.json", "w"), ensure_ascii=False, indent=1)
    print(sum(x["판정"] == "PASS" for x in out), "/", len(out))
    if any(x["판정"] != "PASS" for x in out):
        sys.exit(3)


def run():
    lock = verify()
    for nm, n in (("receipt_build.json", 2), ("receipt_cutacct.json", 6)):
        r = json.load(open(HERE / nm))
        rows = list(r["행"].values()) if isinstance(r["행"], dict) else r["행"]
        if r["잠금"]["mpos17.py"] != lock["mpos17.py"] or len(rows) != n or any(x["판정"] != "PASS" for x in rows):
            sys.exit(f"{nm} 문제 → 중단")
    rb = json.load(open(HERE / "receipt_build.json"))["행"]
    for c in CELLS:
        if X.sha(str(HERE / f"base_{c}.csv")) != rb[c]["바탕 지문"]:
            sys.exit(f"{c} 지문 다름 → 중단")
    R = {c: M.mstats(M.account(HERE / f"base_{c}.csv")) for c in CELLS}
    b = R["BASE"]
    assert b["손실"] == 40 and b["앞손실"] == 20 and b["뒤손실"] == 20 and abs(b["최악달"] + 13.756) < 1e-3 and abs(b["연_거래일"] - 35.02) < 0.01, b
    x = R["PARK"]
    why = {"①": x["최악날"] >= -15 and x["최악달"] >= -15, "②": x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"],
           "③": x["손실"] < b["손실"], "④": x["연_거래일"] >= 30.702, "⑥깊이": x["최악달"] >= b["최악달"]}
    ok = all(why.values())
    bm, pm = b["달"], x["달"]
    rows = list(csv.DictReader(open(HERE / "base_PARK.csv")))
    out = {"cells": R, "잣대": why, "판정": "SELECTED(작은 기계적 개선 · 이웃 · 기전 없음 칸)" if ok else "NO_IMPROVEMENT",
           "부호 바뀐 달": {"손실→이익": [m for m in bm if bm[m] < 0 and pm[m] > 0], "이익→손실": [m for m in bm if bm[m] > 0 and pm[m] < 0]},
           "달 평균 차 %p": round(sum(pm[m] - bm[m] for m in bm) / len(bm) * 100, 4),
           "바탕 비용 누계(원) BASE · PARK": [float(list(csv.DictReader(open(HERE / "base_BASE.csv")))[-1]["비용누계"]), float(rows[-1]["비용누계"])],
           "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in CELLS:
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False))
    print(out["잣대"], out["판정"], out["부호 바뀐 달"], out["달 평균 차 %p"], out["바탕 비용 누계(원) BASE · PARK"])


if __name__ == "__main__":
    {"build": build, "cutacct": cutacct, "run": run}[sys.argv[1]]()
