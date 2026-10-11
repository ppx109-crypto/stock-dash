"""ASYM-EXIT-0056 — 덧붙임 비대칭 버팀(사용자 2026-10-11 "비대칭 버팀 연구 진행해줘").
출발: MIX-0054 최종(켜 둔 판 · 바탕 d0.5_b0.3_no15m + 덧붙임 n24 · persist 3 · r10m5 · 레버리지 0.4 · 횡보 인버스 0.4).
진단(사전등록 전에 봄 · 공개): 완료 114달 중 손실 40달에서 그달 가장 크게 깎은 갈래 = 덧붙임 18달 · 1일봉 14 · 엔진 5 · 바구니 3.
  깊은 손실 달(2026-03 −14.0% · 덧붙임 −10.5%p 등)은 덧붙임이 가장 큼 → 시장이 꺾일 때 사흘 버팀이 늦게 빠져나오는 것이 원인으로 보임.
새 규칙(국면 버팀만 바꿈 · 몫 · 종목 · 때 · 돈은 그대로):
  지금 국면이 '상승'(레버리지)이면: 그날 판정이 '상승이 아닌' 날이 p_up일 이어지면 그날 판정으로 바꿈(빠져나오기).
  지금 국면이 '횡보'(인버스)면: 그날 판정이 '횡보가 아닌' 날이 p_side일 이어지면 그날 판정으로 바꿈.
  지금 국면이 '하락'(덧붙임 없음)이면: 지금 규칙 그대로(같은 그날 판정 3일).
  (지금 판은 '같은 그날 판정이 3일' — 10-07 횡보 · 10-08 하락처럼 섞이면 다시 셈. 새 규칙은 '아닌 날'을 셈.)
python3 research/asym_exit.py lock   → input_lock.json(성과 셈 없음)
python3 research/asym_exit.py run    → 잠금 검사 → 고정 10판 + 고르기 + 이웃(기록 evals.jsonl)
python3 research/asym_exit.py cut    → 자르기 시험"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "ASYM-EXIT-0056")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import regime_rules4 as R4  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/ASYM-EXIT-0056"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
BASE = (0.5, 0.3)
FINAL = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])
P_UP = [1, 2, 3]
P_SIDE = [1, 2, 3]
FIRST_FULL, LAST_FULL = "201703", "202608"
DAY_LIM, MONTH_LIM, NB_CAP = -0.15, -0.15, 100
ANN_SLACK, LOSS_CUT, MONTH_GAIN, ANN_GAIN = 0.005, 3, 0.02, 0.02
LOCK_FILES = ["research/asym_exit.py", "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py",
              "etf-data/069500.json", "etf-data/114800.json", "etf-data/252670.json", "etf-data/122630.json",
              "market-data/investor_KSP.json", "market-data/index_KOSPI.json"]
_ORIG_STATES = D.states


def states_asym(feat, cfg):
    """비대칭 버팀. cfg에 p_up · p_side가 없으면 지금 규칙(regime_dev.states) 그대로."""
    if "p_up" not in cfg:
        return _ORIG_STATES(feat, cfg)
    out, cur, run, last, away = {}, "횡보", 0, None, 0
    for d in sorted(feat):
        s = D.raw_state(feat[d], cfg)
        run = run + 1 if s == last else 1
        last = s
        if cur in ("상승", "횡보"):
            away = away + 1 if s != cur else 0                   # 지금 국면이 '아닌' 날이 이어진 수
            need = cfg["p_up"] if cur == "상승" else cfg["p_side"]
            if s != cur and away >= need:
                cur, away = s, 0
        else:                                                    # 하락: 지금 규칙(같은 그날 판정 persist일)
            if s != cur and run >= cfg["persist"]:
                cur, away = s, 0
        out[d] = cur
    return out


D.states = states_asym                                           # account()가 이 함수로 국면을 셈(설정에 p_up이 없으면 지금 규칙)


def months(navs):
    ds = sorted(navs)
    mo = {}
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * (navs[ds[j]] / navs[ds[j - 1]])
    return {m: v - 1 for m, v in mo.items()}


def score(navs, nst):
    r = D.stats(navs, nst)
    allm = months(navs)
    mo = {m: v for m, v in allm.items() if FIRST_FULL <= m <= LAST_FULL}
    neg = sorted(m for m, v in mo.items() if v < 0)
    switches = sum(1 for a, b in zip(sorted(nst), sorted(nst)[1:]) if nst[a] != nst[b])
    r.update({"loss_months": len(neg), "months": len(mo), "neg_list": neg,
              "worst_full_month_raw": min(mo.values()), "worst_full_month_pct": round(min(mo.values()) * 100, 3),
              "within": all(v["worst_day_raw"] >= DAY_LIM for v in r["by_kind"].values()) and min(mo.values()) >= MONTH_LIM,
              "loss_months_front": sum(1 for m in neg if m < "202201"), "loss_months_back": sum(1 for m in neg if m >= "202201"),
              "partial_months_ref": {m: round(v * 100, 3) for m, v in allm.items() if m not in mo}, "switches": switches,
              "min_cash_slack": D.account.min_slack})
    return r


def log(rec):
    BOX.mkdir(parents=True, exist_ok=True)
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def evaluate(cfg, label):
    key = json.dumps(cfg, sort_keys=True, ensure_ascii=False)
    log({"status": "STARTED", "key": key, "label": label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        r = score(*D.account(cfg))
    except Exception as e:
        log({"status": "FAILED", "key": key, "error": repr(e)})
        raise
    log({"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "loss_months": r["loss_months"],
         "worst_day_pct": r["worst_day_pct"], "worst_full_month_pct": r["worst_full_month_pct"]})
    return r


def grid():
    out = [("기준(지금 판)", dict(FINAL))]
    for pu in P_UP:
        for ps in P_SIDE:
            out.append((f"up{pu}_side{ps}", dict(FINAL, p_up=pu, p_side=ps)))
    return out


def eligible(x, base):
    """채택 조건: 나빠지는 것 없이(연 −0.5%p 안 · 손실 달 · 가장 나쁜 달) 하나는 확실히 좋아짐(손실 달 −3 · 가장 나쁜 달 +2%p · 연 +2%p)."""
    if not x["within"]:
        return False
    not_worse = (x["annual_raw"] >= base["annual_raw"] - ANN_SLACK and x["loss_months"] <= base["loss_months"]
                 and x["worst_full_month_raw"] >= base["worst_full_month_raw"])
    better = (x["loss_months"] <= base["loss_months"] - LOSS_CUT or x["worst_full_month_raw"] >= base["worst_full_month_raw"] + MONTH_GAIN
              or x["annual_raw"] >= base["annual_raw"] + ANN_GAIN)
    return not_worse and better


def neighbors(cfg):
    out = list(R4.neighbors(cfg))                                            # n × 0.85 · × 1.15 · persist ± 1(하락에서 빠져나오기) · r10m4 · r10m6
    for a, axis in (("p_up", P_UP), ("p_side", P_SIDE)):
        i = axis.index(cfg[a])
        out += [(a, axis[j]) for j in (i - 1, i + 1) if 0 <= j < len(axis)]
    return out


def lock_body():
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {f: sha(ROOT / f) for f in LOCK_FILES}
    body["base_ledger:" + M.name(BASE) + ".csv"] = sha(M.BASES / f"{M.name(BASE)}.csv")
    body["snapshot:" + Path(D.SNAP).name] = sha(D.SNAP)
    return body


def verify_inputs(path=None):
    want = json.loads(Path(path or LOCK).read_text())
    have = lock_body()
    bad = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
    if bad:
        sys.exit("입력 잠금이 다름(멈춤): " + json.dumps(bad, ensure_ascii=False))
    return want


def run():
    verify_inputs()
    D.BASE_CSV = M.BASES / f"{M.name(BASE)}.csv"
    D.DATA, D.FEAT = None, None
    rows = []
    for name, cfg in grid():
        r = evaluate(cfg, "고정")
        rows.append({"name": name, "cfg": {k: cfg.get(k) for k in ("p_up", "p_side")}, **{k: r[k] for k in (
            "annual_pct", "annual_raw", "worst_day_pct", "worst_full_month_pct", "worst_full_month_raw", "mdd_report_pct", "loss_months",
            "loss_months_front", "loss_months_back", "within", "years_pct", "halves_report", "neg_list", "partial_months_ref", "switches",
            "min_cash_slack")}})
    base = rows[0]
    ok = sorted([x for x in rows[1:] if eligible(x, base)], key=lambda x: (x["loss_months"], -x["annual_raw"], x["name"]))
    checked, final, used = [], None, 0
    for x in ok:
        cfg = dict(FINAL, **x["cfg"])
        nbs = neighbors(cfg)
        if used + len(nbs) > NB_CAP:
            break
        res, good = {}, True
        for a, v in nbs:
            nr = evaluate(dict(cfg, **{a: v}), "이웃")
            used += 1
            keep = nr["within"] and (base["loss_months"] - nr["loss_months"]) * 2 >= (base["loss_months"] - x["loss_months"]) \
                and (nr["worst_full_month_raw"] - base["worst_full_month_raw"]) * 2 >= (x["worst_full_month_raw"] - base["worst_full_month_raw"]) \
                and nr["annual_raw"] >= base["annual_raw"] - ANN_SLACK
            res[f"{a}={v}"] = {"annual_pct": nr["annual_pct"], "loss_months": nr["loss_months"], "worst_day_pct": nr["worst_day_pct"],
                               "worst_full_month_pct": nr["worst_full_month_pct"], "keep": keep}
            good = good and keep
        checked.append({"name": x["name"], "neighbors": res, "robust": good})
        if good:
            final = x
            break
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": "ASYM_CANDIDATE" if final else "NO_IMPROVEMENT", "final": final, "base": base, "checked": checked,
                      "eligible_count": len(ok), "rows_count": len(rows), "neighbor_evals": used,
                      "rules": {"day": DAY_LIM, "month": MONTH_LIM, "ann_slack": ANN_SLACK, "loss_cut": LOSS_CUT, "month_gain": MONTH_GAIN,
                                "ann_gain": ANN_GAIN, "neighbor_cap": NB_CAP},
                      "period": "2017-02-01 ~ 2026-09-15 · 공식 달은 완료 114달(2017-03 ~ 2026-08)"}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import asym_exit as A,mix54_run as M,regime_dev as D;"
            "D.BASE_CSV=M.BASES/f'{M.name(A.BASE)}.csv';D.DATA,D.FEAT=None,None;"
            "c=dict(A.FINAL,**json.loads(os.environ['AX_CFG']));n,s=D.account(c);print(json.dumps([n,s]))")
    res = []
    for extra in ({"p_up": 1, "p_side": 1}, {"p_up": 2, "p_side": 3}, {"p_up": 1, "p_side": 2}):
        env = dict(os.environ, AX_CFG=json.dumps(extra), REG_CUT="")
        fn, fs = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for c in cuts:
            env["REG_CUT"] = c
            pn, ps = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in pn if d < c]
            bad = [d for d in ds if abs(pn[d] - fn[d]) > 1e-12 or ps.get(d) != fs.get(d)]
            res.append({"cfg": extra, "cut": c, "days": len(ds), "diff_days": len(bad)})
    print(json.dumps({"pass": all(r["diff_days"] == 0 for r in res), "runs": res}, ensure_ascii=False))


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1))
    print(LOCK.read_text())


if __name__ == "__main__":
    {"run": run, "cut": cut, "lock": write_lock}[sys.argv[1]]()
