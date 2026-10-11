"""XROOM-0061 — 1일봉 몫을 덜어 새 봇(해외 · 금 · 달러 · 채권 ETF 추세 바구니) 자리 만들기(사용자 2026-10-11 '가' 선택:
  "1일봉 몫(지금 0.5)을 조금 덜어 새 봇 자리를 만드는 판을 연구").
출발: MIX-0054 최종(바탕 d0.5_b0.3_no15m + 덧붙임 L0.4_S0.4). XASSET-0060(#245 인정)은 남는 돈이 적어(실제 몫 4.9 ~ 9.2%) 연 +0.58%p까지였음.
새 판: 바탕을 MIX-0054에서 이미 만든 d0.3_b0.3_no15m(1일봉 0.3 · 해시 잠금)으로 바꾸고 같은 덧붙임 + 새 봇(XASSET-0060 규칙 그대로 · xasset.account_x).
python3 research/xroom.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "XROOM-0061")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import xasset as X  # noqa: E402  (D.account = xasset.account_x)

BOX = ROOT / "research-exchange/claude-to-gpt/XROOM-0061"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
BASES = {"d0.5": (0.5, 0.3), "d0.3": (0.3, 0.3)}
FINAL = X.FINAL
N_MON = [6, 10]
W = [0.2, 0.3, 0.4]
FIRST_FULL, LAST_FULL = X.FIRST_FULL, X.LAST_FULL
DAY_LIM, MONTH_LIM, NB_CAP = -0.15, -0.15, 100
ANN_GAIN, MONTH_SLACK, LOSS_SLACK, CTRL_GAIN = 0.01, 0.01, 2, 0.01
CODE_FILES = ["research/xroom.py", "research/xasset.py", "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py"]
_CUR = [None]


def check_root():
    roots = {"xroom": ROOT.resolve(), "xasset": X.ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve(), "mix54_run": Path(M.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def use_base(b):
    """바탕 장부를 바꿈(바뀌면 자료를 다시 읽음 · 국면 재료는 ETF · 시장 자료라 같음)."""
    if _CUR[0] != b:
        D.BASE_CSV = M.BASES / f"{M.name(BASES[b])}.csv"
        D.DATA, D.FEAT = None, None
        _CUR[0] = b


def run_cfg(c):
    use_base(c["base"])
    cfg = dict(FINAL, **({"sleeve": c["sleeve"]} if c.get("sleeve") else {}))
    return X.account_x(cfg)


def cname(c):
    return c["base"] + ("_" + X.cname(c["sleeve"]) if c.get("sleeve") else "_새봇없음")


def grid():
    out = [("기준(지금 판 d0.5)", {"base": "d0.5"}), ("대조(1일봉 0.3 · 새 봇 없음)", {"base": "d0.3"})]
    for u in ("U4", "U3"):
        for n in N_MON:
            for w in W:
                c = {"base": "d0.3", "sleeve": {"u": u, "n": n, "w": w}}
                out.append((cname(c), c))
    return out


def eligible(x, base, ctrl):
    """채택: 잣대 안 · 지금 판보다 연 +1%p · 가장 나쁜 달 −1%p 안 · 손실 달 +2 안 · 그리고 대조(1일봉 0.3만)보다 연 +1%p(새 봇 몫이 있어야 함)."""
    return (x["within"] and x["annual_raw"] >= base["annual_raw"] + ANN_GAIN and x["worst_full_month_raw"] >= base["worst_full_month_raw"] - MONTH_SLACK
            and x["loss_months"] <= base["loss_months"] + LOSS_SLACK and x["annual_raw"] >= ctrl["annual_raw"] + CTRL_GAIN)


def neighbors(sl):
    out = [("n", sl["n"] - 2), ("n", sl["n"] + 2)]
    i = W.index(sl["w"])
    out += [("w", W[j]) for j in (i - 1, i + 1) if 0 <= j < len(W)]
    out.append(("u", "U3" if sl["u"] == "U4" else "U4"))
    return out


def lock_body():
    root = check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {"root": str(root)}
    body.update({f: sha(root / f) for f in CODE_FILES})
    body.update({k: sha(v) for k, v in X.loader_files().items()})
    for b, g in BASES.items():
        body["base_ledger:" + M.name(g) + ".csv"] = sha(M.BASES / f"{M.name(g)}.csv")
    body["snapshot:" + Path(D.SNAP).name] = sha(D.SNAP)
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


def evaluate(c, label):
    key = json.dumps(c, sort_keys=True, ensure_ascii=False)
    log({"status": "STARTED", "key": key, "label": label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        r = X.score(*run_cfg(c))
    except Exception as e:
        log({"status": "FAILED", "key": key, "error": repr(e)})
        raise
    log({"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "loss_months": r["loss_months"],
         "worst_day_pct": r["worst_day_pct"], "worst_full_month_pct": r["worst_full_month_pct"]})
    return r


def run():
    verify_inputs()
    rows = []
    for name, c in grid():
        r = evaluate(c, "고정")
        rows.append({"name": name, "cfg": c, **{k: r[k] for k in X.KEEP}})
    base, ctrl = rows[0], rows[1]
    ok = sorted([x for x in rows[2:] if eligible(x, base, ctrl)], key=lambda x: (-x["annual_raw"], x["name"]))
    checked, final, used = [], None, 0
    for x in ok:
        nbs = neighbors(x["cfg"]["sleeve"])
        if used + len(nbs) > NB_CAP:
            break
        res, good = {}, True
        for a, v in nbs:
            nr = evaluate({"base": "d0.3", "sleeve": dict(x["cfg"]["sleeve"], **{a: v})}, "이웃")
            used += 1
            keep = nr["within"] and (nr["annual_raw"] - base["annual_raw"]) * 2 >= (x["annual_raw"] - base["annual_raw"]) \
                and nr["worst_full_month_raw"] >= base["worst_full_month_raw"] - MONTH_SLACK and nr["loss_months"] <= base["loss_months"] + LOSS_SLACK
            res[f"{a}={v}"] = {"annual_pct": nr["annual_pct"], "loss_months": nr["loss_months"], "worst_day_pct": nr["worst_day_pct"],
                               "worst_full_month_pct": nr["worst_full_month_pct"], "keep": keep}
            good = good and keep
        checked.append({"name": x["name"], "neighbors": res, "robust": good})
        if good:
            final = x
            break
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": "XROOM_CANDIDATE" if final else "NO_IMPROVEMENT", "final": final, "base": base, "control": ctrl, "checked": checked,
                      "eligible_count": len(ok), "rows_count": len(rows), "neighbor_evals": used,
                      "rules": {"day": DAY_LIM, "month": MONTH_LIM, "ann_gain": ANN_GAIN, "month_slack": MONTH_SLACK, "loss_slack": LOSS_SLACK,
                                "ctrl_gain": CTRL_GAIN, "neighbor_cap": NB_CAP},
                      "period": "2017-02-01 ~ 2026-09-15 · 공식 달은 완료 114달(2017-03 ~ 2026-08)"}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import xroom as R;"
            "n,s=R.run_cfg(json.loads(os.environ['XR_CFG']));print(json.dumps([n,s]))")
    res = []
    for c in ({"base": "d0.3", "sleeve": {"u": "U4", "n": 6, "w": 0.4}}, {"base": "d0.3", "sleeve": {"u": "U3", "n": 10, "w": 0.2}}, {"base": "d0.3"}):
        env = dict(os.environ, XR_CFG=json.dumps(c), REG_CUT="")
        fn, fs = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["REG_CUT"] = ct
            pn, ps = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in pn if d < ct]
            bad = [d for d in ds if abs(pn[d] - fn[d]) > 1e-12 or ps.get(d) != fs.get(d)]
            res.append({"cfg": c, "cut": ct, "days": len(ds), "diff_days": len(bad)})
    print(json.dumps({"pass": all(r["diff_days"] == 0 for r in res), "runs": res}, ensure_ascii=False))


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1))
    print(LOCK.read_text())


if __name__ == "__main__":
    {"run": run, "cut": cut, "lock": write_lock}[sys.argv[1]]()
