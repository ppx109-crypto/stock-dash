"""빈칸 엔진 · 코스닥 과열 인버스 — 한투 **모의투자** 자동 주문(사용자 2026-10-03 "최종 규칙 정하고 모의투자 제작").

최종 규칙(docs/RL-INVERSE.md '최종 판' · 연구 i013 · i040 · lookahead 통과):
  엔진 켬      : 시장 폭 < 50(규칙들이 못 사는 날) · 규칙(1일봉 · 1시간봉 · 15분봉)이 계좌의 20% 미만을 쓰고 있음
  ① 급락 되돌림: KODEX 200(069500) 5일 수익 ≤ −4.5%(15:10 값) → 069500 · 익절 +3% · 손절 −3% · 20거래일 · 손절 뒤 20거래일 쉼
  ② 하락 추세  : 달러선물(138230) 20일 > +2% · 코스피200 < 20일선 → 138230
  ③ 돌리기     : 나스닥100(133690) · 달러선물(138230) · 금(132030) · 국고채10년(148070) 중 20일 수익 > 0 인 위 2개 반반
                 · 주 마지막 거래일에 다시 고름 · 모두 − 이면 현금
  코스닥 과열 인버스(엔진과 따로): 코스닥150(229200) 10일 ≥ +9.5%(15:10 값) → 251340 · 익절 +1.5% · 손절 −1.5% · 10거래일
돈: 엔진 · 인버스는 '규칙이 안 쓰는 몫'(계좌 × (1 − 규칙 쓴 몫))만 씀. 규칙이 살 돈이 모자라면 paper_trade.make_room이 엔진 것을 먼저 팖.
때: 15:10 판단(장중 연속 매매 → 시장가 즉시 체결) → 1일봉 봇(15:20 · 마감 동시호가)보다 먼저 현금을 비우거나 채움.
미래 참조: 지난 날 종가(etf-data · 어제까지) + 오늘 15:10 값만 씀.
주문은 모의투자 서버에만(paper_trade.PaperBroker) · 키 · 계좌 · 증권사 응답 본문은 찍지 않음 · 장부는 idle-live/에.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "research"))
import idle_signal  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
HOME = Path("idle-live")
STATE = HOME / "state.json"
TODAY = HOME / "today.json"
DECIDE_AT, LAST_ORDER = "1510", "1518"
DIP, DOL, INV, K200, Q150 = "069500", "138230", "251340", "069500", "229200"
ROT = idle_signal.ROT
CODES = sorted({DIP, DOL, INV, K200, Q150, *ROT})
DIP_TAKE, DIP_STOP, DIP_DAYS, DIP_COOL = 0.03, -0.03, 20, 20
INV_TAKE, INV_STOP, INV_DAYS = 0.015, -0.015, 10
NAME = {"069500": "KODEX 200", "138230": "KOSEF 미국달러선물", "251340": "KODEX 코스닥150선물인버스",
        "133690": "TIGER 미국나스닥100", "132030": "KODEX 골드선물(H)", "148070": "KOSEF 국고채10년", "229200": "KODEX 코스닥150"}
# 주 마지막 거래일을 알려고 쓰는 휴장일(평일만 · 틀려도 그 주 고르기가 하루 늦거나 한 주 밀릴 뿐)
HOLIDAYS = {"20261009", "20261225", "20261231",
            "20270101", "20270208", "20270209", "20270301", "20270505", "20270513", "20270816",
            "20270914", "20270915", "20270916", "20271004", "20271011", "20271227", "20271231"}
NOTE = "※ 연구용 자동 알림이에요. 실제 계좌에는 주문하지 않고, 한투 모의투자 계좌에만 자동 주문해요(🧪)."


# ───────────────────────── 계산(증권사 없이 시험할 수 있게) ─────────────────────────

def next_trading_day(day):
    d = date(int(day[:4]), int(day[4:6]), int(day[6:]))
    while True:
        d += timedelta(days=1)
        s = d.strftime("%Y%m%d")
        if d.weekday() < 5 and s not in HOLIDAYS:
            return s


def week_end(day):
    """오늘이 이 주의 마지막 거래일인가(다음 거래일이 다른 주)."""
    a = date(int(day[:4]), int(day[4:6]), int(day[6:])).isocalendar()[:2]
    n = next_trading_day(day)
    return date(int(n[:4]), int(n[4:6]), int(n[6:])).isocalendar()[:2] != a


def step(state, day, px, breadth, used, total, cash, held, now_price, is_week_end):
    """하루 판단. px: {코드: 종가 배열(어제까지 + 오늘 15:10 값)} · used: 규칙이 쓰는 몫(0 ~ 1) ·
    total: 계좌 총액 · cash: 현금 · held: 엔진 장부가 들고 있는 수량 {코드: 주} · now_price: 오늘 값.
    돌려줌: (주문 [(코드, 'buy'|'sell', 수량, 까닭)], 새 상태, 까닭 줄들). 연구(itools.sim · i011.run · i013)와 같게:
    판 날에는 같은 단계를 다시 사지 않음 · 손절 뒤 20거래일 쉼 · 돌리기는 주 끝에만 다시 고름 · 급락 되돌림이 켜지면 다른 엔진 단계는 쉼."""
    st = json.loads(json.dumps(state or {}))
    st.setdefault("positions", {})
    st.setdefault("cool", 0)
    pos = st["positions"]
    if st.get("last_day") != day:
        for p in pos.values():
            p["days"] = p.get("days", 0) + 1
        if st["cool"] > 0:
            st["cool"] -= 1
    sig = idle_signal.decide(px, breadth, used, at_1515=True)
    why = list(sig["까닭"])
    orders, keep, exited = [], {}, set()
    # 인버스 먼저(2026-10-03 · 현금 계좌라 엔진과 같은 돈을 겹쳐 못 씀 → 연구: 인버스 든 날 엔진 쉼이 겹쳐 쓰기와 거의 같음)
    inv_exit = None
    for code, p in pos.items():
        if p["kind"] == "인버스" and now_price.get(code) and int(held.get(code, 0)) >= 1:
            r = now_price[code] / p["price"] - 1
            if r >= INV_TAKE:
                inv_exit = f"코스닥 인버스 익절 {r * 100:+.1f}%"
            elif r <= INV_STOP:
                inv_exit = f"코스닥 인버스 손절 {r * 100:+.1f}%"
            elif p["days"] >= INV_DAYS:
                inv_exit = f"코스닥 인버스 {INV_DAYS}일 지남 {r * 100:+.1f}%"
    inv_hold = any(p["kind"] == "인버스" for p in pos.values()) and inv_exit is None
    inv_new = sig["코스닥인버스"] and not any(p["kind"] == "인버스" for p in pos.values())
    if (inv_hold or inv_new) and sig["엔진"]:
        sig = dict(sig, 엔진=False, 급락=False, 하락추세=False, 돌리기={})
        why.append("코스닥 인버스를 들거나 사는 날이라 엔진은 쉼(인버스 먼저)")
    for code, p in pos.items():
        price = now_price.get(code)
        have = int(held.get(code, 0))
        if not price or have < 1:
            continue
        r = price / p["price"] - 1
        out = None
        if p["kind"] == "급락" and (inv_hold or inv_new):
            out = f"코스닥 인버스 먼저 · 급락 되돌림 정리 {r * 100:+.1f}%"
        elif p["kind"] == "급락":
            if r >= DIP_TAKE:
                out = f"급락 되돌림 익절 {r * 100:+.1f}%"
            elif r <= DIP_STOP:
                out = f"급락 되돌림 손절 {r * 100:+.1f}%"
                st["cool"] = DIP_COOL + 1          # 연구: 손절한 날 j 뒤 j + 1 + 20일부터 다시 삼
            elif p["days"] >= DIP_DAYS:
                out = f"급락 되돌림 {DIP_DAYS}일 지남 {r * 100:+.1f}%"
        elif p["kind"] == "인버스":
            out = inv_exit
        elif p["kind"] == "달러":
            if not (sig["엔진"] and sig["하락추세"]) or sig["급락"]:
                out = "하락 추세(달러) 끝 · 엔진 " + ("켬" if sig["엔진"] else "끔")
        elif p["kind"] == "돌리기":
            if sig["엔진"] and sig["하락추세"] and not sig["급락"] and code == DOL:
                p = dict(p, kind="달러")           # 돌리기로 든 달러를 그대로 하락 추세 달러로(팔고 다시 사지 않음)
            elif not sig["엔진"] or sig["급락"] or sig["하락추세"]:
                out = "돌리기 멈춤(" + ("엔진 끔" if not sig["엔진"] else "급락 되돌림" if sig["급락"] else "하락 추세 달러") + ")"
            elif is_week_end and code not in sig["돌리기"]:
                out = "주 끝 다시 고르기에서 빠짐"
        if out:
            orders.append((code, "sell", have, out))
            exited.add(p["kind"])
        else:
            keep[code] = p
    # 돈: 엔진 · 인버스는 계좌 × (1 − 규칙 쓴 몫)만 · 실제로 쓸 수 있는 돈 = 현금 + 오늘 판 돈
    room = total * (1 - used)
    avail = (cash + sum(q * now_price.get(c, 0) for c, s, q, _ in orders if s == "sell")) * 0.97
    inv_kept = sum(int(held.get(c, 0)) * now_price.get(c, 0) for c, p in keep.items() if p["kind"] == "인버스")
    engine_room = max(0.0, room - inv_kept)
    kinds = {p["kind"] for p in keep.values()}
    buys = []
    if sig["엔진"] and "급락" not in kinds:
        if sig["급락"] and st["cool"] == 0 and "급락" not in exited:
            buys.append((DIP, 1.0, "급락", "급락 되돌림 — 코스피200 5일 급락 뒤 반등"))
        elif sig["급락"]:
            why.append("급락 되돌림 신호지만 " + (f"손절 뒤 쉬는 중(남은 {st['cool']}일)" if st["cool"] else "오늘 판 단계라 내일부터"))
        elif sig["하락추세"] and "달러" not in kinds:
            buys.append((DOL, 1.0, "달러", "하락 추세 — 달러선물"))
        elif not sig["하락추세"] and (is_week_end or "돌리기" not in kinds):
            picks = sig["돌리기"]
            for code, w in picks.items():
                if code not in keep:
                    buys.append((code, w, "돌리기", f"돌리기 — 20일 수익 위 {len(picks)}개"))
    elif sig["엔진"]:
        why.append("급락 되돌림을 들고 있어 다른 엔진 단계는 쉼")
    for code, w, kind, reason in buys:
        price = now_price.get(code)
        money = min(engine_room * w * 0.97, avail)
        qty = math.floor(money / price) if price else 0
        if qty >= 1:
            orders.append((code, "buy", qty, reason))
            avail -= qty * price
            keep[code] = {"kind": kind, "price": price, "day": day, "days": 0}
    if sig["코스닥인버스"] and "인버스" not in kinds and "인버스" not in exited:
        price = now_price.get(INV)
        bought = {c: q * now_price.get(c, 0) for c, s, q, _ in orders if s == "buy"}
        engine_after = sum(bought.values()) + sum(int(held.get(c, 0)) * now_price.get(c, 0) for c in keep if c not in bought)
        money = min(max(0.0, room - engine_after) * 0.97, avail)
        qty = math.floor(money / price) if price and money > 0 else 0
        if qty >= 1:
            orders.append((INV, "buy", qty, "코스닥 과열 인버스 — 코스닥150 10일 급등 뒤"))
            keep[INV] = {"kind": "인버스", "price": price, "day": day, "days": 0}
        else:
            why.append("코스닥 인버스 신호지만 비운 돈이 없음")
    st["positions"] = keep
    st["last_day"] = day
    return orders, st, why


# ───────────────────────── 실제 날(증권사 · 자료) ─────────────────────────

def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, body):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def history(code, day):
    """etf-data의 어제까지 종가(오늘 줄은 뺌 · 오늘 값은 15:10 현재가로 붙임)."""
    body = _load(Path("etf-data") / f"{code}.json", {})
    return [float(c) for d, c in body.get("closes", []) if c and str(d) < day]


def live_breadth(client, day):
    """1일봉 봇과 같은 길로 지금 시장 폭(%)을 셈(전날 시총 150위 지금 값 → final_group.compute)."""
    import caps
    import final_group
    import study
    import data_guard
    prices = study.load_prices()
    _, last, _ = data_guard.daily_ready(prices, data_guard.prev_trading_day(client, day))
    yest = [{"code": c, "date": v["rows"][-1][0], "price": v["rows"][-1][1]} for c, v in prices.items() if v["rows"][-1][0] == last]
    caps.tag(yest, 150)
    import broker_kis
    live = {}
    for r in yest:
        if (r.get(caps.RANK) or 999) > 150:
            continue
        try:
            q = client.quote(r["code"])
        except broker_kis.BrokerError:
            continue
        live[r["code"]] = {"name": prices[r["code"]]["name"], "rows": prices[r["code"]]["rows"] + [(day, q["price"])]}
    found = final_group.compute(live)
    return found.get("breadth") if found.get("date") == day else None


def _wait_until(hhmm):
    while datetime.now(KST).strftime("%H%M") < hhmm:
        time.sleep(15)


def run(now=None):
    import broker_kis
    import paper_trade
    from daily_live import send
    now = now or datetime.now(KST)
    day = now.strftime("%Y%m%d")
    start = os.getenv("IDLE_START", "").strip()
    state = _load(STATE, {"positions": {}, "cool": 0})
    if start and day < start:
        print(f"빈칸 엔진 모의투자는 {start}부터 시작해 오늘은 넘어갑니다.")
        return 0
    if state.get("last_day") == day:
        print("오늘은 이미 처리했습니다.")
        return 0
    if now.weekday() >= 5 or now.strftime("%H%M") > "1520":
        print("주말이거나 판단 시각이 지나 넘어갑니다.")
        return 0
    ok, why_off = paper_trade.enabled(now)
    if not ok:
        print(why_off)
        return 0
    _wait_until(DECIDE_AT)
    client = broker_kis.market()
    for _ in range(3):
        try:
            client.authorize()
            break
        except broker_kis.BrokerError as e:
            print("증권사 연결 다시 시도 ·", e)
            time.sleep(65)
    import collect_kis_intraday as CI
    if not CI.market_open_today(client, day):
        print(f"{day}은 장이 열리지 않은 날로 보여 넘어갑니다.")
        return 0
    now_price = {}
    for code in CODES:
        try:
            now_price[code] = client.quote(code)["price"]
        except broker_kis.BrokerError:
            pass
    if any(c not in now_price for c in (K200, Q150, DOL)):
        print("지수 · 달러 지금 값을 못 받아 넘어갑니다.")
        return 1
    px = {}
    for code in CODES:
        h = history(code, day)
        if code in now_price and len(h) >= 25:
            px[code] = np.array(h + [now_price[code]])
    try:
        breadth = live_breadth(client, day)
    except Exception as e:           # 시장 폭을 못 세면 새로 사지 않고 팔 것만(엔진 끔으로 봄)
        print("시장 폭 계산 실패 ·", type(e).__name__)
        breadth = None
    broker = paper_trade.PaperBroker()
    balance = broker.balance()
    book = _load(paper_trade.IDLE_BOOK, {"orders": [], "held": {}})
    book.setdefault("held", {})
    account = {p["code"]: p for p in balance.get("positions", [])}
    held = {c: min(int(q), int(account.get(c, {}).get("quantity", 0))) for c, q in book["held"].items()}
    cash = float(balance.get("cash") or 0)
    value = float(balance.get("value") or 0)
    total = cash + value
    engine_value = sum(q * float(account.get(c, {}).get("price") or now_price.get(c, 0)) for c, q in held.items())
    used = max(0.0, (value - engine_value) / total) if total > 0 else 1.0
    orders, new_state, why = step(state, day, px, breadth if breadth is not None else 100.0, used, total, cash, held,
                                  now_price, week_end(day))
    if breadth is None:
        why.insert(0, "⚠️ 시장 폭을 못 세어 엔진을 끈 것으로 봄(팔 것만)")
    late = datetime.now(KST).strftime("%H%M") > LAST_ORDER
    lines = [f"🧩 **빈칸 엔진 · {day[4:6]}-{day[6:]} 15:10 판단** (규칙 쓴 몫 {used * 100:.0f}% · 시장 폭 {breadth if breadth is not None else '?'}%)"]
    lines += ["· " + w for w in why]
    done = []
    seen = {o["key"] for o in book["orders"]}
    for code, side, qty, reason in sorted(orders, key=lambda o: o[1] != "sell"):      # 팔기 먼저
        key = f"{day}:{side}:{code}"
        if key in seen:
            continue
        if late:
            lines.append(f"🧪 {NAME.get(code, code)} {'매수' if side == 'buy' else '매도'} 건너뜀 · 작업이 늦게 돎")
            continue
        try:
            no = broker.order(code, side, qty)
            status = "접수"
            book["held"][code] = max(0, int(book["held"].get(code, 0)) + (qty if side == "buy" else -qty))
            if not book["held"][code]:
                del book["held"][code]
            done.append((code, side))
            if side == "sell" and code in state.get("positions", {}):     # 끝난 매매(대시보드 거래 내역 · 손익 합)
                p0 = state["positions"][code]
                price = now_price.get(code) or p0["price"]
                new_state.setdefault("closed", []).append({
                    "판 날": day, "code": code, "name": NAME.get(code, code), "종류": p0.get("kind"), "산 날": p0.get("day"),
                    "손익": round((price / p0["price"] - 1) * 100, 2), "칸": round(qty * price / total * 10, 1) if total else 0,
                    "까닭": reason})
                new_state["closed"] = new_state["closed"][-500:]
        except broker_kis.BrokerError as e:
            no, status = "", f"실패 · {e}"
            if side == "buy":                       # 못 산 것은 상태에서 뺌
                new_state["positions"].pop(code, None)
            else:                                   # 못 판 것은 상태에 남김
                new_state["positions"].setdefault(code, state.get("positions", {}).get(code, {}))
        book["orders"].append({"key": key, "at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "code": code,
                               "name": NAME.get(code, code), "side": side, "qty": qty, "status": status,
                               "order_no": no, "why": reason, "price": now_price.get(code)})
        lines.append(f"🧪 모의투자(빈칸 엔진) {'매수' if side == 'buy' else '매도'} · {NAME.get(code, code)}({code}) {qty}주 · 시장가 · {reason} · {status}")
        time.sleep(0.3)
    if late:
        new_state = dict(state, last_day=day)
    book["orders"] = book["orders"][-5000:]
    _save(paper_trade.IDLE_BOOK, book)
    _save(STATE, new_state)
    _save(TODAY, {"date": day, "made": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "breadth": breadth, "used": round(used, 3),
                  "why": why, "orders": [{"code": c, "side": s, "qty": q, "why": r} for c, s, q, r in orders],
                  "positions": new_state.get("positions", {})})
    if orders or new_state.get("positions"):
        send(lines + [NOTE])
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(run())
