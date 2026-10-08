"""BACKTEST-REPAIR-0001 · 1일봉 '새 82' 신호 재생(기존 연구 엔진 그대로 · 함수만 바꿔 끼움).
python3 d1_signals.py <기준점 폴더(00b98ab1)> <nrl 캐시> <출력 폴더>
판: ASIS(원본) · K1(수급 끝 하루 앞으로 = RULES-0002 FLOW-LAG2) · K2(calm 달별 문턱 = 그 달 앞 자료만) · FIX(K1 + K2).
출력: d1_ledger_<판>.csv = code, entry, exit, pnl_pct_engine(엔진 손익 · 참고만), slots."""
import bisect
import csv
import json
import os
import socket
import sys
import time
from pathlib import Path

BASE, CACHE, OUT = str(Path(sys.argv[1]).resolve()), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지(연구 재생)")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
os.environ["NRL_CACHE"] = CACHE
os.environ.pop("CAPS_ADJ", None)                      # 운영과 같은 raw 시총(캐시도 raw)
os.chdir(BASE)
sys.path[:0] = [BASE, BASE + "/research"]
t0 = time.time()
import final_group, final_study, caps, lab, rule, study  # noqa: E402,F401
import nrl  # noqa: E402
sys.path[:] = [p for p in sys.path if p not in ("/home/user/stock-dash", "/home/user/stock-dash/research")]
import ntools as T  # noqa: E402

ORIG_TEACHER, ORIG_STEADY, ORIG_HOLDS = nrl.teacher, nrl.steady, rule.holds
FULL_CALM = rule._calm


def flow_patch(shift):
    """RULES-0002 d1_diag.flow_patch와 같은 식: 수급 끝을 shift줄 더 앞으로."""
    def teacher(row, n=5):
        f, t, p = (nrl.flow_sum(row, n, c, lag=1 + shift) for c in ("외국인", "투신", "개인"))
        return None not in (f, t, p) and f > 0 and t > 0 and p < 0

    def steady(r, n=3):
        got = nrl.FLOW.get(r["code"])
        if not got:
            return 0
        days, acc, ok, _ = got
        k = bisect.bisect_left(days, r["date"]) - shift
        if k < n:
            return 0
        return sum(1 for j in range(k - n + 1, k + 1)
                   if acc["외국인"][j] - acc["외국인"][j - 1] > 0 and acc["투신"][j] - acc["투신"][j - 1] > 0)
    return teacher, steady


def holds_monthly(r):
    """K2: 그 달 첫날 앞 자료로만 잰 calm 문턱(dguard layer9와 같은 바꿔 끼우기)."""
    edge = (nrl.CALM_MONTH or {}).get(r["date"][:6])
    if edge is None:
        raise RuntimeError(f"달별 calm 문턱 없음: {r['date'][:6]}")
    rule._calm = edge
    try:
        return ORIG_HOLDS(r)
    finally:
        rule._calm = FULL_CALM


t_s0, s_s0 = flow_patch(0)
mism = sum(1 for r in nrl.inside if t_s0(r) != ORIG_TEACHER(r) or s_s0(r) != ORIG_STEADY(r))
assert mism == 0, "수급 함수 옮김 오류"

SPECS = [("ASIS", 0, False), ("K1", 1, False), ("K2", 0, True), ("FIX", 1, True)]
summary = {"base": BASE, "cache": CACHE, "calm_full": FULL_CALM, "calm_month_n": len(nrl.CALM_MONTH or {}), "runs": {}}
for name, shift, monthly in SPECS:
    nrl.teacher, nrl.steady = flow_patch(shift) if shift else (ORIG_TEACHER, ORIG_STEADY)
    rule.holds = holds_monthly if monthly else ORIG_HOLDS
    got = T.once(name)
    rows = [(t["code"], t["산 날"], t["판 날"], float(t["손익"]), int(t.get("자리") or 1))
            for s in ("앞", "뒤") for t in (got.get(s) or {}).get("매매목록", [])]
    with open(OUT / f"d1_ledger_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "entry", "exit", "pnl_pct_engine", "slots"])
        w.writerows(rows)
    summary["runs"][name] = {"rows": len(rows), "codes": len({r[0] for r in rows}),
                             "engine": {s: {k: (got.get(s) or {}).get(k) for k in ("매매", "연수익", "최대낙폭", "승률")} for s in ("앞", "뒤")}}
    print(name, len(rows), round(time.time() - t0), "초", flush=True)
nrl.teacher, nrl.steady, rule.holds = ORIG_TEACHER, ORIG_STEADY, ORIG_HOLDS
summary["seconds"] = round(time.time() - t0)
(OUT / "d1_signals_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
