"""1일봉 규칙 — 일봉 최고 규칙(새 82회차, docs/RULESET.md)을 실제 날에 돌려 디스코드로 알리고 한투 모의투자 계좌에 주문.

사용자 요청(2026-10-01): "모의투자 1H, 1봉기준으로 진행 · 모의투자 거래 내역은 각각 기록하여 보관".
일봉 규칙은 '신호 날 종가에 삼 · 판단도 종가'라, 장 마감 동시호가(15:20 ~ 15:30) 안에 판단하고 주문을 넣어 종가에 체결되게 함:
  15:20 — 지금 값(마감 직전)을 오늘 종가로 보고 규칙을 셈 → 팔 것 · 살 것을 정함 → 모의투자 시장가 주문(동시호가 → 종가 체결)
  15:32 — 장이 끝난 뒤 진짜 종가로 연습 계좌에 적음(연구와 같은 '종가 체결') → 디스코드
규칙(새 82회차):
  살 때 — 시총 100위 안 · (① 추세 문 또는 ② 정배열 문) + 공통 수급(전날까지 5일 외국인+ · 투신+ · 개인−) · 45일 새 목표가 내림이면 안 삼.
  크기 — 10칸 · ① 4칸 · ②인데 외국인·투신 3일 연속 4칸 · ②인데 그날 거래량 ≥ 앞 20일 가운데값 × 2 · 정배열 10일 안 3칸 · 그 밖 2칸.
         칸이 모자라면 남은 만큼 · 180일선 기울기 가파른 순 · 이미 든 종목과 60일 같이 움직임 0.6 이상이면 안 담음 · 상한가면 못 삼.
  팔 때 — ① +5% 처음 닿는 날 절반 · +13% 전량 · −5% · 10거래일 / ② 정배열 깨짐 · −10% · 한때 +8% 뒤 +1% 아래.
지금 값으로 셈하므로 마감 10분 사이 값이 바뀌면 연구와 조금 다를 수 있음(거래량도 마감 동시호가 몫이 빠져 조금 작음).
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
HOME = Path("daily-live")
STATE = HOME / "state.json"
RESULT = HOME / "today.json"
ALERTS = HOME / "alerts.json"
SLOTS = 10
POOL = 150                 # 전날 시총 150위까지 지금 값을 받아 셈(100위 안 판정 · 시장 폭에 넉넉히)
DECIDE_AT, LAST_ORDER, SETTLE_AT = "1520", "1528", "1532"
VOL_BIG, FRESH_DAYS = 2.0, 10
COST = 0.25                # 연구(lab.COST)와 같은 왕복 비용 어림값(%)
KIN = 0.6
NAME = "1일봉 매매"
NOTE = "※ 연구용 자동 알림이에요. 실제 계좌에는 주문하지 않고, 한투 모의투자 계좌에만 자동 주문해요(🧪). 실제 매매 판단은 직접 확인한 뒤에 하세요."


# ───────────────────────── 계산(자료 · 증권사 없이 시험할 수 있게) ─────────────────────────

def size_of(c):
    """새 82회차 크기."""
    if c.get("추세문"):
        return 4
    if c.get("3일연속"):
        return 4
    if (c.get("거래량비") or 0) >= VOL_BIG and (c.get("정배열일수") or 999) <= FRESH_DAYS:
        return 3
    return 2


def exit_decision(pos, close, aligned_now):
    """오늘 종가(close)로 들고 있는 매매를 볼 때: (팔 칸 수, 까닭) 또는 (0, None).
    pos: price(산 값) · kind('추세' | '정배열') · 칸 · 처음칸 · days(산 날 뒤 지난 거래일, 오늘 포함) ·
    max_close(어제까지 종가 가운데 가장 높은 값) · peak(어제까지 가장 높은 종가)."""
    now = (close / pos["price"] - 1) * 100
    if pos["kind"] == "추세":
        if now >= 13:
            return pos["칸"], f"익절 +13% 닿음(오늘 {now:+.1f}%)"
        if now <= -5:
            return pos["칸"], f"손절 −5% 닿음(오늘 {now:+.1f}%)"
        if pos["days"] >= 10:
            return pos["칸"], f"기간 청산(10거래일, 오늘 {now:+.1f}%)"
        before = (pos["max_close"] / pos["price"] - 1) * 100
        if now >= 5 and before < 5:
            return max(1, pos["처음칸"] // 2), f"절반 익절 +5% 처음 닿음(오늘 {now:+.1f}%)"
        return 0, None
    if now <= -10:
        return pos["칸"], f"손절 −10% 닿음(오늘 {now:+.1f}%)"
    peak = (max(pos["peak"], close) / pos["price"] - 1) * 100
    if peak >= 8 and now <= 1:
        return pos["칸"], f"이익 지키기(한때 {peak:+.1f}%까지 갔다가 오늘 {now:+.1f}%)"
    if aligned_now is False:
        return pos["칸"], f"추세 끝(일봉 정배열 깨짐, 오늘 {now:+.1f}%)"
    return 0, None


def decide(state, cands, now_price, aligned, rate, kin_ok):
    """오늘 팔 것 · 살 것. state는 고치지 않음.
    cands: 오늘 조건을 채운 후보(목표가 내림은 이미 뺌) — code · name · 추세문 · 3일연속 · 거래량비 · 정배열일수 · 추세 기울기.
    now_price · aligned · rate: {code: 지금 값 · 일봉 정배열 여부 · 오늘 등락률%}. kin_ok(code, held_codes) → 담아도 되나."""
    held = state.get("positions", {})
    sells, buys = [], []
    left = {}
    for code, p in held.items():
        price = now_price.get(code)
        if price is None:
            left[code] = p["칸"]
            continue
        q = dict(p, days=p.get("days", 0) + 1)
        n, why = exit_decision(q, price, aligned.get(code))
        if n and (rate.get(code) or 0) <= -29.5:
            why, n = None, 0                                    # 하한가에 붙으면 팔 수 없음(연구의 realistic과 같음)
        if n:
            sells.append({"type": "sell", "code": code, "칸": n, "why": why, "name": p["name"], "kind": p["kind"]})
        left[code] = p["칸"] - n
    free = SLOTS - sum(left.values())
    holding = [c for c, k in left.items() if k > 0]
    for c in sorted(cands, key=lambda c: -(c.get("추세 기울기") or -99)):
        code = c["code"]
        if code in held or free <= 0:
            continue
        if (rate.get(code) or 0) >= 29.5:
            continue                                            # 상한가면 종가에 못 삼
        if not kin_ok(code, holding):
            continue
        take = min(size_of(c), free)
        free -= take
        holding.append(code)
        buys.append({"type": "buy", "code": code, "칸": take, "name": c["name"], "kind": "추세" if c.get("추세문") else "정배열",
                     "why": ("① 추세 조건" if c.get("추세문") else "② 정배열 조건")
                            + (" · 외국인·투신 3일 연속" if c.get("3일연속") and not c.get("추세문") else "")
                            + (" · 거래량 터진 새 정배열" if size_of(c) == 3 else "")})
    return sells, buys


def settle(state, day, sells, buys, close):
    """진짜 종가(close)로 연습 계좌에 적음 → 체결 줄들."""
    pos_all = state.setdefault("positions", {})
    closed = state.setdefault("closed", [])
    lines = []
    sold = {x["code"]: x for x in sells}
    for code, p in list(pos_all.items()):
        c = close.get(code)
        p["days"] = p.get("days", 0) + 1
        if code in sold and c:
            x = sold[code]
            part = min(x["칸"], p["칸"])
            gain = round((c / p["price"] - 1) * 100 - COST, 2)
            closed.append({"code": code, "name": p["name"], "kind": p["kind"], "산 날": p["bought"], "판 날": day,
                           "칸": part, "산 값": p["price"], "판 값": c, "손익": gain, "까닭": x["why"]})
            lines.append(f"✅ 매도 체결 · {p['name']}({code}) · {part}칸 · 종가 {c:,.0f}원 · 손익 {gain:+.1f}%(비용 뺌) · {x['why']}")
            p["칸"] -= part
            if p["칸"] <= 0:
                del pos_all[code]
                continue
        if c:
            p["peak"] = max(p["peak"], c)
            p["max_close"] = max(p["max_close"], c)
            p["last_close"] = c
    for x in buys:
        c = close.get(x["code"])
        if not c:
            continue
        pos_all[x["code"]] = {"code": x["code"], "name": x["name"], "kind": x["kind"], "price": c, "peak": c, "max_close": c,
                              "last_close": c, "칸": x["칸"], "처음칸": x["칸"], "days": 0, "bought": day, "why": x["why"]}
        lines.append(f"✅ 매수 체결 · {x['name']}({x['code']}) · {x['칸']}칸({x['칸'] * 10}%) · 종가 {c:,.0f}원 · {x['why']}")
    state["closed"] = closed[-1000:]
    return lines


# ───────────────────────── 자료 ─────────────────────────

def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, body):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def steady3(code, day):
    import final_group
    rows = [r for r in final_group.flow_rows(code) if r.get("date", "") < day][-3:]
    return len(rows) == 3 and all((r.get("외국인") or 0) > 0 and (r.get("투신") or 0) > 0 for r in rows)


def volume_ratio(code, day, today_volume):
    """오늘 거래량 ÷ 앞 20거래일 가운데값(lab.volume_line과 같은 뜻 · 오늘 것은 마감 직전 값)."""
    body = _load(Path("volume-data") / f"{code}.json", {})
    names = body.get("칸") or []
    if "거래량" not in names or not today_volume:
        return None
    k = names.index("거래량")
    past = [row[k] for row in body.get("날") or [] if str(row[0]) < day and row[k]][-20:]
    if len(past) < 20:
        return None
    m = statistics.median(past)
    return today_volume / m if m else None


def target_cut(code, day, back_days=45):
    """45일 새 증권사 목표가(가운데 값)가 내렸으면 True(nrl.target_cut과 같음 · 전날까지 알려진 것만)."""
    import bisect
    import study
    got = study.target_timeline(code)
    if not got:
        return False
    days = [d for d, _ in got]

    def at(d):
        k = bisect.bisect_left(days, d)
        if k == 0:
            return None
        return got[k - 1][1] if days[k - 1] >= study._months_before(d, 3) else None
    then = (datetime.strptime(day, "%Y%m%d") - timedelta(days=back_days)).strftime("%Y%m%d")
    a, b = at(day), at(then)
    return bool(a and b and a["목표가"] < b["목표가"])


def send(lines):
    """디스코드로 보냄. 웹훅은 GitHub Secrets의 DISCORD_WEBHOOK_URL에만 있고 어디에도 찍지 않음."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url or not lines:
        return False
    import requests
    from notify_discord import chunks
    ok = True
    for msg in chunks(lines):
        try:
            ok = requests.post(url, json={"content": msg}, timeout=(10, 20)).status_code < 300 and ok
        except requests.RequestException:
            ok = False
    return ok


ICON = {"매수": "🟢", "절반 익절": "🟡", "익절": "🔵", "손절": "🔴", "청산": "⚪"}


def decision_lines(day, breadth, cands, sells, buys, now_price, held):
    """15:20 판단 알림 줄들(1시간봉 알림처럼 아이콘 · 종목 · 칸 · 까닭 · 지금 값)."""
    out = [f"🌇 **{NAME} · {day[4:6]}-{day[6:]} 15:20 판단** (시장 폭 {breadth}% · 조건을 채운 종목 {len(cands)}개 · "
           f"들고 있는 종목 {len(held)}개)"]
    for x in sells:
        kind = ("절반 익절" if "절반" in x["why"] else "익절" if "익절" in x["why"] or "지키기" in x["why"]
                else "손절" if "손절" in x["why"] else "청산")
        px = now_price.get(x["code"])
        out.append(f"{ICON[kind]} {kind} · {x['name']}({x['code']}) · 오늘 종가에 {x['칸']}칸 팔기"
                   + (f" (지금 약 {px:,.0f}원)" if px else "") + f" · {x['why']}")
    for x in buys:
        px = now_price.get(x["code"])
        out.append(f"🟢 매수 · {x['name']}({x['code']}) · 오늘 종가에 {x['칸']}칸({x['칸'] * 10}%) 사기"
                   + (f" (지금 약 {px:,.0f}원)" if px else "") + f" · {x['why']}")
    if not sells and not buys:
        out.append("오늘은 사고팔 것이 없어요.")
    return out


def _wait_until(hhmm):
    while datetime.now(KST).strftime("%H%M") < hhmm:
        time.sleep(15)


def run(now=None):
    import broker_kis
    import caps
    import final_group
    import lab
    import study
    now = now or datetime.now(KST)
    day = now.strftime("%Y%m%d")
    state = _load(STATE, {"positions": {}, "closed": []})
    start = os.getenv("DAILY_START", "").strip()           # 이 날(YYYYMMDD)부터 운영(사용자 결정 2026-10-01: 내일부터)
    if start and day < start:
        print(f"1일봉 매매는 {start}부터 시작해 오늘은 넘어갑니다.")
        return 0
    if state.get("last_day") == day:
        print("오늘은 이미 처리했습니다.")
        return 0
    if now.weekday() >= 5 or now.strftime("%H%M") > "1600":
        print("장이 끝난 지 오래되었거나 주말이라 넘어갑니다.")
        return 0
    _wait_until(DECIDE_AT)
    late = datetime.now(KST).strftime("%H%M") > LAST_ORDER
    client = broker_kis.market()
    for attempt in range(3):           # 접근토큰은 1분에 한 번 — 다른 작업과 겹치면 잠깐 기다렸다 다시
        try:
            client.authorize()
            break
        except broker_kis.BrokerError as e:
            print("증권사 연결 다시 시도 ·", e)
            time.sleep(65)
    import collect_kis_intraday as I
    if not I.market_open_today(client, day):
        print(f"{day}은 장이 열리지 않은 날로 보여 넘어갑니다.")
        return 0
    prices = study.load_prices()
    last = max((v["rows"][-1][0] for v in prices.values()), default="")
    if not last or last >= day:
        print("일봉 자료가 어제 것까지 있지 않아 넘어갑니다.")
        return 1
    yest = [{"code": c, "date": v["rows"][-1][0], "price": v["rows"][-1][1]} for c, v in prices.items() if v["rows"][-1][0] == last]
    caps.tag(yest, POOL)
    pool = {r["code"] for r in yest if (r.get(caps.RANK) or 999) <= POOL} | set(state.get("positions", {}))
    quotes = {}
    for code in sorted(pool):
        try:
            quotes[code] = client.quote(code)
        except broker_kis.BrokerError:
            continue
    if len(quotes) < len(pool) * 0.8:
        print(f"지금 값을 너무 적게 받아({len(quotes)}/{len(pool)}) 넘어갑니다.")
        return 1
    live = {c: {"name": prices[c]["name"], "rows": prices[c]["rows"] + [(day, quotes[c]["price"])]}
            for c in quotes if c in prices}
    calm = (_load(Path("study") / "a_group.json", {}) or {}).get("calm_edge")
    found = final_group.compute(live, calm=calm)
    if found.get("date") != day:
        print("오늘 값으로 셈하지 못했습니다.")
        return 1
    cands, cut_out = [], []
    for one in found.get("picks", []):
        code = one["code"]
        if target_cut(code, day):
            cut_out.append({"code": code, "name": one["name"], "모자란 수": 1, "가까운 갈래": one.get("갈래"),
                            "모자란 것": {"거름": ["최근 45일 사이 증권사 목표가가 내림"]}})
            continue
        cands.append({**one, "추세문": final_group.RULE_DOOR in (one.get("갈래") or []), "3일연속": steady3(code, day),
                      "거래량비": volume_ratio(code, day, (quotes.get(code) or {}).get("volume"))})
    for c in cands:
        c["칸"] = size_of(c)
    held = state.get("positions", {})
    aligned = {}
    for code in held:
        if code in live:
            form = final_group.lines_now([x for _, x in live[code]["rows"]])
            aligned[code] = bool(form and form.get("정배열"))
    steps = lab.moves(live)
    idx = {c: len(live[c]["rows"]) - 1 for c in live}

    def kin_ok(code, holding):
        row = {"code": code, "i": idx.get(code, 0)}
        return all(lab.kinship(steps, row, {"code": h, "i": idx.get(h, 0)}) < KIN for h in holding if h in idx)
    now_price = {c: q["price"] for c, q in quotes.items()}
    rate = {c: q.get("rate") for c, q in quotes.items()}
    sells, buys = decide(state, cands, now_price, aligned, rate, kin_ok)
    # 판단하자마자 알림(1시간봉 알림과 같은 꼴 · 사용자 요청 2026-10-01): 무엇을 사고팔지 · 까닭 · 지금 값
    send(decision_lines(day, found.get("breadth"), cands, sells, buys, now_price, held) + [NOTE])
    paper = []
    if (sells or buys) and not late:
        try:
            import paper_trade
            after = {"positions": {c: dict(p, 칸=p["칸"] - sum(x["칸"] for x in sells if x["code"] == c)) for c, p in held.items()}}
            paper = paper_trade.execute([dict(x, decided=day) for x in sells + buys], after, now_price, day + "1520",
                                        now=datetime.now(KST), strategy="1d")
        except Exception as e:           # 모의투자 주문이 잘못돼도 연습 계좌 · 알림은 그대로
            paper = [f"🧪 모의투자(1일봉) 주문 중 문제 · {type(e).__name__}"]
    elif (sells or buys) and late:
        paper = ["🧪 모의투자(1일봉) · 작업이 늦게 돌아 마감 동시호가에 주문하지 못했어요(연습 계좌에만 적음)."]
    _wait_until(SETTLE_AT)
    close = {}
    for code in {x["code"] for x in sells + buys} | set(held):
        try:
            close[code] = client.quote(code)["price"]
        except broker_kis.BrokerError:
            close[code] = now_price.get(code)
    fills = settle(state, day, sells, buys, close)
    state["last_day"] = day
    _save(STATE, state)
    _save(RESULT, {"date": day, "made": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "breadth": found.get("breadth"),
                   "candidates": [{k: c.get(k) for k in ("code", "name", "갈래", "추세문", "3일연속", "거래량비", "정배열일수", "칸",
                                                          "추세 기울기")} for c in cands],
                   "sells": sells, "buys": buys, "late": late,
                   # 조건이 1~2개만 모자란 종목(대시보드 '1일봉 매수 후보(충족 미달)' · 사용자 요청 2026-10-01)
                   "near": cut_out + [{k: b.get(k) for k in ("code", "name", "모자란 수", "가까운 갈래", "모자란 것")}
                                      for b in found.get("b_group", []) if b.get("모자란 수") == 1]})
    alerts = _load(ALERTS, [])
    at = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    alerts += [{"at": at, "kind": "매도" if x["type"] == "sell" else "매수", "text": f"{x['name']}({x['code']}) {x['칸']}칸 · {x['why']}"}
               for x in sells + buys]
    _save(ALERTS, alerts[-500:])
    if fills or paper:                   # 체결 알림(사고판 것이 있을 때만)
        send([f"✅ **{NAME} · 체결 · {day[4:6]}-{day[6:]} 종가** (들고 있는 종목 {len(state['positions'])}개)"] + fills + paper)
    print(f"후보 {len(cands)} · 매도 {len(sells)} · 매수 {len(buys)} · 늦음 {late}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
