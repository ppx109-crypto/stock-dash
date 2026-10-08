"""ETF-RULE-PACK-0001 · 빈칸 엔진 + 코스닥 과열 인버스 순수 판정기(연구용 · 독립 파일).

출처: PR #36 고정 head `841b657e`의 research/idle_signal.py(`_ret` · `decide` · ROT)와 idle_live.py(상수 · `inv_take` ·
`next_trading_day` · `week_end` · `step`)를 **상수 · 분기 · 우선순위 · 수량 계산 그대로** 옮김. 바꾼 것은
`idle_signal.decide` 호출을 이 파일의 `decide`로 바꾼 것뿐입니다. 증권사 · 키 · 통신 · 파일 쓰기 · 실행 흐름은 없습니다.

`evaluate(snapshot, state)`는 그 위에 얹은 **연구 입력 검증 계약**입니다(contracts.json). 입력 출처가 없거나
available_at > decision_at이면 UNKNOWN_DATA로 판정 자체를 내지 않습니다. 순수 신호 동작(`decide` · `step`)은 바꾸지 않습니다.
돌려주는 signal_intents는 주문도 체결도 아니며, proposed_state는 '접수 그대로(ASIS) 제안 상태'라 확정 원장에 바로 넣지 않습니다.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta

import numpy as np

# ───────── research/idle_signal.py(841b657e) 그대로 ─────────
ROT = ("133690", "138230", "132030", "148070")


def _ret(a, n):
    return a[-1] / a[-1 - n] - 1 if len(a) > n and a[-1 - n] > 0 else float("nan")


def decide(px, breadth, used, at_1515=False, mood=None):
    """px: {코드: 종가 배열(오래된 → 오늘)} · breadth: 오늘 시장 폭(%) · used: 1일봉이 쓰는 몫(0 ~ 1).
    돌려줌: {'엔진': bool, '급락': bool, '하락추세': bool, '돌리기': {코드: 몫}, '코스닥인버스': bool, '까닭': [글]}"""
    k, q, dol = (np.asarray(px[c], float) for c in ("069500", "229200", "138230"))
    why = []
    engine = used < 0.2 and breadth < 50
    why.append(f"규칙 쓴 몫 {used * 100:.0f}% · 시장 폭 {breadth:.0f} → 엔진 "
               + ("켬" if engine else "끔(" + " · ".join(x for x, bad in (("쓴 몫 20% 넘음", used >= 0.2), ("시장 폭 50 이상", breadth >= 50)) if bad) + ")"))
    dip_th, q_th = (-0.045, 0.095) if at_1515 else (-0.05, 0.10)
    r5 = _ret(k, 5)
    dip = breadth < 50 and r5 <= dip_th          # 2026-10-04: 쓴 몫 20% 조건 없이(연구 i013과 같게 · 돈은 남은 몫만)
    why.append(f"코스피 5일 {r5 * 100:+.1f}% · 시장 폭 {breadth:.0f} → 급락 되돌림 {'예' if dip else '아니오'}")
    ma20 = k[-20:].mean() if len(k) >= 20 else float("nan")
    d20 = _ret(dol, 20)
    down = engine and not dip and d20 > 0.02 and k[-1] < ma20
    why.append(f"원 · 달러 20일 {d20 * 100:+.1f}% · 코스피 {'<' if k[-1] < ma20 else '≥'} 20일선 → 하락 추세(달러) {'예' if down else '아니오'}")
    rot = {}
    if engine and not dip and not down:
        sc = sorted(((_ret(np.asarray(px[c], float), 20), c) for c in ROT if c in px), reverse=True)
        top = [c for r, c in sc if r == r and r > 0][:2]
        rot = {c: 1 / 2 for c in top} if len(top) == 2 else ({top[0]: 0.5} if top else {})
        why.append("돌리기 20일: " + " · ".join(f"{c} {r * 100:+.1f}%" for r, c in sc) + f" → {', '.join(rot) or '현금(모두 −)'}")
    q10 = _ret(q, 10)
    qinv = q10 >= q_th
    why.append(f"코스닥150 10일 {q10 * 100:+.1f}% → 코스닥 인버스 {'예' if qinv else '아니오'}")
    mood_buy = bool(engine and mood is not None and mood == mood and mood >= 70)
    if mood is not None:
        why.append(f"(후보) 시장 분위기 점수 {mood:.0f} → KODEX 200 {'사기' if mood_buy else '아님'}")
    return {"엔진": engine, "급락": dip, "하락추세": down, "돌리기": rot, "코스닥인버스": qinv, "분위기사기": mood_buy, "까닭": why}


# ───────── idle_live.py(841b657e) 상수 · 순수 함수 그대로 ─────────
DECIDE_AT, LAST_ORDER = "1510", "1518"
DIP, DOL, INV, K200, Q150 = "069500", "138230", "251340", "069500", "229200"
CODES = sorted({DIP, DOL, INV, K200, Q150, *ROT})
DIP_TAKE, DIP_STOP, DIP_DAYS, DIP_COOL = 0.03, -0.03, 20, 20
DIP_ON = False          # 급락 되돌림 새로 사기(2026-10-04 사용자 결정으로 끔)
INV_TAKE, INV_STOP, INV_DAYS = 0.015, -0.015, 10          # INV_TAKE = 익절 바닥 · 폭을 못 잴 때 쓰는 값
INV_TAKE_K, INV_TAKE_HI, INV_SIG_N = 0.25, 0.025, 60     # 익절 = clip(0.25 × σ60 × √10, 1.5%, 2.5%)(RNA 26라운드 D11b)
HOLIDAYS = {"20261005", "20261009", "20261225", "20261231",          # 원본 그대로(evaluate는 외부 달력 입력 is_week_end를 씀)
            "20270101", "20270208", "20270209", "20270301", "20270505", "20270513", "20270816",
            "20270914", "20270915", "20270916", "20271004", "20271011", "20271227", "20271231"}


def inv_take(q_closes):
    """코스닥 인버스 익절 폭(D11b): 코스닥150 **어제까지** 종가의 앞 60일 하루 등락 표준편차 × √10 × 0.25를 1.5 ~ 2.5%로 묶음.
    q_closes = 오래된 → 오늘(마지막 값은 오늘 15:10 현재가라 빼고 잼 · 미래 참조 없음). 자료가 모자라면 1.5%."""
    c = np.asarray(q_closes, float)[:-1]
    if len(c) < INV_SIG_N + 1 or not np.all(np.isfinite(c[-(INV_SIG_N + 1):])):
        return INV_TAKE
    r = c[-INV_SIG_N:] / c[-(INV_SIG_N + 1):-1] - 1
    return float(np.clip(np.std(r) * math.sqrt(10) * INV_TAKE_K, INV_TAKE, INV_TAKE_HI))


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


def step(state, day, px, breadth, used, total, cash, held, now_price, is_week_end, reserve=0.0):
    """하루 판단(원본 idle_live.step과 같은 몸통). 돌려줌: (주문 [(코드, 'buy'|'sell', 수량, 까닭)], 새 상태, 까닭 줄들)."""
    st = json.loads(json.dumps(state or {}))
    st.setdefault("positions", {})
    st.setdefault("cool", 0)
    pos = st["positions"]
    if st.get("last_day") != day:
        for p in pos.values():
            p["days"] = p.get("days", 0) + 1
        if st["cool"] > 0:
            st["cool"] -= 1
    sig = decide(px, breadth, used, at_1515=True)
    why = list(sig["까닭"])
    if not DIP_ON:
        sig = dict(sig, 급락=False)
        why = [w.split(" → 급락 되돌림")[0] + " (급락 되돌림은 2026-10-04부터 안 씀)" if "→ 급락 되돌림" in w else w for w in why]
    orders, keep, exited = [], {}, set()
    inv_exit = None
    for code, p in pos.items():
        if p["kind"] == "인버스" and now_price.get(code) and int(held.get(code, 0)) >= 1:
            r = now_price[code] / p["price"] - 1
            take = float(p.get("take") or INV_TAKE)
            if r >= take:
                inv_exit = f"코스닥 인버스 익절 {r * 100:+.1f}%(익절 폭 {take * 100:.1f}%)"
            elif r <= INV_STOP:
                inv_exit = f"코스닥 인버스 손절 {r * 100:+.1f}%"
            elif p["days"] >= INV_DAYS:
                inv_exit = f"코스닥 인버스 {INV_DAYS}일 지남 {r * 100:+.1f}%"
    inv_hold = any(p["kind"] == "인버스" for p in pos.values()) and inv_exit is None
    inv_new = sig["코스닥인버스"] and not any(p["kind"] == "인버스" for p in pos.values())
    if (inv_hold or inv_new) and (sig["엔진"] or sig["급락"]):
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
                st["cool"] = DIP_COOL + 1
            elif p["days"] >= DIP_DAYS:
                out = f"급락 되돌림 {DIP_DAYS}일 지남 {r * 100:+.1f}%"
        elif p["kind"] == "인버스":
            out = inv_exit
        elif p["kind"] == "달러":
            if not (sig["엔진"] and sig["하락추세"]) or sig["급락"]:
                out = "하락 추세(달러) 끝 · 엔진 " + ("켬" if sig["엔진"] else "끔")
        elif p["kind"] == "돌리기":
            if sig["엔진"] and sig["하락추세"] and not sig["급락"] and code == DOL:
                p = dict(p, kind="달러")
            elif not sig["엔진"] or sig["급락"] or sig["하락추세"]:
                out = "돌리기 멈춤(" + ("엔진 끔" if not sig["엔진"] else "급락 되돌림" if sig["급락"] else "하락 추세 달러") + ")"
            elif is_week_end and code not in sig["돌리기"]:
                out = "주 끝 다시 고르기에서 빠짐"
        if out:
            orders.append((code, "sell", have, out))
            exited.add(p["kind"])
        else:
            keep[code] = p
    room = max(0.0, total * (1 - used) - reserve)
    avail = (cash + sum(q * now_price.get(c, 0) for c, s, q, _ in orders if s == "sell")) * 0.97
    inv_kept = sum(int(held.get(c, 0)) * now_price.get(c, 0) for c, p in keep.items() if p["kind"] == "인버스")
    engine_room = max(0.0, room - inv_kept)
    kinds = {p["kind"] for p in keep.values()}
    buys = []
    if sig["급락"] and "급락" not in kinds:
        if st["cool"] == 0 and "급락" not in exited:
            buys.append((DIP, 1.0, "급락", "급락 되돌림 — 코스피200 5일 급락 뒤 반등"))
        else:
            why.append("급락 되돌림 신호지만 " + (f"손절 뒤 쉬는 중(남은 {st['cool']}일)" if st["cool"] else "오늘 판 단계라 내일부터"))
    elif sig["엔진"] and "급락" not in kinds:
        if sig["하락추세"] and "달러" not in kinds:
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
            take = inv_take(px[Q150]) if Q150 in px else INV_TAKE
            orders.append((INV, "buy", qty, f"코스닥 과열 인버스 — 코스닥150 10일 급등 뒤 · 익절 +{take * 100:.1f}% · 손절 −1.5%"))
            keep[INV] = {"kind": "인버스", "price": price, "day": day, "days": 0, "take": round(take, 5)}
        else:
            why.append("코스닥 인버스 신호지만 비운 돈이 없음")
    st["positions"] = keep
    st["last_day"] = day
    return orders, st, why


# ───────── 연구 입력 검증 계약(새로 얹은 부분 · 원 동작 불변) ─────────
REQUIRED = ("px", "breadth", "used", "total", "cash", "held", "now_price", "is_week_end")
OPTIONAL = ("reserve",)
PX_CODES = ("069500", "229200", "138230") + ROT          # decide가 읽는 코드(ROT는 있는 것만 씀 · 원본과 같음)
MEASURES = ("CONFIRMED_BROKER_SNAPSHOT", "LEDGER_ASIS_ACCEPTED", "RESEARCH_SIMULATION", "SYNTHETIC")


def _ts(s):
    t = datetime.fromisoformat(str(s))
    if t.tzinfo is None:
        raise ValueError("시간대 없음")
    return t


def check_inputs(snapshot):
    """돌려줌: (값 dict, missing_inputs 목록). 하나라도 있으면 UNKNOWN_DATA."""
    miss, vals = [], {}
    try:
        dec = _ts(snapshot["decision_at"])
        day = str(snapshot["day"])
        if dec.astimezone(_ts("2026-01-01T00:00:00+09:00").tzinfo).strftime("%Y%m%d") != day:
            miss.append("day: decision_at(KST) 날짜와 다름")
    except (KeyError, TypeError, ValueError):
        return {}, ["decision_at/day: 없음 또는 형식 오류(KST ISO 시간대 필요)"]
    inputs = snapshot.get("inputs") or {}
    for name in REQUIRED + OPTIONAL:
        x = inputs.get(name)
        if x is None:
            if name in REQUIRED:
                miss.append(f"{name}: 없음")
            continue
        if not str(x.get("provenance") or "").strip():
            miss.append(f"{name}: provenance 없음")
        try:
            av, asof = _ts(x["available_at"]), _ts(x["as_of"])
            if av > dec:
                miss.append(f"{name}: available_at > decision_at(미래 입력)")
            if asof > dec:
                miss.append(f"{name}: as_of > decision_at")
        except (KeyError, TypeError, ValueError):
            miss.append(f"{name}: as_of/available_at 없음 또는 형식 오류")
        if name in ("total", "cash", "held") and x.get("measure") not in MEASURES:
            miss.append(f"{name}: measure 없음({'/'.join(MEASURES)})")
        vals[name] = x.get("value")
    px = vals.get("px")
    if isinstance(px, dict):
        out = {}
        for c in PX_CODES:
            e = px.get(c)
            if e is None:
                if c in ("069500", "229200", "138230"):
                    miss.append(f"px.{c}: 없음")
                continue
            if str(e.get("last_date")) != day:
                miss.append(f"px.{c}: last_date가 판단일이 아님(어제까지 + 당일 15:10 값이어야 함)")
            out[c] = e.get("closes")
        vals["px"] = out
    elif "px" in vals:
        miss.append("px: 형식 오류")
    return vals, miss


def evaluate(snapshot, state):
    """연구 계약. 돌려줌: {status, signal_intents, proposed_state, proposed_state_kind, reasons, missing_inputs, measures}."""
    vals, miss = check_inputs(snapshot)
    base = {"status": "UNKNOWN_DATA", "signal_intents": [], "proposed_state": None,
            "proposed_state_kind": "ASIS_PROPOSAL_NOT_FILL_CONFIRMED", "reasons": [], "missing_inputs": miss,
            "measures": {k: ((snapshot.get("inputs") or {}).get(k) or {}).get("measure") for k in ("total", "cash", "held")}}
    if miss:
        base["reasons"] = ["입력 검증 실패 — 판정을 내지 않음(신규 매수 · 매도 의도 모두 없음)"]
        return base
    orders, st, why = step(state, str(snapshot["day"]), vals["px"], vals["breadth"], vals["used"], vals["total"], vals["cash"],
                           vals["held"], vals["now_price"], vals["is_week_end"], vals.get("reserve") or 0.0)
    base.update(status="OK", proposed_state=st, reasons=why,
                signal_intents=[{"code": c, "side": s, "qty": q, "reason": r, "kind": "SIGNAL_INTENT_NOT_ORDER_NOT_FILL"}
                                for c, s, q, r in orders])
    return base
