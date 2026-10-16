"""MPOS-0021(국면 다시 나누기 · 사용자 2026-10-16 "장기이평 60 밑 마감 · 국면 제거 · 더 잘게 · 1,2,3 전부 해보자 · 모든 달 양수가 안 되고 있으니").
세 갈래(칸은 셈 전에 고정):
 A 레버리지 봇 국면(덧붙임만 바꿈 · 바탕 = 원판 BASE 바탕 = REPRO_G):
   A_OFF(국면 제거 · 덧붙임 없음) · A_ON(국면 제거 · 늘 레버리지 0.4)
   A2_50 · A2_60 · A2_70(두 국면: 069500 종가 < N일선 = 하락(없음) · 그 밖 = 상승(레버리지 0.4) · 버팀 1)
   A5_075 · A5_100 · A5_125(다섯 국면: z = (종가 / 60일선 − 1) / (20일 흔들림 × √(20/250)) · z ≥ b 강상승 레버리지 0.4 ·
                         0 ≤ z < b 약상승 레버리지 0.2 · −b ≤ z < 0 약하락 인버스 0.2 · z < −b 강하락 없음 · 버팀 3)
 B 1일봉 국면 문(069500 전 거래일 종가 < N일선이면 새로 안 삼): B50 · B60 · B70 · BX50 · BX60 · BX70(BX = 그 조건이면 들고 있는 것도 팜)
 C 시장 폭 문(정배열 갈래): C0(문 없앰 = 국면 제거) · C40 · C60 · CT(잘게: 폭 < 40 안 삼 · 40 ~ 50 정배열 1칸 · 50 ↑ 원판)
 B · C 칸의 덧붙임은 MIX-0054 그대로. 기준 = BASE(= REPRO_G).
흐름: ex21.py(고정 나무 엔진 · tree_run) → 장부 → z100g(MPOS-0012) → 덧붙임(regime_dev · A는 국면 함수만 바꿈) → 114달 잣대.
python3 mpos21.py self | ledgers | cut | build | cutacct | run"""
import json
import math
import os
import sys
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos21")   # 계산 폴더
SP = HERE.parent
WORK = HERE
M12 = SP / "r8/research-exchange/claude-to-gpt/MPOS-0012"
sys.path.insert(0, str(M12))
import mpos12 as M  # noqa: E402

X = M.X
Dv = M.Dv
LEDGER = {"BASE": dict(EX_MODE="BASE"), "C50": dict(EX_MODE="C", EX_N="50"),
          **{f"B{n}": dict(EX_MODE="B", EX_N=str(n)) for n in (50, 60, 70)},
          **{f"BX{n}": dict(EX_MODE="BX", EX_N=str(n)) for n in (50, 60, 70)},
          **{f"C{n}": dict(EX_MODE="C", EX_N=str(n)) for n in (0, 40, 60)}, "CT": dict(EX_MODE="CT")}
LEAKS = {"GLEAK": dict(EX_MODE="GLEAK", EX_N="60")}
ACELLS = {"A_OFF": dict(up_lev=0.0, side_inv=0.0), "A_ON": dict(kind="always"),
          **{f"A2_{n}": dict(kind="two", n=n, persist=1) for n in (50, 60, 70)},
          **{f"A5_{k}": dict(kind="five", zb=int(k) / 100, persist=3) for k in ("075", "100", "125")}}
ALEAK = {"A_LEAK": dict(kind="twoleak", n=60, persist=1)}       # 검사 도구 자체 시험: 다음 20거래일 종가 평균을 봄(판 1은 이틀 뒤 종가 → 0/3)
CAND = list(ACELLS) + [c for c in LEDGER if c not in ("BASE", "C50")]
NEI = {"A_OFF": [], "A_ON": [], "A2_50": ["A2_60"], "A2_60": ["A2_50", "A2_70"], "A2_70": ["A2_60"],
       "A5_075": ["A5_100"], "A5_100": ["A5_075", "A5_125"], "A5_125": ["A5_100"],
       "B50": ["B60"], "B60": ["B50", "B70"], "B70": ["B60"], "BX50": ["BX60"], "BX60": ["BX50", "BX70"], "BX70": ["BX60"],
       "C0": ["C40"], "C40": ["C0", "C60"], "C60": ["C40"], "CT": ["C40", "C60"]}
FAM = {"A2": ["A2_50", "A2_60", "A2_70"], "A5": ["A5_075", "A5_100", "A5_125"], "B": ["B50", "B60", "B70"], "BX": ["BX50", "BX60", "BX70"],
       "C": ["C0", "C40", "C60", "CT"], "A0": ["A_OFF", "A_ON"]}
POISON_CELLS = ("B60", "BX60", "C0", "CT", "GLEAK")
POISONS = ("20190628", "20240628")
CUTMODES = {"P": "scale", "D": "drop"}
RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
FILES = ("ex21.py", "mpos21.py", "parts20.py", "self21.py")


def verify():
    lock = M.verify()
    for f in FILES:
        lock[f] = X.sha(str(HERE / f))
    lock["NRL_CACHE /tmp/maxret-0026-cache.pkl"] = X.sha("/tmp/maxret-0026-cache.pkl")
    lock["069500 (고정 나무 etf-data)"] = X.sha(str(M.TREE / "etf-data/069500.json"))
    if not (HERE / "lock.json").exists():
        sys.exit("lock.json 없음 → 중단")
    bad = [f for f, v in json.load(open(HERE / "lock.json")).items() if lock.get(f) != v]
    if bad:
        sys.exit(f"잠금 불일치 → 중단 {bad}")
    return lock


# ---- A 갈래: regime_dev의 국면 함수만 바꿔 끼움(바탕 · 맞춤 · 비용 셈은 그대로) ----
_RAW, _TG = Dv.raw_state, Dv.targets


def raw_state(f, cfg):
    k = cfg.get("kind")
    if k == "always":
        return "상승"
    if k in ("two", "twoleak"):
        ma = Dv.ma_of(f, cfg["n"])
        if ma is None:
            return "하락"
        x = f["close"]
        if k == "twoleak":                                   # 일부러 다음 20거래일 종가 평균(누적합 · 자료 끝에서 잘림)
            j0, j1 = f["_k"] + 1, min(f["_k"] + 21, len(Dv.PREF) - 1)
            x = (Dv.PREF[j1] - Dv.PREF[j0]) / (j1 - j0) if j1 > j0 else x
        return "하락" if x < ma else "상승"                 # '60일선 밑으로 봉 마감' = 하락
    if k == "five":
        ma, v = Dv.ma_of(f, 60), f.get("v20a")
        if ma is None or not v:
            return "강하락"
        z = (f["close"] / ma - 1) / (v * math.sqrt(20 / 250))
        b = cfg["zb"]
        return "강상승" if z >= b else "약상승" if z >= 0 else "약하락" if z >= -b else "강하락"
    return _RAW(f, cfg)


def targets(state, cfg, f=None):
    five = {"강상승": (1.0, "122630", 0.4), "약상승": (1.0, "122630", 0.2), "약하락": (1.0, "114800", 0.2), "강하락": (1.0, "114800", 0.0)}
    if state in five:
        return five[state]
    return _TG(state, cfg, f)


Dv.raw_state, Dv.targets = raw_state, targets


def acct(base_csv, cell=None):
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(base_csv), None, None
    cfg = dict(M.CFG, **(ACELLS.get(cell) or ALEAK.get(cell) or {}))
    return Dv.account(cfg)[0]


# ---- 장부 ----
def eng_job(name, extra):
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update(NRL_CACHE="/tmp/maxret-0026-cache.pkl", PYTHONHASHSEED="0", EX_OUT=str(WORK / f"led_{name}.json"), EX_PARTS=str(HERE / "parts20.py"), **extra)
    return dict(cmd=[sys.executable, str(M.TREE_RUN), str(WORK / f"eng_{name}.mods.json"), str(HERE / "ex21.py")], env=env, cwd=str(M.TREE),
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
    """모든 판: 부품 지문 = 잠금 · 판단 합 > 0 · 미래 바 0 · 판단 날 못 읽음 0 · 미래 칸 0(새 칸은 종가 다음 칸을 안 읽음).
    정직한 칸: 국면 문이 읽은 069500 날 ≥ 판단 날 = 0. GLEAK 본판: ≥ 1이어야 함(감사 도구의 힘)."""
    sides = [a[k] for k in ("앞", "뒤") if k in a]
    base = bool(sides) and a.get("부품 지문") == X.sha(str(HERE / "parts20.py")) and sum(x["판단 수"] for x in sides) > 0 and all(
        x["미래 바(오늘 바 날 > 판단 날)"] == 0 and x["판단 날 못 읽음"] == 0 and x["미래 칸(읽은 칸 > 오늘 칸)"] == 0 for x in sides)
    gate = sum(x["국면 문"]["읽은 069500 날 ≥ 판단 날"] for x in sides)
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
    """국면 함수 합성 시험(self21.py · 이 폴더에서 바로 · 성과 출력 없음)."""
    lock = verify()
    import subprocess
    r = subprocess.run([sys.executable, str(HERE / "self21.py")], capture_output=True, text=True, cwd=str(HERE))
    got = json.load(open(WORK / "self_out.json")) if (WORK / "self_out.json").exists() else {"행": [{"시험": "실행", "판정": "FAIL", "오류": r.stderr[-500:]}]}
    rows = got["행"] + [{"시험": "실행", "판정": "PASS" if r.returncode == 0 else "FAIL"}]
    json.dump({"잠금": lock, "행": rows, "영수증 지문": X.sha(str(WORK / "self_out.json")) if (WORK / "self_out.json").exists() else None},
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
    for c in ("BASE", "C50"):                                # C50 = 원판 문턱을 새 코드로 다시 씀 → 원 장부와 같아야 함
        rec[c]["원 장부와 같음"] = rec[c]["장부 지문"] == RAW_SHA
        if not rec[c]["원 장부와 같음"]:
            rec[c]["판정"] = "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_ledgers.json", "w"), ensure_ascii=False, indent=1)
    print(sum(r["판정"] == "PASS" for r in rec.values()), "/", len(rec), "BASE · C50 원 장부와 같음", rec["BASE"]["원 장부와 같음"], rec["C50"]["원 장부와 같음"])
    if any(r["판정"] != "PASS" for r in rec.values()):
        sys.exit(3)


def buys(led, t):
    got = {}
    for r in led:
        if r[1] <= t:
            got[(r[0], r[1])] = got.get((r[0], r[1]), 0) + r[4]
    return got


def entries(name, t):
    """엔진이 실제로 산 진입 기록(크기 함수 덮개 · ex21 ENTRIES) 가운데 자른 날까지(두 반 차례대로)."""
    a = json.load(open(WORK / f"led_{name}.json.audit.json"))
    return [tuple(e) for k in ("앞", "뒤") for e in a[k]["진입"] if e[1] <= t]


def same_cut(full, part, t, mode, fname=None, pname=None):
    """P(0.7배) · D(안 읽기) 모두: 자른 날까지 끝난 매매(줄 전체)가 같음 + 자른 날까지 엔진이 산 진입 기록(종목 · 날 · 칸 · 차례)이 똑같음.
    (MPOS-0020의 D는 '진입 ⊆'였음 → 누수가 진입을 더 막으면 못 잡음 · 여기서 고침)"""
    done = sorted(tuple(r) for r in full if r[2] <= t) == sorted(tuple(r) for r in part if r[2] <= t)
    return done and entries(fname, t) == entries(pname, t)


def cut():
    """장부 자르기(성과 출력 없음): B60 · BX60 · C0 · CT × 6날 × P/D 같아야 함 · GLEAK(국면 문이 5거래일 뒤 069500을 봄)는 방식마다 하나 이상 달라야 함."""
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


BUILD = [c for c in LEDGER if c != "C50"]


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
    """(이름, 바탕 csv, A 칸 이름 또는 None): B · C 칸은 MIX-0054 덧붙임 · A 칸은 BASE 바탕 위에 국면 함수만 바꿈."""
    out = [(c, WORK / f"base_{c}.csv", None) for c in BUILD]
    out += [(c, WORK / "base_BASE.csv", c) for c in list(ACELLS) + list(ALEAK)]
    return out


def cutacct():
    """덧붙임 · 국면 접두사(MPOS-0012와 같은 검사 · 칸 × 자른 날 3): 자른 자료(바탕 · ETF · 국면)로 다시 셈 → 자른 날까지 NAV 같음.
    A_LEAK(다음 20거래일 평균)는 3날 가운데 하나 이상에서 달라야 함. 성과 출력 없음."""
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
        best = sorted(cs, key=lambda c: (R[c]["앞손실"], -round(front_annual(R[c]), 9), cs.index(c)))[0]
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
               "⑤": all(ok_acct(n) for n in NEI[c]) if NEI[c] else "이웃 없음(국면 제거 대조 · 진단 전용)"} for c in CAND}
    ok = [c for c in CAND if all(v is True or isinstance(v, str) for v in why[c].values())]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    out = {"cells": R, "기준선": "BASE(= REPRO_G)", "기전": {"지지": "미검증", "뜻": "국면 칸은 무작위 대조 없음 → 판정은 ①~⑥로만"},
           "잣대": why, "자격": ok, "순위": rank, "판정": "PASS_DIAGNOSTIC(진단 전용 · 후보 아님)" if rank else "NO_IMPROVEMENT",
           "손실 달 수(보고 · 사용자 목표 '모든 달 양수')": {c: R[c]["손실"] for c in R},
           "앞 기간 고르기(보고)": front_pick(R),
           "국면 문(보고)": {c: {k: rl[c]["감사"][k]["국면 문"] for k in ("앞", "뒤")} for c in LEDGER},
           "바탕 평균 몫(보고)": {c: M.shares(WORK / f"base_{c}.csv") for c in BUILD}, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in R:
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False))
    print("자격", ok, "순위", rank)


if __name__ == "__main__":
    {"self": selftest, "ledgers": ledgers, "cut": cut, "build": build, "cutacct": cutacct, "run": run}[sys.argv[1]]()
