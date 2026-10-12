"""KMF-0009 — 추세 · 횡보 두 단타 봇을 장중에 스스로 바꾸는 봇(5분봉 판단 · 1분봉 신호 없음).
사용자 2026-10-13: "목표 10개월에 800p · 추세 횡보에서 각각 작동하는 단타봇 개발".
근거(판정 밖 · 개발 01 ~ 05만 · KMF-0009/diag): 아침 값(첫 60분 ER · 폭 · 갭)으로 추세일 / 횡보일을 미리 못 가림(상관 −0.05 ~ +0.03) ·
 상한(미래 앎): 추세일 돌파 끝까지 +440 · 횡보일 되돌림 +127 · 잘못 고르면 −164 / −95 → 미리 고르지 말고 장중에 바뀌게 함.
규칙(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · −12p 봉 안 멈춤 · 그날 마지막 봉 종가 정리 · 1계약 · 편도 0.04p):
  범위 = 그날 첫 N분(N 30 · 60) 고저 · 폭 W · 가운데 M
  횡보 봇(되돌림): 종가가 범위 위끝 쪽 z × W 안(위끝 − zW ~ 위끝)이면 팖 · 아래끝 쪽이면 삼 · 가운데 닿으면 정리 · z {0.15 · 0.25}
  추세 봇(뒤집기): 종가가 범위 밖으로 b × W 넘게 나가면(위 · 아래) 그 방향으로 듦(되돌림 중이면 정리 뒤 뒤집음) · 장 끝까지 · b {0.25 · 0.5}
  추세 봇이 든 뒤에는 그날 횡보 봇을 다시 켜지 않음 · 새로 들기는 15:00 판단까지
  격자 8칸: N × z × b
python3 research/kmf9.py lock | run | cut"""
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
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0009"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf9.py"]
TF = 5
MIN_TRADES = 30


def grid():
    return [{"bot": "SWITCH", "or": n, "z": z, "b": bb, "tag": f"N{n}_z{z}_b{bb}"} for n in (30, 60) for z in (0.15, 0.25) for bb in (0.25, 0.5)]


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
        pos, mode = 0, "range"                    # mode: range(되돌림 켜짐) · trend(추세 듦 · 되돌림 끔)
        for k in range(i, j):
            m, h, l, c = b[k][1], b[k][3], b[k][4], b[k][5]
            if m < start + cfg["or"]:
                hi = h if hi is None else max(hi, h)
                lo = l if lo is None else min(lo, l)
                continue
            if hi is None or hi <= lo:
                continue
            w = hi - lo
            mid = (hi + lo) / 2
            can_enter = m <= K.ENTRY_TO
            up_break, dn_break = c > hi + cfg["b"] * w, c < lo - cfg["b"] * w
            if mode == "range":
                if (up_break or dn_break) and can_enter:
                    side = 1 if up_break else -1
                    want[k], pos, mode = side, side, "trend"     # 뒤집기 · 장 끝까지
                    continue
                if pos == 0 and can_enter:
                    if hi - cfg["z"] * w <= c <= hi:
                        want[k], pos = -1, -1
                    elif lo <= c <= lo + cfg["z"] * w:
                        want[k], pos = 1, 1
                elif pos != 0 and ((pos < 0 and c <= mid) or (pos > 0 and c >= mid)):
                    want[k], pos = 0, 0
        i = j
    return want


def eligible(d):
    pos_months = sum(1 for v in d.get("months", {}).values() if v > 0)
    return d.get("days", 0) > 0 and d["total_p"] > 0 and pos_months >= 3 and d["trades"] >= MIN_TRADES


def robust(res, key):
    """살아남기: 1차 · 앞 반 · 뒤 반 모두 + · 값 하나만 바꾼 이웃 셋(N · z · b) 모두 개발 합 > 0."""
    d = res[key]["dev"]
    if not eligible(d):
        return False
    mo = d["months"]
    a = sum(v for q, v in mo.items() if q <= "202603"); bb = sum(v for q, v in mo.items() if q >= "202604")
    c = res[key]["cfg"]
    nbs = [g for g in grid() if sum(g[x] != c[x] for x in ("or", "z", "b")) == 1]
    return a > 0 and bb > 0 and all(res[name(g)]["dev"].get("total_p", -1) > 0 for g in nbs)


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
    """① 개발 8칸(06-01부터 안 읽음) → ② robust 1등 한 칸 → ③ 그 칸만 확인(09-01부터 안 읽음) · 목표 800p 대비 하루 평균도 보고(판정 아님)."""
    verify_inputs()
    b = prep(K._rows_before(K.VAL[0]))
    res = {}
    for cfg in grid():
        log({"status": "STARTED", "key": name(cfg), "stage": "dev", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(b, signals(b, cfg))
        res[name(cfg)] = {"cfg": cfg, "dev": K.stats(days, trades, *K.DEV)}
        log({"status": "DONE", "key": name(cfg), "stage": "dev", "dev_total_p": res[name(cfg)]["dev"].get("total_p")})
    cands = sorted([k for k in res if robust(res, k)], key=lambda k: (-res[k]["dev"]["total_p"], k))
    pick = None
    if cands:
        k = cands[0]
        vb = prep(K._rows_before(K.TEST[0]))
        log({"status": "STARTED", "key": k, "stage": "val", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(vb, signals(vb, res[k]["cfg"]))
        pick = {"name": k, "cfg": res[k]["cfg"], "dev": res[k]["dev"], "dev_check": K.stats(days, trades, *K.DEV)["total_p"],
                "val": K.stats(days, trades, *K.VAL)}
        pick["val_pass"] = K.val_pass(pick["dev"], pick["val"])
        log({"status": "DONE", "key": k, "stage": "val", "val_total_p": pick["val"].get("total_p")})
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_rows.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    (BOX / "evidence/pick.json").write_text(json.dumps(pick, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": ("VAL_PASS " + pick["name"]) if pick and pick["val_pass"] else "NO_EDGE", "robust": cands,
                      "goal_per_day_p": 4.0,
                      "pick": pick and {"name": pick["name"], "dev_total_p": pick["dev"]["total_p"], "dev_per_day_p": pick["dev"]["per_day_p"],
                                        "val_total_p": pick["val"]["total_p"], "val_per_day_p": pick["val"]["per_day_p"], "val_pass": pick["val_pass"]}},
                     ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260401", "20260504")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf9 as K9;"
            "c=json.loads(os.environ['KC']);b=K9.prep(K.load());d,_=K.simulate(b,K9.signals(b,c));print(json.dumps(d))")
    res = []
    for cfg in grid():
        env = dict(os.environ, KC=json.dumps(cfg), KMF_CUT=K.VAL[0])
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
