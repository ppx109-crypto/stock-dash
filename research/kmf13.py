"""KMF-0013 — RNA 추세장 봇(5분봉 · 1분봉 신호 없음) · 하루 손실 한도 −25p · 1계약.
사용자 2026-10-13: "목표 10개월 +1000p" · "추세장봇먼저 RNA로 개발" · "국면을 여러번봐도 좋으니" ·
 "앞뒤잘라서 개발말고 한번에 다 보고 개발해봐 · RNA로 개발하면 앞으로도 적용될거니까 · 그냥 해봐".
→ 개발 = 전체 자료 2026-01-02 ~ 10-12 한 번에(탐색 기록 KMF-0013/explore · 조합 738개) · 결정 = 시험 2(10-13부터 새 자료)만.
규칙(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · 하루 −25p 봉 안 멈춤 · 그날 마지막 봉 종가 정리 · 편도 0.04p):
  선: EMA 4 · 15 · 45 · 90봉(= 20 · 75 · 225 · 450분 · 날 넘어 이어 셈) · 정리선 = 45봉 선
  큰 흐름 = 90봉 선 3봉 기울기 · 역추세 금지
  들기: 정배열(4 > 15 > 45 > 90) + 기울기 > 0 → 삼 / 역배열 + 기울기 < 0 → 팖 · 하루 5번까지 · 새로 들기 15:00 판단까지
  정리: 종가가 45봉 선 반대로 마감 · 또는 들고 난 뒤 가장 좋은 종가에서 4 × ATR(앞 20봉 평균 참 범위 · 그 봉 제외) 넘게 되돌림
  아침 관망: 그날 첫 봉(09:05 전 판단)에 이미 배열이 서 있으면 들지 않고, 그 배열이 정리 조건을 만날 때까지 기다림(하루 들기 1번 씀)
   · 밤사이 이어진 추세에 아침부터 따라 들지 않고 장중에 새로 선 배열만 탐 · round 2에서 숨은 동작을 드러내 적음(결과 같음)
시험 2(판정 · 미리 고정 · round 2):
  자료 = kiwoom-data/mini_1min_test2.csv(10-13부터 · 따로 잠금 PR + GPT 동의 뒤 test2_ok.json에 해시가 적혀야만 엶)
  날 고르기 = 10-13부터 날짜 순으로 '완전한 거래일'만 세어 **처음 20일** 딱 그만큼(더도 덜도 아님)
    완전한 거래일: 09:00 ~ 15:34 안 1분봉 360줄 이상 · 줄 사이 빈 분이 5분 넘는 곳 없음 · 그날 첫 분 ≤ 10:00
    불완전한 날은 손익에서 빼고 목록으로 보고(다음 날로 채움 · 20일 이후 날은 안 셈)
  워밍업 = 개발 자료(10-13 앞 전부)에 이어서 EMA · ATR을 셈(라이브 봇과 같음) · 손익은 고른 20일만 더함
  셈 = 개발과 같은 simulate(다음 봉 시가 · −25p · 마지막 봉 정리 · 편도 0.04p) · 고른 칸 하나만
  PASS = 합 > 0 · 하루 평균 ≥ 1.69p(개발 3.379의 절반) · 가장 나쁜 날 ≥ −25.5p · 아니면 NO_EDGE
  다시 돌리기 막기: evidence/test2.json이 있으면 멈춤
python3 research/kmf13.py lock | report | cut | test2"""
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

K.DAY_STOP = -25.0                        # 하루 손실 한도 −25p(사용자 2026-10-13)
ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0013"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf13.py"]
TF = 5
END = "20261013"                          # 개발 = 이 날 앞 전부 · 시험 2는 이 날부터
GUARD_BEFORE = END
PICK = {"scale": 0.75, "exit": 60, "tr": 4, "max_n": 5}
BASE_MIN = (25, 100, 300, 600)            # 선 길이(분) 기준 · scale배 ÷ 5분


def spans_for(scale):
    return tuple(max(2, int(round(m * scale / TF))) for m in BASE_MIN)


def grid():
    """고른 칸 + 값 하나만 바꾼 이웃(보고 · 검사용)."""
    g = [dict(PICK)]
    for key, vals in (("scale", (0.6, 0.9)), ("exit", (20, 120)), ("tr", (0, 6)), ("max_n", (3, 9))):
        for v in vals:
            c = dict(PICK); c[key] = v; g.append(c)
    for c in g:
        c["tag"] = f"sc{c['scale']}_x{c['exit']}_t{c['tr']}_n{c['max_n']}"
    return g


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return K4.day_start_aligned(rows, TF)


def ema(a, s):
    out = np.empty(len(a)); k = 2 / (s + 1); out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = out[i - 1] + k * (a[i] - out[i - 1])
    out[:s] = np.nan
    return out


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    if n == 0:
        return want
    c = np.array([r[5] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b])
    s1, s2, s3, s4 = spans_for(cfg["scale"])
    E = {1: ema(c, s1), 2: ema(c, s2), 3: ema(c, s3), 4: ema(c, s4), 8: ema(c, s4 * 2)}
    exl = {20: E[2], 60: E[3], 120: E[4], 240: E[8]}[cfg["exit"]]
    pc = np.r_[c[0], c[:-1]]
    trr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc))
    atr = np.full(n, np.nan)
    for i in range(20, n):
        atr[i] = trr[i - 20:i].mean()                 # 앞 20봉(그 봉 제외)
    pos, peak, cnt, day, watch = 0, None, 0, None, False
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt, peak, watch = d, 0, 0, None, False
        if i < 4 or np.isnan(E[4][i - 3]) or np.isnan(atr[i]):
            continue
        slope = E[4][i] - E[4][i - 3]
        up = E[1][i] > E[2][i] > E[3][i] > E[4][i] and slope > 0
        dn = E[1][i] < E[2][i] < E[3][i] < E[4][i] and slope < 0
        if pos:                                       # 든 자리(watch면 '보기만 하는 자리' · 체결 없음)
            peak = max(peak, c[i]) if pos > 0 else min(peak, c[i])
            out = (pos > 0 and c[i] < exl[i]) or (pos < 0 and c[i] > exl[i])
            if cfg["tr"]:
                out = out or (pos > 0 and c[i] < peak - cfg["tr"] * atr[i]) or (pos < 0 and c[i] > peak + cfg["tr"] * atr[i])
            if out:
                if not watch:
                    want[i] = 0
                pos, watch = 0, False
            continue
        if m > K.ENTRY_TO or cnt >= cfg["max_n"]:
            continue
        if up or dn:
            side = 1 if up else -1
            if m < K.ENTRY_FROM:                      # 아침 관망: 첫 봉(09:05 전 판단)에 이미 배열이면 들지 않고
                pos, peak, cnt, watch = side, c[i], cnt + 1, True   # 그 배열이 정리 조건을 만날 때까지 보기만 함(하루 들기 1번 씀)
            else:
                want[i], pos, peak, cnt = side, side, c[i], cnt + 1
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


def concentration(days):
    vs = sorted(days.values(), reverse=True)
    return {"best_day": round(vs[0], 2), "top5_sum": round(sum(vs[:5]), 2), "top10_sum": round(sum(vs[:10]), 2),
            "rest_sum": round(sum(vs[10:]), 2)}


def report():
    """개발(전체 2026-01-02 ~ 10-12) 성적: 고른 칸 + 이웃 · 달 · 국면(그날 효율 · 폭) · 쏠림. 시험 2 자료는 안 읽음."""
    verify_inputs()
    rows = K._rows_before(END)
    b = prep(rows)
    byd = defaultdict(list)
    for r in b:
        byd[r[0]].append(r)
    er = {d: abs(v[-1][5] - v[0][2]) / (sum(abs(v[i][5] - v[i - 1][5]) for i in range(1, len(v))) + 1e-9) for d, v in byd.items()}
    rg = {d: max(x[3] for x in v) - min(x[4] for x in v) for d, v in byd.items()}
    qe = np.quantile(list(er.values()), [1 / 3, 2 / 3]); qr = np.quantile(list(rg.values()), [1 / 3, 2 / 3])
    out = {}
    for cfg in grid():
        days, trades = K.simulate(b, signals(b, cfg))
        st = K.stats(days, trades, "20260101", "20261012")
        g = defaultdict(list); gr = defaultdict(list)
        for d, v in days.items():
            g["추세일" if er[d] >= qe[1] else "횡보일" if er[d] < qe[0] else "중간일"].append(v)
            gr["폭 큼" if rg[d] >= qr[1] else "폭 작음" if rg[d] < qr[0] else "폭 중간"].append(v)
        st["regime_er"] = {k: [len(v), round(sum(v), 2)] for k, v in sorted(g.items())}
        st["regime_range"] = {k: [len(v), round(sum(v), 2)] for k, v in sorted(gr.items())}
        st["concentration"] = concentration(days)
        st["extra_cost_0.1"] = round(st["total_p"] - 0.1 * len(trades), 2)
        out[name(cfg)] = st
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    p = out[name(grid()[0])]
    print(json.dumps({"pick": name(grid()[0]), "total_p": p["total_p"], "per_day_p": p["per_day_p"], "months": p["months"],
                      "neighbors_total": {k: v["total_p"] for k, v in out.items()}}, ensure_ascii=False))


TEST2_N = 20
TEST2_OK = BOX / "test2_ok.json"          # 데이터 잠금 PR · GPT 동의 뒤에만 만듦: {"gpt_pr": 번호, "data_sha256": "..."}
TEST2_OUT = BOX / "evidence/test2.json"


def complete_days(rows, start=K.TEST2_FROM):
    """완전한 거래일(1분봉 기준) 목록과 빠진 날 사유."""
    byd = defaultdict(list)
    for r in rows:
        if r[0] >= start:
            byd[r[0]].append(r[1])
    good, bad = [], {}
    for d in sorted(byd):
        ms = sorted(byd[d])
        gaps = max((b2 - a for a, b2 in zip(ms, ms[1:])), default=0)
        if len(ms) >= 360 and gaps <= 5 and ms[0] <= 600:
            good.append(d)
        else:
            bad[d] = {"rows": len(ms), "max_gap": gaps, "first_min": ms[0]}
    return good, bad


def test2():
    """시험 2 한 번(고른 칸 하나 · 처음 완전한 20일). 데이터 잠금 동의(test2_ok.json) 없으면 멈춤 · 이미 했으면 멈춤."""
    verify_inputs()
    if TEST2_OUT.exists():
        sys.exit("시험 2는 이미 했음(다시 안 돌림)")
    if not TEST2_OK.exists() or not K.TEST2_FILE.exists():
        sys.exit("시험 2 자료 잠금 동의(test2_ok.json) 또는 자료가 없음(멈춤)")
    ok = json.loads(TEST2_OK.read_text())
    if hashlib.sha256(K.TEST2_FILE.read_bytes()).hexdigest() != ok["data_sha256"]:
        sys.exit("시험 2 자료 해시가 잠금과 다름(멈춤)")
    rows = K.load()                                       # 개발 자료 + 시험 2 자료(10-13부터) · 워밍업은 이어서
    good, bad = complete_days(rows)
    if len(good) < TEST2_N:
        sys.exit(f"완전한 거래일 {len(good)}일 < {TEST2_N}일(멈춤 · 아직 판정 안 함)")
    pick_days = good[:TEST2_N]
    last = pick_days[-1]
    rows = [r for r in rows if r[0] <= last]              # 20번째 날 뒤 자료는 셈에 안 넣음
    b = prep(rows)
    days, trades = K.simulate(b, signals(b, grid()[0]))
    sel = {d: days.get(d, 0.0) for d in pick_days}
    tr = [t for t in trades if t[0] in sel]
    st = K.stats(sel, tr, pick_days[0], last)
    passed = st["total_p"] > 0 and st["per_day_p"] >= 1.69 and st["worst_day_p"] >= -25.5
    out = {"verdict": "PASS" if passed else "NO_EDGE", "pick": name(grid()[0]), "days": pick_days,
           "excluded_incomplete": {d: v for d, v in bad.items() if d <= last}, "stats": st, "data_sha256": ok["data_sha256"]}
    TEST2_OUT.parent.mkdir(parents=True, exist_ok=True)
    TEST2_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in ("verdict", "pick")} | {"total_p": st["total_p"], "per_day_p": st["per_day_p"]}, ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260601", "20260901")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf13 as M;"
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
