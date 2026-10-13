"""KMF-0017 — 한 계약 봇 + 이익 잠금: 추세 봇(KMF-0013) 우선 · 아니면 횡보 봇(KMF-0014) · 둘 다 쉬면 시간대 봇(KMF-0015)
 · 그날 손익이 +L 넘은 뒤 최고치에서 G 넘게 내려오면 정리하고 그날 끝 · 5분봉 · 하루 −25p · 1계약.
사용자 2026-10-13: "177일은 +94p 너무 적어 · 177일만 갖고 더 연구해보자"(KMF-0016 위 10일 뺀 177일).
규칙(세 봇 규칙은 그대로 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · −25p는 계좌 하나에 한 번 · 편도 0.04p):
  원하는 자리 = 추세 봇 의도(0 아니면) → 횡보 봇 의도 → 시간대 봇 의도 → 0
  이익 잠금: 신호 코드가 실제 체결(다음 봉 시가 · simulate와 같은 셈)을 따라가며 그날 손익(실현 + 종가 평가 · 비용 포함)을 셈
   그날 최고치 ≥ L(40) 이고 지금 ≤ 최고치 − G(15) 이면 → 정리(0) · 그날 더 안 듦
개발 = 전체 자료 2026-01-02 ~ 10-12 · 판정 = 시험 2(10-14부터 완전한 거래일 처음 20일 · 수급 점검 · 영수증은 KMF-0015와 같음)
python3 research/kmf17.py lock | report | cut | test2"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf13 as M13  # noqa: E402
import kmf14 as M14  # noqa: E402
import kmf15 as M15  # noqa: E402
import kmf16 as M16  # noqa: E402

K.DAY_STOP = -25.0
ROOT = K.ROOT
BOX = ROOT / "research-exchange/claude-to-gpt/KMF-0017"
LOCK = BOX / "input_lock.json"
CODE_FILES = ["research/kmf.py", "research/kmf4.py", "research/kmf13.py", "research/kmf14.py", "research/kmf15.py", "research/kmf16.py", "research/kmf17.py"]
END = M13.END
GUARD_BEFORE = END
PICK = {"W": 1, "L": 40, "G": 15}
TEST2_MIN_PER_DAY = 2.29                   # 개발 하루 평균 4.586의 절반 2.293(PLAN §4)


def grid():
    g = [dict(PICK), dict(PICK, W=0), dict(PICK, L=50), dict(PICK, G=10), dict(PICK, G=20), dict(PICK, L=0, G=0)]
    for c in g:
        c["tag"] = f"W{c['W']}_L{c['L']}_G{c['G']}"
    return g


def name(cfg):
    return cfg["tag"]


def prep(rows, cfg=None):
    return M13.prep(rows)


def signals(b, cfg):
    n = len(b)
    want = [None] * n
    if n == 0:
        return want
    T = M16.intent(b, M13.signals(b, M13.grid()[0]))
    R = M16.intent(b, M14.signals(b, M14.grid()[0]))
    W = M16.intent(b, M15.signals(b, M15.grid()[0])) if cfg["W"] else [0] * n
    i = 0
    while i < n:
        d = b[i][0]; j = i
        while j < n and b[j][0] == d:
            j += 1
        pos, entry, real, peak, halt, done, last, pend = 0, 0.0, 0.0, 0.0, False, False, 0, None
        for k in range(i, j):
            o, h, l, c, m = b[k][2], b[k][3], b[k][4], b[k][5], b[k][1]
            # ① 앞 봉 판단을 이 봉 시가에 체결(K.simulate와 같은 셈)
            if pend is not None and not done and m <= K.FLAT_AT:
                tgt, pm = pend
                if tgt != pos:
                    if pos:
                        real += pos * (o - entry) - K.COST; pos = 0
                    if tgt and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > K.DAY_STOP:
                        pos, entry = tgt, o; real -= K.COST
            pend = None
            # ② 하루 −25p 멈춤(봉 안) — 걸리면 그날 끝
            if pos and not done:
                sp = entry + pos * (K.DAY_STOP - real + K.COST)
                if (l <= sp) if pos > 0 else (h >= sp):
                    px = min(o, sp) if pos > 0 else max(o, sp)
                    real += pos * (px - entry) - K.COST; pos = 0; done = True
            if done or m >= K.FLAT_AT:
                continue
            # ③ 봉 종가: 그날 손익 · 이익 잠금
            mtm = real + (pos * (c - entry) - K.COST if pos else 0.0)
            peak = max(peak, mtm)
            if cfg["L"] and peak >= cfg["L"] and mtm <= peak - cfg["G"]:
                halt = True
            tgt = 0 if halt else (T[k] or R[k] or W[k])
            if tgt != last:
                want[k] = tgt; last = tgt
            pend = (tgt, m)
        i = j
    return want


def lock_body():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    body = {f: sha(ROOT / f) for f in CODE_FILES}
    body.update({f"kiwoom-data/{p.name}": sha(p) for p in (K.MINI, K.FUT)})
    body["market-data/investor_KSP.json"] = sha(M15.FLOW)
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


TOP10_KMF16 = ["20260623", "20260703", "20260702", "20260515", "20260513", "20260528", "20260303", "20260728", "20260202", "20260521"]


def report():
    verify_inputs()
    b = prep(K._rows_before(END))
    out = {}
    for cfg in grid():
        days, trades = K.simulate(b, signals(b, cfg))
        st = K.stats(days, trades, "20260101", "20261012")
        vs = sorted(days.values(), reverse=True)
        rest = {d: v for d, v in days.items() if d not in TOP10_KMF16}
        st["rest177"] = {"total": round(sum(rest.values()), 2), "front_01_05": round(sum(v for d, v in rest.items() if d < "20260601"), 2),
                         "back_06_10": round(sum(v for d, v in rest.items() if d >= "20260601"), 2)}
        st["concentration"] = {"top10_sum": round(sum(vs[:10]), 2), "ex_own_top10": round(sum(vs[10:]), 2)}
        out[name(cfg)] = st
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/dev_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    p = out[name(grid()[0])]
    print(json.dumps({"pick": name(grid()[0]), "total_p": p["total_p"], "per_day_p": p["per_day_p"], "rest177": p["rest177"],
                      "concentration": p["concentration"], "neighbors": {k: [v["total_p"], v["rest177"]["total"]] for k, v in out.items()}}, ensure_ascii=False))


TEST2_N = 20
TEST2_FROM = M15.TEST2_FROM                 # 10-14(시간대 봇의 수급 자료 · KMF-0015와 같음)
TEST2_OK = BOX / "test2_ok.json"
TEST2_OUT = BOX / "evidence/test2.json"


def test2():
    """시험 2 한 번: KMF-0015와 같은 수급 점검(앞 21거래일 줄 · 처음 커밋 ≤ 09:00 · 정정 없음 · 영수증 SHA 잠금) · 날 고르기 · 결손일 처리."""
    verify_inputs()
    if TEST2_OUT.exists():
        sys.exit("시험 2는 이미 했음(다시 안 돌림)")
    if not TEST2_OK.exists() or not K.TEST2_FILE.exists():
        sys.exit("시험 2 자료 잠금 동의(test2_ok.json) 또는 자료가 없음(멈춤)")
    ok = json.loads(TEST2_OK.read_text())
    if hashlib.sha256(K.TEST2_FILE.read_bytes()).hexdigest() != ok["data_sha256"]:
        sys.exit("시험 2 자료 해시가 잠금과 다름(멈춤)")
    if hashlib.sha256(M15.FLOW.read_bytes()).hexdigest() != ok.get("flow_sha256"):
        sys.exit("NEEDS_DATA: 수급 자료 해시가 시험 2 잠금과 다름(멈춤)")
    if not M15.RECEIPT.exists():
        sys.exit("NEEDS_DATA: 수급 영수증 없음(멈춤)")
    receipt_sha = M15.receipt_check(ok)
    rows = K.load()
    good, bad = M13.complete_days(rows, start=TEST2_FROM)
    if len(good) < TEST2_N:
        sys.exit(f"완전한 거래일 {len(good)}일 < {TEST2_N}일(멈춤)")
    pick_days = good[:TEST2_N]
    last = pick_days[-1]
    flow_dates = [r["date"] for r in json.loads(M15.FLOW.read_text())["rows"]]
    problems, used = M15.flow_ready(pick_days, sorted({r[0] for r in rows}), flow_dates, json.loads(M15.RECEIPT.read_text()))
    if problems:
        sys.exit("NEEDS_DATA: 수급 자료 문제(판정 안 함) " + json.dumps(problems[:20], ensure_ascii=False))
    b = prep(M13.test2_rows(rows, pick_days))
    days, trades = K.simulate(b, signals(b, grid()[0]))
    sel = {d: days.get(d, 0.0) for d in pick_days}
    st = K.stats(sel, [t for t in trades if t[0] in sel], pick_days[0], last)
    passed = st["total_p"] > 0 and st["per_day_p"] >= TEST2_MIN_PER_DAY and st["worst_day_p"] >= -25.5
    out = {"verdict": "PASS" if passed else "NO_EDGE", "pick": name(grid()[0]), "days": pick_days,
           "excluded_incomplete": {d: v for d, v in bad.items() if d <= last}, "stats": st, "data_sha256": ok["data_sha256"],
           "flow_sha256": ok["flow_sha256"], "flow_dates_used": {d: used[d][-1] for d in pick_days}, "receipt_sha256": receipt_sha}
    TEST2_OUT.parent.mkdir(parents=True, exist_ok=True)
    TEST2_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": out["verdict"], "total_p": st["total_p"], "per_day_p": st["per_day_p"]}, ensure_ascii=False))


def cut():
    cuts = ("20260302", "20260601", "20260901")
    code = ("import os,sys,json;sys.path.insert(0,'research');import kmf as K;import kmf17 as M;"
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
