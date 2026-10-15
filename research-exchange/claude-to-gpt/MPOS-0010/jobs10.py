"""MPOS-0010 일감 만들기(셈 순서 · 환경만 · 판정 코드와 분리 → 판정 한 줄 고침에 장부를 다시 만들지 않음 · rxkit ②)."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
WORK = SP / "mpos10"
TREE = SP / "m54tree"
LED, BASES = WORK / "ledgers", WORK / "bases"
OLD_N = 495
KS, HS, XC = (0.5, 1.0, 1.5), (10, 20), 0.0025
CELLS = [f"RM_K{k}_H{h}" for k in KS for h in HS]               # 후보 6
CENTER = "RM_K1.0_H20"
AB = ["AB_TOTAL", "AB_NOPULL"]                                  # 빼기 2(K1.0 · H20)
XS = [c + "_X" for c in CELLS]                                  # 계획 청산 손익 깎기 6
ALL = CELLS + AB + XS                                           # 결합 계좌 14
SOLO = CELLS + AB                                               # 혼자 계좌 8
CUTS = ("20211231", "20240628")
SYS_KEEP = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR")
NRL_CACHE = "/tmp/maxret-0026-cache.pkl"
ENV_CONTRACT = {"NRL_CACHE": NRL_CACHE, "Z_ACC_VOL": "0.010911", "Z_FROM": "20170201", "Z_TO": "20260930", "Z_MARGIN": "1.30", "Z_ACC": "1e8",
                "Z_D1_VOL": "0", "Z_LOOK": "20", "Z_ACC_STRICT": "1", "Z_STOCK_CAP": "0", "Z_PARK": "0", "Z_BASKET_BEAR": "0",
                "Z_STOCK_VOL": "0", "Z_TRIM_BAND": "0", "Z_SHARE_1D": "0.5", "Z_SHARE_15M": "0.5", "Z_SHARE_BASKET": "0.3", "PYTHONHASHSEED": "0"}


def door_args(c, cut=None):
    if c == "AB_TOTAL":
        a, nm = ["rm", "1.0", "20", "total"], "rm_total_K1.0_H20"
    elif c == "AB_NOPULL":
        a, nm = ["rm", "1.0", "20", "nopull"], "rm_nopull_K1.0_H20"
    else:
        x = c.endswith("_X")
        k, h = c.split("_")[1][1:], c.split("_")[2][1:]
        a, nm = ["rm", k, h, "rm"], f"rm_rm_K{k}_H{h}"
        if x:
            a, nm = a + [str(XC)], nm + f"_x{XC}"
    if cut:
        a = (a + ["0"] if len(a) == 4 else a) + [cut]
        nm += f"_cut{cut}"
    return a, nm


def ledger(c, cut=None):
    return LED / (door_args(c, cut)[1] + ".json")


def sysenv():
    return {k: os.environ[k] for k in SYS_KEEP if k in os.environ}


def tree_cmd(mods, script, *args):
    return [sys.executable, str(HERE / "tree_run.py"), str(mods), str(script), *args]


def z100_env(led, out, drop="15m"):
    e = dict(sysenv())
    e.update(ENV_CONTRACT)
    e.update(Z_DROP=drop, Z_D1_LED=str(led), Z_OUT=str(out))
    return e


def door_env(cut=None):
    e = dict(sysenv())
    e.update(NRL_CACHE=NRL_CACHE, PYTHONHASHSEED="0")
    if cut:
        e["Z_CUT"] = cut                                            # z001 가격 · 시총 표를 자른 날 뒤 처음부터 안 읽음(반대 검토 결함 9)
    return e


def cost_path(c):
    return LED / (door_args(c)[1] + ".cost.json")


def build_jobs():
    out = {}
    for c in ALL:
        a, nm = door_args(c)
        out[f"build:{c}"] = dict(cmd=tree_cmd(WORK / f"{nm}.mods.json", HERE / "door.py", *a), env=door_env(), cwd=str(TREE), out=str(WORK / f"{nm}.log"),
                                 clean=[str(LED / f"{nm}.json"), str(LED / f"{nm}.meta.json"), str(WORK / f"{nm}.mods.json")])
    return out


def solo_path(c):
    return LED / (door_args(c)[1] + "_solo.json")


def bases_jobs():
    out = {}
    for c in ALL:
        out[f"bases:{c}"] = dict(cmd=tree_cmd(BASES / f"{c}.mods.json", "research/z100.py"), env=z100_env(ledger(c), BASES / f"{c}.csv"), cwd=str(TREE),
                                 out=str(BASES / f"{c}.log"), after=[f"build:{c}"], clean=[str(BASES / f"{c}.csv"), str(BASES / f"{c}.mods.json")])
    for c in CELLS + AB:                                              # 추정 비용(계좌 NAV로 주문 크기 · 반대 검토 결함 2)
        nm = door_args(c)[1]
        out[f"cost:{c}"] = dict(cmd=tree_cmd(WORK / f"{nm}.cost.mods.json", HERE / "cost10.py", str(ledger(c)), str(LED / f"{nm}.meta.json"),
                                             str(BASES / f"{c}.csv"), str(cost_path(c))), env=door_env(), cwd=str(TREE),
                                out=str(WORK / f"{nm}.cost.log"), after=[f"bases:{c}"], clean=[str(cost_path(c))])
    for c in SOLO:
        out[f"solo:{c}"] = dict(cmd=[sys.executable, str(HERE / "jobs10.py"), "solo", c], env=sysenv(), cwd=str(HERE), out=str(WORK / f"{c}_solo.log"),
                                after=[f"build:{c}"], clean=[str(solo_path(c))])
        out[f"bases:{c}_SOLO"] = dict(cmd=tree_cmd(BASES / f"{c}_SOLO.mods.json", "research/z100.py"),
                                      env=z100_env(solo_path(c), BASES / f"{c}_SOLO.csv", "15m,basket,engine,inverse"), cwd=str(TREE),
                                      out=str(BASES / f"{c}_SOLO.log"), after=[f"solo:{c}"], clean=[str(BASES / f"{c}_SOLO.csv"), str(BASES / f"{c}_SOLO.mods.json")])
    return out


def cut_jobs():
    out = {}
    for c in CELLS + AB:
        for ct in CUTS:
            a, nm = door_args(c, ct)
            out[f"cutled:{c}@{ct}"] = dict(cmd=tree_cmd(WORK / f"{nm}.mods.json", HERE / "door.py", *a), env=door_env(ct), cwd=str(TREE),
                                           out=str(WORK / f"{nm}.log"), clean=[str(LED / f"{nm}.json"), str(LED / f"{nm}.meta.json")])
            out[f"cutacct:{c}@{ct}"] = dict(cmd=tree_cmd(BASES / f"{c}_cut{ct}.mods.json", "research/z100.py"),
                                            env=z100_env(ledger(c, ct), BASES / f"{c}_cut{ct}.csv"), cwd=str(TREE), out=str(BASES / f"{c}_cut{ct}.log"),
                                            after=[f"cutled:{c}@{ct}"], clean=[str(BASES / f"{c}_cut{ct}.csv"), str(BASES / f"{c}_cut{ct}.mods.json")])
    return out


def smoke_jobs():
    """마른 실행의 실제 짧은 일감(반대 검토 결함 6): 자른 장부 하나 + 원래 1일봉 장부로 z100을 2017-06까지."""
    a, nm = door_args(CENTER, "20170630")
    for f in (LED / f"{nm}.json", LED / f"{nm}.meta.json", WORK / "smoke_door.mods.json", WORK / "smoke_z100.csv", WORK / "smoke_z100.mods.json"):
        if f.exists():
            f.unlink()                                                  # 지난 실행 잔재가 '기대 산출물 있음'으로 오인되지 않게
    return {"smoke:door": dict(cmd=tree_cmd(WORK / "smoke_door.mods.json", HERE / "door.py", *a), env=door_env("20170630"), cwd=str(TREE),
                               expect=[str(LED / f"{nm}.json"), str(LED / f"{nm}.meta.json")], mods=str(WORK / "smoke_door.mods.json")),
            "smoke:z100": dict(cmd=tree_cmd(WORK / "smoke_z100.mods.json", "research/z100.py"),
                               env=dict(z100_env(SP / "z055_d1_raw.json", WORK / "smoke_z100.csv"), Z_TO="20170630"), cwd=str(TREE),
                               expect=[str(WORK / "smoke_z100.csv")], mods=str(WORK / "smoke_z100.mods.json"))}


if __name__ == "__main__" and sys.argv[1] == "solo":
    import json
    c = sys.argv[2]
    json.dump(json.load(open(ledger(c)))[OLD_N:], open(solo_path(c), "w"))
