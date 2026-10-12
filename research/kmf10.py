"""KMF-0010 — 추세 봇(범위 돌파) + 횡보 봇(실패한 돌파 뒤집기 · 덫 봇) · 5분봉 판단 · 1분봉 신호 없음.
사용자 2026-10-13: "목표 10개월에 800p · 추세 횡보에서 각각 작동하는 단타봇 개발" · "천천히: 기본 봇 → 손실 분석 → 줄이기 → 보완 봇".
근거(판정 밖 · KMF-0010/diag): KMF-0009 고른 칸을 나누면 추세 부분 · 되돌림 부분 모두 7 · 8월에 잃음(돌파가 범위 안으로 되돌아온 날) ·
 흔들림 큰 날(앞 5일 폭 ÷ 12p)이 따로 나쁘지는 않음 · 거래량 · 어제 성격으로 추세일을 미리 못 가림.
규칙(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · −12p 봉 안 멈춤 · 그날 마지막 봉 종가 정리 · 1계약 · 편도 0.04p):
  범위 = 그날 첫 N분(N 30 · 60) 고저 · 폭 W
  추세 봇: 종가가 범위 밖으로 b × W 넘게 나가면(b 0.25 · 0.5) 그 방향으로 듦 · 그날 첫 돌파 한 번만 · 장 끝까지
  덫 봇(trap 1일 때만): 추세 봇이 든 뒤 종가가 범위 안으로 R × W(R 0.25 고정) 넘게 되돌아오면(산 경우 위끝 − R×W 이하)
    정리하고 반대로 듦 → 반대쪽 끝(판 경우 아래끝 이하 종가) 닿거나 장 끝에 정리 · 그날 더 안 듦
  trap 0 = 추세 봇만(기준) · 새로 들기는 15:00 판단까지
  격자 8칸: N × b × trap
기간(사전등록): 개발 01-01 ~ 08-31(앞 확인 구간 06 ~ 08을 개발로 씀 · 이미 여러 번 본 구간) · 확인 = 09-01 ~ 10-12(시험 1 구간 · 비독립) · 채택 = 시험 2(10-13부터 새 자료)만
python3 research/kmf10.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf4 as K4  # noqa: E402

ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0010"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf10.py"]
TF = 5
R = 0.25
MIN_TRADES = 60
DEV = ("20260101", "20260831")
VAL = ("20260901", "20261012")
GUARD_BEFORE = "20260901"                 # 검사(kmf_guard)도 개발 자료(09-01 앞)만
BLOCKS = (("20260101", "20260228"), ("20260301", "20260430"), ("20260501", "20260630"), ("20260701", "20260831"))


def grid():
    return [{"bot": "TRAP", "or": n, "b": bb, "trap": t, "tag": f"N{n}_b{bb}_t{t}"} for n in (30, 60) for bb in (0.25, 0.5) for t in (0, 1)]


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return K4.day_start_aligned(rows, TF)


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    i = 0
    while i < n:
        d = b[i][0]
        j = i
        while j < n and b[j][0] == d:
            j += 1
        start = b[i][1] - (TF - 1)
        hi = lo = None
        pos, state = 0, "wait"                    # wait → trend(추세 봇 듦) → trap(덫 봇 듦) → done
        for k in range(i, j):
            m, h, l, c = b[k][1], b[k][3], b[k][4], b[k][5]
            if m < start + cfg["or"]:
                hi = h if hi is None else max(hi, h)
                lo = l if lo is None else min(lo, l)
                continue
            if hi is None or hi <= lo or state == "done":
                continue
            w = hi - lo
            can_enter = m <= K.ENTRY_TO
            if state == "wait":
                if can_enter and c > hi + cfg["b"] * w:
                    want[k], pos, state = 1, 1, "trend"
                elif can_enter and c < lo - cfg["b"] * w:
                    want[k], pos, state = -1, -1, "trend"
            elif state == "trend":
                if cfg["trap"] and ((pos > 0 and c <= hi - R * w) or (pos < 0 and c >= lo + R * w)):
                    if can_enter:
                        want[k], pos, state = -pos, -pos, "trap"
                    else:
                        want[k], pos, state = 0, 0, "done"
            elif state == "trap":
                if (pos < 0 and c <= lo) or (pos > 0 and c >= hi):
                    want[k], pos, state = 0, 0, "done"
        i = j
    return want


def block_sums(d):
    mo = d.get("months", {})
    return [round(sum(v for q, v in mo.items() if a[:6] <= q <= z[:6]), 2) for a, z in BLOCKS]


def eligible(d):
    pos_months = sum(1 for v in d.get("months", {}).values() if v > 0)
    return d.get("days", 0) > 0 and d["total_p"] > 0 and pos_months >= 5 and d["trades"] >= MIN_TRADES


def robust(res, key):
    """살아남기: 1차(합 + · 8달 중 5달 이상 + · 거래 60번 이상) · 앞 반(01 ~ 04) · 뒤 반(05 ~ 08) 모두 + ·
    두 달 묶음 넷 가운데 셋 이상 + · 값 하나만 바꾼 이웃 둘(N · b · 같은 trap) 모두 개발 합 > 0."""
    d = res[key]["dev"]
    if not eligible(d):
        return False
    bl = block_sums(d)
    c = res[key]["cfg"]
    nbs = [g for g in grid() if g["trap"] == c["trap"] and sum(g[x] != c[x] for x in ("or", "b")) == 1]
    return (bl[0] + bl[1] > 0 and bl[2] + bl[3] > 0 and sum(1 for x in bl if x > 0) >= 3
            and all(res[name(g)]["dev"].get("total_p", -1) > 0 for g in nbs))


def val_pass(dev, val):
    """확인(09-01 ~ 10-12 · 비독립): 합 > 0 · 하루 평균 ≥ 개발의 절반 · 가장 나쁜 날 ≥ −12.5p."""
    return (val.get("days", 0) > 0 and val["total_p"] > 0 and val["per_day_p"] >= 0.5 * dev["per_day_p"]
            and val["worst_day_p"] >= K.DAY_STOP - 0.5)


def lock_body():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    body = {f: sha(ROOT / f) for f in CODE_FILES}
    body.update({f"kiwoom-data/{p.name}": sha(p) for p in (K.MINI, K.FUT)})
    return body


def verify_inputs(path=None):
    want = json.loads(Path(path or LOCK).read_text())
    have = lock_body()
    bad = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
    if bad:
        sys.exit("입력 잠금이 다름(멈춤): " + json.dumps(bad, ensure_ascii=False))
    return want


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1)); print(LOCK.read_text())


def log(rec):
    BOX.mkdir(parents=True, exist_ok=True)
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); os.fsync(fh.fileno())


def run():
    """① 개발 8칸(09-01부터 안 읽음) → ② robust 1등 한 칸 → ③ 그 칸만 확인(10-13부터 안 읽음 · 시험 2 자료 안 읽음).
    덫 효과(trap 1 − trap 0)도 같은 N · b끼리 보고(판정 아님) · 목표 800p 대비 하루 평균도 보고(판정 아님)."""
    verify_inputs()
    b = prep(K._rows_before(VAL[0]))
    res = {}
    for cfg in grid():
        log({"status": "STARTED", "key": name(cfg), "stage": "dev", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(b, signals(b, cfg))
        res[name(cfg)] = {"cfg": cfg, "dev": K.stats(days, trades, *DEV)}
        res[name(cfg)]["blocks"] = block_sums(res[name(cfg)]["dev"])
        log({"status": "DONE", "key": name(cfg), "stage": "dev", "dev_total_p": res[name(cfg)]["dev"].get("total_p")})
    trap_effect = {f"N{n}_b{bb}": [round(x - y, 2) for x, y in zip(res[f"N{n}_b{bb}_t1"]["blocks"], res[f"N{n}_b{bb}_t0"]["blocks"])]
                   for n in (30, 60) for bb in (0.25, 0.5)}
    cands = sorted([k for k in res if robust(res, k)], key=lambda k: (-res[k]["dev"]["total_p"], k))
    pick = None
    if cands:
        k = cands[0]
        vb = prep(K._rows_before(K.TEST2_FROM))
        assert max(r[0] for r in vb) <= VAL[1]
        log({"status": "STARTED", "key": k, "stage": "val", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(vb, signals(vb, res[k]["cfg"]))
        pick = {"name": k, "cfg": res[k]["cfg"], "dev": res[k]["dev"], "dev_check": K.stats(days, trades, *DEV)["total_p"],
                "val": K.stats(days, trades, *VAL)}
        pick["val_pass"] = val_pass(pick["dev"], pick["val"])
        log({"status": "DONE", "key": k, "stage": "val", "val_total_p": pick["val"].get("total_p")})
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_rows.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    (BOX / "evidence/pick.json").write_text(json.dumps(pick, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": ("VAL_PASS " + pick["name"]) if pick and pick["val_pass"] else "NO_EDGE", "robust": cands,
                      "trap_effect_blocks_p": trap_effect, "goal_per_day_p": 4.0,
                      "pick": pick and {"name": pick["name"], "dev_total_p": pick["dev"]["total_p"], "dev_per_day_p": pick["dev"]["per_day_p"],
                                        "val_total_p": pick["val"]["total_p"], "val_per_day_p": pick["val"]["per_day_p"], "val_pass": pick["val_pass"]}},
                     ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260504", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf10 as M;"
            "c=json.loads(os.environ['KC']);b=M.prep(K.load());d,_=K.simulate(b,M.signals(b,c));print(json.dumps(d))")
    res = []
    for cfg in grid():
        env = dict(os.environ, KC=json.dumps(cfg), KMF_CUT=VAL[0])
        full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["KMF_CUT"] = ct
            part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in part if d < ct]
            res.append({"cfg": name(cfg), "cut": ct, "days": len(ds), "diff": sum(1 for d in ds if abs(part[d] - full[d]) > 1e-9),
                        "no_future_days": all(d < ct for d in part)})
    print(json.dumps({"pass": all(r["diff"] == 0 and r["no_future_days"] for r in res), "runs": res}, ensure_ascii=False))


if __name__ == "__main__":
    {"lock": write_lock, "cut": cut, "run": run}[sys.argv[1]]()
