"""계좌 전체 흔들림 상한 — 모의투자 계좌에만(연구 ACC-VOL-0007 · GPT 최종 인정 2026-10-09 · 사용자 결정 2026-10-09
"과거 좋은 성적이 나온 규칙대로 하자"). 연구 셈은 research/z086.py(Z_ACC_VOL=0.010911)와 같은 식입니다.

- 허용 비중 E = min(1, 1.0911% ÷ σ). σ = **전날까지** 20거래일 동안 '지금 든 것 전체'(주식 · ETF, 전날 종가 평가액 비중)의
  하루 수익률 표준편차. 값이 없는 날은 앞 값(수익 0). 든 종목 가운데 창 첫날 값이 없는 것이 있으면 그날은 E = 1(연구와 같음).
  1.0911% = 한 달 한도 15% ÷ 3 ÷ √21(하루로 바꾼 값).
- 사기: 15:10 바구니 · 빈칸 엔진, 장중 15분봉, 15:20 1일봉 모두 'E × 계좌 − 든 것 합'까지만 삼(room).
- 덜어내기: 15:20(1일봉 판단 직전) 든 것 합 > E × 계좌면 모든 규칙 장부의 든 것을 같은 비율로 덜어 팜(시장가 · 마감 동시호가).
- 연구와 다른 점(어림 · 공개): 비중은 그날 처음 셀 때 든 수량 × 전날 종가(연구는 전날 끝에 든 것만). 실제 값 · 체결은 모의투자 서버 몫.
끄기: ACC_CAP이 'on'이 아니거나 ACC_CAP_START(YYYYMMDD) 전이면 아무것도 안 함.
기록: acc-cap/today.json(작업마다 따로 · 저장소에 안 올림 — 여러 작업이 같은 파일을 올리다 부딪히지 않게) · acc-cap/log.json(15:20 작업만 올림 · 비율만).
판단은 전날까지 값만 씀(미래 참조 없음) · 덜어낼 금액만 15:20 지금 값(연구는 종가 — 이 차이를 log에 날마다 남김).
막힘(fail-closed · GPT #149 검토): 켜진 날 상한 셈이나 덜어내기가 실패하면 그날 **새 매수만 멈춤**(팔기는 그대로) — safe_room · block · blocked.
"""
import json
import math
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
HOME = Path("acc-cap")
TODAY = HOME / "today.json"
LOG = HOME / "log.json"
PRICES = Path("price-data")
ETF = Path("etf-data")
CAL_CODE = "069500"                     # 거래일 달력(KODEX 200 · 장이 연 날마다 값이 있음)
LOOK = 20
TARGET = float(os.getenv("ACC_CAP_TARGET", "0.010911"))


def enabled(day):
    if os.getenv("ACC_CAP", "").strip().lower() != "on":
        return False
    start = os.getenv("ACC_CAP_START", "").strip()
    return not (start and day < start)


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, body):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def series(code):
    """종목 · ETF 일봉 종가 {날짜: 값}. 주식은 price-data, ETF는 etf-data."""
    for folder in (PRICES, ETF):
        body = _load(folder / f"{code}.json", None)
        if body:
            return {str(d): float(c) for d, c in body.get("closes") or [] if c and float(c) > 0}
    return {}


def sigma(day, qty, get=series):
    """전날까지 LOOK+1 거래일 종가로 든 것 전체의 하루 수익률 σ. 돌려줌: (σ 또는 None, 까닭).
    qty: {코드: 주}. 비중 = 주 × 창 마지막 날(전날) 종가. 달력 = KODEX 200 거래일 ∪ 든 종목 거래일(그날 앞만)."""
    qty = {c: int(q) for c, q in qty.items() if int(q) > 0}
    if not qty:
        return None, "든 것 없음"
    src = {c: get(c) for c in qty}
    cal = set(get(CAL_CODE))
    for s in src.values():
        cal |= set(s)
    cal = sorted(d for d in cal if d < day)
    if len(cal) < LOOK + 1:
        return None, "달력이 짧음"
    win = cal[-(LOOK + 1):]
    seqs = {}
    for c, s in src.items():
        seq, last = [], None
        for d in win:
            last = s.get(d, last)
            seq.append(last)
        if seq[0] is None:
            return None, f"{c} 창 첫날 값 없음"
        seqs[c] = seq
    val = {c: qty[c] * seqs[c][-1] for c in qty}
    tot = sum(val.values())
    if tot <= 0:
        return None, "평가액 0"
    port = [sum(val[c] / tot * (seqs[c][j] / seqs[c][j - 1] - 1) for c in qty) for j in range(1, LOOK + 1)]
    m = sum(port) / LOOK
    sd = math.sqrt(sum((x - m) ** 2 for x in port) / (LOOK - 1))
    return sd, f"{win[0]} ~ {win[-1]} · 든 종목 {len(qty)}"


def allowed_from(sd):
    return 1.0 if not sd or sd <= 0 else min(1.0, TARGET / sd)


def positions_of(balance):
    return {str(p["code"]): int(p.get("quantity") or 0) for p in balance.get("positions", []) if int(p.get("quantity") or 0) > 0}


def today(day, balance, get=series):
    """오늘 E(하루 한 번 셈 · 처음 셀 때 든 수량 기준). acc-cap/today.json에 남김."""
    t = _load(TODAY, {})
    if t.get("date") == day and "E" in t:
        return t
    keep = {"blocked": t["blocked"]} if t.get("date") == day and t.get("blocked") else {}     # 오늘 막힌 것은 그대로 둠
    sd, why = sigma(day, positions_of(balance), get)
    t = {"date": day, "at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "E": round(allowed_from(sd), 4),
         "sigma": None if sd is None else round(sd, 6), "why": why, "target": TARGET, "trimmed_value": 0.0, "trim_done": False, **keep}
    _save(TODAY, t)
    return t


def room(balance, day, get=series):
    """오늘 더 살 수 있는 돈(원) = E × 계좌 − (든 것 − 오늘 덜어내려고 판 것). 꺼져 있으면 None(한도 없음)."""
    if not enabled(day):
        return None
    t = today(day, balance, get)
    cash = float(balance.get("cash") or 0)
    value = float(balance.get("value") or 0)
    held = max(0.0, value - float(t.get("trimmed_value") or 0))
    return max(0.0, t["E"] * (cash + value) - held)


def block(day, why):
    """오늘 새 매수를 멈춤(상한 셈 · 덜어내기 실패 때). acc-cap/today.json에 남김(작업 안에서만 · 저장소에 안 올림)."""
    t = _load(TODAY, {})
    if t.get("date") != day:
        t = {"date": day}
    t["blocked"] = why
    _save(TODAY, t)


def blocked(day):
    """켜진 날이고 오늘 막혔으면 True(새 매수 없음 · 팔기는 그대로)."""
    if not enabled(day):
        return False
    t = _load(TODAY, {})
    return t.get("date") == day and bool(t.get("blocked"))


def safe_room(balance, day, get=series):
    """room과 같되 **켜진 날 셈이 실패하거나 오늘 막혔으면 0**(fail-closed). 꺼져 있으면 None(한도 없음)."""
    if not enabled(day):
        return None
    try:
        r = room(balance, day, get)
    except Exception as e:
        block(day, f"상한 셈 실패 · {type(e).__name__}")
        print("계좌 흔들림 상한 셈 실패 → 오늘 새 매수 멈춤(팔기는 그대로) ·", type(e).__name__)
        return 0.0
    return 0.0 if blocked(day) else r


def plan_trim(balance, E, books, prices=None):
    """덜어낼 주문 [(장부 이름, 코드, 수량)]과 비율 f. books: {이름: {코드: 주}}(규칙 장부의 held).
    모든 장부의 든 것을 같은 비율 f = 1 − E × 계좌 ÷ 든 것 합으로 줄임(반올림 · 계좌에 실제 있는 수량까지)."""
    cash = float(balance.get("cash") or 0)
    value = float(balance.get("value") or 0)
    total = cash + value
    if value <= 0 or value <= E * total + 1e-6:
        return [], 0.0
    f = 1 - E * total / value
    left = positions_of(balance)
    out = []
    for name, held in books.items():
        for code, q in sorted(held.items()):
            q = min(int(q), left.get(code, 0))
            n = int(round(q * f))
            if n >= 1:
                out.append((name, code, n))
                left[code] -= n
    return out, f


def run_trim(day, now=None, broker=None):
    """15:20 덜어내기(1일봉 판단 직전). 돌려줌: 디스코드 줄들. 꺼져 있거나 이미 했으면 []."""
    import broker_kis
    import paper_trade as P
    if not enabled(day):
        return []
    ok, why = P.enabled(now)
    if not ok:
        print(why)
        return []
    now = now or datetime.now(KST)
    t0 = _load(TODAY, {})
    if t0.get("date") == day and t0.get("trim_done"):
        return []
    broker = broker or P.PaperBroker()
    balance = broker.balance()
    t = today(day, balance)
    files = {"1d": P.DAILY_BOOK, "15m": P.M15_BOOK, "1h": P.BOOK, "idle": P.IDLE_BOOK, "basket": P.BASKET_BOOK}
    books = {k: _load(v, {"orders": [], "held": {}}) for k, v in files.items()}
    for b in books.values():
        b.setdefault("orders", [])
        b.setdefault("held", {})
    plan, f = plan_trim(balance, t["E"], {k: b["held"] for k, b in books.items()})
    price = {p["code"]: float(p.get("price") or 0) for p in balance.get("positions", [])}
    cash = float(balance.get("cash") or 0)
    value = float(balance.get("value") or 0)
    # 덜어내기 직전 수량 · 현금 · 값(장 끝 record_close가 같은 날 1일봉 등 다른 체결과 섞이지 않게 · 저장소에 안 올림)
    pre = {"cash": cash, "qty": positions_of(balance), "price": price}
    lines, sold_value, orders = [], 0.0, []
    for name, code, qty in plan:
        try:
            no = broker.order(code, "sell", qty)
            status = "접수"
            b = books[name]
            b["held"][code] = max(0, int(b["held"].get(code, 0)) - qty)
            if not b["held"][code]:
                del b["held"][code]
            sold_value += qty * price.get(code, 0)
        except broker_kis.BrokerError as e:
            no, status = "", f"실패 · {e}"
        books[name]["orders"].append({"key": f"{day}:acccap:{name}:{code}", "at": now.strftime("%Y-%m-%d %H:%M"), "code": code,
                                      "side": "sell", "qty": qty, "status": status, "order_no": no, "price": price.get(code),
                                      "why": f"계좌 흔들림 상한(E {t['E']:.2f}) · 든 것을 {f * 100:.0f}% 덜어냄"})
        orders.append({"book": name, "code": code, "qty": qty, "status": status})
    for name, b in books.items():
        if any(o["book"] == name for o in orders):
            b["orders"] = b["orders"][-5000:]
            _save(files[name], b)
    for name, state_file in (("idle", P.IDLE_STATE), ("basket", P.BASKET_STATE)):     # 다 판 것은 엔진 · 바구니 상태에서도 뺌
        st = _load(state_file, None)
        if st and any(o["book"] == name for o in orders):
            for code in list(st.get("positions", {})):
                if code not in books[name]["held"]:
                    st["positions"].pop(code)
            _save(state_file, st)
    t = dict(t, trim_done=True, trimmed_value=round(sold_value, 0), trim_f=round(f, 4), trim_at=now.strftime("%Y-%m-%d %H:%M"),
             trim_orders=[[o["code"], o["qty"], price.get(o["code"])] for o in orders if o["status"].startswith("접수")],
             pre=pre)     # 이 파일은 저장소에 안 올림
    _save(TODAY, t)
    log = _load(LOG, [])
    log = [x for x in log if x.get("date") != day] + [{
        "date": day, "at": t["trim_at"], "E": t["E"], "sigma": t["sigma"], "why": t["why"],
        "held_share": round(value / (cash + value), 4) if cash + value > 0 else None,     # 금액은 적지 않고 비율만(공개 저장소)
        "trim_f": t["trim_f"], "trimmed_share": round(sold_value / (cash + value), 4) if cash + value > 0 else None,
        "orders": [{k: o[k] for k in ("book", "code", "status")} for o in orders]}]
    _save(LOG, log[-1000:])
    share = value / (cash + value) * 100 if cash + value > 0 else 0
    if plan:
        lines.append(f"🛡️ 계좌 흔들림 상한 · 허용 {t['E'] * 100:.0f}% · 든 것 {share:.0f}% → {f * 100:.0f}% 덜어냄({len(plan)}건)")
        lines += [f"🧪 모의투자(흔들림 상한) 매도 · {o['code']} {o['qty']}주 · {o['status']}" for o in orders]
    else:
        print(f"계좌 흔들림 상한 · 허용 {t['E'] * 100:.0f}% · 든 것 {share:.0f}% → 덜어낼 것 없음")
    return lines


def trim_or_block(day, now=None, broker=None):
    """15:20 덜어내기. 실패하면 오늘 새 매수를 막고 알림 줄을 돌려줌(fail-closed · 1일봉 팔기는 그대로)."""
    try:
        return run_trim(day, now, broker)
    except Exception as e:
        block(day, f"덜어내기 실패 · {type(e).__name__}")
        return [f"⚠️ 계좌 흔들림 상한 단계 문제 · {type(e).__name__} → 오늘 새 매수 멈춤(팔기는 그대로)"]


def record_close(day, broker=None):
    """15:32(장 끝난 뒤) — 같은 날 덜어내기를 연구처럼 **종가**로 셌다면 얼마였을지 log에 나란히 적음(15:20 값과의 차이 재기).
    덜어내기 직전에 남긴 수량 · 현금(today.json의 pre)에 종가를 매겨 셈 — 같은 날 1일봉 등 다른 매수 · 매도는 섞이지 않음(GPT #149).
    pre가 없는 예전 기록이면 지금 수량 + 오늘 덜어내려고 판 수량으로 어림. 비율만 적음."""
    import paper_trade as P
    if not enabled(day):
        return None
    t = _load(TODAY, {})
    if t.get("date") != day or not t.get("trim_done"):
        return None
    broker = broker or P.PaperBroker()
    b = broker.balance()
    price = {p["code"]: float(p.get("price") or 0) for p in b.get("positions", [])}      # 장 끝 값 = 종가
    pre = t.get("pre")
    if pre:
        qty = {c: int(q) for c, q in pre["qty"].items()}
        for c in qty:
            if not price.get(c):         # 오늘 다 팔려 잔고에 없으면 15:20 값으로(드묾)
                price[c] = float(pre["price"].get(c) or 0)
        held = sum(q * price.get(c, 0) for c, q in qty.items())
        total = float(pre["cash"]) + held
    else:
        qty = positions_of(b)
        for code, q, p1520 in t.get("trim_orders") or []:
            qty[code] = qty.get(code, 0) + int(q)
            if not price.get(code):
                price[code] = float(p1520 or 0)
        total = float(b.get("cash") or 0) + float(b.get("value") or 0)
        held = sum(q * price.get(c, 0) for c, q in qty.items())
    if total <= 0:
        return None
    f_close = max(0.0, 1 - t["E"] * total / held) if held > 0 else 0.0
    out = {"held_share_close": round(held / total, 4), "trim_f_close": round(f_close, 4),
           "trim_f_gap": round(float(t.get("trim_f") or 0) - f_close, 4)}
    log = _load(LOG, [])
    for x in log:
        if x.get("date") == day:
            x.update(out)
    _save(LOG, log)
    return out
