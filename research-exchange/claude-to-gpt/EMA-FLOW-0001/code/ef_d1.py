"""EMA-FLOW-0001 · 1일봉 B(D0) · I · P · IP(GPT PR #50 PREREG · 클로드 PREREG d1725d34).
python3 -E -P ef_d1.py <b2> <nrl-cache.pkl> <출력> <train|diag>
PR #45 daily_exec.py 앞부분(신호 · 장부 · 순차 실행)을 그대로 불러 쓰고, run_d1 원문에 'P 부분익절' 갈고리와 고정 수량 매도만 끼움.
I(기관 조건)는 신호 단계(picks)에서 거름. train: 기준 맞춤 → 8판 + 제외 4판 → 선택 → 자르기 → LOCK.json · diag: LOCK의 선택판과 B 뒤 진단."""
import bisect
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "ef_base", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41/#45 그대로)", "exec"), G)
sys.path.insert(0, str(HERE))
import common as CM  # noqa: E402

KN, nrl, final_group = G["KN"], G["nrl"], G["final_group"]
OUT, STAGE = Path(sys.argv[3]), sys.argv[4]
DAYS_ALL, PICKS, SIZE = list(G["DAYS"]), G["PICKS"], G["SIZE"]
TRAIN = ("20170201", "20201231")
PERIODS = (("Train 2017-02~2020-12", *TRAIN), ("2021~2022(재사용 진단)", "20210101", "20221231"),
           ("2023-01~2026-09(재사용 진단)", "20230101", "20260930"), ("전체 2017-02~2026-09", "00000000", "99999999"))
ORDER = ("B", "I", "P", "IP")
CFG = {"B": (False, False), "I": (True, False), "P": (False, True), "IP": (True, True)}
D0_REF = {"end_nav_won": 11653611, "CAGR_x1": 3.99, "CAGR_x2": 0.34, "MDD": -24.4, "worst_day": -4.5, "positions": 123, "top": "006280",
          "CAGR_ex_top": 0.84}

# ── 거래량(수급 날짜와 같은 날짜로 결합) ──
VOL = {}
for c in nrl.FLOW:
    p = Path(G["BASE"], "volume-data", f"{c}.json")
    if p.exists():
        b = json.loads(p.read_text(encoding="utf-8"))
        ix = b["칸"].index("거래량")
        VOL[c] = {str(r[0]): r[ix] for r in b["날"]}
print("거래량 결합", len(VOL), "/", len(nrl.FLOW), flush=True)


def inst_sum(row, FL):
    """기관 순매수 수량 5거래일 합 · 판단일보다 2거래일 앞까지(D0 teacher와 같은 창). 모자라면 None."""
    got = FL.get(row["code"])
    if not got:
        return None
    days, acc, ok, _ = got
    k = bisect.bisect_left(days, row["date"]) - 1
    if k - 5 < 0 or ok[k] - ok[k - 5] < 5:
        return None
    return acc["기관"][k] - acc["기관"][k - 5]


def indiv_up(c, d, FL, VL, CLm):
    """개인 강도(5일 순매수 수량 합 ÷ 같은 5일 거래량 합) 최신 창 > 0 이고 > 직전 창. 돌려줌: (참/거짓, 누락 사유)."""
    got = FL.get(c)
    if not got:
        return False, "수급 파일 없음"
    days, acc, ok, fcl = got
    k = bisect.bisect_left(days, d) - 1
    if k - 10 < 0:
        return False, "창 모자람"
    if ok[k] - ok[k - 10] < 10:
        return False, "수급 칸 누락"
    vs = []
    for j in range(k - 10, k):
        v = VL.get(c, {}).get(days[j])
        if v is None:
            return False, "거래량 누락"
        if v <= 0:
            return False, "거래량 0"
        px = CLm.get(c, {}).get(days[j])
        if not px or not fcl[j] or abs(fcl[j] / px - 1) > 0.01:
            return False, "단위 불일치(종가)"
        vs.append(v)
    new = (acc["개인"][k] - acc["개인"][k - 5]) / sum(vs[5:])
    old = (acc["개인"][k - 5] - acc["개인"][k - 10]) / sum(vs[:5])
    return (new > 0 and new > old), None


# ── run_d1 원문에 갈고리 끼우기 ──
rs = _src[_src.index("def run_d1("):_src.index("\ndef snapshot(")]


def rep(s, a, b):
    assert s.count(a) == 1, a
    return s.replace(a, b)


rs = rep(rs, "def run_d1(mode, mult, LN=None, CLm=None, PK=None, snap_day=None):",
         "def run_ef(mode, mult, LN=None, CLm=None, PK=None, snap_day=None, PCFG=False, FL=None, VL=None):")
rs = rep(rs, '    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"))', '    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"), CM.CASH)')
rs = rep(rs, """                if o["kind"] == "all":
                    acc.sell(pid, price, d, o["dec"], reason=o["why"])
                else:""", """                if o["kind"] == "all":
                    acc.sell(pid, price, d, o["dec"], reason=o["why"])
                elif o["kind"] == "fixed":                          # P: 판단일에 고정한 수량 그대로(다시 셈하지 않음)
                    if o["qty"] >= acc.pos[pid]["qty"]:
                        raise AssertionError("P 고정 수량 ≥ 남은 수량")
                    acc.sell(pid, price, d, o["dec"], qty=o["qty"], reason=o["why"])
                    notes["p_filled"] += 1
                else:""")
rs = rep(rs, """                del open_[c]
            else:
                spot["step"] = step
""", """                del open_[c]
            else:
                spot["step"] = step
                if PCFG and not forced and not spot.get("p_done") and nrl.tier(spot["row"]) == "정배열":
                    hit, why = indiv_up(c, d, FL, VL, CLm)
                    if why:
                        notes["p_missing:" + why] += 1
                    elif hit:
                        pp = acc.pos[spot["pid"]]
                        qn = pp["qty"]
                        px = closes[index]
                        net = qn * px * (1 - acc.costs.rate("sell", c, d, qn * px)[0]) - pp["basis"]
                        if net <= 0:
                            notes["p_not_profit"] += 1
                        elif qn // 2 < 1:
                            notes["p_qty_lt1"] += 1
                        else:
                            pend_sell.append({"pid": spot["pid"], "code": c, "kind": "fixed", "qty": qn // 2, "frac": None, "dec": d,
                                              "why": "개인 강도 부분익절"})
                            spot["p_done"] = True
                            notes["p_decided"] += 1
""")
exec(compile(rs, "run_ef(run_d1 원문 + P 갈고리)", "exec"), G)
G["CM"] = CM
G["indiv_up"] = indiv_up


def picks_for(use_i, FL, exclude=None, base=None):
    base = PICKS if base is None else base
    out, cnt = {}, Counter()
    for d, rows in base.items():
        keep = []
        for r in rows:
            if exclude and r["code"] == exclude:
                continue
            if use_i and nrl.tier(r) == "정배열":
                s = inst_sum(r, FL)
                if s is None:
                    cnt["i_missing"] += 1
                    continue
                if s <= 0:
                    cnt["i_rejected"] += 1
                    continue
                cnt["i_passed"] += 1
            keep.append(r)
        if keep:
            out[d] = keep
    return out, dict(cnt)


def run(cfg, mult, lo=None, hi=None, exclude=None, LN=None, CLm=None, FL=None, VL=None, PK=None, snap_day=None):
    use_i, use_p = CFG[cfg]
    FL, VL = FL or nrl.FLOW, VL or VOL
    pk, icnt = picks_for(use_i, FL, exclude, PK)
    G["DAYS"] = [d for d in DAYS_ALL if (lo is None or d >= lo) and (hi is None or d <= hi)]
    try:
        r = G["run_ef"]("next", mult, LN=LN, CLm=CLm, PK=pk, snap_day=snap_day, PCFG=use_p, FL=FL, VL=VL)
    finally:
        G["DAYS"] = DAYS_ALL
    r["cal"] = [d for d, _, _ in r["nav"]]
    r["notes"]["i_counts"] = icnt
    return r


def top_of(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return max(by.items(), key=lambda x: x[1])[0] if by else None


def raw(r, lo="0", hi="9"):
    """반올림 전 CAGR · MDD · 최악 하루 · 넘음 · 회전율(kernel2.report와 같은 식, 기간 시작 = 앞날 NAV)."""
    nav = r["nav"]
    idx = [i for i, x in enumerate(nav) if lo <= x[0] <= hi]
    i0, i1 = idx[0], idx[-1]
    base = nav[i0 - 1][1] if i0 > 0 else CM.CASH
    seg = [base] + [x[1] for x in nav[i0:i1 + 1]]
    rets = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    yrs = KN._years(nav[i0][0], nav[i1][0])
    peak, mdd = seg[0], 0.0
    for v in seg:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(range(len(rets)), key=lambda i: rets[i])
    fl = [f for f in r["fills"] if f["status"] in ("FILLED", "REDUCED") and lo <= str(f["fill_at"])[:8] <= hi]
    avg = sum(x[1] for x in nav[i0:i1 + 1]) / (i1 - i0 + 1)
    return {"CAGR": ((seg[-1] / seg[0]) ** (1 / yrs) - 1) * 100, "MDD": mdd * 100, "worst_day": rets[wd] * 100, "worst_day_at": nav[i0 + wd][0],
            "day_breach": sum(1 for x in rets if x < -0.15 - 1e-12), "turnover": sum(f["notional"] for f in fl) / 2 / avg / (yrs or 1),
            "end_nav": seg[-1], "fills": len(fl)}


def fills_table(r):
    return [{"pid_day": str(f["pid"]).split(":")[-1], "side": f["side"], "status": f["status"], "decision_at": f["decision_at"],
             "data_end": f["decision_at"], "fill_at": f["fill_at"], "qty_ratio": f.get("qty_ratio"), "notional": round(f.get("notional", 0.0)),
             "cost": round(f.get("cost", 0.0), 2), "reason": f.get("reason", ""), "slots": f.get("slots")} for f in r["fills"]]


def save_nav(name, r):
    with open(OUT / f"nav_{name}.csv", "w", encoding="utf-8") as f:
        f.write("date,nav_won,invested_won\n")
        f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in r["nav"])


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                            encoding="utf-8")


OUT.mkdir(parents=True, exist_ok=True)
PT = (PERIODS[0],)
if STAGE == "train":
    RES = {}
    # ── 1. D0 기준 맞춤 ──
    b1 = run("B", 1.0, hi=TRAIN[1])
    b2 = run("B", 2.0, hi=TRAIN[1])
    a1, a2 = CM.stats(b1, PT)[PT[0][0]], CM.stats(b2, PT)[PT[0][0]]
    btop = top_of(b1)
    bx_run = run("B", 1.0, hi=TRAIN[1], exclude=btop)
    bx = CM.stats(bx_run, PT)[PT[0][0]]
    mine = {"end_nav_won": a1["end_nav_won"], "CAGR_x1": a1["CAGR"], "CAGR_x2": a2["CAGR"], "MDD": a1["MDD_daily"], "worst_day": a1["worst_day"],
            "positions": a1["positions"], "top": btop, "CAGR_ex_top": bx["CAGR"]}
    RES["baseline_check"] = {"pr45": D0_REF, "mine": mine, "same": mine == D0_REF}
    print("기준 맞춤", mine, "같음" if mine == D0_REF else "다름", flush=True)
    if mine != D0_REF:
        dump("ef_train.json", RES)
        print("D0 기준 불일치 · 새 판 계산 중단", flush=True)
        raise SystemExit(3)
    # ── 2. Train 8판 + 제외 4판 ──
    TR, rows = {("B", 1.0): b1, ("B", 2.0): b2}, []
    for cfg in ORDER:
        for m in (1.0, 2.0):
            if (cfg, m) not in TR:
                TR[(cfg, m)] = run(cfg, m, hi=TRAIN[1])
            r = TR[(cfg, m)]
            a = CM.stats(r, PT)[PT[0][0]]
            RES[f"train_{cfg}_x{m:g}"] = {"report": CM.strip({PT[0][0]: a})[PT[0][0]], "raw": raw(r), "notes": r["notes"],
                                          "max_slots_used": r["max_slots_used"], "gap": [r["tot"].get("max_gap_cash"), r["tot"].get("max_gap_nav")]}
            save_nav(f"train_{cfg}_x{m:g}", r)
            if m == 1.0:
                dump(f"fills_train_{cfg}_x1.json", fills_table(r))
            print("Train", cfg, m, a["CAGR"], a["MDD_daily"], a["worst_day"], a["worst_day_at"], a["day_breach_-15"], "포지션", a["positions"],
                  "P", r["notes"].get("p_decided", 0), r["notes"].get("p_filled", 0), "I", r["notes"]["i_counts"], flush=True)
        top = btop if cfg == "B" else top_of(TR[(cfg, 1.0)])
        rx = bx_run if cfg == "B" else run(cfg, 1.0, hi=TRAIN[1], exclude=top)
        ax = raw(rx)
        RES[f"train_{cfg}_ex_top"] = {"excluded": top, "raw": ax, "CAGR_engine": CM.stats(rx, PT)[PT[0][0]]["CAGR"]}
        r1, r2 = RES[f"train_{cfg}_x1"]["raw"], RES[f"train_{cfg}_x2"]["raw"]
        c = {"day_ok": r1["day_breach"] == 0 and r2["day_breach"] == 0, "cagr2_pos": r2["CAGR"] > 0, "ex_top_pos": ax["CAGR"] > 0}
        rows.append({"cfg": cfg, **c, "CAGR_x1": r1["CAGR"], "CAGR_x2": r2["CAGR"], "turnover_x2": r2["turnover"], "MDD_x2": r2["MDD"],
                     "top": top, "CAGR_ex_top": ax["CAGR"]})
        print("제외", cfg, top, round(ax["CAGR"], 4), c, flush=True)
    ok = [r for r in rows if r["day_ok"] and r["cagr2_pos"] and r["ex_top_pos"]]
    chosen = None
    if ok:
        best = max(r["CAGR_x2"] for r in ok)
        near = [r for r in ok if best - r["CAGR_x2"] <= 1.0]
        chosen = sorted(near, key=lambda r: (r["turnover_x2"], -r["MDD_x2"], ORDER.index(r["cfg"])))[0]["cfg"]
    RES["selection"] = {"rows": rows, "passed": [r["cfg"] for r in ok], "chosen": chosen}
    print("선택", chosen, [r["cfg"] for r in ok], flush=True)
    # ── 4. 자르기 시험(B와 선택판 · 비용 1배) ──
    RES["cut_test"] = {}
    for x in ("20191231", "20200930"):
        LN2 = {c: dict(v, closes=[(y * 1.37 if dd > x else y) for dd, y in zip(v["날"], v["closes"])]) for c, v in G["LANE"].items()}
        CL2 = {c: G["bump_after"](v, x) for c, v in G["CL"].items()}
        PK2 = {d: v for d, v in PICKS.items() if d <= x}
        FL2 = {}
        for c in nrl.FLOW:
            fr = final_group.flow_rows(c, Path(G["BASE"], "investor-data"))
            FL2[c] = nrl.flow_entry([dict(z, **{k: (z[k] * -1.37 if z["date"] > x and z.get(k) is not None else z.get(k))
                                               for k in ("개인", "외국인", "기관", "투신", "종가")}) for z in fr])
        VL2 = {c: {d: (v * 1.37 if d > x else v) for d, v in s.items()} for c, s in VOL.items()}
        for cfg in dict.fromkeys(["B", chosen or "B"]):
            rc = run(cfg, 1.0, hi=TRAIN[1], LN=LN2, CLm=CL2, FL=FL2, VL=VL2, PK=PK2)
            same = G["same_prefix"](TR[(cfg, 1.0)], dict(rc, snap=None), x)
            RES["cut_test"][f"{cfg}_{x}"] = {k: v for k, v in same.items() if k != "snap_equal"}
            print("자르기", cfg, x, RES["cut_test"][f"{cfg}_{x}"], flush=True)
    dump("ef_train.json", RES)
    dump("LOCK.json", {"task_id": "EMA-FLOW-0001", "chosen": chosen, "passed": RES["selection"]["passed"],
                       "selection_rows": rows, "cut_test": RES["cut_test"], "baseline_same": True,
                       "note": "Train만 보고 고른 판. 이 파일을 원격에 커밋한 뒤에 뒤 구간 진단을 돌림."})
    print("끝 train", flush=True)

elif STAGE == "diag":
    LOCK = json.loads(Path(sys.argv[5]).read_text(encoding="utf-8"))
    chosen = LOCK["chosen"]
    RES = {"lock": LOCK}
    for cfg in dict.fromkeys([x for x in (chosen, "B") if x]):
        for m in (1.0, 2.0):
            r = run(cfg, m)
            rep_ = CM.stats(r, PERIODS)
            RES[f"full_{cfg}_x{m:g}"] = {"report": CM.strip(rep_), "raw": {p[0]: raw(r, p[1], p[2]) for p in PERIODS}, "notes": r["notes"],
                                         "monthly": rep_[PERIODS[3][0]]["monthly"]}
            if m == 1.0:
                save_nav(f"full_{cfg}_x1", r)
            print("진단", cfg, m, {p[0]: rep_[p[0]]["CAGR"] for p in PERIODS}, "MDD", rep_[PERIODS[3][0]]["MDD_daily"], flush=True)
    dump("ef_diag.json", RES)
    print("끝 diag", flush=True)
