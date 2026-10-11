"""MIX-0053 — 봇 몫까지 함께 다시 고르기(사용자 2026-10-11 "봇 몫까지 함께 다시 골라줘").
1단계(바탕 장부 72판 · z100 · 계좌 흔들림 상한 m1 그대로):
  1일봉 몫 {0.3 · 0.5 · 0.7 · 1.0} × 15분봉 몫 {0.5 · 1.0} × 바구니 몫 {0(뺌) · 0.3 · 0.5} × 빈칸 엔진 · 인버스 {둘 다 · 인버스 뺌 · 둘 다 뺌}
2단계(덧붙임 4가지 × 72 = 288판 · regime_dev): 없음 · 0050 규칙 · 0051 규칙 · 0052 규칙(설정은 각 후보 그대로)
고르기: 세 장 각각 하루 ≥ −15% · 달 ≥ −10%(반올림 전) 안에서 연수익 높은 순. 덧붙임이 있는 칸은 0051과 같은 손실 고원(덧붙임 규칙의 작은 이웃 6개 모두 같은 잣대 안 ·
  더 번 몫 절반 이상)을 넘은 첫 칸이 최종(ROBUST_MIX). 덧붙임 없는 칸이 먼저 오면 그 칸이 최종(이웃 검사 없음 · 덧붙임 규칙이 없으므로).
  봇 몫 축은 몫 축이라 고원에서 뺌(사용자 2026-10-10 정의). 이웃 평가 상한 300판.
보고: 효율(연수익 ÷ |가장 나쁜 달| · 연수익 ÷ |고점 대비|) 상위 · 지금 조합(0.5 · 0.5 · 0.5 · 둘 다 · 덧붙임 없음) 대비.
round 2(GPT #221 · 무결성):
- 1단계: 칸마다 BASES_LOG(STARTED · DONE · FAILED)에 명령 · 환경 · 코드 / 입력 해시를 적음. z100 출력은 .part.csv로 쓰고, 종료 코드 0이며 점검(2,360줄 ·
  첫날 20170201 · 마지막 20260916 · 날짜 고유 · 정렬)을 넘을 때만 .csv로 바꿔 DONE(파일 sha256 포함). 아니면 FAILED · 파일 격리. 다시 돌리면 같은 잠금(코드 · 캐시 해시)의 DONE만 건너뜀.
- round 3: z100 환경은 등록값 allowlist로 고정(ENV_CONTRACT · 부모 환경 안 물려받음 · STARTED에 전부 적음). 잠금 = 코드 해시 + 캐시 + 장부 파일
  (z055_d1_raw · x004_m15_final) + 자료 폴더 HEAD 나무 해시(커밋 안 된 바뀜이 있으면 멈춤) + 환경 계약 해시. 하나라도 바뀌면 옛 DONE을 다시 쓰지 않음.
- 2단계: 72개 모두 같은 잠금의 DONE이고 파일 sha가 기록과 같을 때만 시작. 288 고정 평가와 이웃 평가는 EVALS_LOG에 (바탕 · 덧붙임 설정) 열쇠로 STARTED · DONE · FAILED.
  모든 고정 격자 결과는 evidence/all_rows.json에 씀.
python3 research/mix_run.py bases   → 1단계(4개씩 나란히)
python3 research/mix_run.py select  → 2단계 + 고르기"""
import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
BOX = ROOT / "research-exchange/claude-to-gpt/MIX-0053"
BASES = Path(os.getenv("MIX_BASES", "/tmp/mix0053-bases"))
CACHE = "/tmp/maxret-0026-cache.pkl"
ACC_VOL = "0.010911"
S1D = [0.3, 0.5, 0.7, 1.0]
S15 = [0.5, 1.0]
SBA = [0.0, 0.3, 0.5]
DROPS = ["", "inverse", "engine,inverse"]
NOW = (0.5, 0.5, 0.5, "")
DAY_LIM, MONTH_LIM, NB_CAP = -0.15, -0.10, 300
FIX = {"down_base": 1.0, "down_inv": 0.0, "inv": "114800", "exit_buf": 0.0, "band": None, "up_need": "above_only", "confirm": "r10m5", "lev_vt": None}
OVERLAYS = {"none": None,
            "0050": dict(FIX, n=30, persist=2, up_lev=0.3, side_inv=0.2),
            "0051": dict(FIX, n=24, persist=3, up_lev=0.2, side_inv=0.2),
            "0052": dict(FIX, n=24, persist=3, up_lev=0.25, side_inv=0.3)}


def grid():
    return list(itertools.product(S1D, S15, SBA, DROPS))


def name(g):
    a, b, c, d = g
    return f"d{a}_m{b}_b{c}_x{d.replace(',', '+') or 'none'}"


SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
# round 3(GPT #221): z100 행동을 바꾸는 환경은 모두 등록값으로 고정(부모 환경을 물려받지 않음). 빈 문자열 = 끔(z100 기본과 같음).
ENV_CONTRACT = {"NRL_CACHE": CACHE, "Z_ACC_VOL": ACC_VOL, "Z_FROM": "20170201", "Z_TO": "20260930", "Z_MARGIN": "1.30", "Z_ACC": "1e8",
                "Z_D1_VOL": "0", "Z_LOOK": "20", "Z_ACC_STRICT": "1", "Z_D1_LED": "z055_d1_raw.json", "Z_STOCK_CAP": "0", "Z_PARK": "0",
                "Z_BASKET_BEAR": "0", "Z_STOCK_VOL": "0", "Z_TRIM_BAND": "0"}
ENV_UNSET = ("Z_STOCK_SIDE", "Z_ATTR")          # 없어야 하는 것(있으면 z100 행동이 바뀜)
SYS_KEEP = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR")   # 연구와 무관한 실행 환경만 물려받음
CELL_KEYS = ("Z_SHARE_1D", "Z_SHARE_15M", "Z_SHARE_BASKET", "Z_DROP")


def base_cmd(g, parent=None):
    a, b, c, d = g
    parent = os.environ if parent is None else parent
    drop = ",".join(x for x in [d, "basket" if c == 0.0 else ""] if x)
    env = {k: parent[k] for k in SYS_KEEP if k in parent}
    env.update(ENV_CONTRACT)
    env.update(Z_SHARE_1D=str(a), Z_SHARE_15M=str(b), Z_SHARE_BASKET=str(c), Z_DROP=drop, Z_OUT=str(BASES / f"{name(g)}.csv"),
               PYTHONHASHSEED="0")
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


def within(r):
    return all(k["worst_day_raw"] >= DAY_LIM and k["worst_month_raw"] >= MONTH_LIM for k in r["by_kind"].values())


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
    os.environ.setdefault("REG_BOX", "MIX-0053")
    sys.path.insert(0, str(ROOT / "research"))
    import regime_dev as D
    lk, done = verify_all()                       # 72개 모두 잠금 · 점검 통과해야 시작
    rows = []
    for g in grid():
        for ov, cfg in OVERLAYS.items():
            r = evaluate(g, cfg, D)
            rows.append({"base": name(g), "g": list(g), "overlay": ov, "annual_raw": r["annual_raw"], "annual_pct": r["annual_pct"],
                         "worst_day_pct": r["worst_day_pct"], "worst_month_pct": r["worst_month_pct"], "mdd_report_pct": r["mdd_report_pct"],
                         "within": within(r), "years_pct": r["years_pct"], "halves": r["halves_report"]})
    now = next(x for x in rows if x["g"] == list(NOW) and x["overlay"] == "none")
    ok = sorted([x for x in rows if x["within"]], key=lambda x: (-x["annual_raw"], x["base"], x["overlay"]))
    checked, final, nb_used = [], None, 0
    import regime_rules4 as R4
    for x in ok:
        if x["overlay"] == "none":
            final = x
            checked.append({"cell": x, "robust": "덧붙임 없음(이웃 검사 없음)"})
            break
        cfg = OVERLAYS[x["overlay"]]
        nbs = R4.neighbors(cfg)
        if nb_used + len(nbs) > NB_CAP:
            break
        res, good = {}, True
        for a, v in nbs:
            nr = evaluate(tuple(x["g"]), dict(cfg, **{a: v}), D, label="이웃")
            nb_used += 1
            w = within(nr)
            gain = (nr["annual_raw"] - now["annual_raw"]) >= (x["annual_raw"] - now["annual_raw"]) / 2
            res[f"{a}={v}"] = {"annual_pct": nr["annual_pct"], "worst_month_pct": nr["worst_month_pct"], "within": w, "half_gain": gain}
            good = good and w and gain
        checked.append({"cell": x, "neighbors": res, "robust": good})
        if good:
            final = x
            break
    for x in rows:
        x["eff_month"] = x["annual_pct"] / abs(x["worst_month_pct"]) if x["worst_month_pct"] < 0 else None
        x["eff_mdd"] = x["annual_pct"] / abs(x["mdd_report_pct"]) if x["mdd_report_pct"] < 0 else None
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    out = {"verdict": ("ROBUST_MIX" if final else "NO_MIX"), "final": final, "now": now, "checked": checked, "rows_count": len(rows), "lock": lk,
           "bases_sha256": {k: v["sha256"] for k, v in done.items()},
           "within_count": len(ok), "neighbor_evals": nb_used, "limits": {"day": DAY_LIM, "month": MONTH_LIM},
           "designated_period_gap": "NEEDS_DATA(2016-01 ~ 2017-01 장부 없음)"}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    {"bases": bases, "select": select}[sys.argv[1]]()
