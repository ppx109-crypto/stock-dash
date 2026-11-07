"""MPOS-0022(GPT #453 고침: KR = 참고 대조 · 문턱 = 실제 판단 순간 표본 · 수익 구간 맞춤 · 정배열 진입 쪽 · 사용자 2026-10-17 "다음방향 계속 진행해 · 승인 안 해도 계속 연구"): 칸(셈 전에 고정)
 K70 · K80 · K90: 동조화 문 — 정배열 후보와 들고 있는 종목들의 평균 상관(전 거래일까지 60일 · 구간 맞춤) ≥ 실제 판단 순간 앞 기간 70 · 80 · 90% 분위(0.2315 · 0.2895 · 0.3225)면 안 삼
 KR: 참고 대조(고정 20% 확률 제외 · 기전 검증 아님 · 기술 통계만)
 L5 · L10 · L20: 늦은 구간 진입 막기 — 정배열이 이어진 날 수 ≤ N일 때만 정배열 갈래로 삼
 재현: BASE · K999(문턱 9 = 안 막음) · L999 = 원 장부. 덧붙임은 MIX-0054 그대로. 기준 = BASE(= REPRO_G).
python3 mpos22.py self | ledgers | cut | build | cutacct | run"""
import json
import math
import os
import sys
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos22")   # 계산 폴더
SP = HERE.parent
WORK = HERE
M12 = SP / "r8/research-exchange/claude-to-gpt/MPOS-0012"
sys.path.insert(0, str(M12))
import mpos12 as M  # noqa: E402

X = M.X
Dv = M.Dv
TH = {"K70": "0.2315", "K80": "0.2895", "K90": "0.3225"}    # 실제 판단 순간 표본(K999 = 원판 경로 · 판단 날 ≤ 2021-12-31 · 165개)의 70 · 80 · 90% 분위(GPT #453 2)
LEDGER = {"BASE": dict(EX_MODE="BASE"), "K999": dict(EX_MODE="K", EX_TH="9"), "L999": dict(EX_MODE="L", EX_N="99999"),
          **{c: dict(EX_MODE="K", EX_TH=v) for c, v in TH.items()}, "KR": dict(EX_MODE="KR", EX_P="0.20"),
          **{f"L{n}": dict(EX_MODE="L", EX_N=str(n)) for n in (5, 10, 20)}}
LEAKS = {"KLEAK": dict(EX_MODE="KLEAK", EX_TH="0.2798")}
ACELLS = {}
ALEAK = {}
SANITY = ("BASE", "K999", "L999")
CAND = ["K70", "K80", "K90", "L5", "L10", "L20"]
CONTROL = ["KR"]
NEI = {"K70": ["K80"], "K80": ["K70", "K90"], "K90": ["K80"], "L5": ["L10"], "L10": ["L5", "L20"], "L20": ["L10"]}
FAM = {"K": ["K70", "K80", "K90"], "L": ["L5", "L10", "L20"]}
POISON_CELLS = ("K80", "KR", "L10", "KLEAK")
POISONS = ("20190628", "20240628")
CUTMODES = {"P": "scale", "D": "drop"}
RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
FILES = ("ex22.py", "mpos22.py", "parts22.py", "self22.py", "self22b.py")


def verify():
    lock = M.verify()
    for f in FILES:
        lock[f] = X.sha(str(HERE / f))
    lock["NRL_CACHE /tmp/maxret-0026-cache.pkl"] = X.sha("/tmp/maxret-0026-cache.pkl")
    if not (HERE / "lock.json").exists():
        sys.exit("lock.json 없음 → 중단")
    bad = [f for f, v in json.load(open(HERE / "lock.json")).items() if lock.get(f) != v]
    if bad:
        sys.exit(f"잠금 불일치 → 중단 {bad}")
    return lock


def acct(base_csv, cell=None):
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(base_csv), None, None
    cfg = dict(M.CFG)                                    # 덧붙임은 MIX-0054 그대로(국면 함수 안 바꿈)
    return Dv.account(cfg)[0]


# ---- 장부 ----
def eng_job(name, extra):
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update(NRL_CACHE="/tmp/maxret-0026-cache.pkl", PYTHONHASHSEED="0", EX_OUT=str(WORK / f"led_{name}.json"), EX_PARTS=str(HERE / "parts22.py"), **extra)
    return dict(cmd=[sys.executable, str(M.TREE_RUN), str(WORK / f"eng_{name}.mods.json"), str(HERE / "ex22.py")], env=env, cwd=str(M.TREE),
                out=str(WORK / f"eng_{name}.log"), clean=[str(WORK / f"led_{name}.json"), str(WORK / f"led_{name}.json.audit.json")])


def cut_days(c):
    """자르기 날: 고정 2날 + 그 칸이 실제로 산 날 가운데 고르게 4날(각 반 70번째 매수 뒤)."""
    led = json.load(open(WORK / f"led_{c}.json"))
    ok = []
    for lo, hi in (("", "20210101"), ("20210101", "99999999")):
        bs = sorted(r[1] for r in led if lo <= r[1] < hi)
        ok += sorted(set(bs[70:]))
    pick = [ok[int(k * (len(ok) - 1) / 5)] for k in range(1, 5)]
    return sorted(set(POISONS) | set(pick))


def audit_ok(c, a):
    """모든 판: 부품 지문 = 잠금 · 판단 합 > 0 · 미래 바 0 · 판단 날 못 읽음 0 · 미래 칸 0 · 배정 칸 = 보유 칸.
    정직한 칸: 동조화 문이 읽은 날 ≥ 판단 날 = 0. KLEAK 본판: ≥ 1이어야 함(감사 도구의 힘)."""
    sides = [a[k] for k in ("앞", "뒤") if k in a]
    base = bool(sides) and a.get("부품 지문") == X.sha(str(HERE / "parts22.py")) and sum(x["판단 수"] for x in sides) > 0 and all(
        x["미래 바(오늘 바 날 > 판단 날)"] == 0 and x["판단 날 못 읽음"] == 0 and x["미래 칸(읽은 칸 > 오늘 칸)"] == 0
        and x["배정 칸 대조"]["배정 칸 ≠ 보유 칸"] == 0 for x in sides)
    gate = sum(x["문"]["읽은 날 ≥ 판단 날"] for x in sides)
    if c.split("_")[0] in LEAKS:
        return base and (gate >= 1 if "_" not in c else True)
    return base and gate == 0


def _rec(jobs, rc):
    rec = {}
    for c in jobs:
        f = WORK / f"led_{c}.json"
        af = WORK / f"led_{c}.json.audit.json"
        a = json.load(open(af)) if af.exists() else {}
        mods = json.load(open(WORK / f"eng_{c}.mods.json")) if (WORK / f"eng_{c}.mods.json").exists() else {"바깥": ["없음"]}
        rec[c] = {"rc": rc[c], "장부 지문": X.sha(str(f)) if f.exists() else None, "줄": len(json.load(open(f))) if f.exists() else None,
                  "감사 지문": X.sha(str(af)) if af.exists() else None,
                  "감사": {k: {kk: vv for kk, vv in v.items() if kk != "미래 바 예"} if isinstance(v, dict) else v for k, v in a.items()},
                  "바깥 모듈": mods["바깥"], "판정": "PASS" if rc[c] == 0 and f.exists() and not mods["바깥"] and audit_ok(c, a) else "FAIL"}
    return rec


def selftest():
    """합성 시험(성과 출력 없음): self22.py(상관 창 · 상관 · 난수 · 고르기 · 이 폴더에서 바로) + self22b.py(진입 기록 · 고정 나무 진짜 lab.run · tree_run)."""
    lock = verify()
    import subprocess
    r = subprocess.run([sys.executable, str(HERE / "self22.py")], capture_output=True, text=True, cwd=str(HERE))
    got = json.load(open(WORK / "self_out.json")) if (WORK / "self_out.json").exists() else {"행": [{"시험": "실행", "판정": "FAIL", "오류": r.stderr[-500:]}]}
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update(PYTHONHASHSEED="0", EX_PARTS=str(HERE / "parts22.py"), EX_OUT=str(WORK / "self22b_out.json"))
    rb = subprocess.run([sys.executable, str(M.TREE_RUN), str(WORK / "self22b.mods.json"), str(HERE / "self22b.py")], env=env, cwd=str(M.TREE),
                        capture_output=True, text=True)
    gb = json.load(open(WORK / "self22b_out.json")) if (WORK / "self22b_out.json").exists() else {"행": [{"시험": "B 실행", "판정": "FAIL"}]}
    mods = json.load(open(WORK / "self22b.mods.json"))
    rows = got["행"] + [{"시험": "실행", "판정": "PASS" if r.returncode == 0 else "FAIL"}] + gb["행"] + [
        {"시험": "B 실행 · 바깥 모듈 없음 · 부품 지문", "판정": "PASS" if rb.returncode == 0 and not mods["바깥"] and gb.get("부품 지문") == lock["parts22.py"] else "FAIL"}]
    json.dump({"잠금": lock, "행": rows, "영수증 지문": [X.sha(str(WORK / f)) if (WORK / f).exists() else None for f in ("self_out.json", "self22b_out.json")]},
              open(HERE / "receipt_self.json", "w"), ensure_ascii=False, indent=1)
    print(sum(x["판정"] == "PASS" for x in rows), "/", len(rows))
    if any(x["판정"] != "PASS" for x in rows):
        sys.exit(3)


def ledgers():
    lock = verify()
    jobs = {c: eng_job(c, e) for c, e in {**LEDGER, **LEAKS}.items()}
    bad = X.dry({"엔진": lambda: jobs})
    if bad:
        sys.exit(f"마른 실행 FAIL {bad}")
    rec = _rec(jobs, X.run_dag(jobs, workers=2, log=lambda m: print(m, flush=True)))
    pj = {}
    for c in POISON_CELLS:
        base = {**LEDGER, **LEAKS}[c]
        for t in cut_days(c):
            for k, m in CUTMODES.items():
                pj[f"{c}_{k}{t}"] = eng_job(f"{c}_{k}{t}", dict(base, EX_POISON=t, EX_CUTMODE=m))
    rec.update(_rec(pj, X.run_dag(pj, workers=2, log=lambda m: print(m, flush=True))))
    for c in SANITY:                                          # K999 · L999 = 문을 열어 둔 새 코드 → 원 장부와 같아야 함
        rec[c]["원 장부와 같음"] = rec[c]["장부 지문"] == RAW_SHA
        if not rec[c]["원 장부와 같음"]:
            rec[c]["판정"] = "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_ledgers.json", "w"), ensure_ascii=False, indent=1)
    print(sum(r["판정"] == "PASS" for r in rec.values()), "/", len(rec), "재현", {c: rec[c]["원 장부와 같음"] for c in SANITY})
    if any(r["판정"] != "PASS" for r in rec.values()):
        sys.exit(3)


def buys(led, t):
    got = {}
    for r in led:
        if r[1] <= t:
            got[(r[0], r[1])] = got.get((r[0], r[1]), 0) + r[4]
    return got


def entries(name, t):
    """엔진이 산 진입 기록(parts21.Entries: 종목 · 산 날 · 요청 칸 · 배정 칸) 가운데 자른 날까지(두 반 차례대로)."""
    a = json.load(open(WORK / f"led_{name}.json.audit.json"))
    return [tuple(e) for k in ("앞", "뒤") for e in a[k]["진입(종목 · 산 날 · 요청 칸 · 배정 칸)"] if e[1] <= t]


def same_cut(full, part, t, mode, fname=None, pname=None):
    """P(0.7배) · D(안 읽기) 모두: 자른 날까지 끝난 매매(줄 전체)가 같음 + 자른 날까지 진입 기록(종목 · 날 · 요청 칸 · 배정 칸 · 차례)이 똑같음.
    배정 칸은 엔진 지역 변수로 셈하고, 다음 날 보유 칸 관찰과 장부 단계에서 대조(audit_ok).
    (MPOS-0020의 D는 '진입 ⊆'였음 → 누수가 진입을 더 막으면 못 잡음 · 여기서 고침)"""
    done = sorted(tuple(r) for r in full if r[2] <= t) == sorted(tuple(r) for r in part if r[2] <= t)
    return done and entries(fname, t) == entries(pname, t)


def cut():
    """장부 자르기(성과 출력 없음): K80 · KR · L10 × 6날 × P/D 같아야 함 · KLEAK(상관 창이 5거래일 뒤까지)는 방식마다 하나 이상 달라야 함."""
    lock = verify()
    out = []
    for c in POISON_CELLS:
        full = json.load(open(WORK / f"led_{c}.json"))
        for k in CUTMODES:
            diff = []
            for t in cut_days(c):
                same = same_cut(full, json.load(open(WORK / f"led_{c}_{k}{t}.json")), t, k, c, f"{c}_{k}{t}")
                diff.append(not same)
                if c not in LEAKS:
                    out.append({"칸": c, "방식": k, "자른 날": t, "산 진입": len(buys(full, t)), "판정": "PASS" if same else "FAIL"})
                    print(json.dumps(out[-1], ensure_ascii=False))
            if c in LEAKS:
                out.append({"칸": f"{c}(일부러 미래)", "방식": k, "다른 날 수": sum(diff), "날 수": len(diff), "판정": "PASS" if any(diff) else "FAIL",
                            "뜻": "시험이 미래 참조를 잡으면 PASS"})
                print(json.dumps(out[-1], ensure_ascii=False))
    rl = json.load(open(HERE / "receipt_ledgers.json"))["행"]
    shas = {c: X.sha(str(WORK / f"led_{c}.json")) for c in rl}
    if any(shas[c] != rl[c]["장부 지문"] for c in rl):
        sys.exit("장부 영수증과 파일 지문 다름 → 중단")
    json.dump({"잠금": lock, "행": out, "장부 지문": shas}, open(HERE / "receipt_cut.json", "w"), ensure_ascii=False, indent=1)
    if any(x["판정"] != "PASS" for x in out):
        sys.exit(3)


BUILD = [c for c in LEDGER if c not in ("K999", "L999")]


def build():
    lock = verify()
    rl = json.load(open(HERE / "receipt_ledgers.json"))["행"]
    jobs, rec = {}, {}
    for c in BUILD:
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
    rec["BASE"]["REPRO_G와 같음"] = rec["BASE"]["바탕 지문"] == g
    if not rec["BASE"]["REPRO_G와 같음"]:
        rec["BASE"]["판정"] = "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_build.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({c: r["판정"] for c, r in rec.items()}, ensure_ascii=False), rec["BASE"]["REPRO_G와 같음"])
    if any(r["판정"] != "PASS" for r in rec.values()):
        sys.exit(3)


def books():
    """(이름, 바탕 csv, None): 모든 칸 MIX-0054 덧붙임."""
    out = [(c, WORK / f"base_{c}.csv", None) for c in BUILD]
    out += [(c, WORK / "base_BASE.csv", c) for c in list(ACELLS) + list(ALEAK)]
    return out


def cutacct():
    """덧붙임 · 국면 접두사(MPOS-0012와 같은 검사 · 칸 × 자른 날 3): 자른 자료(바탕 · ETF · 국면)로 다시 셈 → 자른 날까지 NAV 같음.
    덧붙임 코드는 바꾸지 않았으므로 누수 대조는 장부 단계(KLEAK)에서만 봄. 성과 출력 없음."""
    lock = verify()
    rb = json.load(open(HERE / "receipt_build.json"))["행"]
    out = []
    for name, f, cell in books():
        src = "BASE" if cell else name
        assert X.sha(str(f)) == rb[src]["바탕 지문"]
        full = acct(f, cell)
        diff = []
        for ct in M.CUTS:
            Dv.CUT = ct
            part = acct(f, cell)
            Dv.CUT, Dv.DATA, Dv.FEAT = "", None, None
            dd = [d for d in full if d <= ct]
            ok = bool(dd) and max(part) <= ct and all(part.get(d) == full[d] for d in dd)
            diff.append(not ok)
            if name not in ALEAK:
                out.append({"칸": name, "자른 날": ct, "날": len(dd), "판정": "PASS" if ok else "FAIL"})
        if name in ALEAK:
            out.append({"칸": f"{name}(일부러 미래)", "다른 날 수": sum(diff), "판정": "PASS" if any(diff) else "FAIL"})
        print(json.dumps(out[-1], ensure_ascii=False), flush=True)
    json.dump({"잠금": lock, "행": out}, open(HERE / "receipt_cutacct.json", "w"), ensure_ascii=False, indent=1)
    print(sum(x["판정"] == "PASS" for x in out), "/", len(out))
    if any(x["판정"] != "PASS" for x in out):
        sys.exit(3)


FRONT = ("201703", "202112")


def front_annual(r):
    ms = [v for m, v in r["달"].items() if FRONT[0] <= m <= FRONT[1]]
    assert len(ms) == 58, len(ms)
    g = 1.0
    for v in ms:
        g *= 1 + v
    return (g ** (12 / len(ms)) - 1) * 100


def front_pick(R):
    """갈래마다 앞 반 손실 달 → 앞 반 연 → 고정 순서(FAM 목록 순). 뒤 반 값은 안 씀."""
    out = {}
    for fam, cs in FAM.items():
        best = sorted(cs, key=lambda c: (R[c]["앞손실"], -front_annual(R[c]), cs.index(c)))[0]      # 비교엔 반올림 없음(GPT #446 · #450) · 표시만
        out[fam] = {"고른 칸": best, "앞손실": R[best]["앞손실"], "앞연": round(front_annual(R[best]), 3), "뒤손실": R[best]["뒤손실"],
                    "기준 뒤손실": R["BASE"]["뒤손실"]}
    return out


def run():
    lock = verify()
    nled = len(LEDGER) + len(LEAKS) + len(CUTMODES) * sum(len(cut_days(c)) for c in POISON_CELLS)
    ncut = len(CUTMODES) * (sum(len(cut_days(c)) for c in POISON_CELLS if c not in LEAKS) + len(LEAKS))
    nacct = 3 * (len(BUILD) + len(ACELLS)) + len(ALEAK)
    for nm, n in (("receipt_self.json", 0), ("receipt_ledgers.json", nled), ("receipt_cut.json", ncut), ("receipt_build.json", len(BUILD)),
                  ("receipt_cutacct.json", nacct)):
        r = json.load(open(HERE / nm))
        rows = list(r["행"].values()) if isinstance(r["행"], dict) else r["행"]
        if any(r["잠금"][f] != lock[f] for f in FILES) or (n and len(rows) != n) or not rows or any(x["판정"] != "PASS" for x in rows):
            sys.exit(f"{nm}: 지문 · 건수 · FAIL → 중단")
    rl = json.load(open(HERE / "receipt_ledgers.json"))["행"]
    rb = json.load(open(HERE / "receipt_build.json"))["행"]
    for c in BUILD:
        if X.sha(str(WORK / f"base_{c}.csv")) != rb[c]["바탕 지문"] or X.sha(str(WORK / f"led_{c}.json")) != rb[c]["장부 지문"]:
            sys.exit(f"{c} 파일 지문 다름 → 중단")
    R = {name: M.mstats(acct(f, cell)) for name, f, cell in books() if name not in ALEAK}
    b = R["BASE"]
    assert b["손실"] == 40 and b["앞손실"] == 20 and b["뒤손실"] == 20 and abs(b["최악달"] + 13.756) < 1e-3 and abs(b["연_거래일"] - 35.02) < 0.01, b

    def ok_acct(c):
        x = R[c]
        return (x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"]
                and x["연_거래일"] >= 30.702 and x["최악달"] >= b["최악달"])
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연_거래일"] >= 30.702, "⑥깊이": R[c]["최악달"] >= b["최악달"],
               "⑤": all(ok_acct(n) for n in NEI[c])} for c in CAND}
    ok = [c for c in CAND if all(v is True or isinstance(v, str) for v in why[c].values())]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    mech = {"K80 손실 달": R["K80"]["손실"], "KR 손실 달": R["KR"]["손실"], "K80 연": round(R["K80"]["연_거래일"], 3), "KR 연": round(R["KR"]["연_거래일"], 3),
            "지지": "미검증", "뜻": "KR은 막음 몫 · 노출을 맞춘 대조가 아님(GPT #453 1) → K 대 KR은 기술 통계로만 보고 · L 갈래도 미검증"}
    out = {"cells": R, "기준선": "BASE(= REPRO_G)", "기전": mech,
           "잣대": why, "자격": ok, "순위": rank, "판정": "PASS_DIAGNOSTIC(진단 전용 · 후보 아님)" if rank else "NO_IMPROVEMENT",
           "달 수 +/0/−(보고 · 사용자 목표 '모든 달 양수' · 손실 < 40은 그 달성이 아님 · 0인 달도 양수 아님)": {c: [R[c]["이익"], R[c]["영"], R[c]["손실"]] for c in R},
           "대조군": "KR은 후보가 아닌 대조(판정 칸 아님)",
           "앞 기간 고르기(보고)": front_pick(R),
           "문(보고)": {c: {k: rl[c]["감사"][k]["문"] for k in ("앞", "뒤")} for c in LEDGER},
           "바탕 평균 몫(보고)": {c: M.shares(WORK / f"base_{c}.csv") for c in BUILD}, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in R:
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False))
    print("자격", ok, "순위", rank)


if __name__ == "__main__":
    {"self": selftest, "ledgers": ledgers, "cut": cut, "build": build, "cutacct": cutacct, "run": run}[sys.argv[1]]()
