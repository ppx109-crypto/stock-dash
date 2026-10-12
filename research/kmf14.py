"""KMF-0014 — RNA 횡보장 봇(5분봉 · 1분봉 신호 없음) · 하루 손실 한도 −25p · 1계약.
사용자 2026-10-13: "횡보장봇도 RNA로 개발해봐" · 개발 = 전체 자료 2026-01-02 ~ 10-12 한 번에(탐색 기록 KMF-0014/explore) · 판정 = 시험 2만.
규칙(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · 하루 −25p 봉 안 멈춤 · 그날 마지막 봉 종가 정리 · 편도 0.04p):
  이격도 disp = 종가 ÷ EMA15 − 1 · 이격밴드 z = disp가 앞 120봉(그 봉 제외) 평균에서 몇 표준편차인지(한투 1일봉 RNA의 이격밴드)
  횡보 거름(RNA): 큰 흐름 선(EMA90)의 3봉 기울기 크기 < 0.8 × ATR(앞 20봉 평균 참 범위 · 그 봉 제외)
  들기: 거름 켜졌을 때 z ≥ +2.0이면 팖 · z ≤ −2.0이면 삼 · 09:05 ~ 15:00 판단 · 하루 3번까지
  나가기: 들 때 값에서 종가가 3 × ATR 넘게 불리하면 정리 · 아니면 그날 마지막 봉까지 들고 감(평균 돌아옴 나가기는 없음 · 탐색에서 약했음)
시험 2(판정 · KMF-0013과 같은 계약): 완전한 거래일 처음 20일 · 워밍업 = 개발 자료에 이어서 · 결손일은 상태에서도 뺌
  PASS = 합 > 0 · 하루 평균 ≥ 개발의 절반 · 가장 나쁜 날 ≥ −25.5p
python3 research/kmf14.py lock | report | cut | test2"""
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf4 as K4  # noqa: E402
import kmf13 as M13  # noqa: E402  (ema · complete_days · test2_rows · 추세 봇 함께 셈)

K.DAY_STOP = -25.0
ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0014"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf13.py", "research/kmf14.py"]
TF = 5
END = M13.END
GUARD_BEFORE = END
PICK = {"L": 15, "W": 120, "f": 0.8, "k": 2.0, "s": 3.0, "n": 3}
DEV_PER_DAY = None                         # report()가 채움 · 시험 2 잣대는 PLAN에 숫자로 고정
TEST2_MIN_PER_DAY = 1.09                   # 개발 하루 평균 2.172의 절반(반올림 · PLAN §4)


def grid():
    g = [dict(PICK)]
    for key, vals in (("L", (10, 25)), ("W", (90, 180)), ("f", (0.6, 1.0)), ("k", (1.5, 2.5)), ("s", (2.0, 4.0))):
        for v in vals:
            c = dict(PICK); c[key] = v; g.append(c)
    for c in g:
        c["tag"] = f"L{c['L']}_W{c['W']}_f{c['f']}_k{c['k']}_s{c['s']}"
    return g


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return K4.day_start_aligned(rows, TF)


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    if n == 0:
        return want
    c = np.array([r[5] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b])
    e90 = M13.ema(c, 90)
    disp = c / M13.ema(c, cfg["L"]) - 1
    W = cfg["W"]
    z = np.full(n, np.nan)
    for i in range(W, n):
        w = disp[i - W:i]                               # 앞 W봉(그 봉 제외)
        if np.isnan(w).any() or np.isnan(disp[i]):
            continue
        sd = w.std()
        z[i] = (disp[i] - w.mean()) / sd if sd > 0 else 0.0
    pc = np.r_[c[0], c[:-1]]
    trr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc))
    atr = np.full(n, np.nan)
    for i in range(20, n):
        atr[i] = trr[i - 20:i].mean()
    pos, ent, cnt, day = 0, None, 0, None
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt = d, 0, 0
        if i < 3 or np.isnan(z[i]) or np.isnan(atr[i]) or np.isnan(e90[i - 3]):
            continue
        if pos:
            if pos * (c[i] - ent) <= -cfg["s"] * atr[i]:
                want[i], pos = 0, 0
            continue
        if m < K.ENTRY_FROM or m > K.ENTRY_TO or cnt >= cfg["n"]:
            continue
        if abs(e90[i] - e90[i - 3]) < cfg["f"] * atr[i] and abs(z[i]) >= cfg["k"]:
            side = -1 if z[i] > 0 else 1
            want[i], pos, ent, cnt = side, side, c[i], cnt + 1
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


def report():
    """개발(전체) 성적: 고른 칸 + 이웃 10 · 달 · 국면 · 쏠림 · KMF-0013 추세 봇과 함께(두 계약 · 날별 합)."""
    verify_inputs()
    b = prep(K._rows_before(END))
    byd = defaultdict(list)
    for r in b:
        byd[r[0]].append(r)
    er = {d: abs(v[-1][5] - v[0][2]) / (sum(abs(v[i][5] - v[i - 1][5]) for i in range(1, len(v))) + 1e-9) for d, v in byd.items()}
    qe = np.quantile(list(er.values()), [1 / 3, 2 / 3])
    d13, _ = K.simulate(b, M13.signals(b, M13.grid()[0]))
    top13 = set(sorted(d13, key=lambda d: -d13[d])[:10])
    out = {}
    for cfg in grid():
        days, trades = K.simulate(b, signals(b, cfg))
        st = K.stats(days, trades, "20260101", "20261012")
        g = defaultdict(list)
        for d, v in days.items():
            g["추세일" if er[d] >= qe[1] else "횡보일" if er[d] < qe[0] else "중간일"].append(v)
        st["regime_er"] = {k: [len(v), round(sum(v), 2)] for k, v in sorted(g.items())}
        vs = sorted(days.values(), reverse=True)
        st["concentration"] = {"top10_sum": round(sum(vs[:10]), 2), "rest_sum": round(sum(vs[10:]), 2)}
        both = {d: days[d] + d13[d] for d in days}
        bv = sorted(both.values(), reverse=True)
        st["with_kmf13"] = {"total": round(sum(bv), 2), "ex_own_top10": round(sum(bv[10:]), 2),
                            "ex_kmf13_top10_days": round(sum(v for d, v in both.items() if d not in top13), 2),
                            "worst_day": round(min(bv), 2), "on_kmf13_loss_days": round(sum(days[d] for d in days if d13[d] < 0), 2),
                            "corr": round(float(np.corrcoef([days[d] for d in sorted(days)], [d13[d] for d in sorted(days)])[0, 1]), 3)}
        out[name(cfg)] = st
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    p = out[name(grid()[0])]
    print(json.dumps({"pick": name(grid()[0]), "total_p": p["total_p"], "per_day_p": p["per_day_p"], "months": p["months"],
                      "with_kmf13": p["with_kmf13"], "neighbors_total": {k: v["total_p"] for k, v in out.items()}}, ensure_ascii=False))


TEST2_N = 20
TEST2_OK = BOX / "test2_ok.json"
TEST2_OUT = BOX / "evidence/test2.json"


def test2():
    """시험 2 한 번(KMF-0013과 같은 날 고르기 · 워밍업 · 결손일 처리 · 다시 돌리기 막기)."""
    verify_inputs()
    if TEST2_OUT.exists():
        sys.exit("시험 2는 이미 했음(다시 안 돌림)")
    if not TEST2_OK.exists() or not K.TEST2_FILE.exists():
        sys.exit("시험 2 자료 잠금 동의(test2_ok.json) 또는 자료가 없음(멈춤)")
    ok = json.loads(TEST2_OK.read_text())
    if hashlib.sha256(K.TEST2_FILE.read_bytes()).hexdigest() != ok["data_sha256"]:
        sys.exit("시험 2 자료 해시가 잠금과 다름(멈춤)")
    rows = K.load()
    good, bad = M13.complete_days(rows)
    if len(good) < TEST2_N:
        sys.exit(f"완전한 거래일 {len(good)}일 < {TEST2_N}일(멈춤 · 아직 판정 안 함)")
    pick_days = good[:TEST2_N]
    last = pick_days[-1]
    b = prep(M13.test2_rows(rows, pick_days))
    days, trades = K.simulate(b, signals(b, grid()[0]))
    sel = {d: days.get(d, 0.0) for d in pick_days}
    st = K.stats(sel, [t for t in trades if t[0] in sel], pick_days[0], last)
    passed = st["total_p"] > 0 and st["per_day_p"] >= TEST2_MIN_PER_DAY and st["worst_day_p"] >= -25.5
    out = {"verdict": "PASS" if passed else "NO_EDGE", "pick": name(grid()[0]), "days": pick_days,
           "excluded_incomplete": {d: v for d, v in bad.items() if d <= last}, "stats": st, "data_sha256": ok["data_sha256"]}
    TEST2_OUT.parent.mkdir(parents=True, exist_ok=True)
    TEST2_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": out["verdict"], "total_p": st["total_p"], "per_day_p": st["per_day_p"]}, ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260601", "20260901")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf14 as M;"
            "c=json.loads(os.environ['KC']);b=M.prep(K.load());d,_=K.simulate(b,M.signals(b,c));print(json.dumps(d))")
    res = []
    for cfg in grid():
        env = dict(os.environ, KC=json.dumps(cfg), KMF_CUT=END)
        full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for ct in cuts:
            env["KMF_CUT"] = ct
            part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in part if d < ct]
            res.append({"cfg": name(cfg), "cut": ct, "days": len(ds), "diff": sum(1 for d in ds if abs(part[d] - full[d]) > 1e-9),
                        "no_future_days": all(d < ct for d in part)})
    print(json.dumps({"pass": all(r["diff"] == 0 and r["no_future_days"] for r in res), "runs": res}, ensure_ascii=False))


if __name__ == "__main__":
    {"lock": write_lock, "cut": cut, "report": report, "test2": test2}[sys.argv[1]]()
