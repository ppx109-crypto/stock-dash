"""KMF-0003 — 기본 봇 1번(ORB-1 60분 · 하루 2번 · 반대 범위 멈춤) 손실 줄이기(사용자 2026-10-12 "손실 분석 후 줄일 방법 개발").
근거(KMF-0002 개발 기간 손실 분석 · 판정 밖 · KMF-0003/diag): 멈춘 날 24일 중 17일이 아침 범위 넓은 날(≥ 17.32p) · 좁은 날(< 11.06p) 0일 ·
12시 뒤 들기 −50.2p · 멈춘 날은 멈춤 없어도 장 끝 −267.9p(들기가 나빴음) · 이긴 날 47일 중 들기 뒤 −8p보다 밀린 날 4일 · 멈춘 날 갭이 큼(25.5 대 17.1p).
줄이기 방법(하나씩 따로 · 기본 봇에 하나만 더함 · 그 분 종가까지 값만):
  W  범위 폭 거름: 60분 범위 폭 > w포인트면 그날 안 듦 · w {15 · 20 · 25}
  WR 상대 범위 폭 거름: 폭 > 지난 20일(그날 제외 · 앞 날만) 평균 폭 × r이면 안 듦 · r {1.25 · 1.5}
  S  거래 멈춤: 들기 값(판단 다음 분 시가) 대비 종가가 s포인트 넘게 불리하면 다음 분 시가에 정리 · s {6 · 8}
  T  들기 마감: 새로 들기는 t분 판단까지 · t {11:00 · 12:00}
  G  갭 거름: |그날 첫 시가 − 앞 거래일 마지막 종가| > g면 안 듦 · g {20 · 30}
  C  들기 봉(사용자 2026-10-12 "몇분봉으로 진입할건지"): 들기 판단을 c분봉 종가(그날 첫 분부터 c분씩 끊은 봉의 마지막 분 종가)에서만 · c {5 · 15} · 정리는 1분봉 그대로
python3 research/kmf3.py lock | run | cut"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402

ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0003"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf2.py", "research/kmf3.py"]
BASE = {"bot": "ORB1", "or": 60, "max_entries": 2, "stop": "range"}


def grid():
    g = [dict(BASE, tag="B0")]
    g += [dict(BASE, tag=f"W{w}", width_max=w) for w in (15, 20, 25)]
    g += [dict(BASE, tag=f"WR{r}", width_rel=r) for r in (1.25, 1.5)]
    g += [dict(BASE, tag=f"S{s}", trade_stop=s) for s in (6, 8)]
    g += [dict(BASE, tag=f"T{t}", entry_until=t) for t in (660, 720)]
    g += [dict(BASE, tag=f"G{x}", gap_max=x) for x in (20, 30)]
    g += [dict(BASE, tag=f"C{c}", confirm=c) for c in (5, 15)]
    return g


def name(cfg):
    return cfg["tag"]


def signals(rows, cfg):
    """kmf2.signals(ORB-1)와 같은 뼈대 + 줄이기 방법 하나. 그 분 종가까지 값만(앞 날 폭 · 앞 날 종가 포함)."""
    n = len(rows)
    want = [None] * n
    widths = []                                   # 끝난 앞 날들의 범위 폭(앞 날만)
    prev_close = None
    i = 0
    while i < n:
        d = rows[i][0]
        j = i
        while j < n and rows[j][0] == d:
            j += 1
        start = rows[i][1]
        hi = lo = None
        pos, entries, ref, skip, decided = 0, 0, None, False, False
        for k in range(i, j):
            m, h, l, c = rows[k][1], rows[k][3], rows[k][4], rows[k][5]
            if m < start + cfg["or"]:
                hi = h if hi is None else max(hi, h)
                lo = l if lo is None else min(lo, l)
                continue
            if hi is None:
                continue
            if not decided:                       # 범위가 다 만들어진 첫 분: 그날 들지 말지(앞 값만)
                decided = True
                w = hi - lo
                if "width_max" in cfg and w > cfg["width_max"]:
                    skip = True
                if "width_rel" in cfg:
                    past = widths[-20:]
                    if len(past) < 20 or w > cfg["width_rel"] * sum(past) / len(past):
                        skip = True               # 앞 날 20일이 모자라면 들지 않음(보수적)
                if "gap_max" in cfg and (prev_close is None or abs(rows[i][2] - prev_close) > cfg["gap_max"]):
                    skip = True
            if ref is None and pos != 0 and k - 1 >= i:
                ref = rows[k][2]                  # 들기 값 = 판단 다음 분 시가(이 분 시가 · 이미 앎)
            if pos == 0:
                last = min(K.ENTRY_TO, cfg.get("entry_until", K.ENTRY_TO))
                bar_end = (m - start + 1) % cfg.get("confirm", 1) == 0          # c분봉의 마지막 분(그 분 종가 = c분봉 종가)
                if not skip and entries < cfg["max_entries"] and m <= last and bar_end:
                    if c > hi:
                        want[k], pos, entries, ref = 1, 1, entries + 1, None
                    elif c < lo:
                        want[k], pos, entries, ref = -1, -1, entries + 1, None
            elif cfg["stop"] == "range" and ((pos > 0 and c < lo) or (pos < 0 and c > hi)):
                want[k], pos = 0, 0
            elif "trade_stop" in cfg and ref is not None and pos * (c - ref) <= -cfg["trade_stop"]:
                want[k], pos = 0, 0               # 거래 멈춤(종가 기준 · 다음 분 시가에 정리)
        if hi is not None:
            widths.append(hi - lo)
        prev_close = rows[j - 1][5]
        i = j
    return want


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


def better(x, b):
    """개발 기간에서 기본 봇(B0)보다 나은지(사전등록): 멈춘 날 줄고 · 합 ≥ B0 · 가장 나쁜 달 ≥ B0 · 1차 조건(eligible)."""
    return (K.eligible(x) and x["stop_days"] < b["stop_days"] and x["total_p"] >= b["total_p"]
            and x["worst_month_p"] >= b["worst_month_p"])


def val_keep(x, b):
    """확인 기간(이 방법들은 처음 셈): 합 ≥ B0 확인 합 × 0.8 · 멈춘 날 B0보다 적음 · 가장 나쁜 날 ≥ −12.5p."""
    return x["total_p"] >= 0.8 * b["total_p"] and x["stop_days"] < b["stop_days"] and x["worst_day_p"] >= K.DAY_STOP - 0.5


def run():
    """① 개발 14칸(B0 + 방법 13 · 06-01부터 안 읽음) → ② better 넘은 방법 가운데 개발 합 1등 한 칸(같으면 멈춘 날 적은 쪽) →
    ③ 그 칸과 B0만 확인(09-01 앞까지)."""
    verify_inputs()
    rows = K._rows_before(K.VAL[0])
    res = {}
    for cfg in grid():
        log({"status": "STARTED", "key": name(cfg), "stage": "dev", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(rows, signals(rows, cfg))
        res[name(cfg)] = {"cfg": cfg, "dev": K.stats(days, trades, *K.DEV)}
        log({"status": "DONE", "key": name(cfg), "stage": "dev", "dev_total_p": res[name(cfg)]["dev"].get("total_p")})
    b = res["B0"]["dev"]
    cands = sorted([k for k, v in res.items() if k != "B0" and better(v["dev"], b)],
                   key=lambda k: (-res[k]["dev"]["total_p"], res[k]["dev"]["stop_days"], k))
    pick = None
    if cands:
        vrows = K._rows_before(K.TEST[0])
        vb = {}
        for k in ("B0", cands[0]):
            log({"status": "STARTED", "key": k, "stage": "val", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
            days, trades = K.simulate(vrows, signals(vrows, res[k]["cfg"]))
            vb[k] = {"dev_check": K.stats(days, trades, *K.DEV)["total_p"], "val": K.stats(days, trades, *K.VAL)}
            log({"status": "DONE", "key": k, "stage": "val", "val_total_p": vb[k]["val"].get("total_p")})
        k = cands[0]
        pick = {"name": k, "cfg": res[k]["cfg"], "dev": res[k]["dev"], "val": vb[k]["val"], "dev_check": vb[k]["dev_check"],
                "base_val": vb["B0"]["val"], "base_dev_check": vb["B0"]["dev_check"], "val_keep": val_keep(vb[k]["val"], vb["B0"]["val"])}
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_rows.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    (BOX / "evidence/pick.json").write_text(json.dumps(pick, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": ("REDUCE_CANDIDATE " + pick["name"]) if pick and pick["val_keep"] else "NO_IMPROVEMENT", "better_dev": cands,
                      "pick": pick and {"name": pick["name"], "dev_total_p": pick["dev"]["total_p"], "dev_stop_days": pick["dev"]["stop_days"],
                                        "val_total_p": pick["val"]["total_p"], "val_stop_days": pick["val"]["stop_days"],
                                        "base_val_total_p": pick["base_val"]["total_p"], "base_val_stop_days": pick["base_val"]["stop_days"],
                                        "val_keep": pick["val_keep"]}}, ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260401", "20260504")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf3 as K3;rows=K.load();"
            "c=json.loads(os.environ['KC']);d,_=K.simulate(rows,K3.signals(rows,c));print(json.dumps(d))")
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
