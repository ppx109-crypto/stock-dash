"""POOL-GLOBAL-0064 — 새 봇 후보 목록(사용자 2026-10-11 "최종 자본 분배는 봇개발이 더 이상 안될때하자"): 해외 지수 듀얼 모멘텀을 혼자 계좌로 잼.
규칙: 달 첫 거래일 종가에, 전 거래일(p)까지 달 끝 종가로 본 최근 L달 수익 상위 K개(수익 > 0)를 같은 몫으로 삼 ·
      하나도 없으면 148070 국고채10년을 삼(현금 대신) · 비용 각 0.05%. 분배를 고르지 않음(POOL-XASSET-0062와 같은 조건).
python3 research/pool_global.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "POOL-GLOBAL-0064")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import regime_dev as D  # noqa: E402
import pool_xasset as P  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/POOL-GLOBAL-0064"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
GLOBAL = ("133690", "143850", "195930", "241180", "192090")      # 나스닥100 · S&P500선물 · 유로스탁스50 · 니케이 · 중국 CSI300
SAFE = "148070"                                                  # 국고채10년(모두 음수일 때)
POOL1_ROWS = ROOT / "research-exchange/claude-to-gpt/POOL-XASSET-0062/evidence/all_rows.json"     # POOL-1 달 값(보고용 상관)
K_TOP = [1, 2]
L_MON = [6, 12]
CODE_FILES = ["research/pool_global.py", "research/pool_xasset.py", "research/xasset.py", "research/regime_dev.py"]
PX = None


def check_root():
    roots = {"pool_global": ROOT.resolve(), "pool_xasset": P.ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def codes_all():
    return sorted(set(GLOBAL) | {SAFE, "069500", P.BOND})


def files():
    root = Path(D.ROOT)
    return {f"etf-data/{c}.json": root / f"etf-data/{c}.json" for c in codes_all()} | \
           {"mix54_rows:VOL-SIZE-0057/all_rows.json": P.MIX54_ROWS, "pool1_rows:POOL-XASSET-0062/all_rows.json": POOL1_ROWS}


def prices():
    global PX
    if PX is None:
        PX = {c: {d: float(x) for d, x in json.load(open(Path(D.ROOT) / f"etf-data/{c}.json"))["closes"] if x and D.cut_ok(d)} for c in codes_all()}
    return PX


def mom_pick(px, p, k, look):
    """p까지 값만: 달 끝 종가(p가 든 달은 p 종가) 기준 최근 look달 수익 상위 k개(수익 > 0 · 자료 부족 뺌) · 없으면 [SAFE]."""
    score = {}
    for c in GLOBAL:
        ends = {}
        for d in sorted(x for x in px[c] if x <= p):
            ends[d[:6]] = px[c][d]
        vals = [ends[m] for m in sorted(ends)]
        if len(vals) >= look + 1:
            r = vals[-1] / vals[-1 - look] - 1
            if r > 0:
                score[c] = r
    pick = [c for c, _ in sorted(score.items(), key=lambda x: (-x[1], x[0]))[:k]]
    return pick or [SAFE]


def account(cfg):
    px = prices()
    days = [d for d in sorted(px["069500"]) if P.LO <= d <= P.HI]
    last = {}
    codes = tuple(GLOBAL) + (SAFE,) if "k" in cfg else (cfg["hold"],)

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
            pick = mom_pick(px, p, cfg["k"], cfg["l"]) if "k" in cfg else list(codes)
            pick = [c for c in pick if last.get(c)]
            want = {c: A / len(pick) for c in pick} if pick else {}
            cost = P.COST * sum(abs(want.get(c, 0.0) - pos.get(c, 0.0)) for c in set(want) | set(pos))
            A -= cost
            pos = {c: A / len(pick) for c in pick} if pick else {}
            cash = A - sum(pos.values())
        navs[d] = cash + sum(pos.values())
    return navs


def corr_pool1(month_pct):
    """보고용: POOL-1(U3 · N6) 달 수익과의 상관(판정 밖)."""
    rows = json.load(open(POOL1_ROWS))
    ref = next(r for r in rows if r["name"] == "U3_n6")["month_pct"]
    ms = sorted(set(ref) & set(month_pct))
    a, b = [month_pct[m] for m in ms], [ref[m] for m in ms]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return round(sum((x - ma) * (y - mb) for x, y in zip(a, b)) / ((sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5), 3)


def grid():
    out = [("비교: 단기채 153130 계속 들기", {"hold": P.BOND}), ("참고: 나스닥100 133690 계속 들기", {"hold": "133690"})]
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
            r["corr_pool1_report"] = corr_pool1(r["month_pct"])
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
    code = ("import os,sys,json;sys.path.insert(0,'research');import pool_global as G;"
            "print(json.dumps(G.account(json.loads(os.environ['PG_CFG']))))")
    res = []
    for c in ({"k": 1, "l": 6}, {"k": 2, "l": 12}):
        env = dict(os.environ, PG_CFG=json.dumps(c), REG_CUT="")
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
