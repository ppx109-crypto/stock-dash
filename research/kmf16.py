"""KMF-0016 — 한 계약 봇: 추세일 땐 추세 봇(KMF-0013) · 횡보일 땐 횡보 봇(KMF-0014) · 5분봉 · 하루 −25p · 1계약.
사용자 2026-10-13: "계약1개로하자 · 추세봇일때는 추세봇을 횡보일대는횡보봇을".
규칙(고정 · 두 봇 규칙은 KMF-0013 · 0014 그대로 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · −25p는 계좌 하나에 한 번 · 편도 0.04p):
  봉마다 두 봇의 '원하는 자리'(그날 마지막 신호 값 · 그날 처음엔 0)를 만듦
  추세 봇 우선: 추세 봇이 자리(+1 / −1)를 원하면 그 자리 · 아니면 횡보 봇이 원하는 자리 · 둘 다 0이면 정리
  합친 자리가 바뀐 봉에서만 신호(뒤집기 포함)
  (견준 다른 규칙: 먼저 든 봇 따르기 · 횡보 봇 우선 — 탐색 explore/one_lab.py · 보고만)
개발 = 전체 자료 2026-01-02 ~ 10-12 · 판정 = 시험 2(10-13부터 완전한 거래일 처음 20일 · KMF-0013과 같은 계약)
python3 research/kmf16.py lock | report | cut | test2"""
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
import kmf13 as M13  # noqa: E402
import kmf14 as M14  # noqa: E402

K.DAY_STOP = -25.0
ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0016"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf13.py", "research/kmf14.py", "research/kmf16.py"]
END = M13.END
GUARD_BEFORE = END
TEST2_MIN_PER_DAY = 2.32                   # 개발 하루 평균 4.637의 절반 2.3185(PLAN §4)


def grid():
    return [{"rule": r, "tag": f"one_{r}"} for r in ("trend", "first", "range")]


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return M13.prep(rows)


def intent(b, want):
    out, cur, day = [], 0, None
    for i, x in enumerate(want):
        if b[i][0] != day:
            day, cur = b[i][0], 0
        if x in (1, -1, 0):
            cur = x
        out.append(cur)
    return out


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    if n == 0:
        return want
    T = intent(b, M13.signals(b, M13.grid()[0]))
    R = intent(b, M14.signals(b, M14.grid()[0]))
    prev, holder, day = 0, None, None
    for i in range(n):
        if b[i][0] != day:
            day, prev, holder = b[i][0], 0, None
        t, r = T[i], R[i]
        if cfg["rule"] == "trend":
            tgt = t if t else r
        elif cfg["rule"] == "range":
            tgt = r if r else t
        else:                                            # first: 먼저 든 봇이 정리할 때까지
            if holder == "T" and t == 0 or holder == "R" and r == 0:
                holder = None
            if holder is None:
                holder = "T" if t else ("R" if r else None)
            tgt = {"T": t, "R": r, None: 0}[holder]
        if tgt != prev:
            want[i] = tgt
            prev = tgt
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
    verify_inputs()
    b = prep(K._rows_before(END))
    byd = defaultdict(list)
    for r in b:
        byd[r[0]].append(r)
    er = {d: abs(v[-1][5] - v[0][2]) / (sum(abs(v[i][5] - v[i - 1][5]) for i in range(1, len(v))) + 1e-9) for d, v in byd.items()}
    qe = np.quantile(list(er.values()), [1 / 3, 2 / 3])
    d13, _ = K.simulate(b, M13.signals(b, M13.grid()[0]))
    d14, _ = K.simulate(b, M14.signals(b, M14.grid()[0]))
    top13 = set(sorted(d13, key=lambda d: -d13[d])[:10])
    out = {"separate": {"kmf13": round(sum(d13.values()), 2), "kmf14": round(sum(d14.values()), 2),
                        "two_contracts": round(sum(d13[d] + d14[d] for d in d13), 2)}}
    for cfg in grid():
        days, trades = K.simulate(b, signals(b, cfg))
        st = K.stats(days, trades, "20260101", "20261012")
        g = defaultdict(list)
        for d, v in days.items():
            g["추세일" if er[d] >= qe[1] else "횡보일" if er[d] < qe[0] else "중간일"].append(v)
        st["regime_er"] = {k: [len(v), round(sum(v), 2)] for k, v in sorted(g.items())}
        vs = sorted(days.values(), reverse=True)
        st["concentration"] = {"top10_sum": round(sum(vs[:10]), 2), "rest_sum": round(sum(vs[10:]), 2),
                               "ex_kmf13_top10_days": round(sum(v for d, v in days.items() if d not in top13), 2)}
        out[name(cfg)] = st
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    p = out[name(grid()[0])]
    print(json.dumps({"pick": name(grid()[0]), "total_p": p["total_p"], "per_day_p": p["per_day_p"], "concentration": p["concentration"],
                      "others": {k: v["total_p"] for k, v in out.items() if k.startswith("one_")}, "separate": out["separate"]}, ensure_ascii=False))


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
        sys.exit(f"완전한 거래일 {len(good)}일 < {TEST2_N}일(멈춤)")
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
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf16 as M;"
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
