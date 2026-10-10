"""RULES-0002 D1 진단 재생 — 1일봉 '새 82' 연구 엔진(nrl · ntools.once)으로 ASIS · FLOAT-V1 · FLOW-LAG2 · FLOW-LAG3를 한 번에 하나씩.
python d1_diag.py <꺼낸 폴더> <nrl 캐시> <결과 폴더>"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as K  # noqa: E402

BASE, CACHE, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
import os  # noqa: E402
os.environ["NRL_CACHE"] = CACHE
os.environ.pop("CAPS_ADJ", None)                     # 운영과 같은 raw 시총(캐시도 raw)
BASE = K.lock_base(BASE)
t0 = time.time()
# 기준점 폴더 모듈을 먼저 불러 sys.modules에 고정(nrl이 운영 폴더 경로를 앞에 넣어도 이미 불린 모듈을 씀)
import final_group, final_study, caps, lab, rule, study  # noqa: E402,F401
import nrl  # noqa: E402
sys.path[:] = [p for p in sys.path if p not in ("/home/user/stock-dash", "/home/user/stock-dash/research")]
import ntools as T  # noqa: E402
import a_mtm  # noqa: E402
import perf2 as P  # noqa: E402
from z058 import recost  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

LOG = []          # 두 식이 다른 청산 판단


def logdiff(run, rule_id, lane, start, step, price, close, f, x):
    if f != x:
        LOG.append({"run": run, "rule": rule_id, "code": lane["code"], "entry_day": lane["날"][start], "day": lane["날"][start + step],
                    "step": step, "price": price, "close": close, "float": bool(f), "exact": bool(x)})


EVAL = {}


def count(run, key):
    EVAL[(run, key)] = EVAL.get((run, key), 0) + 1


def make_exit(mode, run):
    asis = mode == "asis"

    def half(lane, start, price, step, peak, row=None):
        c = lane["closes"][start + step]
        now = (c / price - 1) * 100
        count(run, "trend_eval")
        f_t, x_t = now >= 13, K.ge(c, price, 13)
        f_s, x_s = now <= -5, K.le(c, price, -5)
        logdiff(run, "trend_tp13", lane, start, step, price, c, f_t, x_t)
        logdiff(run, "trend_sl5", lane, start, step, price, c, f_s, x_s)
        take, stop = (f_t, f_s) if asis else (x_t, x_s)
        if take or stop or step >= 10:
            return True
        cl = lane["closes"]
        mx = max(cl[start + k] for k in range(0, step))
        f_c = now >= 5 and max((cl[start + k] / price - 1) * 100 for k in range(0, step)) < 5
        x_c = K.ge(c, price, 5) and K.lt(mx, price, 5)
        logdiff(run, "trend_half5_first", lane, start, step, price, c, f_c, x_c)
        if f_c if asis else x_c:
            return max(1, nrl.BASE_SIZE(row) // 2)
        return False

    def broken(lane, start, price, step, peak, row=None):
        spot = start + step
        c = lane["closes"][spot]
        count(run, "aligned_eval")
        f_s, x_s = (c / price - 1) * 100 <= -10, K.le(c, price, -10)
        logdiff(run, "aligned_sl10", lane, start, step, price, c, f_s, x_s)
        if f_s if asis else x_s:
            return True
        f_p = (peak / price - 1) * 100 >= 8 and (c / price - 1) * 100 <= 1
        x_p = K.ge(peak, price, 8) and K.le(c, price, 1)
        logdiff(run, "aligned_peak8_now1", lane, start, step, price, c, f_p, x_p)
        if f_p if asis else x_p:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]

    return lab.exit_per_tier(nrl.tier, {"규칙": half, "정배열": broken})


import bisect  # noqa: E402
ORIG_TEACHER, ORIG_STEADY = nrl.teacher, nrl.steady


def flow_patch(shift):
    """수급 끝을 shift줄 더 앞으로(0 = 원본)."""
    def teacher(row, n=5):
        f, t, p = (nrl.flow_sum(row, n, c, lag=1 + shift) for c in ("외국인", "투신", "개인"))
        return None not in (f, t, p) and f > 0 and t > 0 and p < 0

    def steady(r, n=3):
        got = nrl.FLOW.get(r["code"])
        if not got:
            return 0
        days, acc, ok, _ = got
        k = bisect.bisect_left(days, r["date"]) - shift      # 원본 nrl.steady와 같은 식(끝만 shift줄 앞으로)
        if k < n:
            return 0
        return sum(1 for j in range(k - n + 1, k + 1)
                   if acc["외국인"][j] - acc["외국인"][j - 1] > 0 and acc["투신"][j] - acc["투신"][j - 1] > 0)
    return teacher, steady


# 원본 steady와 shift=0 판이 같은지 먼저 확인(다르면 원본 정의를 잘못 옮긴 것)
_t0, _s0 = flow_patch(0)
mism = sum(1 for r in nrl.inside if _s0(r) != ORIG_STEADY(r) or _t0(r) != ORIG_TEACHER(r))
print("원본 수급 함수 옮김 확인(전체 행):", mism, "건 다름", flush=True)
assert mism == 0, "옮김 오류"


def ledger(got):
    out = []
    for s in ("앞", "뒤"):
        for t in (got.get(s) or {}).get("매매목록", []):
            out.append((t["code"], t["산 날"], t["판 날"], float(t["손익"]), int(t.get("자리") or 1)))
    return out


def metrics(got):
    return {s: {k: got[s].get(k) for k in ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "그대로", "가장 낮음", "가장 높음")}
            for s in ("앞", "뒤") if got.get(s)}


RUNS = {}
SPECS = [("ASIS", "asis", 0), ("FLOAT-V1", "exact", 0), ("FLOW-LAG2", "asis", 1), ("FLOW-LAG3", "asis", 2)]
for name, mode, shift in SPECS:
    nrl.teacher, nrl.steady = flow_patch(shift) if shift else (ORIG_TEACHER, ORIG_STEADY)
    got = T.once(name, holds=nrl.BASE_HOLD, exit_at=make_exit(mode, name))
    RUNS[name] = {"metrics": metrics(got), "ledger": ledger(got)}
    print(name, "끝", round(time.time() - t0), "초", flush=True)
nrl.teacher, nrl.steady = ORIG_TEACHER, ORIG_STEADY

# ── F2 후보 집합(엔진 칸 다툼 앞 · 그날 조건 통과 종목) ──
cand = {n: {} for n in ("ASIS", "FLOW-LAG2", "FLOW-LAG3")}
sizes = {n: {} for n in cand}
tch = {n: {} for n in cand}
std = {n: {} for n in cand}
for n, shift in (("ASIS", 0), ("FLOW-LAG2", 1), ("FLOW-LAG3", 2)):
    te, st = flow_patch(shift)
    nrl.teacher, nrl.steady = te, st
    for r in nrl.inside:
        key = (r["code"], r["date"])
        tch[n][key] = None if None in (nrl.flow_sum(r, 5, c, lag=1 + shift) for c in ("외국인", "투신", "개인")) else te(r)
        std[n][key] = st(r)
        if nrl.BASE_HOLD(r):
            cand[n].setdefault(r["date"], set()).add(r["code"])
            sizes[n][key] = nrl.BASE_SIZE(r)
nrl.teacher, nrl.steady = ORIG_TEACHER, ORIG_STEADY
days = sorted(set().union(*[set(cand[n]) for n in cand]) | {r["date"] for r in nrl.inside})
f2 = {}
rows_csv = []
for n in ("FLOW-LAG2", "FLOW-LAG3"):
    jac, new, gone, chg_days = [], 0, 0, 0
    for d in days:
        a, b = cand["ASIS"].get(d, set()), cand[n].get(d, set())
        u = a | b
        if u:
            jac.append(len(a & b) / len(u))
        new += len(b - a)
        gone += len(a - b)
        chg_days += a != b
        if a != b:
            rows_csv.append({"variant": n, "date": d, "asis_n": len(a), "variant_n": len(b), "inter": len(a & b), "union": len(u),
                             "new": ";".join(sorted(b - a)), "gone": ";".join(sorted(a - b))})
    keys = list(tch["ASIS"])
    noncomp = [k for k in keys if tch["ASIS"][k] is None or tch[n][k] is None]
    comp = [k for k in keys if k not in set(noncomp)]
    t_chg = sum(1 for k in comp if tch["ASIS"][k] != tch[n][k])
    s_chg = sum(1 for k in keys if std["ASIS"][k] != std[n][k])
    both = set(sizes["ASIS"]) & set(sizes[n])
    z_chg = sum(1 for k in both if sizes["ASIS"][k] != sizes[n][k])
    cd = sum(1 for d in days if cand["ASIS"].get(d) or cand[n].get(d))
    f2[n] = {"candidate_days": cd, "candidate_changed_days": int(chg_days),
             "candidate_changed_ratio": chg_days / cd if cd else None,
             "jaccard": K.describe(jac), "jaccard_ci": K.boot_ci(jac), "new_candidates": new, "gone_candidates": gone,
             "asis_candidates_total": sum(len(v) for v in cand["ASIS"].values()), "variant_candidates_total": sum(len(v) for v in cand[n].values()),
             "rows_total": len(keys), "rows_noncomparable_flow5_missing": len(noncomp),
             "noncomparable_examples": [list(k) for k in noncomp[:20]],
             "teacher_changed": t_chg, "steady3_value_changed": s_chg, "size_changed_among_both_candidates": z_chg, "both_candidates": len(both)}
pd.DataFrame(rows_csv).to_csv(OUT / "d1_flow_candidate_changes.csv", index=False)


# ── 매매 목록 비교 · 비용 3단 · 날마다 평가 ──
def trade_cmp(a, b):
    """한 매매(종목 · 산 날)가 절반 익절로 여러 줄이면 그 줄들을 묶어 견줌."""
    def group(x):
        g = {}
        for t in x:
            g.setdefault((t[0], t[1]), []).append(tuple(t[2:]))
        return {k: sorted(v) for k, v in g.items()}
    A, B = group(a), group(b)
    common = sorted(set(A) & set(B))
    changed = [(k, A[k], B[k]) for k in common if A[k] != B[k]]
    sp = lambda rows: sum(r[1] * r[2] / 10 for r in rows)      # 계좌 몫 손익(칸/10 가중 · %)
    return {"asis_rows": len(a), "variant_rows": len(b), "asis_trades": len(A), "variant_trades": len(B), "common": len(common),
            "only_asis": len(set(A) - set(B)), "only_variant": len(set(B) - set(A)), "common_changed": len(changed),
            "only_asis_acctpct_sum": sum(sp(A[k]) for k in set(A) - set(B)), "only_variant_acctpct_sum": sum(sp(B[k]) for k in set(B) - set(A)),
            "changed_detail": [{"code": k[0], "entry": k[1], "asis": x, "variant": y, "asis_acctpct": sp(x), "variant_acctpct": sp(y)} for k, x, y in changed]}


z = np.load if False else None
D0 = sorted({d for c in nrl.prices.values() for d, _ in c["rows"] if d >= "20170101"})
res = {"cache_last_day": D0[-1], "period": {"앞": ["20170101", "20201231"], "뒤": ["20210101", D0[-1]]}, "runs": {}}
daily = {}
for name in RUNS:
    led = RUNS[name]["ledger"]
    out = {"metrics_engine(8씨앗·엔진 비용 0.25%)": RUNS[name]["metrics"], "ledger_trades(씨앗0)": len(led), "scales": {}}
    for sc_name, sc in P.SCALES.items():
        rl, tr = recost(led, sc)
        r = pd.Series(a_mtm.account(D0, rl, np.zeros(len(D0)), nrl.prices), index=D0)
        daily[(name, sc_name)] = r
        s = {h: P.daily_stats(r, lo, hi) for h, lo, hi in (("앞", "20170101", "20210101"), ("뒤", "20210101", "20991231"), ("전체", "20170101", "20991231"))}
        out["scales"][sc_name] = {h: ({k: v for k, v in x.items() if k not in ("해마다", "달마다")} if x else None) for h, x in s.items()}
    res["runs"][name] = out
pairs = {}
for name in ("FLOAT-V1", "FLOW-LAG2", "FLOW-LAG3"):
    tc = trade_cmp(RUNS["ASIS"]["ledger"], RUNS[name]["ledger"])
    pr = {"trades": tc, "daily_diff": {}}
    for sc_name in P.SCALES:
        d = (daily[(name, sc_name)] - daily[("ASIS", sc_name)]).to_numpy()
        a, b = res["runs"]["ASIS"]["scales"][sc_name]["전체"], res["runs"][name]["scales"][sc_name]["전체"]
        pr["daily_diff"][sc_name] = {"paired_daily_diff": K.describe(d), "paired_daily_diff_ci_block20": K.block_boot_ci(d),
                                     "delta_MDD": b["MDD"] - a["MDD"], "delta_worst_day": b["나쁜날"] - a["나쁜날"],
                                     "delta_worst_month": b["나쁜달"] - a["나쁜달"], "delta_CAGR": b["CAGR"] - a["CAGR"]}
    if tc["changed_detail"]:
        x = [c["variant_acctpct"] - c["asis_acctpct"] for c in tc["changed_detail"]]
        pr["changed_trade_pnl_diff"] = {**K.describe(x), "ci_cluster_code": K.boot_ci(x, groups=[c["code"] for c in tc["changed_detail"]])}
    pairs[name] = pr
res["pairs_vs_ASIS"] = pairs
res["F2_candidates"] = f2

# ── F1 판단 수 · 다른 판단 ──
log = pd.DataFrame(LOG)
if len(log):
    log.drop_duplicates(subset=["run", "rule", "code", "entry_day", "step"]).to_csv(OUT / "d1_float_mismatch_log.csv", index=False)
res["F1"] = {"evaluations_with_repeats(8씨앗·두 반)": {f"{r}:{k}": v for (r, k), v in EVAL.items()},
             "mismatch_unique": (log.drop_duplicates(subset=["rule", "code", "entry_day", "step"]).groupby("rule").size().to_dict() if len(log) else {}),
             "mismatch_runs": (log.groupby("run").size().to_dict() if len(log) else {})}
# 호가상 가능한 경계 노출(씨앗0 매매의 진입가)
expo = {}
for name in ("ASIS",):
    for c, b, e, p, k in RUNS[name]["ledger"]:
        rows = dict(nrl.prices[c]["rows"])
        px = rows.get(b)
        if px is None:
            continue
        for pct in (13, -5, 5, -10, 8, 1):
            on = K.boundary_on_tick(px, pct)
            exact_float_wrong = None
            if on:
                bnd = float(K.Fr(px) * (100 + pct) / 100)
                now = (bnd / px - 1) * 100
                exact_float_wrong = not (now >= pct) if pct in (13, 5, 8) else not (now <= pct)
            key = str(pct)
            e_ = expo.setdefault(key, {"entries": 0, "boundary_on_tick": 0, "float_misjudges_at_boundary": 0})
            e_["entries"] += 1
            e_["boundary_on_tick"] += bool(on)
            e_["float_misjudges_at_boundary"] += bool(exact_float_wrong)
prices_nonint = sum(1 for c in nrl.prices.values() for _, v in c["rows"] if float(v) != int(float(v)))
res["F1"]["tick_exposure_seed0_entries"] = expo
res["F1"]["nonint_price_rows_in_cache"] = prices_nonint
res["module_origin_violations"] = K.module_origins(BASE)
res["seconds"] = round(time.time() - t0)
(OUT / "d1_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
for n in RUNS:
    pd.DataFrame(RUNS[n]["ledger"], columns=["code", "entry", "exit", "pnl_pct_engine", "slots"]).to_csv(OUT / f"d1_ledger_{n}.csv", index=False)
print("끝", res["seconds"], "초 · 모듈 출처 위반", len(res["module_origin_violations"]), flush=True)
