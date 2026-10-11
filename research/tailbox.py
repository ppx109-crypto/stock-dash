"""TAILBOX-0067 — 지금 판 보완 둘(사용자 2026-10-11 "가, 나 진행해줘" · AUDIT-MIX54-0066 #257 보완 후보):
가(TAIL) 급락일 꼬리 줄이기 = 흔들림 맞춤 레버리지(regime_dev lev_vt · VOL-SIZE-0057 격자의 band 없음 12칸) · 사용자 잣대(하루 · 달 −15% · 연수익 · 가장 나쁜 하루)로 평가.
나(BOX) 박스권에서 덧붙임 쉬기 = 효율비 ER(n) = |C_p − C_{p−n}| ÷ Σ|하루 변화|(전 거래일 p까지) < thr이면 상승 · 횡보 국면에서 덧붙임 0.
두 갈래로 잼: ① 계좌 전체 2017-02 ~ 2026-09-15(regime_dev.account · MIX-0054 바탕) ② 덧붙임만(바탕 = 현금) 2010-03 ~ 2016-12(개발 구간 · 공개).
python3 research/tailbox.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "TAILBOX-0067")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import regime_rules4 as R4  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/TAILBOX-0067"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
BASE = (0.5, 0.3)
FINAL = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])
UP_LEV, LEV_VT = [0.4, 0.5, 0.6], [0.15, 0.20, 0.25, 0.30]
ER_N, ER_THR = [60, 120], [0.10, 0.15, 0.20]
FIRST_FULL, LAST_FULL = "201703", "202608"
DEV_LO, DEV_HI = "20100301", "20161231"
DAY_LIM, MONTH_LIM = -0.15, -0.15
CODE_FILES = ["research/tailbox.py", "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py"]
MARKET_FILES = ["market-data/investor_KSP.json", "market-data/index_KOSPI.json"]
_ORIG_STATES, _ORIG_TARGETS = D.states, D.targets
ER = {}


def check_root():
    roots = {"tailbox": ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve(), "mix54_run": Path(M.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def er_table(n):
    """069500 종가로 날마다 ER(n)(그날까지 값만) · 자료가 n일 안 되면 없음."""
    if n not in ER:
        px = D.data()[1]["069500"]
        ds = sorted(px)
        xs = [px[d] for d in ds]
        out = {}
        for k in range(n, len(xs)):
            path = sum(abs(xs[i] - xs[i - 1]) for i in range(k - n + 1, k + 1))
            out[ds[k]] = abs(xs[k] - xs[k - n]) / path if path > 0 else 0.0
        ER[n] = out
    return ER[n]


def states_box(feat, cfg):
    """box가 없으면 원래 states 그대로. 있으면 원래 국면(버팀 포함)이 상승 · 횡보이고 그날 ER < thr이면 '박스'."""
    st = _ORIG_STATES(feat, cfg)
    bx = cfg.get("box")
    if not bx:
        return st
    er = er_table(bx["n"])
    return {d: ("박스" if s in ("상승", "횡보") and d in er and er[d] < bx["thr"] else s) for d, s in st.items()}


def targets_box(state, cfg, f=None):
    if state == "박스":
        return 1.0, cfg["inv"], 0.0                              # 덧붙임 0(1일봉 몫 그대로)
    return _ORIG_TARGETS(state, cfg, f)


D.states, D.targets = states_box, targets_box                    # account()가 이 둘을 씀(box 없으면 원래와 같음)


def full(cfg):
    D.BASE_CSV = M.BASES / f"{M.name(BASE)}.csv"
    if D.DATA is None:
        D.FEAT = None
    return D.account(cfg)[0]


def standalone(cfg, lo=DEV_LO, hi=DEV_HI):
    """덧붙임만(바탕 = 현금): 같은 국면 · 목표 · 맞춤 때 · 비용(ETF 0.05%) · 첫날 현금."""
    base, etf, br, flow = D.data()
    if D.FEAT is None or D.FEAT[0] is not D.DATA:
        D.FEAT = (D.DATA, D.features(etf, br, flow, D.short_breadth() if br else {}))
    feat = D.FEAT[1]
    st = D.states(feat, cfg)
    days = [d for d in sorted(etf["069500"]) if lo <= d <= hi and all(d in etf[c] for c in ("122630", "114800"))]
    code, ve, cash, pend = None, 0.0, 1.0, None
    navs = {days[0]: 1.0}
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        if code:
            ve *= etf[code][d] / etf[code][p]
        A = ve + cash
        s = st.get(p, "횡보")
        if s != pend or d[:6] != p[:6]:
            _, c2, fe = D.targets(s, cfg, feat.get(p))
            te = fe * A
            A -= D.COST_ETF * (abs(te - ve) if c2 == code else ve + te)
            code = c2 if fe > 0 else None
            ve = fe * A if code else 0.0
            cash = A - ve
            pend = s
        navs[d] = ve + cash
    return navs


def stats(navs, first=FIRST_FULL, last=LAST_FULL):
    ds = sorted(navs)
    rets = [navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))]
    mo = {}
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * (navs[ds[j]] / navs[ds[j - 1]])
    full_m = {m: v - 1 for m, v in mo.items() if first <= m <= last}
    ann = (navs[ds[-1]] / navs[ds[0]]) ** (250 / len(ds)) - 1
    pk, mdd = 0, 0
    for d in ds:
        pk = max(pk, navs[d]); mdd = min(mdd, navs[d] / pk - 1)
    return {"annual_raw": ann, "annual_pct": round(ann * 100, 3), "worst_day_raw": min(rets), "worst_day_pct": round(min(rets) * 100, 3),
            "worst_full_month_raw": min(full_m.values()), "worst_full_month_pct": round(min(full_m.values()) * 100, 3),
            "mdd_report_pct": round(mdd * 100, 2), "loss_months": sum(1 for v in full_m.values() if v < 0), "months": len(full_m),
            "within": min(rets) >= DAY_LIM and min(full_m.values()) >= MONTH_LIM}


def both(cfg):
    a = stats(full(cfg))
    b = stats(standalone(cfg), first="201004", last="201612")
    return {"full": a, "dev": b}


def grid():
    g = [("기준(지금 판)", dict(FINAL))]
    for lv in UP_LEV:
        for vt in LEV_VT:
            g.append((f"가_L{lv}_vt{vt}", dict(FINAL, up_lev=lv, lev_vt=vt)))
    for n in ER_N:
        for t in ER_THR:
            g.append((f"나_ER{n}_{t}", dict(FINAL, box={"n": n, "thr": t})))
    return g


def ok_tail(x, b, half=False):
    """가: 계좌 전체 잣대 안 · 연 ≥ 기준 − 0.5%p · 가장 나쁜 하루 ≥ 기준 + 2%p(이웃은 + 1%p) · 덧붙임만(2010 ~ 2016)에서 하루 · 달 · 연(−0.5%p) 기준보다 나쁘지 않음."""
    f, d, bf, bd = x["full"], x["dev"], b["full"], b["dev"]
    ok = f["within"] and f["annual_raw"] >= bf["annual_raw"] - 0.005 and f["worst_day_raw"] >= bf["worst_day_raw"] + (0.01 if half else 0.02)
    if not half:
        ok = ok and d["worst_day_raw"] >= bd["worst_day_raw"] and d["worst_full_month_raw"] >= bd["worst_full_month_raw"] and d["annual_raw"] >= bd["annual_raw"] - 0.005
    return ok


def ok_box(x, b, half=False):
    """나: 덧붙임만(2010 ~ 2016) 연 ≥ 기준 + 2%p(이웃 + 1%p) · 계좌 전체 잣대 안 · 연 ≥ 기준 − 1%p · 가장 나쁜 달 ≥ 기준 − 1%p."""
    f, d, bf, bd = x["full"], x["dev"], b["full"], b["dev"]
    return (d["annual_raw"] >= bd["annual_raw"] + (0.01 if half else 0.02) and f["within"] and f["annual_raw"] >= bf["annual_raw"] - 0.01
            and f["worst_full_month_raw"] >= bf["worst_full_month_raw"] - 0.01)


def nb_tail(cfg):
    out = []
    i, k = UP_LEV.index(cfg["up_lev"]), LEV_VT.index(cfg["lev_vt"])
    out += [dict(cfg, up_lev=UP_LEV[j]) for j in (i - 1, i + 1) if 0 <= j < len(UP_LEV)]
    out += [dict(cfg, lev_vt=LEV_VT[j]) for j in (k - 1, k + 1) if 0 <= j < len(LEV_VT)]
    out += [dict(cfg, **{a: v}) for a, v in R4.neighbors(cfg)]
    return out


def nb_box(cfg):
    bx = cfg["box"]
    k = ER_THR.index(bx["thr"])
    out = [dict(cfg, box=dict(bx, thr=ER_THR[j])) for j in (k - 1, k + 1) if 0 <= j < len(ER_THR)]
    out.append(dict(cfg, box=dict(bx, n=[n for n in ER_N if n != bx["n"]][0])))
    out += [dict(cfg, **{a: v}) for a, v in R4.neighbors(cfg)]
    return out


def lock_body():
    root = check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {"root": str(root)}
    body.update({f: sha(root / f) for f in CODE_FILES})
    body.update({f"etf-data/{c}.json": sha(Path(D.ROOT) / f"etf-data/{c}.json") for c in D.ETF})
    body.update({f: sha(Path(D.ROOT) / f) for f in MARKET_FILES})
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


def log(rec):
    BOX.mkdir(parents=True, exist_ok=True)
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); os.fsync(fh.fileno())


def evaluate(name, cfg, label):
    key = json.dumps(cfg, sort_keys=True, ensure_ascii=False)
    log({"status": "STARTED", "key": key, "label": label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        r = both(cfg)
    except Exception as e:
        log({"status": "FAILED", "key": key, "error": repr(e)}); raise
    log({"status": "DONE", "key": key, "full_annual": r["full"]["annual_pct"], "dev_annual": r["dev"]["annual_pct"]})
    return {"name": name, "cfg": cfg, **r}


def run():
    verify_inputs()
    D.DATA, D.FEAT = None, None
    rows = [evaluate(n, c, "고정") for n, c in grid()]
    b = rows[0]
    out = {}
    for tag, pref, okf, nbf in (("가", "가_", ok_tail, nb_tail), ("나", "나_", ok_box, nb_box)):
        cand = sorted([x for x in rows if x["name"].startswith(pref) and okf(x, b)], key=lambda x: (-x["full"]["annual_raw"], x["name"]))
        checked, final = [], None
        for x in cand:
            res, good = [], True
            for c in nbf(x["cfg"]):
                nr = evaluate("이웃", c, "이웃")
                keep = okf(nr, b, half=True)
                res.append({"cfg": c, "full": nr["full"], "dev": nr["dev"], "keep": keep})
                good = good and keep
            checked.append({"name": x["name"], "robust": good, "neighbors": res})
            if good:
                final = x
                break
        out[tag] = {"eligible": [x["name"] for x in cand], "final": final["name"] if final else None, "checked": checked}
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": {"가": "TAIL_CANDIDATE" if out["가"]["final"] else "NO_IMPROVEMENT",
                                  "나": "BOX_CANDIDATE" if out["나"]["final"] else "NO_IMPROVEMENT"}, "detail": out}, ensure_ascii=False))


def cut():
    cuts = ("20120615", "20150820", "20200320", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import tailbox as T,regime_dev as D;D.DATA,D.FEAT=None,None;"
            "c=dict(T.FINAL,**json.loads(os.environ['TB_CFG']));"
            "a=T.full(c) if os.environ.get('REG_CUT','') in ('',) or os.environ['REG_CUT']>='20170301' else {};s=T.standalone(c,'20100301','20260915');print(json.dumps([a,s]))")
    res = []
    for extra in ({"up_lev": 0.6, "lev_vt": 0.2}, {"box": {"n": 60, "thr": 0.15}}, {"box": {"n": 120, "thr": 0.2}, "up_lev": 0.5, "lev_vt": 0.25}):
        env = dict(os.environ, TB_CFG=json.dumps(extra), REG_CUT="")
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
