"""MIX-0054 — 15분봉을 빼고 봇 몫 · 덧붙임을 다시 골라 시드를 가장 알차게 쓰기(사용자 2026-10-11 "15m은 빼자 연구기간이 너무 짧아 ·
15m 제외 후 최종 후보와 모의투자 후보로 시드를 최대로 효율적으로 사용하게 해줘 · 셈할 때 지피티도 같이 하여 결과 인정받자").
- 15분봉 장부(x004_m15_final)는 104건 · 2025-09-18 ~ 2026-08-03뿐이라 10년 판정에 쓸 수 없음 → 모든 칸에서 15분봉 뺌(Z_DROP=15m).
1단계(바탕 16판 · z100 · 계좌 흔들림 상한 m1 · 빈칸 엔진 · 인버스 켬 고정 — MIX-0053에서 둘 다 빼면 연 −7%p):
  1일봉 몫 {0.3 · 0.5 · 0.7 · 1.0} × 바구니 몫 {0.3 · 0.5 · 0.7 · 1.0}
2단계(덧붙임 18가지 × 16 = 288판 · regime_dev):
  없음 · 후보 그대로 0049 · 0050 · 0051 규칙(n24 · persist 3 · r10m5)의 몫 격자 레버리지 {0.2 · 0.25 · 0.3 · 0.35 · 0.4} × 횡보 인버스 {0.2 · 0.3 · 0.4}
  (0051 = 0.2 · 0.2 · 0052 = 0.25 · 0.3이 격자 안). 15분봉을 빼서 늘어난 놀던 돈을 덧붙임이 쓸 수 있으므로 레버리지 몫을 0.4까지 넓힘.
고르기: MIX-0053과 같음 — 세 장 각각 하루 ≥ −15% · 달 ≥ −10%(반올림 전) 안에서 연수익 높은 순. 덧붙임이 있는 칸은 규칙 이웃 6개
  (n × 0.85 · × 1.15 · persist ± 1 · r10m4 · r10m6) 모두 같은 잣대 안 · 더 번 몫(15분봉만 뺀 지금 몫 · 덧붙임 없음 대비) 절반 이상을 넘은 첫 칸이 최종(ROBUST_MIX).
  덧붙임 없는 칸이 먼저 오면 그 칸이 최종. 몫 축(봇 몫 · 레버리지 · 인버스 몫)은 고원에서 뺌(사용자 2026-10-10 정의). 이웃 평가 상한 300판.
보고(판정 밖): 효율(연수익 ÷ |가장 나쁜 달|) · 돈 쓰임(바탕 장부 1 − 현금 ÷ NAV 평균) · MIX-0053 최종(15분봉 포함 29.321%) 대비 · 축별 평균.
무결성: MIX-0053 round 3과 같음(환경 등록값 고정 · 코드 · 캐시 · 장부 · 자료 폴더 나무 · 환경 계약 잠금 · .part 점검 뒤 DONE · 72 → 16개 선검증 · 평가 기록).
python3 research/mix54_run.py bases   → 1단계(4개씩 나란히)
python3 research/mix54_run.py select  → 2단계 + 고르기"""
import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
BOX = ROOT / "research-exchange/claude-to-gpt/MIX-0054"
BASES = Path(os.getenv("MIX_BASES", "/tmp/mix0054-bases"))
CACHE = "/tmp/maxret-0026-cache.pkl"
ACC_VOL = "0.010911"
S1D = [0.3, 0.5, 0.7, 1.0]
SBA = [0.3, 0.5, 0.7, 1.0]
NOW = (0.5, 0.5)                     # 15분봉만 뺀 지금 몫(1일봉 0.5 · 바구니 0.5)
DAY_LIM, MONTH_LIM, NB_CAP = -0.15, -0.10, 300
# round 2(GPT #223): 달 잣대 두 갈래를 같은 무게로 함께 판정 · 보고 — T10 = 사용자 2026-10-10 '가장 나쁜 달 −10% 이내로 몫 다시 골라줘'(0050 ~ 0053과 같음) ·
# T15 = 사용자 2026-10-07 손실 한도(하루 · 달 각각 −15%). 어느 쪽을 쓸지는 사용자가 정함. 이웃 평가 상한은 갈래마다 300(같은 이웃은 한 번만 셈 · 기록).
TRACKS = {"T10": -0.10, "T15": -0.15}
FIX = {"down_base": 1.0, "down_inv": 0.0, "inv": "114800", "exit_buf": 0.0, "band": None, "up_need": "above_only", "confirm": "r10m5", "lev_vt": None}
RULE = dict(FIX, n=24, persist=3)
OVERLAYS = {"none": None,
            "0049": dict(FIX, n=30, persist=2, up_lev=0.8, side_inv=0.2, lev_vt=0.25),
            "0050": dict(FIX, n=30, persist=2, up_lev=0.3, side_inv=0.2)}
for _lev in (0.2, 0.25, 0.3, 0.35, 0.4):
    for _side in (0.2, 0.3, 0.4):
        OVERLAYS[f"L{_lev}_S{_side}"] = dict(RULE, up_lev=_lev, side_inv=_side)


def grid():
    return list(itertools.product(S1D, SBA))


def name(g):
    a, c = g
    return f"d{a}_b{c}_no15m"


SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
# round 3(GPT #221): z100 행동을 바꾸는 환경은 모두 등록값으로 고정(부모 환경을 물려받지 않음). 빈 문자열 = 끔(z100 기본과 같음).
ENV_CONTRACT = {"NRL_CACHE": CACHE, "Z_ACC_VOL": ACC_VOL, "Z_FROM": "20170201", "Z_TO": "20260930", "Z_MARGIN": "1.30", "Z_ACC": "1e8",
                "Z_D1_VOL": "0", "Z_LOOK": "20", "Z_ACC_STRICT": "1", "Z_D1_LED": "z055_d1_raw.json", "Z_STOCK_CAP": "0", "Z_PARK": "0",
                "Z_BASKET_BEAR": "0", "Z_STOCK_VOL": "0", "Z_TRIM_BAND": "0"}
ENV_UNSET = ("Z_STOCK_SIDE", "Z_ATTR")          # 없어야 하는 것(있으면 z100 행동이 바뀜)
SYS_KEEP = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR")   # 연구와 무관한 실행 환경만 물려받음
CELL_KEYS = ("Z_SHARE_1D", "Z_SHARE_15M", "Z_SHARE_BASKET", "Z_DROP")


def base_cmd(g, parent=None):
    a, c = g
    parent = os.environ if parent is None else parent
    env = {k: parent[k] for k in SYS_KEEP if k in parent}
    env.update(ENV_CONTRACT)
    env.update(Z_SHARE_1D=str(a), Z_SHARE_15M="0.5", Z_SHARE_BASKET=str(c), Z_DROP="15m", Z_OUT=str(BASES / f"{name(g)}.csv"),
               PYTHONHASHSEED="0")          # Z_SHARE_15M은 15분봉을 빼서 쓰이지 않음(고정값으로 둠)
    assert not any(k in env for k in ENV_UNSET)
    return env


def research_env(env):
    """STARTED에 적는 연구 환경(시스템 경로 빼고 전부)."""
    return {k: v for k, v in sorted(env.items()) if k not in SYS_KEEP}


BASES_LOG = BOX / "bases.jsonl"
EVALS_LOG = BOX / "evals.jsonl"
N_ROWS, FIRST, LAST = 2360, "20170201", "20260916"


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


DATA_DIRS = sorted(x.name for x in ROOT.iterdir() if x.is_dir() and (x.name.endswith("-data") or x.name in ("basket-live", "idle-live")))
SP_FILES = ("z055_d1_raw.json", "x004_m15_final.json")


def code_files():
    """z100이 불러올 수 있는 코드: 루트 *.py 전부 + research의 z100 · z001 · perf2 · idle_signal + 얼린 봇 판."""
    fs = sorted(p.name for p in ROOT.glob("*.py"))
    fs += ["research/z100.py", "research/z001.py", "research/perf2.py", "research/idle_signal.py"]
    fs += sorted(f"research/mix0053/{p.name}" for p in (ROOT / "research/mix0053").glob("*.py"))
    return fs


def data_trees(root=ROOT):
    """자료 폴더마다 HEAD 나무 해시. 고치지 않은 파일이 있으면 멈춤(나무 해시가 실제 파일과 다를 수 있으므로)."""
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", *DATA_DIRS], capture_output=True, text=True).stdout.strip()
    if dirty:
        sys.exit("자료 폴더에 커밋 안 된 바뀜이 있음(멈춤): " + dirty[:300])
    return {d: subprocess.run(["git", "-C", str(root), "rev-parse", f"HEAD:{d}"], capture_output=True, text=True).stdout.strip() for d in DATA_DIRS}


def env_hash():
    import hashlib
    body = {"contract": ENV_CONTRACT, "unset": list(ENV_UNSET), "cell_keys": list(CELL_KEYS), "PYTHONHASHSEED": "0"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def lock():
    out = {f: sha(ROOT / f) for f in code_files()}
    out[CACHE] = sha(CACHE)
    out.update({f"SP/{f}": sha(SP / f) for f in SP_FILES})
    out.update({f"tree:{d}": h for d, h in data_trees().items()})
    out["env_contract"] = env_hash()
    return out


def log(path, rec):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def check_csv(p):
    import csv
    rows = list(csv.DictReader(open(p)))
    ds = [r["날"] for r in rows]
    ok = len(rows) == N_ROWS and ds[0] == FIRST and ds[-1] == LAST and len(set(ds)) == len(ds) and ds == sorted(ds)
    return ok, {"rows": len(rows), "first": ds[0] if ds else None, "last": ds[-1] if ds else None, "unique": len(set(ds)) == len(ds), "sorted": ds == sorted(ds)}


def done_bases(lk):
    if not BASES_LOG.exists():
        return {}
    out = {}
    for r in map(json.loads, BASES_LOG.read_text().splitlines()):
        if r["status"] == "DONE" and r["lock"] == lk:
            out[r["cell"]] = r
    return out


def bases():
    BASES.mkdir(parents=True, exist_ok=True)
    lk = lock()
    done = done_bases(lk)
    todo = [g for g in grid() if name(g) not in done or not (BASES / f"{name(g)}.csv").exists() or sha(BASES / f"{name(g)}.csv") != done[name(g)]["sha256"]]
    running = []
    while todo or running:
        while todo and len(running) < 4:
            g = todo.pop(0)
            env = base_cmd(g)
            part = BASES / f"{name(g)}.part.csv"
            if part.exists():
                part.unlink()
            env["Z_OUT"] = str(part)
            keep = research_env(env)
            log(BASES_LOG, {"status": "STARTED", "cell": name(g), "g": list(g), "env": keep, "lock": lk, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
            lg = open(BASES / f"{name(g)}.log", "w")
            running.append((g, part, subprocess.Popen([sys.executable, str(ROOT / "research/z100.py")], env=env, cwd=ROOT, stdout=lg, stderr=subprocess.STDOUT)))
        time.sleep(5)
        for g, part, p in list(running):
            if p.poll() is None:
                continue
            running.remove((g, part, p))
            final = BASES / f"{name(g)}.csv"
            if p.returncode == 0 and part.exists():
                ok, info = check_csv(part)
            else:
                ok, info = False, {"missing_or_rc": p.returncode}
            if ok:
                part.rename(final)
                log(BASES_LOG, {"status": "DONE", "cell": name(g), "rc": p.returncode, "lock": lk, "sha256": sha(final), **info})
            else:
                if part.exists():
                    part.rename(BASES / f"{name(g)}.failed.csv")
                log(BASES_LOG, {"status": "FAILED", "cell": name(g), "rc": p.returncode, "lock": lk, **info})
            print(time.strftime("%H:%M:%S"), name(g), "끝" if ok else "실패", p.returncode, flush=True)


def verify_all():
    lk = lock()
    done = done_bases(lk)
    bad = [name(g) for g in grid() if name(g) not in done or not (BASES / f"{name(g)}.csv").exists() or sha(BASES / f"{name(g)}.csv") != done[name(g)]["sha256"]]
    if bad:
        sys.exit(f"바탕 장부 {len(bad)}개가 잠금 · 점검을 못 넘음(멈춤): {bad[:5]}")
    return lk, done


def money_use(g):
    """보고 전용: 바탕 장부의 돈 쓰임 = 평균(1 − 현금 ÷ NAV)."""
    import csv
    rows = list(csv.DictReader(open(BASES / f"{name(g)}.csv")))
    return sum(1 - float(r["현금"]) / float(r["NAV"]) for r in rows) / len(rows)


def within(r, month=MONTH_LIM):
    return all(k["worst_day_raw"] >= DAY_LIM and k["worst_month_raw"] >= month for k in r["by_kind"].values())


def evaluate(g, ov_cfg, D, label="고정"):
    key = json.dumps({"base": name(g), "overlay": ov_cfg}, sort_keys=True, ensure_ascii=False)
    log(EVALS_LOG, {"status": "STARTED", "key": key, "label": label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        D.BASE_CSV = BASES / f"{name(g)}.csv"
        if D.DATA is None or getattr(D, "_mix_base", None) != str(D.BASE_CSV):
            D.DATA, D.FEAT = None, None
            D._mix_base = str(D.BASE_CSV)
        cfg = dict(D.R0) if ov_cfg is None else dict(D.R0, **ov_cfg)
        r = D.stats(*D.account(cfg))
    except Exception as e:
        log(EVALS_LOG, {"status": "FAILED", "key": key, "error": repr(e)})
        raise
    log(EVALS_LOG, {"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "worst_day_pct": r["worst_day_pct"], "worst_month_pct": r["worst_month_pct"]})
    return r


def select():
    os.environ.setdefault("REG_BOX", "MIX-0054")
    sys.path.insert(0, str(ROOT / "research"))
    import regime_dev as D
    lk, done = verify_all()                       # 16개 모두 잠금 · 점검 통과해야 시작
    rows = []
    for g in grid():
        for ov, cfg in OVERLAYS.items():
            r = evaluate(g, cfg, D)
            rows.append({"base": name(g), "g": list(g), "overlay": ov, "annual_raw": r["annual_raw"], "annual_pct": r["annual_pct"],
                         "worst_day_pct": r["worst_day_pct"], "worst_month_pct": r["worst_month_pct"], "mdd_report_pct": r["mdd_report_pct"],
                         "within": {tk: within(r, m) for tk, m in TRACKS.items()}, "years_pct": r["years_pct"], "halves": r["halves_report"],
                         "by_kind": {k: {"worst_day_pct": round(v["worst_day_raw"] * 100, 3), "worst_month_pct": round(v["worst_month_raw"] * 100, 3)} for k, v in r["by_kind"].items()},
                         "base_money_use": money_use(g)})
    now = next(x for x in rows if tuple(x["g"]) == NOW and x["overlay"] == "none")
    import regime_rules4 as R4
    memo, tracks = {}, {}
    for tk, mlim in TRACKS.items():
        ok = sorted([x for x in rows if x["within"][tk]], key=lambda x: (-x["annual_raw"], x["base"], x["overlay"]))
        checked, final, nb_used = [], None, 0
        for x in ok:
            if x["overlay"] == "none":
                final = x
                checked.append({"cell": x["base"] + "+" + x["overlay"], "robust": "덧붙임 없음(이웃 검사 없음)"})
                break
            cfg = OVERLAYS[x["overlay"]]
            nbs = R4.neighbors(cfg)
            if nb_used + len(nbs) > NB_CAP:
                break
            res, good = {}, True
            for a, v in nbs:
                ncfg = dict(cfg, **{a: v})
                mk = json.dumps({"base": x["base"], "overlay": ncfg}, sort_keys=True, ensure_ascii=False)
                if mk not in memo:
                    memo[mk] = evaluate(tuple(x["g"]), ncfg, D, label="이웃")
                nr = memo[mk]
                nb_used += 1
                w = within(nr, mlim)
                gain = (nr["annual_raw"] - now["annual_raw"]) >= (x["annual_raw"] - now["annual_raw"]) / 2
                res[f"{a}={v}"] = {"annual_pct": nr["annual_pct"], "worst_day_pct": nr["worst_day_pct"], "worst_month_pct": nr["worst_month_pct"], "within": w, "half_gain": gain}
                good = good and w and gain
            checked.append({"cell": x["base"] + "+" + x["overlay"], "annual_pct": x["annual_pct"], "worst_month_pct": x["worst_month_pct"], "neighbors": res, "robust": good})
            if good:
                final = x
                break
        tracks[tk] = {"month_limit": mlim, "verdict": ("ROBUST_MIX" if final else "NO_MIX"), "final": final, "checked": checked,
                      "within_count": len(ok), "neighbor_checks": nb_used}
    for x in rows:
        x["eff_month"] = x["annual_pct"] / abs(x["worst_month_pct"]) if x["worst_month_pct"] < 0 else None
        x["eff_mdd"] = x["annual_pct"] / abs(x["mdd_report_pct"]) if x["mdd_report_pct"] < 0 else None
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    out = {"tracks": tracks, "now": now, "rows_count": len(rows), "lock": lk,
           "bases_sha256": {k: v["sha256"] for k, v in done.items()},
           "neighbor_evals_unique": len(memo), "limits": {"day": DAY_LIM, "month": TRACKS},
           "period_note": "덧붙임 판정 구간 2017-02-01 ~ 2026-09-15(regime_dev LO · HI 고정) · 바탕 장부는 20260916 줄까지 있어 점검은 그 줄까지(마지막 하루는 판정에 안 씀)",
           "designated_period_gap": "NEEDS_DATA(2016-01 ~ 2017-01 장부 없음)", "mix0053_final_with_15m_annual_pct": 29.321}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    {"bases": bases, "select": select}[sys.argv[1]]()
