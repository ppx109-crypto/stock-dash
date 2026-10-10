"""BACKTEST-REPAIR-0001 재계산 구동기 — 1일봉 · 15분봉 · 빈칸 엔진 + 코스닥 인버스 · 바구니 C를 새 장부(kernel)로.
python3 run_all.py <기준점 폴더(00b98ab1)> <nrl 캐시> <d1 원장 폴더> <RULES-0002 m15 원장 폴더> <출력 폴더>
네트워크 막음 · 키 환경변수 지움 · 운영 파일 안 고침."""
import bisect
import csv
import json
import os
import pickle
import socket
import sys
import time
from pathlib import Path

BASE, CACHE, D1DIR, M15DIR, OUT = (str(Path(sys.argv[1]).resolve()), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]))
OUT.mkdir(parents=True, exist_ok=True)


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
os.environ.pop("CAPS_ADJ", None)
os.environ["COST_REPLAY_ROOT"] = BASE
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import cost_contract as CC  # noqa: E402
import kernel as KN  # noqa: E402
import rules as ER  # noqa: E402
os.chdir(BASE)
sys.path.insert(1, BASE)
import basket_live  # noqa: E402  (기준점 폴더의 순수 함수 step · reactions)

T0 = time.time()
g = pickle.load(open(CACHE, "rb"))
PRICES, BR = g[0], g[3]
DAYS = [d for d in sorted(BR) if d >= "20170201"]
if os.environ.get("BR_LIMIT"):                      # 빠른 점검용(결과에는 안 씀)
    DAYS = DAYS[:int(os.environ["BR_LIMIT"])]
IDX = {d: i for i, d in enumerate(DAYS)}
KQ = {p.stem for p in Path(BASE, "kosdaq-data").glob("*.json")}
market_of = lambda c: "KOSDAQ" if c in KQ else "KOSPI"
CL = {c: dict(v["rows"]) for c, v in PRICES.items()}
CLD = {c: sorted(v) for c, v in CL.items()}
RESULTS = {"meta": {"base": BASE, "cache": CACHE, "days": [DAYS[0], DAYS[-1]], "n_days": len(DAYS)}, "runs": {}}


def stock_px(day):
    def f(code):
        v = CL.get(code, {}).get(day)
        if v:
            return v, False
        ds = CLD.get(code, [])
        k = bisect.bisect_right(ds, day) - 1
        return (CL[code][ds[k]] if k >= 0 else 0.0), True
    return f


def nxt(day):
    i = IDX.get(day)
    return DAYS[i + 1] if i is not None and i + 1 < len(DAYS) else None


def save_evidence(tag, nav_rows, trades):
    with open(OUT / f"nav_{tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "nav", "invested"])
        w.writerows([(d, round(n, 2), round(i, 2)) for d, n, i in nav_rows])
    keys = ["code", "tag", "entry", "exit", "qty", "buy_price", "sell_price", "buy_cost", "sell_cost", "pnl_gross", "pnl_net", "ret_net", "reason"]
    with open(OUT / f"trades_{tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for t in trades:
            w.writerow({k: (round(t[k], 6) if isinstance(t[k], float) else t[k]) for k in keys})


# ───────── 1일봉 ─────────
def run_d1(ledger_name, mode, mult):
    rows = list(csv.DictReader(open(D1DIR / f"d1_ledger_{ledger_name}.csv", encoding="utf-8")))
    costs = KN.Costs(CC, market_of, mult, "stock")
    acc = KN.Account(1e8)
    sched_buy, sched_sell = {}, {}
    for i, r in enumerate(rows):
        e, x = r["entry"], r["exit"]
        if mode == "next":
            e, x = nxt(e), (nxt(x) or DAYS[-1])
        if e is None or e not in IDX:
            continue
        x = x if x in IDX else DAYS[-1]
        sched_buy.setdefault(e, []).append((i, r))
        sched_sell.setdefault(x, []).append(i)
    navs = []
    for d in DAYS:
        pf = stock_px(d)
        for i in sched_sell.get(d, []):
            if i in acc.lots:
                p, stale = pf(acc.lots[i]["code"])
                acc.notes["sell_no_price_used_last"] += stale
                acc.sell(i, p, d, costs, reason="원장 청산")
        if d in sched_buy:
            nav_pre, _ = acc.mtm(pf)
            for i, r in sched_buy[d]:
                p = CL.get(r["code"], {}).get(d)
                acc.buy(i, r["code"], p, nav_pre * int(r["slots"]) / 10, d, costs, tag=f"slots{r['slots']}")
        nav, inv = acc.mtm(pf)
        navs.append((d, nav, inv))
    for i in list(acc.lots):                                  # 끝에 남은 것은 마지막 종가로 셈(기록)
        p, _ = stock_px(DAYS[-1])(acc.lots[i]["code"])
        acc.sell(i, p, DAYS[-1], costs, reason="자료 끝 정리")
    return navs, acc


# ───────── 15분봉 ─────────
def m15_bars(codes):
    out = {}
    for c in codes:
        rows = []
        for f in sorted(Path(BASE, "m15-kis", c).glob("*.csv")):
            for line in f.read_text(encoding="utf-8").splitlines():
                p = line.split(",")
                if len(p) >= 5 and p[0][:1].isdigit():
                    rows.append((p[0], float(p[1]), float(p[4])))
        out[c] = rows
    return out


def run_m15(variant, mult):
    led = json.load(open(M15DIR / f"m15_{variant}.json", encoding="utf-8"))["ledger"]
    codes = sorted({r[0] for r in led})
    bars = m15_bars(codes)
    opens = {c: {t: o for t, o, _ in v} for c, v in bars.items()}
    dclose = {}
    for c, v in bars.items():
        for t, o, cl in v:
            dclose.setdefault(c, {})[t[:8]] = cl
    dds = {c: sorted(v) for c, v in dclose.items()}
    days = sorted({t[:8] for v in bars.values() for t, _, _ in v if "20250917" <= t[:8] <= "20260831"})
    didx = {d: i for i, d in enumerate(days)}
    costs = KN.Costs(CC, market_of, mult, "stock")
    acc = KN.Account(1e8)
    ev = []
    for i, (c, e, x, pnl, slots) in enumerate(led):
        ev.append((e, 1, i, c, slots))
        ev.append((x, 0, i, c, slots))
    ev.sort()
    navs, last_nav, k, missing = [], 1e8, 0, 0

    def pf_day(d):
        def f(code):
            v = dclose.get(code, {}).get(d)
            if v:
                return v, False
            ds = dds.get(code, [])
            j = bisect.bisect_right(ds, d) - 1
            return (dclose[code][ds[j]] if j >= 0 else 0.0), True
        return f

    for d in days:
        while k < len(ev) and ev[k][0][:8] <= d:
            ts, is_buy, i, c, slots = ev[k]
            k += 1
            p = opens.get(c, {}).get(ts)
            if p is None:
                missing += 1
                continue
            if is_buy:
                acc.buy(i, c, p, last_nav * slots / 10, ts[:8], costs, tag=f"slots{slots}")
            elif i in acc.lots:
                acc.sell(i, p, ts[:8], costs, reason="원장 청산(바 시가)")
        nav, inv = acc.mtm(pf_day(d))
        navs.append((d, nav, inv))
        last_nav = nav
    acc.notes["fill_bar_missing"] = missing
    return navs, acc, didx


# ───────── 빈칸 엔진 + 코스닥 인버스 ─────────
def etf_closes(code):
    b = json.loads(Path(BASE, "etf-data", f"{code}.json").read_text(encoding="utf-8"))
    return {str(d): float(c) for d, c in b["closes"] if c}


ETF = {c: etf_closes(c) for c in ER.CODES}
ETFD = {c: sorted(v) for c, v in ETF.items()}


def week_end(d):
    from datetime import date as _d
    n = nxt(d)
    if n is None:
        return True
    a = _d(int(d[:4]), int(d[4:6]), int(d[6:])).isocalendar()[:2]
    b = _d(int(n[:4]), int(n[4:6]), int(n[6:])).isocalendar()[:2]
    return a != b


def run_etf(used_of, mode, mult, only=None):
    costs = KN.Costs(CC, market_of, mult, "etf")
    acc = KN.Account(1e8)
    st, pending, navs = {}, [], []
    orig_decide = ER.decide
    if only == "engine":
        ER.decide = lambda *a, **k: dict(orig_decide(*a, **k), 코스닥인버스=False)
    try:
        for d in DAYS:
            now = {c: ETF[c].get(d) for c in ER.CODES if ETF[c].get(d)}
            pf = lambda code: ((ETF[code].get(d), False) if ETF[code].get(d) else
                               (ETF[code][ETFD[code][max(0, bisect.bisect_right(ETFD[code], d) - 1)]], True))
            if mode == "next" and pending:                       # 어제 판단 → 오늘 종가 체결
                for c, side, q, why, kind in pending:
                    p = now.get(c)
                    if not p:
                        continue
                    if side == "sell":
                        for lid in [l for l, v in acc.lots.items() if v["code"] == c]:
                            acc.sell(lid, p, d, costs, reason=why)
                    else:
                        got = acc.buy(f"{c}:{d}", c, p, q * p, d, costs, tag=kind)
                        if got and c in st.get("positions", {}):
                            st["positions"][c]["price"] = p          # 실제 체결가로 익절 · 손절 기준을 맞춤
                pending = []
            if "069500" not in now or "229200" not in now or "138230" not in now:
                navs.append((d, *acc.mtm(pf)))
                continue
            px = {}
            for c in ER.CODES:
                ds = ETFD[c][:bisect.bisect_right(ETFD[c], d)]
                if c in now and len(ds) >= 26:
                    px[c] = [ETF[c][x] for x in ds]
            held = {c: acc.held(c) for c in ER.CODES if acc.held(c)}
            nav_pre, _ = acc.mtm(pf)
            breadth = 100.0 if only == "inverse" else BR.get(d, 100.0)
            orders, st, why = ER.step(st, d, px, breadth, used_of(d), nav_pre, acc.cash, held, now, week_end(d), 0.0)
            tagged = [(c, s, q, r, (st.get("positions", {}).get(c) or {}).get("kind", "")) for c, s, q, r in orders]
            if mode == "next":
                pending = tagged
            else:
                for c, side, q, r, kind in tagged:
                    if side == "sell":
                        for lid in [l for l, v in acc.lots.items() if v["code"] == c]:
                            acc.sell(lid, now[c], d, costs, reason=r)
                    else:
                        acc.buy(f"{c}:{d}", c, now[c], q * now[c], d, costs, tag=kind)
            navs.append((d, *acc.mtm(pf)))
    finally:
        ER.decide = orig_decide
    for lid in list(acc.lots):
        acc.sell(lid, ETF[acc.lots[lid]["code"]][ETFD[acc.lots[lid]["code"]][-1]], DAYS[-1], costs, reason="자료 끝 정리")
    return navs, acc


def kind_of_trade(t):
    return "인버스" if t["code"] == ER.INV else "엔진"


# ───────── 바구니 C ─────────
BAD_TITLE = ("정정", "매매거래정지", "자회사", "종속회사", "권리락")


def load_events(clean):
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


def run_basket(clean, mode, mult):
    events, dropped = load_events(clean)
    costs = KN.Costs(CC, market_of, mult, "stock")
    acc = KN.Account(1e8)
    st, pending, navs = {}, [], []
    for i, d in enumerate(DAYS):
        pf = stock_px(d)
        now = {c: CL[c][d] for c in CL if d in CL[c]}
        if mode == "next" and pending:
            for c, side, q, r in pending:
                p = now.get(c)
                if not p:
                    continue
                if side == "sell":
                    for lid in [l for l, v in acc.lots.items() if v["code"] == c]:
                        acc.sell(lid, p, d, costs, reason=r)
                else:
                    acc.buy(f"{c}:{d}", c, p, q * p, d, costs, tag="basket")
            pending = []
        if i < 2:
            navs.append((d, *acc.mtm(pf)))
            continue
        t0, prev = DAYS[i - 1], DAYS[i - 2]
        mini = {c: {"rows": [(prev, CL[c][prev]), (t0, CL[c][t0])] if prev in CL[c] else [(t0, CL[c][t0])]}
                for c in CL if t0 in CL[c]}
        react, inside = basket_live.reactions(mini, t0, prev)
        ev = basket_live.todays_events(events, t0, prev)
        held = {c: acc.held(c) for c in {v["code"] for v in acc.lots.values()}}
        nav_pre, _ = acc.mtm(pf)
        ds = lambda x: IDX[d] - IDX.get(x, IDX[d])
        orders, st, why = basket_live.step(st, d, t0, ds, ev, react, inside, held, now, nav_pre, acc.cash)
        if mode == "next":
            pending = orders
        else:
            for c, side, q, r in orders:
                if side == "sell":
                    for lid in [l for l, v in acc.lots.items() if v["code"] == c]:
                        acc.sell(lid, now[c], d, costs, reason=r)
                else:
                    acc.buy(f"{c}:{d}", c, now[c], q * now[c], d, costs, tag="basket")
        navs.append((d, *acc.mtm(pf)))
    for lid in list(acc.lots):
        p, _ = stock_px(DAYS[-1])(acc.lots[lid]["code"])
        acc.sell(lid, p, DAYS[-1], costs, reason="자료 끝 정리")
    acc.notes["events_dropped_by_title"] = dropped
    return navs, acc


def record(name, navs, acc, gross_navs, idx=None, evidence=False, extra=None):
    rep = KN.report(navs, acc.trades, idx or IDX, gross_navs)
    RESULTS["runs"][name] = {"report": rep, "notes": acc.notes, **(extra or {})}
    if evidence:
        save_evidence(name, navs, acc.trades)
    print(name, {k: (v or {}).get("CAGR") for k, v in rep.items()}, round(time.time() - T0), "초", flush=True)


# 1일봉: 원장 4판 × 실행 2 × 비용(1 · 2) + 비용 전(0)
D1_USED = {}
for led in ("ASIS", "K1", "K2", "FIX"):
    for mode in ("close", "next"):
        gross, _ = run_d1(led, mode, 0.0)
        for mult in (1.0, 2.0):
            navs, acc = run_d1(led, mode, mult)
            name = f"D1_{led}_{mode}_x{int(mult)}"
            record(name, navs, acc, gross, evidence=(mult == 1.0 and led in ("ASIS", "FIX")), extra={"cost_tax_unknown": 0})
            if mult == 1.0:
                D1_USED[(led, mode)] = {d: (0.5 * inv / nav if nav > 0 else 1.0) for d, nav, inv in navs}

# 15분봉: ASIS · FLOW-LAG2(K1) × 비용(1 · 2) + 비용 전
for var in ("ASIS", "FLOW-LAG2"):
    g0, _, didx = run_m15(var, 0.0)
    for mult in (1.0, 2.0):
        navs, acc, didx = run_m15(var, mult)
        record(f"M15_{var}_x{int(mult)}", navs, acc, g0, idx=didx, evidence=(mult == 1.0))

# 엔진 + 인버스: ASIS = 종가 근사 · used는 1일봉 ASIS 종가판 / FIX = 보수적 다음 날 종가 · used는 1일봉 FIX 보수판
for tag, (led, mode) in (("ASIS_close", ("ASIS", "close")), ("FIX_next", ("FIX", "next")), ("FIX_close", ("FIX", "close"))):
    used = D1_USED[(led, mode)]
    uf = lambda d, u=used: u.get(d, 1.0)
    for only in (None, "inverse", "engine"):
        gross, _ = run_etf(uf, mode, 0.0, only)
        for mult in (1.0, 2.0):
            navs, acc = run_etf(uf, mode, mult, only)
            name = f"ETF_{only or 'sleeve'}_{tag}_x{int(mult)}"
            ext = {"by_kind": {k: {"trades": sum(1 for t in acc.trades if kind_of_trade(t) == k),
                                   "pnl_net": round(sum(t["pnl_net"] for t in acc.trades if kind_of_trade(t) == k), 0)} for k in ("엔진", "인버스")}}
            record(name, navs, acc, gross, evidence=(mult == 1.0 and only is None and tag != "FIX_close"), extra=ext)

# 바구니 C: ASIS(제목 그대로 · 종가 근사 = 연구 P4b) / FIX(제목 정제 · 보수적 다음 날 종가) / 제목만 · 실행만
for tag, clean, mode in (("ASIS_close", False, "close"), ("K3_close", True, "close"), ("ASIS_next", False, "next"), ("FIX_next", True, "next")):
    gross, _ = run_basket(clean, mode, 0.0)
    for mult in (1.0, 2.0):
        navs, acc = run_basket(clean, mode, mult)
        record(f"BASKET_{tag}_x{int(mult)}", navs, acc, gross, evidence=(mult == 1.0 and tag in ("ASIS_close", "FIX_next")))

RESULTS["meta"]["seconds"] = round(time.time() - T0)
(OUT / "results.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("끝", RESULTS["meta"]["seconds"], "초")
