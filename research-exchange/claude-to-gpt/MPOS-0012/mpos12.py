"""MPOS-0012 — 1일봉 다듬기(사용자 2026-10-16 "1일봉이 손실의 원인이니까 더 다듬어봐 · 키움증권 봇 개발에서 아이디어를 갖고와바").
키움(KMF) 교훈 ③ '믿을 부품만' · ② '날 종류별 부품': 1일봉 매매 중 **정배열 문**을 판단 전날 국면이 믿을 수 없는 날에만 건너뜀(사지 않음 · 빈 칸은 채우지 않음).
부품 해부(diag12.json · 추정 비용 뒤): 규칙 문 93건 t 4.62 · 정배열 × 상승 262건 t 2.10 · 정배열 × 횡보 117건 t 1.60 · 정배열 × 하락 23건 t 1.72.
칸: F_DOWN(하락 날 정배열 건너뜀) · F_SIDE(횡보 날) · F_SIDEDOWN(횡보 · 하락 날) · F_ALL(정배열 전부 건너뜀 = 규칙 문만) · AB_RAND(빼기: F_SIDEDOWN과 같은 건수의 정배열을 고정 씨앗으로 무작위 건너뜀).
흐름: 걸러낸 장부 → z100(MIX-0054 나무 · tree_run) → 덧붙임 P0 → 114달 잣대. python3 mpos12.py build | run | cut"""
import csv
import hashlib
import json
import math
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
WORK = SP / "mpos12"
TREE = SP / "m54tree"
TREE_RUN = SP / "r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py"
sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0012")
import mix54_run as M  # noqa: E402
import regime_dev as Dv  # noqa: E402
import rxkit as X  # noqa: E402

P0_CSV = "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
SNAPDIR = SP / "r8/research-exchange/claude-to-gpt/MPOS-0011/inputs"
SKIP = {"F_DOWN": {"하락"}, "F_SIDE": {"횡보"}, "F_SIDEDOWN": {"횡보", "하락"}, "F_ALL": {"상승", "횡보", "하락"}}
CELLS = ["F_DOWN", "F_SIDE", "F_SIDEDOWN", "F_ALL"]
CENTER, ABL = "F_SIDEDOWN", "AB_RAND"
NEI = {"F_DOWN": ["F_SIDEDOWN"], "F_SIDE": ["F_SIDEDOWN"], "F_SIDEDOWN": ["F_SIDE", "F_DOWN"], "F_ALL": ["F_SIDEDOWN"]}   # F_ALL은 한쪽만(가운데의 이웃 아님)
EXPECT = {"F_DOWN": 23, "F_SIDE": 117, "F_SIDEDOWN": 140, "F_ALL": 402, "AB_RAND": 140}
BUILD = ["REPRO"] + CELLS + [ABL]
RAW = SP / "z055_d1_raw.json"
LOCK = {P0_CSV: "6bacf87ea66e8cde576e7d8b3cd533e2b18ccd78ed8afdb7e79d5ebb72824531",
        "/home/user/stock-dash/research/regime_dev.py": "9b8c18720c489707ca6fc0ab71e888cc6a5dab5e54bcd4d6eb20265cd58fe0bc",
        "/home/user/stock-dash/research/mix54_run.py": "b77ba1c1a68d7d6e242f30f4a3ed3c6fc654dd57e3a6dc44ab96852faf7bbd6e",
        "/tmp/rev-full.pkl": "540114ff96929ceb3e9d6420887e5f5457df4ab65c4457377b9bec13a1fa06a6",
        str(RAW): "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"}
CUTS = ("20211231", "20240628", "20200303")


def verify():
    """잠금(대리 검토 3): 바탕 csv · regime_dev · mix54_run · rev-full · 원 장부 · 스냅숏 입력 · 진단 결과 · 이 코드."""
    got = {f: X.sha(f) for f in LOCK}
    lk = json.load(open(SNAPDIR.parent / "inputs_lock.json"))
    for f, v in lk.items():
        got["inputs/" + f] = X.sha(str(SNAPDIR / f))
    bad = [f for f, v in LOCK.items() if got[f] != v] + [f for f, v in lk.items() if got["inputs/" + f] != v]
    for f in ("diag12.json", "diag12.py", "mpos12.py"):
        got[f] = X.sha(str(HERE / f))
    if (HERE / "lock.json").exists():
        bad += [f for f, v in json.load(open(HERE / "lock.json")).items() if got.get(f) != v]
    if bad:
        sys.exit(f"잠금 불일치 → 중단: {bad}")
    return got


def order_n(led):
    """중립 순서(대리 검토 5): 원 장부는 (판 날, 산 날) 순이라 같은 날 사기 순서가 판 날(미래)을 따름 → (산 날 · 종목 · 판 날)로 다시 줄 세움."""
    return sorted(led, key=lambda r: (r[1], r[0], r[2]))
ENV = {"NRL_CACHE": "/tmp/maxret-0026-cache.pkl", "Z_ACC_VOL": "0.010911", "Z_FROM": "20170201", "Z_TO": "20260930", "Z_MARGIN": "1.30", "Z_ACC": "1e8",
       "Z_D1_VOL": "0", "Z_LOOK": "20", "Z_ACC_STRICT": "1", "Z_STOCK_CAP": "0", "Z_PARK": "0", "Z_BASKET_BEAR": "0", "Z_STOCK_VOL": "0",
       "Z_TRIM_BAND": "0", "Z_SHARE_1D": "0.5", "Z_SHARE_15M": "0.5", "Z_SHARE_BASKET": "0.3", "PYTHONHASHSEED": "0", "Z_DROP": "15m"}

_load0 = Dv.load


def load_snap():
    root0 = Dv.ROOT
    Dv.ROOT = SNAPDIR
    try:
        return _load0()
    finally:
        Dv.ROOT = root0


Dv.load = load_snap


def states(cut=None):
    """판단 전날 국면(regime_dev · 그날까지 자료). cut이면 Dv.CUT로 자른 자료로 다시 셈."""
    Dv.CUT, Dv.DATA, Dv.FEAT = (cut or ""), None, None
    Dv.BASE_CSV = Path(P0_CSV)
    base, etf, br, flow = Dv.data()
    feat = Dv.features(etf, br, flow, Dv.short_breadth() if br else {})
    st = Dv.states(feat, CFG)
    Dv.CUT, Dv.DATA, Dv.FEAT = "", None, None
    return st


def decide(cell, trades, st, seed=20261016):
    """trades: diag12 매매(문 · 산 날) · 돌려줌: 건너뛸 줄 번호 집합 — 산 날 전날 국면만 씀."""
    def reg(b):
        prev = [d for d in st if d < b]
        return st[max(prev)] if prev else "?"
    if cell == ABL:
        n = sum(1 for x in trades if x["door"] == "정배열" and reg(x["b"]) in SKIP[CENTER])
        pool = [i for i, x in enumerate(trades) if x["door"] == "정배열"]
        return set(random.Random(seed).sample(pool, n))
    return {i for i, x in enumerate(trades) if x["door"] == "정배열" and reg(x["b"]) in SKIP[cell]}


def build():
    lock = verify()
    raw = json.load(open(RAW))
    trades = json.load(open(HERE / "diag12.json"))["매매"]
    assert all((r[0], r[1], r[2]) == (x["c"], x["b"], x["e"]) for r, x in zip(raw, trades)) and len(raw) == len(trades) == 495
    st = states()
    rec = {}
    jobs = {}
    for c0 in BUILD:
        sk = set() if c0 == "REPRO" else decide(c0, trades, st)
        assert c0 == "REPRO" or len(sk) == EXPECT[c0], (c0, len(sk))
        led0 = [r for i, r in enumerate(raw) if i not in sk]
        for c, led in ((c0, led0), (c0 + "_N", order_n(led0))):
            p = WORK / f"led_{c}.json"
            json.dump(led, open(p, "w"))
            rec[c] = {"건너뜀": len(sk), "남은 매매": len(led), "장부 지문": X.sha(str(p))}
            env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
            env.update(ENV)
            env.update(Z_D1_LED=str(p), Z_OUT=str(WORK / f"base_{c}.csv"))
            jobs[c] = dict(cmd=[sys.executable, str(TREE_RUN), str(WORK / f"base_{c}.mods.json"), "research/z100.py"], env=env, cwd=str(TREE),
                           out=str(WORK / f"base_{c}.log"), clean=[str(WORK / f"base_{c}.csv")])
    bad = X.dry({"z100": lambda: jobs})
    if bad:
        sys.exit(f"마른 실행 FAIL {bad}")
    rc = X.run_dag(jobs, workers=X.CPU, log=lambda m: print(m, flush=True))
    for c in rc:
        rec[c]["rc"] = rc[c]
        f = WORK / f"base_{c}.csv"
        rec[c]["바탕 지문"] = X.sha(str(f)) if f.exists() else None
        mods = json.load(open(WORK / f"base_{c}.mods.json")) if (WORK / f"base_{c}.mods.json").exists() else {"바깥": ["없음"]}
        rec[c]["판정"] = "PASS" if rc[c] == 0 and f.exists() and not mods["바깥"] else "FAIL"
    for c in rc:
        log = open(WORK / f"base_{c}.log").read() if (WORK / f"base_{c}.log").exists() else ""
        rec[c]["1일봉 못 산 번"] = int(log.split("못 쓴 돈")[1].split("1d ")[1].split("번")[0]) if "못 쓴 돈" in log else None
    rec["REPRO"]["잠금"] = lock
    rec["REPRO"]["P0 바탕과 같음"] = rec["REPRO"]["바탕 지문"] == X.sha(P0_CSV)
    if not rec["REPRO"]["P0 바탕과 같음"]:
        rec["REPRO"]["판정"] = "FAIL"
    json.dump(rec, open(HERE / "receipt_build.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rec, ensure_ascii=False))
    if any(v["판정"] != "PASS" for v in rec.values()):
        sys.exit(3)


def cut():
    """자르기: 2021-12-31 · 2024-06-28까지 자료로 국면을 다시 셈 → 그날까지 산 매매의 건너뜀 결정이 한 건도 안 다름."""
    lock = verify()
    trades = json.load(open(HERE / "diag12.json"))["매매"]
    full = states()
    out = []
    for ct in CUTS:
        part = states(ct)
        assert max(part) <= ct < max(full), (ct, max(part))
        for c in CELLS:
            a = {i for i in decide(c, trades, full) if trades[i]["b"] <= ct}
            b = {i for i in decide(c, trades, part) if trades[i]["b"] <= ct}
            out.append({"칸": c, "자른 날": ct, "건너뜀": len(a), "다름": len(a ^ b), "판정": "PASS" if a == b else "FAIL"})
            print(json.dumps(out[-1], ensure_ascii=False))
    json.dump({"잠금": lock, "행": out}, open(HERE / "receipt_cut.json", "w"), ensure_ascii=False, indent=1)
    if any(x["판정"] != "PASS" for x in out):
        sys.exit(3)


def mstats(navs):
    ds = sorted(navs)
    r = {ds[j]: navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mo = {}
    for d, x in r.items():
        mo[d[:6]] = mo.get(d[:6], 1) * (1 + x)
    full = {m: v - 1 for m, v in mo.items() if "201703" <= m <= "202608"}
    assert len(full) == 114
    pk = mdd = 0
    for d in ds:
        pk = max(pk, navs[d])
        mdd = min(mdd, navs[d] / pk - 1)
    return dict(손실=sum(v < 0 for v in full.values()), 영=sum(v == 0 for v in full.values()), 이익=sum(v > 0 for v in full.values()),
                앞손실=sum(full[m] < 0 for m in full if m <= "202112"), 뒤손실=sum(full[m] < 0 for m in full if m >= "202201"),
                최악달=min(full.values()) * 100, 최악날=min(r.values()) * 100, 연_거래일=((navs[ds[-1]] / navs[ds[0]]) ** (250 / len(ds)) - 1) * 100,
                MDD=mdd * 100, 달=dict(sorted(full.items())))


def account(p):
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(p), None, None
    return Dv.account(CFG)[0]


def gt(a, b):
    return a is not None and b is not None and a > b


def cutacct():
    """자르기 2(대리 검토 4): build 뒤 칸마다 Dv.CUT로 자른 자료(바탕 csv · ETF · 국면 모두 자름)로 덧붙임 계좌를 다시 셈 → 자른 날까지 날마다 NAV가 원정밀도로 같음. 성과는 출력 안 함."""
    lock = verify()
    rb = json.load(open(HERE / "receipt_build.json"))
    out = []
    for c in rb:
        f = WORK / f"base_{c}.csv"
        assert X.sha(str(f)) == rb[c]["바탕 지문"], c
        full = account(f)
        for ct in CUTS:
            Dv.CUT = ct
            part = account(f)
            Dv.CUT, Dv.DATA, Dv.FEAT = "", None, None
            dd = [d for d in full if d <= ct]
            ok = bool(dd) and max(part) <= ct and all(part.get(d) == full[d] for d in dd)
            out.append({"칸": c, "자른 날": ct, "날": len(dd), "판정": "PASS" if ok else "FAIL"})
            print(json.dumps(out[-1], ensure_ascii=False), flush=True)
    json.dump({"잠금": lock, "행": out}, open(HERE / "receipt_cutacct.json", "w"), ensure_ascii=False, indent=1)
    if any(x["판정"] != "PASS" for x in out):
        sys.exit(3)


def shares(f):
    """보고만(대리 검토 1): 바탕 계좌의 평균 몫(%) — 건너뛴 돈이 어디로 갔는지."""
    rows = list(csv.DictReader(open(f)))
    return {k: round(sum(float(r[k]) / float(r["NAV"]) for r in rows) / len(rows) * 100, 2) for k in ("일봉", "바구니", "엔진", "인버스", "현금")}


def run():
    lock = verify()
    rb = json.load(open(HERE / "receipt_build.json"))
    names = [c + n for c in BUILD for n in ("", "_N")]
    assert rb["REPRO"]["P0 바탕과 같음"] and set(rb) == set(names), sorted(rb)
    for c, v in rb.items():
        if (v["판정"] != "PASS" or X.sha(str(WORK / f"base_{c}.csv")) != v["바탕 지문"] or X.sha(str(WORK / f"led_{c}.json")) != v["장부 지문"]
                or (c.split("_N")[0] in EXPECT and v["건너뜀"] != EXPECT[c.split("_N")[0]])):
            sys.exit(f"{c} 장부 영수증 문제 → 중단")
    for nm, n in (("receipt_cut.json", 12), ("receipt_cutacct.json", 3 * len(names))):
        r = json.load(open(HERE / nm))
        if r["잠금"]["mpos12.py"] != lock["mpos12.py"] or len(r["행"]) != n or any(x["판정"] != "PASS" for x in r["행"]):
            sys.exit(f"{nm}: 코드 지문 다름 · 건수 다름 · FAIL → 중단")
    if rb["REPRO"]["잠금"]["mpos12.py"] != lock["mpos12.py"]:
        sys.exit("장부 영수증 코드 지문 다름 → 중단")
    R = {"P0": mstats(account(P0_CSV))}
    b = R["P0"]
    assert b["손실"] == 40 and b["앞손실"] == 20 and b["뒤손실"] == 20 and abs(b["최악달"] + 14.0434) < 1e-3 and abs(b["연_거래일"] - 34.1129) < 1e-3
    for c in names:
        R[c] = mstats(account(WORK / f"base_{c}.csv"))
    assert R["REPRO"]["달"] == b["달"]
    bn = R["REPRO_N"]

    def acct(c):
        x = R[c]
        return (x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"]
                and x["연_거래일"] >= 30.702 and x["최악달"] >= b["최악달"])
    mech = {"손실달_이하": R[CENTER]["손실"] <= R[ABL]["손실"], "연_큼": gt(R[CENTER]["연_거래일"], R[ABL]["연_거래일"])}
    mech["지지"] = mech["손실달_이하"] and mech["연_큼"]
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연_거래일"] >= 30.702, "⑥깊이": R[c]["최악달"] >= b["최악달"],
               "⑤": all(acct(n) for n in NEI[c]), "기전": mech["지지"],
               "중립순서": (R[c + "_N"]["최악날"] >= -15 and R[c + "_N"]["최악달"] >= -15 and R[c + "_N"]["손실"] < bn["손실"]
                        and R[c + "_N"]["연_거래일"] >= 30.702)} for c in CELLS}
    ok = [c for c in CELLS if all(why[c].values())]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    sh = {c: shares(WORK / f"base_{c}.csv") for c in names}
    out = {"cells": R, "기전": mech, "잣대": why, "자격": ok, "순위": rank, "판정": "SELECTED" if rank else "NO_IMPROVEMENT",
           "중립 순서 P0(REPRO_N) — P0와 같은 달 수익인가": R["REPRO_N"]["달"] == b["달"], "바탕 평균 몫(보고)": sh, "장부": rb, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in ["P0"] + names:
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False), sh.get(c, ""))
    print("기전", mech, "자격", ok, "순위", rank, "중립 순서 P0 같음", out["중립 순서 P0(REPRO_N) — P0와 같은 달 수익인가"])


if __name__ == "__main__":
    {"build": build, "run": run, "cut": cut, "cutacct": cutacct}[sys.argv[1]]()
