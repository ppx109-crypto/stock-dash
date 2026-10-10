"""RULES-0001 측정 계약 — 순수 함수(표준 라이브러리만 · 네트워크 · 계좌 · 운영 모듈 import 없음).
설계용: 운영에 연결하지 않음. 시각은 모두 KST ISO 문자열('YYYY-MM-DDTHH:MM:SS') — 문자열 비교로 순서를 정함.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

LOSS_LIMIT = -0.15          # 사용자 기준: 계좌 하루 · 달력월 각각 −15%(MDD와 별개)


# ── 1. 자료 사용 가능 시각 ──
def usable_value(versions, decision_at):
    """versions: [{'value', 'available_at', 'version'}] — 같은 관측치의 최초값 · 정정값.
    decision_at 이전(같거나 앞)에 나온 것 가운데 가장 늦은 판만 씀. 정정값으로 과거를 덮어쓰지 않음.
    돌려줌: (value, version) 또는 (None, None)."""
    ok = [v for v in versions if v["available_at"] <= decision_at]
    if not ok:
        return None, None
    best = max(ok, key=lambda v: (v["available_at"], v.get("version", 0)))
    return best["value"], best.get("version")


def bar_usable(bar_close_time, observed_at):
    """봉은 닫힌 시각 ≤ 관측 시각일 때만 신호에 씀(아직 안 닫힌 봉 금지)."""
    return bar_close_time <= observed_at


def fill_price_allowed(order_submitted_at, price_time):
    """체결 가정 가격은 주문 제출 뒤의 가격만. 신호를 늦게 계산했으면 이미 지난 다음 봉 시가는 못 씀."""
    return price_time >= order_submitted_at


def next_trading_open(d, holidays=()):
    """날짜만 있는 공시(시각 없음)의 교정안 available_at: 다음 거래일 09:00(제안 rule_id DART-DATEONLY-NEXT)."""
    x = date.fromisoformat(d) + timedelta(days=1)
    while x.weekday() >= 5 or x.isoformat() in holidays:
        x += timedelta(days=1)
    return x.isoformat() + "T09:00:00"


def dart_available_at(rcept_dt, rcept_time=None, holidays=()):
    """as-is는 접수일(날짜) 그날 사건으로 씀. 교정안: 시각이 있으면 그 시각, 없으면 다음 거래일 09:00."""
    if rcept_time:
        return f"{rcept_dt}T{rcept_time}"
    return next_trading_open(rcept_dt, holidays)


def reaction_window_valid(event_available_at, window_start):
    """공시 뒤 반응이라 부르려면 반응 창 시작 ≥ 공시가 알려진 시각."""
    return window_start >= event_available_at


# ── 2. 주문 · 체결 ──
def apply_order(position, cash, order, fills, fee_rate, tax_rate):
    """order: {'side','qty'} · fills: [{'qty','price','time'}](부분 · 0건 가능). 접수는 체결 증거가 아님 → fills만 반영.
    돌려줌: (새 수량, 새 현금, {'filled','unfilled','fees','taxes','status'})."""
    q = sum(f["qty"] for f in fills)
    if q > order["qty"]:
        raise ValueError("체결 수량이 주문 수량보다 큼")
    gross = sum(f["qty"] * f["price"] for f in fills)
    fees = gross * fee_rate
    taxes = gross * tax_rate if order["side"] == "sell" else 0.0
    if order["side"] == "buy":
        position, cash = position + q, cash - gross - fees
    else:
        if q > position:
            raise ValueError("가진 것보다 많이 팖")
        position, cash = position - q, cash + gross - fees - taxes
    status = "filled" if q == order["qty"] else ("partial" if q > 0 else "unfilled")
    return position, cash, {"filled": q, "unfilled": order["qty"] - q, "fees": fees, "taxes": taxes, "status": status}


def same_bar_tp_sl(bar, entry, tp, sl):
    """한 OHLC 봉에서 익절(+tp) · 손절(−sl)이 둘 다 닿으면 순서를 알 수 없음 → 보수적으로 손절 · ambiguous 표시."""
    hit_tp = bar["high"] >= entry * (1 + tp)
    hit_sl = bar["low"] <= entry * (1 - sl)
    if hit_tp and hit_sl:
        return {"exit": "SL", "price": entry * (1 - sl), "ambiguous": True}
    if hit_sl:
        return {"exit": "SL", "price": min(entry * (1 - sl), bar["open"]), "ambiguous": False}
    if hit_tp:
        return {"exit": "TP", "price": max(entry * (1 + tp), bar["open"]), "ambiguous": False}
    return {"exit": None, "price": None, "ambiguous": False}


def allocate_slots(requested, free):
    """요청 칸이 빈 칸보다 많으면 빈 칸만큼만(부분 배정). 빈 칸 0이면 못 삼."""
    return max(0, min(requested, free))


def qty_for(money, price):
    """1주 미만은 0(주문 안 함)."""
    return math.floor(money / price) if price > 0 and money > 0 else 0


def dedup_events(events, window):
    """events: [(코드, 갈래, 거래일 번호)] 정렬 · 같은 코드 · 갈래는 앞 사건에서 window 거래일 안이면 버림."""
    last, keep = {}, []
    for code, kind, i in sorted(events, key=lambda e: e[2]):
        k = (code, kind)
        if k in last and i - last[k] < window:
            continue
        last[k] = i
        keep.append((code, kind, i))
    return keep


# ── 3. NAV · 수익률 · 손실 ──
def nav(cash, positions, prices, receivable=0.0, payable=0.0, cash_includes_settlement=True):
    """NAV = 순현금 + 보유 평가 + 순결제채권. 예수금이 이미 결제 예정분을 반영했으면 채권 · 채무를 다시 더하지 않음."""
    v = cash + sum(q * prices[c] for c, q in positions.items())
    return v if cash_includes_settlement else v + receivable - payable


def daily_twr(nav_prev_close, segments):
    """segments: 하루 안 외부 입출금 시점으로 나눈 구간 [(구간 시작 NAV(입출금 직후), 구간 끝 NAV(다음 입출금 직전))].
    입출금이 없으면 segments=[(nav_prev_close, nav_close)]. TWR = Π(끝/시작) − 1."""
    r = 1.0
    for start, end in segments:
        if start <= 0:
            raise ValueError("구간 시작 NAV ≤ 0")
        r *= end / start
    return r - 1


def calendar_months(days_returns, month_first_trading_days=()):
    """[(YYYY-MM-DD, r)] → {YYYY-MM: (월 TWR, partial_month)}. 기록 첫날이 그 달 첫 거래일(month_first_trading_days)이 아니면 그 달은 partial."""
    g = {}
    for d, r in days_returns:
        g[d[:7]] = g.get(d[:7], 1.0) * (1 + r)
    res = {m: (v - 1, False) for m, v in g.items()}
    if days_returns and days_returns[0][0] not in set(month_first_trading_days):
        m = days_returns[0][0][:7]
        res[m] = (res[m][0], True)
    return res


def mtm_mdd(returns):
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in returns:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    return mdd


def loss_gate(day_twr, month_twr, limit=LOSS_LIMIT):
    """설계만(운영 적용 안 함): 그날 또는 그달 누적 TWR ≤ limit이면 '새 위험 늘리기' 주문을 막음. 갭 · 정지로 limit보다 더 잃을 수 있음."""
    return {"block_new_risk": day_twr <= limit or month_twr <= limit, "guarantee": False}


def attribute(strategy_pnls, account_pnl, tol=1e-9):
    """전략별 귀속 합 = 계좌 손익(내부 이체 · 비용 중복 없이). 다르면 차이를 돌려줌."""
    s = sum(strategy_pnls.values())
    return {"sum": s, "account": account_pnl, "gap": account_pnl - s, "ok": abs(account_pnl - s) <= tol}
