"""FLOW-GATE-0059 — 손실 달 공통점에서 만든 엣지: 외국인 20일 순매도가 깊으면 레버리지 덜 들기(사용자 2026-10-11 "손실달의 공통점을 파악하고 거기서 엣지를 만드는건 어떨까?").
출발: MIX-0054 최종(켜 둔 판 · 바탕 d0.5_b0.3_no15m + 덧붙임 n24 · persist 3 · r10m5 · 레버리지 0.4 · 횡보 인버스 0.4).
진단(사전등록 전에 봄 · 공개 · PLAN §0): 완료 114달을 '전달 마지막 거래일까지 알 수 있는 값' 12개로 3등분해 손실 달 비율을 봄.
  앞 반 · 뒤 반 모두에서 같은 방향이 나온 것은 외국인 20일 순매수(F20 · 코스피 거래대금 대비 합)뿐: 앞 반 문턱(−0.154) 아래 달의 손실 비율 앞 40% · 뒤 50%(나머지 32% · 28%).
새 규칙(국면 판정 · 종목 · 때 · 비용은 그대로 · 레버리지 크기만):
  상승 국면 목표 레버리지 = F20(판정 전날 장 끝까지 · 수급은 장 끝난 뒤 자료라 다음 거래일 종가에 실행) < thr 이면 up_lev × k, 아니면 up_lev.
  맞춤 때는 지금과 같음(국면이 바뀐 날 · 달 첫날 · band 없음) → 달 첫날 판단이 진단(전달 끝 값)과 같은 꼴.
python3 research/flow_gate.py lock   → input_lock.json(성과 셈 없음)
python3 research/flow_gate.py run    → 잠금 검사 → 고정 7판 + 고르기 + 이웃(기록 evals.jsonl)
python3 research/flow_gate.py cut    → 자르기 시험"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "FLOW-GATE-0059")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import regime_rules4 as R4  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/FLOW-GATE-0059"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
BASE = (0.5, 0.3)
FINAL = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])                   # lev_vt None · band None
THR = [-0.20, -0.15, -0.10]
GATE_K = [0.0, 0.5]
UP_LEV = [0.4]                                                   # round 2(GPT #242 지적 1): 문 효과만 보도록 0.4 고정
_ORIG_TARGETS = D.targets


def targets_gate(state, cfg, f=None):
    """상승 국면이고 cfg에 f_thr가 있으면: 전날까지 F20 < f_thr 이면 레버리지 × gate_k. 그 밖은 원래 targets 그대로."""
    fb, code, fe = _ORIG_TARGETS(state, cfg, f)
    if state == "상승" and cfg.get("f_thr") is not None and f is not None and f.get("F20") is not None and f["F20"] < cfg["f_thr"]:
        fe = fe * cfg["gate_k"]
    return fb, code, fe


D.targets = targets_gate                                         # account()가 이 함수로 목표를 셈(f_thr가 없으면 지금 판 그대로)
FIRST_FULL, LAST_FULL = "201703", "202608"
DAY_LIM, MONTH_LIM, NB_CAP = -0.15, -0.15, 100
ANN_SLACK, LOSS_CUT, MONTH_GAIN, ANN_GAIN = 0.005, 3, 0.02, 0.02
# 경로 계약(ASYM-EXIT-0056 round 2와 같음): 잠금 · 실제 계산이 모두 같은 저장소 뿌리를 씀. 다르면 첫 STARTED 전에 멈춤.
CODE_FILES = ["research/flow_gate.py", "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py"]
MARKET_FILES = ["market-data/investor_KSP.json", "market-data/index_KOSPI.json"]


def check_root():
    roots = {"flow_gate": ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve(), "mix54_run": Path(M.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def loader_files():
    root = Path(D.ROOT)
    return {f"etf-data/{c}.json": root / f"etf-data/{c}.json" for c in D.ETF} | {f: root / f for f in MARKET_FILES}


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
    r.update({"loss_months": len(neg), "months": len(mo), "neg_list": neg, "month_pct": {m: round(v * 100, 3) for m, v in mo.items()},
              "worst_full_month_raw": min(mo.values()), "worst_full_month_pct": round(min(mo.values()) * 100, 3),
              "within": all(v["worst_day_raw"] >= DAY_LIM for v in r["by_kind"].values()) and min(mo.values()) >= MONTH_LIM,
              "loss_months_front": sum(1 for m in neg if m < "202201"), "loss_months_back": sum(1 for m in neg if m >= "202201"),
              "partial_months_ref": {m: round(v * 100, 3) for m, v in allm.items() if m not in mo},
              "min_cash_slack": D.account.min_slack, "etf_trims": D.account.trims})
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


def cname(cfg):
    return f"thr{cfg['f_thr']}_k{cfg['gate_k']}_L{cfg['up_lev']}"


def grid():
    out = [("기준(지금 판)", dict(FINAL))]
    for t in THR:
        for k in GATE_K:
            for lv in UP_LEV:
                c = dict(FINAL, f_thr=t, gate_k=k, up_lev=lv)
                out.append((cname(c), c))
    return out


def eligible(x, base):
    """채택 조건(ASYM-EXIT-0056과 같음): 나빠지는 것 없이(연 −0.5%p 안 · 손실 달 · 가장 나쁜 달) 하나는 확실히 좋아짐(손실 달 −3 · 가장 나쁜 달 +2%p · 연 +2%p)."""
    if not x["within"]:
        return False
    not_worse = (x["annual_raw"] >= base["annual_raw"] - ANN_SLACK and x["loss_months"] <= base["loss_months"]
                 and x["worst_full_month_raw"] >= base["worst_full_month_raw"])
    better = (x["loss_months"] <= base["loss_months"] - LOSS_CUT or x["worst_full_month_raw"] >= base["worst_full_month_raw"] + MONTH_GAIN
              or x["annual_raw"] >= base["annual_raw"] + ANN_GAIN)
    return not_worse and better


def neighbors(cfg):
    """덧붙임 규칙 이웃(n × 0.85 · × 1.15 · persist ± 1 · r10m4 · r10m6) + 문턱 한 칸씩 + k 반대쪽(up_lev는 0.4 고정)."""
    out = list(R4.neighbors(cfg))
    i = THR.index(cfg["f_thr"])
    out += [("f_thr", THR[j]) for j in (i - 1, i + 1) if 0 <= j < len(THR)]
    out.append(("gate_k", GATE_K[1 - GATE_K.index(cfg["gate_k"])]))
    return out


def lock_body():
    root = check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {"root": str(root)}
    body.update({f: sha(root / f) for f in CODE_FILES})
    body.update({k: sha(v) for k, v in loader_files().items()})
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


KEEP = ("annual_pct", "annual_raw", "worst_day_pct", "worst_full_month_pct", "worst_full_month_raw", "mdd_report_pct", "loss_months",
        "loss_months_front", "loss_months_back", "within", "years_pct", "halves_report", "neg_list", "month_pct", "partial_months_ref",
        "min_cash_slack", "etf_trims")


def run():
    verify_inputs()
    D.BASE_CSV = M.BASES / f"{M.name(BASE)}.csv"
    D.DATA, D.FEAT = None, None
    rows = []
    for name, cfg in grid():
        r = evaluate(cfg, "고정")
        rows.append({"name": name, "cfg": {k: cfg.get(k) for k in ("f_thr", "gate_k", "up_lev")}, **{k: r[k] for k in KEEP}})
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
    print(json.dumps({"verdict": "FLOW_CANDIDATE" if final else "NO_IMPROVEMENT", "final": final, "base": base, "checked": checked,
                      "eligible_count": len(ok), "rows_count": len(rows), "neighbor_evals": used,
                      "rules": {"day": DAY_LIM, "month": MONTH_LIM, "ann_slack": ANN_SLACK, "loss_cut": LOSS_CUT, "month_gain": MONTH_GAIN,
                                "ann_gain": ANN_GAIN, "neighbor_cap": NB_CAP},
                      "period": "2017-02-01 ~ 2026-09-15 · 공식 달은 완료 114달(2017-03 ~ 2026-08)"}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import flow_gate as V,mix54_run as M,regime_dev as D;"
            "D.BASE_CSV=M.BASES/f'{M.name(V.BASE)}.csv';D.DATA,D.FEAT=None,None;"
            "c=dict(V.FINAL,**json.loads(os.environ['FX_CFG']));n,s=D.account(c);print(json.dumps([n,s]))")
    res = []
    for extra in ({"f_thr": -0.15, "gate_k": 0.0, "up_lev": 0.4}, {"f_thr": -0.10, "gate_k": 0.5, "up_lev": 0.4},
                  {"f_thr": -0.20, "gate_k": 0.0, "up_lev": 0.4}):
        env = dict(os.environ, FX_CFG=json.dumps(extra), REG_CUT="")
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
