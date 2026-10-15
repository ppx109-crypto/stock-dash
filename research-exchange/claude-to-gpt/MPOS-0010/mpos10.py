"""MPOS-0010 — 새 문 'RM'(GPT #426 G1: 중기 잔차 강세 + 눌림 → RNA 회복) · MPOS-0008 틀(walk · tree_run · 자르기 · 영수증) + rxkit(마른 실행 · 단계별 영수증 · 병렬).
python3 mpos10.py verify → selfcheck → pipeline(build · bases · cut 병렬 · 단계별 영수증) → run(판정)"""
import csv
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0010")
import mix54_run as M  # noqa: E402
import regime_dev as Dv  # noqa: E402
import rxkit as X  # noqa: E402
import jobs10 as J  # noqa: E402
import checks10 as C  # noqa: E402

SP, TREE, WORK, LED, BASES = J.SP, J.TREE, J.WORK, J.LED, J.BASES
P0_CSV = "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
CELLS, CENTER, AB, XS, ALL, SOLO, CUTS, OLD_N, XC = J.CELLS, J.CENTER, J.AB, J.XS, J.ALL, J.SOLO, J.CUTS, J.OLD_N, J.XC
H1_END, H2_BEG, YEAR_MAX = "202112", "202201", 0.5
LOCK = {"/home/user/stock-dash/research/regime_dev.py": "9b8c18720c489707ca6fc0ab71e888cc6a5dab5e54bcd4d6eb20265cd58fe0bc",
        "/home/user/stock-dash/research/mix54_run.py": "b77ba1c1a68d7d6e242f30f4a3ed3c6fc654dd57e3a6dc44ab96852faf7bbd6e",
        P0_CSV: "6bacf87ea66e8cde576e7d8b3cd533e2b18ccd78ed8afdb7e79d5ebb72824531",
        "/tmp/rev-full.pkl": "540114ff96929ceb3e9d6420887e5f5457df4ab65c4457377b9bec13a1fa06a6",
        "/tmp/maxret-0026-cache.pkl": "03dcdd0042b333f5a02e0e65d01518d97ae6efe8e7cb03bb84d4ed3e37b340d7",
        str(SP / "z055_d1_raw.json"): "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"}
TREE_COMMIT = "9743cb80273"
SNAPDIR = HERE / "inputs"
CODE = ("mpos10.py", "jobs10.py", "door.py", "checks10.py", "cost10.py", "tree_run.py", "rxkit.py", "test_door.py", "test_judge10.py", "test_checks10.py", "ref_mods.json")
STAGE = {st: ("door.py", "jobs10.py", "checks10.py", "cost10.py", "tree_run.py", "rxkit.py", "ref_mods.json") for st in ("build", "bases", "cut")}   # 셈 · 검사 코드(판정 코드 mpos10.py는 빠짐)


def code(stage):
    return X.stage_code([str(HERE / f) for f in STAGE[stage]])


def verify(quiet=False):
    got = {f: X.sha(f) for f in LOCK}
    for f in CODE:
        got[f] = X.sha(str(HERE / f))
    lk = json.load(open(HERE / "inputs_lock.json"))
    for f in lk:
        got["inputs/" + f] = X.sha(str(SNAPDIR / f))
    bad = [f for f, v in LOCK.items() if got[f] != v] + [f for f, v in lk.items() if got["inputs/" + f] != v]
    head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
    if not head.startswith(TREE_COMMIT) or dirty:
        bad.append(f"z100 나무 {head[:11]} 깨끗함={not dirty}")
    want = {k: v for k, v in M.ENV_CONTRACT.items() if k != "Z_D1_LED"}
    if any(J.ENV_CONTRACT.get(k) != v for k, v in want.items()):
        bad.append("z100 환경 계약이 MIX-0054와 다름")
    if (HERE / "lock.json").exists():
        reg = json.load(open(HERE / "lock.json"))
        bad += [f for f, v in reg.items() if got.get(f) != v]
    json.dump({"해시": got, "z100 나무": head, "불일치": bad}, open(HERE / "receipt_lock.json", "w"), ensure_ascii=False, indent=1)
    if bad:
        sys.exit(f"잠금 불일치 → 중단: {bad}")
    if not quiet:
        print("잠금 확인 PASS")
    return got


_load0 = Dv.load


def load_snap():
    root0 = Dv.ROOT
    Dv.ROOT = SNAPDIR
    try:
        return _load0()
    finally:
        Dv.ROOT = root0


Dv.load = load_snap


# ───────── 내기 전 · 돌리기 전 점검(rxkit ① ④) ─────────
def selfcheck():
    rows = {}
    for t in ("test_door.py", "test_judge10.py", "test_checks10.py"):
        r = subprocess.run([sys.executable, str(HERE / t)], capture_output=True, text=True)
        rows[t] = {"판정": "PASS" if r.returncode == 0 else "FAIL", "출력": (r.stdout + r.stderr)[-800:]}
    hits = X.lint([str(HERE / f) for f in ("mpos10.py", "jobs10.py", "door.py", "checks10.py", "cost10.py")])
    rows["lint"] = {"판정": "PASS" if not hits else "FAIL", "걸린 것": hits}
    J.WORK.mkdir(parents=True, exist_ok=True)
    J.LED.mkdir(parents=True, exist_ok=True)
    dry = X.dry({"build": J.build_jobs, "bases": J.bases_jobs, "cut": J.cut_jobs, "smoke": J.smoke_jobs}, smoke=J.smoke_jobs(), timeout=900)
    for f in J.LED.glob("*cut20170630*"):
        f.unlink()                                                  # smoke 장부는 손익을 보지 않고 지움
    jobs = {**J.build_jobs(), **J.bases_jobs(), **J.cut_jobs()}
    missing = [f"{n}→{d}" for n, j in jobs.items() for d in j.get("after", []) if d not in jobs]
    rows["dry"] = {"판정": "PASS" if not dry and not missing else "FAIL", "문제": dry + missing, "일감 수": len(jobs)}
    bad = X.write_receipt(str(HERE / "receipt_selfcheck.json"), X.stage_code([str(HERE / f) for f in CODE]), rows)
    print(json.dumps({k: v["판정"] for k, v in rows.items()}, ensure_ascii=False), "일감", rows["dry"]["일감 수"])
    if bad:
        sys.exit(f"selfcheck FAIL {bad}")


# ───────── 셈(병렬 · 단계별 영수증) ─────────
REF = None


def ref():
    global REF
    REF = REF or json.load(open(HERE / "ref_mods.json"))["모듈"]
    return REF


def pipeline():
    WORK.mkdir(parents=True, exist_ok=True)
    LED.mkdir(parents=True, exist_ok=True)
    BASES.mkdir(parents=True, exist_ok=True)
    jobs = {**J.build_jobs(), **J.bases_jobs(), **J.cut_jobs()}
    rc = X.run_dag(jobs, workers=X.CPU, log=lambda m: print(m, flush=True))
    rows = {}
    for c in ALL:
        a, nm = J.door_args(c)
        p, mp = str(LED / f"{nm}.json"), str(LED / f"{nm}.meta.json")
        ok_m, why_m = C.mods_ok(WORK / f"{nm}.mods.json", ref())
        ok_l, why_l, w = (C.ledger_ok(json.load(open(p)), json.load(open(mp)), json.load(open(SP / "z055_d1_raw.json")))
                          if rc.get(f"build:{c}") == 0 and os.path.exists(p) else (False, "결과 없음", None))
        rows[c] = {"rc": rc.get(f"build:{c}"), "칸 최대": w, "판정": "PASS" if ok_m and ok_l else "FAIL", "까닭": f"{why_m} {why_l}".strip(),
                   "파일": {f: X.sha(f) for f in (p, mp) if os.path.exists(f)}}
    bad_all = X.write_receipt(str(HERE / "receipt_build.json"), code("build"), rows)
    rows = {}
    for c in ALL + [s + "_SOLO" for s in SOLO]:
        f = str(BASES / f"{c}.csv")
        ok_m, why = C.mods_ok(BASES / f"{c}.mods.json", ref())
        ok = rc.get(f"bases:{c}") == 0 and os.path.exists(f) and ok_m
        rows[c] = {"rc": rc.get(f"bases:{c}"), "판정": "PASS" if ok else "FAIL", "까닭": why, "파일": {f: X.sha(f)} if os.path.exists(f) else {}}
    for c in CELLS + AB:
        f = str(J.cost_path(c))
        ok_m, why = C.mods_ok(WORK / f"{J.door_args(c)[1]}.cost.mods.json", ref())
        ok = rc.get(f"cost:{c}") == 0 and os.path.exists(f) and ok_m
        rows[f"cost:{c}"] = {"rc": rc.get(f"cost:{c}"), "판정": "PASS" if ok else "FAIL", "까닭": why, "파일": {f: X.sha(f)} if os.path.exists(f) else {}}
    bad_all += X.write_receipt(str(HERE / "receipt_bases.json"), code("bases"), rows)
    rows = {}
    for c in CELLS + AB:
        fp, fm = J.ledger(c), str(J.ledger(c)).replace(".json", ".meta.json")
        full = C.new_rows(json.load(open(fp)), json.load(open(fm))) if os.path.exists(fp) and os.path.exists(fm) else []
        fullnav = C.nav_rows(BASES / f"{c}.csv") if os.path.exists(BASES / f"{c}.csv") else {}
        for ct in CUTS:
            k = f"{c}@{ct}"
            if rc.get(f"cutled:{k}") != 0 or rc.get(f"cutacct:{k}") != 0 or not full or not fullnav:
                rows[k] = {"판정": "FAIL", "까닭": f"rc {rc.get(f'cutled:{k}')} / {rc.get(f'cutacct:{k}')}"}
                continue
            pp = J.ledger(c, ct)
            part = C.new_rows(json.load(open(pp)), json.load(open(str(pp).replace(".json", ".meta.json"))))
            ok, info = C.cut_compare(full, part, fullnav, C.nav_rows(BASES / f"{c}_cut{ct}.csv"), ct)
            ok_m = C.mods_ok(WORK / f"{J.door_args(c, ct)[1]}.mods.json", ref())[0] and C.mods_ok(BASES / f"{c}_cut{ct}.mods.json", ref())[0]
            rows[k] = {**info, "모듈": ok_m, "판정": "PASS" if ok and ok_m else "FAIL"}
    bad_all += X.write_receipt(str(HERE / "receipt_cut.json"), code("cut"), rows)
    fails = [n for n, v in rc.items() if v != 0]
    print("실패 일감", fails[:10], "· 영수증 FAIL", bad_all[:10])
    if fails or bad_all:                                            # 반대 검토 결함 4: 세 영수증 FAIL 모두 종료 코드에
        sys.exit(3)


# ───────── 계좌 · 잣대 ─────────
def account(p):
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(p), None, None
    return Dv.account(CFG)[0]


def mstats(navs):
    ds = sorted(navs)
    r = {ds[j]: navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mo = {}
    for d, x in r.items():
        mo[d[:6]] = mo.get(d[:6], 1) * (1 + x)
    full = {m: v - 1 for m, v in mo.items() if "201703" <= m <= "202608"}
    assert len(full) == 114, len(full)
    pk = mdd = 0
    for d in ds:
        pk = max(pk, navs[d])
        mdd = min(mdd, navs[d] / pk - 1)
    return dict(손실=sum(v < 0 for v in full.values()), 영=sum(v == 0 for v in full.values()), 이익=sum(v > 0 for v in full.values()),
                앞손실=sum(full[m] < 0 for m in full if m <= H1_END), 뒤손실=sum(full[m] < 0 for m in full if m >= H2_BEG), 최악달=min(full.values()) * 100,
                최악날=min(r.values()) * 100, 연_거래일=(navs[ds[-1]] ** (250 / len(ds)) - 1) * 100, MDD=mdd * 100, 달=dict(sorted(full.items())))


def base_stats(p):
    nav = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(p, encoding="utf-8"))}
    nav = {d: v / nav[min(nav)] for d, v in nav.items() if Dv.LO <= d <= Dv.HI}
    return mstats(nav)


def gt(a, b):
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        return False
    return a > b


def trade_stats(rows, meta, cost):
    """새 문 매매: 장부 평균(0.25% 관례) · 비용 대리치 뒤 평균(장부 + 0.25 − cost10 추정 왕복 · 기준 금액 A) · 2배 금액(관문 ⓑ) · 반 금액(보고).
    cost10은 잠재 장부 거래의 근사(GPT #428) — z100 실제 체결 금액 · 비용이 아님."""
    meta = [dict(m, **(k or {})) for m, k in zip(meta, cost)]
    sh = [(r, m) for r, m in zip(rows, meta) if r[2] != "99999999"]

    def one(xs):
        if not xs:
            return dict(건=0, 평균=None, 추정비용뒤=None, 추정비용뒤_2배금액=None)
        led = [r[3] for r, _ in xs]
        net = {k: [r[3] + 0.25 - m[c] for r, m in xs] for k, c in (("기준", "추정왕복비용"), ("2배", "추정왕복비용_2배금액"), ("반", "추정왕복비용_반금액"))}
        w, lo = [p for p in net["기준"] if p > 0], -sum(p for p in net["기준"] if p < 0)
        return dict(건=len(xs), 평균=sum(led) / len(led), 추정비용뒤=sum(net["기준"]) / len(xs), 추정비용뒤_2배금액=sum(net["2배"]) / len(xs),
                    추정비용뒤_반금액=sum(net["반"]) / len(xs), 승률=len(w) / len(xs) * 100, PF=(sum(w) / lo) if lo else None, 합=sum(net["기준"]))
    yrs = {}
    for r, m in sh:
        yrs[r[2][:4]] = yrs.get(r[2][:4], 0.0) + r[3] + 0.25 - m["추정왕복비용"]
    tot = sum(yrs.values())
    MON = [f"{y}{k:02d}" for y in range(2017, 2027) for k in range(1, 13) if "201703" <= f"{y}{k:02d}" <= "202608"]
    q = lambda v, x: sorted(v)[int(x * (len(v) - 1))] if v else None
    betas = [m["β"] for _, m in sh if m.get("β") is not None]
    rep = dict(β_사분위=[q(betas, .25), q(betas, .5), q(betas, .75)], 점수표본_최소=min((m["점수 표본"] for _, m in sh), default=None),
               점수표본_100미만=sum(1 for _, m in sh if m["점수 표본"] < 100), ADV없음대입=sum(1 for _, m in sh if m.get("ADV 없음 대입")),
               비용구성_평균={k: (sum(m[k] for _, m in sh) / len(sh) if sh else None) for k in ("수수료슬리피지", "매도세", "충격")})
    return dict(전체=one(sh), 앞반=one([x for x in sh if x[0][2][:6] <= H1_END]), 뒤반=one([x for x in sh if x[0][2][:6] >= H2_BEG]),
                못판=len(rows) - len(sh), 해마다_비용대리치뒤합=dict(sorted(yrs.items())), 한해몰림=(max(yrs.values()) / tot) if tot > 0 and yrs else None,
                달평균_114분모=sum(1 for r, _ in sh if r[2][:6] in MON) / 114, 거래있는달=len({r[2][:6] for r, _ in sh if r[2][:6] in MON}), 보고=rep)


def nei(c):
    k, h = float(c.split("_")[1][1:]), int(c.split("_")[2][1:])
    i = J.KS.index(k)
    return [f"RM_K{J.KS[i + d]}_H{h}" for d in (-1, 1) if 0 <= i + d < len(J.KS)] + [f"RM_K{k}_H{x}" for x in J.HS if x != h]


def mechanism(R, T):
    """기전(결과 보기 전 고정): 가운데 칸(K1.0 · H20)이 빼기 둘 각각보다 결합 손실 달 ≤ 이고 새 문 추정 비용 뒤 평균이 > 이어야 '지지'."""
    out = {a: dict(손실달_이하=R[CENTER]["손실"] <= R[a]["손실"], 추정비용뒤_큼=gt(T[CENTER]["전체"]["추정비용뒤"], T[a]["전체"]["추정비용뒤"])) for a in AB}
    out["지지"] = all(out[a]["손실달_이하"] and out[a]["추정비용뒤_큼"] for a in AB)
    return out


def judge(R, T, mech):
    b = R["P0"]

    def acct(c):
        x = R[c]
        return (x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"]
                and x["연_거래일"] >= 30.702 and x["최악달"] >= b["최악달"])

    def gate(c):
        x, t = R[c + "_X"], T[c]
        stress = x["최악날"] >= -15 and x["최악달"] >= -15 and x["손실"] < b["손실"] and x["연_거래일"] >= 30.702
        trade = gt(t["앞반"]["추정비용뒤_2배금액"], 0.0) and gt(t["뒤반"]["추정비용뒤_2배금액"], 0.0)   # 근사 금액 차이에 견디게 가장 비싼 쪽(GPT #428)
        year = t["한해몰림"] is not None and t["한해몰림"] <= YEAR_MAX
        return stress and trade and year and mech["지지"]
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연_거래일"] >= 30.702,
               "⑥깊이": R[c]["최악달"] >= b["최악달"], "⑤": all(acct(n) for n in nei(c)), "관문": gate(c)} for c in CELLS}
    ok = [c for c in CELLS if all(why[c].values())]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    return ok, rank, why


def boot(R, c, reps=2000, blk=6, seed=20261016):
    MON = sorted(R["P0"]["달"])
    a, p = [R[c]["달"][m] for m in MON], [R["P0"]["달"][m] for m in MON]
    rnd, n, dl, dr = random.Random(seed), len(MON), [], []
    for _ in range(reps):
        idx = []
        while len(idx) < n:
            s = rnd.randrange(n - blk + 1)
            idx += range(s, s + blk)
        idx = idx[:n]
        dl.append(sum(a[i] < 0 for i in idx) - sum(p[i] < 0 for i in idx))
        dr.append((math.prod(1 + a[i] for i in idx) ** (12 / n) - math.prod(1 + p[i] for i in idx) ** (12 / n)) * 100)
    q = lambda v, x: sorted(v)[int(x * (len(v) - 1))]
    return dict(손실달차_90=[q(dl, .05), q(dl, .95)], 달기하연환산차_90=[q(dr, .05), q(dr, .95)], 묶음=blk, 횟수=reps, 씨앗=seed)


def run():
    for st in ("build", "bases", "cut"):
        why = X.check_receipt(str(HERE / f"receipt_{st}.json"), code(st))
        if why:
            sys.exit(f"{st} 영수증 문제 {why[:3]} → 중단")
    why = X.check_receipt(str(HERE / "receipt_selfcheck.json"), X.stage_code([str(HERE / f) for f in CODE]))
    if why:
        sys.exit(f"selfcheck 영수증 문제 {why[:3]} → 중단")
    R, T, B = {"P0": mstats(account(P0_CSV))}, {}, {"P0": base_stats(P0_CSV)}
    for c in ALL:
        R[c] = mstats(account(BASES / f"{c}.csv"))
        B[c] = base_stats(BASES / f"{c}.csv")
        meta = json.load(open(str(J.ledger(c)).replace(".json", ".meta.json")))
        led = C.new_rows(json.load(open(J.ledger(c))), meta)
        cost = json.load(open(J.cost_path(c))) if c in CELLS + AB else [None] * len(meta)
        T[c] = trade_stats(led, meta, cost) if c in CELLS + AB else {"건": len(led)}
        if c in SOLO:
            T[c]["혼자 계좌"] = {k: v for k, v in base_stats(BASES / f"{c}_SOLO.csv").items() if k != "달"}
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False), flush=True)
    mech = mechanism(R, T)
    ok, rank, why = judge(R, T, mech)
    out = {"P0": R["P0"], "cells": R, "바탕만": B, "매매": T, "기전": mech, "잣대": why, "자격": ok, "순위": rank, "고른 것": rank[0] if rank else None,
           "판정": "SELECTED" if rank else "NO_IMPROVEMENT", "묶음 이어뽑기(보고만)": {c: boot(R, c) for c in CELLS},
           "잠금": json.load(open(HERE / "receipt_lock.json"))["해시"]}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print("기전", mech, "자격", ok, "순위", rank)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    verify(quiet=cmd != "verify")
    if cmd == "selfcheck":
        selfcheck()
    elif cmd == "pipeline":
        why = X.check_receipt(str(HERE / "receipt_selfcheck.json"), X.stage_code([str(HERE / f) for f in CODE]))
        if why:
            sys.exit(f"selfcheck 먼저 {why[:2]}")
        pipeline()
    elif cmd == "p0check":
        print({k: v for k, v in mstats(account(P0_CSV)).items() if k != "달"})
    elif cmd == "run":
        run()
