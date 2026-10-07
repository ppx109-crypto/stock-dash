"""사건 바구니 C — 한투 **모의투자**(사용자 2026-10-07 "바구니C 좋네 넣어주고" · 연구 docs/RL-PRO.md P4 · P4b · research/z021.py).

규칙(연구와 같게):
  사건   : 어제(t0) DART 접수 공시 가운데 그날 시총 200위 안 종목의
           · 자사주 취득(제목 '자기주식취득') — t0 반응(t0−1 → t0 종가 수익 − 그날 200위 가운데값) < −2%
           · 무상증자 — 반응과 상관없이
           같은 종목 · 같은 갈래는 20거래일 안 다시 안 셈(앞 사건과만 견줌).
  사기   : 공시 다음 날(t0+1) 15:10 판단 → 시장가(종가 근처). 반응은 t0 종가까지 값이라 15:15에 판단해도 같은 결정.
  칸     : 5칸 · 한 칸 = 바구니 돈 ÷ 5 · 바구니 돈 = **1일봉 몫(계좌 × 50%) 가운데 1일봉이 안 쓰는 돈**(연구 P4b와 같게 · 2026-10-07 오푸스 검토:
           15분봉 몫까지 쓰면 다음 날 15분봉이 살 때 바구니가 20일 전에 강제로 팔림) · 다른 규칙이 든 종목은 안 삼.
           빈 칸이 있을 때만 · 이미 든 종목은 안 삼.
  팔기   : 산 날부터 20거래일째 15:10 시장가. 손절 · 익절 없음.
  돈 차례: 규칙 > 바구니 > 빈칸 엔진(연구 P4b: 쉬는 돈을 바구니가 먼저 · 엔진은 남은 몫).
           규칙이 살 돈이 모자라면 paper_trade.make_room이 엔진 것 다음 바구니 것을 팖.
미래 참조: 공시는 t0 저녁(19:20 events 작업)에 모임 → 다음 날 씀 · 종가는 t0까지 · 시총 순위는 t0 종가 × 그날까지 접수된 주식 수.
주문은 모의투자 서버에만 · 키 · 계좌 · 증권사 응답 본문은 찍지 않음 · 장부는 basket-live/에.
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

HOME = Path("basket-live")
STATE = HOME / "state.json"
BOOK = HOME / "paper-orders.json"
TODAY = HOME / "today.json"
SLOTS, HOLD, GAP, TH, TOP = 5, 20, 20, -0.02, 200
KINDS = ("자사주취득", "무상증자")


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, body):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


# ───────────────────────── 계산(증권사 없이 시험할 수 있게) ─────────────────────────

def reactions(prices, t0, prev, top=TOP):
    """t0 반응(그날 200위 가운데값 뺌) · 200위 안 종목 모음. prices: {코드: {'rows': [(날, 종가)]}}.
    돌려줌: ({코드: 반응}, {200위 안 코드}). 시총 순위는 caps.tag(t0 종가 × 그날까지 접수된 주식 수)."""
    import caps
    rows = []
    for c, v in prices.items():
        got = dict(v["rows"])
        if t0 in got:
            rows.append({"code": c, "date": t0, "price": got[t0], "_prev": got.get(prev)})
    caps.tag(rows, top)
    inside = {r["code"] for r in rows if caps.inside(r, top)}
    raw = {r["code"]: r["price"] / r["_prev"] - 1 for r in rows if r["code"] in inside and r.get("_prev")}
    if len(raw) < 40:
        return {}, inside
    mid = statistics.median(raw.values())
    return {c: x - mid for c, x in raw.items()}, inside


def todays_events(events, t0, before):
    """events: {코드: [(접수일, 갈래)]} → t0 사건 [(코드, 갈래)]. 주말 · 휴일 접수(before < 접수일 ≤ t0)도 t0 사건으로(연구와 같게)."""
    return sorted({(c, k) for c, rows in events.items() for d, k in rows if before < d <= t0 and k in KINDS})


def step(state, day, t0, days_since, events_t0, react, inside, held, now_price, capital, avail, names=None, others=()):
    """하루 판단(15:10).
    state: {'positions': {코드: {'day', 'price', 'kind', 'react'}}, 'last': {'코드:갈래': t0 위치 열쇠(날)}}
    days_since(buy_day) → 산 날부터 오늘까지 거래일 수(산 날 = 0) · events_t0: [(코드, 갈래)] ·
    held: 바구니 장부 수량 · capital: 바구니 돈(원) · avail: 지금 쓸 수 있는 현금(원 · 1일봉 몫 비켜 둔 뒤).
    돌려줌: (주문 [(코드, 'buy'|'sell', 수량, 까닭)], 새 상태, 까닭 줄들)."""
    names = names or {}
    st = json.loads(json.dumps(state or {}))
    pos = st.setdefault("positions", {})
    last = st.setdefault("last", {})
    orders, why = [], []
    for code, p in list(pos.items()):
        have = int(held.get(code, 0))
        if have < 1:                                   # 장부에 없으면(자리 내줌 등) 상태에서도 뺌
            pos.pop(code)
            continue
        n = days_since(p["day"])
        if n >= HOLD:
            price = now_price.get(code)
            r = f" {(price / p['price'] - 1) * 100:+.1f}%" if price and p.get("price") else ""
            orders.append((code, "sell", have, f"바구니 {HOLD}거래일 지남{r}"))
            pos.pop(code)
    freed = sum(q * (now_price.get(c) or 0) for c, s, q, _ in orders if s == "sell")
    left = (avail + freed) * 0.97
    slot = capital / SLOTS
    for code, kind in events_t0:
        key = f"{code}:{kind}"
        prev = last.get(key)
        if prev and days_since(prev) - days_since(t0) < GAP:       # 같은 종목 · 같은 갈래 20거래일 안 겹침(앞 사건과만)
            why.append(f"{names.get(code, code)} {kind} — 앞 사건({prev})과 20거래일 안이라 셈하지 않음")
            continue
        if code not in inside:
            continue
        r = react.get(code)
        if r is None:
            continue
        last[key] = t0                               # 200위 안 · 반응이 있는 사건만 '앞 사건'으로 남김(연구와 같게)
        if kind == "자사주취득" and not r < TH:
            why.append(f"{names.get(code, code)} 자사주 취득 — 반응 {r * 100:+.1f}%(−2% 아래만 삼)")
            continue
        label = f"{'자사주 취득 · 반응 ' + format(r * 100, '+.1f') + '%' if kind == '자사주취득' else '무상증자'}"
        if code in pos:
            why.append(f"{names.get(code, code)} {label} — 이미 들고 있음")
            continue
        if code in others:
            why.append(f"{names.get(code, code)} {label} — 다른 규칙이 이미 들고 있어 안 삼(한 종목 40% 한도)")
            continue
        if len(pos) >= SLOTS:
            why.append(f"{names.get(code, code)} {label} — 5칸이 다 참")
            continue
        price = now_price.get(code)
        qty = math.floor(min(slot * 0.97, left) / price) if price else 0
        if qty < 1:
            why.append(f"{names.get(code, code)} {label} — 살 돈이 모자람")
            continue
        left -= qty * price
        orders.append((code, "buy", qty, f"바구니 — {label}"))
        pos[code] = {"day": day, "price": price, "kind": kind, "react": round(r, 4)}
    # 오래된 '앞 사건' 기록은 40거래일 넘으면 지움(파일이 끝없이 커지지 않게)
    for key in [k for k, d in last.items() if days_since(d) > 2 * GAP]:
        last.pop(key)
    st["last_day"] = day
    return orders, st, why


# ───────────────────────── 실제 날(idle_live.run 안에서 15:10에 부름) ─────────────────────────

def load_events(codes=None, folder="event-data"):
    out = {}
    for path in Path(folder).glob("*.json"):
        if codes is not None and path.stem not in codes:
            continue
        b = _load(path, {})
        out[path.stem] = [(str(r.get("date")), r.get("kind")) for r in (b.get("rows") or []) if r.get("date")]
    return out


def held_now(account):
    """바구니 장부 수량(계좌에 실제로 있는 만큼까지)."""
    book = _load(BOOK, {"orders": [], "held": {}})
    return {c: min(int(q), int(account.get(c, {}).get("quantity", 0))) for c, q in (book.get("held") or {}).items() if int(q) > 0}


def run(client, broker, day, account, total, capital, avail, quote, days, others=()):
    """15:10 바구니 하루. account: {코드: 잔고 줄} · capital: 바구니 돈(원 · 1일봉 몫의 쉬는 돈 — 연구 P4b와 같게) ·
    avail: 쓸 수 있는 현금 · others: 다른 규칙 · 엔진이 들고 있는 종목(바구니는 안 삼 · 한 종목 40% 한도 지키기) ·
    quote(code) → 지금 값 또는 None · days: 오늘까지 거래일(오래된 → 오늘).
    돌려줌: (디스코드 줄들, 오늘 주문 뒤 바구니 평가액, 오늘 바구니가 쓴 현금(산 것 − 판 것))."""
    import broker_kis
    import data_guard
    import study
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    state = _load(STATE, {"positions": {}, "last": {}})
    held = held_now(account)
    if state.get("last_day") == day:
        val = sum(q * float(account.get(c, {}).get("price") or 0) for c, q in held.items())
        return [], val, 0.0
    t0 = data_guard.prev_trading_day(client, day)
    prices = study.load_prices()
    names = {c: v["name"] for c, v in prices.items()}
    if t0 and t0 in days and days.index(t0) > 0:
        before = days[days.index(t0) - 1]
        react, inside = reactions(prices, t0, before)
        ev = todays_events(load_events(), t0, before)
    else:                                            # 어제 거래일을 못 알면 새로 사지 않고 팔 것만
        before, react, inside, ev = None, {}, set(), []
    pos = {d: i for i, d in enumerate(days)}

    def days_since(d):
        if d in pos:
            return len(days) - 1 - pos[d]
        return sum(1 for x in days if x > d)

    now_price = {}
    for code in sorted(set(held) | {c for c, _ in ev if c in inside}):
        p = quote(code)
        if p:
            now_price[code] = p
    orders, new_state, why = step(state, day, t0, days_since, ev, react, inside, held, now_price,
                                  capital=max(0.0, capital), avail=avail, names=names, others=set(others))
    book = _load(BOOK, {"orders": [], "held": {}})
    book.setdefault("held", {})
    seen = {o["key"] for o in book["orders"]}
    short, spent = [], 0.0
    for code, side, qty, reason in sorted(orders, key=lambda o: o[1] != "sell"):
        key = f"{day}:{side}:{code}"
        if key in seen:
            continue
        try:
            want = qty
            no = broker.order(code, side, qty)
            qty = int(getattr(broker, "last_qty", qty) or qty)
            status = "접수" if qty == want else f"접수 · {want:,}주 중 살 수 있는 {qty:,}주로 줄임"
            book["held"][code] = max(0, int(book["held"].get(code, 0)) + (qty if side == "buy" else -qty))
            if not book["held"][code]:
                del book["held"][code]
            spent += qty * now_price.get(code, 0) * (1 if side == "buy" else -1)
            if side == "sell" and code in state.get("positions", {}):
                p0 = state["positions"][code]
                new_state.setdefault("closed", []).append({
                    "판 날": day, "code": code, "name": names.get(code, code), "종류": p0.get("kind"), "산 날": p0.get("day"),
                    "손익": round((now_price.get(code, p0["price"]) / p0["price"] - 1) * 100, 2), "까닭": reason})
                new_state["closed"] = new_state["closed"][-500:]
        except broker_kis.BrokerError as e:
            no, status = "", f"실패 · {e}"
            if side == "buy":
                new_state["positions"].pop(code, None)
            else:
                new_state["positions"][code] = state["positions"].get(code, {})
        book["orders"].append({"key": key, "at": now.strftime("%Y-%m-%d %H:%M"), "code": code, "name": names.get(code, code),
                               "side": side, "qty": qty, "status": status, "order_no": no, "why": reason,
                               "price": now_price.get(code)})
        mark = "✅ 접수" if status.startswith("접수") else "❌ 거절"
        short.append(f"🧺 {'매수' if side == 'buy' else '매도'} {names.get(code, code)} {qty:,}주 → {mark} · {reason.split(' — ')[-1]}")
    book["orders"] = book["orders"][-5000:]
    _save(BOOK, book)
    _save(STATE, new_state)
    _save(TODAY, {"date": day, "t0": t0, "made": now.strftime("%Y-%m-%d %H:%M"), "events": [list(e) for e in ev],
                  "why": why, "orders": [{"code": c, "side": s, "qty": q, "why": r} for c, s, q, r in orders],
                  "positions": new_state.get("positions", {})})
    val = sum(int(q) * (now_price.get(c) or float(account.get(c, {}).get("price") or 0)) for c, q in book["held"].items())
    return short, val, spent
