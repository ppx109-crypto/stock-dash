"""1시간봉 A그룹 — 연구 90회차 최종 규칙(자리 바꾸기 폭<90 + 같은 봉 후보 순서)을 실제 날에 돌려 디스코드로 알립니다.

주문은 넣지 않습니다(증권사 연결은 조회 전용). 10칸 연습 계좌를 따라가며 '살 때 · 팔 때'를 알려 줄 뿐입니다.

두 가지로 돕니다.
  python hourly_a.py plan   — 장 마감 뒤(일봉 A그룹 계산 다음): 내일의 1시간봉 A그룹 후보를 만들고,
                               정배열이 깨진 보유 종목은 '내일 09:00 시가 청산'을 알립니다.
  python hourly_a.py live   — 장중 1시간마다(10:01 · 11:01 · 12:01 · 13:01 · 14:01 · 15:31): 방금 닫힌 1시간봉으로
                               매수 · 자리 바꾸기 · 절반 익절 · 익절 · 손절 · 본전 지키기 · 기간 청산을 판단해 알립니다.

규칙(docs/RULESET-1H.md · docs/BEST-RULES.md, 연구 3 · 53 · 90회차):
  무엇을 — 전 거래일 일봉 재료: 추세 문 또는 정배열 문(시장 폭 50% 이상 · 선 간격 19~53%) + 수급(외국인+ · 투신+ · 개인−, 5일) · 시총 100위 안.
  언제   — 그날 1시간봉 EMA 5 · 20 · 60 · 120 · 180이 정배열이 **된** 봉이 닫히면 다음 봉 시가, 11시 봉까지 없으면 12:00 시가.
  크기   — 10칸 · 추세 문 또는 외국인 · 투신 3일 연속이면 4칸, 아니면 2칸.
  순서   — 같은 봉에 후보가 여럿이면 추세 문 → 3일 연속 → 같은 봉 후보끼리 '외국인+투신 5일 수급이 약하고 20일 수익이 큰' 무리.
  자리 바꾸기 — 칸이 모자라면 7봉 넘게 들고 +4% 못 간 매매(전 거래일 시장 폭 90% 미만)를 손익 나쁜 것부터 팔고 삼.
  팔기   — 추세 문: +5% 처음 닿으면 절반 · +13% 전량 · −5% · 60봉 / 정배열 문: −10% · +8% 닿은 뒤 +1% 아래 · 일봉 정배열이 깨지면.
           모두 봉이 닫힌 뒤 판단 → 다음 봉 시가(마지막 봉이면 다음 날 09:00 시가).
1시간봉은 09 · 10 · 11 · 12 · 13 · 14시 봉(14시 봉은 15:30 마감까지 — 연구의 야후 봉과 같은 모양).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
HOME = Path("hourly-live")
PLAN = HOME / "plan.json"
STATE = HOME / "state.json"
ALERTS = HOME / "alerts.json"
SLOTS = 10
EMA_A = (5, 20, 60, 120, 180)
HOURS = ("09", "10", "11", "12", "13", "14")
CLOSE_AT = {"09": "1000", "10": "1100", "11": "1200", "12": "1300", "13": "1400", "14": "1530"}
NOTE_PLAIN = "※ 연구용 자동 알림이에요(주문은 넣지 않아요). 매매 판단은 직접 확인한 뒤에 하세요."
NOTE_PAPER = "※ 연구용 자동 알림이에요. 실제 계좌에는 주문하지 않고, 한투 모의투자 계좌에만 자동 주문해요(🧪). 실제 매매 판단은 직접 확인한 뒤에 하세요."
NOTE = NOTE_PLAIN


# ───────────────────────── 계산(자료 · 증권사 없이 시험할 수 있게) ─────────────────────────

def ema(values, span):
    """지수이동평균. 처음 span개는 None(rna.ema와 같은 뜻 — 아직 믿지 않음)."""
    out, k, prev = [], 2.0 / (span + 1), None
    for i, v in enumerate(values):
        prev = v if prev is None else prev + k * (v - prev)
        out.append(prev if i >= span else None)
    return out


def aligned_series(closes):
    """봉마다 EMA 5 > 20 > 60 > 120 > 180이면 True(닫힌 봉까지의 값만)."""
    lines = [ema(closes, s) for s in EMA_A]
    out = []
    for i in range(len(closes)):
        vals = [line[i] for line in lines]
        out.append(all(v is not None for v in vals) and all(a > b for a, b in zip(vals, vals[1:])))
    return out


def order_tiers(cands):
    """같은 봉 후보끼리: 수급 세기(약할수록 좋음) · 20일 수익(클수록 좋음)을 세 무리(0 · 1 · 2)로 나눠 더함(0 ~ 4).
    cands = {code: {"flow5": 값 또는 None, "r20": 값 또는 None}}. 후보가 하나면 가운데(2)."""
    codes = sorted(cands)
    if len(codes) <= 1:
        return {c: 2 for c in codes}
    tot = {c: 0 for c in codes}
    for key, good_high in (("flow5", False), ("r20", True)):
        vals = [cands[c].get(key) for c in codes]
        known = sorted(v for v in vals if v is not None)
        mid = known[len(known) // 2] if known else 0.0
        vals = [mid if v is None else v for v in vals]
        order = sorted(range(len(codes)), key=lambda i: (vals[i], codes[i]))
        rank = {codes[i]: r for r, i in enumerate(order)}
        for c in codes:
            q = rank[c] / (len(codes) - 1)
            if not good_high:
                q = 1 - q
            tot[c] += min(int(q * 3), 2)
    return tot


def tie(code, bar):
    """같은 무리 안에서 쓸 흔들기(연구의 무작위 대신, 날마다 달라지되 다시 돌려도 같은 값)."""
    return hashlib.sha256(f"{code}|{bar}".encode()).hexdigest()


def size_of(c):
    return 4 if c.get("추세문") or c.get("3일연속") else 2


def exit_decision(pos, close, prev_closes_max):
    """봉이 닫힌 뒤 들고 있는 매매를 볼 때: (팔 칸 수, 까닭) 또는 (0, None). 정배열 깨짐은 저녁(plan)에서 봄.
    pos: price(산 값) · peak(산 뒤 가장 높은 종가, 이 봉 포함) · 칸 · 처음칸 · bars(산 봉부터 센 봉 수, 이 봉까지) · kind."""
    now = (close / pos["price"] - 1) * 100
    if pos["kind"] == "추세":
        if now >= 13:
            return pos["칸"], f"익절 +13% 닿음(지금 {now:+.1f}%)"
        if now <= -5:
            return pos["칸"], f"손절 −5% 닿음(지금 {now:+.1f}%)"
        if pos["bars"] >= 60:
            return pos["칸"], f"기간 청산(60봉 · 약 10거래일, 지금 {now:+.1f}%)"
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
    """자리 바꾸기로 비킬 만한가: 7봉 넘게 들고 +4% 못 감 · 전 거래일 시장 폭 90% 미만."""
    return pos["bars"] >= 7 and (close / pos["price"] - 1) * 100 < 4 and (breadth if breadth is not None else 100) < 90


def step(state, plan, bars, bar_id, next_open, log):
    """닫힌 봉 bar_id(YYYYMMDDHH) 하나를 처리합니다(연구 hlab.simulate와 같은 차례).
    bars: {code: {"t": [...], "c": [...]}} — bar_id까지의 닫힌 봉(오늘 것 포함).
    next_open: {code: 다음 봉 시가 또는 None(아직 모름 · 마지막 봉)} — 알림 문구와 체결 기록에 씀.
    log(kind, text, extra) — 알림을 남김. state를 고쳐 씀."""
    day, hh = bar_id[:8], bar_id[8:]
    fill_note = "내일 09:00 시가" if hh == "14" else f"{int(hh) + 1:02d}:00 시가"
    pos_all = state.setdefault("positions", {})
    pend = state.setdefault("pending", [])
    cands = {c["code"]: c for c in plan.get("candidates", [])}
    # ① 들고 있는 매매: 봉 수 · 가장 높은 종가를 올리고 팔지 판단
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
    # ② 새 매수: 그날 첫 신호(1시간봉 정배열이 된 봉, 없으면 11시 봉) · 이미 들었거나 그날 본 종목은 뺌
    # 신호는 들고 있는지와 상관없이 셈(연구와 같음): 그날 처음 신호가 난 종목은 그날 다시 보지 않음. 11시 봉이 지나면 모두 본 것.
    seen = state.setdefault("seen", {})
    today_seen = set(seen.get(day, []))
    sigs, how = [], {}
    for code, c in cands.items():
        if code in today_seen:
            continue
        b = bars.get(code)
        if not b or bar_id not in b["t"]:
            continue
        k = b["t"].index(bar_id)
        al = aligned_series(b["c"])
        crossed = al[k] and not (k > 0 and al[k - 1])
        if crossed or hh == "11":
            today_seen.add(code)
            if code not in pos_all:
                sigs.append(code)
                how[code] = "1시간봉 EMA 정배열이 됨" if crossed else "11시 봉까지 정배열 없음 → 12시"
    seen[day] = sorted(today_seen)
    for old in [d for d in seen if d < day]:
        del seen[old]
    if not sigs:
        return
    tiers = order_tiers({c: cands[c] for c in sigs})
    sigs.sort(key=lambda c: (0 if cands[c].get("추세문") else 1, 0 if cands[c].get("3일연속") else 1, -tiers[c], tie(c, bar_id)))
    held = sum(p["칸"] for p in pos_all.values()) + sum(x["칸"] for x in pend if x["type"] == "buy")
    leaving = {x["code"]: x["칸"] for x in pend if x["type"] == "sell"}
    free = SLOTS - held + sum(leaving.values())
    for code in sigs:
        c = cands[code]
        need = size_of(c)
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
        why = how[code]
        pend.append({"type": "buy", "code": code, "칸": take, "decided": bar_id, "kind": "추세" if c.get("추세문") else "정배열",
                     "name": c["name"], "why": why})
        door = "추세 문" if c.get("추세문") else "정배열 문"
        extra = " · 3일 연속" if c.get("3일연속") else ""
        price = next_open.get(code)
        at = f" (약 {price:,.0f}원)" if price else ""
        log("매수", f"{c['name']}({code}) · {fill_note}{at}에 {take}칸({take * 10}%) 사기 · {door}{extra} · {why} · 순서 무리 {tiers[code]}/4", {"code": code})


def fill(state, bar_id, opens):
    """앞 봉에서 정한 매수 · 매도를 이 봉(bar_id) 시가로 체결해 연습 계좌에 적음."""
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
            gain = (price / p["price"] - 1) * 100 - 0.30
            closed.append({"code": x["code"], "name": p["name"], "산 때": p["bought"], "판 때": bar_id, "칸": part,
                           "손익": round(gain, 2), "까닭": x["why"]})
            x = {**x, "name": p["name"], "손익": round(gain, 2), "칸": part}
            p["칸"] -= part
            if p["칸"] <= 0:
                del pos_all[x["code"]]
        elif x["type"] == "buy" and x["code"] not in pos_all:
            pos_all[x["code"]] = {"code": x["code"], "name": x["name"], "kind": x["kind"], "price": price, "peak": price,
                                  "칸": x["칸"], "처음칸": x["칸"], "bars": -1, "bought": bar_id, "max_close": None}
            # bars는 이 봉(산 봉)이 닫히며 0이 됨 — 연구의 '산 봉부터 센 봉 수'(k − i)와 같음
        done.append(x)
    state["pending"] = keep
    state["closed"] = closed[-300:]
    return done


# ───────────────────────── 자료 · 증권사 · 디스코드 ─────────────────────────

def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, body):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


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
            r = requests.post(url, json={"content": msg}, timeout=(10, 20))
            ok = ok and r.status_code < 300
        except requests.RequestException:
            ok = False
    return ok


def _flow_features(code, through):
    """through(그날 포함)까지의 외국인+투신 5일 합 ÷ 20일 평균 거래량, 20일 수익, 외국인 · 투신 3일 연속."""
    import final_group
    rows = [r for r in final_group.flow_rows(code) if r.get("date", "") <= through]
    vols = _load(f"volume-data/{code}.json", {}).get("날") or []
    vols = [float(v[1]) for v in vols if v[0] <= through][-20:]
    closes = [float(c) for d, c in (_load(f"price-data/{code}.json", {}).get("closes") or []) if d <= through]
    last5 = rows[-5:]
    flow5 = None
    if len(last5) == 5 and len(vols) == 20 and sum(vols) > 0:
        flow5 = sum((r.get("외국인") or 0) + (r.get("투신") or 0) for r in last5) / (sum(vols) / 20)
    r20 = closes[-1] / closes[-21] - 1 if len(closes) > 21 and closes[-21] > 0 else None
    last3 = rows[-3:]
    steady = len(last3) == 3 and all((r.get("외국인") or 0) > 0 and (r.get("투신") or 0) > 0 for r in last3)
    return flow5, r20, steady


def make_plan():
    """장 마감 뒤: 내일 쓸 후보(오늘 종가 · 오늘 수급까지) + 들고 있는 정배열 매매의 정배열 깨짐."""
    import final_group
    import study
    prices = study.load_prices()
    found = final_group.compute(prices, flow_day="next")
    day = found.get("date")
    if not day:
        print("일봉이 없어 후보를 만들지 못했습니다.")
        return 1
    import data_guard
    ready, _, why = data_guard.daily_ready(prices, day)
    print("자료 확인 ·", why)
    if not ready:
        # 자료가 덜 들어온 채 만든 후보는 틀림(2026-10-02 사고). 옛 후보는 내일 장중 실행이 '낡은 후보'로 보고 새로 사지 않음.
        send([f"⚠️ **1시간봉 후보 만들기 멈춤** · {why}", "자료가 다 들어오면 다시 만듭니다. 그때까지 1시간봉은 새로 사지 않고 들고 있는 종목만 관리해요."])
        return 1
    cands = []
    for one in found.get("picks", []):
        flow5, r20, steady = _flow_features(one["code"], day)
        cands.append({"code": one["code"], "name": one["name"], "추세문": final_group.RULE_DOOR in (one.get("갈래") or []),
                      "3일연속": steady, "flow5": flow5, "r20": r20, "시총순위": one.get("시총순위"), "갈래": one.get("갈래")})
    plan = {"base": day, "made": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "breadth": found.get("breadth"),
            "candidates": cands,
            # 조건이 1~2개만 모자란 종목(대시보드 '1시간봉 매수 후보(충족 미달)' · 사용자 요청 2026-10-01)
            "near": [{k: b.get(k) for k in ("code", "name", "모자란 수", "가까운 갈래", "모자란 것")} for b in found.get("b_group", []) if b.get("모자란 수") == 1]}
    _save(PLAN, plan)
    state = _load(STATE, {"positions": {}, "pending": []})
    lines = [f"📋 **1시간봉 매매 · {day[:4]}-{day[4:6]}-{day[6:]} 마감 기준 → 다음 거래일 후보 {len(cands)}종목**",
             f"시장 폭 {found.get('breadth')}% · 장중 1시간마다 1시간봉 EMA 정배열(없으면 12시)에 사는지 알려 드려요."]
    for c in sorted(cands, key=lambda c: (not c["추세문"], not c["3일연속"])):
        size = size_of(c)
        lines.append(f"• **{c['name']}**({c['code']}) · {'·'.join(c.get('갈래') or [])} · {size}칸({size * 10}%)"
                     + (" · 3일 연속" if c["3일연속"] else ""))
    if not cands:
        lines.append("⚪ 다음 거래일 후보가 없어요.")
    # 들고 있는 정배열 매매: 오늘 종가로 일봉 정배열이 깨졌으면 내일 09:00 시가 청산
    alerts = []
    for code, p in list(state.get("positions", {}).items()):
        if p["kind"] != "정배열" or any(x["code"] == code and x["type"] == "sell" for x in state.get("pending", [])):
            continue
        closes = [float(c) for d, c in (prices.get(code, {}).get("rows") or [])]
        shape = final_group.lines_now(closes) if closes else None
        if shape is not None and not shape.get("정배열"):
            state.setdefault("pending", []).append({"type": "sell", "code": code, "칸": p["칸"], "why": "일봉 정배열 깨짐",
                                                     "decided": day + "14"})
            alerts.append(f"⚪ 청산 · {p['name']}({code}) · 내일 09:00 시가에 {p['칸']}칸 팔기 · 일봉 정배열 깨짐")
    if alerts:
        _save(STATE, state)
        _log_alerts([("청산", a, {}) for a in alerts])
    held = state.get("positions", {})
    if held:
        lines.append(f"📦 들고 있는 종목 {len(held)}개 · " + " · ".join(f"{p['name']} {p['칸']}칸" for p in held.values()))
    send(lines + alerts + [NOTE])
    print(f"후보 {len(cands)}종목 · 청산 알림 {len(alerts)}건")
    return 0


def _log_alerts(items):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    got = _load(ALERTS, [])
    got += [{"at": now, "kind": k, "text": t, **extra} for k, t, extra in items]
    _save(ALERTS, got[-500:])


def today_bars(client, code, day):
    """오늘 1분봉 → 1시간봉(09 ~ 14시, 15시 봉은 14시 봉에 합침). [(시각, o, h, l, c, v)]."""
    import collect_kis_hourly as K
    rows = []
    for end in K.ENDS:
        rows += K.broker_kis_rows(client, code, day, end)
    got = {}
    for t, o, h, l, c, v in K.to_hours(rows, day):
        hh = t[8:]
        key = day + ("14" if hh == "15" else hh)
        if key in got:
            po, ph, pl, pc, pv = got[key]
            got[key] = (po, max(ph, h), min(pl, l), c, pv + v)
        else:
            got[key] = (o, h, l, c, v)
    return [(t, *got[t]) for t in sorted(got)]


def kis_history(code):
    """야후 1시간봉이 없는 종목은 한국투자증권 기록으로 EMA를 셈(15시 봉은 14시 봉에 합침).
    한투 1시간봉(hourly-kis)과 한투 15분봉(m15-kis, 1시간으로 묶음)을 함께 읽음 — 둘은 같은 1분봉에서 만들어 종가가 100% 같고
    (2026-10-02 확인), 2026-10-02부터 1시간봉 따로 받기를 멈추고 15분봉으로만 받음(사용자 결정 · 같은 자료 두 번 받지 않게)."""
    by = {}
    for home in ("hourly-kis", "m15-kis"):
        folder = Path(home) / code
        if not folder.is_dir():
            continue
        for f in sorted(folder.glob("*.csv")):
            for ln in f.read_text(encoding="utf-8").splitlines():
                p = ln.split(",")
                if len(p) != 6 or not p[0][:1].isdigit():
                    continue
                hh = p[0][8:10]
                key = p[0][:8] + ("14" if hh == "15" else hh)
                by[key] = float(p[4])      # 시각 순으로 읽으므로 그 시간 마지막 봉(15시 봉은 마감) 종가가 남음
    t = sorted(by)
    return {"t": t, "c": [by[x] for x in t]} if t else None


def closed_bars(now):
    """지금까지 닫힌 오늘 봉 이름들(HH)."""
    hm = now.strftime("%H%M")
    return [hh for hh in HOURS if hm >= CLOSE_AT[hh]]


def fill_lines(filled):
    """연습 계좌에서 이번에 체결된 매수 · 매도를 디스코드 줄로(사용자 요청: 진입 · 청산은 모두 알림)."""
    out = []
    for bar_id, done, px in filled:
        when = "09:00" if bar_id[8:] == "09" else f"{bar_id[8:]}:00"
        for x in done:
            price = px.get(x["code"])
            at = f" {price:,.0f}원" if price else ""
            name = x.get("name") or x["code"]
            if x["type"] == "buy":
                out.append(f"✅ 매수 체결 · {name}({x['code']}) · {x['칸']}칸({x['칸'] * 10}%) · {when} 시가{at}")
            else:
                out.append(f"✅ 매도 체결 · {name}({x['code']}) · {x['칸']}칸 · {when} 시가{at} · "
                           f"손익 {x.get('손익', 0):+.1f}%(비용 뺌) · {x.get('why', '')}")
    return out


def run_live(now=None):
    import broker_kis
    import hlab
    now = now or datetime.now(KST)
    day = now.strftime("%Y%m%d")
    plan = _load(PLAN, None)
    state = _load(STATE, {"positions": {}, "pending": []})
    if not plan or plan.get("base", "") >= day:
        print("쓸 후보(plan)가 없거나 오늘 것이 아닙니다.")
        return 0
    done_bars = closed_bars(now)
    todo = [day + hh for hh in done_bars if day + hh > state.get("last_bar", "")]
    codes = sorted({c["code"] for c in plan.get("candidates", [])} | set(state.get("positions", {}))
                   | {x["code"] for x in state.get("pending", [])})
    if not codes:
        print("후보도 들고 있는 종목도 없습니다.")
        state["last_bar"] = max([state.get("last_bar", "")] + [day + hh for hh in done_bars])
        _save(STATE, state)
        return 0
    try:
        client = broker_kis.market()
        import collect_kis_intraday as I
        if not I.market_open_today(client, day):
            print(f"{day}은 장이 열리지 않은 날로 보여 넘어갑니다.")
            return 0
        import data_guard
        ready, why = data_guard.plan_ready(plan, data_guard.prev_trading_day(client, day))
        if not ready:
            # 낡은 후보로는 새로 사지 않음 · 들고 있는 종목의 팔기 · 정해 둔 매매 체결은 그대로(사용자 요청 2026-10-02)
            print("자료 확인 ·", why)
            plan = {**plan, "candidates": []}
            if state.get("자료 멈춤") != day:
                state["자료 멈춤"] = day
                send([f"⚠️ **1시간봉 새로 사기 멈춤** · {why}", "들고 있는 종목의 팔기는 그대로 해요."])
        live = {c: today_bars(client, c, day) for c in codes}
    except broker_kis.BrokerError as e:
        print("증권사 조회 실패 ·", e)
        return 1
    hist = hlab.load(codes)
    bars = {}
    for c in codes:
        h = hist.get(c) or kis_history(c)
        t = [x for x in (h["t"] if h else []) if x[:8] < day]
        cl = [float(x) for x in (h["c"][:len(t)] if h else [])]
        for row in live.get(c, []):
            t.append(row[0]); cl.append(row[4])
        bars[c] = {"t": t, "c": cl}
    opens = {c: {row[0]: row[1] for row in live.get(c, [])} for c in codes}
    items = []
    log = lambda kind, text, extra: items.append((kind, text, extra))
    names = {c["code"]: c["name"] for c in plan.get("candidates", [])}
    filled = []          # (봉, 체결된 매매, 그 봉 시가) — 모의투자 주문이 따라 넣음
    for bar_id in todo:
        # 이 봉 시가로 앞에서 정한 것들 체결
        px = {c: opens[c].get(bar_id) for c in codes}
        filled.append((bar_id, fill(state, bar_id, px), px))
        closed = {c: {"t": [x for x in bars[c]["t"] if x <= bar_id], "c": bars[c]["c"][:len([x for x in bars[c]["t"] if x <= bar_id])]}
                  for c in codes}
        nxt = HOURS[HOURS.index(bar_id[8:]) + 1] if bar_id[8:] != "14" else None
        next_open = {c: (opens[c].get(day + nxt) if nxt else None) for c in codes}
        step(state, plan, closed, bar_id, next_open, log)
        state["last_bar"] = bar_id
    # 방금 시작한 봉의 시가가 이미 있으면 바로 체결(알림의 '약 몇 원'과 같은 값)
    cur = [hh for hh in HOURS if hh not in done_bars]
    # 09:01 실행: 오늘 닫힌 봉은 없지만 전날 마지막 봉 · 일봉 정배열 깨짐으로 정한 매도는 오늘 09시 시가에 체결
    first_open = bool(cur) and not todo and cur[0] == "09" and any(x["decided"] < day + "09" for x in state.get("pending", []))
    if cur and (todo or first_open):
        px = {c: opens[c].get(day + cur[0]) for c in codes}
        filled.append((day + cur[0], fill(state, day + cur[0], px), px))
    _save(STATE, state)
    paper = []
    try:
        import paper_trade
        for bar_id, done, px in filled:
            paper += paper_trade.execute(done, state, {c: v for c, v in px.items() if v}, bar_id, now=now)
    except Exception as e:          # 모의투자 주문이 잘못돼도 알림 · 연습 계좌는 그대로 돌아가게
        paper.append(f"🧪 모의투자 주문 중 문제 · {type(e).__name__}")
    fills = fill_lines(filled)
    if (paper or fills) and not items:
        send([f"✅ **1시간봉 매매 · 체결 · {now.strftime('%m-%d %H:%M')}**"] + fills + paper)
    if items:
        _log_alerts(items)
        icon = {"매수": "🟢", "자리 바꾸기": "🔄", "절반 익절": "🟡", "익절": "🔵", "손절": "🔴", "청산": "⚪", "못 삼": "⚫"}
        head = f"⏰ **1시간봉 매매 · {now.strftime('%m-%d %H:%M')}** (봉 {', '.join(b[8:] + '시' for b in todo)} 마감)"
        try:
            import paper_trade
            note = NOTE_PAPER if paper_trade.enabled()[0] else NOTE_PLAIN
        except Exception:
            note = NOTE_PLAIN
        send([head] + fills + [f"{icon.get(k, '•')} {k} · {t}" for k, t, _ in items] + paper + [note])
    print(f"처리한 봉 {todo} · 알림 {len(items)}건 · 들고 있는 종목 {len(state.get('positions', {}))}개")
    return 0


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "live"
    sys.exit(make_plan() if what == "plan" else run_live())
