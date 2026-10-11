"""GUARD-ROB-0070 — 그달 지킴이로 '설정 운'까지 견디기(사용자 2026-10-11 "백테스트하고 약점을 보완방법 연구해줘 지피티와" · SAFE-LEV-0069 #263 다음):
SAFE-LEV-0069에서 레버리지를 0.25로 줄여도 국면 숫자 n 32 둘이 2026-03(시장 −19.86%)에 완료 달 −15%를 넘었음.
MONTH-POS-0055 판정 밖 관찰: 그달 계좌 누적 ≤ −k%면 그달 남은 날 덧붙임 0(A0) 또는 현금(A2) → n 24 · persist 3에서 가장 나쁜 달 −14.0 → −7.1 ~ −9.3%.
질문: 지킴이를 켜면 국면 숫자 15개(n {17 · 20 · 24 · 28 · 32} × persist {2 · 3 · 4}) 모두가 하루 · 완료 달 −15% 안에 드는가 · 연수익은 얼마나 잃는가.
계좌 셈은 month_guard.account_guard 그대로(코드 변경 없음 · 레버리지 0.4 · 횡보 인버스 0.4 · 바탕 MIX-0054 장부).
python3 research/guard_robust.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "GUARD-ROB-0070")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import month_guard as G  # noqa: E402

D, M = G.D, G.M
BOX = ROOT / "research-exchange/claude-to-gpt/GUARD-ROB-0070"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
OUT = BOX / "evidence"
FINAL = G.FINAL
N_SET, P_SET = [17, 20, 24, 28, 32], [2, 3, 4]
GUARDS = {"none": {}, "A0_k4": {"k": 0.04, "g": None, "fb": 1.0}, "A0_k6": {"k": 0.06, "g": None, "fb": 1.0}, "A2_k4": {"k": 0.04, "g": None, "fb": 0.0}}
UNIQUE, ATTEMPT_CAP = 60, 66
ANN_GAP = 0.02                                                   # 연수익 허용 손해 2%p(지금 숫자 · 15개 평균 각각)
KEEP = ("annual_raw", "annual_pct", "worst_day_pct", "worst_full_month_pct", "mdd_report_pct", "loss_months", "within", "guard_days", "min_cash_slack")
CODE_FILES = ["research/guard_robust.py", "research/month_guard.py", "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py"]


def grid():
    return [(f"{gn}_n{n}_p{p}", gn, n, p) for gn in GUARDS for n in N_SET for p in P_SET]


def key_of(gn, n, p):
    return json.dumps({"cfg": dict(FINAL, n=n, persist=p), "guard": GUARDS[gn]}, sort_keys=True, ensure_ascii=False)


def calc(gn, n, p):
    r = G.score(*G.account_guard(dict(FINAL, n=n, persist=p), GUARDS[gn]))
    return {k: r[k] for k in KEEP}


def pick(rows):
    """지킴이마다: ① 15개 모두 잣대 안 ② 지금 숫자(n 24 · p 3) 연 ≥ 지킴이 없는 같은 숫자 − 2%p ③ 15개 평균 연 ≥ 지킴이 없는 15개 평균 − 2%p.
    모두 지킨 지킴이 가운데 15개 평균 연이 가장 높은 것(같으면 이름 순). 없으면 None."""
    by = {gn: [r for r in rows if r["guard_name"] == gn] for gn in GUARDS}
    mean = lambda rs: sum(r["annual_raw"] for r in rs) / len(rs)
    now = lambda rs: next(r for r in rs if r["n"] == 24 and r["persist"] == 3)
    base = by["none"]
    out = {}
    for gn, rs in by.items():
        if gn == "none":
            continue
        full = len(rs) == len(N_SET) * len(P_SET)
        out[gn] = {"within_count": sum(1 for r in rs if r["within"]), "all_within": full and all(r["within"] for r in rs),
                   "now_ok": full and now(rs)["annual_raw"] >= now(base)["annual_raw"] - ANN_GAP,
                   "mean_ok": full and mean(rs) >= mean(base) - ANN_GAP, "mean_annual": mean(rs) if rs else None}
        out[gn]["pass"] = out[gn]["all_within"] and out[gn]["now_ok"] and out[gn]["mean_ok"]
    ok = sorted([g for g in out if out[g]["pass"]], key=lambda g: (-out[g]["mean_annual"], g))
    return (ok[0] if ok else None), out


def lock_body():
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {"root": str(ROOT)}
    body.update({f: sha(ROOT / f) for f in CODE_FILES})
    body.update({f"etf-data/{c}.json": sha(Path(D.ROOT) / f"etf-data/{c}.json") for c in D.ETF})
    body.update({f: sha(Path(D.ROOT) / f) for f in ("market-data/investor_KSP.json", "market-data/index_KOSPI.json")})
    body["base_ledger:" + M.name(G.BASE) + ".csv"] = sha(M.BASES / f"{M.name(G.BASE)}.csv")
    body["snapshot:" + Path(D.SNAP).name] = sha(D.SNAP)
    return body


def verify_inputs(path=None):
    if len({ROOT.resolve(), Path(D.ROOT).resolve(), Path(M.ROOT).resolve(), Path(G.ROOT).resolve()}) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤)")
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
    st, fl, done = 0, 0, {}
    if EVALS.exists():
        for line in EVALS.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            st += r["status"] == "STARTED"
            fl += r["status"] == "FAILED"
            if r["status"] == "DONE":
                done[r["key"]] = r
    return st, fl, done


def evaluate(name, gn, n, p, done):
    key = key_of(gn, n, p)
    if key in done:                                              # 끝난 설정은 다시 셈하지 않음
        r = done[key]["result"]
    else:
        log({"status": "STARTED", "key": key, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        try:
            r = calc(gn, n, p)
        except Exception as e:
            log({"status": "FAILED", "key": key, "error": repr(e)}); raise
        log({"status": "DONE", "key": key, "result": r})
    return {"name": name, "guard_name": gn, "n": n, "persist": p, **r}


def run():
    verify_inputs()
    g = grid()
    assert len(g) == UNIQUE
    st, fl, done = prior()
    todo = [x for x in g if key_of(*x[1:]) not in done]
    if st + len(todo) > ATTEMPT_CAP:                             # 첫 STARTED 전에 멈춤
        sys.exit(f"평가 상한 넘음(멈춤): 앞선 STARTED {st} + 남은 {len(todo)} > {ATTEMPT_CAP}")
    D.BASE_CSV = M.BASES / f"{M.name(G.BASE)}.csv"
    D.DATA, D.FEAT = None, None
    rows = [evaluate(*x, done) for x in g]
    best, per = pick(rows)
    st2, fl2, done2 = prior()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": f"GUARD_ROBUST_{best}" if best else "NO_IMPROVEMENT", "per_guard": per,
                      "attempts": {"started": st2, "done_unique": len(done2), "failed": fl2, "unique_settings": UNIQUE, "cap": ATTEMPT_CAP}},
                     ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import guard_robust as R;D=R.D;"
            "D.BASE_CSV=R.M.BASES/f'{R.M.name(R.G.BASE)}.csv';D.DATA,D.FEAT=None,None;"
            "a=json.loads(os.environ['GR_ARG']);n,_=R.G.account_guard(dict(R.FINAL,n=a[1],persist=a[2]),R.GUARDS[a[0]]);print(json.dumps(n))")
    res = []
    for arg in (["A0_k4", 32, 3], ["A2_k4", 17, 2], ["A0_k6", 20, 4]):
        env = dict(os.environ, GR_ARG=json.dumps(arg), REG_CUT="")
        full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for c in cuts:
            env["REG_CUT"] = c
            part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in part if d < c]
            res.append({"arg": arg, "cut": c, "days": len(ds), "diff": sum(1 for d in ds if abs(part[d] - full[d]) > 1e-12)})
    print(json.dumps({"pass": all(r["diff"] == 0 for r in res), "runs": res}, ensure_ascii=False))


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1)); print(LOCK.read_text())


if __name__ == "__main__":
    {"run": run, "cut": cut, "lock": write_lock}[sys.argv[1]]()
