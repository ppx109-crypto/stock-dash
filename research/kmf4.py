"""KMF-0004 — RNA 봇(15 · 30분봉) · 한투 1일봉 EMA 규칙을 키움 미니 코스피200 선물에 옮김 · 1분봉 신호는 안 씀.
사용자 2026-10-13: "한투 1일봉 개발시 사용했던 ema를 응용해봐 ema의 기울기 · 이격밴드 · 이격도 · 봉 위아래마감 · 박스 · 1분봉 고점트레일 · 역추세금지"
 · "변화에도 살아남을수있게 rna위주로 개발해줘" · "1분봉은 하지말자(잡음이 심하고 시간낭비)".
봉: 1분봉 자료를 N분봉(N 15 · 30)으로 묶음 · 그날 첫 분부터 N분씩 · 15:29까지 · 봉 이름 = 그 봉의 마지막 분.
   판단 = 봉 종가 · 체결 = 다음 봉 시가 · −12p 멈춤은 봉 안 고저로(KMF 공통 simulate) · 그날 마지막 봉(15:15 ~ 15:29) 종가에 정리.
RNA(N분봉 · 선 5 · 20 · 60 · 120봉 · 날 넘어 이어 셈 · 그 봉까지 값만):
  기본(E0) — 역추세금지: 120선 4봉 기울기 > 0이면 사기만 · < 0이면 팔기만
            정배열: 5 · 20 · 60 · 120선이 차례대로(사기) / 거꾸로(팔기)
            봉 위아래 마감(눌림 뒤 다시 섬): 앞 봉 종가 ≤ 20선 · 이 봉 종가 > 20선이면 삼(팔기는 거꾸로)
            정리: 종가가 60선 아래(팔기는 위)로 마감하면 다음 봉 시가에 정리 · 하루 들기 3번까지
  더하기(하나씩 · 모두 흔들림 따라 움직이는 상대 잣대 · KMF-0003 교훈):
   Z2  이격밴드: 120선 이격밴드(지난 60봉 대비 z)가 그 방향으로 2 넘으면 안 듦(너무 벌어짐)
   D2  이격도: 종가가 20선에서 ATR(지난 20봉 평균 봉 길이) 2배 넘게 떨어졌으면 안 듦
   B8  박스: 지난 8봉 박스(폭 ≤ 4 × ATR)를 그 방향으로 종가가 뚫을 때만
   T3  고점 트레일: 들고 나서 가장 높은 고가(팔기는 가장 낮은 저가) − 3 × ATR(들 때) 아래로 종가 마감하면 정리
   X20 정리 선: 60선 대신 20선
   H60 큰 흐름: 다 끝난 60분봉의 20선 2봉 기울기도 같은 방향일 때만
python3 research/kmf4.py lock | run | cut"""
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

ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0004"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py"]
SPANS = (5, 20, 60, 120)
LAST_MIN = 929
VARIANTS = ("E0", "Z2", "D2", "B8", "T3", "X20", "H60")


def grid():
    return [{"bot": "RNA", "tf": tf, "v": v, "tag": f"{v}_{tf}"} for tf in (15, 30) for v in VARIANTS]


def name(cfg):
    return cfg["tag"]


def day_start_aligned(rows, n):
    """봉 경계를 그날 첫 분 기준 n분 간격으로 맞춤(늦게 연 날도)."""
    out, start, cur = [], {}, None
    for r in rows:
        if r[1] > LAST_MIN:
            continue
        s = start.setdefault(r[0], r[1])
        b = (r[1] - s) // n
        if cur is None or cur[0] != r[0] or cur[7] != b:
            if cur is not None:
                out.append(tuple(cur[:7]))
            cur = [r[0], r[1], r[2], r[3], r[4], r[5], r[6], b]
        else:
            cur[1] = r[1]; cur[3] = max(cur[3], r[3]); cur[4] = min(cur[4], r[4]); cur[5] = r[5]; cur[6] += r[6]
    if cur is not None:
        out.append(tuple(cur[:7]))
    return out


def prep(rows, cfg):
    return day_start_aligned(rows, cfg["tf"])


def atr(b, n=20):
    rng = np.array([r[3] - r[4] for r in b], float)
    c = np.cumsum(np.insert(rng, 0, 0.0))
    out = np.full(len(b), np.nan)
    for i in range(n - 1, len(b)):
        out[i] = (c[i + 1] - c[i + 1 - n]) / n
    return out


def h60_slope(b, tf):
    """각 봉 시점에 '다 끝난' 60분봉들의 종가로 셈한 20선의 2봉 기울기 부호(+1 · −1 · 0) · 앞만.
    60분봉 = 그날 첫 봉부터 60 ÷ tf개씩 다 찬 묶음만(장 끝 15:00 ~ 15:29 같은 모자란 조각은 넣지 않음 · GPT #282).
    이 봉이 60분 묶음의 마지막 봉이면 그 60분봉은 이 봉 종가에 끝남."""
    per = 60 // tf
    out = np.zeros(len(b))
    ema, hist, k = None, [], 2.0 / 21
    j, day = 0, None
    for i, r in enumerate(b):
        if r[0] != day:
            day, j = r[0], 0
        else:
            j += 1
        if (j + 1) % per == 0:
            ema = r[5] if ema is None else ema + k * (r[5] - ema)
            hist.append(ema)
        if len(hist) >= 23:
            out[i] = np.sign(hist[-1] - hist[-3])
    return out


def signals(b, cfg):
    """b = N분봉. 분마다가 아니라 봉마다 원하는 자리(+1 · −1 · 0 · None)."""
    v = cfg["v"]
    c = np.array([r[5] for r in b], float)
    f = K.rna(c, SPANS, slope_k=4, band=60)
    lines = {s: K.ema(c, s) for s in SPANS}
    a = atr(b)
    hs = h60_slope(b, cfg["tf"]) if v == "H60" else None
    ex = 20 if v == "X20" else 60
    n = len(b)
    want = [None] * n
    pos, entries, peak, stopv, day = 0, 0, None, None, None
    for i in range(n):
        d, m, h, l, cl = b[i][0], b[i][1], b[i][3], b[i][4], b[i][5]
        if d != day:
            day, pos, entries, peak, stopv = d, 0, 0, None, None
        if pos != 0:
            peak = (h if peak is None else max(peak, h)) if pos > 0 else (l if peak is None else min(peak, l))
            out = (pos > 0 and cl < lines[ex][i]) or (pos < 0 and cl > lines[ex][i])
            if v == "T3" and stopv is not None:
                out = out or (pos > 0 and cl < peak - stopv) or (pos < 0 and cl > peak + stopv)
            if out:
                want[i], pos, peak, stopv = 0, 0, None, None
            continue
        if entries >= 3 or not (K.ENTRY_FROM <= m <= K.ENTRY_TO) or i == 0 or b[i - 1][0] != d:
            continue
        o, s = f["order"][i], f["slope"][i]
        if np.isnan(o) or np.isnan(s) or np.isnan(a[i]):
            continue
        e_now, e_prev = lines[20][i], lines[20][i - 1]
        side = 0
        if s > 0 and o == 3 and c[i - 1] <= e_prev and cl > e_now:
            side = 1
        elif s < 0 and o == 0 and c[i - 1] >= e_prev and cl < e_now:
            side = -1
        if side == 0:
            continue
        if v == "Z2":
            z = f["z120"][i]
            if np.isnan(z) or side * z > 2.0:
                continue
        if v == "D2" and abs(cl - e_now) > 2 * a[i]:
            continue
        if v == "B8":
            k0 = i - 8
            if k0 < 0 or b[k0][0] != d:
                continue
            bh = max(r[3] for r in b[k0:i]); bl = min(r[4] for r in b[k0:i])
            if bh - bl > 4 * a[i] or not ((side > 0 and cl > bh) or (side < 0 and cl < bl)):
                continue
        if v == "H60" and hs[i] != side:
            continue
        want[i], pos, entries, peak = side, side, entries + 1, None
        stopv = 3 * a[i] if v == "T3" else None
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


MIN_TRADES = 15      # 추세 봇은 드물게 삼 · 개발 98일 15번 이상(KMF-0001 ~ 0003의 30번 대신 · 거래 수만 보고 정함 · 손익은 안 봄)


def eligible(d):
    pos_months = sum(1 for v in d.get("months", {}).values() if v > 0)
    return d.get("days", 0) > 0 and d["total_p"] > 0 and pos_months >= 3 and d["trades"] >= MIN_TRADES


def robust(res, key):
    """변화에도 살아남기(사전등록): 1차 조건 · 개발 앞 반(01 ~ 03) 합 > 0 · 뒤 반(04 ~ 05) 합 > 0 · 같은 더하기의 다른 봉 길이도 개발 합 > 0."""
    d = res[key]["dev"]
    if not eligible(d):
        return False
    mo = d["months"]
    first = sum(v for k, v in mo.items() if k <= "202603"); second = sum(v for k, v in mo.items() if k >= "202604")
    cfg = res[key]["cfg"]
    other = f"{cfg['v']}_{30 if cfg['tf'] == 15 else 15}"
    return first > 0 and second > 0 and res[other]["dev"].get("total_p", -1) > 0


def run():
    """① 개발 14칸(06-01부터 안 읽음) → ② robust 칸 가운데 개발 합 1등 한 칸 → ③ 그 칸만 확인(09-01부터 안 읽음)."""
    verify_inputs()
    raw = K._rows_before(K.VAL[0])
    res = {}
    for cfg in grid():
        b = prep(raw, cfg)
        log({"status": "STARTED", "key": name(cfg), "stage": "dev", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(b, signals(b, cfg))
        res[name(cfg)] = {"cfg": cfg, "dev": K.stats(days, trades, *K.DEV)}
        log({"status": "DONE", "key": name(cfg), "stage": "dev", "dev_total_p": res[name(cfg)]["dev"].get("total_p")})
    cands = sorted([k for k in res if robust(res, k)], key=lambda k: (-res[k]["dev"]["total_p"], k))
    pick = None
    if cands:
        k = cands[0]
        vb = prep(K._rows_before(K.TEST[0]), res[k]["cfg"])
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
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf4 as K4;"
            "c=json.loads(os.environ['KC']);b=K4.prep(K.load(),c);d,_=K.simulate(b,K4.signals(b,c));print(json.dumps(d))")
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
