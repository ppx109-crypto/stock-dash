"""장 마감 뒤 견줌(사용자 2026-10-02 "장 마감시 그날 1m 다운로드하여 백테스트 진행하여 조합하여 15m · 1h · 1일봉과 모의투자 결과 비교").

그날 한투 1분봉을 15분봉(m15-kis, collect_kis_m15가 받음)으로 받은 뒤, 15분봉을 묶어 1시간봉 · 1일봉을 만들고
같은 규칙을 '완성된 봉'으로 다시 돌려(백테스트) 그날 운영 · 모의투자가 실제로 한 것과 견줍니다.
- 1시간봉: hourly_a의 판단(step) · 체결(fill)을 그대로 씀. 운영은 장중 실시간 1분봉으로, 여기선 15분봉을 묶은 완성 봉으로.
  전날 저녁 후보(plan)도 운영 make_plan과 같은 셈(final_group.compute · 전날까지 자료)으로 다시 만듦.
- 1일봉: daily_live의 판단(decide · settle · kin_checker)을 그대로 씀. 운영은 15:20 값으로, 여기선 15분봉을 묶은 그날 종가로.
  (재현 시험 research/x007.py: daily_live 판단 = 연구 엔진 lab.run, 9년 매매 하나하나까지 같음.)
- 검산: 15분봉으로 만든 그날 일봉 종가 vs 일봉 자료(price-data) 종가 — 0.1% 넘게 다른 종목을 적음(사용자 결정: 1일봉은 견줌 · 검산용).
백테스트 상태는 reconcile/state.json에 날마다 이어 적고(운영 시작일 START부터), 그날 결과는 reconcile/{날}.json에 둡니다.
주문은 하지 않습니다(읽기 · 셈만). 그날 15분봉이 덜 모였으면 그 날은 건너뛰고 다음에 다시 셉니다.
python reconcile.py [YYYYMMDD]  — 날을 주지 않으면 아직 안 센 지난 거래일을 차례로 셈.
"""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

START = os.getenv("RECONCILE_START", "20261002")      # 1시간봉 · 1일봉 모의투자 시작일
HOME = Path(os.getenv("RECONCILE_HOME", "reconcile"))
STATE = HOME / "state.json"
M15 = Path("m15-kis")
HOURS = ("09", "10", "11", "12", "13", "14")
NEED = 0.9                                             # 그날 15분봉이 있어야 할 종목 가운데 이만큼은 있어야 셈


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


# ───────────────────────── 15분봉 → 1시간봉 · 1일봉 ─────────────────────────

def m15_day(code, day, home=M15):
    """그날 15분봉 [(YYYYMMDDHHMM, o, h, l, c, v)] — 없으면 []."""
    f = Path(home) / code / f"{day[:4]}.csv"
    if not f.exists():
        return []
    out = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        p = ln.split(",")
        if len(p) == 6 and p[0][:8] == day:
            out.append((p[0], *(float(x) for x in p[1:5]), float(p[5])))
    return sorted(out)


def to_hours(rows, day):
    """15분봉 → 1시간봉 [(YYYYMMDDHH, o, h, l, c, v)] — 운영 today_bars와 같게 15시 칸은 14시 봉에 합침."""
    got = {}
    for t, o, h, l, c, v in rows:
        hh = t[8:10]
        key = day + ("14" if hh == "15" else hh)
        if key in got:
            po, ph, pl, pc, pv = got[key]
            got[key] = (po, max(ph, h), min(pl, l), c, pv + v)
        else:
            got[key] = (o, h, l, c, v)
    return [(t, *got[t]) for t in sorted(got)]


def to_day(rows):
    """15분봉 → 그날 일봉 (o, h, l, c, v) 또는 None."""
    if not rows:
        return None
    return (rows[0][1], max(r[2] for r in rows), min(r[3] for r in rows), rows[-1][4], sum(r[5] for r in rows))


def check_daily(day, prices, codes=None):
    """검산: 15분봉으로 만든 그날 종가 vs 일봉 자료 종가. → {"종목": n, "다름": [(code, 15분봉 종가, 일봉 종가, %)]}."""
    bad, n = [], 0
    for code in sorted(codes or prices):
        d1 = to_day(m15_day(code, day))
        rows = (prices.get(code) or {}).get("rows") or []
        daily = next((float(c) for d, c in reversed(rows) if str(d) == day), None)
        if d1 is None or daily is None:
            continue
        n += 1
        gap = (d1[3] / daily - 1) * 100 if daily else 0.0
        if abs(gap) > 0.1:
            bad.append((code, d1[3], daily, round(gap, 2)))
    return {"종목": n, "다름": bad}


# ───────────────────────── 1일봉 백테스트(daily_live 판단 · 15분봉 종가) ─────────────────────────

def backtest_daily(day, prices, state):
    """daily_live.run과 같은 셈을 '15분봉으로 만든 그날 종가'로. state(1일봉 백테스트 계좌)를 고쳐 씀 → (sells, buys, 쓴 종가)."""
    import caps
    import daily_live as D
    import final_group
    import lab
    past = {c: dict(v, rows=[r for r in v["rows"] if str(r[0]) < day]) for c, v in prices.items()}
    past = {c: v for c, v in past.items() if v["rows"]}
    last = max(v["rows"][-1][0] for v in past.values())
    yest = [{"code": c, "date": v["rows"][-1][0], "price": v["rows"][-1][1]} for c, v in past.items() if v["rows"][-1][0] == last]
    caps.tag(yest, D.POOL)
    held = state.setdefault("positions", {})
    pool = {r["code"] for r in yest if (r.get(caps.RANK) or 999) <= D.POOL} | set(held)
    close, vol = {}, {}
    for code in pool:
        d1 = to_day(m15_day(code, day))
        if d1:
            close[code], vol[code] = d1[3], d1[4]
        else:                                      # 15분봉이 없는 종목(15분봉 대상 밖)은 일봉 자료 종가
            got = next((float(c) for d, c in reversed(prices.get(code, {}).get("rows") or []) if str(d) == day), None)
            if got is not None:
                close[code] = got
    live = {c: {"name": past[c]["name"], "rows": past[c]["rows"] + [(day, close[c])]} for c in close if c in past}
    calm = (_load(Path("study") / "a_group.json", {}) or {}).get("calm_edge")
    found = final_group.compute(live, calm=calm)
    if found.get("date") != day:
        return None
    cands = []
    for one in found.get("picks", []):
        code = one["code"]
        if D.target_cut(code, day):
            continue
        cands.append({**one, "추세문": final_group.RULE_DOOR in (one.get("갈래") or []), "3일연속": D.steady3(code, day),
                      "거래량비": D.volume_ratio(code, day, vol.get(code))})
    aligned = {}
    for code in held:
        if code in live:
            form = final_group.lines_now([x for _, x in live[code]["rows"]])
            aligned[code] = bool(form and form.get("정배열"))
    steps = lab.moves(live)
    idx = {c: len(live[c]["rows"]) - 1 for c in live}
    kin_ok = D.kin_checker(steps, idx, {c: [str(d) for d, _ in live[c]["rows"]] for c in live},
                           {c: p.get("bought") for c, p in held.items()})
    rate = {c: (close[c] / float(past[c]["rows"][-1][1]) - 1) * 100 for c in close if c in past and past[c]["rows"][-1][1]}
    sells, buys = D.decide(state, cands, close, aligned, rate, kin_ok)
    D.settle(state, day, sells, buys, close)
    return sells, buys, {"breadth": found.get("breadth"), "후보": [c["code"] for c in cands]}


# ───────────────────────── 1시간봉 백테스트(hourly_a 판단 · 15분봉을 묶은 완성 봉) ─────────────────────────

def plan_for(day, prices):
    """운영 make_plan과 같은 셈: day 앞 거래일까지의 일봉 · 그날 수급까지 → day에 쓸 후보."""
    import final_group
    import hourly_a as A
    past = {c: dict(v, rows=[r for r in v["rows"] if str(r[0]) < day]) for c, v in prices.items()}
    past = {c: v for c, v in past.items() if v["rows"]}
    found = final_group.compute(past, flow_day="next")
    base = found.get("date")
    cands = []
    for one in found.get("picks", []):
        flow5, r20, steady = A._flow_features(one["code"], base)
        cands.append({"code": one["code"], "name": one["name"], "추세문": final_group.RULE_DOOR in (one.get("갈래") or []),
                      "3일연속": steady, "flow5": flow5, "r20": r20, "시총순위": one.get("시총순위"), "갈래": one.get("갈래")})
    return {"base": base, "breadth": found.get("breadth"), "candidates": cands}, past


def backtest_hourly(day, prices, state):
    """hourly_a.run_live와 같은 차례(봉마다 앞서 정한 것 체결 → 판단)를 그날 완성 봉으로. state를 고쳐 씀."""
    import final_group
    import hlab
    import hourly_a as A
    plan, past = plan_for(day, prices)
    # 전날 저녁 make_plan: 들고 있는 정배열 매매가 전날 종가로 일봉 정배열이 깨졌으면 오늘 09시 시가에 팜
    for code, p in list(state.get("positions", {}).items()):
        if p["kind"] != "정배열" or any(x["code"] == code and x["type"] == "sell" for x in state.get("pending", [])):
            continue
        closes = [float(c) for d, c in (past.get(code, {}).get("rows") or [])]
        shape = final_group.lines_now(closes) if closes else None
        if shape is not None and not shape.get("정배열"):
            state.setdefault("pending", []).append({"type": "sell", "code": code, "칸": p["칸"], "why": "일봉 정배열 깨짐",
                                                     "decided": plan["base"] + "14"})
    codes = sorted({c["code"] for c in plan["candidates"]} | set(state.get("positions", {}))
                   | {x["code"] for x in state.get("pending", [])})
    today = {c: to_hours(m15_day(c, day), day) for c in codes}
    saved = os.environ.get("HLAB_OPEN_HOLDOUT")
    os.environ["HLAB_OPEN_HOLDOUT"] = "1"
    try:
        hist = hlab.load(codes)
    finally:
        if saved is None:
            os.environ.pop("HLAB_OPEN_HOLDOUT", None)
        else:
            os.environ["HLAB_OPEN_HOLDOUT"] = saved
    bars = {}
    for c in codes:
        t, cl = A.history_bars(hist.get(c), A.kis_history(c), day)
        for row in today[c]:
            t.append(row[0]); cl.append(row[4])
        bars[c] = {"t": t, "c": cl}
    opens = {c: {row[0]: row[1] for row in today[c]} for c in codes}
    log, filled = [], []
    for hh in HOURS:
        bar_id = day + hh
        px = {c: opens[c].get(bar_id) for c in codes}
        filled += [dict(x, 봉=bar_id, 값=px.get(x["code"])) for x in A.fill(state, bar_id, px)]
        closed = {c: {"t": [x for x in bars[c]["t"] if x <= bar_id],
                      "c": bars[c]["c"][:len([x for x in bars[c]["t"] if x <= bar_id])]} for c in codes}
        nxt = HOURS[HOURS.index(hh) + 1] if hh != "14" else None
        next_open = {c: (opens[c].get(day + nxt) if nxt else None) for c in codes}
        A.step(state, plan, closed, bar_id, next_open, lambda kind, text, extra: log.append((bar_id, kind, text)))
        state["last_bar"] = bar_id
    return filled, log, {"base": plan["base"], "breadth": plan["breadth"], "후보": [c["code"] for c in plan["candidates"]],
                         "15분봉 없는 종목": [c for c in codes if not today[c]]}


# ───────────────────────── 모의투자 · 운영 기록과 견줌 ─────────────────────────

def _trades_from_state(state, key_buy, key_sell):
    closed = [(t["code"], str(t[key_buy]), str(t[key_sell]), t["칸"], t["손익"]) for t in state.get("closed", [])]
    held = sorted((c, str(p.get("bought")), p["칸"], p["price"]) for c, p in state.get("positions", {}).items())
    return closed, held


def compare(back, live, key_buy, key_sell):
    bc, bh = _trades_from_state(back, key_buy, key_sell)
    lc, lh = _trades_from_state(live, key_buy, key_sell)
    keyed = lambda rows: {(r[0], r[1]): r for r in rows}
    kb, kl = keyed(bc), keyed(lc)
    gap = [(k[0], k[1], kb[k][4], kl[k][4]) for k in kb.keys() & kl.keys() if abs(kb[k][4] - kl[k][4]) > 0.01]
    sum_w = lambda rows: round(sum(r[3] * r[4] for r in rows) / 10, 2)
    return {"백테스트 끝난 매매": len(bc), "운영 끝난 매매": len(lc), "같은 매매": len(kb.keys() & kl.keys()),
            "백테스트에만": sorted(kb.keys() - kl.keys()), "운영에만": sorted(kl.keys() - kb.keys()),
            "같은 매매 손익 차이": sorted(gap), "계좌 몫 합(백테스트 · 운영 · %)": (sum_w(bc), sum_w(lc)),
            "들고 있는 종목(백테스트)": [x[0] for x in bh], "들고 있는 종목(운영)": [x[0] for x in lh]}


def paper_orders(path, day):
    book = _load(path, {"orders": []})
    return [{k: o.get(k) for k in ("at", "code", "side", "qty", "status")} for o in book.get("orders", [])
            if str(o.get("at", "")).replace("-", "")[:8] == day]


# ───────────────────────── 하루 셈 ─────────────────────────

def trading_days(prices):
    ref = prices.get("005930") or next(iter(prices.values()))
    return [str(d) for d, _ in ref["rows"]]


def ready(day, codes):
    """그날 15분봉이 있어야 할 종목 가운데 NEED 넘게 있으면 참."""
    if not codes:
        return True
    have = sum(1 for c in codes if (M15 / c).is_dir() and m15_day(c, day))
    want = sum(1 for c in codes if (M15 / c).is_dir())
    return want == 0 or have / want >= NEED


def run_day(day, prices, book):
    """하루를 셈 → 결과(dict) 또는 None(자료가 덜 모임). book: reconcile/state.json 내용(고쳐 씀)."""
    s1h = copy.deepcopy(book.get("1h", {"positions": {}, "pending": []}))
    s1d = copy.deepcopy(book.get("1d", {"positions": {}, "closed": []}))
    probe = sorted(set(s1h.get("positions", {})) | set(s1d.get("positions", {})) | {"005930", "000660"})
    if not ready(day, probe):
        return None
    got1d = backtest_daily(day, prices, s1d)
    filled, log, info1h = backtest_hourly(day, prices, s1h)
    live_1h = _load(Path("hourly-live") / "state.json", {})
    live_1d = _load(Path("daily-live") / "state.json", {})
    idle_today = _load(Path("idle-live") / "today.json", {})
    out = {
        "date": day,
        "검산(15분봉 종가 vs 일봉 종가)": check_daily(day, prices),
        "1시간봉": {"백테스트 체결": [{k: x.get(k) for k in ("봉", "type", "code", "칸", "값", "why")} for x in filled],
                  "백테스트 알림": log, "정보": info1h,
                  "운영과 견줌(START부터 누계)": compare(s1h, live_1h, "산 때", "판 때"),
                  "모의투자 주문(그날)": paper_orders(Path("hourly-live") / "paper-orders.json", day)},
        "1일봉": {"백테스트 판단": None if got1d is None else {"팔기": got1d[0], "사기": got1d[1], **got1d[2]},
                "운영과 견줌(START부터 누계)": compare(s1d, live_1d, "산 날", "판 날"),
                "운영 그날 판단": _load(Path("daily-live") / "today.json", {}) if (_load(Path("daily-live") / "today.json", {}) or {}).get("date") == day else None,
                "모의투자 주문(그날)": paper_orders(Path("daily-live") / "paper-orders.json", day)},
        # 2026-10-03 최종 조합: 1일봉 50 · 15분봉 50 · 빈칸 엔진 · 코스닥 인버스(남는 돈) — 1시간봉은 모의 주문 쉼
        "15분봉": {"모의투자 주문(그날)": paper_orders(Path("m15-live") / "paper-orders.json", day),
                 "메모": "15분봉 완성 봉 백테스트 견줌은 아직 없음(연구 엔진 m15lab으로 따로 셈)"},
        "빈칸 엔진": {"운영 그날 판단": idle_today if (idle_today or {}).get("date") == day else None,
                  "모의투자 주문(그날)": paper_orders(Path("idle-live") / "paper-orders.json", day),
                  "들고 있는 것": (_load(Path("idle-live") / "state.json", {}) or {}).get("positions", {})},
    }
    book["1h"], book["1d"], book["last_day"] = s1h, s1d, day
    return out


def summary_lines(out):
    """장 마감 뒤 견줌 디스코드 — 한 줄(사용자 2026-10-06 "거두절미하고 요약버전으로 전부"). 자세한 건 reconcile/{날}.json."""
    v = out["검산(15분봉 종가 vs 일봉 종가)"]
    h, d = out["1시간봉"]["운영과 견줌(START부터 누계)"], out["1일봉"]["운영과 견줌(START부터 누계)"]
    day = out["date"]
    e = out.get("빈칸 엔진") if isinstance(out.get("빈칸 엔진"), dict) else {}
    return [f"🔁 **견줌 {day[4:6]}-{day[6:]}** · 검산 다름 {len(v['다름'])}/{v['종목']}"
            f" · 1시간봉 같은 매매 {h['같은 매매']}/{h['운영 끝난 매매']} · 1일봉 {d['같은 매매']}/{d['운영 끝난 매매']}"
            + (f" · 엔진 주문 {len(e.get('모의투자 주문(그날)') or [])}" if e else "")]


def idle_line(out):
    """빈칸 엔진 한 줄(그날 판단 · 주문 · 들고 있는 것). 옛 결과 파일엔 없으니 없으면 빈 목록."""
    e = out.get("빈칸 엔진") if isinstance(out.get("빈칸 엔진"), dict) else None
    if not e:
        return []
    t = e.get("운영 그날 판단") or {}
    held = ", ".join(f"{c}({p.get('kind')})" for c, p in (e.get("들고 있는 것") or {}).items()) or "없음"
    return [f"• 빈칸 엔진: 시장 폭 {t.get('breadth', '?')} · 규칙 쓴 몫 {round((t.get('used') or 0) * 100)}% · "
            f"그날 모의 주문 {len(e.get('모의투자 주문(그날)') or [])}건 · 들고 있는 것 {held}"]


def main(argv):
    import study
    prices = study.load_prices()
    days = trading_days(prices)
    book = _load(STATE, {})
    if len(argv) > 1:
        todo = [argv[1]]
    else:
        todo = [d for d in days if d >= START and d > book.get("last_day", "")]
    done = []
    for day in todo:
        out = run_day(day, prices, book)
        if out is None:
            print(f"{day} · 15분봉이 아직 덜 모여 다음에 셉니다.")
            break
        _save(HOME / f"{day}.json", out)
        _save(STATE, book)
        done.append(out)
        print("\n".join(summary_lines(out)))
    if done and os.getenv("DISCORD_WEBHOOK_URL", "").strip():
        import daily_live as D
        D.send(summary_lines(done[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
