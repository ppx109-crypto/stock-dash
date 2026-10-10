"""PAPER-MEASURE-0001 · 비공개 정규화 체결 + 현금흐름 + 일별 평가 → 공개 비식별 일별 성과. 네트워크 0 · 표준 라이브러리만.

규칙(PREREG-LOCK §2):
- 외부 입출금 F_t는 그날 시작에 들어온 것으로 봄: r_t = E_t ÷ (E_{t−1} + F_t) − 1.
- 시작 상태 · 체결 비용 · 그날 평가가격 · 불가능 체결 검사 중 하나라도 실패하면 그날부터 null + 이유(보간 없음).
- 정규화 NAV 시작 1.0, 일별 MTM MDD는 NAV 기준(매매 끝난 날 기준 아님).
- 하루 · 달 손실 경보는 −15%보다 나쁠 때만(관측 경보 · 보장 아님).
공개 출력은 허용 필드만 쓰고 public_guard로 계좌 · 주문 · 토큰 · 원본 응답 · 절대 잔고 · 절대 수량 · 원 단위 금액을 검사합니다.

사용(로컬):
  python3 -I build_daily_measurement.py --fills <ledger.jsonl> --start <start.json> --prices <prices.json> \
      [--flows <flows.json>] [--corp-actions <ca.json>] [--sanitize-counts <counts.json>] --out <공개 출력.json>
start.json: {"date": "YYYY-MM-DD", "cash_krw": 숫자, "positions": {"종목": 수량}}
prices.json: {"YYYY-MM-DD": {"종목": 평가가격}} — 키에 있는 날이 측정 대상 거래일 전부(빠진 날 없다고 선언)
flows.json: [{"date": "YYYY-MM-DD", "amount_krw": +입금/−출금}]   ca.json: [{"date", "code", "qty_ratio"}]
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from math import isfinite
from pathlib import Path

SCHEMA_VERSION = 1
LOSS_LIMIT = -0.15
EPS = 1e-12                 # 부동소수 오차(0.85 − 1 = −0.15000000000000002)로 경계가 경보가 되지 않게

DAY_KEYS = {"date", "nav_norm", "twr_day", "day_loss_alert", "utilization", "cash_weight", "fills_confirmed", "status", "reason"}
MONTH_KEYS = {"month", "twr_month", "month_loss_alert", "days", "partial", "status", "reason"}
SUMMARY_KEYS = {
    "schema_version", "kind", "data_status", "period", "days_total", "days_valid", "first_invalid", "mdd_daily_mtm",
    "worst_day_twr", "worst_month_twr", "day_alerts", "month_alerts", "loss_limit", "fills_confirmed",
    "rejected_counts", "cost_bps", "slippage_bps", "completeness", "provenance", "days", "months", "notes",
}
NESTED_OK = {"period": {"from", "to"},
             "cost_bps": {"actual", "assumed", "missing_fills", "n_fills"},
             "slippage_bps": {"buy_mean", "sell_mean", "buy_n", "sell_n", "null_no_reference"},
             "rejected_counts": {"input_rows", "cancelled", "unfilled", "duplicate", "confirmed", "same_time_opposite_side"},
             "completeness": {"start_state", "valuation_missing_days", "cost_missing_fills", "impossible_fill_days",
                              "corp_actions_declared", "fill_at_basis", "missing_field_counts"},
             "provenance": {"generator_commit", "schema_version", "tool", "fill_source", "price_source"}}
FORBIDDEN_KEY = re.compile(r"account|acnt|cano|order|odno|ord_no|token|secret|appkey|raw|response|balance|"
                           r"quantity|qty|amount|krw|price(?!_source)|branch|brno|hmac|uid|equity", re.I)
ACCOUNT_LIKE = re.compile(r"\d{8}-?\d{2}(?!\d)|\d{10,}")


class MeasureError(ValueError):
    pass


def public_guard(obj, path="$"):
    """공개 출력 검사. 문제 목록(경로 · 이유만)을 돌려줌. 빈 목록이면 통과."""
    bad = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if k == "missing_field_counts":            # 값은 개수, 키는 필드 이름(값 없음)
                if not isinstance(v, dict) or any(not isinstance(n, int) or isinstance(n, bool) or not 0 <= n < 1e6 for n in v.values()):
                    bad.append((p, "missing_counts_not_int"))
                continue
            if k == "generator_commit" and (v is None or re.fullmatch(r"(?=.*[a-f])[0-9a-f]{7,40}", str(v))):
                continue
            if FORBIDDEN_KEY.search(str(k)):
                bad.append((p, "forbidden_key"))
            bad += public_guard(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad += public_guard(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        if ACCOUNT_LIKE.search(obj):
            bad.append((path, "account_or_order_like_string"))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if isfinite(obj) and abs(obj) >= 1e6:
            bad.append((path, "absolute_amount_like_number"))
    return bad


def whitelist_guard(out):
    bad = [("$." + k, "not_allowed") for k in out if k not in SUMMARY_KEYS]
    for k, allowed in NESTED_OK.items():
        if isinstance(out.get(k), dict):
            bad += [(f"$.{k}.{x}", "not_allowed") for x in out[k] if x not in allowed]
    for i, d in enumerate(out.get("days") or []):
        bad += [(f"$.days[{i}].{x}", "not_allowed") for x in d if x not in DAY_KEYS]
    for i, m in enumerate(out.get("months") or []):
        bad += [(f"$.months[{i}].{x}", "not_allowed") for x in m if x not in MONTH_KEYS]
    return bad


def _num(v, label):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise MeasureError(f"{label} 숫자 아님") from None
    if not isfinite(x):
        raise MeasureError(f"{label} 숫자 아님")
    return x


def _day(s):
    return date.fromisoformat(str(s)[:10]).isoformat()


def _fill_costs(f):
    vals, kinds = 0.0, set()
    for c in (f.get("costs") or {}).values():
        if c.get("kind") == "missing" or c.get("krw") is None:
            return None, "missing"
        vals += float(c["krw"])
        kinds.add(c["kind"])
    if not kinds:
        return None, "missing"
    return vals, ("actual" if kinds == {"actual"} else "assumed")


def measure(fills, start, prices, flows=(), corp_actions=(), sanitize_counts=None, generator_commit=None):
    if isinstance(sanitize_counts, dict) and isinstance(sanitize_counts.get("counts"), dict):
        sanitize_counts = sanitize_counts["counts"]          # sanitize_fills 표준출력을 그대로 받아도 됨
    days = sorted(_day(d) for d in prices)
    d0 = _day(start["date"])
    days = [d for d in days if d > d0]
    if not days:
        raise MeasureError("측정할 거래일이 없습니다.")
    by_day = defaultdict(list)
    for f in fills:
        by_day[_day(f["fill_at_kst"])].append(f)
    if any(d <= d0 or d > days[-1] for d in by_day):
        raise MeasureError("측정 기간 밖 체결이 있습니다.")
    if any(d not in set(days) for d in by_day):
        raise MeasureError("평가가격이 없는 날의 체결이 있습니다(거래일 목록 불완전).")
    flow = defaultdict(float)
    for x in flows:
        flow[_day(x["date"])] += _num(x["amount_krw"], "입출금")
    ca = defaultdict(list)
    for x in corp_actions:
        ca[_day(x["date"])].append((str(x["code"]), _num(x["qty_ratio"], "기업행동 비율")))

    cash = _num(start.get("cash_krw"), "시작 현금")
    pos = {str(k): _num(v, "시작 수량") for k, v in (start.get("positions") or {}).items()}
    p0 = {str(k): v for k, v in (prices.get(d0) or prices.get(start["date"]) or {}).items()}
    broken = None
    if any(q > 0 and str(c) not in p0 for c, q in pos.items()):
        broken = "START_VALUATION_MISSING"
        e_prev = None
    else:
        e_prev = cash + sum(q * _num(p0[c], "평가가격") for c, q in pos.items() if q > 0)
        if e_prev <= 0:
            broken, e_prev = "START_EQUITY_NONPOSITIVE", None

    out_days, nav, cost_tot = [], 1.0, {"actual": 0.0, "assumed": 0.0}
    traded, cost_missing, slips = 0.0, 0, {"buy": [], "sell": []}
    val_missing = imp_days = 0
    null_ref = 0
    for d in days:
        row = {"date": d, "nav_norm": None, "twr_day": None, "day_loss_alert": None, "utilization": None,
               "cash_weight": None, "fills_confirmed": len(by_day.get(d, [])), "status": "OK", "reason": ""}
        cash += flow.get(d, 0.0)
        for code, ratio in ca.get(d, []):
            if code in pos:
                pos[code] *= ratio
        day_reason = ""
        for f in by_day.get(d, []):
            c, kind = _fill_costs(f)
            amt = _num(f["amount_krw"], "체결금액")
            traded += amt
            if c is None:
                cost_missing += 1
                day_reason = day_reason or "COSTS_MISSING"
                c = 0.0
            else:
                cost_tot[kind] += c
            q = _num(f["quantity"], "수량")
            if f["side"] == "buy":
                cash -= amt + c
                pos[f["asset_id"]] = pos.get(f["asset_id"], 0.0) + q
            else:
                cash += amt - c
                pos[f["asset_id"]] = pos.get(f["asset_id"], 0.0) - q
            ref = f.get("reference_price")
            if ref in (None, "") or not f.get("reference_price_basis"):
                null_ref += 1
            else:
                r = _num(ref, "기준가")
                px = _num(f["fill_price"], "체결가")
                slips[f["side"]].append(((px - r) / r if f["side"] == "buy" else (r - px) / r) * 1e4)
        if any(q < -1e-9 for q in pos.values()) or cash < -1e-6:
            imp_days += 1
            day_reason = "IMPOSSIBLE_FILL(현금 또는 보유 음수)"
        held = {c: q for c, q in pos.items() if q > 1e-9}
        pd_ = prices.get(d) or {}
        if any(c not in pd_ for c in held):
            val_missing += 1
            day_reason = day_reason or "VALUATION_MISSING"
        if broken or day_reason:
            broken = broken or f"{day_reason}@{d}"
            row.update(status="NULL", reason=broken)
            out_days.append(row)
            continue
        posval = sum(q * _num(pd_[c], "평가가격") for c, q in held.items())
        e = cash + posval
        base = e_prev + flow.get(d, 0.0)
        if base <= 0 or e <= 0:
            broken = f"EQUITY_NONPOSITIVE@{d}"
            row.update(status="NULL", reason=broken)
            out_days.append(row)
            continue
        r = e / base - 1
        nav *= 1 + r
        row.update(nav_norm=round(nav, 10), twr_day=round(r, 10), day_loss_alert=r < LOSS_LIMIT - EPS,
                   utilization=round(posval / e, 10), cash_weight=round(cash / e, 10))
        out_days.append(row)
        e_prev = e

    valid = [x for x in out_days if x["status"] == "OK"]
    peak, mdd = 1.0, 0.0
    for x in valid:
        peak = max(peak, x["nav_norm"])
        mdd = min(mdd, x["nav_norm"] / peak - 1)
    months = []
    for m in sorted({d[:7] for d in days}):
        md = [x for x in out_days if x["date"][:7] == m]
        if all(x["status"] == "OK" for x in md):
            g = 1.0
            for x in md:
                g *= 1 + x["twr_day"]
            months.append({"month": m, "twr_month": round(g - 1, 10), "month_loss_alert": g - 1 < LOSS_LIMIT - EPS,
                           "days": len(md), "partial": m in (days[0][:7], days[-1][:7]), "status": "OK", "reason": ""})
        else:
            months.append({"month": m, "twr_month": None, "month_loss_alert": None, "days": len(md),
                           "partial": m in (days[0][:7], days[-1][:7]), "status": "NULL", "reason": "그 달에 null 날 있음"})
    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None
    sc = {k: v for k, v in (sanitize_counts or {}).items() if k in NESTED_OK["rejected_counts"]}
    out = {
        "schema_version": SCHEMA_VERSION, "kind": "PUBLIC_DEIDENTIFIED_DAILY", "data_status": "MEASURED" if valid else "NO_VALID_DAYS",
        "period": {"from": days[0], "to": days[-1]}, "days_total": len(days), "days_valid": len(valid),
        "first_invalid": next((x["date"] for x in out_days if x["status"] != "OK"), None),
        "mdd_daily_mtm": round(mdd, 10) if valid else None,
        "worst_day_twr": min((x["twr_day"] for x in valid), default=None),
        "worst_month_twr": min((m["twr_month"] for m in months if m["status"] == "OK"), default=None),
        "day_alerts": sum(1 for x in valid if x["day_loss_alert"]),
        "month_alerts": sum(1 for m in months if m["month_loss_alert"]),
        "loss_limit": LOSS_LIMIT, "fills_confirmed": sum(len(v) for v in by_day.values()), "rejected_counts": sc,
        "cost_bps": {"actual": round(cost_tot["actual"] / traded * 1e4, 4) if traded else None,
                     "assumed": round(cost_tot["assumed"] / traded * 1e4, 4) if traded else None,
                     "missing_fills": cost_missing, "n_fills": sum(len(v) for v in by_day.values())},
        "slippage_bps": {"buy_mean": mean(slips["buy"]), "sell_mean": mean(slips["sell"]), "buy_n": len(slips["buy"]),
                         "sell_n": len(slips["sell"]), "null_no_reference": null_ref},
        "completeness": {"start_state": "OK" if e_prev is not None or valid else "MISSING",
                         "valuation_missing_days": val_missing, "cost_missing_fills": cost_missing,
                         "impossible_fill_days": imp_days, "corp_actions_declared": sum(len(v) for v in ca.values()),
                         "fill_at_basis": "ORDER_TIME_LOWER_BOUND",
                         "missing_field_counts": (sanitize_counts or {}).get("missing_field_counts", {})},
        "provenance": {"generator_commit": generator_commit, "schema_version": SCHEMA_VERSION,
                       "tool": "PAPER-MEASURE-0001/build_daily_measurement.py", "fill_source": "KIS 체결 원문(로컬) → sanitize_fills",
                       "price_source": "로컬 평가가격 파일"},
        "days": out_days, "months": months,
        "notes": "관측 지표 · 경보는 −15%보다 나쁠 때만 · 보장 아님 · 체결 시각은 주문 시각 하한",
    }
    bad = public_guard(out) + whitelist_guard(out)
    if bad:
        raise MeasureError(f"공개 출력 검사 실패 {len(bad)}건: " + ", ".join(sorted({b[1] for b in bad})))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    for k in ("--fills", "--start", "--prices", "--out"):
        ap.add_argument(k, required=True)
    for k in ("--flows", "--corp-actions", "--sanitize-counts", "--generator-commit"):
        ap.add_argument(k)
    a = ap.parse_args(argv)
    rd = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
    try:
        fills = [json.loads(x) for x in Path(a.fills).read_text(encoding="utf-8").splitlines() if x.strip()]
        out = measure(fills, rd(a.start), rd(a.prices), rd(a.flows) if a.flows else (), rd(a.corp_actions) if a.corp_actions else (),
                      rd(a.sanitize_counts) if a.sanitize_counts else None, a.generator_commit)
    except (MeasureError, OSError, ValueError, KeyError) as e:
        print(json.dumps({"ok": False, "error": str(e)[:200]}, ensure_ascii=False))
        return 2
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "days_valid": out["days_valid"], "days_total": out["days_total"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
