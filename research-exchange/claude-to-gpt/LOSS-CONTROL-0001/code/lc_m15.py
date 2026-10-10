"""LOSS-CONTROL-0001 · 15분봉 M0 · M4 · R30 · R40 · R50(GPT PR #48 PREREG · 클로드 PREREG 2cc68ef7). MR_D1PICKS=<d1_picks.json> python3 -E -P lc_m15.py <b3> <출력>
PR #47 mr2_m15.py에서 진입 상한을 빼고 '보유 축소' 갈고리 · 종목별 손익 사진 · 원인 대조 · 선택 · 자르기 시험만 더함.
PR #41 m15_exec.py 앞부분(신호 · 순위 · 청산 · 묵음 · 자료)을 그대로 불러 쓰고, 계좌 루프는 m15_exec.run과 같은 순서에
실험 갈고리(약한 신호 생략 · 나눠 팔기 없음 · 1일봉 보완 · 종목 제외 · 기간 · 자금)만 더함."""
import bisect
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "m15_exec.py").read_text(encoding="utf-8").split("\ndef run(mult):")[0]
P = {"__name__": "mr_m15", "__file__": str(HERE / "m15_exec.py")}
exec(compile(_src, "m15_exec(앞부분 · PR #41 그대로)", "exec"), P)
sys.path.insert(0, str(HERE))
import common as CM  # noqa: E402

KN, CC, np = P["KN"], P["CC"], P["np"]
SG, RANK, EXIT, STALE, SIZE, data, market_of = P["SG"], P["RANK"], P["EXIT"], P["STALE"], P["SIZE"], P["data"], P["market_of"]
OUT = Path(sys.argv[2])
SLOTS = 10
D1 = json.loads(Path(os.environ["MR_D1PICKS"]).read_text(encoding="utf-8"))
D1CAL = D1["cal"]
D1IX = {d: i for i, d in enumerate(D1CAL)}
D1SET = {(c, d) for d, cs in D1["picks"].items() for c in cs}
CFG = {"M0": {}, "M4": {"d1filter": True}, "R30": {"d1filter": True, "hold_cap": 0.30}, "R40": {"d1filter": True, "hold_cap": 0.40},
       "R50": {"d1filter": True, "hold_cap": 0.50}}
TRAIN = ("202509170000", "202604010000")
FULLW = ("202509170000", "202609010000")
COMMONW = ("202509180000", "202609010000")
PERIODS = (("Train 2025-09-17~2026-03-31", "20250917", "20260331"), ("2026-04~08(재사용 진단)", "20260401", "20260831"),
           ("전체 2025-09-17~2026-08-31", "00000000", "99999999"))


def d1_recent(code, day):
    """그날을 뺀 최근 5거래일(1일봉 달력) 안에 1일봉 신호가 있었나."""
    i = bisect.bisect_left(D1CAL, day)
    return any((code, D1CAL[j]) in D1SET for j in range(max(0, i - 5), i))


def run(cfg, mult, lo, hi, exclude=None, snaps=()):
    opt = CFG[cfg]
    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"), CM.CASH)
    rng = np.random.default_rng(0)
    idx, times = {}, set()
    for c in SG:
        t = data[c]["t"]
        k0, k1 = bisect.bisect_left(t, lo), bisect.bisect_left(t, hi)
        idx[c] = (k0, k1)
        times.update(t[k0:k1])
    times = sorted(times)
    at = {}
    for c, (k0, k1) in idx.items():
        for k in range(k0, k1):
            at.setdefault(data[c]["t"][k], []).append((c, k))
    pos, want_buy, want_sell, last_close = {}, {}, {}, {}
    navs, gross, last_day = [], [], None
    notes = {"cant_split": 0, "stale_bumped": 0, "buy_signal_no_slot": 0, "skip_weak": 0, "skip_no_d1": 0, "partial_suppressed": 0,
             "trim_decided": 0, "trim_filled": 0, "trim_cancelled": 0, "trim_cut_to_remaining": 0, "trim_closed_all": 0, "trim_notional": 0.0}
    pf = lambda code: (last_close.get(code, 0.0), False)
    trim, snap, last_T = {}, {}, None                    # trim: 종목 → (고정 수량, 판단한 날, pid, 판단 봉)

    def snapshot(day):
        """그날 장 마감 시점 종목별 '누적 실현 손익 + 보유 평가 손익'."""
        by = {}
        for row in acc.closed:
            by[row["code"]] = by.get(row["code"], 0.0) + row["pnl_net"]
        for q in acc.pos.values():
            by[q["code"]] = by.get(q["code"], 0.0) + q["realized"] + q["qty"] * pf(q["code"])[0] - q["basis"]
        snap[day] = by

    for T in times:
        if last_day and T[:8] != last_day:
            nav, inv = acc.mtm(pf)
            acc.check(pf)
            navs.append((last_day, nav, inv))
            gross.append((last_day, nav + acc.cum_cost()))
            if last_day in snaps:
                snapshot(last_day)
            cap = opt.get("hold_cap")
            if cap:                                         # ⓪ 장 마감 뒤 보유 축소 판단(그날 마지막 봉까지의 값만)
                for c, p in pos.items():
                    if c in trim:
                        continue
                    qty, px = acc.pos[p["pid"]]["qty"], pf(c)[0]
                    if qty * px > cap * nav:
                        q = math.floor(qty - cap * nav / px)
                        if q >= 1:
                            trim[c] = (q, last_day, p["pid"], last_T)
                            notes["trim_decided"] += 1
        bars = at[T]
        for c, k in bars:                                   # ① 다음 봉 시가에 팔기
            if c in want_sell and c in pos:
                n, dec = want_sell.pop(c)
                p = pos[c]
                part = p["칸"] if n == "all" or n >= p["칸"] else int(n)
                if part >= p["칸"]:
                    acc.sell(p["pid"], data[c]["o"][k], T, dec, reason="청산")
                else:
                    q = math.floor(acc.pos[p["pid"]]["qty"] * part / p["칸"])
                    if q < 1:
                        notes["cant_split"] += 1
                    else:
                        acc.sell(p["pid"], data[c]["o"][k], T, dec, qty=q, reason="나눠 팔기")
                p["칸"] -= part
                if p["칸"] <= 0:
                    del pos[c]
            if c in trim and T[:8] > trim[c][1]:            # ①' 보유 축소: 다음 거래일 이후 첫 봉 시가 · 고정 수량
                q, dday, tpid, dT = trim.pop(c)
                if not (dT < T and dday < T[:8]):
                    raise AssertionError("미래 참조: 축소 판단 봉 ≥ 체결 봉")
                p = pos.get(c)
                if p is None or p["pid"] != tpid or tpid not in acc.pos:
                    notes["trim_cancelled"] += 1
                else:
                    left = acc.pos[tpid]["qty"]
                    if q > left:
                        notes["trim_cut_to_remaining"] += 1
                    qq = min(q, left)
                    px = data[c]["o"][k]
                    if acc.sell(tpid, px, T, dT, qty=qq, reason="보유 축소"):
                        notes["trim_filled"] += 1
                        notes["trim_notional"] += qq * px
                        if tpid not in acc.pos:             # 남은 수량이 0이면 장부에서 닫혀 칸도 비움
                            notes["trim_closed_all"] += 1
                            del pos[c]
        buys = [(c, k) for c, k in bars if c in want_buy and c not in pos]
        buys.sort(key=lambda ck: (RANK(ck[0], data[ck[0]], ck[1] - 1), rng.random()))
        for c, k in buys:                                   # ② 다음 봉 시가에 사기
            need, dec = want_buy.pop(c)
            free = SLOTS - sum(p["칸"] for p in pos.values())
            if free < need:
                weak = sorted((q for q in pos.values() if STALE(q)), key=lambda q: data[q["code"]]["c"][q["now"]] / q["price"])
                for q in weak:
                    if free >= need:
                        break
                    qc, qb = q["code"], data[q["code"]]
                    kk = bisect.bisect_left(qb["t"], T)
                    if kk < len(qb["t"]) and qb["t"][kk] == T:
                        if q["now"] >= kk:
                            raise AssertionError("미래 참조: 비킴 판단 봉 ≥ 체결 봉")
                        free += q["칸"]
                        acc.sell(q["pid"], qb["o"][kk], T, qb["t"][kk - 1], reason="묵음 비키기")
                        notes["stale_bumped"] += 1
                        del pos[qc]
                        want_sell.pop(qc, None)
            if free <= 0:
                notes["buy_signal_no_slot"] += 1
                continue
            take = min(need, free)
            o = data[c]["o"][k]
            pid = f"{c}:{T}"
            if acc.buy(pid, c, o, T, dec, value=take / SLOTS * acc.mtm(pf)[0], slots=take, tag=f"칸{take}"):
                pos[c] = {"pid": pid, "i": k, "price": o, "칸": take, "처음칸": take, "peak": o, "now": k, "day": T[:8], "code": c}
        for c, _ in bars:
            want_buy.pop(c, None)
        for c, k in bars:                                   # ③ 봉 갱신
            p = pos.get(c)
            if p:
                p["now"] = k
                p["peak"] = max(p["peak"], data[c]["c"][k])
        for c, k in bars:                                   # ④ 봉이 닫힌 뒤 판단
            bb = data[c]
            p = pos.get(c)
            if p:
                n = EXIT(c, bb, p, k)
                if opt.get("no_partial") and n and n != "all":
                    notes["partial_suppressed"] += 1
                    n = 0
                if n:
                    want_sell[c] = (n, T)
            elif SG[c][k] and k + 1 < len(bb["t"]) and c != exclude:
                need = SIZE(c, bb, k)
                if opt.get("skip_weak") and need < 4:
                    notes["skip_weak"] += 1
                elif opt.get("d1filter") and not d1_recent(c, T[:8]):
                    notes["skip_no_d1"] += 1
                else:
                    want_buy[c] = (need, T)
            last_close[c] = bb["c"][k]
        last_day, last_T = T[:8], T
    nav, inv = acc.mtm(pf)
    acc.check(pf)
    navs.append((last_day, nav, inv))
    gross.append((last_day, nav + acc.cum_cost()))
    if last_day in snaps:
        snapshot(last_day)
    notes["trim_pending_at_end"] = len(trim)
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills, "counts": dict(acc.counts),
            "tot": dict(acc.tot), "notes": notes, "cal": [x[0] for x in navs], "snap": snap}


def top_of(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return max(by.items(), key=lambda x: x[1])[0] if by else None


def top_of(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return max(by.items(), key=lambda x: x[1])[0] if by else None


def indep(nav, cash=CM.CASH):
    """제가 따로 짠 지표 산술(kernel2.report를 쓰지 않음)."""
    prev, peak, mdd, wd, wd_at, br = cash, cash, 0.0, 0.0, None, 0
    for d, v, _ in nav:
        r = v / prev - 1
        if r < wd:
            wd, wd_at = r, d
        br += int(r < -0.15 - 1e-12)
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
        prev = v
    from datetime import date
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    yrs = (D(nav[-1][0]) - D(nav[0][0])).days / 365.25
    return {"first_nav_day": nav[0][0], "end_nav_won": round(nav[-1][1]), "CAGR": round(((nav[-1][1] / cash) ** (1 / yrs) - 1) * 100, 2),
            "MDD_daily": round(mdd * 100, 2), "worst_day_unrounded_pct": wd * 100, "worst_day_at": wd_at, "day_breach_-15": br}


def filled(r, lo="0", hi="9"):
    return [f for f in r["fills"] if f["status"] in ("FILLED", "REDUCED") and lo <= str(f["fill_at"])[:8] <= hi]


OUT.mkdir(parents=True, exist_ok=True)
PT = (PERIODS[0],)
RES = {}

# ── 1단계: 03-31 원인 대조(다르면 멈춤) ──
import subprocess  # noqa: E402
GA = json.loads(subprocess.check_output(["git", "-C", os.environ.get("LC_REPO", "/home/user/stock-dash"), "show",
                                         "812810b54be4e03c6eccce5e56affb0897ccf4a2:research-exchange/gpt-to-claude/LOSS-CONTROL-0001/GPT_ATTRIBUTION.json"]))
r = run("M4", 2.0, *TRAIN, snaps=("20260330", "20260331"))
nv = {d: n for d, n, _ in r["nav"]}
a, b = r["snap"]["20260330"], r["snap"]["20260331"]
contrib = {c: b.get(c, 0.0) - a.get(c, 0.0) for c in set(a) | set(b)}
contrib = {c: v for c, v in contrib.items() if abs(v) > 1e-6}
ranked = sorted(contrib.items(), key=lambda x: x[1])
recs331 = [f for f in r["fills"] if str(f["fill_at"])[:8] == "20260331"]
mine = {"nav_previous": nv["20260330"], "nav_end": nv["20260331"], "nav_change_won": nv["20260331"] - nv["20260330"],
        "return_pct": (nv["20260331"] / nv["20260330"] - 1) * 100, "fills_on_day": len(filled(r, "20260331", "20260331")),
        "request_records_on_day": len(recs331),
        "contributions": [{"code": c, "won": v, "share_pct": round(v / (nv["20260331"] - nv["20260330"]) * 100, 2)} for c, v in ranked],
        "sum_attribution_won": sum(contrib.values())}
chk = []
for k in ("nav_previous", "nav_end", "nav_change_won", "sum_attribution_won"):
    chk.append((k, GA[k], mine[k], abs(GA[k] - mine[k]) <= 0.01))
chk.append(("return_pct", GA["return_pct"], mine["return_pct"], abs(GA["return_pct"] - mine["return_pct"]) <= 1e-9))
chk.append(("fills_on_day", GA["fills_on_day"], mine["fills_on_day"], GA["fills_on_day"] == mine["fills_on_day"]))
for i, g in enumerate(GA["contributions"]):
    m = mine["contributions"][i] if i < len(mine["contributions"]) else {"code": None, "won": float("nan"), "share_pct": None}
    chk.append((f"상위{i + 1}", f"{g['code']} {g['won']} {g['share_pct']}", f"{m['code']} {m['won']} {m['share_pct']}",
                g["code"] == m["code"] and abs(g["won"] - m["won"]) <= 0.01 and g["share_pct"] == m["share_pct"]))
attr_ok = all(x[3] for x in chk)
RES["attribution"] = {"mine": mine, "check": [{"item": k, "gpt": g, "claude": m, "same": s} for k, g, m, s in chk], "all_same": attr_ok}
for k, g, m, s in chk:
    print("대조", k, "GPT", g, "클로드", m, "같음" if s else "다름", flush=True)
(OUT / "attribution_M4_x2_20260331.json").write_text(json.dumps(RES["attribution"], ensure_ascii=False, indent=1, default=str), encoding="utf-8")
if not attr_ok:
    print("원인 대조 불일치 · 규칙 배치 중단", flush=True)
    raise SystemExit(3)

# ── 2단계: Train 배치 ──
TR, rows, ok = {}, [], []
for cfg in CFG:
    for m in (1.0, 2.0):
        rr = run(cfg, m, *TRAIN)
        a = CM.stats(rr, PT)[PT[0][0]]
        TR[(cfg, m)] = (rr, a)
        RES[f"train_{cfg}_x{m:g}"] = {"engine_report": {k: a[k] for k in ("CAGR", "MDD_daily", "worst_day", "worst_day_at", "day_breach_-15", "positions",
                                                                          "end_nav_won", "worst_month", "month_breach_-15", "turnover_per_year",
                                                                          "top_code", "top_code_share_pct")},
                                      "independent_arith": indep(rr["nav"]), "fills": len(filled(rr)), "notes": rr["notes"],
                                      "trim_fills": sum(1 for f in filled(rr) if f.get("reason") == "보유 축소"),
                                      "max_gap_cash": rr["tot"].get("max_gap_cash", 0.0), "max_gap_nav": rr["tot"].get("max_gap_nav", 0.0)}
        with open(OUT / f"nav_train_{cfg}_x{m:g}.csv", "w", encoding="utf-8") as f:
            f.write("date,nav_won,invested_won\n")
            f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in rr["nav"])
        print("Train", cfg, m, a["CAGR"], a["MDD_daily"], a["worst_day"], a["worst_day_at"], a["day_breach_-15"], "체결", len(filled(rr)),
              "축소", rr["notes"]["trim_filled"], flush=True)
    top = top_of(TR[(cfg, 1.0)][0])
    ax = CM.stats(run(cfg, 1.0, *TRAIN, exclude=top), PT)[PT[0][0]]
    RES[f"train_{cfg}_ex_top"] = {"excluded": top, "CAGR": ax["CAGR"], "end_nav_won": ax["end_nav_won"], "day_breach_-15": ax["day_breach_-15"]}
    a1, a2 = TR[(cfg, 1.0)][1], TR[(cfg, 2.0)][1]
    c = {"day_ok": a1["day_breach_-15"] == 0 and a2["day_breach_-15"] == 0, "cagr2_pos": (a2["CAGR"] or -1) > 0, "ex_top_pos": (ax["CAGR"] or -1) > 0}
    rows.append({"cfg": cfg, **c, "CAGR_x1": a1["CAGR"], "CAGR_x2": a2["CAGR"], "turnover_x2": a2["turnover_per_year"], "MDD_x2": a2["MDD_daily"],
                 "top": top, "CAGR_ex_top": ax["CAGR"]})
    print("제외", cfg, top, ax["CAGR"], c, flush=True)
    if all(c.values()):
        ok.append(rows[-1])
chosen = None
if ok:
    best = max(r_["CAGR_x2"] for r_ in ok)
    near = [r_ for r_ in ok if best - r_["CAGR_x2"] <= 1.0]
    chosen = sorted(near, key=lambda r_: (r_["turnover_x2"], -r_["MDD_x2"], list(CFG).index(r_["cfg"])))[0]["cfg"]
RES["selection"] = {"rows": rows, "passed": [r_["cfg"] for r_ in ok], "chosen": chosen}
print("선택", chosen, [r_["cfg"] for r_ in ok], flush=True)

# ── 자르기 시험(R 판 · 비용 1배) ──
RES["cut_test"] = {}
for cfg in ("R30", "R40", "R50"):
    full = TR[(cfg, 1.0)][0]
    for cut in ("20260102", "20260303"):
        rc = run(cfg, 1.0, TRAIN[0], cut + "0000")
        same_nav = rc["nav"] == full["nav"][:len(rc["nav"])]
        f1 = [f for f in rc["fills"] if str(f["fill_at"])[:8] < cut]
        f2 = [f for f in full["fills"] if str(f["fill_at"])[:8] < cut]
        RES["cut_test"][f"{cfg}_{cut}"] = {"nav_days": len(rc["nav"]), "nav_same": same_nav, "fills_same": f1 == f2, "fills": len(f1)}
        print("자르기", cfg, cut, same_nav, f1 == f2, flush=True)

# ── 선택 뒤 진단(재사용 진단 · OOS 아님): 선택판 + M0 + M4 ──
DIAG = list(dict.fromkeys([x for x in (chosen, "M0", "M4") if x]))
for cfg in DIAG:
    for m in (1.0, 2.0):
        rr = run(cfg, m, *FULLW)
        RES[f"full_{cfg}_x{m:g}"] = CM.strip(CM.stats(rr, PERIODS))
        RES[f"full_{cfg}_x{m:g}"]["fills"] = len(filled(rr))
        RES[f"full_{cfg}_x{m:g}"]["notes"] = rr["notes"]
        if m == 1.0:
            with open(OUT / f"nav_full_{cfg}_x1.csv", "w", encoding="utf-8") as f:
                f.write("date,nav_won,invested_won\n")
                f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in rr["nav"])
    rc = run(cfg, 1.0, *COMMONW)
    RES[f"common_{cfg}_x1"] = CM.strip(CM.stats(rc, (("같은 시작 2025-09-18~2026-08-31", "20250918", "20260831"),)))
    print("진단", cfg, RES[f"full_{cfg}_x1"][PERIODS[2][0]]["CAGR"], RES[f"full_{cfg}_x2"][PERIODS[2][0]]["CAGR"],
          RES[f"common_{cfg}_x1"]["같은 시작 2025-09-18~2026-08-31"]["CAGR"], flush=True)
(OUT / "lc_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                                     encoding="utf-8")
print("끝", flush=True)
