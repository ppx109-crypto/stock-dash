"""15분봉 규칙(15분봉 22회차 후보) 운영 — 사용자 2026-10-02 "2번 15m 모의도 진행해줘"(모의투자 몫 1일봉 40 · 1시간봉 40 · 15분봉 20).

연구(research/q027.py의 SGF · RKF · q_rule.exit_rule · stale90)와 같은 규칙을 장중 15분마다 돌림. 짜임은 1시간봉 운영(hourly_a)과 같음.
- 무엇을: 1시간봉과 같은 후보(전날 저녁 hourly_a make_plan이 만든 hourly-live/plan.json · 같은 후보 문).
- 언제: 그날 15분봉 EMA 5 · 20 · 60 · 120 · 180이 정배열이 된 봉 → 다음 봉 시가. 없으면 10:45 봉이 닫힌 뒤 11:00 시가.
  다만 그 봉에서 그날 +2% 넘게 올랐거나(그날 첫 봉 시가 대비) 장중 시장 흐름이 −1% 아래면 사지 않음 — 걸러진 신호는 그날 기회를 쓰지 않음
  (뒤에 다시 정배열이 되면 살 수 있음 · 연구 entry3와 같음).
- 크기 · 순서: 추세 문 · 3일 연속 4칸, 그 밖 2칸 · 추세 → 3일 연속 → 같은 봉 후보끼리 '수급 약 + 20일 수익 큼' 무리(hourly_a.order_tiers).
- 팔 때: 1시간봉과 같되 봉 수 × 4(추세 240봉 · 자리 바꾸기 28봉). 정배열 매매의 일봉 정배열 깨짐은 그날 첫 실행에서 전날 종가로 보고 09:00 시가에.
- 시장 흐름: 연구는 15분봉 160종목의 그날 수익 평균. 운영은 같은 160종목(universe top100)의 현재가 · 시가로 그 순간 값을 셈(가장 최근 봉에만 · 놓친 봉은 거르지 않음).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import hourly_a as A

KST = ZoneInfo("Asia/Seoul")
HOME = Path("m15-live")
STATE = HOME / "state.json"
ALERTS = HOME / "alerts.json"
PLAN = Path("hourly-live") / "plan.json"
SLOTS = 10
BARS = tuple(f"{h:02d}{m:02d}" for h in range(9, 16) for m in (0, 15, 30, 45) if (h, m) <= (15, 15))
NOON = "1045"
UP, MKT = 0.02, -0.01
HOLD_TREND, STALE_BARS = 240, 28
COST = 0.30
NAME = "15분봉 매매"
ICON = {"매수": "🟢", "절반 익절": "🟡", "익절": "🔵", "손절": "🔴", "청산": "⚪", "자리 바꾸기": "🔁", "못 삼": "⚫"}


def close_at(bar):
    """봉이 닫히는 시각(HHMM). 15:15 봉은 15:30(마감 동시호가 포함)."""
    h, m = int(bar[:2]), int(bar[2:]) + 15
    return f"{h + m // 60:02d}{m % 60:02d}" if bar != "1515" else "1530"


def closed_bars(now):
    hm = now.strftime("%H%M")
    return [b for b in BARS if hm >= close_at(b)]


# ───────────────────────── 계산(자료 · 증권사 없이 시험할 수 있게) ─────────────────────────

def exit_decision(pos, close, prev_closes_max):
    """15분봉 봉이 닫힌 뒤: (팔 칸 수, 까닭) 또는 (0, None) — 연구 q_rule.exit_rule(봉 수 × 4)과 같음."""
    now = (close / pos["price"] - 1) * 100
    if pos["kind"] == "추세":
        if now >= 13:
            return pos["칸"], f"익절 +13% 닿음(지금 {now:+.1f}%)"
        if now <= -5:
            return pos["칸"], f"손절 −5% 닿음(지금 {now:+.1f}%)"
        if pos["bars"] >= HOLD_TREND:
            return pos["칸"], f"기간 청산({HOLD_TREND}봉 · 약 10거래일, 지금 {now:+.1f}%)"
        before = (prev_closes_max / pos["price"] - 1) * 100 if prev_closes_max is not None else -99
        if now >= 5 and before < 5 and pos["칸"] == pos["처음칸"]:
            return max(1, pos["처음칸"] // 2), f"절반 익절 +5% 처음 닿음(지금 {now:+.1f}%)"
        return 0, None
    if now <= -10:
        return pos["칸"], f"손절 −10% 닿음(지금 {now:+.1f}%)"
    peak = (pos["peak"] / pos["price"] - 1) * 100
    if peak >= 8 and now <= 1:
        return pos["칸"], f"본전 지키기(한때 {peak:+.1f}%까지 갔다가 지금 {now:+.1f}%)"
    return 0, None


def stale(pos, close, breadth):
    return pos["bars"] >= STALE_BARS and (close / pos["price"] - 1) * 100 < 4 and (breadth if breadth is not None else 100) < 90


def day_ret(bars, bar_id):
    """그날 첫 봉 시가 대비 bar_id 봉 종가 수익(m15feat.day_ret과 같음). bars = {"t", "o", "c"}."""
    day = bar_id[:8]
    first = next((o for t, o in zip(bars["t"], bars["o"]) if t[:8] == day), None)
    if bar_id not in bars["t"] or not first:
        return None
    return bars["c"][bars["t"].index(bar_id)] / first - 1


def step(state, plan, bars, bar_id, next_open, log, market=None):
    """닫힌 15분봉 bar_id(YYYYMMDDHHMM) 하나를 처리(연구 hlab.simulate와 같은 차례). market: 이 봉의 장중 시장 흐름(없으면 거르지 않음)."""
    day, hm = bar_id[:8], bar_id[8:]
    nxt = BARS[BARS.index(hm) + 1] if hm != "1515" else None
    fill_note = "내일 09:00 시가" if nxt is None else f"{nxt[:2]}:{nxt[2:]} 시가"
    pos_all = state.setdefault("positions", {})
    pend = state.setdefault("pending", [])
    cands = {c["code"]: c for c in plan.get("candidates", [])}
    for code, p in list(pos_all.items()):
        b = bars.get(code)
        if not b or bar_id not in b["t"]:
            continue
        k = b["t"].index(bar_id)
        close = b["c"][k]
        before = p.get("max_close")
        p["bars"] = p.get("bars", 0) + 1 if p.get("last_bar") != bar_id else p.get("bars", 0)
        p["last_bar"] = bar_id
        p["peak"] = max(p["peak"], close)
        p["last_close"] = close
        if any(x["code"] == code and x["type"] == "sell" for x in pend):
            continue
        n, why = exit_decision(p, close, before)
        p["max_close"] = max(before, close) if before is not None else close
        if n:
            pend.append({"type": "sell", "code": code, "칸": n, "why": why, "decided": bar_id})
            kind = "절반 익절" if "절반" in why else ("익절" if "익절" in why else "손절" if "손절" in why else "청산")
            log(kind, f"{p['name']}({code}) · {fill_note}에 {n}칸 팔기 · {why}", {"code": code})
    seen = state.setdefault("seen", {})
    today_seen = set(seen.get(day, []))
    sigs, how, allsig = [], {}, []
    for code, c in cands.items():
        if code in today_seen:
            continue
        b = bars.get(code)
        if not b or bar_id not in b["t"]:
            continue
        k = b["t"].index(bar_id)
        al = A.aligned_series(b["c"])
        crossed = al[k] and not (k > 0 and al[k - 1])
        if not (crossed or hm == NOON):
            continue
        dr = day_ret(b, bar_id)
        if (dr is not None and dr > UP) or (market is not None and market < MKT):
            continue                      # 걸러진 신호는 그날 기회를 쓰지 않음(연구 entry3)
        today_seen.add(code)
        allsig.append(code)
        if code not in pos_all:
            sigs.append(code)
            how[code] = "15분봉 EMA 정배열이 됨" if crossed else "10:45 봉까지 정배열 없음 → 11:00"
    seen[day] = sorted(today_seen)
    for old in [d for d in seen if d < day]:
        del seen[old]
    if not sigs:
        return
    # 순서 무리는 연구(q_rule.tiers)처럼 그 봉의 신호 모두(이미 든 종목 포함)로 나눔(재현 시험 x009에서 갈린 까닭)
    tiers = A.order_tiers({c: cands[c] for c in allsig})
    sigs.sort(key=lambda c: (0 if cands[c].get("추세문") else 1, 0 if cands[c].get("3일연속") else 1, -tiers[c], A.tie(c, bar_id)))
    held = sum(p["칸"] for p in pos_all.values()) + sum(x["칸"] for x in pend if x["type"] == "buy")
    leaving = {x["code"]: x["칸"] for x in pend if x["type"] == "sell"}
    free = SLOTS - held + sum(leaving.values())
    for code in sigs:
        c = cands[code]
        need = A.size_of(c)
        if free < need:
            weak = sorted((q for q in pos_all.values() if q["code"] not in leaving
                           and stale(q, q.get("last_close", q["price"]), plan.get("breadth"))),
                          key=lambda q: q.get("last_close", q["price"]) / q["price"])
            for q in weak:
                if free >= need:
                    break
                gain = (q.get("last_close", q["price"]) / q["price"] - 1) * 100
                pend.append({"type": "sell", "code": q["code"], "칸": q["칸"], "why": f"자리 바꾸기({q['bars']}봉 · {gain:+.1f}%)", "decided": bar_id})
                leaving[q["code"]] = q["칸"]
                free += q["칸"]
                log("자리 바꾸기", f"{q['name']}({q['code']}) · {fill_note}에 팔고 자리를 {c['name']}({code})에 · {q['bars']}봉 들고 {gain:+.1f}%", {"code": q["code"]})
        if free <= 0:
            log("못 삼", f"{c['name']}({code}) · 신호가 났지만 칸이 없어 거름", {"code": code})
            continue
        take = min(need, free)
        free -= take
        pend.append({"type": "buy", "code": code, "칸": take, "decided": bar_id, "kind": "추세" if c.get("추세문") else "정배열",
                     "name": c["name"], "why": how[code]})
        price = next_open.get(code)
        at = f" (약 {price:,.0f}원)" if price else ""
        log("매수", f"{c['name']}({code}) · {fill_note}{at}에 {take}칸({take * 10}%) 사기 · "
                   f"{'추세 문' if c.get('추세문') else '정배열 문'}{' · 3일 연속' if c.get('3일연속') else ''} · {how[code]} · 순서 무리 {tiers[code]}/4",
            {"code": code})


def fill(state, bar_id, opens):
    """앞 봉에서 정한 매수 · 매도를 이 봉(bar_id) 시가로 체결(hourly_a.fill과 같음 · 비용 0.30%)."""
    pos_all = state.setdefault("positions", {})
    done, keep = [], []
    closed = state.setdefault("closed", [])
    for x in state.get("pending", []):
        price = opens.get(x["code"])
        if price is None or x["decided"] >= bar_id:
            keep.append(x)
            continue
        if x["type"] == "sell" and x["code"] in pos_all:
            p = pos_all[x["code"]]
            part = min(x["칸"], p["칸"])
            gain = (price / p["price"] - 1) * 100 - COST
            closed.append({"code": x["code"], "name": p["name"], "산 때": p["bought"], "판 때": bar_id, "칸": part,
                           "손익": round(gain, 2), "까닭": x["why"]})
            x = {**x, "name": p["name"], "손익": round(gain, 2), "칸": part}
            p["칸"] -= part
            if p["칸"] <= 0:
                del pos_all[x["code"]]
        elif x["type"] == "buy" and x["code"] not in pos_all:
            pos_all[x["code"]] = {"code": x["code"], "name": x["name"], "kind": x["kind"], "price": price, "peak": price,
                                  "칸": x["칸"], "처음칸": x["칸"], "bars": -1, "bought": bar_id, "max_close": None}
        done.append(x)
    state["pending"] = keep
    state["closed"] = closed[-300:]
    return done


def daily_breaks(state, prices_before, decided):
    """들고 있는 정배열 매매가 전 거래일 종가로 일봉 정배열이 깨졌으면 오늘 첫 봉 시가에 팖(연구: ATT[k+1] 정배열 아님 → 다음 봉)."""
    import final_group
    out = []
    for code, p in list(state.get("positions", {}).items()):
        if p["kind"] != "정배열" or any(x["code"] == code and x["type"] == "sell" for x in state.get("pending", [])):
            continue
        closes = [float(c) for d, c in (prices_before.get(code, {}).get("rows") or [])]
        shape = final_group.lines_now(closes) if closes else None
        if shape is not None and not shape.get("정배열"):
            state.setdefault("pending", []).append({"type": "sell", "code": code, "칸": p["칸"], "why": "일봉 정배열 깨짐", "decided": decided})
            out.append(code)
    return out


# ───────────────────────── 자료 · 증권사 ─────────────────────────

def history(code, day, home=Path("m15-kis")):
    """오늘(day) 앞의 한투 15분봉 {"t", "o", "c"}(연구 자료와 같은 파일)."""
    t, o, c = [], [], []
    folder = Path(home) / code
    for f in sorted(folder.glob("*.csv")) if folder.is_dir() else []:
        for ln in f.read_text(encoding="utf-8").splitlines():
            p = ln.split(",")
            if len(p) == 6 and p[0][:1].isdigit() and p[0][:8] < day:
                t.append(p[0]); o.append(float(p[1])); c.append(float(p[4]))
    return {"t": t, "o": o, "c": c}


def today_bars(client, code, day):
    """오늘 1분봉 → 15분봉 [(YYYYMMDDHHMM, o, h, l, c, v)] (collect_kis_m15.to_bars와 같은 묶음)."""
    import collect_kis_hourly as K
    import collect_kis_m15 as Q
    rows = []
    for end in K.ENDS:
        rows += K.broker_kis_rows(client, code, day, end)
    return Q.to_bars(rows, day)


def market_now(client, codes):
    """그 순간 장중 시장 흐름: 종목들의 (현재가 ÷ 오늘 시가 − 1) 평균(시가를 못 받으면 뺌). 5종목 미만이면 None."""
    vals = []
    for code in codes:
        try:
            q = client.quote(code)
        except Exception:
            continue
        o = q.get("open")
        if o:
            vals.append(q["price"] / o - 1)
    return sum(vals) / len(vals) if len(vals) >= 5 else None


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def run_live(now=None):
    import broker_kis
    import data_guard
    now = now or datetime.now(KST)
    day = now.strftime("%Y%m%d")
    plan = _load(PLAN, None)
    state = _load(STATE, {"positions": {}, "pending": []})
    if not plan or plan.get("base", "") >= day:
        print("쓸 후보(plan)가 없거나 오늘 것이 아닙니다.")
        return 0
    done_bars = closed_bars(now)
    todo = [day + b for b in done_bars if day + b > state.get("last_bar", "")]
    try:
        client = broker_kis.market()
        for attempt in range(3):           # 접근토큰은 1분에 한 번 — 1시간봉 · 수집과 겹치면 잠깐 기다렸다 다시(daily_live와 같음)
            try:
                client.authorize()
                break
            except broker_kis.BrokerError as e:
                print("증권사 연결 다시 시도 ·", e)
                import time
                time.sleep(65)
        import collect_kis_intraday as I
        if not I.market_open_today(client, day):
            print(f"{day}은 장이 열리지 않은 날로 보여 넘어갑니다.")
            return 0
        ready, why = data_guard.plan_ready(plan, data_guard.prev_trading_day(client, day))
        if not ready:
            print("자료 확인 ·", why)
            plan = {**plan, "candidates": []}
        if state.get("break_day") != day:            # 그날 첫 실행: 전날 종가로 정배열 깨짐 → 09:00 시가에 팖
            import study
            prices = study.load_prices()
            before = {c: dict(v, rows=[r for r in v["rows"] if str(r[0]) < day]) for c, v in prices.items() if c in state.get("positions", {})}
            daily_breaks(state, before, plan.get("base", day) + "1515")
            state["break_day"] = day
        codes = sorted({c["code"] for c in plan.get("candidates", [])} | set(state.get("positions", {}))
                       | {x["code"] for x in state.get("pending", [])})
        live = {c: today_bars(client, c, day) for c in codes}
        uni = json.loads(Path("hourly-data/universe.json").read_text(encoding="utf-8"))
        market = market_now(client, uni["top100"]) if todo and plan.get("candidates") else None
    except broker_kis.BrokerError as e:
        print("증권사 조회 실패 ·", e)
        return 1
    bars = {}
    for c in codes:
        h = history(c, day)
        for row in live.get(c, []):
            h["t"].append(row[0]); h["o"].append(row[1]); h["c"].append(row[4])
        bars[c] = h
    opens = {c: {row[0]: row[1] for row in live.get(c, [])} for c in codes}
    items = []
    log = lambda kind, text, extra: items.append((kind, text, extra))
    filled = []
    for bar_id in todo:
        px = {c: opens[c].get(bar_id) for c in codes}
        filled.append((bar_id, fill(state, bar_id, px), px))
        closed = {c: {"t": [x for x in bars[c]["t"] if x <= bar_id], "o": bars[c]["o"][:len([x for x in bars[c]["t"] if x <= bar_id])],
                      "c": bars[c]["c"][:len([x for x in bars[c]["t"] if x <= bar_id])]} for c in codes}
        hm = bar_id[8:]
        nxt = BARS[BARS.index(hm) + 1] if hm != "1515" else None
        next_open = {c: (opens[c].get(day + nxt) if nxt else None) for c in codes}
        step(state, plan, closed, bar_id, next_open, log, market=market if bar_id == todo[-1] else None)
        state["last_bar"] = bar_id
    cur = [b for b in BARS if b not in done_bars]
    first_open = bool(cur) and not todo and cur[0] == "0900" and any(x["decided"] < day + "0900" for x in state.get("pending", []))
    if cur and (todo or first_open):
        px = {c: opens[c].get(day + cur[0]) for c in codes}
        filled.append((day + cur[0], fill(state, day + cur[0], px), px))
    _save(STATE, state)
    paper = []
    if os.getenv("M15_PAPER", "").strip().lower() == "on":
        try:
            import paper_trade
            for bar_id, done, px in filled:
                if done:
                    paper += paper_trade.execute(done, state, px, bar_id, now=now, strategy="15m")
        except Exception as e:
            paper = [f"🧪 모의투자(15분봉) 주문 중 문제 · {type(e).__name__}"]
    alerts = _load(ALERTS, [])
    at = now.strftime("%Y-%m-%d %H:%M")
    alerts += [{"at": at, "kind": k, "text": t} for k, t, _ in items]
    _save(ALERTS, alerts[-500:])
    lines = [f"⏱️ **{NAME} · {day[4:6]}-{day[6:]} {now.strftime('%H:%M')}**"] + [f"{ICON.get(k, '•')} {k} · {t}" for k, t, _ in items] + paper
    if items or paper:
        A.send(lines + [A.NOTE_PAPER])
    print(f"처리한 봉 {todo} · 알림 {len(items)}건 · 들고 있는 종목 {len(state.get('positions', {}))}개")
    return 0


NEAR_NOW = HOME / "near-now.json"     # 장중 15분마다 다시 센 후보 · 충족 미달(대시보드 · 사용자 요청 2026-10-02 "실시간 반영")


if __name__ == "__main__":
    code = run_live()
    try:                   # 보기용이라 실패해도 매매 실행 결과는 그대로(1시간봉 실행의 매시 셈과 같은 셈 · 더 자주)
        A.refresh_near(out=NEAR_NOW)
    except Exception as e:
        print("후보 다시 세기 실패 ·", type(e).__name__)
    sys.exit(code)
