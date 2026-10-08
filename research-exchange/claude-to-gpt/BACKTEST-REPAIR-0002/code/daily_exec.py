"""BACKTEST-REPAIR-0002 · 일봉 전략 순차 재실행(1일봉 새82 FIX · 빈칸 엔진 · 코스닥 인버스 · 바구니 C).
python3 daily_exec.py <b2 폴더(00b98ab1)> <nrl 캐시> <출력 폴더>

- 1일봉: 원 엔진(lab.run)의 칸 판단 · 청산 함수 · 순위 · 겹침 · 상하한가를 그대로 부르고, 계좌만 돈 장부(kernel2)로 순차 실행.
  기존 원장(d1_ledger_*.csv)은 읽지 않음. 비교 기준(원 엔진 칸 원장)은 같은 프로세스에서 lab.run을 다시 돌려 얻음.
- 빈칸 엔진 · 인버스 · 바구니: 원 step을 그대로 부르고, research adapter가 체결 확인 뒤 상태를 확정.
- mode 'next' = d 종가 판단 → 다음 거래일 종가 체결(별도 연구 규칙) · 'close' = 같은 날 종가(종가 근사 · 원본 재현 불가).
- 네트워크 막음 · 키 환경변수 지움 · 운영 파일 안 고침."""
import bisect
import copy
import json
import math
import os
import pickle
import socket
import sys
import time
from collections import Counter
from datetime import date as _date
from pathlib import Path

BASE, CACHE, OUT = str(Path(sys.argv[1]).resolve()), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).resolve().parent


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
os.environ["NRL_CACHE"] = CACHE
os.environ.pop("CAPS_ADJ", None)
os.environ["COST_REPLAY_ROOT"] = BASE
sys.path.insert(0, str(HERE))
import cost_contract as CC  # noqa: E402
import kernel2 as KN  # noqa: E402
import rules as ER  # noqa: E402
os.chdir(BASE)
sys.path[:0] = [BASE, BASE + "/research"]
T0 = time.time()
import final_group, final_study, caps, lab, rule, study  # noqa: E402,F401
import nrl  # noqa: E402
import basket_live  # noqa: E402

START, SLOTS, CAP, X_CUT = "20170201", 10, 130, "20211015"

# ───────── 1일봉 FIX 바꿔 끼우기(PR #39 d1_signals.py와 같은 식) ─────────
ORIG_HOLDS, FULL_CALM = rule.holds, rule._calm


def flow_patch(shift):
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
    edge = (nrl.CALM_MONTH or {}).get(r["date"][:6])
    if edge is None:
        raise RuntimeError(f"달별 calm 문턱 없음: {r['date'][:6]}")
    rule._calm = edge
    try:
        return ORIG_HOLDS(r)
    finally:
        rule._calm = FULL_CALM


nrl.teacher, nrl.steady = flow_patch(1)
rule.holds = holds_monthly
HOLD, SIZE, RANK, EXIT, KIN = nrl.BASE_HOLD, nrl.BASE_SIZE, rule.order, nrl.BASE_EXIT, nrl.kin
LANE = lab.lanes(nrl.prices)
IDXOF = {c: {x: i for i, x in enumerate(v["날"])} for c, v in LANE.items()}
CL = {c: dict(v["rows"]) for c, v in nrl.prices.items()}
CLD = {c: sorted(v) for c, v in CL.items()}
PICKS = {}
for row in nrl.inside:
    if row["date"] >= START and HOLD(row):
        PICKS.setdefault(row["date"], []).append(row)
LAST = max(r["date"] for r in nrl.inside)
DAYS = [d for d in lab.trading_days(LANE) if START <= d <= LAST]
BR = nrl.BR
DIDX = {d: i for i, d in enumerate(DAYS)}
KQ = {p.stem for p in Path(BASE, "kosdaq-data").glob("*.json")}
market_of = lambda c: "KOSDAQ" if c in KQ else "KOSPI"
row_i_mismatch = sum(1 for rs in PICKS.values() for r in rs if LANE[r["code"]]["날"][r["i"]] != r["date"])
META = {"days": [DAYS[0], DAYS[-1]], "n_days": len(DAYS), "picks_days": len(PICKS), "picks_rows": sum(len(v) for v in PICKS.values()),
        "row_i_date_mismatch": row_i_mismatch, "br_days_equal": sorted(d for d in BR if START <= d <= LAST) == DAYS}
print("준비", round(time.time() - T0), "초", META, flush=True)


def stock_pf(CLm, CLDm, d):
    def f(code):
        v = CLm.get(code, {}).get(d)
        if v:
            return v, False
        ds = CLDm.get(code, [])
        k = bisect.bisect_right(ds, d) - 1
        return (CLm[code][ds[k]] if k >= 0 else 0.0), True
    return f


def reject(acc, pid, code, side, dec, day, why, slots=None, tag=""):
    acc._miss({"pid": pid, "code": code, "side": side, "decision_at": dec, "fill_at": day, "slots": slots, "tag": tag},
              "UNFILLED" if side == "buy" else "RETRY", why)


def finish(acc, navs, gross, pf, last_day, extra):
    liq, liq_cost = acc.liquidation_nav(pf, last_day)
    return dict({"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills,
                 "counts": dict(acc.counts), "tot": dict(acc.tot), "liquidation": {"nav": liq, "cost": liq_cost}}, **extra)


# ───────── 1일봉 ─────────
def run_d1(mode, mult, LN=None, CLm=None, PK=None, snap_day=None):
    LN, CLm, PK = LN or LANE, CLm or CL, PK if PK is not None else PICKS
    CLDm = {c: sorted(v) for c, v in CLm.items()} if CLm is not CL else CLD
    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"))
    open_, frozen, pend_buy, pend_sell = {}, {}, [], []
    navs, gross, notes, snap, max_used = [], [], Counter(), None, 0
    for d in DAYS:
        pf = stock_pf(CLm, CLDm, d)
        if mode == "next":
            keep = []
            for o in pend_sell:                                     # 파는 것 먼저
                pid, c = o["pid"], o["code"]
                if pid not in acc.pos:
                    continue
                j, price = IDXOF[c].get(d), CLm.get(c, {}).get(d)
                if price is None:
                    reject(acc, pid, c, "sell", o["dec"], d, "체결 날 값 없음 → 다음 날 다시")
                    keep.append(o)
                    continue
                if j is not None and lab.locked(LN[c]["closes"], LN[c]["날"], j, -1):
                    reject(acc, pid, c, "sell", o["dec"], d, "하한가 → 다음 날 다시")
                    keep.append(o)
                    continue
                if o["kind"] == "all":
                    acc.sell(pid, price, d, o["dec"], reason=o["why"])
                else:
                    q = math.floor(acc.pos[pid]["qty"] * o["frac"])
                    if q < 1:
                        notes["cant_split"] += 1
                    else:
                        acc.sell(pid, price, d, o["dec"], qty=q, reason=o["why"])
            pend_sell = keep
            for o in pend_buy:
                c = o["code"]
                j, price = IDXOF[c].get(d), CLm.get(c, {}).get(d)
                if j is None or price is None:
                    reject(acc, o["pid"], c, "buy", o["dec"], d, "체결 날 값 없음", o["slots"])
                    continue
                if lab.locked(LN[c]["closes"], LN[c]["날"], j, 1):
                    reject(acc, o["pid"], c, "buy", o["dec"], d, "상한가", o["slots"])
                    continue
                if acc.buy(o["pid"], c, price, d, o["dec"], value=o["value"], slots=o["slots"], tag=f"칸{o['slots']}"):
                    open_[c] = {"pid": o["pid"], "i": j, "price": price, "step": 0, "peak": price, "row": o["row"],
                                "자리": o["slots"], "filled": d}
            pend_buy = []
        for c in list(open_):                                       # 들고 있는 것 판단(원 엔진 순서)
            spot = open_[c]
            if spot["filled"] == d:
                continue
            closes = LN[c]["closes"]
            step = spot["step"] + 1
            index = spot["i"] + step
            if index >= len(closes):
                frozen[spot["pid"]] = open_.pop(c)
                notes["data_end_frozen"] += 1
                continue
            forced = step > CAP
            spot["peak"] = max(spot["peak"], closes[index])
            if mode == "close" and lab.locked(closes, LN[c]["날"], index, -1):
                spot["step"] = step
                continue
            if LN[c]["날"][index] != d:
                notes["lane_date_mismatch"] += 1
            decided = True if forced else EXIT(LN[c], spot["i"], spot["price"], step, spot["peak"], spot["row"])
            notes["cap_forced"] += forced
            if decided is not True and isinstance(decided, int) and not isinstance(decided, bool) and decided > 0:
                if spot["자리"] < 2:
                    spot["step"] = step
                    continue
                part = min(decided, spot["자리"] - 1)
                frac = part / spot["자리"]
                if mode == "close":
                    q = math.floor(acc.pos[spot["pid"]]["qty"] * frac)
                    if q < 1:
                        notes["cant_split"] += 1
                    else:
                        acc.sell(spot["pid"], closes[index], d, d, qty=q, reason="+5% 나눠 팔기")
                else:
                    pend_sell.append({"pid": spot["pid"], "code": c, "kind": "part", "frac": frac, "dec": d, "why": "+5% 나눠 팔기"})
                spot["자리"] -= part
                spot["step"] = step
                continue
            if decided:
                if mode == "close":
                    acc.sell(spot["pid"], closes[index], d, d, reason="청산" if not forced else "cap 130")
                else:
                    pend_sell.append({"pid": spot["pid"], "code": c, "kind": "all", "frac": 1.0, "dec": d,
                                      "why": "청산" if not forced else "cap 130"})
                del open_[c]
            else:
                spot["step"] = step
        used = sum(s["자리"] for s in open_.values())
        room = SLOTS - used
        nav_d, _ = acc.mtm(pf)
        held_rows = [s["row"] for s in open_.values()]
        ready = sorted(PK.get(d, []), key=RANK)
        for row in ready[:max(room, 0)]:
            if used >= SLOTS:
                break
            c = row["code"]
            if c in open_ or any(o["code"] == c for o in pend_buy):
                continue
            if not KIN(row, held_rows):
                continue
            want = min(max(int(SIZE(row)), 1), SLOTS - used)
            if mode == "close":
                one, i = LN[c], row["i"]
                if i >= len(one["closes"]):
                    continue
                if lab.locked(one["closes"], one["날"], i, 1):
                    continue
                pid = f"{c}:{d}"
                if acc.buy(pid, c, one["closes"][i], d, d, value=want / SLOTS * nav_d, slots=want, tag=f"칸{want}"):
                    open_[c] = {"pid": pid, "i": i, "price": one["closes"][i], "step": 0, "peak": one["closes"][i], "row": row,
                                "자리": want, "filled": d}
                    used += want
                    held_rows.append(row)
                else:
                    notes["buy_unfilled_slot_released"] += 1
            else:
                pend_buy.append({"pid": f"{c}:{d}", "code": c, "row": row, "slots": want, "value": want / SLOTS * nav_d, "dec": d})
                used += want
                held_rows.append(row)
        max_used = max(max_used, used)
        nav, inv = acc.mtm(pf)
        acc.check(pf)
        navs.append((d, nav, inv))
        gross.append((d, nav + acc.cum_cost()))
        if snap_day == d:
            snap = snapshot(acc, {"open": {c: {k: v for k, v in s.items() if k != "row"} for c, s in open_.items()},
                                  "pend_buy": [{k: v for k, v in o.items() if k != "row"} for o in pend_buy], "pend_sell": pend_sell})
    notes["pending_buy_at_end"] = len(pend_buy)
    notes["pending_sell_at_end"] = len(pend_sell)
    return finish(acc, navs, gross, stock_pf(CLm, CLDm, DAYS[-1]), DAYS[-1],
                  {"notes": dict(notes), "max_slots_used": max_used, "snap": snap, "cal": DAYS})


def snapshot(acc, state):
    return json.loads(json.dumps({"cash": round(acc.cash, 4), "pos": {k: {"qty": p["qty"], "basis": round(p["basis"], 4)}
                                                                       for k, p in sorted(acc.pos.items())}, "state": state},
                                 default=str, sort_keys=True))


def d1_reference():
    """원 엔진 칸 원장(씨앗 0 · 한 번에 2017-02 ~ 끝) — 비교 기준만."""
    got = lab.run(nrl.inside, nrl.prices, HOLD, EXIT, slots=SLOTS, rank=RANK, since=START, apart=KIN, realistic=True, cap=CAP,
                  detail=True, size=SIZE)
    return [(t["code"], t["산 날"], t["판 날"], t["자리"], bool(t.get("나눠 팜"))) for t in got["매매목록"]]


# ───────── 빈칸 엔진 · 코스닥 인버스 ─────────
def etf_closes(code):
    b = json.loads(Path(BASE, "etf-data", f"{code}.json").read_text(encoding="utf-8"))
    return {str(d): float(c) for d, c in b["closes"] if c}


ETF = {c: etf_closes(c) for c in ER.CODES}


def week_end(d):
    i = DIDX.get(d)
    if i is None or i + 1 >= len(DAYS):
        return True
    n = DAYS[i + 1]
    a = _date(int(d[:4]), int(d[4:6]), int(d[6:])).isocalendar()[:2]
    b = _date(int(n[:4]), int(n[4:6]), int(n[6:])).isocalendar()[:2]
    return a != b


def run_etf(mode, mult, used_of, only, EM=None, snap_day=None):
    EM = EM or ETF
    EMD = {c: sorted(v) for c, v in EM.items()}
    acc = KN.Account(KN.Costs(CC, market_of, mult, "etf"))
    st, pending, navs, gross, notes, snap = {}, [], [], [], Counter(), None
    orig = ER.decide
    if only == "engine":
        ER.decide = lambda *a, **k: dict(orig(*a, **k), 코스닥인버스=False)
    try:
        for d in DAYS:
            now = {c: EM[c].get(d) for c in ER.CODES if EM[c].get(d)}
            pf = lambda code, d=d: ((EM[code][d], False) if EM[code].get(d) else
                                    (EM[code][EMD[code][max(0, bisect.bisect_right(EMD[code], d) - 1)]], True))
            if mode == "next" and pending:
                fill_orders(acc, st, pending, now, d, notes)
                pending = []
            if mode == "next":
                state_matches(acc, st, notes)
            if not all(c in now for c in ("069500", "229200", "138230")):
                nav, inv = acc.mtm(pf)
                navs.append((d, nav, inv))
                gross.append((d, nav + acc.cum_cost()))
                continue
            px = {}
            for c in ER.CODES:
                ds = EMD[c][:bisect.bisect_right(EMD[c], d)]
                if c in now and len(ds) >= 26:
                    px[c] = [EM[c][x] for x in ds]
            held = {c: acc.held(c) for c in ER.CODES if acc.held(c)}
            nav_pre, _ = acc.mtm(pf)
            breadth = 100.0 if only == "inverse" else BR.get(d, 100.0)
            prev = copy.deepcopy(st.get("positions", {}))
            orders, st, _why = ER.step(st, d, px, breadth, used_of(d), nav_pre, acc.cash, held, now, week_end(d), 0.0)
            req = [{"code": c, "side": s, "qty": q, "why": r, "dec": d, "prev": prev.get(c),
                    "kind": (st.get("positions", {}).get(c) or prev.get(c) or {}).get("kind", "")} for c, s, q, r in orders]
            if mode == "next":
                pending = req
            else:
                fill_orders(acc, st, req, now, d, notes, same_day=True)
                state_matches(acc, st, notes)
            nav, inv = acc.mtm(pf)
            acc.check(pf)
            navs.append((d, nav, inv))
            gross.append((d, nav + acc.cum_cost()))
            if snap_day == d:
                snap = snapshot(acc, {"st": st, "pending": [{k: v for k, v in o.items()} for o in pending]})
    finally:
        ER.decide = orig
    last = DAYS[-1]
    pfl = lambda code: ((EM[code][last], False) if EM[code].get(last) else (EM[code][EMD[code][-1]], True))
    notes["pending_at_end"] = len(pending)
    return finish(acc, navs, gross, pfl, last, {"notes": dict(notes), "snap": snap, "cal": DAYS})


def fill_orders(acc, st, req, now, d, notes, same_day=False, pos_key="positions", basket=False):
    """research adapter: 요청을 체결하고 상태를 장부와 맞춤(파는 것 먼저)."""
    pos = st.setdefault(pos_key, {})
    for o in [x for x in req if x["side"] == "sell"]:
        c, p = o["code"], now.get(o["code"])
        pids = acc.pids_of(c)
        if not pids:
            notes["sell_without_position"] += 1
            continue
        if not p:
            for pid in pids:
                reject(acc, pid, c, "sell", o["dec"], d, "체결 날 값 없음 → 상태 되돌려 다음 날 다시 판단")
            if o.get("prev") is not None:
                pos[c] = o["prev"]
            notes["sell_retry_state_restored"] += 1
            continue
        for pid in pids:
            acc.sell(pid, p, d, o["dec"], reason=o["why"])
    for o in [x for x in req if x["side"] == "buy"]:
        c, p = o["code"], now.get(o["code"])
        pid = f"{c}:{d}"
        got = acc.buy(pid, c, p, d, o["dec"], qty=o["qty"], tag=o.get("kind", "")) if p else 0
        if not p:
            reject(acc, pid, c, "buy", o["dec"], d, "체결 날 값 없음")
        if got:
            if c in pos and not same_day:
                notes["state_price_set_to_fill"] += 1
                pos[c]["price"] = p                 # 실제 체결가로 익절 · 손절 · 보유 기준
                pos[c]["day"] = d
                if not basket:
                    pos[c]["days"] = -1             # 같은 날 step이 하나 올려 0(체결 날부터 셈)
            if got < o["qty"]:
                notes["buy_reduced_state_kept"] += 1
        else:
            pos.pop(c, None)
            notes["buy_unfilled_state_removed"] += 1


def state_matches(acc, st, notes):
    """체결 처리 뒤 상태의 포지션 코드 = 장부에 수량이 있는 코드인가(어긋난 날 수를 셈)."""
    a = set((st or {}).get("positions", {}))
    b = {p["code"] for p in acc.pos.values() if p["qty"] > 0}
    notes["state_ledger_checks"] += 1
    if a != b:
        notes["state_ledger_mismatch_days"] += 1


# ───────── 바구니 C ─────────
BAD_TITLE = ("정정", "매매거래정지", "자회사", "종속회사", "권리락")


def load_events(clean=True):
    out, dropped = {}, 0
    for path in Path(BASE, "event-data").glob("*.json"):
        b = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for r in b.get("rows") or []:
            if not r.get("date") or r.get("kind") not in basket_live.KINDS:
                continue
            if clean and any(w in (r.get("title") or "") for w in BAD_TITLE):
                dropped += 1
                continue
            rows.append((str(r["date"]), r["kind"]))
        out[path.stem] = rows
    return out, dropped


EVENTS, DROPPED = load_events(True)


def run_basket(mode, mult, CLm=None, EV=None, snap_day=None):
    CLm, EV = CLm or CL, EV if EV is not None else EVENTS
    CLDm = {c: sorted(v) for c, v in CLm.items()} if CLm is not CL else CLD
    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"))
    st, pending, navs, gross, notes, snap = {}, [], [], [], Counter(), None
    for i, d in enumerate(DAYS):
        pf = stock_pf(CLm, CLDm, d)
        now = {c: CLm[c][d] for c in CLm if d in CLm[c]}
        if mode == "next" and pending:
            fill_orders(acc, st, pending, now, d, notes, basket=True)
            pending = []
        if mode == "next":
            state_matches(acc, st, notes)
        if i < 2:
            nav, inv = acc.mtm(pf)
            navs.append((d, nav, inv))
            gross.append((d, nav + acc.cum_cost()))
            continue
        t0, prev = DAYS[i - 1], DAYS[i - 2]
        mini = {c: {"rows": [(prev, CLm[c][prev]), (t0, CLm[c][t0])] if prev in CLm[c] else [(t0, CLm[c][t0])]}
                for c in CLm if t0 in CLm[c]}
        react, inside = basket_live.reactions(mini, t0, prev)
        ev = basket_live.todays_events(EV, t0, prev)
        held = {c: acc.held(c) for c in {p["code"] for p in acc.pos.values()}}
        nav_pre, _ = acc.mtm(pf)
        ds = lambda x, d=d: DIDX[d] - DIDX.get(x, DIDX[d])
        prevpos = copy.deepcopy(st.get("positions", {}))
        orders, st, _why = basket_live.step(st, d, t0, ds, ev, react, inside, held, now, nav_pre, acc.cash)
        req = [{"code": c, "side": s, "qty": q, "why": r, "dec": d, "prev": prevpos.get(c), "kind": "basket"} for c, s, q, r in orders]
        if mode == "next":
            pending = req
        else:
            fill_orders(acc, st, req, now, d, notes, same_day=True, basket=True)
            state_matches(acc, st, notes)
        nav, inv = acc.mtm(pf)
        acc.check(pf)
        navs.append((d, nav, inv))
        gross.append((d, nav + acc.cum_cost()))
        if snap_day == d:
            snap = snapshot(acc, {"st": st, "pending": pending})
    notes["pending_at_end"] = len(pending)
    notes["events_dropped_by_title"] = DROPPED
    return finish(acc, navs, gross, stock_pf(CLm, CLDm, DAYS[-1]), DAYS[-1], {"notes": dict(notes), "snap": snap, "cal": DAYS})


# ───────── 자르기(미래 바꾸기) 회귀 ─────────
def bump_after(series, x, k=1.37):
    return {d: (v * k if d > x else v) for d, v in series.items()}


def prefix(res, x):
    f = [json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, sort_keys=True, default=str)
         for r in res["fills"] if str(r["fill_at"])[:8] <= x]
    n = [(d, round(v, 4), round(i, 4)) for d, v, i in res["nav"] if d <= x]
    return f, n


def same_prefix(a, b, x):
    fa, na = prefix(a, x)
    fb, nb = prefix(b, x)
    return {"fills_equal": fa == fb, "n_fills": len(fa), "nav_equal": na == nb, "n_days": len(na),
            "snap_equal": a["snap"] is not None and a["snap"] == b["snap"]}


def save(name, res):
    with open(OUT / f"{name}.pkl", "wb") as f:
        pickle.dump(res, f)
    print(name, "NAV", round(res["nav"][-1][1]), "열린", len(res["open"]), "닫힌", len(res["closed"]), res.get("notes"),
          round(time.time() - T0), "초", flush=True)


RUNS, CUTS = {}, {}
# 1일봉
for mode, mults in (("next", (1.0, 2.0, 0.0)), ("close", (1.0,))):
    for m in mults:
        RUNS[f"D1_{mode}_x{m:g}"] = r = run_d1(mode, m, snap_day=X_CUT if (mode, m) == ("next", 1.0) else None)
        save(f"D1_{mode}_x{m:g}", r)
REF = d1_reference()
print("원 엔진 칸 원장", len(REF), "줄", round(time.time() - T0), "초", flush=True)
LN2 = {c: dict(v, closes=[(x * 1.37 if dd > X_CUT else x) for dd, x in zip(v["날"], v["closes"])]) for c, v in LANE.items()}
CL2 = {c: bump_after(v, X_CUT) for c, v in CL.items()}
PK2 = {d: v for d, v in PICKS.items() if d <= X_CUT}
cut = run_d1("next", 1.0, LN=LN2, CLm=CL2, PK=PK2, snap_day=X_CUT)
CUTS["D1_next"] = same_prefix(RUNS["D1_next_x1"], cut, X_CUT)
print("자르기 1일봉", CUTS["D1_next"], flush=True)


def used_series(run):
    """ETF used = 0.5 × 1일봉 투자 비율(전 거래일 종가)."""
    r = {d: (inv / nav if nav > 0 else 0.0) for d, nav, inv in run["nav"]}
    return lambda d: 0.5 * r.get(DAYS[DIDX[d] - 1], 0.0) if DIDX.get(d, 0) > 0 else 0.0


for only in ("engine", "inverse"):
    for mode, mults in (("next", (1.0, 2.0, 0.0)), ("close", (1.0,))):
        for m in mults:
            src = RUNS.get(f"D1_{mode}_x{m:g}") or RUNS[f"D1_{mode}_x1"]
            RUNS[f"ETF_{only}_{mode}_x{m:g}"] = r = run_etf(mode, m, used_series(src), only,
                                                             snap_day=X_CUT if (mode, m) == ("next", 1.0) else None)
            save(f"ETF_{only}_{mode}_x{m:g}", r)
    EM2 = {c: bump_after(v, X_CUT) for c, v in ETF.items()}
    cut = run_etf("next", 1.0, used_series(RUNS["D1_next_x1"]), only, EM=EM2, snap_day=X_CUT)
    CUTS[f"ETF_{only}_next"] = same_prefix(RUNS[f"ETF_{only}_next_x1"], cut, X_CUT)
    print("자르기", only, CUTS[f"ETF_{only}_next"], flush=True)
for mode, mults in (("next", (1.0, 2.0, 0.0)), ("close", (1.0,))):
    for m in mults:
        RUNS[f"BASKET_{mode}_x{m:g}"] = r = run_basket(mode, m, snap_day=X_CUT if (mode, m) == ("next", 1.0) else None)
        save(f"BASKET_{mode}_x{m:g}", r)
EV2 = {c: [(d, k) for d, k in v if d <= X_CUT] for c, v in EVENTS.items()}
cut = run_basket("next", 1.0, CLm=CL2, EV=EV2, snap_day=X_CUT)
CUTS["BASKET_next"] = same_prefix(RUNS["BASKET_next_x1"], cut, X_CUT)
print("자르기 바구니", CUTS["BASKET_next"], flush=True)
with open(OUT / "daily_meta.pkl", "wb") as f:
    pickle.dump({"meta": META, "d1_reference": REF, "cuts": CUTS, "x_cut": X_CUT, "seconds": round(time.time() - T0)}, f)
print("끝", round(time.time() - T0), "초", flush=True)
