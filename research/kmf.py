"""KMF — 키움 미니 코스피200 선물 1분봉에 맞춘 RNA로 새 봇 만들기(사용자 2026-10-12 · 한투 모의투자와 별개 · 연구 · 백테스트까지).

사용자 결정(2026-10-12): 사기 · 팔기 둘 다 · 그날 다 정리(밤 넘기지 않음) · 편도 비용 0.04p · 하루 손실 −12p에 닿으면 그날 정리하고 멈춤 · 1계약 기준.
자료: kiwoom-data/mini_1min_2026_01_08.csv(2026-01-02 ~ 08-31 · 미니 근월물) + kiwoom-data/kospi200_futures_1min.csv의 09-01 ~ 10-12 미니 근월물(A056*).
  - 두 파일이 겹치는 미니 근월물 구간은 같은 분 값이 같음(차 0 · 2026-10-12 확인). 09:00(540분) ~ 15:34(934분)만 씀(첫 파일과 같은 시간대).
RNA(분봉판 · rna.py와 같은 뜻 · 그 분 종가까지만): 배열 · 기울기 · 이격도 · 이격밴드(z).
체결: 그 분 종가에 판단 → 다음 분 시가에 체결(편도 0.04p). 하루 −12p는 '멈춤 주문'으로 그 분 안에서 닿으면 그 값(시가가 이미 넘었으면 시가)에 정리.
새로 사기 · 팔기는 09:05 ~ 15:00 판단까지 · 15:30(930분) 종가에 모두 정리.
기간(사전등록 · 결과 보기 전 고정): 개발 2026-01 ~ 05 · 확인 06 ~ 08 · 마지막 시험 09-01 ~ 10-12(한 번만).
python3 research/kmf.py lock | run | cut | final
고친 판(2026-10-12 GPT 검토 #273 반영): 계약은 그날 거래량 합 1등(같으면 코드 앞) · 개발 18칸은 확인 기간을 처음부터 안 읽음(KMF_CUT=06-01)
· 확인 값은 봇마다 고른 1칸만 셈 · 자르기 시험은 시험 기간을 안 읽음 · 마지막 시험은 final(지피티 동의 파일이 있을 때 한 번만)."""
import csv
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "kiwoom-data"
MINI = DATA / "mini_1min_2026_01_08.csv"
FUT = DATA / "kospi200_futures_1min.csv"
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0001"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
COST = 0.04                    # 편도(포인트)
DAY_STOP = -12.0               # 하루 손실 한도(포인트 · 비용 포함)
FIRST_MIN, LAST_MIN = 540, 934
ENTRY_FROM, ENTRY_TO, FLAT_AT = 545, 900, 930
DEV = ("20260101", "20260531")
VAL = ("20260601", "20260831")
TEST = ("20260901", "20261012")
CUT = os.getenv("KMF_CUT", "")          # 자르기 시험: 이 날(YYYYMMDD)부터 뒤 자료는 처음부터 안 읽음


# ───────── 자료 ─────────
def load():
    """[(날, 분, 시가, 고가, 저가, 종가, 거래량)] 날 · 분 순서. CUT이 있으면 그 날 앞만."""
    rows = []
    with open(MINI, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d, m = r["date"], int(r["minute"])
            if CUT and d >= CUT:
                continue
            if FIRST_MIN <= m <= LAST_MIN:
                rows.append((d, m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    last = max(r[0] for r in rows) if rows else ""
    fut = defaultdict(list)
    with open(FUT, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            d = r["datetime"][:10].replace("-", "")
            if d <= last or not r["code"].startswith("A056") or (CUT and d >= CUT):
                continue                          # 첫 파일 뒤 날의 미니 근월물만
            m = int(r["datetime"][11:13]) * 60 + int(r["datetime"][14:16])
            if FIRST_MIN <= m <= LAST_MIN:
                fut[d].append((r["code"], m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    for d in sorted(fut):
        vol = Counter()
        for x in fut[d]:
            vol[x[0]] += x[6]
        main = sorted(vol.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]    # 그날 거래량 합 1등 미니 계약(같으면 코드 앞)
        for x in sorted((x for x in fut[d] if x[0] == main), key=lambda x: x[1]):
            rows.append((d,) + x[1:])
    return rows


# ───────── RNA(분봉판) ─────────
def ema(x, span):
    a = np.asarray(x, float)
    out = np.empty_like(a)
    k = 2.0 / (span + 1)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = out[i - 1] + k * (a[i] - out[i - 1])
    out[:span] = np.nan
    return out


def rna(close, spans, slope_k=5, band=120):
    """분마다(그 분 종가까지만): order = 짧은 선이 바로 긴 선 위인 짝 수(0 ~ len−1) · slope = 가장 긴 선의 k분 기울기(%) ·
    disp[s] = 종가 ÷ EMA(s) − 1(%) · z[s] = disp가 지난 band분(그 분 제외 · 앞만) 평균에서 몇 표준편차인지."""
    c = np.asarray(close, float)
    lines = {s: ema(c, s) for s in spans}
    order = np.sum([lines[a] > lines[b] for a, b in zip(spans, spans[1:])], axis=0).astype(float)
    order[np.isnan(lines[spans[-1]])] = np.nan
    L = lines[spans[-1]]
    slope = np.full_like(c, np.nan)
    slope[slope_k:] = (L[slope_k:] / L[:-slope_k] - 1) * 100
    out = {"order": order, "slope": slope}
    for s in spans:
        disp = (c / lines[s] - 1) * 100
        z = np.full_like(c, np.nan)
        for i in range(band, len(c)):
            w = disp[i - band:i]                       # 그 분 앞 band분(그 분 제외)
            if np.isnan(w).any():
                continue
            sd = w.std()
            z[i] = (disp[i] - w.mean()) / sd if sd > 0 else 0.0
        out[f"disp{s}"], out[f"z{s}"] = disp, z
    return out


# ───────── 신호(봇 셋 · 고정 격자) ─────────
SPANS = {"fast": (3, 10, 30, 60), "mid": (5, 20, 60, 120), "slow": (10, 30, 90, 180)}


def grid():
    g = []
    for sp in SPANS:                                   # A 추세 배열(TR)
        for hold in (1, 2):
            g.append({"bot": "TR", "spans": sp, "exit_gap": hold})
    for k in (2.0, 2.5):                               # B 이격 되돌림(MR) · 큰 흐름 따라
        for band in (60, 120):
            for line in (20, 60):
                g.append({"bot": "MR", "k": k, "band": band, "line": line})
    for orw in (15, 30):                               # C 시가 범위 돌파(ORB) · RNA 거름 켜고 끔
        for filt in (True, False):
            g.append({"bot": "ORB", "or": orw, "filter": filt})
    return g


def name(cfg):
    return "_".join(f"{k}{v}" for k, v in cfg.items())


def signals(rows, cfg):
    """분마다 원하는 자리: +1 삼 · −1 팖 · 0 정리 · 'L0' 산 것만 정리 · 'S0' 판 것만 정리 · None 그대로. 그 분 종가까지 값만 씀."""
    c = [r[5] for r in rows]
    n = len(rows)
    want = [None] * n
    if cfg["bot"] == "TR":
        spans = SPANS[cfg["spans"]]
        f = rna(c, spans)
        top = len(spans) - 1
        for i in range(n):
            o, s = f["order"][i], f["slope"][i]
            if np.isnan(o) or np.isnan(s):
                continue
            if o == top and s > 0:
                want[i] = 1
            elif o == 0 and s < 0:
                want[i] = -1
            else:                                      # 배열이 exit_gap칸 넘게 풀리면 그쪽만 정리(사이에 버팀)
                cl, cs = o <= top - cfg["exit_gap"], o >= cfg["exit_gap"]
                want[i] = 0 if cl and cs else "L0" if cl else "S0" if cs else None
        return want
    if cfg["bot"] == "MR":
        spans = (cfg["line"], 120)
        f = rna(c, spans, band=cfg["band"])
        z, slope = f[f"z{cfg['line']}"], f["slope"]
        for i in range(n):
            zi, s = z[i], slope[i]
            if np.isnan(zi) or np.isnan(s):
                continue
            if s > 0 and zi <= -cfg["k"]:
                want[i] = 1                            # 오르는 흐름에서 많이 눌림 → 삼
            elif s < 0 and zi >= cfg["k"]:
                want[i] = -1                           # 내리는 흐름에서 많이 뜀 → 팖
            elif abs(zi) <= 0.25:
                want[i] = 0                            # 평균으로 돌아오면 정리
        return want
    if cfg["bot"] == "ORB":
        f = rna(c, SPANS["mid"])
        top = len(SPANS["mid"]) - 1
        hi = lo = None
        day = None
        for i, r in enumerate(rows):
            d, m = r[0], r[1]
            if d != day:
                day, hi, lo = d, None, None
            if m < FIRST_MIN + cfg["or"]:
                hi = r[3] if hi is None else max(hi, r[3])
                lo = r[4] if lo is None else min(lo, r[4])
                continue
            if hi is None:
                continue
            o = f["order"][i]
            if r[5] > hi and (not cfg["filter"] or (not np.isnan(o) and o >= top - 1)):
                want[i] = 1
            elif r[5] < lo and (not cfg["filter"] or (not np.isnan(o) and o <= 1)):
                want[i] = -1
            elif lo <= r[5] <= hi:
                want[i] = 0                            # 범위 안으로 돌아오면 정리
        return want
    raise KeyError(cfg["bot"])


# ───────── 매매 셈(1계약 · 포인트) ─────────
def simulate(rows, want):
    """돌려줌: {날: 그날 손익(p · 비용 포함)} · 거래 목록. 체결은 다음 분 시가 · 하루 −12p 멈춤 주문 · 15:30 종가 정리."""
    days, trades = {}, []
    pos, entry, real, stopped = 0, 0.0, 0.0, False
    for i, r in enumerate(rows):
        d, m, o, h, l, c = r[0], r[1], r[2], r[3], r[4], r[5]
        if i == 0 or rows[i - 1][0] != d:                 # 새 날: 앞날은 이미 정리돼 있음
            pos, entry, real, stopped = 0, 0.0, 0.0, False
            days[d] = 0.0
        # 1) 앞 분 판단을 이 분 시가에 체결(멈춘 날 · 정리 시각 뒤는 안 함)
        if i > 0 and rows[i - 1][0] == d and not stopped and m <= FLAT_AT:
            w = want[i - 1]
            pm = rows[i - 1][1]
            if w == "L0":
                w = 0 if pos > 0 else None
            elif w == "S0":
                w = 0 if pos < 0 else None
            if w is not None and w != pos:
                if pos:                                   # 정리 · 뒤집기 때 든 것 먼저 정리(시각과 상관없이)
                    real += pos * (o - entry) - COST
                    trades.append((d, pm, pos, entry, o))
                    pos = 0
                if w and ENTRY_FROM <= pm <= ENTRY_TO and real > DAY_STOP:   # 새로 들기는 09:05 ~ 15:00 판단까지
                    pos, entry = w, o
                    real -= COST
        # 2) 하루 −12p 멈춤 주문(이 분 안에서 닿으면)
        if pos and not stopped:
            stop_px = entry + pos * (DAY_STOP - real + COST)      # real + pos*(p−entry) − COST = −12
            hit = (l <= stop_px) if pos > 0 else (h >= stop_px)
            if hit:
                px = min(o, stop_px) if pos > 0 else max(o, stop_px)
                real += pos * (px - entry) - COST
                trades.append((d, m, pos, entry, px))
                pos, stopped = 0, True
        elif not pos and real <= DAY_STOP:
            stopped = True
        # 3) 15:30 종가에 모두 정리(또는 그날 마지막 분)
        last_of_day = i + 1 == len(rows) or rows[i + 1][0] != d
        if pos and (m >= FLAT_AT or last_of_day):
            real += pos * (c - entry) - COST
            trades.append((d, m, pos, entry, c))
            pos = 0
        days[d] = real
    return days, trades


MULT = 50000                   # 미니 코스피200 선물 1포인트 = 5만 원(참고 · 원 환산)


def boot_ci(vals, n=2000, seed=0):
    """하루 평균(p)의 95% 구간(날을 다시 뽑기 · 고정 씨앗)."""
    if len(vals) < 2:
        return None
    rng = np.random.default_rng(seed)
    a = np.asarray(vals, float)
    m = a[rng.integers(0, len(a), (n, len(a)))].mean(axis=1)
    return [round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3)]


def stats(days, trades, lo, hi):
    ds = {d: v for d, v in days.items() if lo <= d <= hi}
    if not ds:
        return {"days": 0}
    vals = list(ds.values())
    mo = defaultdict(float)
    for d, v in ds.items():
        mo[d[:6]] += v
    eq, pk, mdd = 0.0, 0.0, 0.0
    for d in sorted(ds):
        eq += ds[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    tr = [t for t in trades if lo <= t[0] <= hi]
    wins = sum(1 for t in tr if t[2] * (t[4] - t[3]) - 2 * COST > 0)
    return {"days": len(ds), "total_p": round(sum(vals), 2), "per_day_p": round(sum(vals) / len(ds), 3), "worst_day_p": round(min(vals), 2),
            "best_day_p": round(max(vals), 2), "win_days": sum(1 for v in vals if v > 0), "loss_days": sum(1 for v in vals if v < 0),
            "trades": len(tr), "win_rate": round(wins / len(tr), 3) if tr else None, "mdd_p": round(mdd, 2),
            "months": {k: round(v, 2) for k, v in sorted(mo.items())}, "stop_days": sum(1 for v in vals if v <= DAY_STOP + 1e-9),
            "worst_month_p": round(min(mo.values()), 2), "per_day_ci95_p": boot_ci(vals),
            "won": {"total": round(sum(vals) * MULT), "worst_day": round(min(vals) * MULT), "worst_month": round(min(mo.values()) * MULT)}}


def evaluate(rows, cfg):
    days, trades = simulate(rows, signals(rows, cfg))
    return {"name": name(cfg), "cfg": cfg, "dev": stats(days, trades, *DEV)}


# ───────── 기록 · 잠금 ─────────
CODE_FILES = ["research/kmf.py"]


def lock_body():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    body = {"root": str(ROOT)}
    body.update({f: sha(ROOT / f) for f in CODE_FILES})
    body.update({f"kiwoom-data/{p.name}": sha(p) for p in (MINI, FUT)})
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
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); os.fsync(fh.fileno())


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1)); print(LOCK.read_text())


def cut():
    """자르기 시험: 어느 날부터 뒤 자료를 처음부터 안 읽은 채 돌린 날별 손익이 그 날 앞까지 같아야 함."""
    import subprocess
    cuts = ("20260302", "20260401", "20260504")              # 개발 기간 안에서만(확인 · 시험 기간은 기준 판도 안 읽음)
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;rows=K.load();"
            "c=json.loads(os.environ['KC']);d,_=K.simulate(rows,K.signals(rows,c));print(json.dumps(d))")
    picks = [g for g in grid() if g in ({"bot": "TR", "spans": "mid", "exit_gap": 1}, {"bot": "MR", "k": 2.0, "band": 60, "line": 20},
                                         {"bot": "ORB", "or": 30, "filter": True})]
    res = []
    for cfg in picks:
        env = dict(os.environ, KC=json.dumps(cfg), KMF_CUT=VAL[0])
        full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["KMF_CUT"] = ct
            part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in part if d < ct]
            res.append({"cfg": name(cfg), "cut": ct, "days": len(ds), "diff": sum(1 for d in ds if abs(part[d] - full[d]) > 1e-9),
                        "no_future_days": all(d < ct for d in part)})
    print(json.dumps({"pass": all(r["diff"] == 0 and r["no_future_days"] for r in res), "runs": res}, ensure_ascii=False))


# ───────── 고르기(사전등록) ─────────
def eligible(dev):
    """개발 기간 1차 조건: 합 > 0 · 다섯 달 가운데 셋 이상 + · 거래 30번 이상."""
    pos_months = sum(1 for v in dev.get("months", {}).values() if v > 0)
    return dev.get("days", 0) > 0 and dev["total_p"] > 0 and pos_months >= 3 and dev["trades"] >= 30


def val_pass(dev, val):
    """확인 기간: 합 > 0 · 하루 평균 ≥ 개발의 절반 · 가장 나쁜 날 ≥ −12.5p(멈춤 주문 미끄러짐 여유 0.5p) · 세 달 가운데 둘 이상 +."""
    pos_months = sum(1 for v in val.get("months", {}).values() if v > 0)
    return (val.get("days", 0) > 0 and val["total_p"] > 0 and val["per_day_p"] >= 0.5 * dev["per_day_p"]
            and val["worst_day_p"] >= DAY_STOP - 0.5 and pos_months >= 2)


def neighbors(cfg):
    """같은 봇에서 값 하나만 다른 칸(보고만)."""
    out = []
    for g in grid():
        if g["bot"] == cfg["bot"] and g != cfg and sum(g[k] != cfg[k] for k in cfg) == 1:
            out.append(g)
    return out


def _rows_before(day):
    """그 날 앞 자료만(처음부터 안 읽음)."""
    global CUT
    old, CUT = CUT, day
    try:
        rows = load()
    finally:
        CUT = old
    assert max(r[0] for r in rows) < day
    return rows


def run():
    """① 개발(01 ~ 05) 18칸: 확인 기간부터 뒤는 처음부터 안 읽음 → ② 봇마다 개발 1등(1차 조건 넘은 칸) →
    ③ 그 칸만 확인(06 ~ 08 · 시험 기간은 안 읽음). 다른 칸은 확인 기간을 셈하지도 않음."""
    verify_inputs()
    rows = _rows_before(VAL[0])
    res = {}
    for cfg in grid():
        key = name(cfg)
        log({"status": "STARTED", "key": key, "stage": "dev", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = simulate(rows, signals(rows, cfg))
        res[key] = {"cfg": cfg, "dev": stats(days, trades, *DEV)}
        log({"status": "DONE", "key": key, "stage": "dev", "dev_total_p": res[key]["dev"].get("total_p")})
    picks = {}
    for bot in ("TR", "MR", "ORB"):
        cands = sorted([k for k, v in res.items() if v["cfg"]["bot"] == bot and eligible(v["dev"])],
                       key=lambda k: (-res[k]["dev"]["total_p"], k))
        picks[bot] = {"name": cands[0], "cfg": res[cands[0]]["cfg"], "dev": res[cands[0]]["dev"],
                      "neighbors_dev": {name(nb): res[name(nb)]["dev"].get("total_p") for nb in neighbors(res[cands[0]]["cfg"])}} if cands else None
    vrows = _rows_before(TEST[0]) if any(picks.values()) else []
    for bot, pk in picks.items():
        if not pk:
            continue
        log({"status": "STARTED", "key": pk["name"], "stage": "val", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = simulate(vrows, signals(vrows, pk["cfg"]))
        pk["dev_check"] = stats(days, trades, *DEV)["total_p"]          # 개발 값이 ①과 같아야 함(자르기 맞춤)
        pk["val"] = stats(days, trades, *VAL)
        pk["val_pass"] = val_pass(pk["dev"], pk["val"])
        log({"status": "DONE", "key": pk["name"], "stage": "val", "val_total_p": pk["val"].get("total_p")})
    BOX.mkdir(parents=True, exist_ok=True)
    (BOX / "evidence").mkdir(exist_ok=True)
    (BOX / "evidence/dev_rows.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    (BOX / "evidence/picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1))
    passed = [b for b, p in picks.items() if p and p["val_pass"]]
    print(json.dumps({"verdict": "VAL_PASS " + ",".join(passed) if passed else "NO_EDGE", "val_cells_computed": sum(1 for p in picks.values() if p),
                      "picks": {b: (p and {"name": p["name"], "dev_total_p": p["dev"]["total_p"], "dev_check": p["dev_check"],
                                           "val_total_p": p["val"]["total_p"], "val_pass": p["val_pass"]}) for b, p in picks.items()}}, ensure_ascii=False))


FINAL_OK = BOX / "final_ok.json"        # 지피티 동의 뒤 클로드가 올리는 파일: {"gpt_pr": 번호, "picks": [칸 이름, ...]}
FINAL_OUT = BOX / "evidence/final.json"


def final():
    """마지막 시험(09-01 ~ 10-12) 한 번: 확인을 통과했고 동의 파일에 적힌 칸만. 이미 돌렸으면 멈춤."""
    verify_inputs()
    if FINAL_OUT.exists():
        sys.exit("마지막 시험은 이미 한 번 돌렸음(멈춤)")
    if not FINAL_OK.exists():
        sys.exit("지피티 동의 파일이 없음(멈춤)")
    ok = json.loads(FINAL_OK.read_text())
    picks = json.loads((BOX / "evidence/picks.json").read_text())
    allowed = {p["name"]: p for p in picks.values() if p and p.get("val_pass")}
    want = list(ok["picks"])
    if not want or any(n not in allowed for n in want):
        sys.exit("동의 파일의 칸이 확인 통과 칸이 아님(멈춤): " + json.dumps(want, ensure_ascii=False))
    rows = load()
    out = {}
    for n in want:
        days, trades = simulate(rows, signals(rows, allowed[n]["cfg"]))
        t = stats(days, trades, *TEST)
        out[n] = {"test": t, "pass": t.get("days", 0) > 0 and t["total_p"] > 0 and t["worst_day_p"] >= DAY_STOP - 0.5}
    FINAL_OUT.write_text(json.dumps({"gpt_pr": ok.get("gpt_pr"), "results": out}, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": "KMF_CANDIDATE" if any(v["pass"] for v in out.values()) else "NO_EDGE",
                      "results": {n: {"test_total_p": v["test"].get("total_p"), "pass": v["pass"]} for n, v in out.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    {"lock": write_lock, "cut": cut, "run": run, "final": final}[sys.argv[1]]()
