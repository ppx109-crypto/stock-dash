"""POOL-SECTOR-0063 — 새 봇 후보 목록(사용자 2026-10-11 "최종 자본 분배는 봇개발이 더 이상 안될때하자"): 국내 업종 ETF 모멘텀 순환을 혼자 계좌로 잼.
규칙: 달 첫 거래일 종가에, 전 거래일(p)까지 달 끝 종가로 본 최근 L달 수익이 높은 업종 K개(L달 수익 > 0인 것만)를 같은 몫으로 삼 · 없으면 현금(수익 0) · 비용 각 0.05%.
분배를 고르지 않음 · 후보 목록에 넣을지만 판정(POOL-XASSET-0062와 같은 조건).
python3 research/pool_sector.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "POOL-SECTOR-0063")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import regime_dev as D  # noqa: E402
import pool_xasset as P  # noqa: E402  (score · 지금 판 달 값 · 단기채 비교를 그대로 씀)

BOX = ROOT / "research-exchange/claude-to-gpt/POOL-SECTOR-0063"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
SECTORS = ("091160", "091170", "091180", "102970", "117680", "117700", "139260", "266420", "305720")
#          반도체 · 은행 · 자동차 · 증권 · 철강 · 건설 · IT · 헬스케어(2017-03 상장) · 2차전지(2018-09 상장)
K_TOP = [2, 3]
L_MON = [3, 6]
CODE_FILES = ["research/pool_sector.py", "research/pool_xasset.py", "research/xasset.py", "research/regime_dev.py"]
PX = None


def check_root():
    roots = {"pool_sector": ROOT.resolve(), "pool_xasset": P.ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def codes_all():
    return sorted(set(SECTORS) | {"069500", P.BOND})


def files():
    root = Path(D.ROOT)
    return {f"etf-data/{c}.json": root / f"etf-data/{c}.json" for c in codes_all()} | {"mix54_rows:VOL-SIZE-0057/all_rows.json": P.MIX54_ROWS}


def prices():
    global PX
    if PX is None:
        PX = {c: {d: float(x) for d, x in json.load(open(Path(D.ROOT) / f"etf-data/{c}.json"))["closes"] if x and D.cut_ok(d)} for c in codes_all()}
    return PX


def mom_pick(px, p, k, look):
    """p까지 값만: 달 끝 종가(p가 든 달은 p 종가) 기준 최근 look달 수익 상위 k개(수익 > 0 · 자료가 look+1달 안 되면 뺌)."""
    score = {}
    for c in SECTORS:
        ends = {}
        for d in sorted(x for x in px[c] if x <= p):
            ends[d[:6]] = px[c][d]
        vals = [ends[m] for m in sorted(ends)]
        if len(vals) >= look + 1:
            r = vals[-1] / vals[-1 - look] - 1
            if r > 0:
                score[c] = r
    return [c for c, _ in sorted(score.items(), key=lambda x: (-x[1], x[0]))[:k]]


def account(cfg):
    """혼자 계좌. cfg = {"k", "l"} · 또는 {"hold": 코드}."""
    px = prices()
    days = [d for d in sorted(px["069500"]) if P.LO <= d <= P.HI]
    last = {}
    codes = SECTORS if "k" in cfg else (cfg["hold"],)

    def p_at(c, d):
        if d in px[c]:
            last[c] = px[c][d]
        return last.get(c)
    for c in codes:
        p_at(c, days[0])
    cash, pos, navs = 1.0, {}, {days[0]: 1.0}
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        for c in codes:
            prev = last.get(c)
            now = p_at(c, d)
            if c in pos and prev and now:
                pos[c] *= now / prev
        A = cash + sum(pos.values())
        if d[:6] != p[:6] or j == 1:
            pick = mom_pick(px, p, cfg["k"], cfg["l"]) if "k" in cfg else [c for c in codes if last.get(c)]
            pick = [c for c in pick if last.get(c)]
            want = {c: A / len(pick) for c in pick} if pick else {}
            cost = P.COST * sum(abs(want.get(c, 0.0) - pos.get(c, 0.0)) for c in set(want) | set(pos))
            A -= cost
            pos = {c: A / len(pick) for c in pick} if pick else {}
            cash = A - sum(pos.values())
        navs[d] = cash + sum(pos.values())
    return navs


def grid():
    out = [("비교: 단기채 153130 계속 들기", {"hold": P.BOND}), ("참고: KODEX 200 069500 계속 들기", {"hold": "069500"})]
    for k in K_TOP:
        for look in L_MON:
            out.append((f"K{k}_L{look}", {"k": k, "l": look}))
    return out


def lock_body():
    root = check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {"root": str(root)}
    body.update({f: sha(root / f) for f in CODE_FILES})
    body.update({k: sha(v) for k, v in files().items()})
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
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def run():
    verify_inputs()
    rows = []
    for name, cfg in grid():
        key = json.dumps(cfg, sort_keys=True)
        log({"status": "STARTED", "key": key, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        try:
            r = P.score(account(cfg))
        except Exception as e:
            log({"status": "FAILED", "key": key, "error": repr(e)})
            raise
        log({"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "corr_mix54": r["corr_mix54"]})
        rows.append({"name": name, "cfg": cfg, **r})
    bond = rows[0]
    ok = [x for x in rows[2:] if P.eligible(x, bond)]
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": "POOL_CANDIDATE" if len(ok) >= 3 else "NOT_POOLED", "eligible": [x["name"] for x in ok],
                      "rows": [{k: v for k, v in x.items() if k != "month_pct"} for x in rows],
                      "rules": {"day": P.DAY_LIM, "month": P.MONTH_LIM, "bond_gain": P.BOND_GAIN, "corr_max": P.CORR_MAX, "need_cells": 3}}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import pool_sector as S;"
            "print(json.dumps(S.account(json.loads(os.environ['PS_CFG']))))")
    res = []
    for c in ({"k": 2, "l": 3}, {"k": 3, "l": 6}):
        env = dict(os.environ, PS_CFG=json.dumps(c), REG_CUT="")
        fn = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["REG_CUT"] = ct
            pn = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in pn if d < ct]
            res.append({"cfg": c, "cut": ct, "days": len(ds), "diff_days": sum(1 for d in ds if abs(pn[d] - fn[d]) > 1e-12)})
    print(json.dumps({"pass": all(r["diff_days"] == 0 for r in res), "runs": res}, ensure_ascii=False))


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1))
    print(LOCK.read_text())


if __name__ == "__main__":
    {"run": run, "cut": cut, "lock": write_lock}[sys.argv[1]]()
