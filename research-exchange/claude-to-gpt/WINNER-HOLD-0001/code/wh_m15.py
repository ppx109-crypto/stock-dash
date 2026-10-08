"""WINNER-HOLD-0001 · 15분봉 B(M4) · R(R30) · H · RH(GPT PR #52 PREREG · 클로드 PREREG ab31b32b).
WH_STAGE=train|diag [WH_LOCK=<LOCK.json>] MR_D1PICKS=<d1_picks.json> python3 -E -P wh_m15.py <b3> <출력>
PR #49 lc_m15.py 계좌 루프를 그대로 두고 'H: 첫 부분청산 1회 보류' 갈고리와 매도 기록만 더함."""
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
CFG = {"B": {"d1filter": True}, "R": {"d1filter": True, "hold_cap": 0.30}, "H": {"d1filter": True, "hold_first": True},
       "RH": {"d1filter": True, "hold_cap": 0.30, "hold_first": True}}
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
    sells, holds = [], []                                   # 매도 기록(보류 효과 근사용) · H 보류 목록
    _sell = acc.sell

    def sell_rec(pid, price, day, dec, qty=None, reason=""):
        q = _sell(pid, price, day, dec, qty=qty, reason=reason)
        if q:
            sells.append((pid, day, price, q, reason))
        return q
    acc.sell = sell_rec
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
             "h_checked": 0, "h_no_d1": 0, "h_not_profit": 0, "h_suppressed": 0}
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
                if opt.get("hold_first") and n and n != "all" and not p.get("h_seen"):
                    p["h_seen"] = True                      # 포지션의 첫 부분청산 요청만 봄
                    notes["h_checked"] += 1
                    ok1 = d1_recent(c, T[:8])
                    pp = acc.pos[p["pid"]]
                    val = pp["qty"] * bb["c"][k]
                    net = val * (1 - acc.costs.rate("sell", c, T, val)[0]) - pp["basis"]
                    if not ok1:
                        notes["h_no_d1"] += 1
                    if net <= 0:
                        notes["h_not_profit"] += 1
                    if ok1 and net > 0:
                        part = p["칸"] if n >= p["칸"] else int(n)
                        holds.append({"pid": p["pid"], "code": c, "T": T, "part_ratio": part / p["칸"],
                                      "qty_held_back": math.floor(pp["qty"] * part / p["칸"]), "close": bb["c"][k],
                                      "next_open": bb["o"][k + 1] if k + 1 < len(bb["t"]) else None, "net_won": net})
                        notes["h_suppressed"] += 1
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
            "tot": dict(acc.tot), "notes": notes, "cal": [x[0] for x in navs], "snap": snap, "sells": sells, "holds": holds,
            "last_close": dict(last_close)}


def top_of(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return max(by.items(), key=lambda x: x[1])[0] if by else None


def by_code(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return by


def raw(r, lo="0", hi="9"):
    """반올림 전 CAGR · MDD · 최악 하루 · 넘음 · 회전율(kernel2.report와 같은 식)."""
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
            "end_nav": seg[-1], "fills": len(fl), "positions_closed_or_open": None}


def hold_effects(r):
    """보류 목록마다 다음 실제 매도(체결가 · 이유)와 효과 근사 = 보류 수량 × (다음 매도가 − 다음 봉 시가)."""
    out = []
    for h in r["holds"]:
        nxt = next((s for s in r["sells"] if s[0] == h["pid"] and s[1] > h["T"]), None)
        px = nxt[2] if nxt else r["last_close"].get(h["code"])
        eff = h["qty_held_back"] * (px - h["next_open"]) if h["next_open"] is not None and px is not None else None
        out.append(dict(h, next_sell_T=nxt[1] if nxt else None, next_sell_px=px, next_sell_reason=nxt[4] if nxt else "끝까지 보유(마지막 종가)",
                        effect_won_approx=eff))
    return out


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                            encoding="utf-8")


def save_nav(name, r):
    with open(OUT / f"nav_{name}.csv", "w", encoding="utf-8") as f:
        f.write("date,nav_won,invested_won\n")
        f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in r["nav"])


import subprocess  # noqa: E402
OUT.mkdir(parents=True, exist_ok=True)
STAGE = os.environ["WH_STAGE"]                     # 3번째 인자는 m15_exec가 HLAB_CUT으로 읽으므로 쓰지 않음
PT = (PERIODS[0],)
ORDER = ("B", "R", "H", "RH")
PR49_EX = {"B": 112.08, "R": 112.99}
if STAGE == "train":
    P49 = json.loads(subprocess.check_output(["git", "-C", os.environ.get("WH_REPO", "/home/user/stock-dash"), "show",
                                              "ba7e05a3ec1aa5db2a09043af3da5a03a8102fc4:research-exchange/claude-to-gpt/LOSS-CONTROL-0001/evidence/lc_results.json"]))
    RES, TR = {}, {}
    for cfg in ORDER:
        for m in (1.0, 2.0):
            r = TR[(cfg, m)] = run(cfg, m, *TRAIN)
            a = CM.stats(r, PT)[PT[0][0]]
            w = raw(r)
            RES[f"train_{cfg}_x{m:g}"] = {"report": CM.strip({PT[0][0]: a})[PT[0][0]], "raw": w, "notes": r["notes"],
                                          "trim_fills": sum(1 for s in r["sells"] if s[4] == "보유 축소"),
                                          "gap": [r["tot"].get("max_gap_cash"), r["tot"].get("max_gap_nav")]}
            save_nav(f"train_{cfg}_x{m:g}", r)
            print("Train", cfg, m, a["CAGR"], a["MDD_daily"], a["worst_day"], a["worst_day_at"], a["day_breach_-15"], "포지션", a["positions"],
                  "체결", w["fills"], "H", r["notes"].get("h_checked", 0), r["notes"].get("h_suppressed", 0), flush=True)
        if cfg in ("B", "R"):                                   # 기준 맞춤(PR #49 M4 · R30)
            old = {"B": "M4", "R": "R30"}[cfg]
            chk = {}
            for m in ("1", "2"):
                o = P49[f"train_{old}_x{m}"]
                mine = RES[f"train_{cfg}_x{m}"]
                pairs = {"end_nav_won": (o["engine_report"]["end_nav_won"], mine["report"]["end_nav_won"]),
                         "CAGR": (o["engine_report"]["CAGR"], mine["report"]["CAGR"]),
                         "MDD": (o["engine_report"]["MDD_daily"], mine["report"]["MDD_daily"]),
                         "worst_day_unrounded": (o["independent_arith"]["worst_day_unrounded_pct"], mine["raw"]["worst_day"]),
                         "worst_day_at": (o["engine_report"]["worst_day_at"], mine["report"]["worst_day_at"]),
                         "day_breach": (o["engine_report"]["day_breach_-15"], mine["report"]["day_breach_-15"]),
                         "positions": (o["engine_report"]["positions"], mine["report"]["positions"]),
                         "fills": (o["fills"], mine["raw"]["fills"]), "trim_fills": (o["trim_fills"], mine["trim_fills"])}
                for k, (x, y) in pairs.items():
                    same = abs(x - y) <= 1e-9 * max(1, abs(x)) if isinstance(x, float) else x == y
                    chk[f"x{m}_{k}"] = {"pr49": x, "claude": y, "same": same}
            RES[f"baseline_{cfg}"] = chk
            bad = [k for k, v in chk.items() if not v["same"]]
            print("기준 맞춤", cfg, "같음" if not bad else f"다름 {bad}", flush=True)
            if bad:
                dump("wh_train.json", RES)
                print("기준 불일치 · 새 판 계산 중단(BLOCKED)", flush=True)
                raise SystemExit(3)
    # ── 제외 2판(H · RH) ──
    rows = []
    for cfg in ORDER:
        r1, r2 = RES[f"train_{cfg}_x1"]["raw"], RES[f"train_{cfg}_x2"]["raw"]
        top = top_of(TR[(cfg, 1.0)])
        if cfg in ("H", "RH"):
            rx = run(cfg, 1.0, *TRAIN, exclude=top)
            exc = raw(rx)["CAGR"]
            RES[f"train_{cfg}_ex_top"] = {"excluded": top, "raw": raw(rx), "CAGR_engine": CM.stats(rx, PT)[PT[0][0]]["CAGR"]}
        else:
            exc = PR49_EX[cfg]
        c = {"day_ok": r1["day_breach"] == 0 and r2["day_breach"] == 0, "cagr2_pos": r2["CAGR"] > 0, "ex_top_pos": exc > 0}
        rows.append({"cfg": cfg, **c, "CAGR_x1": r1["CAGR"], "CAGR_x2": r2["CAGR"], "turnover_x2": r2["turnover"], "MDD_x2": r2["MDD"],
                     "top": top, "CAGR_ex_top": exc, "ex_source": "이번 계산" if cfg in ("H", "RH") else "PR #49"})
        print("선택표", cfg, round(r2["CAGR"], 4), c, top, exc, flush=True)
    ok = [r for r in rows if r["day_ok"] and r["cagr2_pos"] and r["ex_top_pos"]]
    chosen = None
    if ok:
        best = max(r["CAGR_x2"] for r in ok)
        near = [r for r in ok if best - r["CAGR_x2"] <= 1.0]
        chosen = sorted(near, key=lambda r: (r["turnover_x2"], -r["MDD_x2"], ORDER.index(r["cfg"])))[0]["cfg"]
    RES["selection"] = {"rows": rows, "passed": [r["cfg"] for r in ok], "chosen": chosen}
    print("선택", chosen, [r["cfg"] for r in ok], flush=True)
    # ── 보류 목록 · 종목별 분해 ──
    for cfg in ("H", "RH"):
        for m in (1.0, 2.0):
            RES[f"holds_{cfg}_x{m:g}"] = hold_effects(TR[(cfg, m)])
    for a_, b_ in (("B", "H"), ("R", "RH")):
        for m in (1.0, 2.0):
            ba, bb_ = by_code(TR[(a_, m)]), by_code(TR[(b_, m)])
            diff = {c: bb_.get(c, 0.0) - ba.get(c, 0.0) for c in set(ba) | set(bb_)}
            diff = sorted(((c, v) for c, v in diff.items() if abs(v) > 0.5), key=lambda x: x[1])
            RES[f"by_code_{a_}_to_{b_}_x{m:g}"] = {"total": sum(v for _, v in diff), "nav_diff": TR[(b_, m)]["nav"][-1][1] - TR[(a_, m)]["nav"][-1][1],
                                                   "codes": diff}
    # ── 자르기 4판(H · RH 비용 1배) ──
    RES["cut_test"] = {}
    for cfg in ("H", "RH"):
        full = TR[(cfg, 1.0)]
        for cut in ("20260102", "20260303"):
            rc = run(cfg, 1.0, TRAIN[0], cut + "0000")
            f1 = [{k: v for k, v in f.items()} for f in rc["fills"] if str(f["fill_at"])[:8] < cut]
            f2 = [{k: v for k, v in f.items()} for f in full["fills"] if str(f["fill_at"])[:8] < cut]
            RES["cut_test"][f"{cfg}_{cut}"] = {"nav_days": len(rc["nav"]), "nav_same": rc["nav"] == full["nav"][:len(rc["nav"])],
                                               "fills_same": f1 == f2, "fills": len(f1)}
            print("자르기", cfg, cut, RES["cut_test"][f"{cfg}_{cut}"], flush=True)
    dump("wh_train.json", RES)
    dump("LOCK.json", {"task_id": "WINNER-HOLD-0001", "chosen": chosen, "passed": RES["selection"]["passed"], "selection_rows": rows,
                       "cut_test": RES["cut_test"], "baseline_same": True, "note": "Train만 보고 고른 판. 원격 커밋 뒤에 진단을 돌림."})
    print("끝 train", flush=True)

elif STAGE == "diag":
    LOCK = json.loads(Path(os.environ["WH_LOCK"]).read_text(encoding="utf-8"))
    chosen = LOCK["chosen"]
    RES = {"lock": LOCK}
    for cfg in dict.fromkeys([x for x in ("B", "R", chosen) if x]):
        for m in (1.0, 2.0):
            r = run(cfg, m, *FULLW)
            rp = CM.stats(r, PERIODS)
            RES[f"full_{cfg}_x{m:g}"] = {"report": CM.strip(rp), "raw": {p[0]: raw(r, p[1], p[2]) for p in PERIODS}, "notes": r["notes"],
                                         "monthly": rp[PERIODS[2][0]]["monthly"]}
            if cfg in ("H", "RH"):
                RES[f"holds_full_{cfg}_x{m:g}"] = hold_effects(r)
            save_nav(f"full_{cfg}_x{m:g}", r)
            print("진단", cfg, m, {p[0]: rp[p[0]]["CAGR"] for p in PERIODS}, "MDD", rp[PERIODS[2][0]]["MDD_daily"],
                  "넘음", rp[PERIODS[2][0]]["day_breach_-15"], flush=True)
    dump("wh_diag.json", RES)
    print("끝 diag", flush=True)
