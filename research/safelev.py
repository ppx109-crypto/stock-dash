"""SAFE-LEV-0069 — '설정 운'까지 견디는 레버리지 몫(사용자 2026-10-11 "백테스트하고 약점을 보완방법 연구해줘 지피티와" · ENS-0068 #261 다음):
국면 숫자 15개(n {17 · 20 · 24 · 28 · 32} × persist {2 · 3 · 4}) 모두가 계좌 전체 하루 · 완료 달 −15% 안에 드는 가장 큰 up_lev를 고름.
몫 축은 손실 한도로만 정함(REGIME-SW-0049 사용자 정의). 횡보 인버스 0.4 · 그 밖 규칙은 지금 판 그대로.
python3 research/safelev.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "SAFE-LEV-0069")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import ens as E  # noqa: E402  (TAILBOX-0067 셈 · 지금 판 FINAL · 구성원 묶음)

T, D = E.T, E.D
BOX = ROOT / "research-exchange/claude-to-gpt/SAFE-LEV-0069"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
FINAL = E.FINAL
UP_LEV = [0.25, 0.30, 0.35, 0.40]
UNIQUE = 60                                                     # 고유 설정(고정 격자)
ATTEMPT_CAP = 66                                                # 총 STARTED 상한(실패 뒤 다시 돌리기 6번까지 · GPT #262)
OUT = BOX / "evidence"
CODE_FILES = ["research/safelev.py"] + E.CODE_FILES


def grid():
    return [(f"L{lv}_n{n}_p{p}", lv, n, p, dict(FINAL, up_lev=lv, n=n, persist=p)) for lv in UP_LEV for n in E.N_SET for p in E.P_SET]


def pick(rows):
    """몫마다 15개 모두 잣대 안(반올림 전 하루 · 완료 달 ≥ −15%)이면 '견딤'. 견디는 가장 큰 몫을 고름. 없으면 None."""
    out = {}
    for lv in UP_LEV:
        rs = [r for r in rows if r["up_lev"] == lv]
        out[lv] = {"count": len(rs), "within": sum(1 for r in rs if r["full"]["within"]),
                   "all_within": len(rs) == len(E.N_SET) * len(E.P_SET) and all(r["full"]["within"] for r in rs)}
    ok = [lv for lv in UP_LEV if out[lv]["all_within"]]
    return (max(ok) if ok else None), out


def lock_body():
    root = T.check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = E.lock_body()
    body.update({f: sha(root / f) for f in CODE_FILES})
    return body


def verify_inputs(path=None):
    want = json.loads(Path(path or LOCK).read_text())
    have = lock_body()
    bad = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
    if bad:
        sys.exit("입력 잠금이 다름(멈춤): " + json.dumps(bad, ensure_ascii=False))
    return want


def log(rec):
    BOX.mkdir(parents=True, exist_ok=True)
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); os.fsync(fh.fileno())


def prior():
    """앞서 남은 기록: STARTED 수 · FAILED 수 · DONE(결과 통째) 열쇠별."""
    st, fl, done = 0, 0, {}
    if EVALS.exists():
        for line in EVALS.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            st += r["status"] == "STARTED"
            fl += r["status"] == "FAILED"
            if r["status"] == "DONE":
                done[r["key"]] = r
    return st, fl, done


def evaluate(name, lv, n, p, cfg, done):
    key = json.dumps(cfg, sort_keys=True, ensure_ascii=False)
    if key in done:                                              # 끝난 설정은 다시 셈하지 않음(STARTED 안 늘림)
        r = {"full": done[key]["full"], "dev": done[key]["dev"]}
    else:
        log({"status": "STARTED", "key": key, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        try:
            r = E.both(cfg)
        except Exception as e:
            log({"status": "FAILED", "key": key, "error": repr(e)}); raise
        log({"status": "DONE", "key": key, "full": r["full"], "dev": r["dev"]})
    return {"name": name, "up_lev": lv, "n": n, "persist": p, "cfg": cfg, **r}


def run():
    verify_inputs()
    g = grid()
    assert len(g) == UNIQUE
    st, fl, done = prior()
    todo = [x for x in g if json.dumps(x[4], sort_keys=True, ensure_ascii=False) not in done]
    if st + len(todo) > ATTEMPT_CAP:                             # 첫 STARTED 전에 멈춤(fail-closed)
        sys.exit(f"평가 상한 넘음(멈춤): 앞선 STARTED {st} + 남은 {len(todo)} > {ATTEMPT_CAP}")
    D.DATA, D.FEAT = None, None
    rows = [evaluate(*x, done) for x in g]
    best, per = pick(rows)
    st2, fl2, done2 = prior()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    now = {str(lv): next(r["full"] for r in rows if r["up_lev"] == lv and r["n"] == 24 and r["persist"] == 3) for lv in UP_LEV}
    print(json.dumps({"verdict": f"SAFE_SIZE_L{best}" if best is not None else "NONE_IN_GRID", "per_lev": {str(k): v for k, v in per.items()},
                      "attempts": {"started": st2, "done_unique": len(done2), "failed": fl2, "unique_settings": UNIQUE, "cap": ATTEMPT_CAP},
                      "n24_p3": {k: {"annual_pct": v["annual_pct"], "worst_full_month_pct": v["worst_full_month_pct"], "worst_day_pct": v["worst_day_pct"]} for k, v in now.items()}},
                     ensure_ascii=False))


def cut():
    cuts = ("20120615", "20150820", "20200320", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import safelev as S;D=S.D;D.DATA,D.FEAT=None,None;"
            "c=dict(S.FINAL,**json.loads(os.environ['SL_CFG']));"
            "a=S.T.full(c) if os.environ.get('REG_CUT','')=='' or os.environ['REG_CUT']>='20170301' else {};"
            "s=S.T.standalone(c,'20100301','20260915');print(json.dumps([a,s]))")
    res = []
    for extra in ({"up_lev": 0.25, "n": 17, "persist": 2}, {"up_lev": 0.3, "n": 32, "persist": 4}, {"up_lev": 0.35, "n": 20, "persist": 3}):
        env = dict(os.environ, SL_CFG=json.dumps(extra), REG_CUT="")
        fa, fs = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["REG_CUT"] = ct
            pa, ps = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            da = [d for d in pa if d < ct]; dsx = [d for d in ps if d < ct]
            res.append({"cfg": extra, "cut": ct, "full_days": len(da), "dev_days": len(dsx),
                        "diff": sum(1 for d in da if abs(pa[d] - fa[d]) > 1e-12) + sum(1 for d in dsx if abs(ps[d] - fs[d]) > 1e-12)})
    print(json.dumps({"pass": all(r["diff"] == 0 for r in res), "runs": res}, ensure_ascii=False))


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1)); print(LOCK.read_text())


if __name__ == "__main__":
    {"run": run, "cut": cut, "lock": write_lock}[sys.argv[1]]()
