"""BACKTEST-REPAIR-0002 · 15분봉 22회차(FLOW-LAG2) 순차 재실행 — 신호 → 요청 → 다음 봉 시가 체결 → 확정 상태, 돈 장부(kernel2).
python3 m15_exec.py <b3 폴더> <출력 폴더> [HLAB_CUT 10자리]
- 신호 · 순위 · 칸 · 청산 · 묵음 판정은 RULES-0002 intraday_diag.py와 같은 바꿔 끼우기(q023 entry3(al_mkt=−0.01) · 수급 끝 1줄 앞)로 만든 원 함수 그대로.
- 계좌 모의만 새로: 원 hlab._one_run의 ① 팔기 ② 사기(묵음 비키기) ③ 봉 갱신 ④ 판단 순서를 그대로 따르되, 칸 비율 대신 정수 주 · 현금 장부.
- 기존 원장(m15_*.json)은 읽지 않음. 비교 기준은 같은 함수의 원 칸 모의(한 기간)를 이 프로세스에서 다시 돌려 얻음.
- 두 반으로 나누지 않고 2025-09-17 ~ 2026-08-31 한 번. 끝에 열린 포지션은 마지막 종가로 평가(청산 시나리오는 따로)."""
import bisect
import math
import os
import pickle
import socket
import sys
import time
from pathlib import Path

BASE, OUT = str(Path(sys.argv[1]).resolve()), Path(sys.argv[2])
CUT = sys.argv[3] if len(sys.argv) > 3 else None
OUT.mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).resolve().parent


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")) or k in ("Q_BARS", "Q_SCALE", "Q_SPAN", "HLAB_ST_CACHE", "CAPS_ADJ",
                                                                   "HLAB_CUT", "HLAB_POISON", "M15_OPEN_OOS", "HLAB_OPEN_HOLDOUT"):
        os.environ.pop(k)
if CUT:
    os.environ["HLAB_CUT"] = CUT
os.environ["COST_REPLAY_ROOT"] = BASE
sys.path.insert(0, str(HERE))
import cost_contract as CC  # noqa: E402
import kernel2 as KN  # noqa: E402
os.chdir(BASE)
sys.path[:0] = [BASE, BASE + "/research"]
t0 = time.time()
import numpy as np  # noqa: E402
import hlab  # noqa: E402

SHIFT = 1
src = Path(hlab.__file__).read_text(encoding="utf-8")
a, b = src.index("def daily_context("), src.index("\ndef _events(")
OLD = "k = bisect.bisect_right(fdays, day)"
assert src[a:b].count(OLD) == 1
exec(compile(src[a:b].replace(OLD, OLD + " - _FLOW_SHIFT"), "hlab.daily_context(수급 끝 당김)", "exec"), hlab.__dict__)
hlab._FLOW_SHIFT = SHIFT
G = {"__name__": "br0002"}
code = Path(BASE, "research/q023.py").read_text(encoding="utf-8").replace("/home/user/stock-dash", BASE).split("\npart = os.environ")[0]
exec(compile(code, "q023(앞부분)", "exec"), G)
RAW_OLD = "f = bisect.bisect_left(fd, day) - 1"
qsrc = Path(BASE, "research/q_rule.py").read_text(encoding="utf-8")
a, b = qsrc.index("def raw("), qsrc.index("\ndef tiers(")
assert qsrc[a:b].count(RAW_OLD) == 1
exec(compile(qsrc[a:b].replace(RAW_OLD, RAW_OLD + " - _FLOW_SHIFT"), "q_rule.raw(수급 끝 당김)", "exec"), G)
G["_FLOW_SHIFT"] = SHIFT
sig_fn = G["entry3"](al_mkt=-0.01)
data = G["data"]
SG = {c: np.asarray(sig_fn(c, bb), bool) for c, bb in data.items() if not c.startswith("K")}
RANK = G["rank_plus"](G["tiers"](SG))
EXIT, STALE, SIZE, M = G["exit_rule"], G["stale90"], G["size"], G["M"]
LO, HI = M.EARLY[0], M.LATE[1]
SLOTS = 10
KQ = {p.stem for p in Path(BASE, "kosdaq-data").glob("*.json")}
market_of = lambda c: "KOSDAQ" if c in KQ else "KOSPI"
print("자료 준비", round(time.time() - t0), "초 ·", len(SG), "종목", flush=True)


def run(mult):
    costs = KN.Costs(CC, market_of, mult, "stock")
    acc = KN.Account(costs)
    rng = np.random.default_rng(0)
    idx, times = {}, set()
    for c in SG:
        t = data[c]["t"]
        k0, k1 = bisect.bisect_left(t, LO), bisect.bisect_left(t, HI)
        idx[c] = (k0, k1)
        times.update(t[k0:k1])
    times = sorted(times)
    at = {}
    for c, (k0, k1) in idx.items():
        for k in range(k0, k1):
            at.setdefault(data[c]["t"][k], []).append((c, k))
    pos, want_buy, want_sell, last_close = {}, {}, {}, {}
    navs, gross, last_day, slot_log = [], [], None, []
    notes = {"cant_split": 0, "stale_bumped": 0, "buy_signal_no_slot": 0}
    pf = lambda code: (last_close.get(code, 0.0), False)

    def nav_now():
        return acc.mtm(pf)[0]

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
                slot_log.append((T, c, "sell", part))
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
                        slot_log.append((T, qc, "bump", q["칸"]))
                        del pos[qc]
                        want_sell.pop(qc, None)
            if free <= 0:
                notes["buy_signal_no_slot"] += 1
                continue
            take = min(need, free)
            o = data[c]["o"][k]
            pid = f"{c}:{T}"
            got = acc.buy(pid, c, o, T, dec, value=take / SLOTS * nav_now(), slots=take, tag=f"칸{take}")
            if got:
                pos[c] = {"pid": pid, "i": k, "price": o, "칸": take, "처음칸": take, "peak": o, "now": k, "day": T[:8], "code": c}
                slot_log.append((T, c, "buy", take))
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
                if isinstance(n, tuple):
                    raise AssertionError("더 사기는 이 규칙에 없음")
                if n:
                    want_sell[c] = (n, T)
            elif SG[c][k] and k + 1 < len(bb["t"]):
                want_buy[c] = (SIZE(c, bb, k), T)
            last_close[c] = bb["c"][k]
        last_day = T[:8]
    nav, inv = acc.mtm(pf)
    acc.check(pf)
    navs.append((last_day, nav, inv))
    gross.append((last_day, nav + acc.cum_cost()))
    liq, liq_cost = acc.liquidation_nav(pf, last_day)
    pend = {"buy": len(want_buy), "sell": len(want_sell)}
    return {"nav": navs, "gross": gross, "closed": acc.closed, "open": acc.open_rows(pf), "fills": acc.fills,
            "counts": dict(acc.counts), "tot": dict(acc.tot), "notes": notes, "liquidation": {"nav": liq, "cost": liq_cost},
            "pending_at_end": pend, "slot_log": slot_log, "cal": [x[0] for x in navs]}


def reference():
    """같은 원 함수로 원 칸 모의(hlab._one_run)를 한 기간으로 — 비교 기준만."""
    res = M.simulate(data, lambda c, bb: SG[c], EXIT, SIZE, rank=RANK, stale_of=STALE, seeds=1, periods=(("전체", (LO, HI)),))
    return [(t["code"], t["산 때"], t["판 때"], t["칸"]) for t in res["전체"]["목록"]]


out = {"cut": CUT, "lo": LO, "hi": HI, "codes": len(SG), "runs": {}}
for mult in ((1.0,) if CUT else (1.0, 2.0, 0.0)):
    out["runs"][mult] = run(mult)
    r = out["runs"][mult]
    print("x", mult, "NAV", round(r["nav"][-1][1]), "열린", len(r["open"]), "닫힌", len(r["closed"]), round(time.time() - t0), "초", flush=True)
if not CUT:
    out["reference"] = reference()
    print("원 칸 모의", len(out["reference"]), "줄", round(time.time() - t0), "초", flush=True)
out["seconds"] = round(time.time() - t0)
with open(OUT / f"m15{'_cut' if CUT else ''}.pkl", "wb") as f:
    pickle.dump(out, f)
print("끝", out["seconds"], "초", flush=True)
