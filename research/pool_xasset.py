"""POOL-XASSET-0062 — 새 봇 후보 목록(사용자 2026-10-11 "최종 자본 분배는 봇개발이 더 이상 안될때하자"):
XASSET-0060 추세 바구니를 '혼자 계좌'로 재고 지금 판(MIX-0054)과의 상관을 봄. 분배를 고르지 않음 · 후보 목록에 넣을지만 판정.
규칙: xasset.trend_pick 그대로(전 거래일까지 달 끝 종가 > N달 평균) · 달 첫 거래일 종가에 같은 몫 · 못 고른 몫은 현금(수익 0) · 비용 각 0.05%.
python3 research/pool_xasset.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "POOL-XASSET-0062")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import regime_dev as D  # noqa: E402
import xasset as X  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/POOL-XASSET-0062"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
MIX54_ROWS = ROOT / "research-exchange/claude-to-gpt/VOL-SIZE-0057/evidence/all_rows.json"      # 지금 판 달 값(기준 칸 · VOL-SIZE-0057 #240 인정)
BOND = "153130"                                                  # KODEX 단기채권(비교만)
COST = D.COST_ETF
LO, HI = D.LO, D.HI
FIRST_FULL, LAST_FULL = X.FIRST_FULL, X.LAST_FULL
DAY_LIM, MONTH_LIM, BOND_GAIN, CORR_MAX = -0.15, -0.15, 0.03, 0.5
CODE_FILES = ["research/pool_xasset.py", "research/xasset.py", "research/regime_dev.py"]
PX = None


def check_root():
    roots = {"pool_xasset": ROOT.resolve(), "xasset": X.ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def files():
    root = Path(D.ROOT)
    return {f"etf-data/{c}.json": root / f"etf-data/{c}.json" for c in sorted(set(X.SLEEVE_ETF) | {"069500", BOND})} | \
           {"mix54_rows:VOL-SIZE-0057/all_rows.json": MIX54_ROWS}


def prices():
    global PX
    if PX is None:
        PX = {c: {d: float(x) for d, x in json.load(open(Path(D.ROOT) / f"etf-data/{c}.json"))["closes"] if x and D.cut_ok(d)}
              for c in sorted(set(X.SLEEVE_ETF) | {"069500", BOND})}
    return PX


def account(cfg):
    """혼자 계좌. cfg = {"u", "n"} · 또는 {"hold": 코드}(그 ETF만 계속 들기 · 비교용)."""
    px = prices()
    days = [d for d in sorted(px["069500"]) if LO <= d <= HI]
    last = {}

    def p_at(c, d):
        if d in px[c]:
            last[c] = px[c][d]
        return last.get(c)
    cash, pos, navs = 1.0, {}, {}
    codes = X.UNIVERSE[cfg["u"]] if "u" in cfg else (cfg["hold"],)
    for c in codes:
        p_at(c, days[0])
    navs[days[0]] = 1.0
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        for c in codes:
            prev = last.get(c)
            now = p_at(c, d)
            if c in pos and prev and now:
                pos[c] *= now / prev
        A = cash + sum(pos.values())
        if d[:6] != p[:6] or j == 1:
            if "u" in cfg:
                pick = [c for c in X.trend_pick(px, p, cfg["n"], codes) if last.get(c)]
            else:
                pick = [c for c in codes if last.get(c)]
            want = {c: A / len(pick) for c in pick} if pick else {}
            cost = COST * sum(abs(want.get(c, 0.0) - pos.get(c, 0.0)) for c in set(want) | set(pos))
            A -= cost
            pos = {c: A / len(pick) for c in pick} if pick else {}
            cash = A - sum(pos.values())
        navs[d] = cash + sum(pos.values())
    return navs


def score(navs):
    ds = sorted(navs)
    rets = [navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))]
    mo = {}
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * (navs[ds[j]] / navs[ds[j - 1]])
    full = {m: v - 1 for m, v in mo.items() if FIRST_FULL <= m <= LAST_FULL}
    ann = navs[ds[-1]] ** (250 / len(ds)) - 1
    pk, mdd = 0, 0
    for d in ds:
        pk = max(pk, navs[d])
        mdd = min(mdd, navs[d] / pk - 1)
    mix = json.load(open(MIX54_ROWS))[0]["month_pct"]
    ms = sorted(set(full) & set(mix))
    a = [full[m] for m in ms]
    b = [mix[m] / 100 for m in ms]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    corr = cov / ((sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5)
    neg = sorted(m for m, v in full.items() if v < 0)
    mixneg = [m for m in ms if mix[m] < 0]
    return {"annual_raw": ann, "annual_pct": round(ann * 100, 3), "worst_day_pct": round(min(rets) * 100, 3), "worst_day_raw": min(rets),
            "worst_full_month_raw": min(full.values()), "worst_full_month_pct": round(min(full.values()) * 100, 3),
            "mdd_report_pct": round(mdd * 100, 2), "loss_months": len(neg), "months": len(full), "corr_mix54": round(corr, 3), "corr_raw": corr,
            "mean_in_mix54_loss_months_pct": round(sum(full[m] for m in mixneg) / len(mixneg) * 100, 3),
            "pos_in_mix54_loss_months": sum(1 for m in mixneg if full[m] > 0), "mix54_loss_months": len(mixneg),
            "month_pct": {m: round(v * 100, 3) for m, v in full.items()}}


def grid():
    out = [("비교: 단기채 153130 계속 들기", {"hold": BOND})]
    for u in ("U4", "U3"):
        for n in (6, 10):
            out.append((f"{u}_n{n}", {"u": u, "n": n}))
    return out


def eligible(x, bond):
    """후보 목록 조건(분배 아님): 하루 · 완료 달 ≥ −15% · 연 ≥ 단기채 + 3%p · 지금 판과 달 상관 ≤ 0.5."""
    return (x["worst_day_raw"] >= DAY_LIM and x["worst_full_month_raw"] >= MONTH_LIM and x["annual_raw"] >= bond["annual_raw"] + BOND_GAIN
            and x["corr_raw"] <= CORR_MAX)


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
            r = score(account(cfg))
        except Exception as e:
            log({"status": "FAILED", "key": key, "error": repr(e)})
            raise
        log({"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "corr_mix54": r["corr_mix54"]})
        rows.append({"name": name, "cfg": cfg, **r})
    bond = rows[0]
    ok = [x for x in rows[1:] if eligible(x, bond)]
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": "POOL_CANDIDATE" if len(ok) >= 3 else "NOT_POOLED", "eligible": [x["name"] for x in ok],
                      "rows": [{k: v for k, v in x.items() if k != "month_pct"} for x in rows],
                      "rules": {"day": DAY_LIM, "month": MONTH_LIM, "bond_gain": BOND_GAIN, "corr_max": CORR_MAX, "need_cells": 3}}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import pool_xasset as P;"
            "print(json.dumps(P.account(json.loads(os.environ['PX_CFG']))))")
    res = []
    for c in ({"u": "U4", "n": 6}, {"u": "U3", "n": 10}):
        env = dict(os.environ, PX_CFG=json.dumps(c), REG_CUT="")
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
