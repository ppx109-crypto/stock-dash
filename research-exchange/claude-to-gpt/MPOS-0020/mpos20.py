"""MPOS-0020(키움 부품 → 1일봉 정배열 갈래 청산 · 사용자 2026-10-16 승인): 칸 IMM(원판 · 기준 REPRO_G와 같아야 함)
· NP3 · NP5 · NP7 · NP10('무익 N일') · CH10 · CH20 · CH40('N일 채널 저점').
흐름: ex20.py(고정 나무 엔진 · tree_run) → 장부 → z100g(MPOS-0012 · 같은 날 비율 배정) → 덧붙임 → 114달 잣대(기준선 REPRO_G).
python3 mpos20.py self | ledgers | cut | build | cutacct | align | run"""
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
CAND = ["NP3", "NP5", "NP7", "NP10", "CH10", "CH20", "CH40"]
NEI = {"NP3": ["NP5"], "NP5": ["NP3", "NP7"], "NP7": ["NP5", "NP10"], "NP10": ["NP7"],
       "CH10": ["CH20"], "CH20": ["CH10", "CH40"], "CH40": ["CH20"]}
POISONS = ("20190628", "20240628")
RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"


def verify():
    lock = M.verify()                                      # MPOS-0012 잠금(z100g · 바탕 · 입력) 그대로인지
    for f in ("ex20.py", "mpos20.py", "parts20.py", "self20.py"):
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
    env.update(NRL_CACHE="/tmp/maxret-0026-cache.pkl", PYTHONHASHSEED="0", EX_OUT=str(WORK / f"led_{name}.json"), EX_PARTS=str(HERE / "parts20.py"), **extra)
    return dict(cmd=[sys.executable, str(M.TREE_RUN), str(WORK / f"eng_{name}.mods.json"), str(HERE / "ex20.py")], env=env, cwd=str(M.TREE),
                out=str(WORK / f"eng_{name}.log"), clean=[str(WORK / f"led_{name}.json"), str(WORK / f"led_{name}.json.audit.json")])


POISON_CELLS = ("NP5", "CH20", "LEAK", "LEAK2")
LEAKS = ("LEAK", "LEAK2")
CUTMODES = {"P": "scale", "D": "drop"}      # P = 그 날 뒤 종가 0.7배 · D = 그 날 뒤 종가 줄을 처음부터 안 읽음(I_CUT)


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


def audit_ok(c, a):
    """날짜 접근 감사 관문: 모든 판(LEAK 포함)에서 미래 바 0 · 판단 날 못 읽음 0 · 부품 지문 = 잠금.
    정직한 칸은 미래 칸 0. LEAK · LEAK2 본판은 미래 칸 ≥ 1이어야 함(감사 도구의 힘)."""
    sides = [a[k] for k in ("앞", "뒤") if k in a]
    # 판단 수는 두 반 합으로 봄(자른 날이 앞 반이면 뒤 반은 새로 안 사서 판단 0이 정상)
    base = bool(sides) and a.get("부품 지문") == X.sha(str(HERE / "parts20.py")) and sum(x["판단 수"] for x in sides) > 0 and all(
        x["미래 바(오늘 바 날 > 판단 날)"] == 0 and x["판단 날 못 읽음"] == 0 for x in sides)
    far = sum(x["미래 칸(읽은 칸 > 오늘 칸)"] for x in sides)
    leak = c.split("_")[0] in LEAKS
    if leak and "_" not in c:
        return base and far >= 1
    return base and (leak or far == 0)


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


def ledgers():
    lock = verify()
    jobs = {c: eng_job(c, e) for c, e in CELLS.items()}
    for lk in LEAKS:                                                                   # 검사 도구 자체 시험: 일부러 다음 날(LEAK) · 모레/내일 비율(LEAK2)을 본 판
        jobs[lk] = eng_job(lk, dict(EX_MODE=lk))
    for nm, b in (("엔진", lambda: jobs),):
        bad = X.dry({nm: b})
        if bad:
            sys.exit(f"마른 실행 FAIL {bad}")
    rec = _rec(jobs, X.run_dag(jobs, workers=2, log=lambda m: print(m, flush=True)))      # 메모리 때문에 2개씩
    pj = {}
    for c in POISON_CELLS:
        base = dict(EX_MODE=c) if c in LEAKS else CELLS[c]
        for t in cut_days(c):
            for k, m in CUTMODES.items():
                pj[f"{c}_{k}{t}"] = eng_job(f"{c}_{k}{t}", dict(base, EX_POISON=t, EX_CUTMODE=m))
    rec.update(_rec(pj, X.run_dag(pj, workers=2, log=lambda m: print(m, flush=True))))
    for c in ("IMM",):
        rec[c]["원 장부와 같음"] = rec[c]["장부 지문"] == RAW_SHA
        if not rec[c]["원 장부와 같음"]:
            rec[c]["판정"] = "FAIL"
    json.dump({"잠금": lock, "행": rec}, open(HERE / "receipt_ledgers.json", "w"), ensure_ascii=False, indent=1)
    print(sum(r["판정"] == "PASS" for r in rec.values()), "/", len(rec), "IMM 원 장부와 같음", rec["IMM"]["원 장부와 같음"])
    if any(r["판정"] != "PASS" for r in rec.values()):
        sys.exit(3)


def selftest():
    """감사 도구 · NP/CH 경계 합성 시험(self20.py · 고정 나무 진짜 lab.run). 성과 출력 없음."""
    lock = verify()
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update(PYTHONHASHSEED="0", EX_PARTS=str(HERE / "parts20.py"), EX_OUT=str(WORK / "self_out.json"))
    jobs = {"self": dict(cmd=[sys.executable, str(M.TREE_RUN), str(WORK / "self.mods.json"), str(HERE / "self20.py")], env=env, cwd=str(M.TREE),
                         out=str(WORK / "self.log"), clean=[str(WORK / "self_out.json")])}
    rc = X.run_dag(jobs, workers=1, log=lambda m: print(m, flush=True))
    got = json.load(open(WORK / "self_out.json")) if (WORK / "self_out.json").exists() else {"행": [{"시험": "실행", "판정": "FAIL"}]}
    mods = json.load(open(WORK / "self.mods.json"))
    rows = got["행"] + [{"시험": "실행 · 바깥 모듈 없음 · 부품 지문", "판정": "PASS" if rc["self"] == 0 and not mods["바깥"]
                         and got.get("부품 지문") == lock["parts20.py"] else "FAIL"}]
    json.dump({"잠금": lock, "행": rows, "뜻": got.get("뜻"), "영수증 지문": X.sha(str(WORK / "self_out.json"))}, open(HERE / "receipt_self.json", "w"),
              ensure_ascii=False, indent=1)
    print(sum(r["판정"] == "PASS" for r in rows), "/", len(rows))
    if any(r["판정"] != "PASS" for r in rows):
        sys.exit(3)


def buys(led, t):
    """자른 날까지 산 진입(종목 · 산 날) → 자리 합(부분 청산 줄을 한 진입으로 묶음 · 나눔은 뒤 값에 따라 달라질 수 있음)."""
    got = {}
    for r in led:
        if r[1] <= t:
            got[(r[0], r[1])] = got.get((r[0], r[1]), 0) + r[4]
    return got


def same_cut(full, part, t, mode):
    """P(0.7배): 자른 날까지 산 진입(종목 · 산 날 · 자리 합)과 자른 날까지 끝난 매매(줄 전체)가 같음.
    D(안 읽기): 자른 날까지 끝난 매매(줄 전체)가 같음 + 자른 판의 진입이 모두 온 판에 있음
    (자른 날에 아직 들고 있던 진입은 자른 판에선 팔 날이 없어 줄이 안 생김 → 그 진입은 P에서 확인)."""
    done = sorted(tuple(r) for r in full if r[2] <= t) == sorted(tuple(r) for r in part if r[2] <= t)
    if mode == "P":
        return done and buys(full, t) == buys(part, t)
    return done and set(buys(part, t)) <= set(buys(full, t))


def cut():
    """독 시험: 자른 날 뒤 종가를 0.7배로 바꾸거나(P) 처음부터 안 읽고(D) 그 뒤엔 새로 사지 않는 판 vs 온 판(same_cut).
    칸 NP5 · CH20 × 8날 × 두 방식. 검사 도구 자체 시험: LEAK(내일 종가) · LEAK2(모레/내일 비율)는 방식마다 8날 가운데
    하나 이상에서 달라져야 함. 성과 출력 없음."""
    lock = verify()
    out = []
    for c in POISON_CELLS:
        full = json.load(open(WORK / f"led_{c}.json"))
        for k in CUTMODES:
            diff = []
            for t in cut_days(c):
                part = json.load(open(WORK / f"led_{c}_{k}{t}.json"))
                same = same_cut(full, part, t, k)
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


FRONT = ("201703", "202112")     # mstats 앞 반(58달) · 엔진 장부의 앞/뒤(rule.MID = 20210101)와 다름 — 결과표에 따로 적음


def front_annual(r):
    """앞 반 58달(2017-03 ~ 2021-12) 달 수익을 곱해 연으로 바꿈: (Π(1 + 달))^(12 / 58) − 1 (%)."""
    ms = [v for m, v in r["달"].items() if FRONT[0] <= m <= FRONT[1]]
    assert len(ms) == 58, len(ms)
    g = 1.0
    for v in ms:
        g *= 1 + v
    return (g ** (12 / len(ms)) - 1) * 100


def front_pick(R, cand=None):
    """앞에서 고르고 뒤에서 봄(CLAUDE.md · GPT #446 §1): 부품마다 ① 앞 반 손실 달 적은 칸 ② 같으면 앞 반 연(front_annual) 큰 칸
    ③ 그래도 같으면 고정 순서(NP3 < NP5 < NP7 < NP10 · CH10 < CH20 < CH40). 뒤 반 값은 고르기에 쓰지 않음."""
    cand = cand or CAND
    out = {}
    for fam in ("NP", "CH"):
        cs = [c for c in cand if c.startswith(fam)]
        best = sorted(cs, key=lambda c: (R[c]["앞손실"], -front_annual(R[c]), cand.index(c)))[0]      # 비교엔 반올림 없음(GPT #446 round 2) · 표시만 반올림
        out[fam] = {"고른 칸": best, "앞손실": R[best]["앞손실"], "앞연": round(front_annual(R[best]), 3), "뒤손실": R[best]["뒤손실"],
                    "기준 뒤손실": R["IMM"]["뒤손실"], "기간": "mstats 앞 2017-03 ~ 2021-12(58달) · 뒤 2022-01 ~ 2026-08(56달)"}
    return out


def align():
    """달력 정렬 대조(GPT #446 §2): 모든 칸(7 + IMM)을 align_days=True로 다시 돌려 장부가 원 칸과 바이트까지 같은지(결정 같음).
    직접 증거는 장부 단계의 날짜 접근 감사(미래 바 0)이고, 이것은 그 보조 대조. 성과 출력 없음."""
    lock = verify()
    rl = json.load(open(HERE / "receipt_ledgers.json"))["행"]
    jobs = {f"{c}_AL": eng_job(f"{c}_AL", dict(e, EX_ALIGN="1")) for c, e in CELLS.items()}
    rc = X.run_dag(jobs, workers=2, log=lambda m: print(m, flush=True))
    out = {}
    for c in CELLS:
        f = WORK / f"led_{c}_AL.json"
        mods = json.load(open(WORK / f"eng_{c}_AL.mods.json")) if (WORK / f"eng_{c}_AL.mods.json").exists() else {"바깥": ["없음"]}
        sh = X.sha(str(f)) if f.exists() else None
        af = WORK / f"led_{c}_AL.json.audit.json"
        a = json.load(open(af)) if af.exists() else {}
        out[c] = {"rc": rc[f"{c}_AL"], "정렬 장부 지문": sh, "원 장부 지문": rl[c]["장부 지문"], "바깥 모듈": mods["바깥"],
                  "감사": {k: {kk: vv for kk, vv in v.items() if kk != "미래 바 예"} if isinstance(v, dict) else v for k, v in a.items()},
                  "판정": "PASS" if rc[f"{c}_AL"] == 0 and sh == rl[c]["장부 지문"] and not mods["바깥"] and audit_ok(c, a) else "FAIL"}
        print(c, out[c]["판정"], flush=True)
    json.dump({"잠금": lock, "행": out}, open(HERE / "receipt_align.json", "w"), ensure_ascii=False, indent=1)
    if any(x["판정"] != "PASS" for x in out.values()):
        sys.exit(3)


def mech_report(led):
    """기전 진단(보고만 · GPT #446 §3): 원판(IMM)과 같은 진입(종목 · 산 날) 수 · 그중 판 날이 앞당겨진 진입 · 새 진입 · 판 날과 같은 날 같은 종목 재진입."""
    def entries(rows):
        e = {}
        for c, b, s_, g, z in rows:
            k = (c, b)
            x = e.setdefault(k, {"판": s_, "자리": 0})
            x["판"] = max(x["판"], s_)
            x["자리"] += z
        return e
    base = entries(led["IMM"])
    out = {}
    for c in CAND:
        e = entries(led[c])
        same = [k for k in e if k in base]
        early = [k for k in same if e[k]["판"] < base[k]["판"]]
        new = [k for k in e if k not in base]
        sells = sorted((r[0], r[2]) for r in led[c])
        buys = {(r[0], r[1]) for r in led[c]}
        re_in = sum(1 for code, sd in set(sells) if (code, sd) in buys)
        out[c] = {"진입": len(e), "원판과 같은 진입": len(same), "그중 판 날 앞당김": len(early), "새 진입": len(new),
                  "원판에만 있는 진입": len([k for k in base if k not in e]), "판 날 같은 날 같은 종목 재진입": re_in}
    return out


STAGE_COPY = "mpos20_stage.py"     # 성과 안 보는 단계(self · ledgers · cut · build · cutacct · align)를 돌린 그 코드 사본(영수증 잠금 지문과 같아야 함)
RUN_ONLY = {"front_pick", "run", "stage_reuse"}


def stage_reuse(lock):
    """단계 산출물 재사용 근거(GPT #446 round 2): 영수증을 만든 사본과 지금 코드의 구문 나무(ast)를 맨 위 문장마다 견줘,
    run에서만 쓰는 함수(front_pick · run · stage_reuse)와 이 두 상수 줄 밖에는 한 글자도 다르지 않음을 확인. 다르면 멈춤."""
    import ast
    def parts(src):
        out = {}
        for node in ast.parse(src).body:          # 이름 없는 문장은 내용 지문을 이름으로(자리 번호가 밀려도 같은 문장은 같게 봄)
            name = getattr(node, "name", None) or (node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                                                   else "#" + __import__("hashlib").sha256(ast.dump(node).encode()).hexdigest()[:12])
            out.setdefault(name, []).append(ast.dump(node))
        return out
    old, new = parts(open(HERE / STAGE_COPY).read()), parts(open(HERE / "mpos20.py").read())
    skip = RUN_ONLY | {"STAGE_COPY", "RUN_ONLY"}
    diff = sorted(k for k in set(old) | set(new) if k not in skip and old.get(k) != new.get(k))
    numbered = [k for k in set(old) | set(new) if k.startswith("#")]
    rec = {"단계 사본 지문": X.sha(str(HERE / STAGE_COPY)), "지금 코드 지문": lock["mpos20.py"], "다른 맨 위 문장(run 전용 밖)": diff,
           "이름 없는 맨 위 문장": len(numbered), "run 전용": sorted(RUN_ONLY & (set(old) | set(new)))}
    if diff:
        sys.exit(f"단계 코드가 바뀜 → 단계 다시 돌려야 함 {diff}")
    return rec


def run():
    lock = verify()
    reuse = stage_reuse(lock)
    nled = len(CELLS) + len(LEAKS) + len(CUTMODES) * sum(len(cut_days(c)) for c in POISON_CELLS)
    ncut = len(CUTMODES) * (sum(len(cut_days(c)) for c in POISON_CELLS if c not in LEAKS) + len(LEAKS))
    for nm, n in (("receipt_self.json", 0), ("receipt_ledgers.json", nled), ("receipt_cut.json", ncut), ("receipt_build.json", len(CELLS)),
                  ("receipt_cutacct.json", 3 * len(CELLS)), ("receipt_align.json", len(CELLS))):
        r = json.load(open(HERE / nm))
        rows = list(r["행"].values()) if isinstance(r["행"], dict) else r["행"]
        if r["잠금"]["mpos20.py"] != reuse["단계 사본 지문"] or any(r["잠금"][f] != lock[f] for f in ("ex20.py", "parts20.py", "self20.py")) \
                or (n and len(rows) != n) or not rows \
                or any(x["판정"] != "PASS" for x in rows):
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
    mech = {"지지": "미검증", "뜻": "청산 부품 칸은 무작위 대조 없음 → 기전은 미검증 · 판정은 ①~⑥(⑤ 이웃 · ② 앞 · 뒤 반)로만 · 기전 진단은 '기전 진단(보고)'"}
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연_거래일"] >= 30.702, "⑥깊이": R[c]["최악달"] >= b["최악달"],
               "⑤": all(acct(n) for n in NEI[c])} for c in CAND}
    ok = [c for c in CAND if all(why[c].values())]
    led = {c: json.load(open(WORK / f"led_{c}.json")) for c in CELLS}
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    info = {c: {"줄": len(led[c]), "평균 손익 %(줄 · 왕복 0.25% 뒤)": round(sum(r[3] for r in led[c]) / len(led[c]), 3)} for c in CELLS}
    sh = {c: M.shares(WORK / f"base_{c}.csv") for c in CELLS}
    costs = {c: float(list(M.csv.DictReader(open(WORK / f"base_{c}.csv")))[-1]["비용누계"]) for c in CELLS}     # 대리 검토 4
    out = {"cells": R, "기준선": "IMM(= REPRO_G)", "기전": mech, "잣대": why, "자격": ok, "순위": rank,
           "판정": "PASS_DIAGNOSTIC(진단 전용 · 후보 아님)" if rank else "NO_IMPROVEMENT",
           "범위": "진단 전용: 일봉 종가 대리 구조 · 상속된 후보 줄 미래 존재 조건(lab.py:317) · 폐지 종목 없음",
           "앞 기간 고르기(보고)": front_pick(R),
           "기전 진단(보고)": mech_report(led), "단계 재사용 근거": reuse,
           "청산 사유 · 자리일(보고 · 엔진 앞/뒤 반 합)": {c: {"더한 조건만으로 팜": sum(rl[c]["감사"][k]["청산 사유"]["더한 조건만으로 팜"] for k in ("앞", "뒤")),
                                                     "원판 조건(nrl.broken)으로 팜": sum(rl[c]["감사"][k]["청산 사유"]["원판 조건(nrl.broken)으로 팜"] for k in ("앞", "뒤")),
                                                     "자리일": sum(rl[c]["감사"][k]["자리일(들고 × 자리)"] for k in ("앞", "뒤"))} for c in CELLS},
           "줄 끝 사라짐(보고 · 상속 한계)": {c: sum(rl[c]["감사"][k]["줄 끝 사라짐(보고 · 상속 한계)"] for k in ("앞", "뒤")) for c in CELLS},
           "장부(보고)": info, "바탕 평균 몫(보고)": sh, "바탕 비용 누계(보고 · 빌드 바탕 전체 구간 마지막 행 · 원)": costs, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in CELLS:
        print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False), info[c], sh[c])
    print("기전", mech, "자격", ok, "순위", rank)


if __name__ == "__main__":
    {"self": selftest, "ledgers": ledgers, "cut": cut, "build": build, "cutacct": cutacct, "align": align, "run": run}[sys.argv[1]]()
