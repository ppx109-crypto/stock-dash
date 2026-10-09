"""REPLAY-RAW-PRICE-CONTRACT-0001 · 원주가 재생 어댑터(연구 복사본 · 운영 import 경로 안 건드림 · 네트워크 안 씀).

입력
- fills: [{fill_id, sleeve('D1'|'BASKET'), date('YYYYMMDD'), code, side('buy'|'sell'), intent}]
  · buy intent = {"notional": 목표 금액(원)} — 수량은 그날 공식 원주가 · 현금 · 비용으로 셈
  · sell intent = {"fraction": 0~1} — 그날 보유(기업행동 조정 뒤) 수량의 비율, 1이면 전부 · 또는 {"qty": 원수량}(보유 넘으면 SELL_CAPPED)
- raw: {code: {date: {"close": 원주가 종가, "status": 'OK'|...}}} — check_raw_pair()를 거친 값만
- ca: resolve_ca()를 거친 기업행동(효력일 · 비율)
- rate(side, code, day, notional) → 편도 비용률(비용 2배 계약은 호출 쪽에서 kernel2.Costs로 넣음)
- cash0 · days(거래일 목록)

출력 · 불변식
- 체결가 = 그날 공식 원주가 종가(호가 배수 아니면 INVALID_OFFICIAL_RAW로 체결 안 함)
- 매수 수량 = floor(min(목표 금액, 현금 한도) ÷ 원주가), 매도 수량 ≤ 보유(기업행동 조정 뒤)
- 비용 · 세금 = 원주가 × 원수량 notional × rate
- 일별 MTM = 원주가 종가 × 실제 수량(값 없으면 앞 값 + STALE 표시)
- 기업행동 = 효력일 장 시작 전 명시적 수량 · 현금 조정 레코드
- 현금 · 수량 항등식(두 경로) · 음수 금지 · 공식 필드 없으면 UNKNOWN(추정 · 반올림으로 채우지 않음)"""
import math
from collections import defaultdict

UNKNOWN = {
    "UNKNOWN_SELECTION_UNSUPPORTED": "원/수정 선택(FID_ORG_ADJ_PRC 1/0)이 기업행동 영향 구간에서도 같은 응답 — 원주가인지 알 수 없음",
    "INVALID_OFFICIAL_RAW": "원주가 응답 종가가 호가 단위 배수가 아님 — 원주가로 쓸 수 없음",
    "UNKNOWN_MISSING_RAW": "그날 원주가 응답 없음",
    "UNKNOWN_CA_FIELDS": "기업행동의 비율 · 기준일 · 효력일 중 필요한 칸이 없음",
    "UNKNOWN_CASH_IN_LIEU": "단주 현금 처리 칸 없음 — 단주를 버리거나 추정하지 않고 표시만",
    "UNKNOWN_MTM_STALE": "평가일 원주가 없음 — 앞 원주가로 평가하고 표시",
    "OUT_OF_SCOPE_15M": "15분봉 입력(12자리 시각 또는 M15 소계정) — 이번 범위 밖",
    "SELL_CAPPED": "매도 요청이 보유보다 많아 보유까지만",
    "BUY_REDUCED": "현금 한도로 매수 수량 축소",
}


def tick(p):
    for lim, t in ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)):
        if p < lim:
            return t
    return 1000


def on_tick(p):
    return p > 0 and abs(p / tick(p) - round(p / tick(p))) < 1e-9


# ── 공식 일봉 원/수정 쌍 검사 ──
def check_raw_pair(raw_rows, adj_rows, ca_effective_dates=()):
    """raw_rows/adj_rows: {date: close}. ca_effective_dates: 그 종목의 효력일들(조정이 생겨야 하는 날).
    돌려줌: {date: {"close": float|None, "status": str}}"""
    out = {}
    affected = [d for d in raw_rows if any(d < e for e in ca_effective_dates)]       # 효력일 앞 날 = 수정이 다르게 나와야 하는 날
    same = all(raw_rows.get(d) == adj_rows.get(d) for d in set(raw_rows) | set(adj_rows))
    unsupported = bool(affected) and same
    for d, c in raw_rows.items():
        if unsupported and d in affected:
            out[d] = {"close": None, "status": "UNKNOWN_SELECTION_UNSUPPORTED"}
        elif c is None:
            out[d] = {"close": None, "status": "UNKNOWN_MISSING_RAW"}
        elif not on_tick(c):
            out[d] = {"close": None, "status": "INVALID_OFFICIAL_RAW"}
        else:
            out[d] = {"close": float(c), "status": "OK"}
    return out


# ── 기업행동: 정정 사슬 · 필수 칸 ──
REQ = {"split": ("ratio", "effective_date"), "reverse_split": ("ratio", "effective_date"), "capital_reduction": ("ratio", "effective_date"),
       "bonus_issue": ("ratio", "record_date", "effective_date"), "rights_issue": ("ratio", "record_date", "effective_date"),
       "merger": ("ratio", "effective_date"), "spinoff": ("ratio", "effective_date")}
QTY_CHANGING = {"split", "reverse_split", "capital_reduction", "bonus_issue"}       # 보유 주식 수가 바뀌는 사건(유상 · 합병 · 분할은 계약상 수량 자동 조정 안 함 → 표시)


def resolve_ca(records):
    """정정공시는 원 접수(original_rcept_no)로 묶고 가장 늦은 접수(rcept_no)를 씀. 사슬은 보존."""
    chains = defaultdict(list)
    for r in records:
        chains[r.get("original_rcept_no") or r["rcept_no"]].append(r)
    out = []
    for root, rs in chains.items():
        rs = sorted(rs, key=lambda x: x["rcept_no"])
        last = dict(rs[-1])
        last["chain"] = [x["rcept_no"] for x in rs]
        last["root_rcept_no"] = root
        missing = [f for f in REQ.get(last["kind"], ("ratio", "effective_date")) if last.get(f) in (None, "")]
        last["status"] = "UNKNOWN_CA_FIELDS" if missing else "OK"
        last["missing"] = missing
        last["same_day_pit"] = bool(last.get("available_time"))                    # 시각 없으면 같은 날 사용을 PIT로 올리지 않음
        out.append(last)
    return out


# ── 재생 ──
def replay(fills, raw, ca, rate, cash0, days):
    for f in fills:
        if len(str(f["date"])) != 8 or f.get("sleeve") not in ("D1", "BASKET"):
            return {"status": "OUT_OF_SCOPE_15M", "fill_id": f.get("fill_id")}
    q, cash = defaultdict(int), float(cash0)
    rows, flags, mtm = [], defaultdict(list), []
    tot = defaultdict(float)
    adj_qty, adj_cash = defaultdict(int), 0.0
    lastp = {}
    by_day = defaultdict(list)
    for f in fills:
        by_day[f["date"]].append(f)
    for d in days:
        for e in ca:                                                    # ① 효력일 장 시작 전 조정
            if e.get("effective_date") != d or q.get(e["code"], 0) <= 0:
                continue
            c = e["code"]
            if e["status"] != "OK" or e["kind"] not in QTY_CHANGING:
                flags[d].append((c, e["status"] if e["status"] != "OK" else "CA_NO_AUTO_QTY:" + e["kind"]))
                continue
            new = q[c] * e["ratio"]
            whole = math.floor(new + 1e-9)
            frac = new - whole
            dq = whole - q[c]
            q[c] = whole
            adj_qty[c] += dq
            rows.append({"type": "CA_QTY", "date": d, "code": c, "dq": dq, "rcept": e["rcept_no"]})
            if frac > 1e-9:
                if e.get("cash_in_lieu_per_share") is None:
                    flags[d].append((c, "UNKNOWN_CASH_IN_LIEU"))
                else:
                    amt = frac * e["cash_in_lieu_per_share"]
                    cash += amt
                    adj_cash += amt
                    rows.append({"type": "CA_CASH", "date": d, "code": c, "amount": amt, "rcept": e["rcept_no"]})
        for f in sorted(by_day.get(d, []), key=lambda x: x["side"] != "sell"):   # ② 팔기 먼저
            c = f["code"]
            px_rec = raw.get(c, {}).get(d)
            if not px_rec or px_rec["status"] != "OK":
                flags[d].append((f["fill_id"], px_rec["status"] if px_rec else "UNKNOWN_MISSING_RAW"))
                continue
            px = px_rec["close"]
            assert on_tick(px)
            if f["side"] == "sell":
                it = f["intent"]
                want = int(it["qty"]) if "qty" in it else (q[c] if it["fraction"] >= 1 else math.floor(q[c] * it["fraction"]))
                if want > q[c]:
                    flags[d].append((f["fill_id"], "SELL_CAPPED"))
                    want = q[c]
                if want <= 0:
                    continue
                n = want * px
                cost = n * rate("sell", c, d, n)
                cash += n - cost
                q[c] -= want
                tot["sell_n"] += n
                tot["sell_c"] += cost
                tot["sell_q"] += want
                rows.append({"type": "SELL", "date": d, "code": c, "qty": want, "price": px, "cost": cost, "fill_id": f["fill_id"]})
            else:
                want = math.floor(f["intent"]["notional"] / px)
                total = lambda k: k * px * (1 + rate("buy", c, d, k * px))
                k = want
                if total(k) > cash:
                    lo, hi = 0, want
                    while lo < hi:
                        mid = (lo + hi + 1) // 2
                        if total(mid) <= cash:
                            lo = mid
                        else:
                            hi = mid - 1
                    k = lo
                    flags[d].append((f["fill_id"], "BUY_REDUCED"))
                if k <= 0:
                    continue
                n = k * px
                cost = n * rate("buy", c, d, n)
                cash -= n + cost
                q[c] += k
                tot["buy_n"] += n
                tot["buy_c"] += cost
                tot["buy_q"] += k
                rows.append({"type": "BUY", "date": d, "code": c, "qty": k, "price": px, "cost": cost, "fill_id": f["fill_id"]})
            assert cash >= -1e-6 and q[c] >= 0, "현금 · 수량 음수"
        inv = 0.0                                                       # ③ 일별 MTM(원주가)
        for c, n in q.items():
            if n <= 0:
                continue
            rec = raw.get(c, {}).get(d)
            if rec and rec["status"] == "OK":
                lastp[c] = rec["close"]
            else:
                flags[d].append((c, "UNKNOWN_MTM_STALE"))
            inv += n * lastp.get(c, 0.0)
        mtm.append({"date": d, "cash": cash, "inv": inv, "nav": cash + inv})
    # 두 경로 항등식
    cash_b = cash0 - tot["buy_n"] - tot["buy_c"] + tot["sell_n"] - tot["sell_c"] + adj_cash
    qty_b = {}
    for r in rows:
        if r["type"] in ("BUY", "SELL", "CA_QTY"):
            qty_b[r["code"]] = qty_b.get(r["code"], 0) + (r["qty"] if r["type"] == "BUY" else -r["qty"] if r["type"] == "SELL" else r["dq"])
    ident = {"cash_gap": abs(cash - cash_b), "qty_match": all(qty_b.get(c, 0) == v for c, v in q.items() if v) and all(v >= 0 for v in q.values()),
             "fill_prices_on_tick": all(on_tick(r["price"]) for r in rows if r["type"] in ("BUY", "SELL"))}
    return {"status": "DONE", "rows": rows, "flags": {d: v for d, v in flags.items()}, "mtm": mtm, "cash": cash, "qty": dict(q),
            "identity": ident, "totals": dict(tot), "adj_cash": adj_cash, "adj_qty": dict(adj_qty)}
