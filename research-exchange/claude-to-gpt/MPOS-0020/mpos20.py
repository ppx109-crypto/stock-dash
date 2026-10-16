"""MPOS-0020(키움 부품 → 1일봉 정배열 갈래 청산 · 사용자 2026-10-16 승인): 칸 IMM(원판 · 기준 REPRO_G와 같아야 함)
· NP3 · NP5 · NP7 · NP10('무익 N일') · CH10 · CH20 · CH40('N일 채널 저점').
흐름: ex20.py(고정 나무 엔진 · tree_run) → 장부 → z100g(MPOS-0012 · 같은 날 비율 배정) → 덧붙임 → 114달 잣대(기준선 REPRO_G).
python3 mpos20.py ledgers | cut | build | cutacct | run"""
import json
import math
import os
import sys
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos20")   # 계산 폴더
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
WORK = SP / "mpos20"
M12 = SP / "r8/research-exchange/claude-to-gpt/MPOS-0012"
sys.path.insert(0, str(M12))
import mpos12 as M  # noqa: E402

X = M.X
CELLS = {"IMM": dict(EX_MODE="IMM"), **{f"NP{n}": dict(EX_MODE="NP", EX_N=str(n)) for n in (3, 5, 7, 10)},
         **{f"CH{n}": dict(EX_MODE="CH", EX_N=str(n)) for n in (10, 20, 40)}}
EXTRA = {}
SIGS = {}
CAND = ["NP3", "NP5", "NP7", "NP10", "CH10", "CH20", "CH40"]
NEI = {"NP3": ["NP5"], "NP5": ["NP3", "NP7"], "NP7": ["NP5", "NP10"], "NP10": ["NP7"],
       "CH10": ["CH20"], "CH20": ["CH10", "CH40"], "CH40": ["CH20"]}
POISONS = ("20190628", "20240628")
RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"


def verify():
    lock = M.verify()                                      # MPOS-0012 잠금(z100g · 바탕 · 입력) 그대로인지
    for f in ("ex20.py", "mpos20.py"):
        lock[f] = X.sha(str(HERE / f))
    lock["NRL_CACHE /tmp/maxret-0026-cache.pkl"] = X.sha("/tmp/maxret-0026-cache.pkl")     # GPT #438 고칠 것 3: 실제 읽는 캐시
    if not (HERE / "lock.json").exists():                 # 대리 검토 2: 잠금 없으면 멈춤
        sys.exit("lock.json 없음 → 중단")
    bad = [f for f, v in json.load(open(HERE / "lock.json")).items() if lock.get(f) != v]
    if bad:
        sys.exit(f"잠금 불일치 → 중단 {bad}")
    return lock


def eng_job(name, extra):
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update(NRL_CACHE="/tmp/maxret-0026-cache.pkl", PYTHONHASHSEED="0", EX_OUT=str(WORK / f"led_{name}.json"), **extra)
    return dict(cmd=[sys.executable, str(M.TREE_RUN), str(WORK / f"eng_{name}.mods.json"), str(HERE / "ex20.py")], env=env, cwd=str(M.TREE),
                out=str(WORK / f"eng_{name}.log"), clean=[str(WORK / f"led_{name}.json")])


POISON_CELLS = ("NP5", "CH20", "LEAK")


def cut_days(c):
    """독 시험 날: 고정 2날 + 그 칸이 실제로 산 날 가운데 고르게 6날(하루 앞을 보는 실수는 자른 날의 매수에서만 드러나므로)."""
    # 엔진(lab.run)은 한 반의 매매가 60건보다 적으면 그 반 결과를 버림(None) → 각 반에서 70번째 매수 뒤 날만 고름
    led = json.load(open(WORK / f"led_{c}.json"))
    ok = []
    for lo, hi in (("", "20210101"), ("20210101", "99999999")):
        bs = sorted(r[1] for r in led if lo <= r[1] < hi)
        ok += sorted(set(bs[70:]))
    pick = [ok[int(k * (len(ok) - 1) / 7)] for k in range(1, 7)]
    return sorted(set(POISONS) | set(pick))


def _rec(jobs, rc):
    rec = {}
    for c in jobs:
        f = WORK / f"led_{c}.json"
        mods = json.load(open(WORK / f"eng_{c}.mods.json")) if (WORK / f"eng_{c}.mods.json").exists() else {"바깥": ["없음"]}
        rec[c] = {"rc": rc[c], "장부 지문": X.sha(str(f)) if f.exists() else None, "줄": len(json.load(open(f))) if f.exists() and not c.startswith("SIG") else None,
                  "바깥 모듈": mods["바깥"], "판정": "PASS" if rc[c] == 0 and f.exists() and not mods["바깥"] else "FAIL"}
    return rec


def ledgers():
    lock = verify()
    jobs = {c: eng_job(c, e) for c, e in {**CELLS, **EXTRA, **SIGS}.items()}
    jobs["LEAK"] = eng_job("LEAK", dict(EX_MODE="LEAK"))                              # 검사 도구 자체 시험: 일부러 다음 날 종가를 본 판
    for nm, b in (("엔진", lambda: jobs),):
        bad = X.dry({nm: b})
        if bad:
            sys.exit(f"마른 실행 FAIL {bad}")
    rec = _rec(jobs, X.run_dag(jobs, workers=2, log=lambda m: print(m, flush=True)))      # 메모리 때문에 2개씩
    pj = {}
    for c in POISON_CELLS:
        base = dict(EX_MODE="LEAK") if c == "LEAK" else CELLS[c]
        for t in cut_days(c):
            pj[f"{c}_P{t}"] = eng_job(f"{c}_P{t}", dict(base, EX_POISON=t))
    rec.update(_rec(pj, X.run_dag(pj, workers=2, log=lambda m: print(m, flush=True))))
    for c in ("IMM",):
        rec[c]["원 장부와 같음"] = rec[c]["장부 지문"] == RAW_SHA
        if not rec[c]["원 장부와 같음"]:
            rec[c]["판정"] = "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_ledgers.json", "w"), ensure_ascii=False, indent=1)
    print(sum(r["판정"] == "PASS" for r in rec.values()), "/", len(rec), "IMM 원 장부와 같음", rec["IMM"]["원 장부와 같음"])
    if any(r["판정"] != "PASS" for r in rec.values()):
        sys.exit(3)


def buys(led, t):
    """자른 날까지 산 진입(종목 · 산 날) → 자리 합(부분 청산 줄을 한 진입으로 묶음 · 나눔은 뒤 값에 따라 달라질 수 있음)."""
    got = {}
    for r in led:
        if r[1] <= t:
            got[(r[0], r[1])] = got.get((r[0], r[1]), 0) + r[4]
    return got


def cut():
    """독 시험: 자른 날 뒤 종가를 0.7배로 바꾸고 그 뒤엔 새로 사지 않는 판 vs 온 판 → 자른 날까지 산 매매(종목 · 산 날)와
    자른 날까지 끝난 매매(줄 전체)가 한 건도 안 다름. 칸 NP5 · CH20 × 8날. 검사 도구 자체 시험: LEAK(일부러 다음 날 종가)는
    8날 가운데 하나 이상에서 달라져야 함. 성과 출력 없음."""
    lock = verify()
    out = []
    for c in POISON_CELLS:
        full = json.load(open(WORK / f"led_{c}.json"))
        diff = []
        for t in cut_days(c):
            part = json.load(open(WORK / f"led_{c}_P{t}.json"))
            same = buys(full, t) == buys(part, t) and sorted(tuple(r) for r in full if r[2] <= t) == sorted(tuple(r) for r in part if r[2] <= t)
            diff.append(not same)
            if c != "LEAK":
                out.append({"칸": c, "자른 날": t, "산 진입": len(buys(full, t)), "판정": "PASS" if same else "FAIL"})
        if c == "LEAK":
            out.append({"칸": "LEAK(일부러 미래)", "다른 날 수": sum(diff), "날 수": len(diff), "판정": "PASS" if any(diff) else "FAIL", "뜻": "시험이 미래 참조를 잡으면 PASS"})
        for x in out[-(1 if c == "LEAK" else len(diff)):]:
            print(json.dumps(x, ensure_ascii=False))
    # 신호 단위 접근 감사(대리 검토 6): 모든 줄에서 판단이 읽은 종가 · 정배열 모양 · 신호 줄의 가장 먼 앞날(줄 번호 차) ≤ 0
    for c in SIGS:
        g = json.load(open(WORK / f"led_{c}.json"))
        far = max(v["판단이 읽은 가장 먼 앞날(줄 수)"] for v in g.values())
        leak = "LEAK" in c
        out.append({"칸": c, "읽은 가장 먼 앞날": far, "줄": sum(v["줄"] for v in g.values()),
                    "판정": "PASS" if (far > 0 if leak else far <= 0) else "FAIL", "뜻": "LEAK는 앞날을 읽어야 PASS(검사 힘)" if leak else "앞날 안 읽음"})
        print(json.dumps(out[-1], ensure_ascii=False))
    rl = json.load(open(HERE / "receipt_ledgers.json"))["행"]
    shas = {c: X.sha(str(WORK / f"led_{c}.json")) for c in rl}
    if any(shas[c] != rl[c]["장부 지문"] for c in rl):
        sys.exit("장부 영수증과 파일 지문 다름 → 중단")
    json.dump({"잠금": lock, "행": out, "장부 지문": shas}, open(HERE / "receipt_cut.json", "w"), ensure_ascii=False, indent=1)
    if any(x["판정"] != "PASS" for x in out):
        sys.exit(3)


def build():
    lock = verify()
    rl = json.load(open(HERE / "receipt_ledgers.json"))["행"]
    jobs, rec = {}, {}
    for c in CELLS:
        led = WORK / f"led_{c}.json"
        assert X.sha(str(led)) == rl[c]["장부 지문"], c
        env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
        env.update(M.ENV)
        env.update(Z_D1_LED=str(led), Z_OUT=str(WORK / f"base_{c}.csv"))
        jobs[c] = dict(cmd=[sys.executable, str(M.TREE_RUN), str(WORK / f"base_{c}.mods.json"), str(M.Z100G)], env=env, cwd=str(M.TREE),
                       out=str(WORK / f"base_{c}.log"), clean=[str(WORK / f"base_{c}.csv")])
    bad = X.dry({"z100g": lambda: jobs})
    if bad:
        sys.exit(f"마른 실행 FAIL {bad}")
    rc = X.run_dag(jobs, workers=X.CPU, log=lambda m: print(m, flush=True))
    for c in jobs:
        f = WORK / f"base_{c}.csv"
        mods = json.load(open(WORK / f"base_{c}.mods.json")) if (WORK / f"base_{c}.mods.json").exists() else {"바깥": ["없음"]}
        rec[c] = {"rc": rc[c], "바탕 지문": X.sha(str(f)) if f.exists() else None, "장부 지문": rl[c]["장부 지문"],
                  "판정": "PASS" if rc[c] == 0 and f.exists() and not mods["바깥"] else "FAIL"}
    g = json.load(open(M12 / "receipt_build.json"))["REPRO_G"]["바탕 지문"]
    rec["IMM"]["REPRO_G와 같음"] = rec["IMM"]["바탕 지문"] == g
    if not rec["IMM"]["REPRO_G와 같음"]:
        rec["IMM"]["판정"] = "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_build.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({c: r["판정"] for c, r in rec.items()}, ensure_ascii=False), rec["IMM"]["REPRO_G와 같음"])
    if any(r["판정"] != "PASS" for r in rec.values()):
        sys.exit(3)


def cutacct():
    """덧붙임 · 국면 접두사(MPOS-0012와 같은 검사 · 칸 5 × 자른 날 3)."""
    lock = verify()
    rb = json.load(open(HERE / "receipt_build.json"))["행"]
    out = []
    for c in CELLS:
        f = WORK / f"base_{c}.csv"
        assert X.sha(str(f)) == rb[c]["바탕 지문"]
        full = M.account(f)
        for ct in M.CUTS:
            M.Dv.CUT = ct
            part = M.account(f)
            M.Dv.CUT, M.Dv.DATA, M.Dv.FEAT = "", None, None
            dd = [d for d in full if d <= ct]
            ok = bool(dd) and max(part) <= ct and all(part.get(d) == full[d] for d in dd)
            out.append({"칸": c, "자른 날": ct, "날": len(dd), "판정": "PASS" if ok else "FAIL"})
    json.dump({"잠금": lock, "행": out}, open(HERE / "receipt_cutacct.json", "w"), ensure_ascii=False, indent=1)
    print(sum(x["판정"] == "PASS" for x in out), "/", len(out))
    if any(x["판정"] != "PASS" for x in out):
        sys.exit(3)


def front_pick(R):
    """설정은 앞 기간에서 고르고 뒤 기간에서 본 결과를 함께 적음(CLAUDE.md): 부품마다 앞 반 손실 달이 가장 적은 칸(같으면 앞 반 연 수익 큰 칸)."""
    out = {}
    for fam in ("NP", "CH"):
        cs = [c for c in CAND if c.startswith(fam)]
        best = sorted(cs, key=lambda c: (R[c]["앞손실"], -R[c].get("앞연", 0), c))[0]
        out[fam] = {"고른 칸": best, "앞손실": R[best]["앞손실"], "뒤손실": R[best]["뒤손실"], "기준 뒤손실": R["IMM"]["뒤손실"]}
    return out


def run():
    lock = verify()
    nled = len(CELLS) + 1 + sum(len(cut_days(c)) for c in POISON_CELLS)
    for nm, n in (("receipt_ledgers.json", nled), ("receipt_cut.json", sum(len(cut_days(c)) for c in POISON_CELLS if c != "LEAK") + 1), ("receipt_build.json", len(CELLS)),
                  ("receipt_cutacct.json", 3 * len(CELLS))):
        r = json.load(open(HERE / nm))
        rows = list(r["행"].values()) if isinstance(r["행"], dict) else r["행"]
        if r["잠금"]["mpos20.py"] != lock["mpos20.py"] or r["잠금"]["ex20.py"] != lock["ex20.py"] or (n and len(rows) != n) or any(x["판정"] != "PASS" for x in rows):
            sys.exit(f"{nm}: 지문 · 건수 · FAIL → 중단")
    rl = json.load(open(HERE / "receipt_ledgers.json"))["행"]
    if json.load(open(HERE / "receipt_cut.json"))["장부 지문"] != {c: v["장부 지문"] for c, v in rl.items()}:
        sys.exit("독 시험 영수증이 장부 영수증과 다른 장부를 봄 → 중단")
    rb = json.load(open(HERE / "receipt_build.json"))["행"]
    for c in CELLS:
        if X.sha(str(WORK / f"base_{c}.csv")) != rb[c]["바탕 지문"] or X.sha(str(WORK / f"led_{c}.json")) != rb[c]["장부 지문"]:
            sys.exit(f"{c} 파일 지문 다름 → 중단")
    R = {c: M.mstats(M.account(WORK / f"base_{c}.csv")) for c in CELLS}
    b = R["IMM"]                                    # = REPRO_G(바이트 같음 확인)
    assert b["손실"] == 40 and b["앞손실"] == 20 and b["뒤손실"] == 20 and abs(b["최악달"] + 13.756) < 1e-3 and abs(b["연_거래일"] - 35.02) < 0.01, b

    def acct(c):
        x = R[c]
        return (x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"]
                and x["연_거래일"] >= 30.702 and x["최악달"] >= b["최악달"])
    mech = {"지지": True, "뜻": "청산 부품 칸은 무작위 대조 없음 · 이웃 칸 평평함(⑤)과 앞 · 뒤 반(②)으로 봄"}
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연_거래일"] >= 30.702, "⑥깊이": R[c]["최악달"] >= b["최악달"],
               "⑤": all(acct(n) for n in NEI[c]), "기전": mech["지지"]} for c in CAND}
    ok = [c for c in CAND if all(why[c].values())]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    led = {c: json.load(open(WORK / f"led_{c}.json")) for c in CELLS}
    info = {c: {"줄": len(led[c]), "평균 손익 %(줄 · 왕복 0.25% 뒤)": round(sum(r[3] for r in led[c]) / len(led[c]), 3)} for c in CELLS}
    sh = {c: M.shares(WORK / f"base_{c}.csv") for c in CELLS}
    costs = {c: float(list(M.csv.DictReader(open(WORK / f"base_{c}.csv")))[-1]["비용누계"]) for c in CELLS}     # 대리 검토 4
    out = {"cells": R, "기준선": "IMM(= REPRO_G)", "기전": mech, "잣대": why, "자격": ok, "순위": rank,
           "판정": "PASS_DIAGNOSTIC(진단 전용 · 후보 아님)" if rank else "NO_IMPROVEMENT",
           "범위": "진단 전용: 일봉 종가 대리 구조 · 상속된 후보 줄 미래 존재 조건(lab.py:317) · 폐지 종목 없음",
           "앞 기간 고르기(보고)": front_pick(R),
           "장부(보고)": info, "바탕 평균 몫(보고)": sh, "바탕 비용 누계(보고 · 빌드 바탕 전체 구간 마지막 행 · 원)": costs, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in CELLS:
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False), info[c], sh[c])
    print("기전", mech, "자격", ok, "순위", rank)


if __name__ == "__main__":
    {"ledgers": ledgers, "cut": cut, "build": build, "cutacct": cutacct, "run": run}[sys.argv[1]]()
