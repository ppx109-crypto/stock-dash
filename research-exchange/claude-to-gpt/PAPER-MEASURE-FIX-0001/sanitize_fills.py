"""PAPER-MEASURE-FIX-0001(PAPER-MEASURE-0001 교정판) · 로컬 KIS 체결 원문 → 비공개 정규화 체결 원장(JSONL). 네트워크 0 · 표준 라이브러리만.

확정 체결 규칙은 predash/trades.py normalize_kis와 같습니다(취소 제외 · 체결수량 0/빈칸 제외 · side 01/02만 ·
같은 (날짜 · 지점 · 주문 · 종목 · side) 재전달은 한 번, 합계가 다르면 중단). 다른 점:
- 원 주문번호 · 지점번호는 출력하지 않고 로컬 키 HMAC(fill_uid)만 남김. 키(PAPER_MEASURE_HMAC_KEY)가 없으면 거부.
- 주문 장부("접수" · order_no) 꼴 행은 체결로 받지 않고 거부(ORDER_ACCEPTED_NOT_FILL).
- 비공개 입력(--kis-rows · --context)과 비공개 출력(--out) 경로가 Git 작업트리 안이면 읽기 · 쓰기 전에 거부.
  그대로의 절대경로와 resolve()(심볼릭 링크 따라감) 결과 둘 중 하나라도 안이면 거부(FIX-0001 D3).
- KIS 행의 시각은 주문 시각 → fill_at_basis = ORDER_TIME_LOWER_BOUND.

사용(로컬 · 비공개):
  PAPER_MEASURE_HMAC_KEY=... python3 -I sanitize_fills.py --kis-rows <rows.json> --context <context.json> \
      --out <저장소 밖 경로/ledger.jsonl> --generator-commit <sha>
표준출력에는 개수 요약만 나옵니다(값 · 식별자 없음).
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime
from math import isfinite
from pathlib import Path

SCHEMA_VERSION = 1
KEY_ENV = "PAPER_MEASURE_HMAC_KEY"
MIN_KEY_BYTES = 16
COST_ITEMS = ("commission", "sell_tax", "farm_tax", "exchange_fees")
COST_KINDS = ("actual", "assumed")
ORDER_BOOK_KEYS = {"order_no", "status", "qty"}


class InputError(ValueError):
    pass


def _has_git_ancestor(p):
    for d in (p, *p.parents):
        if (d / ".git").exists():
            return True
    return False


def inside_git_worktree(path):
    """그대로의 절대경로('..'만 정리, 링크 안 따라감)와 resolve() 결과 중 하나라도 Git 작업트리 안이면 True."""
    return _has_git_ancestor(Path(os.path.abspath(path))) or _has_git_ancestor(Path(path).resolve())


def check_private_path(path, label):
    if inside_git_worktree(path):
        raise InputError(f"비공개 {label} 경로가 Git 작업트리 안(링크 · 상대경로 포함)이라 거부합니다.")
    return Path(path)


def load_key(env=None):
    raw = (env if env is not None else os.environ).get(KEY_ENV, "")
    key = raw.encode("utf-8")
    if len(key) < MIN_KEY_BYTES:
        raise InputError(f"{KEY_ENV}가 없거나 {MIN_KEY_BYTES}바이트보다 짧아 실제 입력 처리를 거부합니다.")
    return key


def _positive(value, label):
    try:
        v = float(str(value).replace(",", ""))
        if not isfinite(v) or v <= 0:
            raise ValueError
        return v
    except (TypeError, ValueError):
        raise InputError(f"{label} 값이 올바르지 않습니다.") from None


def fill_uid(key, day, branch, order, code, side):
    msg = "|".join((day, branch, order, code, side)).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _context_for(context, day, code, side):
    base = dict((context or {}).get("defaults") or {})
    for c in (context or {}).get("by_fill") or []:
        if str(c.get("date")) == day and str(c.get("code")) == code and str(c.get("side")) == side:
            base.update({k: v for k, v in c.items() if k not in ("date", "code", "side")})
    return base


def _costs(ctx):
    out = {}
    for item in COST_ITEMS:
        c = (ctx.get("costs") or {}).get(item)
        if c is None:
            out[item] = {"krw": None, "kind": "missing"}
            continue
        if c.get("kind") not in COST_KINDS:
            raise InputError(f"비용 {item}의 kind는 actual 또는 assumed여야 합니다.")
        v = float(c.get("krw"))
        if not isfinite(v) or v < 0:
            raise InputError(f"비용 {item} 값이 올바르지 않습니다.")
        out[item] = {"krw": v, "kind": c["kind"]}
    return out


def normalize(rows, key, context=None, generator_commit=None):
    """rows: KIS inquire-daily-ccld output1 행 목록. 돌려줌: (체결 목록, 개수 요약)."""
    if not isinstance(rows, list):
        raise InputError("체결 원문은 행 목록이어야 합니다.")
    fills, seen = [], {}
    n = {"input_rows": len(rows), "cancelled": 0, "unfilled": 0, "duplicate": 0, "confirmed": 0}
    for row in rows:
        if not isinstance(row, dict):
            raise InputError("행 형식이 올바르지 않습니다.")
        if ORDER_BOOK_KEYS <= set(row) and "tot_ccld_qty" not in row:
            raise InputError("ORDER_ACCEPTED_NOT_FILL: 주문 장부 행은 체결이 아닙니다.")
        if str(row.get("cncl_yn", "N")).upper() in ("Y", "1"):
            n["cancelled"] += 1
            continue
        raw_qty = row.get("tot_ccld_qty")
        if raw_qty in (None, "", "0", "0.0"):
            n["unfilled"] += 1
            continue
        side = {"01": "sell", "02": "buy"}.get(str(row.get("sll_buy_dvsn_cd", "")))
        if not side:
            raise InputError("매수 · 매도 구분을 확인할 수 없습니다.")
        code = str(row.get("pdno", "")).strip().upper()
        if re.fullmatch(r"A[0-9A-Z]{6}", code):
            code = code[1:]
        if not re.fullmatch(r"(?:[0-9A-Z]{6}|Q[0-9]{6})", code):
            raise InputError("종목코드 형식이 올바르지 않습니다.")
        day = str(row.get("ord_dt", "")).strip()
        clock = str(row.get("ord_tmd", "000000")).strip().zfill(6)
        try:
            if not (re.fullmatch(r"[0-9]{8}", day) and re.fullmatch(r"[0-9]{6}", clock)):
                raise ValueError    # predash보다 엄격: 자리 수가 틀린 날짜를 다른 날로 읽지 않음
            at = datetime.strptime(day + clock, "%Y%m%d%H%M%S")
        except ValueError:
            raise InputError("체결 일시를 확인할 수 없습니다.") from None
        qty = _positive(raw_qty, "체결수량")
        price = _positive(row.get("avg_prvs"), "체결 평균가")
        raw_amount = row.get("tot_ccld_amt")
        amount = _positive(raw_amount, "체결금액") if raw_amount not in (None, "") else qty * price
        branch, order = str(row.get("ord_gno_brno", "")).strip(), str(row.get("odno", "")).strip()
        if not order:
            raise InputError("주문번호가 없어 체결 중복을 판별할 수 없습니다.")
        unique = (day, branch, order, code, side)
        if unique in seen:
            if seen[unique] != (qty, price, amount):
                raise InputError("같은 주문에 다른 체결 합계가 있어 중복 계산을 중단했습니다.")
            n["duplicate"] += 1
            continue
        seen[unique] = (qty, price, amount)
        ctx = _context_for(context, day, code, side)
        fills.append({
            "schema_version": SCHEMA_VERSION,
            "fill_uid": fill_uid(key, *unique),
            "asset_id": code,
            "instrument_type": ctx.get("instrument_type"),
            "market_at_fill": ctx.get("market_at_fill"),
            "fill_at_kst": at.isoformat(),
            "fill_at_basis": "ORDER_TIME_LOWER_BOUND",
            "side": side,
            "quantity": qty,
            "fill_price": price,
            "amount_krw": amount,
            "costs": _costs(ctx),
            "strategy_id": ctx.get("strategy_id"),
            "rule_version": ctx.get("rule_version"),
            "signal_at_kst": ctx.get("signal_at_kst"),
            "available_at_basis": ctx.get("available_at_basis"),
            "reference_price": ctx.get("reference_price"),
            "reference_price_basis": ctx.get("reference_price_basis"),
            "generator_commit": generator_commit,
            "source": "KIS inquire-daily-ccld 로컬 파일",
        })
        n["confirmed"] += 1
    fills.sort(key=lambda f: (f["fill_at_kst"], f["asset_id"], 0 if f["side"] == "buy" else 1))
    stamps = {}
    for f in fills:
        stamps.setdefault((f["asset_id"], f["fill_at_kst"]), set()).add(f["side"])
    n["same_time_opposite_side"] = sum(1 for s in stamps.values() if len(s) > 1)
    missing = {}
    for f in fills:
        for k in ("instrument_type", "market_at_fill", "strategy_id", "rule_version", "signal_at_kst",
                  "available_at_basis", "reference_price", "generator_commit"):
            if f.get(k) in (None, ""):
                missing[k] = missing.get(k, 0) + 1
        for item, c in f["costs"].items():
            if c["kind"] == "missing":
                missing[f"costs.{item}"] = missing.get(f"costs.{item}", 0) + 1
    n["missing_field_counts"] = missing
    return fills, n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kis-rows", required=True)
    ap.add_argument("--context")
    ap.add_argument("--out", required=True)
    ap.add_argument("--generator-commit")
    a = ap.parse_args(argv)
    try:
        key = load_key()
        check_private_path(a.kis_rows, "입력 --kis-rows")
        if a.context:
            check_private_path(a.context, "입력 --context")
        check_private_path(a.out, "출력 --out")
        rows = json.loads(Path(a.kis_rows).read_text(encoding="utf-8"))
        if isinstance(rows, dict):
            rows = rows.get("rows", rows.get("output1"))
        ctx = json.loads(Path(a.context).read_text(encoding="utf-8")) if a.context else None
        fills, n = normalize(rows, key, ctx, a.generator_commit)
    except (InputError, OSError, ValueError) as e:
        print(json.dumps({"ok": False, "error": str(e)[:200]}, ensure_ascii=False))
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in fills), encoding="utf-8")
    print(json.dumps({"ok": True, "counts": n}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
