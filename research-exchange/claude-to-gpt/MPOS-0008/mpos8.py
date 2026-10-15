"""MPOS-0008(round 2 · GPT #421 고칠 것 반영) — 1일봉 업그레이드: G1 '2N 칸 나눔' · G2 '시장 대비 과매도 → RNA 회복 확인' 새 문.
흐름: door.py 장부(들어간 순서 · 기존 문 우선 · 칸 ≤ 10) → z100(MIX-0054 결과 커밋 9743cb802 나무 · tree_run.py로 바깥 코드 막음)
      → 덧붙임 P0(L0.4_S0.4 · regime_dev) → 114달 잣대.
순서(앞 단계 영수증이 모두 PASS여야 다음 단계): python3 mpos8.py verify → test → build → bases → cut → run"""
import csv
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
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
KS, HS, XC = (1.5, 2.0, 2.5), (5, 10), 0.0025
G2 = [f"G2_K{k}_H{h}" for k in KS for h in HS]                    # 고를 수 있는 칸 6
CENTER = "G2_K2.0_H10"
AB = ["AB_RAW", "AB_NOCONF"]                                      # 빼기 2(K2.0 · H10) — 기전 판정에만
XS = [c + "_X" for c in G2]                                       # 비용 스트레스 6
SEL = G2 + ["G1_2N"]                                              # 후보 7
ALL = SEL + AB + XS                                               # 결합 계좌 15
SOLO = G2 + AB                                                    # 혼자 계좌 8
CUTS = ("20211231", "20240628")
OLD_N = 495
ENV = dict(M.ENV_CONTRACT, Z_SHARE_1D="0.5", Z_SHARE_15M="0.5", Z_SHARE_BASKET="0.3", PYTHONHASHSEED="0")
H1_END, H2_BEG = "202112", "202201"
YEAR_MAX = 0.5                                                    # 한 해가 새 문 순손익 합의 절반 넘으면 '특정 해 몰림'


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


def ledger(c, cut=None):
    return LED / (door_args(c)[1] + (f"_cut{cut}" if cut else "") + ".json")


# ───────── 잠금 · 영수증 ─────────
LOCK = {"/home/user/stock-dash/research/regime_dev.py": "9b8c18720c489707ca6fc0ab71e888cc6a5dab5e54bcd4d6eb20265cd58fe0bc",
        "/home/user/stock-dash/research/mix54_run.py": "b77ba1c1a68d7d6e242f30f4a3ed3c6fc654dd57e3a6dc44ab96852faf7bbd6e",
        P0_CSV: "6bacf87ea66e8cde576e7d8b3cd533e2b18ccd78ed8afdb7e79d5ebb72824531",
        "/tmp/rev-full.pkl": "540114ff96929ceb3e9d6420887e5f5457df4ab65c4457377b9bec13a1fa06a6",
        "/tmp/maxret-0026-cache.pkl": "03dcdd0042b333f5a02e0e65d01518d97ae6efe8e7cb03bb84d4ed3e37b340d7",
        str(SP / "z055_d1_raw.json"): "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99",
        str(TREE / "study/features.json"): None}                   # 4GB · 크기 · 바뀐 때만(nrl은 캐시를 씀)
TREE_COMMIT = "9743cb80273"
SNAPDIR = HERE / "inputs"
CODE = ("mpos8.py", "door.py", "diag8.py", "tree_run.py", "test_door.py", "test_judge.py", "ref_mods.json")


def sha(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def verify(quiet=False):
    got = {}
    for f, v in LOCK.items():
        if v is None:
            st = os.stat(f)
            got[f] = f"size={st.st_size} mtime={int(st.st_mtime)}"
        else:
            got[f] = sha(f)
    for f in CODE:
        got[f] = sha(HERE / f)
    lk = json.load(open(HERE / "inputs_lock.json"))
    for f in lk:
        got["inputs/" + f] = sha(SNAPDIR / f)
    bad = [f for f, v in LOCK.items() if v and got[f] != v] + [f for f, v in lk.items() if got["inputs/" + f] != v]
    if got[str(TREE / "study/features.json")] != "size=4256874748 mtime=1790304366":
        bad.append("features.json")
    head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
    if not head.startswith(TREE_COMMIT) or dirty:
        bad.append(f"z100 나무 {head[:11]} 깨끗함={not dirty}")
    if (HERE / "lock.json").exists():
        reg = json.load(open(HERE / "lock.json"))
        bad += [f for f, v in reg.items() if got.get(f) != v]
    json.dump({"해시": got, "z100 나무": head, "불일치": bad}, open(HERE / "receipt_lock.json", "w"), ensure_ascii=False, indent=1)
    if bad:
        sys.exit(f"잠금 불일치 → 중단: {bad}")
    if not quiet:
        print("잠금 확인 PASS · receipt_lock.json")
    return got


def receipt(name):
    p = HERE / f"receipt_{name}.json"
    return json.load(open(p)) if p.exists() else None


def need(name, lock):
    """앞 단계 영수증: 있음 · 이번 잠금과 같은 코드 지문 · 모든 줄 PASS · 결과 파일 지문 그대로."""
    r = receipt(name)
    if not r:
        sys.exit(f"{name} 영수증 없음 → 중단")
    if r["코드"] != {f: lock[f] for f in CODE}:
        sys.exit(f"{name} 영수증이 다른 코드로 만든 것 → 중단")
    for k, v in r["줄"].items():
        if v["판정"] != "PASS":
            sys.exit(f"{name} {k} FAIL → 중단")
        for f, h in v.get("파일", {}).items():
            if not os.path.exists(f) or sha(f) != h:
                sys.exit(f"{name} {k} 파일 바뀜/없음 {f} → 중단")
    return r


def write_receipt(name, lock, rows):
    json.dump({"코드": {f: lock[f] for f in CODE}, "때": time.strftime("%Y-%m-%d %H:%M:%S"), "줄": rows},
              open(HERE / f"receipt_{name}.json", "w"), ensure_ascii=False, indent=1)
    bad = [k for k, v in rows.items() if v["판정"] != "PASS"]
    print(name, "PASS" if not bad else f"FAIL {bad}")
    if bad:
        sys.exit(3)


_load0 = Dv.load


def load_snap():
    root0 = Dv.ROOT
    Dv.ROOT = SNAPDIR
    try:
        return _load0()
    finally:
        Dv.ROOT = root0


Dv.load = load_snap


# ───────── 실행 ─────────
def sysenv():
    return {k: os.environ[k] for k in M.SYS_KEEP if k in os.environ}


def tree_cmd(mods, script, *args):
    return [sys.executable, str(HERE / "tree_run.py"), str(mods), script, *args]


def pool(jobs, n=3):
    """jobs: (이름, 명령, 환경, 기록 파일, 모듈 영수증, 결과 파일 목록) → {이름: rc}"""
    for _, _, _, _, mods, outs in jobs:
        for f in [mods] + outs:
            if os.path.exists(f):
                os.remove(f)                                      # 지난 실행 잔재 지움
    run, rc = [], {}
    jobs = list(jobs)
    while jobs or run:
        while jobs and len(run) < n:
            j = jobs.pop(0)
            fh = open(j[3], "w")
            run.append((j, subprocess.Popen(j[1], env=j[2], cwd=str(TREE), stdout=fh, stderr=subprocess.STDOUT), fh))
        for x in list(run):
            if x[1].poll() is not None:
                x[2].close()
                run.remove(x)
                rc[x[0][0]] = x[1].returncode
                print(x[0][0], "rc", x[1].returncode, flush=True)
        if run:
            time.sleep(5)
    return rc


def mods_ok(path, ref):
    """모듈 영수증: 바깥 코드 없음 · 같은 이름 모듈은 기준(재현 때)과 같은 지문."""
    if not os.path.exists(path):
        return False, "모듈 영수증 없음"
    r = json.load(open(path))
    if r["바깥"]:
        return False, f"바깥 {r['바깥'][:2]}"
    diff = [k for k, v in r["모듈"].items() if k in ref and ref[k] != v]
    return (not diff), (f"지문 다름 {diff}" if diff else "")


def door_env():
    return dict(sysenv(), NRL_CACHE=M.CACHE, PYTHONHASHSEED="0")


def z100_env(led, out, drop="15m"):
    e = dict(sysenv(), **ENV)                                     # ENV(M.ENV_CONTRACT)에 Z_D1_LED가 이미 있어 덮어씀(round 4: 실행 오류 고침)
    e.update(Z_DROP=drop, Z_D1_LED=str(led), Z_OUT=str(out))
    return e


def occupancy(led):
    days = sorted({r[1] for r in led} | {r[2] for r in led if r[2] != "99999999"})
    ev = {}
    for c, b, e, p, s in led:
        ev[b] = ev.get(b, 0) + s
        if e != "99999999":
            ev[e] = ev.get(e, 0) - s
    cur, worst = 0.0, 0.0
    for d in days:
        cur += ev.get(d, 0)
        worst = max(worst, cur)
    return worst


def check_ledger(c, path, meta_path=None):
    led = json.load(open(path))
    msg = []
    if c != "G1_2N" and led[:OLD_N] != json.load(open(SP / "z055_d1_raw.json")):
        msg.append("기존 495줄 바뀜")
    w = occupancy(led)
    if w > 10 + 1e-9:
        msg.append(f"칸 최대 {w}")
    if meta_path:
        meta = json.load(open(meta_path))
        new = led[OLD_N:]
        keys = [(m["산 날"], m["그날 순위"]) for m in meta]
        if keys != sorted(keys) or len(set(keys)) != len(keys) or [r[1] for r in new] != [m["산 날"] for m in meta]:
            msg.append("새 문 순서 ≠ 들어간 순서")
    return (not msg), "; ".join(msg), w


def build(lock):
    LED.mkdir(parents=True, exist_ok=True)
    ref = json.load(open(HERE / "ref_mods.json"))["모듈"]
    jobs, seen = [], set()
    for c in ALL:
        a, nm = door_args(c)
        if nm in seen:
            continue
        seen.add(nm)
        outs = [str(LED / f"{nm}.json")] + ([str(LED / f"{nm}.meta.json")] if c != "G1_2N" else [])
        jobs.append((c, tree_cmd(WORK / f"{nm}.mods.json", str(HERE / "door.py"), *a), door_env(), WORK / f"{nm}.log", WORK / f"{nm}.mods.json", outs))
    rc = pool(jobs)
    rows = {}
    for c, _, _, _, mods, outs in jobs:
        ok_m, why_m = mods_ok(mods, ref)
        ok_l, why_l, w = (check_ledger(c, outs[0], outs[1] if len(outs) > 1 else None) if rc[c] == 0 and os.path.exists(outs[0]) else (False, "결과 없음", None))
        rows[c] = {"rc": rc[c], "칸 최대": w, "판정": "PASS" if rc[c] == 0 and ok_m and ok_l else "FAIL", "까닭": "; ".join(x for x in (why_m, why_l) if x),
                   "파일": {f: sha(f) for f in outs if os.path.exists(f)}}
    for c in SOLO:                                                    # 혼자 장부: 새 문 줄만
        json.dump(json.load(open(ledger(c)))[OLD_N:], open(LED / (door_args(c)[1] + "_solo.json"), "w"))
        rows[c + "_solo"] = {"판정": "PASS", "파일": {str(LED / (door_args(c)[1] + "_solo.json")): sha(LED / (door_args(c)[1] + "_solo.json"))}}
    write_receipt("build", lock, rows)


def bases(lock):
    need("build", lock)
    BASES.mkdir(parents=True, exist_ok=True)
    ref = json.load(open(HERE / "ref_mods.json"))["모듈"]
    jobs = [(c, tree_cmd(BASES / f"{c}.mods.json", "research/z100.py"), z100_env(ledger(c), BASES / f"{c}.csv"), BASES / f"{c}.log",
             BASES / f"{c}.mods.json", [str(BASES / f"{c}.csv")]) for c in ALL]
    jobs += [(c + "_SOLO", tree_cmd(BASES / f"{c}_SOLO.mods.json", "research/z100.py"),
              z100_env(LED / (door_args(c)[1] + "_solo.json"), BASES / f"{c}_SOLO.csv", "15m,basket,engine,inverse"),
              BASES / f"{c}_SOLO.log", BASES / f"{c}_SOLO.mods.json", [str(BASES / f"{c}_SOLO.csv")]) for c in SOLO]
    rc = pool(jobs)
    rows = {}
    for c, _, _, _, mods, outs in jobs:
        ok_m, why = mods_ok(mods, ref)
        ok_f = rc[c] == 0 and os.path.exists(outs[0])
        rows[c] = {"rc": rc[c], "판정": "PASS" if ok_m and ok_f else "FAIL", "까닭": why, "파일": {outs[0]: sha(outs[0])} if ok_f else {}}
    write_receipt("bases", lock, rows)


def nav_rows(path):
    return {r["날"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def cut(lock):
    """자르기(감사 실행 · 후보 격자 아님): G2 6 + 빼기 2 장부를 자른 날까지 자료만으로 처음부터 → ① 새 문 줄의 순서 있는 진입 목록(종목 · 산 날 · 칸)
    ② 그날까지 판 줄 전체 ③ 그날 보유 중 목록 ④ z100 계좌 날마다 줄 전체(NAV · 현금 · 봇별) prefix 가 한 칸도 안 다름. 하나라도 FAIL → 중단."""
    need("bases", lock)
    ref = json.load(open(HERE / "ref_mods.json"))["모듈"]
    jobs = []
    for c in G2 + AB:
        a, nm = door_args(c)
        for ct in CUTS:
            outs = [str(ledger(c, ct)), str(LED / f"{nm}_cut{ct}.meta.json")]
            jobs.append((f"{c}@{ct}", tree_cmd(WORK / f"{nm}_cut{ct}.mods.json", str(HERE / "door.py"), *a, "0", ct), door_env(),
                         WORK / f"{nm}_cut{ct}.log", WORK / f"{nm}_cut{ct}.mods.json", outs))
    rc = pool(jobs)
    jobs2 = [(f"{c}@{ct}#acct", tree_cmd(BASES / f"{c}_cut{ct}.mods.json", "research/z100.py"), z100_env(ledger(c, ct), BASES / f"{c}_cut{ct}.csv"),
              BASES / f"{c}_cut{ct}.log", BASES / f"{c}_cut{ct}.mods.json", [str(BASES / f"{c}_cut{ct}.csv")]) for c in G2 + AB for ct in CUTS]
    rc2 = pool(jobs2)
    rows = {}
    for c in G2 + AB:
        full = json.load(open(ledger(c)))[OLD_N:]
        fullnav = nav_rows(BASES / f"{c}.csv")
        for ct in CUTS:
            k = f"{c}@{ct}"
            if rc[k] or rc2[k + "#acct"]:
                rows[k] = {"판정": "FAIL", "까닭": f"rc {rc[k]} / {rc2[k + '#acct']}"}
                continue
            part = json.load(open(ledger(c, ct)))[OLD_N:]
            e1 = [(r[0], r[1], r[4]) for r in full if r[1] <= ct]
            e2 = [(r[0], r[1], r[4]) for r in part if r[1] <= ct]
            s1 = [r for r in full if r[2] <= ct]
            s2 = [r for r in part if r[2] <= ct]
            o1 = [(r[0], r[1]) for r in full if r[1] <= ct < r[2]]
            o2 = [(r[0], r[1]) for r in part if r[1] <= ct and r[2] == "99999999"]
            pn = nav_rows(BASES / f"{c}_cut{ct}.csv")
            days = [d for d in sorted(fullnav) if d <= ct]
            nd = [d for d in days if pn.get(d) != fullnav[d]]
            ok_m = mods_ok(WORK / f"{door_args(c)[1]}_cut{ct}.mods.json", ref)[0] and mods_ok(BASES / f"{c}_cut{ct}.mods.json", ref)[0]
            ok = e1 == e2 and s1 == s2 and o1 == o2 and not nd and bool(e1) and ok_m
            rows[k] = {"진입": len(e1), "판 줄": len(s1), "보유 중": len(o1), "계좌 날": len(days), "진입 순서 다름": e1 != e2, "판 줄 다름": s1 != s2,
                       "보유 다름": o1 != o2, "계좌 다른 날": nd[:3], "모듈": ok_m, "판정": "PASS" if ok else "FAIL"}
            print(k, json.dumps(rows[k], ensure_ascii=False), flush=True)
    write_receipt("cut", lock, rows)


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
                최악날=min(r.values()) * 100, 연_거래일=(navs[ds[-1]] ** (250 / len(ds)) - 1) * 100, MDD=mdd * 100,
                달=dict(sorted(full.items())))                    # 원정밀도(표시 때만 반올림)


def base_stats(csv_path):
    nav = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(csv_path, encoding="utf-8"))}
    nav = {d: v / nav[min(nav)] for d, v in nav.items() if Dv.LO <= d <= Dv.HI}
    return mstats(nav)


def trade_stats(rows):
    def one(ps):
        if not ps:
            return dict(건=0, 평균=None, 스트레스평균=None)
        w = [p for p in ps if p > 0]
        lo = -sum(p for p in ps if p < 0)
        return dict(건=len(ps), 승률=len(w) / len(ps) * 100, 평균=sum(ps) / len(ps), 스트레스평균=sum(ps) / len(ps) - XC * 100,
                    PF=(sum(w) / lo) if lo else None, 합=sum(ps))
    shut = [r for r in rows if r[2] != "99999999"]
    yrs = {}
    for r in shut:
        yrs[r[2][:4]] = yrs.get(r[2][:4], 0.0) + r[3]
    tot = sum(r[3] for r in shut)
    MON = [f"{y}{m:02d}" for y in range(2017, 2027) for m in range(1, 13) if "201703" <= f"{y}{m:02d}" <= "202608"]
    mon = {}
    for r in shut:
        mon[r[2][:6]] = mon.get(r[2][:6], 0) + 1
    return dict(전체=one([r[3] for r in shut]), 앞반=one([r[3] for r in shut if r[2][:6] <= H1_END]), 뒤반=one([r[3] for r in shut if r[2][:6] >= H2_BEG]),
                못판=len(rows) - len(shut), 해마다_합=dict(sorted(yrs.items())),
                한해몰림=(max(yrs.values()) / tot) if tot > 0 and yrs else None,
                달평균_114분모=sum(mon.get(m, 0) for m in MON) / 114, 거래있는달=sum(1 for m in MON if mon.get(m)))


def nei(c):
    if not c.startswith("G2"):
        return []
    k, h = float(c.split("_")[1][1:]), int(c.split("_")[2][1:])
    i = KS.index(k)
    out = [f"G2_K{KS[i + d]}_H{h}" for d in (-1, 1) if 0 <= i + d < len(KS)]
    return out + [f"G2_K{k}_H{x}" for x in HS if x != h]


def gt(a, b):
    """GPT #421 round 2: 숫자 0과 결측(None)을 구분. 둘 중 하나라도 결측이면 거짓(= 기전 미지지 · 관문 탈락), 아니면 원정밀도 a > b."""
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        return False
    return a > b


def mechanism(R, T):
    """G2 기전(사전등록 §3 · 결과 보기 전 고정): 가운데 칸(K2.0 · H10)이 빼기 둘 각각보다
    결합 계좌 손실 달 ≤ 이고 새 문 매매 스트레스 평균(전체)이 > 이어야 '지지'. 아니면 G2 칸은 자격 없음."""
    c = CENTER
    out = {}
    for a in AB:
        out[a] = dict(손실달_이하=R[c]["손실"] <= R[a]["손실"],
                      스트레스평균_큼=gt(T[c]["전체"]["스트레스평균"], T[a]["전체"]["스트레스평균"]))
    out["지지"] = all(out[a]["손실달_이하"] and out[a]["스트레스평균_큼"] for a in AB)
    return out


def judge(R, T, mech):
    b = R["P0"]

    def acct(c):
        x = R[c]
        return x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"] and x["연_거래일"] >= 30.702

    def g2gate(c):
        if not c.startswith("G2"):
            return True
        x, t = R[c + "_X"], T[c]
        stress = (x["최악날"] >= -15 and x["최악달"] >= -15 and x["손실"] < b["손실"] and x["연_거래일"] >= 30.702
                  and gt(t["앞반"]["스트레스평균"], 0.0) and gt(t["뒤반"]["스트레스평균"], 0.0))
        year = t["한해몰림"] is not None and t["한해몰림"] <= YEAR_MAX
        return stress and year and mech["지지"]
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연_거래일"] >= 30.702, "⑤": all(acct(n) for n in nei(c)), "G2 관문": g2gate(c)} for c in SEL}
    ok = [c for c in SEL if all(why[c].values())]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    return ok, rank, why


def boot(R, c, reps=2000, blk=6, seed=20261015):
    """6달 묶음 이어뽑기 — P0와 같은 묶음으로 짝지어 손실 달 수 차 · '114달 기하 연환산' 차(본표 '거래일 연환산'과 다른 셈)의 90% 구간(보고만)."""
    MON = sorted(R["P0"]["달"])
    a = [R[c]["달"][m] for m in MON]
    p = [R["P0"]["달"][m] for m in MON]
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
        dr.append((math.prod(1 + a[i] for i in idx) ** (12 / n) - math.prod(1 + p[i] for i in idx) ** (12 / n)) * 100)
    q = lambda v, x: sorted(v)[int(x * (len(v) - 1))]
    return dict(손실달차_90=[q(dl, 0.05), q(dl, 0.95)], 달기하연환산차_90=[q(dr, 0.05), q(dr, 0.95)], 묶음=blk, 횟수=reps, 씨앗=seed)


def run(lock):
    need("build", lock)
    need("bases", lock)
    need("cut", lock)
    R, T, B = {"P0": mstats(account(P0_CSV))}, {}, {"P0": base_stats(P0_CSV)}
    for c in ALL:
        R[c] = mstats(account(BASES / f"{c}.csv"))
        B[c] = base_stats(BASES / f"{c}.csv")
        led = json.load(open(ledger(c)))
        T[c] = trade_stats(led[OLD_N:] if c != "G1_2N" else led)
        if c in SOLO:
            T[c]["혼자 계좌"] = {k: v for k, v in base_stats(BASES / f"{c}_SOLO.csv").items() if k != "달"}
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False), flush=True)
    T["P0_1일봉"] = trade_stats(json.load(open(SP / "z055_d1_raw.json")))
    mech = mechanism(R, T)
    ok, rank, why = judge(R, T, mech)
    out = {"P0": R["P0"], "cells": R, "바탕만(덧붙임 없음)": B, "매매": T, "기전(G2)": mech, "잣대": why, "자격": ok, "순위": rank,
           "고른 것": rank[0] if rank else None, "판정": "SELECTED" if rank else "NO_IMPROVEMENT",
           "묶음 이어뽑기(보고만)": {c: boot(R, c) for c in SEL}, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    print("기전", mech, "자격", ok, "순위", rank)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    lk = verify(quiet=cmd != "verify")
    if cmd == "test":
        rows = {}
        for t in ("test_door.py", "test_judge.py"):
            r = subprocess.run([sys.executable, str(HERE / t)], capture_output=True, text=True)
            print(r.stdout)
            rows[t] = {"판정": "PASS" if r.returncode == 0 else "FAIL", "출력": r.stdout + r.stderr[-500:]}
        write_receipt("test", lk, rows)
    elif cmd == "build":
        need("test", lk)
        build(lk)
    elif cmd == "bases":
        bases(lk)
    elif cmd == "cut":
        cut(lk)
    elif cmd == "p0check":
        s = mstats(account(P0_CSV))
        print({k: v for k, v in s.items() if k != "달"})
    elif cmd == "run":
        run(lk)
