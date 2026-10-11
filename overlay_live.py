"""덧붙임(MIX-0054 최종 · 레버리지 · 횡보 인버스) — 한투 **모의투자** 자동 주문(사용자 2026-10-11 "승인, 코드제작 후 검토까지 진행해줘").

연구: MIX-0054(#224 ROBUST_MIX 인정) · 운영 계산 · 구현 계약 MIX-0054-OPS(#226 인정).
국면(KODEX 200 · 069500 종가만 · 어제 장 끝까지):
  그날 판정: 종가 < 24일 단순평균이고 10일 수익 < −5%면 '하락' · 종가 > 24일선이면 '상승' · 나머지 '횡보'
  같은 그날 판정이 3일 이어져야 국면이 바뀜(시작부터 이어 셈 · 연구 regime_dev.states와 같음 · tests/fixtures/overlay_states.json)
목표(전날 국면): 상승 → 122630(KODEX 레버리지) 계좌 × 0.4 · 횡보 → 114800(KODEX 인버스) × 0.4 · 하락 → 덧붙임 없음.
맞추는 날: 전날 국면이 지난번 맞춘 국면과 다르거나 그 달 첫 맞춤이 아직이면(연구: 국면 바뀐 다음 날 · 달 첫 거래일). 그 밖의 날은 그대로.
돈(바탕 가상 계좌 계약 · MIX-0054-OPS §5-4):
  덧붙임 장부(overlay-live/state.json)의 수량 held와 자금잔액 B를 둠. 바탕 현금 = 실제 현금 + B · 바탕 NAV = 계좌 NAV − 덧붙임 평가액 + B.
  paper_trade.PaperBroker.balance()가 이 바탕 가상 계좌를 돌려줌(base_view) → 1일봉 · 바구니 · 엔진 · 계좌 흔들림 상한은 덧붙임이 없을 때와 같은 수를 봄.
  맞추는 날 B = 맞춘 뒤 덧붙임 평가액(그때 값) · 덜기 매도는 순수입만큼 B를 줄임 · 다 팔면(하락) B = 0.
  덧붙임 크기 = min(목표 몫, (바탕 현금 − 15:20 1일봉 몫 × 1.36) ÷ 바탕 NAV) × 계좌 NAV(연구 room = 바탕 현금 비율 · 빚 없음).
  바탕 봇이 사려는데 실제 현금이 모자라면(15:20 전 연속 매매) 그 매수 전에 덧붙임을 먼저 팖(yield_for · PaperBroker.order에서).
  15:10 엔진 뒤에는 15:20 1일봉 몫(daily_reserve)만큼 실제 현금이 남도록 덧붙임을 덜어 둠(prepare · 동시호가는 판 돈이 15:30에야 풀림).
때: 15:10 빈칸 엔진 뒤(같은 작업 · 연속 매매 → 시장가 즉시 체결). 연구는 종가 · 여기서는 15:1x 값(엔진과 같은 어림 · 공개).
켜기: MIX54='on'이고 MIX54_START(YYYYMMDD) 이후 · overlay-live/off 파일이 없을 때만. 끄면 새 주문 없음(든 것은 장부대로 둠).
손실 알림: 날마다 15:1x 계좌 NAV(실제 계좌) 하루 · 그달 변화가 −10% · −12%를 넘으면 디스코드 알림(사용자 한도 −15%).
주문은 모의투자 서버에만 · 키 · 계좌 · 증권사 응답 본문은 찍지 않음. 실전 계좌 없음."""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
HOME = Path("overlay-live")
STATE = HOME / "state.json"
BOOK = HOME / "paper-orders.json"
OFF = HOME / "off"
SIGNAL = "069500"
N, PERSIST, R10 = 24, 3, 0.05
TARGET = {"상승": ("122630", 0.4), "횡보": ("114800", 0.4), "하락": (None, 0.0)}
NAME = {"122630": "KODEX 레버리지", "114800": "KODEX 인버스"}
COST_ETF = 0.0005
DAY_WARN, MONTH_WARN = -0.10, -0.12
AUCTION = "1520"                       # 이 시각부터는 동시호가(판 돈이 15:30에야 풀림) → 덜기로 자리를 못 냄


# ───────────────────────── 켜기 · 장부 ─────────────────────────

def active(day):
    if os.getenv("MIX54", "").strip().lower() != "on":
        return False
    start = os.getenv("MIX54_START", "").strip()
    return bool(start) and day >= start and not OFF.exists()


def load_state():
    try:
        st = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    st.setdefault("held", {})
    st.setdefault("B", 0.0)
    return st


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def log_order(rec):
    try:
        book = json.loads(BOOK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        book = {"orders": []}
    book.setdefault("orders", []).append(rec)
    book["orders"] = book["orders"][-3000:]
    BOOK.parent.mkdir(parents=True, exist_ok=True)
    BOOK.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")


# ───────────────────────── 국면(연구 regime_dev와 같은 셈) ─────────────────────────

def closes(before=None, code=SIGNAL):
    """etf-data의 종가 [(날, 값)] · before가 있으면 그날 앞만(어제 장 끝까지)."""
    try:
        body = json.loads((Path("etf-data") / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = sorted((str(d), float(c)) for d, c in body.get("closes", []) if c)
    return [r for r in rows if before is None or r[0] < before]


def raw_state(xs, k):
    """그날 판정(버팀 전). 24일선이 아직 없으면 '횡보'(연구와 같음)."""
    if k < N - 1:
        return "횡보"
    ma = sum(xs[k - N + 1:k + 1]) / N
    r10 = xs[k] / xs[k - 10] - 1 if k >= 10 else 0.0
    if xs[k] < ma and r10 < -R10:
        return "하락"
    return "상승" if xs[k] > ma else "횡보"


def states(rows):
    """[(날, 종가)] → {날: 국면}. 같은 그날 판정이 PERSIST일 이어져야 바뀜(처음은 '횡보')."""
    xs = [x for _, x in rows]
    out, cur, run, last = {}, "횡보", 0, None
    for k, (d, _) in enumerate(rows):
        s = raw_state(xs, k)
        run = run + 1 if s == last else 1
        last = s
        if s != cur and run >= PERSIST:
            cur = s
        out[d] = cur
    return out


# ───────────────────────── 바탕 가상 계좌 ─────────────────────────

def base_view(balance, st=None):
    """실제 잔고 → 바탕 가상 잔고(덧붙임 수량 · 평가액을 빼고 현금에 B를 더함). 덧붙임이 없고 B = 0이면 그대로."""
    st = load_state() if st is None else st
    held = {str(c): int(q) for c, q in (st.get("held") or {}).items() if int(q) > 0}
    B = float(st.get("B") or 0.0)
    if not held and abs(B) < 1e-6:
        return balance
    positions, ov_value = [], 0.0
    for p in balance.get("positions", []):
        q = int(p.get("quantity") or 0)
        o = min(held.get(str(p.get("code")), 0), q)
        if o <= 0:
            positions.append(p)
            continue
        part = float(p.get("value") or 0) * o / q if q else 0.0
        ov_value += part
        if q - o > 0:
            positions.append(dict(p, quantity=q - o, value=float(p.get("value") or 0) - part))
    out = dict(balance)
    out["positions"] = positions
    out["value"] = float(balance.get("value") or 0) - ov_value
    out["cash"] = float(balance.get("cash") or 0) + B
    out["overlay"] = {"value": ov_value, "B": B, "held": held}
    return out


def target_qty(state, nav_total, cash_b, nav_b, reserve, price):
    """맞출 수량 = floor(min(목표 몫, 남는 바탕 현금 비율) × 계좌 NAV ÷ 값). (코드, 수량, 쓴 몫)."""
    code, fe = TARGET[state]
    if not code or fe <= 0 or nav_b <= 0 or not price:
        return code, 0, 0.0
    room = max(0.0, cash_b - reserve) / nav_b
    f = min(fe, room)
    return code, max(0, math.floor(f * nav_total / price)), f


def needs_rebalance(st, state, day):
    return st.get("applied") != state or st.get("rebalanced_month") != day[:6]


def other_books_held(code):
    """다른 규칙 장부가 같은 종목을 든 수량(수량 단위로 나눔 · 종목코드 통째 빼기 아님)."""
    import paper_trade as P
    n = 0
    for bk in (P.DAILY_BOOK, P.M15_BOOK, P.BOOK, P.IDLE_BOOK, P.BASKET_BOOK):
        try:
            n += int(((json.loads(Path(bk).read_text(encoding="utf-8")) or {}).get("held") or {}).get(code, 0))
        except (OSError, ValueError, TypeError):
            continue
    return n


# ───────────────────────── 자리 내주기(바탕이 먼저) ─────────────────────────

def _quote(code):
    try:
        import broker_kis
        return float(broker_kis.market().quote(code)["price"])
    except Exception:
        return None


def _acct_qty(broker, code):
    try:
        return {p["code"]: int(p["quantity"]) for p in broker.balance(raw=True).get("positions", [])}.get(code, 0)
    except Exception:
        return None


def sell_for(broker, need, now=None, why="바탕 봇에 자리 내줌", quote=_quote):
    """실제 현금이 need(원)만큼 더 필요할 때 덧붙임을 그만큼 팖. 장부(held · B)는 **확인된 체결 수량**으로만 고침
    (주문 앞뒤 실제 잔고 수량 차 · 0주 체결이면 그대로 두고 '미확인'으로 남김 → 다음 실행의 reconcile이 실제 잔고와 맞춤).
    꺼져 있으면(active 아님) 아무것도 안 함. 체결 확인된 판 금액(원)을 돌려줌."""
    now = now or datetime.now(KST)
    if need <= 0 or now.strftime("%H%M") >= AUCTION or not active(now.strftime("%Y%m%d")):
        return 0.0
    st = load_state()
    held = {c: int(q) for c, q in st["held"].items() if int(q) > 0}
    if not held:
        return 0.0
    code = next(iter(held))
    px = quote(code)
    if not px:
        return 0.0
    qty = min(held[code], math.ceil(need / (px * (1 - COST_ETF))))
    if qty < 1:
        return 0.0
    before = _acct_qty(broker, code)
    if before is None:
        return 0.0
    broker._overlay_selling = True
    try:
        no = broker.order(code, "sell", qty)
        status = "접수"
    except Exception as e:
        no, status = "", f"실패 · {type(e).__name__}"
    finally:
        broker._overlay_selling = False
    filled = 0
    if status == "접수":
        for _ in range(int(os.getenv("OVERLAY_FILL_TRIES", "5"))):
            time.sleep(float(os.getenv("PAPER_ROOM_WAIT", "2")))
            after = _acct_qty(broker, code)
            if after is None:
                continue
            filled = max(0, min(qty, before - after))
            if filled >= qty:
                break
        status = f"접수 · 체결 확인 {filled}/{qty}주" + ("" if filled == qty else " · 나머지 미확인(다음 실행에 실제 잔고와 맞춤)")
    if filled:
        held[code] -= filled
        st["held"] = {c: q for c, q in held.items() if q > 0}
        st["B"] = float(st["B"]) - filled * px * (1 - COST_ETF)
    if status.startswith("접수") and filled < qty:
        st["unconfirmed"] = {"code": code, "qty": qty - filled, "at": now.strftime("%Y-%m-%d %H:%M")}
    save_state(st)
    log_order({"key": f"{now.strftime('%Y%m%d%H%M%S')}:yield:{code}", "at": now.strftime("%Y-%m-%d %H:%M"), "code": code, "side": "sell",
               "qty": qty, "filled": filled, "status": status, "order_no": no, "why": why, "price": px})
    return filled * px


def reconcile(st, raw, quote=_quote):
    """장부 수량이 실제 잔고(다른 장부 몫 뺀 것)보다 많으면 줄이고, 사라진 수량은 판 것으로 보고 B를 순수입(지금 값)만큼 줄임."""
    acct = {p["code"]: (int(p["quantity"]), float(p.get("price") or 0)) for p in raw.get("positions", [])}
    for code, q in list(st.get("held", {}).items()):
        real = max(0, acct.get(code, (0, 0))[0] - other_books_held(code))
        if real < int(q):
            px = acct.get(code, (0, 0))[1] or quote(code) or 0.0
            st["B"] = float(st.get("B") or 0) - (int(q) - real) * px * (1 - COST_ETF)
            if real:
                st["held"][code] = real
            else:
                st["held"].pop(code)
    for code in st.get("pending", []):                # 지난 맞춤에서 잔고 확인을 못 한 종목: 실제로 더 있으면 덧붙임 몫으로(B도 그만큼 · NAV_b 그대로)
        real = max(0, acct.get(code, (0, 0))[0] - other_books_held(code))
        have = int(st["held"].get(code, 0))
        if real > have:
            px = acct.get(code, (0, 0))[1] or quote(code) or 0.0
            st["held"][code] = real
            st["B"] = float(st.get("B") or 0) + (real - have) * px
    st.pop("unconfirmed", None)
    st.pop("pending", None)
    return st


def yield_for(broker, code, qty, now=None, quote=_quote):
    """PaperBroker.order(매수) 앞에서 부름: 매수가능 수량이 모자라면 모자란 금액만큼 덧붙임을 먼저 팖(연구: ETF부터 덜기)."""
    now = now or datetime.now(KST)
    if getattr(broker, "_overlay_selling", False) or getattr(broker, "_overlay_buying", False) or now.strftime("%H%M") >= AUCTION:
        return 0.0
    if not active(now.strftime("%Y%m%d")):          # 꺼져 있으면(MIX54 off · 시작 전 · off 파일) 새 주문 없음
        return 0.0
    st = load_state()
    if not any(int(q) > 0 for q in st["held"].values()):
        return 0.0
    can = broker.buyable(code)
    if can is None or can >= qty:
        return 0.0
    px = quote(code)
    if not px:
        return 0.0
    import paper_trade as P
    return sell_for(broker, (qty - can) * px * P.MKT_MARGIN, now, quote=quote)


def prepare(broker, reserve, now=None, quote=_quote):
    """15:10 엔진 뒤: 15:20 1일봉이 살 몫(reserve · 원)만큼 실제 현금이 남게 덧붙임을 덜어 둠(연속 매매 중)."""
    now = now or datetime.now(KST)
    if reserve <= 0 or not active(now.strftime("%Y%m%d")):
        return 0.0
    import paper_trade as P
    raw = broker.balance(raw=True)
    short = reserve * P.MKT_MARGIN / 0.98 - float(raw.get("cash") or 0)        # 시장가가 묶는 1.36배 · 2% 여유까지
    return sell_for(broker, short, now, why="15:20 1일봉 몫을 비켜 둠", quote=quote) if short > 0 else 0.0


# ───────────────────────── 손실 알림 ─────────────────────────

def nav_watch(st, day, nav):
    """실제 계좌 NAV(15:1x)로 하루 · 그달 변화를 셈. (경고 줄들, 고친 st). 그달 시작 = 전달 마지막 기록(처음이면 오늘 값)."""
    lines = []
    last_day, last_nav = st.get("nav_day"), st.get("nav")
    if last_day and last_nav and last_day[:6] != day[:6]:
        st["month_start_nav"] = last_nav
    if not st.get("month_start_nav"):
        st["month_start_nav"] = nav
    if last_day and last_nav and last_day < day:
        r = nav / float(last_nav) - 1
        if r <= DAY_WARN:
            lines.append(f"⚠️ 계좌 하루 손실 {r * 100:.1f}%(15:1x 값) · 사용자 한도 −15%에 가까움")
    rm = nav / float(st["month_start_nav"]) - 1
    if rm <= MONTH_WARN:
        lines.append(f"⚠️ 계좌 그달 손실 {rm * 100:.1f}%(15:1x 값) · 사용자 한도 −15%에 가까움")
    st["nav_day"], st["nav"] = day, nav
    return lines, st


# ───────────────────────── 하루 실행(15:10 엔진 뒤) ─────────────────────────

def run(broker, client, day, reserve=0.0, now=None, quote=_quote, prev_day=None):
    """덧붙임 하루 실행. 디스코드 줄들을 돌려줌. 꺼져 있으면 빈 목록."""
    now = now or datetime.now(KST)
    if not active(day):
        return []
    st = load_state()
    if st.get("last_day") == day:
        return []
    lines = []
    raw = broker.balance(raw=True)
    st = reconcile(st, raw, quote)                   # 지난 미확인 매도 · 다른 까닭으로 줄어든 수량을 실제 잔고와 맞춤
    nav = float(raw.get("cash") or 0) + float(raw.get("value") or 0)
    warn, st = nav_watch(st, day, nav)
    lines += warn
    rows = closes(before=day)
    if prev_day is None:
        try:
            import data_guard
            prev_day = data_guard.prev_trading_day(client, day)
        except Exception:
            prev_day = None
    stale = not rows or not prev_day or rows[-1][0] != prev_day
    state = None if stale else states(rows)[rows[-1][0]]
    if stale or not needs_rebalance(st, state, day):
        save_state(st)                               # 손실 알림 기록 먼저(prepare가 장부를 다시 읽음)
        prepare(broker, reserve, now, quote)         # 맞추지 않는 날도 15:20 1일봉 몫은 비켜 둠
        st = load_state()
        st["last_day"] = day
        save_state(st)
        if stale:
            lines.append(f"⚠️ 덧붙임: 어제({prev_day or '?'}) KODEX 200 종가가 아직 없어 오늘은 맞추지 않음(자료 마지막 {rows[-1][0] if rows else '?'})")
        return lines
    view = base_view(raw, st)
    cash_b = float(view.get("cash") or 0)
    nav_b = cash_b + float(view.get("value") or 0)
    import paper_trade as P
    cur = {c: int(q) for c, q in st["held"].items() if int(q) > 0}
    code_new, fe = TARGET[state]
    px_new = quote(code_new) if code_new else None
    if code_new and not px_new:
        st["last_day"] = day
        save_state(st)
        return lines + [f"⚠️ 덧붙임: {NAME.get(code_new, code_new)} 지금 값을 못 받아 오늘은 맞추지 않음"]
    _, want, f = target_qty(state, nav, cash_b, nav_b, reserve * P.MKT_MARGIN, px_new)
    orders = []
    for c, q in cur.items():
        if c != code_new:
            orders.append((c, "sell", q))
    if code_new:
        diff = want - cur.get(code_new, 0)
        if diff < 0:
            orders.append((code_new, "sell", -diff))
        elif diff > 0:
            orders.append((code_new, "buy", diff))
    before = {p["code"]: int(p["quantity"]) for p in raw.get("positions", [])}
    done, sells = [], {}
    for c, side, q in sorted(orders, key=lambda o: o[1] != "sell"):      # 팔기 먼저(연속 매매라 판 돈이 바로 풀림)
        broker._overlay_buying = side == "buy"
        try:
            no = broker.order(c, side, q)
            q = int(getattr(broker, "last_qty", q) or q) if side == "buy" else q
            status = "접수"
            done.append((c, side, q))
            if side == "sell":
                sells[c] = q
        except Exception as e:
            no, status = "", f"실패 · {type(e).__name__}"
        finally:
            broker._overlay_buying = False
        log_order({"key": f"{day}:{side}:{c}", "at": now.strftime("%Y-%m-%d %H:%M"), "code": c, "name": NAME.get(c, c), "side": side,
                   "qty": q, "status": status, "order_no": no, "why": f"국면 {state} · 목표 몫 {f:.2f}", "price": quote(c) if c != code_new else px_new})
        lines.append(f"🧪 모의투자(덧붙임) {'매수' if side == 'buy' else '매도'} · {NAME.get(c, c)}({c}) {q:,}주 · {status}")
        time.sleep(0.3)
    # 체결 확인: 판 종목은 실제 잔고가 판 만큼 줄었는지(최대 OVERLAY_FILL_TRIES번) · 장부는 확인된 실제 수량으로만
    after = None
    for _ in range(int(os.getenv("OVERLAY_FILL_TRIES", "5"))):
        time.sleep(float(os.getenv("PAPER_ROOM_WAIT", "2")))
        try:
            after = {p["code"]: int(p["quantity"]) for p in broker.balance(raw=True).get("positions", [])}
        except Exception:
            continue
        if all(after.get(c, 0) <= before.get(c, 0) - q for c, q in sells.items()):
            break
    keep = {k: st[k] for k in ("nav_day", "nav", "month_start_nav") if k in st}
    codes = set(cur) | ({code_new} if code_new else set())
    if after is None:                                # 잔고를 못 읽음 → 추정하지 않고 맞춤 전 장부 그대로 · 다음 실행이 실제 잔고와 맞추고 다시 맞춤
        st = {"held": cur, "B": float(st.get("B") or 0), "applied": None, "rebalanced_month": st.get("rebalanced_month"),
              "last_day": day, "pending": sorted(codes), **keep}
        save_state(st)
        return lines + ["⚠️ 덧붙임: 주문 뒤 잔고를 못 읽어 장부를 그대로 두고 내일 다시 맞춤"]
    held, px = {}, {}
    for c in codes:
        real = max(0, after.get(c, 0) - other_books_held(c))
        q = real if c == code_new else min(cur.get(c, 0), real)          # 옛 종목은 못 판 잔량만 남김(덧붙임 몫 그대로)
        if q > 0:
            held[c] = q
            px[c] = px_new if c == code_new else (quote(c) or 0.0)
    left = {c: q for c, q in held.items() if c != code_new}
    complete = not left
    # B = 맞춘 뒤 덧붙임 평가액(남은 옛 종목 포함 · 그때 값) · 다 못 팔았으면 '맞춤 끝'으로 적지 않아 다음 실행에 다시 맞춤
    st = {"held": held, "B": round(sum(q * px[c] for c, q in held.items()), 2) if held else 0.0,
          "applied": state if complete else None, "rebalanced_month": day[:6] if complete else st.get("rebalanced_month"),
          "last_day": day, "signal_day": rows[-1][0], **keep}
    if left:
        st["unconfirmed"] = {"left": left, "at": now.strftime("%Y-%m-%d %H:%M")}
        lines.append("⚠️ 덧붙임: 옛 종목 " + " · ".join(f"{NAME.get(c, c)} {q:,}주" for c, q in left.items()) + " 매도가 다 체결되지 않음 → 장부에 남기고 내일 다시 맞춤")
    save_state(st)
    lines.insert(0, f"🪜 **덧붙임 {day[4:6]}-{day[6:]}** · 국면 {state}(어제 장 끝) · 목표 {NAME.get(code_new, '없음')} 몫 {f:.2f}")
    return lines
