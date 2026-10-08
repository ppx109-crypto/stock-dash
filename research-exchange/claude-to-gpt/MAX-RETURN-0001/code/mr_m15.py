"""MAX-RETURN-0001 · 15분봉 M0 ~ M4(PREREG). MR_D1PICKS=<d1_picks.json> python3 -E -P mr_m15.py <b3> <출력>
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
CFG = {"M0": {}, "M1": {"skip_weak": True}, "M2": {"no_partial": True}, "M3": {"skip_weak": True, "no_partial": True}, "M4": {"d1filter": True}}
TRAIN = ("202509170000", "202604010000")
FULLW = ("202509170000", "202609010000")
COMMONW = ("202509180000", "202609010000")
PERIODS = (("Train 2025-09-17~2026-03-31", "20250917", "20260331"), ("2026-04~08(재사용 진단)", "20260401", "20260831"),
           ("전체 2025-09-17~2026-08-31", "00000000", "99999999"))


def d1_recent(code, day):
    """그날을 뺀 최근 5거래일(1일봉 달력) 안에 1일봉 신호가 있었나."""
    i = bisect.bisect_left(D1CAL, day)
    return any((code, D1CAL[j]) in D1SET for j in range(max(0, i - 5), i))


def run(cfg, mult, lo, hi, exclude=None):
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
    notes = {"cant_split": 0, "stale_bumped": 0, "buy_signal_no_slot": 0, "skip_weak": 0, "skip_no_d1": 0, "partial_suppressed": 0}
    pf = lambda code: (last_close.get(code, 0.0), False)
    for T in times:
        if last_day and T[:8] != last_day:
            nav, inv = acc.mtm(pf)
            acc.check(pf)
            navs.append((last_day, nav, inv))
            gross.append((last_day, nav + acc.cum_cost()))
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
        last_day = T[:8]
    nav, inv = acc.mtm(pf)
    acc.check(pf)
    navs.append((last_day, nav, inv))
    gross.append((last_day, nav + acc.cum_cost()))
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills, "counts": dict(acc.counts),
            "tot": dict(acc.tot), "notes": notes, "cal": [x[0] for x in navs]}


def top_of(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return max(by.items(), key=lambda x: x[1])[0] if by else None


OUT.mkdir(parents=True, exist_ok=True)
PT = (PERIODS[0],)
TR, rows, ok = {}, [], []
for cfg in CFG:
    for m in (1.0, 2.0):
        r = run(cfg, m, *TRAIN)
        TR[(cfg, m)] = (r, CM.stats(r, PT)[PT[0][0]])
    top = top_of(TR[(cfg, 1.0)][0])
    ax = CM.stats(run(cfg, 1.0, *TRAIN, exclude=top), PT)[PT[0][0]]
    a1, a2 = TR[(cfg, 1.0)][1], TR[(cfg, 2.0)][1]
    c = {"day_ok": a1["day_breach_-15"] == 0 and a2["day_breach_-15"] == 0, "cagr2_pos": (a2["CAGR"] or -1) > 0, "ex_top_pos": (ax["CAGR"] or -1) > 0}
    rows.append({"cfg": cfg, **c, "CAGR_x1": a1["CAGR"], "CAGR_x2": a2["CAGR"], "MDD_x1": a1["MDD_daily"], "worst_day_x1": a1["worst_day"],
                 "worst_month_x1": a1["worst_month"], "month_breach_x1": a1["month_breach_-15"], "turnover": a1["turnover_per_year"],
                 "positions": a1["positions"], "top": top, "CAGR_ex_top": ax["CAGR"], "notes": TR[(cfg, 1.0)][0]["notes"]})
    print("Train", cfg, a1["CAGR"], a2["CAGR"], a1["worst_day"], "제외", top, ax["CAGR"], a1["positions"], flush=True)
    if all(c.values()):
        ok.append(rows[-1])
ok.sort(key=lambda r: -r["CAGR_x1"])
chosen = None
if ok:
    best = ok[0]["CAGR_x1"]
    chosen = sorted([r for r in ok if best - r["CAGR_x1"] <= 1.0], key=lambda r: (-r["CAGR_x2"], list(CFG).index(r["cfg"])))[0]["cfg"]
print("15분봉 선택", chosen, [r["cfg"] for r in ok], flush=True)
FULL = {}
for cfg in CFG:
    for m in (1.0, 2.0):
        r = run(cfg, m, *FULLW)
        FULL[(cfg, m)] = CM.stats(r, PERIODS)
        if m == 1.0:
            FULL[(cfg, "top")] = top_of(r)
            FULL[(cfg, "ex")] = CM.stats(run(cfg, 1.0, *FULLW, exclude=FULL[(cfg, "top")]), PERIODS)
            rc = run(cfg, 1.0, *COMMONW)
            FULL[(cfg, "common")] = CM.stats(rc, (("같은 시작 2025-09-18~2026-08-31", "20250918", "20260831"),))
            if cfg in ("M0", chosen):
                with open(OUT / f"nav_{cfg}_x1_1e7.csv", "w", encoding="utf-8") as f:
                    f.write("date,nav_norm,invested_ratio\n")
                    f.writelines(f"{d},{n / CM.CASH:.6f},{i / n:.5f}\n" for d, n, i in r["nav"])
    print("전체", cfg, FULL[(cfg, 1.0)][PERIODS[2][0]]["CAGR"], "같은 시작", FULL[(cfg, "common")]["같은 시작 2025-09-18~2026-08-31"]["CAGR"], flush=True)
out = {"train": rows, "chosen": chosen, "passed": [r["cfg"] for r in ok],
       "full": {f"{k[0]}_{k[1]}": (CM.strip(v) if isinstance(v, dict) else v) for k, v in FULL.items()},
       "monthly_M0": FULL[("M0", 1.0)][PERIODS[2][0]]["monthly"], "monthly_chosen": FULL[(chosen, 1.0)][PERIODS[2][0]]["monthly"] if chosen else None}
(OUT / "m15_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("끝", flush=True)
