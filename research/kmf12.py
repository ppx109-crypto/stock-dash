"""KMF-0012 — 멈춤에 맞춘 추세 봇 + 덫 봇 · 하루 손실 한도 −25p(5분봉 판단 · 1분봉 신호 없음).
사용자 2026-10-13 "손실 한도 -25로해줘" → KMF-0011(−12p · S 6 · 10)을 실행 전에 거둬들이고 같은 꼴을 −25p에 맞춤(S 12 · 20 = 한도의 약 0.5 · 0.8배).
사용자 2026-10-13: "목표 10개월에 800p · 추세 횡보에서 각각 작동하는 단타봇" · 처음엔 '−12p 그대로'를 골랐다가 "손실 한도 -25로해줘"로 바꿈.
근거(판정 밖 · KMF-0010/diag/trap_block_diag): 범위 폭이 큰 날은 덫 조건 전에 −12p 멈춤이 먼저 남(05 ~ 08 두 달마다 11 ~ 23일).
 → 거래마다 '틀렸을 때 나갈 자리(거래 멈춤)'를 정하고, 들 때 그 거리가 S p 안일 때만 듦(S는 사용자 손실 한도 25p에 맞춘 값).
규칙(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · 하루 −25p 봉 안 멈춤 · 그날 마지막 봉 종가 정리 · 1계약 · 편도 0.04p):
  범위 = 그날 첫 N분(N 30 · 60) 고저 · 폭 W
  추세 봇: 종가가 범위 밖으로 b × W 넘게(b 0.25 · 0.5) → 거래 멈춤 = 범위 안쪽 R × W(R 0.25) 자리(산 경우 위끝 − R×W)
    · (종가 − 거래 멈춤) ≤ S 일 때만 듦 · 그날 첫 돌파 한 번만 · 장 끝까지(거래 멈춤 닿으면 덫 봇으로 넘어감)
  덫 봇: 추세 봇 거래 멈춤 자리(종가 기준)에 닿으면 정리 · 그 돌파 뒤 가장 먼 극값(산 경우 돌파 뒤 최고가)을 거래 멈춤으로
    · (극값 − 종가) ≤ S 일 때만 반대로 듦 · 반대쪽 끝 닿으면 이익 정리 · 거래 멈춤(종가가 극값 넘음) 닿으면 정리 · 그날 더 안 듦
  거래 멈춤은 5분봉 종가로 판단 → 다음 봉 시가에 나감(봉 안에서는 하루 −25p 멈춤만)
  격자 8칸: N × b × S(12 · 20)
기간(사전등록 · KMF-0010과 같음): 개발 01-01 ~ 08-31(이미 본 자료) · 확인 09-01 ~ 10-12(비독립 · KMF-0010에서도 씀 · KMF-0011은 실행 안 함) · 채택 = 시험 2만
python3 research/kmf12.py lock | run | cut | contracts"""
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

K.DAY_STOP = -25.0                        # 하루 손실 한도 −25p(사용자 2026-10-13) · simulate · stats가 이 값을 씀
DAY_STOP = K.DAY_STOP
ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0012"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf12.py"]
TF = 5
R = 0.25
MIN_TRADES = 60
DEV = ("20260101", "20260831")
VAL = ("20260901", "20261012")
GUARD_BEFORE = "20260901"                 # 검사(kmf_guard)도 개발 자료(09-01 앞)만
BLOCKS = (("20260101", "20260228"), ("20260301", "20260430"), ("20260501", "20260630"), ("20260701", "20260831"))


def grid():
    return [{"bot": "FIT", "or": n, "b": bb, "S": s, "tag": f"N{n}_b{bb}_S{s}"} for n in (30, 60) for bb in (0.25, 0.5) for s in (12, 20)]


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return K4.day_start_aligned(rows, TF)


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    i = 0
    S = cfg["S"]
    while i < n:
        d = b[i][0]
        j = i
        while j < n and b[j][0] == d:
            j += 1
        start = b[i][1] - (TF - 1)
        hi = lo = None
        pos, state, stop, ext = 0, "wait", None, None     # wait → trend → (trap) → done
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
                for side in (1, -1):
                    brk = c > hi + cfg["b"] * w if side > 0 else c < lo - cfg["b"] * w
                    if not brk:
                        continue
                    st = hi - R * w if side > 0 else lo + R * w
                    if can_enter and side * (c - st) <= S:
                        want[k], pos, state, stop, ext = side, side, "trend", st, (h if side > 0 else l)
                    else:
                        state = "done"                   # 첫 돌파가 너무 멀면 그날 쉼(늦게 들지 않음)
                    break
            elif state == "trend":
                ext = max(ext, h) if pos > 0 else min(ext, l)
                if pos * (c - stop) <= 0:                # 추세 봇 거래 멈춤(종가) → 덫 봇으로
                    if can_enter and pos * (ext - c) <= S:
                        want[k], pos, state, stop = -pos, -pos, "trap", ext
                    else:
                        want[k], pos, state = 0, 0, "done"
            elif state == "trap":
                if (pos < 0 and c <= lo) or (pos > 0 and c >= hi) or pos * (c - stop) <= 0:
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
    두 달 묶음 넷 가운데 셋 이상 + · 값 하나만 바꾼 이웃 셋(N · b · S) 모두 개발 합 > 0."""
    d = res[key]["dev"]
    if not eligible(d):
        return False
    bl = block_sums(d)
    c = res[key]["cfg"]
    nbs = [g for g in grid() if sum(g[x] != c[x] for x in ("or", "b", "S")) == 1]
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


def contract_check():
    """확인 구간 자료(미니 파일 뒤 날 · 10-13 앞)에서 날마다 A056 후보 계약 수 · 코드 · load()가 고른 코드.
    후보가 하루 둘 이상이면 '그날 종일 거래량 1등' 고르기가 미래 참조가 될 수 있으므로 멈춤(KMF-0010 #300 round 1 에서 들인 점검).
    달력 규칙(코드 A05 + 해 끝자리 + 달(1 ~ 9 · A · B · C) + 000 · 그 달 둘째 목요일 만기 · 만기 날부터 다음 달 계약)과도 견줌 — 장 열기 전에 아는 규칙."""
    import csv
    import datetime as dt
    from collections import defaultdict
    mini_last = ""
    with open(K.MINI, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            mini_last = max(mini_last, r["date"])
    codes = defaultdict(set)
    with open(K.FUT, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            d = r["datetime"][:10].replace("-", "")
            m = int(r["datetime"][11:13]) * 60 + int(r["datetime"][14:16])
            if mini_last < d < K.TEST2_FROM and r["code"].startswith("A056") and K.FIRST_MIN <= m <= K.LAST_MIN:
                codes[d].add(r["code"])

    def second_thu(y, mo):
        x = dt.date(y, mo, 1)
        return x + dt.timedelta(days=(3 - x.weekday()) % 7 + 7)

    def cal_code(d):
        x = dt.date(int(d[:4]), int(d[4:6]), int(d[6:]))
        y, mo = x.year, x.month
        if x >= second_thu(y, mo):
            y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
        return f"A05{y % 10}{'0123456789ABC'[mo]}000"
    rows = K._rows_before(K.TEST2_FROM)
    out = []
    for d in sorted(codes):
        out.append({"day": d, "n_codes": len(codes[d]), "codes": sorted(codes[d]), "calendar_code": cal_code(d),
                    "rows_used": sum(1 for r in rows if r[0] == d)})
    ok = all(x["n_codes"] == 1 for x in out)
    return {"mini_last": mini_last, "days": len(out), "all_single": ok,
            "calendar_match": all(x["codes"] == [x["calendar_code"]] for x in out), "per_day": out}


def run():
    """① 개발 8칸(09-01부터 안 읽음) → ② robust 1등 한 칸 → ③ 그 칸만 확인(10-13부터 안 읽음 · 시험 2 자료 안 읽음).
    목표 800p 대비 하루 평균도 보고(판정 아님)."""
    verify_inputs()
    cc = contract_check()
    if not cc["all_single"]:
        sys.exit("확인 구간에 계약 후보가 둘 이상인 날이 있음(멈춤 · 계약 고르기 미래 참조 우려)")
    b = prep(K._rows_before(VAL[0]))
    res = {}
    for cfg in grid():
        log({"status": "STARTED", "key": name(cfg), "stage": "dev", "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        days, trades = K.simulate(b, signals(b, cfg))
        res[name(cfg)] = {"cfg": cfg, "dev": K.stats(days, trades, *DEV)}
        res[name(cfg)]["blocks"] = block_sums(res[name(cfg)]["dev"])
        log({"status": "DONE", "key": name(cfg), "stage": "dev", "dev_total_p": res[name(cfg)]["dev"].get("total_p")})
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
                      "goal_per_day_p": 4.0,
                      "pick": pick and {"name": pick["name"], "dev_total_p": pick["dev"]["total_p"], "dev_per_day_p": pick["dev"]["per_day_p"],
                                        "val_total_p": pick["val"]["total_p"], "val_per_day_p": pick["val"]["per_day_p"], "val_pass": pick["val_pass"]}},
                     ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260504", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf12 as M;"
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
    if sys.argv[1] == "contracts":
        print(json.dumps(contract_check(), ensure_ascii=False, indent=1)); sys.exit()
    {"lock": write_lock, "cut": cut, "run": run}[sys.argv[1]]()
