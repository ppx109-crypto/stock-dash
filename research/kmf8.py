"""KMF-0008 — 단타 기본 봇: 아침 범위 돌파 단타(5분봉 판단 · 1분봉 신호 없음).
사용자 2026-10-13 "단타개발"(질문 답 · RNA만으로는 하루 안 방향을 못 맞힌다는 결과 뒤).
근거: KMF-0001 ~ 0007에서 살아남은 신호는 '아침 범위 돌파 방향' 하나 · 이를 짧게 들고 빨리 나오는 단타로 바꿈.
규칙(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · −12p 봉 안 멈춤 · 그날 마지막 봉 종가 정리 · 1계약 · 편도 0.04p):
  범위 = 그날 첫 N분(N 30 · 60) 고저 · 폭 W
  들기: 5분봉 종가가 범위 위면 삼 · 아래면 팖(하루 2번까지 · 15:00 판단까지)
  나오기(먼저 오는 것): ① 목표 — 종가가 들기 기준(범위 끝) 대비 k × W 넘게 유리(k 0.5 · 1.0) ② 멈춤 — 종가가 범위 가운데를 넘어 되돌아옴
                        ③ 시간 — 든 뒤 H분(H 60 · 120) 지난 봉 종가 ④ 장 끝 · −12p
  목표 · 멈춤은 범위 폭에 맞춘 상대 잣대(포인트 고정 아님 · KMF-0003 교훈).
python3 research/kmf8.py lock | run | cut"""
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
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0008"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf8.py"]
TF = 5
MIN_TRADES = 30


def grid():
    return [{"bot": "ORBS", "or": n, "k": k, "hold": h, "tag": f"N{n}_k{k}_H{h}"} for n in (30, 60) for k in (0.5, 1.0) for h in (60, 120)]


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
        pos, entries, t0, ref = 0, 0, None, None
        for k in range(i, j):
            m, h, l, c = b[k][1], b[k][3], b[k][4], b[k][5]
            if m < start + cfg["or"]:
                hi = h if hi is None else max(hi, h)
                lo = l if lo is None else min(lo, l)
                continue
            if hi is None:
                continue
            w = hi - lo
            mid = (hi + lo) / 2
            if pos == 0:
                if entries < 2 and m <= K.ENTRY_TO:
                    if c > hi:
                        want[k], pos, entries, t0, ref = 1, 1, entries + 1, m, hi
                    elif c < lo:
                        want[k], pos, entries, t0, ref = -1, -1, entries + 1, m, lo
                continue
            target = pos * (c - ref) >= cfg["k"] * w
            back = (pos > 0 and c < mid) or (pos < 0 and c > mid)
            timeout = m - t0 >= cfg["hold"]
            if target or back or timeout:
                want[k], pos = 0, 0
        i = j
    return want


def eligible(d):
    pos_months = sum(1 for v in d.get("months", {}).values() if v > 0)
    return d.get("days", 0) > 0 and d["total_p"] > 0 and pos_months >= 3 and d["trades"] >= MIN_TRADES


def robust(res, key):
    """살아남기: 1차 조건 · 개발 앞 반 · 뒤 반 모두 + · 값 하나만 바꾼 이웃 셋(N · k · H)이 모두 개발 합 > 0."""
    d = res[key]["dev"]
    if not eligible(d):
        return False
    mo = d["months"]
    a = sum(v for q, v in mo.items() if q <= "202603"); bb = sum(v for q, v in mo.items() if q >= "202604")
    c = res[key]["cfg"]
    nbs = [g for g in grid() if sum(g[x] != c[x] for x in ("or", "k", "hold")) == 1]
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
    """① 개발 8칸(06-01부터 안 읽음) → ② robust 1등 한 칸 → ③ 그 칸만 확인(09-01부터 안 읽음)."""
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
                      "pick": pick and {"name": pick["name"], "dev_total_p": pick["dev"]["total_p"], "dev_check": pick["dev_check"],
                                        "val_total_p": pick["val"]["total_p"], "val_pass": pick["val_pass"]}}, ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260401", "20260504")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf8 as K8;"
            "c=json.loads(os.environ['KC']);b=K8.prep(K.load());d,_=K.simulate(b,K8.signals(b,c));print(json.dumps(d))")
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
