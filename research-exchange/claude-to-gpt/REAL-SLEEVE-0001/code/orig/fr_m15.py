"""FRESH-RANK-0001 · 15분봉 B(M4) · R(R30) · F(최근 D1 우선 정렬) · RF × seed 0~3(GPT PR #54 · 클로드 PREREG 7b8c55bb).
MR_D1PICKS=<d1_picks.json> python3 -E -P fr_m15.py <b3> <출력>
PR #49 lc_m15.py 계좌 루프에서 seed와 같은 시각 매수 후보 정렬 키만 바꿈(난수는 원래처럼 후보마다 목록 순서대로 한 번)."""
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
CFG = {"B": {"d1filter": True}, "R": {"d1filter": True, "hold_cap": 0.30}, "F": {"d1filter": True, "fresh": True},
       "RF": {"d1filter": True, "hold_cap": 0.30, "fresh": True}}
TRAIN = ("202509170000", "202604010000")
FULLW = ("202509170000", "202609010000")
COMMONW = ("202509180000", "202609010000")
PERIODS = (("Train 2025-09-17~2026-03-31", "20250917", "20260331"), ("2026-04~08(재사용 진단)", "20260401", "20260831"),
           ("전체 2025-09-17~2026-08-31", "00000000", "99999999"))


def d1_recent(code, day):
    """그날을 뺀 최근 5거래일(1일봉 달력) 안에 1일봉 신호가 있었나."""
    i = bisect.bisect_left(D1CAL, day)
    return any((code, D1CAL[j]) in D1SET for j in range(max(0, i - 5), i))


def d1_age(code, day):
    """그날을 뺀 1일봉 달력 직전 5거래일 가운데 D1 신호가 있는 가장 최근 날까지의 거리(1~5). 없으면 6."""
    i = bisect.bisect_left(D1CAL, day)
    for age in range(1, 6):
        j = i - age
        if j >= 0 and (code, D1CAL[j]) in D1SET:
            if not D1CAL[j] < day:
                raise AssertionError("미래 참조: D1 날짜 ≥ 판단일")
            return age
    return 6


def run(cfg, mult, lo, hi, exclude=None, snaps=(), seed=0):
    opt = CFG[cfg]
    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"), CM.CASH)
    rng = np.random.default_rng(seed)
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
             "trim_decided": 0, "trim_filled": 0, "trim_cancelled": 0, "trim_cut_to_remaining": 0, "trim_closed_all": 0, "trim_notional": 0.0,
             "multi_candidate_times": 0, "fresh_order_changed_times": 0, "age_missing": 0}
    changed_codes = set()
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
        draw = {ck: rng.random() for ck in buys}         # 원래 키와 같은 순서 · 같은 수로 난수를 뽑음
        base_key = lambda ck: (RANK(ck[0], data[ck[0]], ck[1] - 1), draw[ck])
        if opt.get("fresh"):
            ages = {ck: d1_age(ck[0], want_buy[ck[0]][1][:8]) for ck in buys}
            notes["age_missing"] += sum(1 for v in ages.values() if v == 6)
            order_b = sorted(buys, key=base_key)
            buys.sort(key=lambda ck: (ages[ck],) + base_key(ck))
            if len(buys) >= 2:
                notes["multi_candidate_times"] += 1
                if buys != order_b:
                    notes["fresh_order_changed_times"] += 1
                    changed_codes.update(x[0] for x, y in zip(buys, order_b) if x != y)
        else:
            buys.sort(key=base_key)
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
    notes["fresh_changed_codes"] = sorted(changed_codes)
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills, "counts": dict(acc.counts),
            "tot": dict(acc.tot), "notes": notes, "cal": [x[0] for x in navs], "snap": snap}


def by_code(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return by


def raw(r):
    """반올림 전 CAGR · MDD · 최악 하루 · 넘음 · 회전율(kernel2.report와 같은 식)."""
    nav = r["nav"]
    seg = [CM.CASH] + [x[1] for x in nav]
    rets = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    yrs = KN._years(nav[0][0], nav[-1][0])
    peak, mdd = seg[0], 0.0
    for v in seg:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(range(len(rets)), key=lambda i: rets[i])
    fl = [f for f in r["fills"] if f["status"] in ("FILLED", "REDUCED")]
    avg = sum(x[1] for x in nav) / len(nav)
    return {"CAGR": ((seg[-1] / seg[0]) ** (1 / yrs) - 1) * 100, "MDD": mdd * 100, "worst_day": rets[wd] * 100, "worst_day_at": nav[wd][0],
            "day_breach": sum(1 for x in rets if x < -0.15 - 1e-12), "turnover": sum(f["notional"] for f in fl) / 2 / avg / yrs,
            "end_nav": seg[-1], "fills": len(fl)}


def median(xs):
    s = sorted(xs)
    n = len(s)
    return (s[n // 2 - 1] + s[n // 2]) / 2 if n % 2 == 0 else s[n // 2]


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                            encoding="utf-8")


import subprocess  # noqa: E402
OUT.mkdir(parents=True, exist_ok=True)
PT = (PERIODS[0],)
ORDER, SEEDS = ("B", "R", "F", "RF"), (0, 1, 2, 3)
P49 = json.loads(subprocess.check_output(["git", "-C", os.environ.get("FR_REPO", "/home/user/stock-dash"), "show",
                                          "ba7e05a3ec1aa5db2a09043af3da5a03a8102fc4:research-exchange/claude-to-gpt/LOSS-CONTROL-0001/evidence/lc_results.json"]))
RES, BY = {"runs": {}}, {}
PLAN = [(c, m, 0) for c in ("B", "R") for m in (1.0, 2.0)] + [(c, 2.0, s) for c in ("B", "R") for s in (1, 2, 3)] + \
       [(c, m, 0) for c in ("F", "RF") for m in (1.0, 2.0)] + [(c, 2.0, s) for c in ("F", "RF") for s in (1, 2, 3)]
assert len(PLAN) == 20 and len(set(PLAN)) == 20
for n_run, (cfg, m, seed) in enumerate(PLAN, 1):
    r = run(cfg, m, *TRAIN, seed=seed)
    a = CM.stats(r, PT)[PT[0][0]]
    w = raw(r)
    key = f"{cfg}_x{m:g}_s{seed}"
    RES["runs"][key] = {"cfg": cfg, "mult": m, "seed": seed, "raw": w, "report": CM.strip({PT[0][0]: a})[PT[0][0]], "notes": r["notes"],
                        "trim_fills": sum(1 for f in r["fills"] if f.get("reason") == "보유 축소" and f["status"] == "FILLED"),
                        "gap": [r["tot"].get("max_gap_cash"), r["tot"].get("max_gap_nav")]}
    BY[key] = by_code(r)
    with open(OUT / f"nav_{key}.csv", "w", encoding="utf-8") as f:
        f.write("date,nav_won,invested_won\n")
        f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in r["nav"])
    print(n_run, key, round(w["end_nav"]), round(w["CAGR"], 2), round(w["MDD"], 2), round(w["worst_day"], 2), w["worst_day_at"], w["day_breach"],
          "포지션", a["positions"], "체결", w["fills"], "바뀐 순서", r["notes"]["fresh_order_changed_times"], "/", r["notes"]["multi_candidate_times"], flush=True)
    if n_run == 4:                                          # seed 0 B · R 비용 1 · 2배 기준 맞춤(PR #49)
        chk = {}
        for c, old in (("B", "M4"), ("R", "R30")):
            for mm in ("1", "2"):
                o, me = P49[f"train_{old}_x{mm}"], RES["runs"][f"{c}_x{mm}_s0"]
                pairs = {"end_nav_won": (o["engine_report"]["end_nav_won"], me["report"]["end_nav_won"]),
                         "CAGR": (o["engine_report"]["CAGR"], me["report"]["CAGR"]), "MDD": (o["engine_report"]["MDD_daily"], me["report"]["MDD_daily"]),
                         "worst_day_unrounded": (o["independent_arith"]["worst_day_unrounded_pct"], me["raw"]["worst_day"]),
                         "worst_day_at": (o["engine_report"]["worst_day_at"], me["raw"]["worst_day_at"]),
                         "day_breach": (o["engine_report"]["day_breach_-15"], me["raw"]["day_breach"]),
                         "positions": (o["engine_report"]["positions"], me["report"]["positions"]), "fills": (o["fills"], me["raw"]["fills"]),
                         "trim_fills": (o["trim_fills"], me["trim_fills"])}
                for k, (x, y) in pairs.items():
                    chk[f"{c}_x{mm}_{k}"] = {"pr49": x, "claude": y, "same": (abs(x - y) <= 1e-9 * max(1, abs(x))) if isinstance(x, float) else x == y}
        RES["baseline_check"] = chk
        bad = [k for k, v in chk.items() if not v["same"]]
        print("기준 맞춤", "같음" if not bad else f"다름 {bad}", flush=True)
        if bad:
            dump("fr_results.json", RES)
            print("BLOCKED · 기준 불일치로 중단", flush=True)
            raise SystemExit(3)

# ── 판정 ──
E = lambda c, s: RES["runs"][f"{c}_x2_s{s}"]["raw"]


def concentration(a, b):
    """seed마다 (b − a) 종목별 손익 차이 · 양의 개선분 중 최대 종목 몫."""
    out = []
    for s in SEEDS:
        A, Bb = BY[f"{a}_x2_s{s}"], BY[f"{b}_x2_s{s}"]
        diff = {c: Bb.get(c, 0.0) - A.get(c, 0.0) for c in set(A) | set(Bb)}
        pos = sum(v for v in diff.values() if v > 0)
        top = max(diff.items(), key=lambda x: x[1])
        ranked = sorted(diff.items(), key=lambda x: -abs(x[1]))[:5]
        out.append({"seed": s, "net": E(b, s)["end_nav"] - E(a, s)["end_nav"], "positive_sum": pos, "top_code": top[0], "top_won": top[1],
                    "top_share_of_positive": top[1] / pos if pos > 0 else None, "top5_abs": ranked})
    return out


def paired(a, b):
    d = [E(b, s)["end_nav"] - E(a, s)["end_nav"] for s in SEEDS]
    rate = [E(b, s)["end_nav"] / E(a, s)["end_nav"] - 1 for s in SEEDS]
    return {"diff": d, "rate": rate, "wins": sum(1 for x in d if x > 0), "median_diff": median(d), "median_rate": median(rate),
            "worst_seed": min(SEEDS, key=lambda s: d[s]), "worst_diff": min(d)}


R_vs_B = paired("B", "R")
mB = median([E("B", s)["end_nav"] for s in SEEDS])
RES["r30"] = dict(R_vs_B, median_B_end=mB, threshold=0.02 * mB, keep=R_vs_B["wins"] >= 3 and R_vs_B["median_diff"] >= 0.02 * mB,
                  concentration=concentration("B", "R"))
cands = {}
for cand, base in (("F", "B"), ("RF", "R")):
    pr = paired(base, cand)
    conc = concentration(base, cand)
    tops = [x["top_code"] for x in conc if x["top_share_of_positive"] is not None and x["top_share_of_positive"] >= 0.70]
    same_code_seeds = max((tops.count(c) for c in set(tops)), default=0)
    x1 = RES["runs"][f"{cand}_x1_s0"]["raw"]
    c2 = [E(cand, s)["CAGR"] for s in SEEDS]
    crit = {"1_wins_ge3": pr["wins"] >= 3, "2_median_rate_ge5pct": pr["median_rate"] >= 0.05,
            "3_no_day_breach": all(E(cand, s)["day_breach"] == 0 for s in SEEDS) and x1["day_breach"] == 0,
            "4_cagr_pos": x1["CAGR"] > 0 and median(c2) > 0, "5_not_concentrated_same_code": same_code_seeds < 3}
    cands[cand] = {"vs": base, "paired": pr, "concentration": conc, "criteria": crit, "pass": all(crit.values()),
                   "seeds_top_ge70_any_code": len(tops), "seeds_top_ge70_same_code": same_code_seeds,
                   "pass_if_any_code_rule": all(v for k, v in crit.items() if not k.startswith("5")) and len(tops) < 3,
                   "median_cagr_x2": median(c2), "worst_seed_cagr_x2": min(c2), "median_mdd_x2": median([E(cand, s)["MDD"] for s in SEEDS])}
    print("판정", cand, "vs", base, crit, "통과" if cands[cand]["pass"] else "실패", flush=True)
RES["candidates"] = cands
passed = [c for c in ("F", "RF") if cands[c]["pass"]]
chosen = None
if passed:
    best = max(cands[c]["median_cagr_x2"] for c in passed)
    near = [c for c in passed if best - cands[c]["median_cagr_x2"] <= 1.0]
    chosen = sorted(near, key=lambda c: (-cands[c]["worst_seed_cagr_x2"], -cands[c]["median_mdd_x2"], ("F", "RF").index(c)))[0]
RES["verdict"] = {"R30": "유지" if RES["r30"]["keep"] else "종료(경로 민감 후보로 내려놓음)",
                  "F_RF": f"개선 후보({chosen})" if chosen else "개선 없음", "passed": passed}
print("R30", RES["verdict"]["R30"], "· F/RF", RES["verdict"]["F_RF"], flush=True)
dump("fr_results.json", RES)
print("끝", flush=True)
