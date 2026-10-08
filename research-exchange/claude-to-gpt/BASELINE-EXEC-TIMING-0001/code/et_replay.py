"""BASELINE-EXEC-TIMING-0001 · 일봉 복제 주문 시점 고정(t 종가 뒤 확정 → t+1 종가 체결) · 합성 검사 · Train 1회 재생.
python3 -E -P et_replay.py <b2> <옛 nrl-cache.pkl> <출력> <저장 입력 폴더(PR68 evidence)> <PR68 m15_natural.pkl> [--synthetic-only]

- 통제 · 옛 후보 · 15분봉은 다시 돌리지 않음: PR #68 저장 체결(control_trades · candidate_trades) · NAV(nav_control_candidate.csv)만 읽음.
- 고친 후보(일봉 소계정 D1 · ETF · BASKET만):
  t 종가 뒤 = 통제 체결이 끝난 뒤 이미 확정된 값(통제 보유 수량_t · 통제 소계정 NAV_t · 후보 소계정 NAV_t · E_{t+1})만으로
  목표_{t+1}(c) = floor(E_{t+1} × 후보NAV_t ÷ 통제NAV_t × 통제수량_t(c))를 잠그고, t+1 종가에 그 수량으로 체결(파는 것 먼저).
  t+1 종가로 목표를 다시 맞추지 않음. 현금이 모자라면 장부가 수량을 줄임(건수 공개) · 값 없음/상하한가면 그날 체결 안 함(다음 날 새 목표).
  첫날(2025-09-18)은 직전 거래일 통제 상태가 창 앞이라 없음 → 현금 유지(사전등록 고정).
- E_t는 PR #68 저장값(통제 P4의 t−1 마감까지로 셈). E_{t+1}은 t 마감까지 값이라 t 종가 뒤에 알 수 있음.
- 15분봉 후보는 PR #68 저장 경로(cand_M15)를 그대로 더함.
네트워크 막음 · 키 환경변수 지움 · 운영 파일 안 고침."""
import bisect
import csv
import json
import math
import pickle
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYN_ONLY = "--synthetic-only" in sys.argv
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "et_base", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41 그대로 · 자료 읽기만)", "exec"), G)
KN, CC, lab = G["KN"], G["CC"], G["lab"]
OUT, IN, M15PKL = Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
SLEEVE, TOTAL = 2_500_000.0, 10_000_000.0
LO, HI = "20250918", "20260331"
SL = ("D1", "M15", "ETF", "BASKET")
DAILY = ("D1", "ETF", "BASKET")


# ═════════ 고친 계약(일봉 소계정 하나) ═════════
def replay_lag(win, E, navN, qend, price, costs, lock=None, cash=SLEEVE):
    """win: 날 목록 · E[d] · navN[d](통제 소계정 NAV) · qend[d](통제 d 마감 보유) · price(c, d) · lock(c, d, side)."""
    acc = KN.Account(costs, cash)
    pending, navC, invC, cashC, trades, decisions, notes, seq = None, [], [], [], [], [], Counter(), 0
    held = lambda c: sum(p["qty"] for p in acc.pos.values() if p["code"] == c)
    lastp = {}
    for i, d in enumerate(win):
        if pending is not None:                                   # ① 어제 종가 뒤 잠근 목표를 오늘 종가에 체결
            tgt, dec = pending
            assert dec == win[i - 1]
            for side in ("sell", "buy"):
                for c in sorted(tgt):
                    h, t = held(c), tgt[c]
                    if not ((side == "sell" and t < h) or (side == "buy" and t > h)):
                        continue
                    px = price(c, d)
                    if not px:
                        notes["no_price"] += 1
                        continue
                    if lock and lock(c, d, -1 if side == "sell" else 1):
                        notes["locked"] += 1
                        continue
                    if side == "sell":
                        left, sold = h - t, 0
                        for pid in sorted(acc.pids_of(c)):              # 한 주문을 여러 매수 묶음(pid)에서 나눠 뺌 → 기록은 주문 하나
                            if left <= 0:
                                break
                            q = min(left, acc.pos[pid]["qty"])
                            acc.sell(pid, px, d, dec, qty=q, reason="노출 맞춤(t+1)")
                            sold += q
                            left -= q
                        trades.append((d, c, "sell", sold))
                    else:
                        seq += 1
                        got = acc.buy(f"{c}:{d}:{seq}", c, px, d, dec, qty=t - h, tag="노출 맞춤(t+1)")
                        if got < t - h:
                            notes["buy_reduced_or_unfilled"] += 1
                        if got:
                            trades.append((d, c, "buy", got))
        for c in {p["code"] for p in acc.pos.values()}:
            if price(c, d):
                lastp[c] = price(c, d)
        pf = lambda c, d=d: ((price(c, d), False) if price(c, d) else (lastp.get(c, 0.0), True))
        nav, inv = acc.mtm(pf)
        acc.check(pf)
        navC.append(nav)
        invC.append(inv)
        cashC.append(acc.cash)
        if i + 1 < len(win):                                      # ② 오늘 종가 뒤: 이미 확정된 값만으로 내일 목표 잠금
            k = nav / navN[d]
            en = E[win[i + 1]]
            q = qend.get(d, {})
            codes = {c for c, v in q.items() if v > 0} | {p["code"] for p in acc.pos.values()}
            tgt = {c: math.floor(en * k * q.get(c, 0)) for c in codes}
            decisions.append({"decided_at": d, "for": win[i + 1], "E_next": en, "k": k, "targets": dict(tgt)})
            pending = (tgt, d)
    dup = [x for x, n in Counter((t[0], t[1], t[2]) for t in trades).items() if n > 1]
    return {"acc": acc, "nav": navC, "inv": invC, "cash": cashC, "trades": trades, "decisions": decisions, "notes": dict(notes), "dup": dup}


def qend_of(trades, win, key=lambda t: t[:8]):
    """통제 체결 → 날 마감 보유 수량(그날 체결 뒤)."""
    by = {}
    for t, c, s, n, _p in trades:
        by.setdefault(key(t), []).append((c, n if s == "buy" else -n))
    q, out = {}, {}
    for d in win:
        for c, n in by.get(d, []):
            q[c] = q.get(c, 0) + n
            assert q[c] >= 0
        out[d] = dict(q)
    return out


# ═════════ 합성 검사 ═════════
class Flat:
    def rate(self, side, code, day, notional):
        return 0.001, {}


def synthetic():
    win = [f"2025010{i}" for i in range(1, 8)]
    base = {"A": [100, 102, 101, 105, 103, 108, 110], "B": [50, 49, 51, 52, None, 53, 55]}

    def world(pert=None, qpert=None):
        px = {c: dict(zip(win, v)) for c, v in base.items()}
        if pert:
            px[pert[0]][pert[1]] *= pert[2]
        # 통제: d−1 판단 · d 종가 체결 · 수량 = floor(금액 ÷ d 종가) — PR #68 D1 통제와 같은 의존
        orders = {win[1]: {"A": 400_000}, win[2]: {"B": 300_000}, win[3]: {"A": 600_000}, win[5]: {"A": -1}}
        q, qend, nav = {}, {}, {}
        for d in win:
            for c, v in orders.get(d, {}).items():
                if px[c][d] is None:
                    continue
                q[c] = 0 if v < 0 else math.floor(v / px[c][d])
            if qpert and d == qpert[0]:
                q[qpert[1]] = q.get(qpert[1], 0) + qpert[2]
            qend[d] = dict(q)
            nav[d] = 1_000_000 + sum(q[c] * (px[c][d] or 0) for c in q) * 0.01   # 통제 NAV(검사용 근사)
        return px, qend, nav

    E = dict(zip(win, [1.0, 1.0, 0.5, 0.5, 1.0, 0.25, 0.25]))

    def run_new(px, qend, nav, cash=1_000_000, nav_scale=1.0):
        return replay_lag(win, E, {d: v * nav_scale for d, v in nav.items()}, qend, lambda c, d: px[c].get(d), Flat(), cash=cash)

    def old_targets(px, qend, nav):
        """PR #68 계약(그날 통제 최종 수량을 같은 날 종가에) — 비교용 목표만."""
        return {d: {c: math.floor(E[d] * qend[d].get(c, 0)) for c in qend[d]} for d in win}

    res = {}
    px0, q0, n0 = world()
    r0 = run_new(px0, q0, n0)
    t_day = win[3]                                                  # t+1 = 4번째 날
    for tag, w in (("t+1 종가 +10%(A)", world(pert=("A", t_day, 1.10))), ("t+1 통제 체결 수량 +7(A)", world(qpert=(t_day, "A", 7)))):
        r1 = run_new(*w)
        same_new = [x for x in r0["decisions"] if x["decided_at"] < t_day] == [x for x in r1["decisions"] if x["decided_at"] < t_day]
        tgt_new = next(x["targets"] for x in r0["decisions"] if x["for"] == t_day) == next(x["targets"] for x in r1["decisions"] if x["for"] == t_day)
        fills_new = [x for x in r0["trades"] if x[0] == t_day] == [x for x in r1["trades"] if x[0] == t_day]
        o0, o1 = old_targets(px0, q0, n0), old_targets(*w)
        res[tag] = {"new_decisions_before_t+1_same": same_new, "new_target_for_t+1_same": tgt_new, "new_fill_qty_t+1_same": fills_new,
                    "old_contract_target_t+1_same": o0[t_day] == o1[t_day]}
    res["보존 · 정수 · 중복 · 음수 현금"] = {"checks": r0["acc"].counts.get("checks"), "max_gap": [r0["acc"].tot.get("max_gap_cash"), r0["acc"].tot.get("max_gap_nav")],
                                    "all_int": all(isinstance(x[3], int) for x in r0["trades"]), "dup": r0["dup"], "min_cash": min(r0["cash"])}
    res["거래정지 · 값 없음(B, 5번째 날)"] = {"no_price_skips": r0["notes"].get("no_price", 0),
                                      "B_traded_on_halt_day": any(x[0] == win[4] and x[1] == "B" for x in r0["trades"])}
    r2 = run_new(px0, q0, n0, nav_scale=0.3)                       # 통제 NAV를 0.3배로 → k ≈ 3.3 → 목표 금액이 현금보다 큼
    res["현금 부족(k≈3.3)"] = {"buy_reduced_or_unfilled": r2["notes"].get("buy_reduced_or_unfilled", 0), "min_cash": min(r2["cash"]),
                                 "checks": r2["acc"].counts.get("checks")}
    res["첫날 주문 없음"] = {"trades_day0": sum(1 for x in r0["trades"] if x[0] == win[0])}
    p = res
    res["pass"] = (all(v["new_decisions_before_t+1_same"] and v["new_target_for_t+1_same"] and v["new_fill_qty_t+1_same"]
                       for k, v in p.items() if k.startswith("t+1"))
                   and not any(v["old_contract_target_t+1_same"] for k, v in p.items() if k.startswith("t+1"))
                   and p["보존 · 정수 · 중복 · 음수 현금"]["all_int"] and not p["보존 · 정수 · 중복 · 음수 현금"]["dup"]
                   and p["보존 · 정수 · 중복 · 음수 현금"]["min_cash"] >= 0 and p["거래정지 · 값 없음(B, 5번째 날)"]["no_price_skips"] > 0
                   and not p["거래정지 · 값 없음(B, 5번째 날)"]["B_traded_on_halt_day"] and p["현금 부족(k≈3.3)"]["min_cash"] >= 0
                   and p["현금 부족(k≈3.3)"]["buy_reduced_or_unfilled"] > 0
                   and p["첫날 주문 없음"]["trades_day0"] == 0)
    return res


OUT.mkdir(parents=True, exist_ok=True)
SYN = synthetic()
print("합성", json.dumps(SYN, ensure_ascii=False), flush=True)
RES = {"synthetic": SYN}
if not SYN["pass"]:
    RES["verdict"] = "BLOCKED"
    (OUT / "et_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    raise SystemExit("BLOCKED: 합성 검사 실패 → Train 실행 안 함")

# ═════════ 저장 입력 ═════════
rows = list(csv.DictReader(open(IN / "nav_control_candidate.csv", encoding="utf-8")))
WIN = [r["date"] for r in rows if LO <= r["date"] <= HI]
cal = [d for d in G["DAYS"] if LO <= d <= HI]
assert WIN == cal and len(WIN) == 127, (len(WIN), len(cal))
R = {r["date"]: r for r in rows}
E = {d: float(R[d]["exposure"]) for d in R}
navN = {k: {d: float(R[d][f"control_{k}"]) for d in R} for k in SL}
navO = {k: {d: float(R[d][f"cand_{k}"]) for d in R} for k in SL}
CT = json.load(open(IN / "control_trades.json"))
OT = json.load(open(IN / "candidate_trades.json"))
M = pickle.load(open(M15PKL, "rb"))
QE = {k: qend_of(CT[k], WIN) for k in DAILY}
stockp = lambda c, d: G["CL"].get(c, {}).get(d)
etfp = lambda c, d: G["ETF"].get(c, {}).get(d)
PRICE = {"D1": stockp, "ETF": etfp, "BASKET": stockp}
KIND = {"D1": "stock", "ETF": "etf", "BASKET": "stock", "M15": "stock"}


def d1lock(c, d, side):
    ln, j = G["LANE"].get(c), G["IDXOF"].get(c, {}).get(d)
    return ln is not None and j is not None and lab.locked(ln["closes"], ln["날"], j, side)


# 15분봉 날 마감 값(저장 봉의 그날 마지막 종가)
m15close = {}
for c, bl in M["bars"].items():
    for T, o, cl in bl:
        m15close.setdefault(c, {})[T[:8]] = cl
m15p = lambda c, d: m15close.get(c, {}).get(d)


def recon(trades, kind, price, navs, key=lambda t: t[:8]):
    """저장 체결 + 비용식 → 날별 현금 · 투자액 · 비용 · 거래 금액(전략 재실행 아님). 저장 NAV와 차이를 셈."""
    costs = KN.Costs(CC, G["market_of"], 2.0, kind)
    by = {}
    for t, c, s, n, p in trades:
        by.setdefault(key(t), []).append((t, c, s, n, p))
    q, cash, lastp, out = {}, SLEEVE, {}, {"cash": [], "inv": [], "gap": [], "cost": 0.0, "notional": 0.0, "buy": 0, "sell": 0}
    for d in WIN:
        for t, c, s, n, p in by.get(d, []):
            amt = n * p
            r = costs.rate(s, c, t, amt)[0]
            if s == "buy":
                cash -= amt * (1 + r)
                q[c] = q.get(c, 0) + n
                out["buy"] += 1
            else:
                cash += amt * (1 - r)
                q[c] = q.get(c, 0) - n
                out["sell"] += 1
            out["cost"] += amt * r
            out["notional"] += amt
        inv = 0.0
        for c, n in q.items():
            if n:
                v = price(c, d)
                if v:
                    lastp[c] = v
                inv += n * lastp.get(c, 0.0)
        out["cash"].append(cash)
        out["inv"].append(inv)
        out["gap"].append(abs(cash + inv - navs[d]))
    out["max_gap"] = max(out["gap"])
    return out


REC = {"control": {}, "old_candidate": {}}
for k in SL:
    pr = m15p if k == "M15" else PRICE[k]
    REC["control"][k] = recon(CT[k], KIND[k], pr, navN[k])
    REC["old_candidate"][k] = recon(OT[k], KIND[k], pr, navO[k])
RES["reconstruction_max_gap_won"] = {g: {k: REC[g][k]["max_gap"] for k in SL} for g in REC}
print("저장 체결 재구성 최대 차이(원)", RES["reconstruction_max_gap_won"], flush=True)
recon_ok = all(v <= 1.0 for g in RES["reconstruction_max_gap_won"].values() for v in g.values())
RES["reconstruction_ok(≤1원)"] = recon_ok
if SYN_ONLY or not recon_ok:
    RES["verdict"] = "BLOCKED" if not recon_ok else "SYNTHETIC_ONLY"
    (OUT / "et_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    raise SystemExit("저장 입력 재구성 실패 → Train 실행 안 함" if not recon_ok else "합성 · 재구성만")

# ═════════ Train 1회 재생(고친 후보 · 일봉 셋) ═════════
NEW = {}
for k in DAILY:
    NEW[k] = replay_lag(WIN, E, navN[k], QE[k], PRICE[k], KN.Costs(CC, G["market_of"], 2.0, KIND[k]), lock=d1lock if k == "D1" else None)
    print("고친 후보", k, round(NEW[k]["nav"][-1]), "매매", len(NEW[k]["trades"]), NEW[k]["notes"], "중복", NEW[k]["dup"], flush=True)
    assert not NEW[k]["dup"]


def metrics(nav, cash, cost, notional, trades):
    seg = [TOTAL] + nav
    r = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    peak, mdd, mdd_at = TOTAL, 0.0, None
    for d, v in zip([None] + WIN, seg):
        peak = max(peak, v)
        if v / peak - 1 < mdd:
            mdd, mdd_at = v / peak - 1, d
    wd = min(range(len(r)), key=lambda i: r[i])
    mo = {}
    for d, x in zip(WIN, r):
        mo[d[:6]] = mo.get(d[:6], 1.0) * (1 + x)
    wm = min(mo, key=mo.get)
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    yrs = (D(WIN[-1]) - D(WIN[0])).days / 365.25
    cs = [c / n for c, n in zip(cash, nav)]
    return {"end_won": nav[-1], "return_pct": (nav[-1] / TOTAL - 1) * 100, "MDD_pct": mdd * 100, "MDD_at": mdd_at,
            "worst_day_pct": r[wd] * 100, "worst_day_at": WIN[wd], "worst_month_pct": (mo[wm] - 1) * 100, "worst_month_at": wm,
            "day_breach_-15": sum(1 for x in r if x < -0.15 - 1e-12), "month_breach_-15": sum(1 for v in mo.values() if v - 1 < -0.15 - 1e-12),
            "cost_won": cost, "turnover_per_year": notional / 2 / (sum(nav) / len(nav)) / yrs,
            "cash_share_avg_pct": sum(cs) / len(cs) * 100, "cash_share_min_pct": min(cs) * 100, "trades": trades}


def pack(navs, cashs, costs_, notional, trades):
    nav = [sum(navs[k][i] for k in SL) for i in range(len(WIN))]
    cash = [sum(cashs[k][i] for k in SL) for i in range(len(WIN))]
    return metrics(nav, cash, sum(costs_.values()), sum(notional.values()), trades), nav


tab, NAVS = {}, {}
for g, src in (("control", navN), ("old_candidate", navO)):
    tab[g], NAVS[g] = pack({k: [src[k][d] for d in WIN] for k in SL}, {k: REC[g][k]["cash"] for k in SL}, {k: REC[g][k]["cost"] for k in SL},
                           {k: REC[g][k]["notional"] for k in SL}, {k: {"buy": REC[g][k]["buy"], "sell": REC[g][k]["sell"]} for k in SL})
fnav = {k: NEW[k]["nav"] for k in DAILY} | {"M15": [navO["M15"][d] for d in WIN]}
fcash = {k: NEW[k]["cash"] for k in DAILY} | {"M15": REC["old_candidate"]["M15"]["cash"]}
fcost = {k: NEW[k]["acc"].tot["buy_cost"] + NEW[k]["acc"].tot["sell_cost"] for k in DAILY} | {"M15": REC["old_candidate"]["M15"]["cost"]}
fnot = {k: NEW[k]["acc"].tot["buy_notional"] + NEW[k]["acc"].tot["sell_notional"] for k in DAILY} | {"M15": REC["old_candidate"]["M15"]["notional"]}
ftr = {k: {"buy": sum(1 for x in NEW[k]["trades"] if x[2] == "buy"), "sell": sum(1 for x in NEW[k]["trades"] if x[2] == "sell")} for k in DAILY} | \
      {"M15": {"buy": REC["old_candidate"]["M15"]["buy"], "sell": REC["old_candidate"]["M15"]["sell"]}}
tab["fixed_candidate"], NAVS["fixed_candidate"] = pack(fnav, fcash, fcost, fnot, ftr)
RES["table"] = tab
RES["sleeve_end"] = {"control": {k: navN[k][WIN[-1]] for k in SL}, "old_candidate": {k: navO[k][WIN[-1]] for k in SL},
                     "fixed_candidate": {k: fnav[k][-1] for k in SL}}
RES["fixed_notes"] = {k: NEW[k]["notes"] for k in DAILY}
RES["fixed_conservation"] = {k: {"checks": NEW[k]["acc"].counts.get("checks"), "max_gap_cash": NEW[k]["acc"].tot.get("max_gap_cash"),
                                 "max_gap_nav": NEW[k]["acc"].tot.get("max_gap_nav"), "min_cash": min(NEW[k]["cash"]), "dup": NEW[k]["dup"],
                                 "buy_counts": {kk: v for kk, v in NEW[k]["acc"].counts.items() if kk.startswith("buy_")}} for k in DAILY}
# 시점 감사: 모든 목표가 체결 전날 잠겼는지
aud = {"decisions": 0, "decided_before_fill": 0}
for k in DAILY:
    for x in NEW[k]["decisions"]:
        aud["decisions"] += 1
        aud["decided_before_fill"] += int(x["decided_at"] < x["for"] and WIN.index(x["for"]) == WIN.index(x["decided_at"]) + 1)
    for d, c, s, n in NEW[k]["trades"]:
        assert d != WIN[0]
RES["timing_audit"] = aud
RES["pass"] = {"synthetic": SYN["pass"], "reconstruction": recon_ok,
               "conservation": all(v["max_gap_cash"] <= 1 and v["max_gap_nav"] <= 1 and v["min_cash"] >= 0 and not v["dup"] for v in RES["fixed_conservation"].values()),
               "timing_audit": aud["decisions"] == aud["decided_before_fill"]}
RES["verdict"] = "READY" if all(RES["pass"].values()) else "BLOCKED"
with open(OUT / "nav_train_control_old_fixed.csv", "w", encoding="utf-8") as f:
    f.write("date,exposure_E_t,control_nav,old_candidate_nav,fixed_candidate_nav," + ",".join(f"fixed_{k}" for k in SL) + "\n")
    for i, d in enumerate(WIN):
        f.write(f"{d},{E[d]:.10f},{NAVS['control'][i]:.2f},{NAVS['old_candidate'][i]:.2f},{NAVS['fixed_candidate'][i]:.2f}," +
                ",".join(f"{fnav[k][i]:.2f}" for k in SL) + "\n")
dec_sum = {k: {"n": len(NEW[k]["decisions"]), "nonzero_target_days": sum(1 for x in NEW[k]["decisions"] if any(v > 0 for v in x["targets"].values()))} for k in DAILY}
RES["decision_summary"] = dec_sum
local = {k: {"decisions": NEW[k]["decisions"], "trades": NEW[k]["trades"]} for k in DAILY}
raw = json.dumps(local, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
(OUT / "fixed_local_only.json").write_bytes(raw)
import hashlib  # noqa: E402
RES["fixed_local_only_sha256"] = hashlib.sha256(raw).hexdigest()
(OUT / "et_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
for g in tab:
    print(g, {k: v for k, v in tab[g].items()}, flush=True)
print("통과", RES["pass"], RES["verdict"], flush=True)
print("끝", flush=True)
