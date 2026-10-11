"""VOL-SIZE-0057 — 덧붙임 레버리지 몫을 시장 흔들림에 맞춰 줄이기(손실 달 연구 다음 후보 · GPT #237 '다음 연구는 클로드가 고름').
출발: MIX-0054 최종(켜 둔 판 · 바탕 d0.5_b0.3_no15m + 덧붙임 n24 · persist 3 · r10m5 · 레버리지 0.4 · 횡보 인버스 0.4).
진단(사전등록 전에 봄 · 공개 · ASYM-EXIT-0056 §0과 같음): 손실 40달 중 덧붙임이 가장 크게 깎은 달 18 · 깊은 손실 달은 덧붙임이 가장 큼.
  ASYM-EXIT-0056(#235 인정)은 '빨리 빠져나오기'로 헛걸음만 늘었음 → 이번에는 국면 판정은 그대로 두고 '레버리지 크기'만 흔들림에 맞춤.
새 규칙(이미 있는 regime_dev.targets의 lev_vt · band를 씀 · 코드 새로 넣지 않음):
  상승 국면 레버리지 몫 = up_lev × min(1, lev_vt ÷ 전날 장 끝까지 KODEX200 20일 흔들림(연 환산 v20a)).
  맞춤 때: 국면이 바뀐 날 · 달 첫날(지금과 같음) + band가 있으면 지금 ETF 몫이 목표와 band 넘게 벌어진 날(같은 ETF일 때만).
  band는 regime_dev의 기존 동작 그대로라 횡보 인버스 몫에도 적용됨(사전등록에 밝힘).
python3 research/vol_size.py lock   → input_lock.json(성과 셈 없음)
python3 research/vol_size.py run    → 잠금 검사 → 고정 26판 + 고르기 + 이웃(기록 evals.jsonl)
python3 research/vol_size.py cut    → 자르기 시험"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "VOL-SIZE-0057")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import regime_rules4 as R4  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/VOL-SIZE-0057"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
BASE = (0.5, 0.3)
FINAL = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])                   # lev_vt None · band None
UP_LEV = [0.4, 0.5, 0.6]
LEV_VT = [0.15, 0.20, 0.25, 0.30]
BAND = [None, 0.05]
FIRST_FULL, LAST_FULL = "201703", "202608"
DAY_LIM, MONTH_LIM, NB_CAP = -0.15, -0.15, 100
ANN_SLACK, LOSS_CUT, MONTH_GAIN, ANN_GAIN = 0.005, 3, 0.02, 0.02
# 경로 계약(ASYM-EXIT-0056 round 2와 같음): 잠금 · 실제 계산이 모두 같은 저장소 뿌리를 씀. 다르면 첫 STARTED 전에 멈춤.
CODE_FILES = ["research/vol_size.py", "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py"]
MARKET_FILES = ["market-data/investor_KSP.json", "market-data/index_KOSPI.json"]


def check_root():
    roots = {"vol_size": ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve(), "mix54_run": Path(M.ROOT).resolve()}
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
    return f"L{cfg['up_lev']}_vt{cfg['lev_vt']}_band{cfg['band']}"


def grid():
    out = [("기준(지금 판)", dict(FINAL)), ("대조: band만(L0.4 · vt 없음 · band 0.05)", dict(FINAL, band=0.05))]
    for lv in UP_LEV:
        for vt in LEV_VT:
            for bd in BAND:
                c = dict(FINAL, up_lev=lv, lev_vt=vt, band=bd)
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
    """덧붙임 규칙 이웃(n × 0.85 · × 1.15 · persist ± 1 · r10m4 · r10m6) + up_lev · lev_vt 한 칸씩 + band 반대쪽."""
    out = list(R4.neighbors(cfg))
    for a, axis in (("up_lev", UP_LEV), ("lev_vt", LEV_VT)):
        i = axis.index(cfg[a])
        out += [(a, axis[j]) for j in (i - 1, i + 1) if 0 <= j < len(axis)]
    out.append(("band", BAND[1 - BAND.index(cfg["band"])]))
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
        rows.append({"name": name, "cfg": {k: cfg.get(k) for k in ("up_lev", "lev_vt", "band")}, **{k: r[k] for k in KEEP}})
    base = rows[0]
    ok = sorted([x for x in rows[2:] if eligible(x, base)], key=lambda x: (x["loss_months"], -x["annual_raw"], x["name"]))
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
    print(json.dumps({"verdict": "VOL_CANDIDATE" if final else "NO_IMPROVEMENT", "final": final, "base": base, "checked": checked,
                      "eligible_count": len(ok), "rows_count": len(rows), "neighbor_evals": used,
                      "rules": {"day": DAY_LIM, "month": MONTH_LIM, "ann_slack": ANN_SLACK, "loss_cut": LOSS_CUT, "month_gain": MONTH_GAIN,
                                "ann_gain": ANN_GAIN, "neighbor_cap": NB_CAP},
                      "period": "2017-02-01 ~ 2026-09-15 · 공식 달은 완료 114달(2017-03 ~ 2026-08)"}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import vol_size as V,mix54_run as M,regime_dev as D;"
            "D.BASE_CSV=M.BASES/f'{M.name(V.BASE)}.csv';D.DATA,D.FEAT=None,None;"
            "c=dict(V.FINAL,**json.loads(os.environ['VX_CFG']));n,s=D.account(c);print(json.dumps([n,s]))")
    res = []
    for extra in ({"up_lev": 0.6, "lev_vt": 0.15, "band": 0.05}, {"up_lev": 0.5, "lev_vt": 0.25, "band": None},
                  {"up_lev": 0.4, "lev_vt": 0.20, "band": 0.05}):
        env = dict(os.environ, VX_CFG=json.dumps(extra), REG_CUT="")
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
