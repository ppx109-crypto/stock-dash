"""MPOS-0008 — 1일봉 업그레이드(사용자 H3) 통합 사전등록 셈: G1 '2N 칸 나눔'(GPT #420 G1) · G2 '시장 대비 과매도 → RNA 회복 확인' 새 문(GPT G2 + 클로드 H1).
흐름: door.py 장부 → z100(MIX-0054 결과 커밋 9743cb802 나무 그대로 · 바탕 d0.5_b0.3 · 15분봉 뺌) → 덧붙임 P0(L0.4_S0.4 · regime_dev) → 114달 잣대.
python3 mpos8.py verify | build | bases | p0check | run | cut"""
import hashlib
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0008")
import mix54_run as M  # noqa: E402
import regime_dev as Dv  # noqa: E402

HERE = Path(__file__).resolve().parent
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
WORK = SP / "mpos8"
TREE = SP / "m54tree"
LED, BASES = WORK / "ledgers", WORK / "bases"
P0_CSV = "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
KS, HS, XC = (1.5, 2.0, 2.5), (5, 10), 0.0025                     # G2 격자 · 비용 스트레스(왕복 +0.25%p = 기존 뺌의 2배)
G2 = [f"G2_K{k}_H{h}" for k in KS for h in HS]                    # 고를 수 있는 칸 6
AB = ["AB_RAW", "AB_NOCONF"]                                      # 빼기 2(K2.0 · H10) — 고르지 않음
XS = [c + "_X" for c in G2]                                       # 비용 스트레스 6 — 문 매매만 +0.25%p
SEL = G2 + ["G1_2N"]                                              # 고를 수 있는 칸 7
ALL = SEL + AB + XS                                               # 계좌 셈 15 + 혼자 셈 8(G2 · AB) = z100 23판(상한)
OLD_N = 495
ENV = dict(M.ENV_CONTRACT, Z_SHARE_1D="0.5", Z_SHARE_15M="0.5", Z_SHARE_BASKET="0.3", PYTHONHASHSEED="0")
H1_END, H2_BEG = "202112", "202201"


def door_args(c):
    if c == "G1_2N":
        return ["g1"], "g1_2n"
    if c == "AB_RAW":
        return ["g2", "2.0", "10", "raw"], "g2_raw_K2.0_H10"
    if c == "AB_NOCONF":
        return ["g2", "2.0", "10", "noconf"], "g2_noconf_K2.0_H10"
    x = c.endswith("_X")
    k, h = c.split("_")[1][1:], c.split("_")[2][1:]
    return (["g2", k, h, "rv"] + ([str(XC)] if x else [])), f"g2_rv_K{k}_H{h}" + (f"_x{XC}" if x else "")


def ledger(c):
    return LED / (door_args(c)[1] + ".json")


# ───────── 잠금 ─────────
LOCK = {"/home/user/stock-dash/research/regime_dev.py": "9b8c18720c489707ca6fc0ab71e888cc6a5dab5e54bcd4d6eb20265cd58fe0bc",
        "/home/user/stock-dash/research/mix54_run.py": "b77ba1c1a68d7d6e242f30f4a3ed3c6fc654dd57e3a6dc44ab96852faf7bbd6e",
        P0_CSV: "6bacf87ea66e8cde576e7d8b3cd533e2b18ccd78ed8afdb7e79d5ebb72824531",
        "/tmp/rev-full.pkl": "540114ff96929ceb3e9d6420887e5f5457df4ab65c4457377b9bec13a1fa06a6",
        "/tmp/maxret-0026-cache.pkl": "03dcdd0042b333f5a02e0e65d01518d97ae6efe8e7cb03bb84d4ed3e37b340d7",
        str(SP / "z055_d1_raw.json"): "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99",
        str(TREE / "research/z100.py"): "47b85d2aee5743db81aa82166581156480801f5ab492df1a74c367f0ce28840d"}
TREE_COMMIT = "9743cb802"
SNAPDIR = HERE / "inputs"


def sha(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def verify(quiet=False):
    got = {f: sha(f) for f in LOCK}
    for f in ("mpos8.py", "door.py", "diag8.py"):
        got[f] = sha(HERE / f)
    lk = json.load(open(HERE / "inputs_lock.json"))
    for f in lk:
        got["inputs/" + f] = sha(SNAPDIR / f)
    bad = [f for f, v in LOCK.items() if got[f] != v] + [f for f, v in lk.items() if got["inputs/" + f] != v]
    head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
    if not head.startswith(TREE_COMMIT) or dirty:
        bad.append(f"z100 나무 {head[:9]} 깨끗함={not dirty}")
    if (HERE / "lock.json").exists():                                 # 사전등록 때 적은 코드 지문과 같아야 함
        reg = json.load(open(HERE / "lock.json"))
        bad += [f for f, v in reg.items() if got.get(f) != v]
    rec = {"해시": got, "z100 나무": head, "불일치": bad}
    json.dump(rec, open(HERE / "receipt_lock.json", "w"), ensure_ascii=False, indent=1)
    if bad:
        sys.exit(f"잠금 불일치 → 중단: {bad}")
    if not quiet:
        print("잠금 확인 PASS · receipt_lock.json")
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


# ───────── 장부 · 바탕 ─────────
def pool(jobs, n=3):
    run, done = [], []
    jobs = list(jobs)
    while jobs or run:
        while jobs and len(run) < n:
            name, cmd, env, out = jobs.pop(0)
            fh = open(out, "w")
            run.append((name, subprocess.Popen(cmd, env=env, cwd=str(TREE), stdout=fh, stderr=subprocess.STDOUT), fh))
        for x in list(run):
            if x[1].poll() is not None:
                x[2].close()
                run.remove(x)
                done.append((x[0], x[1].returncode))
                print(x[0], "rc", x[1].returncode, flush=True)
        if run:
            import time
            time.sleep(5)
    return done


def sysenv():
    return {k: os.environ[k] for k in M.SYS_KEEP if k in os.environ}


def build():
    LED.mkdir(parents=True, exist_ok=True)
    jobs = []
    for c in ALL:
        a, nm = door_args(c)
        jobs.append((nm, [sys.executable, str(HERE / "door.py")] + a, dict(sysenv(), NRL_CACHE=M.CACHE, PYTHONHASHSEED="0"), WORK / f"{nm}.log"))
    seen, uniq = set(), []
    for j in jobs:
        if j[0] not in seen:
            seen.add(j[0])
            uniq.append(j)
    r = pool(uniq)
    for c in ALL:                                                     # 혼자 셈 장부: 새 문 매매만(G2 · AB)
        if c.startswith(("G2", "AB")) and not c.endswith("_X"):
            led = json.load(open(ledger(c)))
            assert led[:OLD_N] == json.load(open(SP / "z055_d1_raw.json")), c
            json.dump(led[OLD_N:], open(LED / (door_args(c)[1] + "_solo.json"), "w"))
    return r


def bases():
    BASES.mkdir(parents=True, exist_ok=True)
    jobs = []
    for c in ALL:
        jobs.append((c, [sys.executable, "research/z100.py"], dict(sysenv(), **ENV, Z_DROP="15m", Z_D1_LED=str(ledger(c)), Z_OUT=str(BASES / f"{c}.csv")),
                     BASES / f"{c}.log"))
        if c.startswith(("G2", "AB")) and not c.endswith("_X"):
            jobs.append((c + "_SOLO", [sys.executable, "research/z100.py"],
                         dict(sysenv(), **ENV, Z_DROP="15m,basket,engine,inverse", Z_D1_LED=str(LED / (door_args(c)[1] + "_solo.json")),
                              Z_OUT=str(BASES / f"{c}_SOLO.csv")), BASES / f"{c}_SOLO.log"))
    return pool(jobs)


# ───────── 계좌 · 잣대 ─────────
def account(csv_path):
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(csv_path), None, None
    navs, _ = Dv.account(CFG)
    return navs


def mstats(navs):
    ds = sorted(navs)
    r = {ds[j]: navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mo = {}
    for d, x in r.items():
        mo[d[:6]] = mo.get(d[:6], 1) * (1 + x)
    full = {m: v - 1 for m, v in mo.items() if "201703" <= m <= "202608"}
    assert len(full) == 114, len(full)
    h1 = [m for m in full if m <= H1_END]
    h2 = [m for m in full if m >= H2_BEG]
    pk = mdd = 0
    for d in ds:
        pk = max(pk, navs[d])
        mdd = min(mdd, navs[d] / pk - 1)
    return dict(손실=sum(v < 0 for v in full.values()), 영=sum(v == 0 for v in full.values()), 이익=sum(v > 0 for v in full.values()),
                앞손실=sum(full[m] < 0 for m in h1), 뒤손실=sum(full[m] < 0 for m in h2), 최악달=min(full.values()) * 100,
                최악날=min(r.values()) * 100, 연=(navs[ds[-1]] ** (250 / len(ds)) - 1) * 100, MDD=mdd * 100,
                달=dict(sorted((m, round(v * 100, 4)) for m, v in full.items())))


def base_stats(csv_path):
    import csv
    nav = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(csv_path, encoding="utf-8"))}
    nav = {d: v / nav[min(nav)] for d, v in nav.items() if Dv.LO <= d <= Dv.HI}
    return mstats(nav)


def trade_stats(rows):
    def one(ps):
        if not ps:
            return dict(건=0)
        w = [p for p in ps if p > 0]
        lo = -sum(p for p in ps if p < 0)
        return dict(건=len(ps), 승률=round(len(w) / len(ps) * 100, 2), 평균=round(sum(ps) / len(ps), 4),
                    스트레스평균=round(sum(ps) / len(ps) - XC * 100, 4), PF=round(sum(w) / lo, 3) if lo else None)
    shut = [r for r in rows if r[2] != "99999999"]
    yrs = {}
    for r in shut:
        yrs.setdefault(r[2][:4], []).append(r[3])
    mon = {}
    for r in shut:
        mon.setdefault(r[2][:6], []).append(r[3])
    MON = [f"{y}{m:02d}" for y in range(2017, 2027) for m in range(1, 13) if "201703" <= f"{y}{m:02d}" <= "202608"]
    return dict(전체=one([r[3] for r in shut]), 앞반=one([r[3] for r in shut if r[2][:6] <= H1_END]), 뒤반=one([r[3] for r in shut if r[2][:6] >= H2_BEG]),
                못판=len(rows) - len(shut), 해마다={y: one(v)["평균"] for y, v in sorted(yrs.items())},
                달평균_114분모=round(sum(len(mon.get(m, [])) for m in MON) / 114, 2), 거래있는달=sum(1 for m in MON if mon.get(m)))


def nei(c):
    if not c.startswith("G2"):
        return []
    k, h = float(c.split("_")[1][1:]), int(c.split("_")[2][1:])
    i = KS.index(k)
    out = [f"G2_K{KS[i + d]}_H{h}" for d in (-1, 1) if 0 <= i + d < len(KS)]
    return out + [f"G2_K{k}_H{x}" for x in HS if x != h]


def judge(R, T):
    b = R["P0"]

    def ok1(c):
        x = R[c]
        return x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"] and x["연"] >= 30.702

    def stress(c):                                                    # 비용 스트레스(G2만): 계좌 ① · ③ · ④ 유지 + 문 매매 앞 · 뒤 반 스트레스 평균 > 0
        if not c.startswith("G2"):
            return True
        x = R[c + "_X"]
        t = T[c]
        return (x["최악날"] >= -15 and x["최악달"] >= -15 and x["손실"] < b["손실"] and x["연"] >= 30.702
                and t["앞반"].get("스트레스평균", -1) > 0 and t["뒤반"].get("스트레스평균", -1) > 0)
    ok = [c for c in SEL if ok1(c) and all(ok1(n) for n in nei(c)) and stress(c)]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연"], c))
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연"] >= 30.702, "⑤": all(ok1(n) for n in nei(c)), "스트레스": stress(c)} for c in SEL}
    return ok, rank, why


def boot(R, c, reps=2000, blk=6, seed=20261015):
    """달 묶음(6달) 이어 뽑기 — P0와 같은 묶음으로 짝지어 손실 달 수 · 연수익 차의 90% 구간(보고만)."""
    MON = sorted(R["P0"]["달"])
    a = [R[c]["달"][m] / 100 for m in MON]
    p = [R["P0"]["달"][m] / 100 for m in MON]
    rnd = random.Random(seed)
    dl, dr = [], []
    n = len(MON)
    for _ in range(reps):
        idx = []
        while len(idx) < n:
            s = rnd.randrange(n - blk + 1)
            idx += range(s, s + blk)
        idx = idx[:n]
        dl.append(sum(a[i] < 0 for i in idx) - sum(p[i] < 0 for i in idx))
        ga = math.prod(1 + a[i] for i in idx) ** (12 / n) - 1
        gp = math.prod(1 + p[i] for i in idx) ** (12 / n) - 1
        dr.append((ga - gp) * 100)
    q = lambda v, x: sorted(v)[int(x * (len(v) - 1))]
    return dict(손실달차_90=[q(dl, 0.05), q(dl, 0.95)], 연수익차_90=[round(q(dr, 0.05), 3), round(q(dr, 0.95), 3)], 묶음=blk, 횟수=reps, 씨앗=seed)


def run():
    R, T, B = {"P0": mstats(account(P0_CSV))}, {}, {"P0": base_stats(P0_CSV)}
    for c in ALL:
        R[c] = mstats(account(BASES / f"{c}.csv"))
        B[c] = base_stats(BASES / f"{c}.csv")
        led = json.load(open(ledger(c)))
        T[c] = trade_stats(led[OLD_N:] if c.startswith(("G2", "AB")) else led)
        if (BASES / f"{c}_SOLO.csv").exists():
            T[c]["혼자 계좌"] = {k: v for k, v in base_stats(BASES / f"{c}_SOLO.csv").items() if k != "달"}
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False), flush=True)
    T["P0_1일봉"] = trade_stats(json.load(open(SP / "z055_d1_raw.json")))
    ok, rank, why = judge(R, T)
    bs = {c: boot(R, c) for c in SEL}
    out = {"P0": {k: v for k, v in R["P0"].items()}, "cells": R, "바탕만(덧붙임 없음)": B, "매매": T, "잣대": why, "자격": ok, "순위": rank,
           "고른 것": rank[0] if rank else None, "판정": "SELECTED" if rank else "NO_IMPROVEMENT", "묶음 이어뽑기(보고만)": bs,
           "잠금": json.load(open(HERE / "receipt_lock.json"))["해시"]}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print("자격", ok, "순위", rank)


def cut():
    """자르기: G2 장부 8종(6 + 빼기 2)을 자른 날까지 자료만으로 다시 만들어 그날까지 산 매매 · 판 매매가 한 칸도 안 다른지 + 고른 칸 계좌."""
    recs = []
    jobs = []
    for c in G2 + AB:
        a, nm = door_args(c)
        for ct in ("20211231", "20240628"):
            assert len(a) == 4, c
            jobs.append((f"{nm}_cut{ct}", [sys.executable, str(HERE / "door.py")] + a + ["0", ct],
                         dict(sysenv(), NRL_CACHE=M.CACHE, PYTHONHASHSEED="0"), WORK / f"{nm}_cut{ct}.log"))
    pool(jobs)
    for c in G2 + AB:
        a, nm = door_args(c)
        full = json.load(open(ledger(c)))[OLD_N:]
        for ct in ("20211231", "20240628"):
            part = json.load(open(LED / f"{nm}_cut{ct}.json"))[OLD_N:]
            fb = sorted((r[0], r[1]) for r in full if r[1] <= ct)
            pb = sorted((r[0], r[1]) for r in part if r[1] <= ct)
            fs = sorted(tuple(r) for r in full if r[2] <= ct)
            ps = sorted(tuple(r) for r in part if r[2] <= ct)
            rec = {"칸": c, "자른 날": ct, "산 매매": len(fb), "판 매매": len(fs), "산 다름": len(set(fb) ^ set(pb)), "판 다름": len(set(fs) ^ set(ps)),
                   "판정": "PASS" if fb == pb and fs == ps and fb else "FAIL"}
            print(json.dumps(rec, ensure_ascii=False), flush=True)
            recs.append(rec)
    with open(HERE / "receipt_cut.jsonl", "w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "verify":
        verify()
    elif cmd == "build":
        verify()
        build()
    elif cmd == "bases":
        verify()
        bases()
    elif cmd == "p0check":
        verify()
        Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(P0_CSV), None, None
        s = mstats(account(P0_CSV))
        print({k: v for k, v in s.items() if k != "달"})
    elif cmd == "run":
        verify()
        run()
    elif cmd == "cut":
        verify()
        cut()
