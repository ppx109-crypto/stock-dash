"""BASELINE-ADJUSTMENT-CONSISTENCY-0001 · off-tick 저장가격 74/747의 역할별 노출 · 체결 유효성 · 수량/현금 일관성 감사(성과 재실행 없음).
python3 -E -P pa_audit.py <옛 nrl-cache.pkl> <control_trades.json> <signals_old.json> <PR76 원장 fixed_local_only.json>
                        <PR68 nav_control_candidate.csv> <PR76 nav_train_control_old_fixed.csv> <b2> <저장소(git)> <salt 파일> <출력 폴더>
- 네트워크 막음 · 읽기만. 원장 범위: 통제(PR #68) · 고친 후보(PR #76) × D1 · BASKET(747 분모와 같은 범위). 옛 후보는 쓰지 않는 기준이라 뺌.
- 비용식: kernel2.Costs(비용 2배) — 같은 폴더의 kernel2 · cost_contract(PR #68과 같은 해시)."""
import bisect
import hashlib
import json
import os
import pickle
import socket
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

OLD, CTRL, SIG, L76, NAV68, NAV76, B2, REPO, SALT, OUT = sys.argv[1:11]
OUT = Path(OUT)
(OUT / "evidence").mkdir(parents=True, exist_ok=True)


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
LO, HI = "20250918", "20260331"
LOG = []


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


salt = Path(SALT).read_text().strip()
H = lambda *x: hashlib.sha256((salt + "|" + "|".join(x)).encode()).hexdigest()[:16]
jl = lambda p: json.load(open(p, encoding="utf-8"))
CL = {c: dict(v["rows"]) for c, v in pickle.load(open(OLD, "rb"))[0].items()}
CAL = sorted(d for d in CL["005930"] if LO <= d <= HI)
ALLCAL = sorted(CL["005930"])
ct, sg, l76 = jl(CTRL), jl(SIG), jl(L76)


def tick(p):                                                 # PR #82 tick_check.py와 같은 표(2023-01-25 뒤 유가 · 코스닥)
    for lim, t in ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)):
        if p < lim:
            return t
    return 1000


on_tick = lambda p: abs(p / tick(p) - round(p / tick(p))) < 1e-9

# ═════════ 1. 분모 747 재구성(PR #82와 같은 규칙: (종목, 날짜) 중복 제거) ═════════
sigset = {(c, d) for d, v in sg["picks"].items() if LO <= d <= HI for c, _ in v}
FILLS = []                                                   # (원장, 소계정, 날, 종목, 방향, 수량, 체결가, 비고)
for k in ("D1", "BASKET"):
    for t, c, s, n, p in ct[k]:
        if LO <= str(t)[:8] <= HI:
            FILLS.append(("control", k, str(t)[:8], c, s, n, float(p)))
    for d, c, s, n in l76[k]["trades"]:
        FILLS.append(("fixed76", k, d, c, s, n, CL.get(c, {}).get(d)))   # PR #76 재생은 그날 저장 종가로 체결(et_replay.py PRICE)
need = set(sigset) | {(c, d) for _, _, d, c, *_ in FILLS}
off = {x for x in need if CL.get(x[0], {}).get(x[1]) is not None and not on_tick(CL[x[0]][x[1]])}
miss = {x for x in need if CL.get(x[0], {}).get(x[1]) is None}
say("분모", len(need), "· off-tick", len(off), "· 가격 없음", len(miss), "· off 종목", len({c for c, _ in off}))
assert len(need) == 747 and len(off) == 74, (len(need), len(off))

# ═════════ 2. 보유(포지션-일) 재구성 ═════════
def qty_paths(ledger, sleeve):
    q, out = defaultdict(int), {}
    by = defaultdict(list)
    for L, k, d, c, s, n, p in FILLS:
        if L == ledger and k == sleeve:
            by[d].append((c, s, n))
    for d in CAL:
        for c, s, n in by.get(d, []):
            q[c] += n if s == "buy" else -n
            assert q[c] >= 0, ("수량 음수", ledger, sleeve)
        out[d] = {c: v for c, v in q.items() if v > 0}
    return out


HOLD = {(L, k): qty_paths(L, k) for L in ("control", "fixed76") for k in ("D1", "BASKET")}

# 기업행동 8종목 · 저장 공시일(Train 안) ±5 거래일
CA = ("감자", "분할", "합병", "무상증자", "유상증자", "유무상증자")
ca_days = {}
for c in sorted({c for c, _ in need}):
    p = Path(B2, "dart-events", f"{c}.json")
    if not p.exists():
        continue
    rows = jl(p)["rows"]
    ds = sorted({str(r.get("rcept_no", ""))[:8] for k in CA for r in rows.get(k) or [] if "20250918" <= str(r.get("rcept_no", ""))[:8] <= "20261007"})
    if ds:
        ca_days[c] = ds
win = {}
for c, ds in ca_days.items():
    s = set()
    for x in ds:
        if not (LO <= x <= HI):
            continue
        i = bisect.bisect_left(ALLCAL, x)
        s.update(ALLCAL[max(0, i - 5):i + 6])
    win[c] = s
say("기업행동 종목", len(ca_days), "· Train 안 공시가 있는 종목", sum(1 for c in ca_days if win[c]))

# ═════════ 3. 역할별 노출(74 레코드) ═════════
role = {}
for c, d in off:
    r = set()
    if (c, d) in sigset:
        r.add("signal")
    for L, k, dd, cc, s, n, p in FILLS:
        if cc == c and dd == d:
            r.add("entry" if s == "buy" else "exit")
            r.add("fee_tax_notional")
    if any(c in HOLD[key].get(d, {}) for key in HOLD):
        r.add("open_position_mtm")
    if c in win and d in win[c]:
        r.add("ca_window")
    role[(c, d)] = r
combo = Counter("+".join(sorted(r)) or "(역할 없음)" for r in role.values())
excl = Counter()
for r in role.values():
    core = r - {"ca_window", "fee_tax_notional"}
    if core == {"signal"}:
        excl["신호에만"] += 1
    elif core == {"open_position_mtm"}:
        excl["MTM에만"] += 1
    elif core & {"entry", "exit"}:
        excl["체결에 사용(+다른 역할 가능)"] += 1
    elif not core:
        excl["역할 없음"] += 1
    else:
        excl["둘 이상(체결 없음)"] += 1
assert sum(excl.values()) == 74 and sum(combo.values()) == 74
fills_off = [f for f in FILLS if (f[3], f[2]) in off]
pos_days_off = Counter()
for key, path in HOLD.items():
    for d, h in path.items():
        for c in h:
            if (c, d) in off:
                pos_days_off["_".join(key)] += 1
cov = {"denominator_records": 747, "off_tick_records": 74, "off_tick_codes": len({c for c, _ in off}), "price_missing": len(miss),
       "role_counts(비배타)": {x: sum(1 for r in role.values() if x in r) for x in ("signal", "entry", "exit", "fee_tax_notional", "open_position_mtm", "ca_window")},
       "exclusive_buckets(합 74)": dict(excl), "role_combinations(합 74)": dict(combo),
       "fills_on_off_tick_records": {"fills": len(fills_off), "by_ledger_sleeve_side": dict(Counter(f"{f[0]}_{f[1]}_{f[4]}" for f in fills_off)),
                                     "unique_trade_days(종목·날)": len({(f[3], f[2]) for f in fills_off})},
       "position_days_on_off_tick_records": dict(pos_days_off),
       "off_tick_record_hashes": sorted(H(c, d) for c, d in off),
       "note": "74는 가격 레코드 수이고 거래 수가 아님. 한 레코드가 여러 원장 · 역할에 걸칠 수 있음."}

# ═════════ 4. 체결 유효성(범위 안 모든 체결) ═════════
fv = Counter()
fv_by = defaultdict(Counter)
price_eq = Counter()
for L, k, d, c, s, n, p in FILLS:
    stored = CL.get(c, {}).get(d)
    if p is None or stored is None:
        cls = "UNKNOWN_MISSING_MAPPING"
    else:
        price_eq["fill_price_eq_stored_close" if abs(p - stored) < 1e-9 else "fill_price_ne_stored_close"] += 1
        cls = "UNKNOWN_RAW_OR_ADJUSTED" if on_tick(p) else "IMPOSSIBLE_RAW_FILL"
    fv[cls] += 1
    fv_by[f"{L}_{k}_{s}"][cls] += 1
imp_trades = {(f[0], f[1], f[3], f[2]) for f in FILLS if f[6] is not None and not on_tick(f[6])}
fill_validity = {"denominator_fills": len(FILLS), "classes": dict(fv), "by_ledger_sleeve_side": {k: dict(v) for k, v in fv_by.items()},
                 "fill_price_vs_stored_close": dict(price_eq),
                 "cross_check(역할표 체결 수 = 유효성표 IMPOSSIBLE 수)": len(fills_off) == fv["IMPOSSIBLE_RAW_FILL"],
                 "impossible_fill_unique(원장·소계정·종목·날)": len(imp_trades),
                 "fee_tax_notional_on_impossible_fills": fv["IMPOSSIBLE_RAW_FILL"],
                 "note": "off-tick 체결가는 KRX 가격 단위 밖이라 실제 원주가 체결일 수 없음(한정된 뜻). on-tick은 원주가 · 수정주가 구별 불가."}

# ═════════ 5. 수량 · 현금 일관성(두 경로: 원장 직접 재구성 대 저장 NAV) ═════════
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["COST_REPLAY_ROOT"] = B2
import cost_contract as CC  # noqa: E402
import kernel2 as KN  # noqa: E402
KQ = {p.stem for p in Path(B2, "kosdaq-data").glob("*.json")}
market_of = lambda c: "KOSDAQ" if c in KQ else "KOSPI"
import csv  # noqa: E402
N68 = {r["date"]: r for r in csv.DictReader(open(NAV68, encoding="utf-8"))}
N76 = {r["date"]: r for r in csv.DictReader(open(NAV76, encoding="utf-8"))}
NAVS = {("control", k): {d: float(N68[d][f"control_{k}"]) for d in CAL} for k in ("D1", "BASKET")}
NAVS.update({("fixed76", k): {d: float(N76[d][f"fixed_{k}"]) for d in CAL} for k in ("D1", "BASKET")})


def ledger(key, lots):
    costs = KN.Costs(CC, market_of, 2.0, "stock")
    by = defaultdict(list)
    for L, k, d, c, s, n, p in FILLS:
        if (L, k) == key:
            by[d].append((c, s, n, p))
    cash, q, book, lastp = 2_500_000.0, defaultdict(int), defaultdict(list), {}
    rows, pos_days, off_mtm, stale = [], 0, 0, 0
    cash0 = cash
    buy_amt = sell_amt = cost_sum = 0.0
    bq = sq = 0
    for d in CAL:
        for c, s, n, p in by.get(d, []):
            pieces = [n]
            if s == "buy":
                book[c].append([d, n])
            elif lots:
                pieces, left = [], n
                for lot in sorted(book[c]):
                    if left <= 0:
                        break
                    tk = min(left, lot[1])
                    pieces.append(tk)
                    lot[1] -= tk
                    left -= tk
                book[c] = [x for x in book[c] if x[1] > 0]
            for m in pieces:
                amt = m * p
                r = costs.rate(s, c, d, amt)[0]
                cost_sum += amt * r
                if s == "buy":
                    cash -= amt * (1 + r)
                    buy_amt += amt
                else:
                    cash += amt * (1 - r)
                    sell_amt += amt
            if s == "buy":
                q[c] += n
                bq += n
            else:
                q[c] -= n
                sq += n
        inv = 0.0
        for c, n in q.items():
            if n:
                v = CL.get(c, {}).get(d)
                if v:
                    lastp[c] = v
                    off_mtm += not on_tick(v)
                else:
                    stale += 1
                inv += n * lastp.get(c, 0.0)
                pos_days += 1
        rows.append(abs(cash + inv - NAVS[key][d]))
    ident_cash = abs(cash - (cash0 - buy_amt + sell_amt - cost_sum))
    return {"days": len(CAL), "max_nav_gap_won(경로A 재구성 대 경로B 저장 NAV)": max(rows), "days_gap_gt_1won": sum(1 for x in rows if x > 1.0),
            "cash_identity_gap_won(기말 = 기초 − 매수 + 매도 − 비용)": ident_cash, "qty_identity_ok(기말 = 기초 + 매수 − 매도 · 음수 0)": all(v >= 0 for v in q.values()),
            "buy_qty": bq, "sell_qty": sq, "end_qty": sum(q.values()), "position_days": pos_days, "position_days_off_tick_mtm": off_mtm,
            "position_days_stale_price": stale, "explicit_ca_adjust_records": 0, "non_trade_qty_changes": 0}


acct = {}
for key in HOLD:
    acct["_".join(key)] = ledger(key, lots=(key[0] == "fixed76"))
kinds = Counter(s for _, _, _, _, s, *_ in FILLS)
for k, v in acct.items():
    v["verdict"] = "INTERNAL_CONSISTENCY_PASS" if v["days_gap_gt_1won"] == 0 and v["cash_identity_gap_won(기말 = 기초 − 매수 + 매도 − 비용)"] < 1e-6 and v["qty_identity_ok(기말 = 기초 + 매수 − 매도 · 음수 0)"] else "INTERNAL_INCONSISTENCY_PROVED"
position_accounting = {"ledgers": acct, "record_kinds_in_ledgers": dict(kinds),
                       "explicit_corporate_action_adjustment_records": 0,
                       "note": "원장에는 buy/sell 밖의 수량 · 현금 조정 레코드가 없음(기업행동 조정을 명시적으로 다루지 않음). 수정주가 계열 위에서 수량 · 현금이 서로 맞는다는 뜻이지, 실제 체결 가능 수량 · notional이 검증됐다는 뜻은 아님."}
say("회계", json.dumps({k: {kk: v[kk] for kk in ("max_nav_gap_won(경로A 재구성 대 경로B 저장 NAV)", "position_days", "position_days_off_tick_mtm", "verdict")} for k, v in acct.items()}, ensure_ascii=False))

# ═════════ 6. 기업행동 통과(8종목 · 실제 보유구간) ═════════
def versions(code):
    out = subprocess.run(["git", "-C", REPO, "log", "--format=%H", "00b98ab1655c84806357f44f2de6f1509ef1447f", "--", f"price-data/{code}.json"],
                         capture_output=True, text=True).stdout.split()
    vs = []
    for h in out:
        raw = subprocess.run(["git", "-C", REPO, "show", f"{h}:price-data/{code}.json"], capture_output=True, text=True).stdout
        try:
            vs.append({str(d): float(c) for d, c in json.loads(raw).get("closes") or []})
        except ValueError:
            pass
    return vs


cx = {"ca_codes": len(ca_days), "codes_with_train_filing": sum(1 for c in ca_days if win[c]), "per_code": [], "totals": Counter()}
for c in sorted(ca_days):
    held = {(key, d) for key, path in HOLD.items() for d, h in path.items() if c in h}
    held_days = sorted({d for _, d in held})
    vs = versions(c)
    jumps = 0
    for d in held_days:
        i = ALLCAL.index(d)
        a, b = CL.get(c, {}).get(ALLCAL[i - 1]), CL.get(c, {}).get(d)
        if a and b and abs(b / a - 1) > 0.30:
            jumps += 1
    changed = sum(1 for d in held_days if len({v[d] for v in vs if d in v}) > 1)
    in_win = [x for x in held if x[1] in win[c]]
    fills_win = [f for f in FILLS if f[3] == c and f[2] in win[c]]
    off_held = sum(1 for d in held_days if CL.get(c, {}).get(d) and not on_tick(CL[c][d]))
    verdict = ("NOT_HELD_IN_TRAIN" if not held else
               "UNKNOWN_NEEDS_OFFICIAL_RAW_AND_CA_EFFECTIVE_DATE")
    rec = {"code": H(c), "train_filings": sum(1 for x in ca_days[c] if LO <= x <= HI), "held_position_days": len(held), "held_unique_days": len(held_days),
           "held_days_in_±5_window": len(in_win), "fills_in_±5_window": len(fills_win), "held_days_off_tick": off_held,
           "held_day_jumps_gt_30pct(가격제한 밖 = 기계적 재배율 흔적)": jumps, "held_days_value_changed_across_git_versions": changed,
           "git_versions": len(vs), "qty_change_without_trade": 0, "cash_change_without_trade": 0, "verdict": verdict}
    cx["per_code"].append(rec)
    for kk in ("held_position_days", "held_days_in_±5_window", "fills_in_±5_window", "held_days_off_tick", "held_day_jumps_gt_30pct(가격제한 밖 = 기계적 재배율 흔적)", "held_days_value_changed_across_git_versions"):
        cx["totals"][kk] += rec[kk]
    cx["totals"]["verdict:" + verdict] += 1
cx["totals"] = dict(cx["totals"])
cx["note"] = "저장 공시일은 효력일이 아님. ±5 거래일 창은 탐색 표시일 뿐 원인 확정에 쓰지 않음. 공식 원주가 · 효력일 · 비율 없이 특정 사건의 오류라고 단정하지 않음."
say("기업행동", json.dumps(cx["totals"], ensure_ascii=False))

for name, obj in (("off-tick-role-coverage", cov), ("fill-validity", fill_validity), ("position-accounting", position_accounting), ("corporate-action-crossings", cx)):
    (OUT / "evidence" / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
say("역할", json.dumps({k: v for k, v in cov.items() if k not in ("off_tick_record_hashes",)}, ensure_ascii=False))
say("체결 유효성", json.dumps({k: v for k, v in fill_validity.items() if k != "note"}, ensure_ascii=False))
(OUT / "evidence" / "run.log").write_text("\n".join(LOG) + "\n", encoding="utf-8")
say("끝")
