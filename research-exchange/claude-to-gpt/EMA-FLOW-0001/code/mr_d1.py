"""MAX-RETURN-0001 · 1일봉 D0 ~ D3(PREREG). python3 -E -P mr_d1.py <b2> <nrl-cache.pkl> <출력>
PR #41 daily_exec.py 앞부분(신호 · 장부 · 순차 실행)을 그대로 불러 쓰고, 실험마다 picks(약한 신호 생략) · EXIT(나눠 팔기 없음)만 바꿔 끼움."""
import json
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "mr_base", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41 그대로)", "exec"), G)
sys.path.insert(0, str(HERE))
import common as CM  # noqa: E402

KN, OUT = G["KN"], Path(sys.argv[3])
DAYS_ALL, PICKS, EXIT0, SIZE = list(G["DAYS"]), G["PICKS"], G["EXIT"], G["SIZE"]
TRAIN = ("20170201", "20201231")
COMMON = ("20250918", "20260831")
PERIODS = (("Train 2017-02~2020-12", *TRAIN), ("2021~2022(재사용 진단)", "20210101", "20221231"),
           ("2023-01~2026-09(재사용 진단)", "20230101", "20260930"), ("전체 2017-02~2026-09", "00000000", "99999999"))


class Acc1e7(KN.Account):
    def __init__(self, costs, cash=CM.CASH):
        super().__init__(costs, CM.CASH)


KN.Account = Acc1e7


def no_partial(*a, **k):
    d = EXIT0(*a, **k)
    return False if (d is not True and isinstance(d, int) and not isinstance(d, bool)) else d


STRONG = {d: [r for r in rows if SIZE(r) >= 3] for d, rows in PICKS.items()}
CFG = {"D0": (PICKS, EXIT0), "D1": (STRONG, EXIT0), "D2": (PICKS, no_partial), "D3": (STRONG, no_partial)}


def run(cfg, mult, lo=None, hi=None, exclude=None):
    pk, ex = CFG[cfg]
    if exclude:
        pk = {d: [r for r in rows if r["code"] != exclude] for d, rows in pk.items()}
    G["DAYS"] = [d for d in DAYS_ALL if (lo is None or d >= lo) and (hi is None or d <= hi)]
    G["EXIT"] = ex
    try:
        r = G["run_d1"]("next", mult, PK=pk)
    finally:
        G["DAYS"], G["EXIT"] = DAYS_ALL, EXIT0
    r["cal"] = [d for d, _, _ in r["nav"]]
    return r


def tr_top(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return max(by.items(), key=lambda x: x[1])[0] if by else None


OUT.mkdir(parents=True, exist_ok=True)
(OUT / "d1_picks.json").write_text(json.dumps({"cal": DAYS_ALL, "picks": {d: sorted({r["code"] for r in rows}) for d, rows in PICKS.items()}}),
                                   encoding="utf-8")
PT = (PERIODS[0],)
TR = {}
for cfg in CFG:
    for m in (1.0, 2.0):
        r = run(cfg, m, hi=TRAIN[1])
        TR[(cfg, m)] = (r, CM.stats(r, PT)[PT[0][0]])
    top = tr_top(TR[(cfg, 1.0)][0])
    rx = run(cfg, 1.0, hi=TRAIN[1], exclude=top)
    TR[(cfg, "ex")] = (top, CM.stats(rx, PT)[PT[0][0]])
    a1, a2, ax = TR[(cfg, 1.0)][1], TR[(cfg, 2.0)][1], TR[(cfg, "ex")][1]
    print("Train", cfg, a1["CAGR"], a2["CAGR"], a1["worst_day"], a2["worst_day"], "제외", top, ax["CAGR"], a1["turnover_per_year"], a1["positions"], flush=True)
rows, ok = [], []
for cfg in CFG:
    a1, a2 = TR[(cfg, 1.0)][1], TR[(cfg, 2.0)][1]
    top, ax = TR[(cfg, "ex")]
    c = {"day_ok": a1["day_breach_-15"] == 0 and a2["day_breach_-15"] == 0, "cagr2_pos": (a2["CAGR"] or -1) > 0, "ex_top_pos": (ax["CAGR"] or -1) > 0}
    rows.append({"cfg": cfg, **c, "CAGR_x1": a1["CAGR"], "CAGR_x2": a2["CAGR"], "MDD_x1": a1["MDD_daily"], "worst_day_x1": a1["worst_day"],
                 "worst_month_x1": a1["worst_month"], "month_breach_x1": a1["month_breach_-15"], "turnover": a1["turnover_per_year"],
                 "positions": a1["positions"], "top": top, "CAGR_ex_top": ax["CAGR"]})
    if all(c.values()):
        ok.append(rows[-1])
ok.sort(key=lambda r: -r["CAGR_x1"])
chosen = None
if ok:
    best = ok[0]["CAGR_x1"]
    chosen = sorted([r for r in ok if best - r["CAGR_x1"] <= 1.0], key=lambda r: (-r["CAGR_x2"], list(CFG).index(r["cfg"])))[0]["cfg"]
print("1일봉 선택", chosen, [r["cfg"] for r in ok], flush=True)

FULL = {}
for cfg in CFG:                                        # 고른 뒤 규칙 고정 · 모든 실험의 뒤 구간을 한 번에 보고
    for m in (1.0, 2.0):
        r = run(cfg, m)
        FULL[(cfg, m)] = CM.stats(r, PERIODS)
        if m == 1.0:
            FULL[(cfg, "top")] = tr_top(r)
            rx = run(cfg, 1.0, exclude=FULL[(cfg, "top")])
            FULL[(cfg, "ex")] = CM.stats(rx, PERIODS)
            rc = run(cfg, 1.0, lo=COMMON[0], hi=COMMON[1])
            FULL[(cfg, "common")] = CM.stats(rc, (("같은 시작 2025-09-18~2026-08-31", *COMMON),))
            if cfg in ("D0", chosen):
                with open(OUT / f"nav_{cfg}_x1_1e7.csv", "w", encoding="utf-8") as f:
                    f.write("date,nav_norm,invested_ratio\n")
                    f.writelines(f"{d},{n / CM.CASH:.6f},{i / n:.5f}\n" for d, n, i in r["nav"])
    print("전체", cfg, FULL[(cfg, 1.0)]["전체 2017-02~2026-09"]["CAGR"], "같은 시작", FULL[(cfg, "common")]["같은 시작 2025-09-18~2026-08-31"]["CAGR"], flush=True)
out = {"train": rows, "chosen": chosen, "passed": [r["cfg"] for r in ok],
       "full": {f"{k[0]}_{k[1]}": (CM.strip(v) if isinstance(v, dict) else v) for k, v in FULL.items()},
       "monthly_D0": FULL[("D0", 1.0)]["전체 2017-02~2026-09"]["monthly"],
       "monthly_chosen": FULL[(chosen, 1.0)]["전체 2017-02~2026-09"]["monthly"] if chosen else None}
(OUT / "d1_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("끝", flush=True)
