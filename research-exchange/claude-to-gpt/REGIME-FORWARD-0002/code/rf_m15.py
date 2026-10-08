"""REGIME-FORWARD-0002 · 15분봉 통제 소계정(M0 · seed 0 · 비용 2배 · 250만 원) — 신호 경로(2025-09-17 ~ 2026-09-30 한 번) · 9월 평가(09-01 현금 새 시작).
MR_D1PICKS=<d1_picks.json> python3 -E -P rf_m15.py <b3> <출력> <PR #68 m15_natural.pkl>   → <출력>/m15_signal.pkl · m15_eval.pkl
PR #68 rr_m15.py 그대로에 두 가지만 바꿈: ① 9월 시험지 1회 열기(M15_OPEN_OOS=1 · HLAB_OPEN_HOLDOUT=1 · HLAB_CUT=2026093023 → 2026-09-30 봉까지, 10월은 잘라 냄)
② 실행 창 두 개 · 신호 경로의 2026-08-31까지가 PR #68과 한 칸도 다르지 않을 때만 9월 평가를 돌림."""
import bisect
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "m15_exec.py").read_text(encoding="utf-8").split("\ndef run(mult):")[0]
P = {"__name__": "mr_m15", "__file__": str(HERE / "m15_exec.py")}
ENV_OLD = 'if CUT:\n    os.environ["HLAB_CUT"] = CUT\n'
assert _src.count(ENV_OLD) == 1
_src = _src.replace(ENV_OLD, ENV_OLD + 'os.environ["M15_OPEN_OOS"] = "1"\nos.environ["HLAB_OPEN_HOLDOUT"] = "1"\nos.environ["HLAB_CUT"] = "2026093023"\n')
exec(compile(_src, "m15_exec(앞부분 · PR #41 그대로 + 9월 열기 세 줄)", "exec"), P)
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
       "RF": {"d1filter": True, "hold_cap": 0.30, "fresh": True}, "M0": {}}
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
    hold = []

    def held_values():
        v = {}
        for q in acc.pos.values():
            v[q["code"]] = v.get(q["code"], 0.0) + q["qty"] * pf(q["code"])[0]
        return v
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
            hold.append((last_day, held_values()))         # 보고용 기록(판단과 무관)
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
    hold.append((last_day, held_values()))
    if last_day in snaps:
        snapshot(last_day)
    notes["trim_pending_at_end"] = len(trim)
    notes["fresh_changed_codes"] = sorted(changed_codes)
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills, "counts": dict(acc.counts),
            "tot": dict(acc.tot), "notes": notes, "cal": [x[0] for x in navs], "snap": snap, "hold": hold}


import hashlib  # noqa: E402
import pickle  # noqa: E402

LOG = []


class LogAccount(KN.Account):
    def buy(self, pid, code, price, day, decision_at, value=None, qty=None, slots=None, tag=""):
        q = super().buy(pid, code, price, day, decision_at, value=value, qty=qty, slots=slots, tag=tag)
        if q:
            LOG.append((str(day), code, "buy", q, price))
        return q

    def sell(self, pid, price, day, decision_at, qty=None, reason=""):
        code = self.pos[pid]["code"] if pid in self.pos else None
        q = super().sell(pid, price, day, decision_at, qty=qty, reason=reason)
        if q:
            LOG.append((str(day), code, "sell", q, price))
        return q


KN.Account = LogAccount
assert CM.CASH == 2.5e6
assert os.environ.get("HLAB_CUT") == "2026093023" and os.environ.get("M15_OPEN_OOS") == "1"
OUT.mkdir(parents=True, exist_ok=True)
PR68 = Path(sys.argv[3])
assert hashlib.sha256(PR68.read_bytes()).hexdigest() == "61101d86b2032f4a9394830006f69afc48f5c9fdf3dc52da71b42e3550877a02"
OLDM = pickle.load(open(PR68, "rb"))
maxT = max(data[c]["t"][-1] for c in data)
print("봉 마지막 시각", maxT, "· 9월 봉 있는 종목", sum(1 for c in SG if any("20260901" <= t[:8] <= "20260930" for t in data[c]["t"][-400:])), flush=True)
assert maxT < "202610010000"
SIGW = ("202509170000", "202610010000")
EVALW = ("202609010000", "202610010000")


def pack(r, win):
    codes = sorted({x[1] for x in LOG})
    bars = {}
    for c in codes:
        t = data[c]["t"]
        k0, k1 = bisect.bisect_left(t, win[0]), bisect.bisect_left(t, win[1])
        bars[c] = [(t[k], float(data[c]["o"][k]), float(data[c]["c"][k])) for k in range(k0, k1)]
    return {"nav": [(d, float(n), float(i)) for d, n, i in r["nav"]], "log": list(LOG), "bars": bars, "tot": dict(r["tot"]),
            "counts": dict(r["counts"]), "notes": {k: v for k, v in r["notes"].items() if not isinstance(v, (list, set))}, "window": win}


# ① 신호 경로(한 번에 이어서)
r = run("M0", 2.0, *SIGW, seed=0)
sig = pack(r, SIGW)
with open(OUT / "m15_signal.pkl", "wb") as f:
    pickle.dump({k: v for k, v in sig.items() if k != "bars"}, f)
old_nav = [(d, round(n, 6), round(i, 6)) for d, n, i in OLDM["nav"]]
new_nav = [(d, round(n, 6), round(i, 6)) for d, n, i in sig["nav"] if d <= "20260831"]
old_log = [tuple(x) for x in OLDM["log"]]
new_log = [tuple(x) for x in sig["log"] if x[0][:8] <= "20260831"]
cont = {"nav_days_old_new": [len(old_nav), len(new_nav)], "nav_equal": old_nav == new_nav, "log_equal": old_log == new_log,
        "first_nav_diff": next((a[0] for a, b in zip(old_nav, new_nav) if a != b), None),
        "first_log_diff": next((a for a, b in zip(old_log, new_log) if a != b), None),
        "sig_sep_days": [d for d, _, _ in sig["nav"] if d >= "20260901"]}
print("M15 신호 경로", len(sig["nav"]), sig["nav"][0][0], sig["nav"][-1][0], round(sig["nav"][-1][1]), "· 연속성", cont, flush=True)
(OUT / "m15_continuity.json").write_text(json.dumps(cont, ensure_ascii=False, indent=1), encoding="utf-8")
if not (cont["nav_equal"] and cont["log_equal"]):
    print("BLOCKED: 15분봉 신호 경로가 2026-08-31까지 PR #68과 다름 → 9월 평가 안 함", flush=True)
    raise SystemExit(3)

# ② 9월 평가(현금 새 시작)
LOG.clear()
r = run("M0", 2.0, *EVALW, seed=0)
ev = pack(r, EVALW)
with open(OUT / "m15_eval.pkl", "wb") as f:
    pickle.dump(ev, f)
print("M15 9월 평가", len(ev["nav"]), ev["nav"][0][0], ev["nav"][-1][0], round(ev["nav"][-1][1]), "체결", len(ev["log"]), "보존",
      ev["tot"].get("max_gap_cash"), ev["tot"].get("max_gap_nav"), flush=True)
print("끝", flush=True)
