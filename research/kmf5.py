"""KMF-0005 — 15분봉 아침 범위 돌파 · 장 끝까지 들고 가기(1분봉 신호 없음) + 일봉 RNA 역추세금지 시험.
사용자 2026-10-13: "1분봉은 하지말자" · "변화에도 살아남을수있게 rna위주로" · "역추세금지".
근거(판정 밖 · 개발 기간만 · KMF-0005/diag): ① 아침 RNA 상태(15 · 30 · 60분봉)는 그날 남은 방향을 못 맞힘(맞힘 46 ~ 53%)
 ② 15분봉 종가 판단 · 60분 범위 · 하루 1번 · 장 끝까지 = 개발 +202.76p(1분봉판 KMF-0002 +191.84p와 비슷) — 이 한 칸은 사전등록 전에 개발 값을 봄(숨기지 않음)
 ③ 일봉 RNA와 같은 방향 돌파 +77.66p · 반대 방향 +134.14p(46일 · 판정 밖 · 반대 방향만 고르는 칸은 넣지 않음).
규칙(15분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · −12p 봉 안 멈춤 · 그날 마지막 봉 종가 정리):
  범위 = 그날 첫 N분(N 30 · 60) 고저 → 그 뒤 15분봉 종가가 위면 삼 · 아래면 팖 · 장 끝까지 들고 감
  멈춤 day = −12p만 · range = 종가가 반대쪽 범위를 넘으면 정리 · 하루 들기 1 · 2번
  RNA(역추세금지): 일봉 RNA(앞 날 15:29 종가들의 EMA 3 · 5 · 10 · 20 · 배열 점수 ≥ 2이고 10선 3일 기울기 > 0 = 오름 · 점수 ≤ 1이고 < 0 = 내림 · 나머지 섞임)
   → 오름이면 위 돌파만 · 내림이면 아래 돌파만 · 섞임 · 셈 전이면 안 듦
python3 research/kmf5.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf4 as K4  # noqa: E402  (day_start_aligned · 늦게 연 날 · 15:29까지)

ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0005"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf5.py"]
TF = 15
MIN_TRADES = 30


def grid():
    g = []
    for n in (30, 60):
        for stop in ("day", "range"):
            for e in (1, 2):
                g.append({"bot": "ORB15", "or": n, "stop": stop, "max_entries": e, "rna": False, "tag": f"N{n}_{stop}_e{e}"})
    for n in (30, 60):
        g.append({"bot": "ORB15", "or": n, "stop": "range", "max_entries": 2, "rna": True, "tag": f"N{n}_range_e2_RNA"})
        g.append({"bot": "ORB15", "or": n, "stop": "day", "max_entries": 1, "rna": True, "tag": f"N{n}_day_e1_RNA"})
    return g


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return K4.day_start_aligned(rows, TF)


def daily_state(b):
    """{날: '오름' · '내림' · '섞임' · None} — 그날 쓰는 값은 앞 날 마지막 봉 종가까지로만 셈."""
    days, last = [], {}
    for r in b:
        if not days or days[-1] != r[0]:
            days.append(r[0])
        last[r[0]] = r[5]
    dc = np.array([last[d] for d in days], float)
    f = K.rna(dc, (3, 5, 10, 20), slope_k=3, band=20)
    out = {}
    for k, d in enumerate(days):
        if k == 0 or np.isnan(f["order"][k - 1]) or np.isnan(f["slope"][k - 1]):
            out[d] = None
            continue
        o, s = f["order"][k - 1], f["slope"][k - 1]
        out[d] = "오름" if (o >= 2 and s > 0) else "내림" if (o <= 1 and s < 0) else "섞임"
    return out


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    st = daily_state(b) if cfg["rna"] else {}
    i = 0
    while i < n:
        d = b[i][0]
        j = i
        while j < n and b[j][0] == d:
            j += 1
        start = b[i][1] - (TF - 1)                  # 그날 첫 분(첫 봉의 첫 분)
        hi = lo = None
        pos, entries = 0, 0
        allow = {1, -1}
        if cfg["rna"]:
            s = st.get(d)
            allow = {1} if s == "오름" else {-1} if s == "내림" else set()
        for k in range(i, j):
            m, h, l, c = b[k][1], b[k][3], b[k][4], b[k][5]
            if m < start + cfg["or"]:               # 범위 봉(이 봉의 마지막 분이 범위 안)
                hi = h if hi is None else max(hi, h)
                lo = l if lo is None else min(lo, l)
                continue
            if hi is None:
                continue
            if pos == 0:
                if entries < cfg["max_entries"] and m <= K.ENTRY_TO:
                    if c > hi and 1 in allow:
                        want[k], pos, entries = 1, 1, entries + 1
                    elif c < lo and -1 in allow:
                        want[k], pos, entries = -1, -1, entries + 1
            elif cfg["stop"] == "range" and ((pos > 0 and c < lo) or (pos < 0 and c > hi)):
                want[k], pos = 0, 0
        i = j
    return want


def eligible(d):
    pos_months = sum(1 for v in d.get("months", {}).values() if v > 0)
    return d.get("days", 0) > 0 and d["total_p"] > 0 and pos_months >= 3 and d["trades"] >= MIN_TRADES


def robust(res, key):
    """살아남기: 1차 조건 · 개발 앞 반(01 ~ 03) · 뒤 반(04 ~ 05) 모두 + · 범위 N만 바꾼 이웃도 개발 합 > 0."""
    d = res[key]["dev"]
    if not eligible(d):
        return False
    mo = d["months"]
    a = sum(v for k, v in mo.items() if k <= "202603"); b = sum(v for k, v in mo.items() if k >= "202604")
    cfg = res[key]["cfg"]
    other = key.replace(f"N{cfg['or']}", f"N{60 if cfg['or'] == 30 else 30}", 1)
    return a > 0 and b > 0 and res[other]["dev"].get("total_p", -1) > 0


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
    """① 개발 12칸(06-01부터 안 읽음) → ② robust 칸 가운데 개발 합 1등 → ③ 그 칸만 확인(09-01부터 안 읽음)."""
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
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf5 as K5;"
            "c=json.loads(os.environ['KC']);b=K5.prep(K.load());d,_=K.simulate(b,K5.signals(b,c));print(json.dumps(d))")
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
