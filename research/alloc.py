"""ALLOC-0065 — 최종 자본 분배 연구(사용자 2026-10-11 '가': 봇 개발이 더 나아가지 못해 최종 분배 연구로 넘어감).
갈래 셋: A = 지금 판 MIX-0054(regime_dev.account 그대로) · B = POOL-1 추세 바구니(pool_xasset.account) · C = POOL-2 해외 지수 듀얼 모멘텀(pool_global.account).
각 갈래는 따로 굴리고, 달 첫 거래일 종가에 목표 몫(wA · wB · wC)으로 다시 맞춤. 옮기는 돈 비용: A를 줄이면 0.30% · 늘리면 0.05% · B · C는 0.05%.
분배를 '추천'까지만 함 · 실제로 바꾸는 것은 사용자 직접 승인.
python3 research/alloc.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "ALLOC-0065")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import pool_xasset as PX  # noqa: E402
import pool_global as PG  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/ALLOC-0065"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
BASE = (0.5, 0.3)
FINAL = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])
B_CELLS = {"U3_n6": {"u": "U3", "n": 6}, "U4_n10": {"u": "U4", "n": 10}}       # POOL-1 칸 둘(바구니 · N이 서로 다른 끝)
C_CELL = {"k": 2, "l": 12}                                                       # POOL-2 칸 하나
WB = [0.0, 0.1, 0.2, 0.3, 0.4]
WC = [0.0, 0.1, 0.2]
COST_A_DOWN, COST_A_UP, COST_ETF = D.COST_BASE_DOWN, D.COST_BASE_UP, D.COST_ETF
FIRST_FULL, LAST_FULL = "201703", "202608"
DAY_LIM, MONTH_LIM = -0.15, -0.15
CODE_FILES = ["research/alloc.py", "research/pool_global.py", "research/pool_xasset.py", "research/xasset.py",
              "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py"]
CACHE = {}


def check_root():
    roots = {"alloc": ROOT.resolve(), "pool_global": PG.ROOT.resolve(), "pool_xasset": PX.ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve(),
             "mix54_run": Path(M.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def streams(b_cell):
    """갈래 셋의 날마다 NAV(A의 날 기준 · B · C는 그날 또는 그 앞 마지막 값)."""
    key = b_cell
    if key in CACHE:
        return CACHE[key]
    D.BASE_CSV = M.BASES / f"{M.name(BASE)}.csv"
    D.DATA, D.FEAT = None, None
    a, _ = D.account(dict(FINAL))
    b = PX.account(B_CELLS[b_cell])
    c = PG.account(C_CELL)
    days = sorted(a)

    def align(s):
        ks, out, j, last = sorted(s), {}, 0, None
        for d in days:
            while j < len(ks) and ks[j] <= d:
                last = s[ks[j]]
                j += 1
            out[d] = last
        return out
    CACHE[key] = (days, a, align(b), align(c))
    return CACHE[key]


def account(cfg):
    """cfg = {"b": 칸, "wb", "wc"} · wA = 1 − wb − wc. 첫날 목표 몫으로 시작(비용 없음) · 달 첫 거래일마다 다시 맞춤."""
    days, a, b, c = streams(cfg["b"])
    w = {"A": 1 - cfg["wb"] - cfg["wc"], "B": cfg["wb"], "C": cfg["wc"]}
    src = {"A": a, "B": b, "C": c}
    v = dict(w)
    navs = {days[0]: 1.0}
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        for k in v:
            if v[k] and src[k][p] and src[k][d]:
                v[k] *= src[k][d] / src[k][p]
        tot = sum(v.values())
        if d[:6] != p[:6]:
            want = {k: w[k] * tot for k in v}
            cost = sum((COST_A_DOWN if want[k] < v[k] else COST_A_UP) * abs(want[k] - v[k]) if k == "A" else COST_ETF * abs(want[k] - v[k]) for k in v)
            tot -= cost
            v = {k: w[k] * tot for k in v}
        navs[d] = sum(v.values())
    return navs


def score(navs):
    r = D.stats(navs, {d: "횡보" for d in navs})
    mo = {}
    ds = sorted(navs)
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * (navs[ds[j]] / navs[ds[j - 1]])
    full = {m: v - 1 for m, v in mo.items() if FIRST_FULL <= m <= LAST_FULL}
    neg = sorted(m for m, v in full.items() if v < 0)
    wd = min(navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds)))
    return {"annual_raw": r["annual_raw"], "annual_pct": r["annual_pct"], "worst_day_raw": wd, "worst_day_pct": round(wd * 100, 3),
            "worst_full_month_raw": min(full.values()), "worst_full_month_pct": round(min(full.values()) * 100, 3),
            "within": wd >= DAY_LIM and min(full.values()) >= MONTH_LIM, "mdd_report_pct": r["mdd_report_pct"],
            "loss_months": len(neg), "neg_list": neg, "eff": r["annual_raw"] / abs(min(full.values())), "years_pct": r["years_pct"],
            "month_pct": {m: round(v * 100, 3) for m, v in full.items()}}


def grid():
    out = [("기준: 지금 판 100%", {"b": "U3_n6", "wb": 0.0, "wc": 0.0})]
    for wc in WC:
        if wc:
            out.append((f"B0_C{wc}", {"b": "U3_n6", "wb": 0.0, "wc": wc}))
    for bc in B_CELLS:
        for wb in WB[1:]:
            for wc in WC:
                out.append((f"{bc}_B{wb}_C{wc}", {"b": bc, "wb": wb, "wc": wc}))
    return out


def pick(rows):
    """추천 둘(사전등록):
    ① 수익 추천: 잣대 안 칸 중 연수익 최고(같으면 손실 달 적은 칸).
    ② 균형 추천: 잣대 안 · 연 ≥ 기준 − 3%p인 칸 중 효율(연 ÷ |가장 나쁜 완료 달|) 최고."""
    base = rows[0]
    ok = [x for x in rows if x["within"]]
    r1 = max(ok, key=lambda x: (x["annual_raw"], -x["loss_months"])) if ok else None
    bal = [x for x in ok if x["annual_raw"] >= base["annual_raw"] - 0.03]
    r2 = max(bal, key=lambda x: (x["eff"], x["annual_raw"])) if bal else None
    return r1, r2


def neighbors(cfg):
    out = []
    i = WB.index(cfg["wb"])
    out += [dict(cfg, wb=WB[j]) for j in (i - 1, i + 1) if 0 <= j < len(WB) and WB[j] > 0]
    k = WC.index(cfg["wc"])
    out += [dict(cfg, wc=WC[j]) for j in (k - 1, k + 1) if 0 <= j < len(WC)]
    if cfg["wb"] > 0:
        out.append(dict(cfg, b=[x for x in B_CELLS if x != cfg["b"]][0]))
    return out


def lock_body():
    root = check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {"root": str(root)}
    body.update({f: sha(root / f) for f in CODE_FILES})
    files = {f"etf-data/{c}.json": Path(D.ROOT) / f"etf-data/{c}.json" for c in sorted(set(D.ETF) | set(PG.codes_all()) | set(PX.X.SLEEVE_ETF) | {PX.BOND})}
    files |= {f: Path(D.ROOT) / f for f in ("market-data/investor_KSP.json", "market-data/index_KOSPI.json")}
    body.update({k: sha(v) for k, v in files.items()})
    body["base_ledger:" + M.name(BASE) + ".csv"] = sha(M.BASES / f"{M.name(BASE)}.csv")
    body["snapshot:" + Path(D.SNAP).name] = sha(D.SNAP)
    body["mix54_rows"] = sha(PX.MIX54_ROWS)
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


def evaluate(name, cfg, label):
    key = json.dumps(cfg, sort_keys=True)
    log({"status": "STARTED", "key": key, "label": label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        r = score(account(cfg))
    except Exception as e:
        log({"status": "FAILED", "key": key, "error": repr(e)})
        raise
    log({"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "worst_full_month_pct": r["worst_full_month_pct"]})
    return {"name": name, "cfg": cfg, **r}


def run():
    verify_inputs()
    rows = [evaluate(n, c, "고정") for n, c in grid()]
    r1, r2 = pick(rows)
    nb = {}
    for tag, x in (("수익 추천", r1), ("균형 추천", r2)):
        if x and x["name"] != rows[0]["name"]:
            nb[tag] = [{k: v for k, v in evaluate(f"이웃:{json.dumps(c, sort_keys=True)}", c, "이웃").items() if k != "month_pct"} for c in neighbors(x["cfg"])]
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    strip = lambda x: {k: v for k, v in x.items() if k != "month_pct"} if x else None
    print(json.dumps({"recommend_return": strip(r1), "recommend_balance": strip(r2), "base": strip(rows[0]), "neighbors": nb,
                      "rows": [strip(x) for x in rows]}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import alloc as A;"
            "print(json.dumps(A.account(json.loads(os.environ['AL_CFG']))))")
    res = []
    for c in ({"b": "U3_n6", "wb": 0.3, "wc": 0.2}, {"b": "U4_n10", "wb": 0.1, "wc": 0.0}):
        env = dict(os.environ, AL_CFG=json.dumps(c), REG_CUT="")
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
