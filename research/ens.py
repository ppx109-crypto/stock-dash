"""ENS-0068 — 국면 판단 여러 판 섞기(사용자 2026-10-11 "백테스트하고 약점을 보완방법 연구해줘 지피티와"):
약점 = 설정 운(MIX-0054 이웃: n 20 → 달 −10.8% · persist 4 → 달 −14.5% · 연 28.5 ~ 35.5%) · 늦게 빠져나오기(AUDIT −70.5%p).
보완 = 같은 규칙의 n · persist를 여러 개 함께 돌려 판단을 섞음.
  frac: 순 노출 E = 2 × up_lev × (상승 수 ÷ K) − side_inv × (횡보 수 ÷ K) → E > 0이면 122630 E ÷ 2 · E < 0이면 인버스 −E · 하락 표는 0
  vote: 가장 많은 국면(같으면 하락 > 횡보 > 상승) → 지금 판 목표 그대로
두 갈래로 잼(TAILBOX-0067과 같은 셈): ① 계좌 전체 2017-02 ~ 2026-09-15 ② 덧붙임만 2010-03 ~ 2016-12(개발 구간).
python3 research/ens.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "ENS-0068")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import tailbox as T  # noqa: E402  (full · standalone · stats · 지금 판 FINAL을 그대로 씀)

D, M = T.D, T.M
BOX = ROOT / "research-exchange/claude-to-gpt/ENS-0068"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
FINAL = T.FINAL
N_SET, P_SET = [17, 20, 24, 28, 32], [2, 3, 4]
UP_LEV = [0.4, 0.5]
CODE_FILES = ["research/ens.py"] + T.CODE_FILES
_PREV_STATES, _PREV_TARGETS = D.states, D.targets             # tailbox 감싼 것(box 없으면 원래와 같음)
ORDER = ("하락", "횡보", "상승")                                  # vote 같을 때 앞이 이김(조심 쪽)


def members(e):
    return [(n, p) for n in e["n"] for p in e["p"]]


def vote(c):
    """c = (상승 수, 횡보 수, 하락 수) → 가장 많은 국면 · 같으면 하락 > 횡보 > 상승."""
    best = max(c)
    return next(k for k in ORDER if c[("상승", "횡보", "하락").index(k)] == best)


def states_ens(feat, cfg):
    """ens가 없으면 그대로. 있으면 구성원마다 원래 states(그날까지 값 · 버팀 포함)를 돌려 날마다 표를 셈 → 'E:상승/횡보/하락' 이름."""
    e = cfg.get("ens")
    if not e:
        return _PREV_STATES(feat, cfg)
    sts = [T._ORIG_STATES(feat, dict(cfg, n=n, persist=p)) for n, p in members(e)]
    out = {}
    for d in sts[0]:
        c = [sum(1 for s in sts if s[d] == k) for k in ("상승", "횡보", "하락")]
        if e["mode"] == "vote":
            out[d] = vote(c)
        else:
            out[d] = f"E:{c[0]}/{c[1]}/{c[2]}"
    return out


def targets_ens(state, cfg, f=None):
    if not state.startswith("E:"):
        return _PREV_TARGETS(state, cfg, f)
    u, s, dn = (int(x) for x in state[2:].split("/"))
    k = u + s + dn
    net = 2 * cfg["up_lev"] * u / k - cfg["side_inv"] * s / k
    if net > 1e-12:
        return 1.0, "122630", net / 2
    if net < -1e-12:
        return 1.0, cfg["inv"], -net
    return 1.0, cfg["inv"], 0.0


D.states, D.targets = states_ens, targets_ens


def both(cfg):
    a = T.stats(T.full(cfg))
    b = T.stats(T.standalone(cfg), first="201004", last="201612")
    return {"full": a, "dev": b}


def ens(mode, ns=N_SET, ps=P_SET):
    return {"mode": mode, "n": list(ns), "p": list(ps)}


def grid():
    g = [("기준(지금 판)", dict(FINAL))]
    for lv in UP_LEV:
        g.append((f"frac_np_L{lv}", dict(FINAL, up_lev=lv, ens=ens("frac"))))
        g.append((f"frac_n_L{lv}", dict(FINAL, up_lev=lv, ens=ens("frac", ps=[3]))))
        g.append((f"vote_np_L{lv}", dict(FINAL, up_lev=lv, ens=ens("vote"))))
    return g


def ok(x, b, nb=False):
    """채택(사전등록): ① 계좌 전체 잣대 안 · 연 ≥ 기준 − 0.5%p · 가장 나쁜 완료 달 ≥ 기준 + 1%p ② 덧붙임만 연 · 가장 나쁜 완료 달이 기준보다 나쁘지 않음.
    이웃: ① 잣대 안 · 연 ≥ 기준 − 1%p · 가장 나쁜 달 ≥ 기준 ② 연 ≥ 기준 − 0.5%p."""
    f, d, bf, bd = x["full"], x["dev"], b["full"], b["dev"]
    if nb:
        return (f["within"] and f["annual_raw"] >= bf["annual_raw"] - 0.01 and f["worst_full_month_raw"] >= bf["worst_full_month_raw"]
                and d["annual_raw"] >= bd["annual_raw"] - 0.005)
    return (f["within"] and f["annual_raw"] >= bf["annual_raw"] - 0.005 and f["worst_full_month_raw"] >= bf["worst_full_month_raw"] + 0.01
            and d["annual_raw"] >= bd["annual_raw"] and d["worst_full_month_raw"] >= bd["worst_full_month_raw"])


def neighbors(cfg):
    """구성원 묶음을 통째로 옮긴 넷: n × 0.85 · × 1.15(반올림) · persist − 1 · + 1."""
    e = cfg["ens"]
    out = []
    for m in (0.85, 1.15):
        out.append(dict(cfg, ens=dict(e, n=[int(round(n * m)) for n in e["n"]])))
    for dp in (-1, 1):
        out.append(dict(cfg, ens=dict(e, p=[p + dp for p in e["p"]])))
    return out


def lock_body():
    root = T.check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = T.lock_body()
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
    cand = sorted([x for x in rows[1:] if ok(x, b)], key=lambda x: (-x["full"]["annual_raw"], x["name"]))
    checked, final = [], None
    for x in cand:
        res, good = [], True
        for c in neighbors(x["cfg"]):
            nr = evaluate("이웃", c, "이웃")
            keep = ok(nr, b, nb=True)
            res.append({"cfg": c, "full": nr["full"], "dev": nr["dev"], "keep": keep})
            good = good and keep
        checked.append({"name": x["name"], "robust": good, "neighbors": res})
        if good:
            final = x
            break
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    (BOX / "evidence/checked.json").write_text(json.dumps(checked, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": "ENS_CANDIDATE" if final else "NO_IMPROVEMENT", "final": final["name"] if final else None,
                      "eligible": [x["name"] for x in cand], "checked": [{"name": c["name"], "robust": c["robust"],
                      "keep": [n["keep"] for n in c["neighbors"]]} for c in checked]}, ensure_ascii=False))


def cut():
    cuts = ("20120615", "20150820", "20200320", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import ens as E;D=E.D;D.DATA,D.FEAT=None,None;"
            "c=dict(E.FINAL,**json.loads(os.environ['EN_CFG']));"
            "a=E.T.full(c) if os.environ.get('REG_CUT','')=='' or os.environ['REG_CUT']>='20170301' else {};"
            "s=E.T.standalone(c,'20100301','20260915');print(json.dumps([a,s]))")
    res = []
    for extra in ({"up_lev": 0.5, "ens": ens("frac")}, {"ens": ens("vote")}, {"ens": ens("frac", ns=[20, 23, 28, 32, 37], ps=[3])}):
        env = dict(os.environ, EN_CFG=json.dumps(extra), REG_CUT="")
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
