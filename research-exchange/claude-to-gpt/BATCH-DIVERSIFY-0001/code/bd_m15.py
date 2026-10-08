"""BATCH-DIVERSIFY-0001 · 15분봉 D(공평 배분) · DR(D + R30)(GPT PR #56 · 클로드 PREREG 03a34aba).
MR_D1PICKS=<d1_picks.json> python3 -E -P bd_m15.py <b3> <출력>
PR #49 lc_m15.py 계좌 루프에서 ②단계 매수만 '한 묶음 · (RANK, 종목코드) 정렬 · 1칸씩 순환 배분'으로 바꿈. 난수 없음."""
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
CFG = {"D": {"d1filter": True, "fair": True}, "DR": {"d1filter": True, "hold_cap": 0.30, "fair": True}}


def fair_alloc(cands, free):
    """cands: [(종목, need, RANK 값)] 아무 순서 → (RANK, 종목) 정렬 뒤 1칸씩 순환 배분. 돌려줌: (정렬된 종목 목록, {종목: 칸})."""
    order = sorted(cands, key=lambda x: (x[2], x[0]))
    got = {c: 0 for c, _, _ in order}
    left = free
    while left > 0 and any(got[c] < n for c, n, _ in order):
        for c, n, _ in order:
            if left <= 0:
                break
            if got[c] < n:
                got[c] += 1
                left -= 1
    return [c for c, _, _ in order], got
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
             "trim_decided": 0, "trim_filled": 0, "trim_cancelled": 0, "trim_cut_to_remaining": 0, "trim_closed_all": 0, "trim_notional": 0.0,
             "batch_times": 0, "multi_candidate_times": 0, "multi_split_times": 0, "zero_alloc": 0, "short_alloc": 0, "one_slot_positions": 0,
             "invariance_checks": 0}
    shuf = np.random.default_rng(7)                         # 입력 순서 섞기 검사 전용(배분에는 안 씀)
    held_counts = []
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
            held_counts.append(len(pos))
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
        if opt.get("fair") and buys:                        # ② D: 한 묶음 · 공평 배분
            notes["batch_times"] += 1
            kof = dict(buys)
            cands = [(c, want_buy[c][0], RANK(c, data[c], k - 1)) for c, k in buys]
            total = sum(n for _, n, _ in cands)
            free = SLOTS - sum(p["칸"] for p in pos.values())
            if free < total:
                weak = sorted((q for q in pos.values() if STALE(q)), key=lambda q: data[q["code"]]["c"][q["now"]] / q["price"])
                for q in weak:
                    if free >= total:
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
            order, got = fair_alloc(cands, free)
            for perm in (cands[::-1], [cands[i] for i in shuf.permutation(len(cands))]):
                if fair_alloc(perm, free) != (order, got):
                    raise AssertionError("입력 순서에 따라 배분이 달라짐")
                notes["invariance_checks"] += 1
            if len(cands) >= 2:
                notes["multi_candidate_times"] += 1
                if sum(1 for v in got.values() if v > 0) >= 2:
                    notes["multi_split_times"] += 1
            for c in order:
                k = kof[c]
                need, dec = want_buy.pop(c)
                take = got[c]
                if take <= 0:
                    notes["zero_alloc"] += 1
                    continue
                if take < need:
                    notes["short_alloc"] += 1
                o = data[c]["o"][k]
                pid = f"{c}:{T}"
                if acc.buy(pid, c, o, T, dec, value=take / SLOTS * acc.mtm(pf)[0], slots=take, tag=f"칸{take}"):
                    pos[c] = {"pid": pid, "i": k, "price": o, "칸": take, "처음칸": take, "peak": o, "now": k, "day": T[:8], "code": c}
                    notes["one_slot_positions"] += take == 1
            buys = []
        buys.sort(key=lambda ck: (RANK(ck[0], data[ck[0]], ck[1] - 1), rng.random()))
        for c, k in buys:                                   # ② 다음 봉 시가에 사기(B 원래 경로 · D에서는 빈 목록)
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
    held_counts.append(len(pos))
    notes["avg_held_names"] = sum(held_counts) / len(held_counts)
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills, "counts": dict(acc.counts),
            "tot": dict(acc.tot), "notes": notes, "cal": [x[0] for x in navs], "snap": snap}


def by_code(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return by


def raw(r, lo="0", hi="9"):
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


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                            encoding="utf-8")


OUT.mkdir(parents=True, exist_ok=True)
PT = (PERIODS[0],)
BENCH = {"B": {"train_x2_median": (18279632 + 18346201) / 2, "full_x2_cagr": 219.9011}, "R": {"train_x2_median": (18483370 + 18575047) / 2, "full_x2_cagr": 223.4248}}
PAIR = {"D": "B", "DR": "R"}
RES, RUNS = {"runs": {}, "bench": BENCH}, {}
n_run = 0
for cfg in ("D", "DR"):
    for win, (lo, hi) in (("train", TRAIN), ("full", FULLW)):
        for m in (1.0, 2.0):
            n_run += 1
            r = RUNS[(cfg, win, m)] = run(cfg, m, lo, hi)
            per = PT if win == "train" else PERIODS
            rp = CM.stats(r, per)
            key = f"{win}_{cfg}_x{m:g}"
            RES["runs"][key] = {"raw": {p[0]: raw(r, p[1], p[2]) for p in per}, "report": CM.strip(rp), "notes": r["notes"],
                                "monthly": rp[per[-1][0]]["monthly"], "gap": [r["tot"].get("max_gap_cash"), r["tot"].get("max_gap_nav")],
                                "by_code_top5": sorted(((c, round(v)) for c, v in by_code(r).items()), key=lambda x: -x[1])[:5]}
            with open(OUT / f"nav_{key}.csv", "w", encoding="utf-8") as f:
                f.write("date,nav_won,invested_won\n")
                f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in r["nav"])
            w = RES["runs"][key]["raw"][per[-1][0]]
            nt = r["notes"]
            print(n_run, key, round(w["end_nav"]), round(w["CAGR"], 2), round(w["MDD"], 2), round(w["worst_day"], 2), w["worst_day_at"], w["day_breach"],
                  "체결", w["fills"], "묶음", nt["batch_times"], "2개↑", nt["multi_candidate_times"], "나눔", nt["multi_split_times"], "0칸", nt["zero_alloc"],
                  "부족", nt["short_alloc"], "1칸", nt["one_slot_positions"], "평균보유", round(nt["avg_held_names"], 2), "불변검사", nt["invariance_checks"], flush=True)
RES["cut_test"] = {}
for cfg in ("D", "DR"):
    full = RUNS[(cfg, "train", 1.0)]
    for cut in ("20260102", "20260303"):
        n_run += 1
        rc = run(cfg, 1.0, TRAIN[0], cut + "0000")
        f1 = [f for f in rc["fills"] if str(f["fill_at"])[:8] < cut]
        f2 = [f for f in full["fills"] if str(f["fill_at"])[:8] < cut]
        RES["cut_test"][f"{cfg}_{cut}"] = {"nav_same": rc["nav"] == full["nav"][:len(rc["nav"])], "fills_same": f1 == f2, "nav_days": len(rc["nav"]),
                                           "fills": len(f1)}
        print(n_run, "자르기", cfg, cut, RES["cut_test"][f"{cfg}_{cut}"], flush=True)
assert n_run == 12
J = {}
for cfg, b in PAIR.items():
    tr2 = RES["runs"][f"train_{cfg}_x2"]["raw"][PT[0][0]]
    fu2 = RES["runs"][f"full_{cfg}_x2"]["raw"][PERIODS[2][0]]
    breaches = {k: RES["runs"][f"{w}_{cfg}_x{m}"]["raw"][(PT if w == "train" else PERIODS)[-1][0]]["day_breach"]
                for k, w, m in (("train_x1", "train", "1"), ("train_x2", "train", "2"), ("full_x1", "full", "1"), ("full_x2", "full", "2"))}
    inv = all(RES["runs"][f"{w}_{cfg}_x{m}"]["notes"]["invariance_checks"] > 0 for w in ("train", "full") for m in ("1", "2"))
    cut = all(v["nav_same"] and v["fills_same"] for k, v in RES["cut_test"].items() if k.startswith(cfg + "_"))
    crit = {"1_train_x2_ge_median_plus5": tr2["end_nav"] >= 1.05 * BENCH[b]["train_x2_median"],
            "2_no_day_breach": all(v == 0 for v in breaches.values()),
            "3_cagr_x2_pos": tr2["CAGR"] > 0 and fu2["CAGR"] > 0,
            "4_full_x2_cagr_gt_bench": fu2["CAGR"] > BENCH[b]["full_x2_cagr"],
            "6_invariance_and_cut": inv and cut}
    pass_1to4_6 = all(crit.values())
    J[cfg] = {"vs": b, "train_x2_end": tr2["end_nav"], "train_x2_vs_median_pct": (tr2["end_nav"] / BENCH[b]["train_x2_median"] - 1) * 100,
              "full_x2_cagr": fu2["CAGR"], "bench_full_x2_cagr": BENCH[b]["full_x2_cagr"], "breaches": breaches, "criteria": crit,
              "5_concentration": "판정 보류(자료 부족) · B/R 종목별 손익 없음" if pass_1to4_6 else "1~4 · 6 실패로 판단 불필요",
              "verdict": "판정 보류(5번 자료 부족)" if pass_1to4_6 else "실패"}
    print("판정", cfg, crit, J[cfg]["verdict"], flush=True)
RES["judgement"] = J
RES["axis"] = "D 축 종료" if all(J[c]["verdict"] == "실패" for c in J) else "5번 판정 필요"
print(RES["axis"], flush=True)
dump("bd_results.json", RES)
print("끝", flush=True)
