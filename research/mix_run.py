"""MIX-0053 — 봇 몫까지 함께 다시 고르기(사용자 2026-10-11 "봇 몫까지 함께 다시 골라줘").
1단계(바탕 장부 72판 · z100 · 계좌 흔들림 상한 m1 그대로):
  1일봉 몫 {0.3 · 0.5 · 0.7 · 1.0} × 15분봉 몫 {0.5 · 1.0} × 바구니 몫 {0(뺌) · 0.3 · 0.5} × 빈칸 엔진 · 인버스 {둘 다 · 인버스 뺌 · 둘 다 뺌}
2단계(덧붙임 4가지 × 72 = 288판 · regime_dev): 없음 · 0050 규칙 · 0051 규칙 · 0052 규칙(설정은 각 후보 그대로)
고르기: 세 장 각각 하루 ≥ −15% · 달 ≥ −10%(반올림 전) 안에서 연수익 높은 순. 덧붙임이 있는 칸은 0051과 같은 손실 고원(덧붙임 규칙의 작은 이웃 6개 모두 같은 잣대 안 ·
  더 번 몫 절반 이상)을 넘은 첫 칸이 최종(ROBUST_MIX). 덧붙임 없는 칸이 먼저 오면 그 칸이 최종(이웃 검사 없음 · 덧붙임 규칙이 없으므로).
  봇 몫 축은 몫 축이라 고원에서 뺌(사용자 2026-10-10 정의). 이웃 평가 상한 300판.
보고: 효율(연수익 ÷ |가장 나쁜 달| · 연수익 ÷ |고점 대비|) 상위 · 지금 조합(0.5 · 0.5 · 0.5 · 둘 다 · 덧붙임 없음) 대비.
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


def base_cmd(g):
    a, b, c, d = g
    drop = ",".join(x for x in [d, "basket" if c == 0.0 else ""] if x)
    env = dict(os.environ, NRL_CACHE=CACHE, Z_ACC_VOL=ACC_VOL, Z_SHARE_1D=str(a), Z_SHARE_15M=str(b), Z_SHARE_BASKET=str(c),
               Z_DROP=drop, Z_OUT=str(BASES / f"{name(g)}.csv"))
    return env


def bases():
    BASES.mkdir(parents=True, exist_ok=True)
    todo = [g for g in grid() if not (BASES / f"{name(g)}.csv").exists()]
    running = []
    while todo or running:
        while todo and len(running) < 4:
            g = todo.pop(0)
            log = open(BASES / f"{name(g)}.log", "w")
            running.append((g, subprocess.Popen([sys.executable, str(ROOT / "research/z100.py")], env=base_cmd(g), cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)))
        time.sleep(5)
        for g, p in list(running):
            if p.poll() is not None:
                running.remove((g, p))
                print(time.strftime("%H:%M:%S"), name(g), "끝", p.returncode, flush=True)


def within(r):
    return all(k["worst_day_raw"] >= DAY_LIM and k["worst_month_raw"] >= MONTH_LIM for k in r["by_kind"].values())


def evaluate(g, ov_cfg, D):
    D.BASE_CSV = BASES / f"{name(g)}.csv"
    if D.DATA is None or getattr(D, "_mix_base", None) != str(D.BASE_CSV):
        D.DATA, D.FEAT = None, None
        D._mix_base = str(D.BASE_CSV)
    cfg = dict(D.R0) if ov_cfg is None else dict(D.R0, **ov_cfg)
    return D.stats(*D.account(cfg))


def select():
    os.environ.setdefault("REG_BOX", "MIX-0053")
    sys.path.insert(0, str(ROOT / "research"))
    import regime_dev as D
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
            nr = evaluate(tuple(x["g"]), dict(cfg, **{a: v}), D)
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
    out = {"verdict": ("ROBUST_MIX" if final else "NO_MIX"), "final": final, "now": now, "checked": checked, "rows": rows,
           "within_count": len(ok), "neighbor_evals": nb_used, "limits": {"day": DAY_LIM, "month": MONTH_LIM},
           "designated_period_gap": "NEEDS_DATA(2016-01 ~ 2017-01 장부 없음)"}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    {"bases": bases, "select": select}[sys.argv[1]]()
