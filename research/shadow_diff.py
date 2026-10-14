"""그림자 견주기 — '연구 셈'과 '실제 모의투자'를 날마다 나란히 봄(사용자 2026-10-14 요청 · 읽기 전용 · 주문 없음).

무엇을: 최종본 봇(docs/PAPER-FINAL.md) — 1일봉 · 사건 바구니 · 빈칸 엔진(+코스닥 과열 인버스) · 덧붙임 · 계좌 흔들림 상한.
       MIX54 시작일(SHADOW_START · 기본 20261012)부터 거래일마다
         ① 연구 규칙이 그날 무엇을 했을지(운영과 같은 순수 함수를 다시 돌림 · 다시 짜지 않음)
         ② 실제로 무엇을 정했는지 · 주문 결과(장부 · git 기록)
         ③ 같은지 · 손익 차이 어림(연구 = 그날 종가 체결 · 실제 = 장부의 주문 때 값)
       을 shadow/diff.json(날마다) · shadow/DIFF.md(쉬운 표 · 최근 20거래일)에 적음.

연구 셈의 값(미래 참조 막기):
  · 15:10 · 15:13 · 15:20 판단 값 자리에 **그날 종가**를 씀(연구 판 그대로 · 운영은 그 시각 현재가라 조금 다를 수 있음).
  · 그 밖에는 그날 앞 자료만: 덧붙임 국면 = 어제 장 끝까지 · 바구니 사건 = 어제(t0)까지 접수 · 수급 = 전날까지 ·
    흔들림 상한 σ = 전날까지 20거래일. 그날 종가가 아직 안 모였으면 그 봇은 '자료 기다림'으로 두고 다음 실행에 다시 셈.
  · 1일봉 고요 문턱(calm)은 운영처럼 study/a_group.json의 그날(없으면 앞날) 값 · 후보는 전날 시총 150위 안(운영과 같은 범위).
연구 길(path): 시작 전날 실제 장부(git)에서 출발해 연구 결정대로 날마다 이어 감(계좌 크기 = 실제 계좌 NAV 어림).
손익 차이: 봇마다 그날 손익(전날 종가 → 그날 종가로 매김 · 그날 산 · 판 것은 체결값 → 종가) 연구 − 실제.
          실제 체결값은 장부에 적힌 주문 때 값(체결 확인 값이 아님 · 어림). 비용은 넣지 않음.
비밀: 키 · 계좌번호 · 증권사 응답 본문은 읽지도 적지도 않음(장부에 있는 비율 · 수량 · 주문 결과 글만).
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

KST = ZoneInfo("Asia/Seoul")
START = os.getenv("SHADOW_START", "20261012")
OUT = Path("shadow")
CACHE = OUT / "cache.json"
BOTS = ("1일봉", "사건 바구니", "빈칸 엔진", "덧붙임", "흔들림 상한")
D1_SHARE, BASKET_SHARE = 0.5, 0.3           # 1일봉 계좌 몫 0.5 · 바구니 0.3(MIX-0054)
LEDGERS = {"daily_today": "daily-live/today.json", "daily_state": "daily-live/state.json",
           "basket_today": "basket-live/today.json", "basket_state": "basket-live/state.json",
           "idle_today": "idle-live/today.json", "idle_state": "idle-live/state.json",
           "overlay_state": "overlay-live/state.json", "cap_log": "acc-cap/log.json"}
BOOKS = {"1일봉": "daily-live/paper-orders.json", "사건 바구니": "basket-live/paper-orders.json",
         "빈칸 엔진": "idle-live/paper-orders.json", "덧붙임": "overlay-live/paper-orders.json"}


# ───────────────────────── 순수 셈(시험 대상) ─────────────────────────

def mark_pnl(qty_prev, trades, close_prev, close_now):
    """그날 손익(원). qty_prev: 전날 끝 수량 {코드: 주} · trades: [(코드, 'buy'|'sell', 수량, 체결값)] ·
    close_prev · close_now: {코드: 종가}. 값이 모자라면 None(셀 수 없음)."""
    pnl = 0.0
    for c, q in qty_prev.items():
        if not q:
            continue
        a, b = close_prev.get(c), close_now.get(c)
        if not a or not b:
            return None
        pnl += q * (b - a)
    for c, side, q, px in trades:
        b = close_now.get(c)
        if not b or not px:
            return None
        pnl += q * (b - px) if side == "buy" else q * (px - b)
    return pnl


def apply_trades(qty, trades):
    """수량 {코드: 주}에 체결 [(코드, side, 수량, 값)]을 더한 새 사전."""
    out = dict(qty)
    for c, side, q, _ in trades:
        out[c] = out.get(c, 0) + (q if side == "buy" else -q)
        if out[c] <= 0:
            out.pop(c)
    return out


def book_trades(orders, day):
    """주문 장부 줄들 → 그날 '접수'된 체결 어림 [(코드, side, 수량, 값)]과 그날 주문 결과 글 목록."""
    done, notes = [], []
    for o in orders or []:
        if not str(o.get("key", "")).startswith(day + ":"):
            continue
        st = str(o.get("status") or "")
        ok = st.startswith("접수")
        notes.append(f"{o.get('code')} {'매수' if o.get('side') == 'buy' else '매도'} {int(o.get('qty') or 0):,}주 · "
                     + ("접수" + (" (줄임)" if "줄임" in st else "") if ok else short_fail(st)))
        if ok and o.get("price"):
            q = int(o.get("filled") if o.get("filled") is not None else o.get("qty") or 0)
            if q:
                done.append((str(o["code"]), o["side"], q, float(o["price"])))
    return done, notes


def short_fail(status):
    """'실패 · 까닭' → '실패(까닭)'. 증권사 설명 글만(응답 본문이 아님)."""
    s = str(status or "").strip()
    if not s:
        return "결과 없음"
    if " · " in s:
        head, why = s.split(" · ", 1)
        return f"{head}({why.rstrip('.')})"
    return s


def held_before(orders, day):
    """그날 앞까지 '접수'된 주문을 쌓은 수량(장부 held를 날짜별로 되살림)."""
    qty = {}
    for o in sorted(orders or [], key=lambda o: str(o.get("key", ""))):
        if str(o.get("key", ""))[:8] >= day or not str(o.get("status") or "").startswith("접수"):
            continue
        q = int(o.get("filled") if o.get("filled") is not None else o.get("qty") or 0)
        c = str(o.get("code"))
        qty[c] = qty.get(c, 0) + (q if o.get("side") == "buy" else -q)
        if qty[c] <= 0:
            qty.pop(c)
    return qty


def order_set(orders):
    """[(코드, side, ...)] → {(코드, side)} — 같음 판단은 '무엇을 사고팔기로 했나'만 봄(수량은 계좌 크기에 따라 다름)."""
    return {(str(o[0]), o[1]) for o in orders}


def verdict(research, actual):
    """research: 연구 주문 목록 또는 None(자료 기다림) · actual: 실제 결정 주문 목록 또는 None(안 돎 · 기록 없음).
    돌려줌: '같음' · '다름' · '자료 기다림' · '같음(둘 다 할 일 없음 · 운영은 안 돎)'."""
    if research is None:
        return "자료 기다림"
    if actual is None:
        return "다름(운영 안 돎)" if research else "같음(할 일 없음 · 운영은 안 돎)"
    return "같음" if order_set(research) == order_set(actual) else "다름"


def describe(orders, names=None):
    """주문 목록을 쉬운 글로."""
    names = names or {}
    if not orders:
        return "사고팔 것 없음"
    return " · ".join(f"{names.get(o[0], o[0])} {'매수' if o[1] == 'buy' else '매도'} {int(o[2]):,}주"
                      + (f"({str(o[3]).split(' — ')[0]})" if len(o) > 3 and o[3] and not isinstance(o[3], (int, float)) else "")
                      for o in orders)


def cap_room(E, nav, held_value):
    """흔들림 상한이 허락하는 더 살 돈 = E × 계좌 − 든 것(0 아래면 0)."""
    return max(0.0, E * nav - held_value)


def overlay_actual(state_versions, orders, day, prev_day, prev_seen=None, need=None, t0_missing=False):
    """덧붙임 실제: 그날 state(마지막 판) · 그날 주문으로 무엇이 일어났는지 글로.
    prev_seen = 어제 KODEX 200 종가가 저장소에 처음 올라온 때(한국 시각 'YYYYMMDDHHMM' · 모르면 None).
    그날 15:13보다 늦게 올라왔으면 stale(어제 종가 없어 안 맞춤).
    need = 그날 앞 장부로 보면 맞춰야 하는 날인가(needs_rebalance) · t0_missing = 같은 날 바구니도 어제 거래일을 못 알았나."""
    st = None
    for v in state_versions:
        if v.get("last_day") == day:
            st = v
    todays = [o for o in orders or [] if str(o.get("key", "")).startswith(day + ":")]
    if st is None and not todays:
        return None, "안 돎(기록 없음)"
    if todays:
        return [(o["code"], o["side"], int(o.get("qty") or 0)) for o in todays], "맞춤 시도"
    if prev_seen and prev_seen > day + "1513":
        return [], f"어제({prev_day}) KODEX 200 종가가 그날 {prev_seen[8:10]}:{prev_seen[10:]}에야 저장소에 올라와 맞추지 않음(stale)"
    if need and t0_missing:
        return [], "맞출 날인데 주문 없음 — 같은 날 바구니도 어제 거래일을 못 알아냄 → 어제 거래일 조회 실패로 stale 처리된 것으로 보임(작업 기록 미확인)"
    if need:
        return [], "맞출 날인데 주문 없음(까닭 미확인)"
    if need is False:
        return [], "주문 없음(맞출 날 아님)"
    return [], "주문 없음(까닭 미확인)"


def first_seen(vers, day):
    """etf-data 판들 [(올린 때, 내용)]에서 그날 종가가 처음 들어온 때. 못 찾으면 None."""
    for at, body in vers:
        if any(str(d) == day for d, c in (body.get("closes") or []) if c):
            return at if at != "999999999999" else None
    return None


def render_md(rows, limit=20):
    """diff.json 날 줄들 → 쉬운 한국어 표(최근 limit 거래일)."""
    days = sorted({r["date"] for r in rows})[-limit:]
    out = ["# 연구 셈 vs 실제 모의투자 — 날마다 차이",
           "",
           f"만든 때: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')}(한국 시각) · 시작 {START} · 코드 research/shadow_diff.py",
           "",
           "- 연구 셈은 15:10 · 15:20 값 자리에 **그날 종가**를 씀(운영은 그 시각 현재가). 그 밖에는 그날 앞 자료만 씀(미래 참조 없음).",
           "- 손익 차이 = 연구 손익 − 실제 손익(그날 · 원 · 비용 뺌 없음 · 실제 체결값은 장부의 주문 때 값이라 어림).",
           "- '자료 기다림' = 그날 종가가 아직 안 모임(다음 실행에 다시 셈).",
           ""]
    tot = {}
    for d in reversed(days):
        out += [f"## {d[:4]}-{d[4:6]}-{d[6:]}", "", "| 봇 | 연구 결정 | 실제 결정 | 주문 결과 | 같나 | 손익 차이(연구−실제) |", "|---|---|---|---|---|---|"]
        for r in [x for x in rows if x["date"] == d]:
            gap = r.get("gap")
            g = "—" if gap is None else f"{gap / 1e4:+,.0f}만 원" + (f"({r['gap_pct']:+.2f}%)" if r.get("gap_pct") is not None else "")
            if gap is not None:
                tot[r["bot"]] = tot.get(r["bot"], 0.0) + gap
            cell = [r["bot"], r["research"], r["actual"], r.get("result") or "—", r["match"], g]
            out.append("| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in cell) + " |")
        out.append("")
    if tot:
        out += ["## 쌓인 손익 차이(셀 수 있었던 날만)", ""]
        out += [f"- {b}: {v / 1e4:+,.0f}만 원" for b, v in tot.items()]
        out.append("")
    return "\n".join(out)


# ───────────────────────── 자료 읽기 ─────────────────────────

def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(Path.cwd()), timeout=60)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def versions(path, since):
    """git 기록에서 그 파일의 판들 [(올린 때 한국 시각 'YYYYMMDDHHMM', 내용)] 오래된 → 새것. 지금 파일도 끝에 붙임."""
    out = []
    for line in reversed(_git("log", f"--since={since}", "--format=%H %ct", "--", path).split("\n")):
        if not line.strip():
            continue
        sha, ts = line.split()
        body = _git("show", f"{sha}:{path}")
        try:
            out.append((datetime.fromtimestamp(int(ts), KST).strftime("%Y%m%d%H%M"), json.loads(body)))
        except ValueError:
            continue
    cur = _load(path, None)
    if cur is not None:
        out.append(("999999999999", cur))
    return out


def before_start(path, start):
    """시작일 앞(전날 끝) 마지막 판. git 기록이 얕으면 None."""
    t = datetime.strptime(start, "%Y%m%d").replace(tzinfo=KST)
    sha = _git("rev-list", "-1", f"--before={t.isoformat()}", "HEAD", "--", path).strip()
    if not sha:
        return None
    try:
        return json.loads(_git("show", f"{sha}:{path}"))
    except ValueError:
        return None


def closes_of(code):
    import acc_cap
    return acc_cap.series(code)


# ───────────────────────── 1일봉(연구 셈) ─────────────────────────

def calm_for(day):
    """그날(없으면 그 앞 가장 늦은 날) study/a_group.json의 고요 문턱 — 운영 daily_live와 같은 값."""
    best = None
    for _, body in versions("study/a_group.json", "60 days ago"):
        d = str(body.get("date") or "")
        if d and d <= day and body.get("calm_edge") is not None and (best is None or d >= best[0]):
            best = (d, float(body["calm_edge"]))
    return best[1] if best else None


def daily_found(day, prev, prices, cache):
    """그날 종가로 final_group.compute(운영과 같은 범위 · 같은 문턱). 캐시에 남김. 자료가 덜 왔으면 None."""
    if day in cache:
        return cache[day]
    import caps
    import final_group
    yest = [{"code": c, "date": prev, "price": dict(v["rows"])[prev]} for c, v in prices.items() if prev in dict(v["rows"])]
    if not yest:
        return None
    caps.tag(yest, 150)
    pool = {r["code"] for r in yest if (r.get(caps.RANK) or 999) <= 150}
    live = {c: {"name": prices[c]["name"], "rows": [r for r in prices[c]["rows"] if r[0] <= day]} for c in pool}
    live = {c: v for c, v in live.items() if v["rows"] and v["rows"][-1][0] == day}
    if len(live) < len(pool) * 0.9:
        return None
    found = final_group.compute(live, calm=calm_for(day))
    if found.get("date") != day:
        return None
    aligned = {}
    for c, v in live.items():
        form = final_group.lines_now([x for _, x in v["rows"]])
        aligned[c] = bool(form and form.get("정배열"))
    out = {"breadth": found.get("breadth"), "aligned": aligned,
           "picks": [{k: p.get(k) for k in ("code", "name", "갈래", "추세 기울기", "정배열일수")} for p in found.get("picks", [])]}
    cache[day] = out
    return out


def daily_research(state, day, found, prices, nav):
    """1일봉 하루(연구 = 그날 종가). 돌려줌: (주문 [(코드, side, 수량, 까닭)], 새 state, 체결 [(코드, side, 수량, 값)])."""
    import daily_live as D
    import final_group
    cands = []
    for one in found["picks"]:
        code = one["code"]
        if D.target_cut(code, day):
            continue
        vols = _load(Path("volume-data") / f"{code}.json", {})
        k = (vols.get("칸") or []).index("거래량") if "거래량" in (vols.get("칸") or []) else None
        tv = next((row[k] for row in vols.get("날") or [] if k is not None and str(row[0]) == day), None)
        cands.append({**one, "추세문": final_group.RULE_DOOR in (one.get("갈래") or []), "3일연속": D.steady3(code, day),
                      "거래량비": D.volume_ratio(code, day, tv)})
    close = {c: dict(v["rows"]).get(day) for c, v in prices.items()}
    held = state.get("positions", {})
    sub = {c: {"name": prices[c]["name"], "rows": [r for r in prices[c]["rows"] if r[0] <= day]}
           for c in set(held) | {x["code"] for x in cands} if c in prices}
    import lab
    steps = lab.moves(sub)
    idx = {c: len(v["rows"]) - 1 for c, v in sub.items()}
    kin_ok = D.kin_checker(steps, idx, {c: [str(d) for d, _ in v["rows"]] for c, v in sub.items()},
                           {c: p.get("bought") for c, p in held.items()})
    prev_close = {}
    for c, v in prices.items():
        rows = [r for r in v["rows"] if r[0] < day]
        if rows:
            prev_close[c] = rows[-1][1]
    rate = {c: (close[c] / prev_close[c] - 1) * 100 for c in close if close.get(c) and prev_close.get(c)}
    sells, buys = D.decide(state, cands, {c: x for c, x in close.items() if x}, found["aligned"], rate, kin_ok)
    st = json.loads(json.dumps(state))
    slot = nav * D1_SHARE / D.SLOTS
    orders, fills = [], []
    for x in sells:
        p = held[x["code"]]
        q = int(p.get("qty") or round(p["칸"] * slot / p["price"]))
        q = q if x["칸"] >= p["칸"] else int(round(q * x["칸"] / p["칸"]))
        orders.append((x["code"], "sell", q, x["why"]))
        fills.append((x["code"], "sell", q, close[x["code"]]))
    for x in buys:
        q = math.floor(x["칸"] * slot / close[x["code"]]) if close.get(x["code"]) else 0
        if q >= 1:
            orders.append((x["code"], "buy", q, x["why"]))
            fills.append((x["code"], "buy", q, close[x["code"]]))
    D.settle(st, day, sells, buys, {c: x for c, x in close.items() if x})
    for c, side, q, _ in fills:                          # 연구 길의 수량(손익 셈용)
        if c in st["positions"]:
            st["positions"][c]["qty"] = (int(held.get(c, {}).get("qty") or 0) - q) if side == "sell" else q
    return orders, st, fills


# ───────────────────────── 하루 실제(장부) ─────────────────────────

def last_of_day(vers, day, key="date"):
    """같은 날짜의 판 가운데 마지막."""
    got = None
    for _, v in vers:
        if isinstance(v, dict) and str(v.get(key)) == day:
            got = v
    return got


# ───────────────────────── 하루 셈 전체 ─────────────────────────

def run(until=None):
    import basket_live
    import idle_live
    import overlay_live
    import acc_cap
    import study
    OUT.mkdir(exist_ok=True)
    cache = _load(CACHE, {}) or {}
    cache.setdefault("daily", {})
    since = (datetime.strptime(START, "%Y%m%d") - timedelta(days=10)).strftime("%Y-%m-%d")
    led = {k: versions(p, since) for k, p in LEDGERS.items()}
    led["k200"] = versions("etf-data/069500.json", since)
    books = {b: (_load(p, {}) or {}).get("orders", []) for b, p in BOOKS.items()}
    cal = sorted(d for d in closes_of("069500"))
    now = datetime.now(KST)
    today = now.strftime("%Y%m%d")
    ran = {str(v.get("date")) for k in ("daily_today", "idle_today", "basket_today") for _, v in led[k] if isinstance(v, dict)}
    days = sorted({d for d in cal if d >= START} | {d for d in ran if d >= START and d <= today})
    if until:
        days = [d for d in days if d <= until]
    allcal = sorted(set(cal) | set(days))
    prev_of = {d: max([x for x in allcal if x < d], default=None) for d in days}
    prices = study.load_prices()
    names = {c: v["name"] for c, v in prices.items()}
    names.update(idle_live.NAME)
    names.update(overlay_live.NAME)
    etf = {c: closes_of(c) for c in sorted(set(idle_live.CODES) | {"122630", "114800"})}

    def close(code, d):
        if code in etf:
            return etf[code].get(d)
        return dict(prices.get(code, {}).get("rows", [])).get(d)

    # 연구 길의 출발점 = 시작 전날 실제 장부
    nav = None
    for _, v in led["overlay_state"]:
        if v.get("nav") and str(v.get("nav_day", "")) >= START:
            nav = float(v["nav"])
            break
    nav = nav or 1e8
    s_idle = before_start(LEDGERS["idle_state"], START) or {"positions": {}, "cool": 0}
    s_idle.pop("closed", None)
    s_daily = before_start(LEDGERS["daily_state"], START) or {"positions": {}, "closed": []}
    s_basket = before_start(LEDGERS["basket_state"], START) or {"positions": {}, "last": {}}
    s_basket.pop("closed", None)
    s_over = {"held": {}, "applied": None, "rebalanced_month": None}
    rq = {b: held_before(books[b], START) for b in ("빈칸 엔진", "사건 바구니", "덧붙임")}
    rq["1일봉"] = {}
    events = basket_live.load_events()
    rows_out, stop = [], None
    ov_rows = overlay_live.closes()
    ov_states = overlay_live.states(ov_rows)
    for d in days:
        prev = prev_of[d]
        res = {}
        rq_prev = {b: dict(v) for b, v in rq.items()}
        rq_prev["덧붙임"] = dict(s_over["held"])
        if stop:
            for b in BOTS:
                res[b] = {"orders": None, "note": f"앞날({stop}) 연구 셈이 자료를 기다려 이어 갈 수 없음", "fills": None}
        else:
            # 15:10 사건 바구니(t0 = 어제 거래일 · 사건 · 반응은 t0 종가까지 → 판단은 그날 앞 자료만)
            t0 = prev
            before = max([x for x in allcal if x < t0], default=None) if t0 else None
            react, inside = basket_live.reactions(prices, t0, before) if before else ({}, set())
            ev = basket_live.todays_events(events, t0, before) if before else []
            dpos = {x: i for i, x in enumerate(allcal)}
            sofar = [x for x in allcal if x <= d]

            def days_since(x):
                return len(sofar) - 1 - dpos[x] if x in dpos else sum(1 for y in sofar if y > x)
            bnow = {c: close(c, d) for c in set(rq["사건 바구니"]) | {c for c, _ in ev if c in inside}}
            d_val = sum(q * (close(c, d) or close(c, prev) or 0) for c, q in rq["1일봉"].items())
            base_hold = {**rq["1일봉"], **rq["사건 바구니"], **rq["빈칸 엔진"]}
            hold_val = sum(q * (close(c, prev) or 0) for c, q in base_hold.items())
            cash = nav - hold_val
            sd, why_sd = acc_cap.sigma(d, base_hold)
            E = acc_cap.allowed_from(sd)
            room = cap_room(E, nav, hold_val)
            if any(v is None for v in bnow.values()):
                res["사건 바구니"] = {"orders": None, "note": "그날 종가 기다림"}
            else:
                o, s_basket, why_b = basket_live.step(s_basket, d, t0, days_since, ev, react, inside, rq["사건 바구니"], bnow,
                                                      capital=max(0.0, nav * BASKET_SHARE - d_val), avail=min(cash, room), names=names)
                f = [(c, s, q, bnow[c]) for c, s, q, _ in o]
                res["사건 바구니"] = {"orders": o, "fills": f,
                                     "note": f"t0 {t0} · 사건 {len(ev)}건" + (" · " + why_b[0] if why_b else "")}
            # 15:10 빈칸 엔진(그날 종가를 15:10 값 자리에)
            px, ok = {}, True
            for c in idle_live.CODES:
                h = [v for x, v in sorted(etf[c].items()) if x <= d]
                if etf[c].get(d) is None:
                    ok = ok and c not in (idle_live.K200, idle_live.Q150, idle_live.DOL)
                    continue
                if len(h) >= 25:
                    px[c] = __import__("numpy").array(h)
            f_d = daily_found(d, prev, prices, cache["daily"]) if prev else None
            breadth = f_d["breadth"] if f_d else None
            if not ok:
                res["빈칸 엔진"] = {"orders": None, "note": "그날 ETF 종가 기다림"}
            else:
                bnote = ""
                if breadth is None:          # 주식 종가가 아직이면 운영이 그날 쓴 시장 폭을 빌림(공개)
                    it = last_of_day(led["idle_today"], d)
                    breadth = it.get("breadth") if it else None
                    bnote = " · 시장 폭은 운영 15:10 값 빌림(종가 자료 아직)" if breadth is not None else ""
                if breadth is None:
                    res["빈칸 엔진"] = {"orders": None, "note": "시장 폭 기다림"}
                else:
                    if res["사건 바구니"]["orders"]:
                        rq["사건 바구니"] = apply_trades(rq["사건 바구니"], res["사건 바구니"]["fills"])
                    now_p = {c: etf[c][d] for c in idle_live.CODES if etf[c].get(d)}
                    b_val = sum(q * (close(c, d) or 0) for c, q in rq["사건 바구니"].items())
                    used = d_val / nav
                    b_spent = sum(q * px_ * (1 if sd_ == "buy" else -1) for _, sd_, q, px_ in res["사건 바구니"].get("fills") or [])
                    e_free = nav - d_val - b_val - sum(q * now_p.get(c, 0) for c, q in rq["빈칸 엔진"].items())
                    e_cash = min(e_free, max(0.0, room - max(0.0, b_spent)))
                    o, s_idle, why_i = idle_live.step(s_idle, d, px, float(breadth), used, nav, max(0.0, e_cash), rq["빈칸 엔진"], now_p,
                                                      idle_live.week_end(d), reserve=b_val)
                    f = [(c, s, q, now_p[c]) for c, s, q, _ in o]
                    res["빈칸 엔진"] = {"orders": o, "fills": f,
                                       "note": f"시장 폭 {breadth} · 1일봉 쓴 몫 {used * 100:.0f}% · 흔들림 상한 살 돈 {room / 1e4:,.0f}만 원" + bnote}
            # 15:13 덧붙임(국면 = 어제 장 끝까지 · 15:10 엔진 · 바구니 체결 뒤 바탕 현금으로)
            if res["빈칸 엔진"]["orders"] is not None:
                rq["빈칸 엔진"] = apply_trades(rq["빈칸 엔진"], res["빈칸 엔진"]["fills"])
            reg = ov_states.get(prev) if prev else None
            if reg is None:
                res["덧붙임"] = {"orders": None, "note": "어제 KODEX 200 종가 없음"}
            elif not overlay_live.needs_rebalance(s_over, reg, d):
                res["덧붙임"] = {"orders": [], "fills": [], "note": f"국면 {reg} · 맞출 날 아님"}
            else:
                code_new, fe = overlay_live.TARGET[reg]
                o = [(c, "sell", q, f"국면 {reg}") for c, q in s_over["held"].items() if c != code_new]
                pn = close(code_new, d) if code_new else None
                if code_new and not pn:
                    res["덧붙임"] = {"orders": None, "note": f"국면 {reg} · 그날 종가 기다림"}
                else:
                    base_cash = nav - sum(q * (close(c, d) or 0) for c, q in {**rq["1일봉"], **rq["사건 바구니"], **rq["빈칸 엔진"]}.items())
                    f_room = min(fe, max(0.0, base_cash) / nav) if code_new else 0.0
                    want = math.floor(f_room * nav / pn) if code_new else 0
                    diff = want - s_over["held"].get(code_new, 0) if code_new else 0
                    if diff:
                        o.append((code_new, "buy" if diff > 0 else "sell", abs(diff), f"국면 {reg} · 목표 몫 {f_room:.2f}"))
                    fl = [(c, s, q, close(c, d)) for c, s, q, _ in o]
                    if any(x[3] is None for x in fl):
                        res["덧붙임"] = {"orders": None, "note": f"국면 {reg} · 그날 종가 기다림"}
                    else:
                        res["덧붙임"] = {"orders": o, "fills": fl, "note": f"국면 {reg}(어제 장 끝) · 목표 몫 {f_room:.2f}"}
                        s_over = {"held": {code_new: want} if want else {}, "applied": reg, "rebalanced_month": d[:6]}
            # 15:20 흔들림 상한(σ = 전날까지 · 바탕 봇 든 것 · 덧붙임은 빼고 봄 — 운영 base_view와 같게)
            base_now = {**rq["1일봉"], **rq["사건 바구니"], **rq["빈칸 엔진"]}
            sd2, why2 = acc_cap.sigma(d, base_now)
            E2 = acc_cap.allowed_from(sd2)
            cl = {c: close(c, d) for c in base_now}
            if any(v is None for v in cl.values()):
                res["흔들림 상한"] = {"orders": None, "note": "그날 종가 기다림"}
            else:
                hv = sum(q * cl[c] for c, q in base_now.items())
                bal = {"cash": nav - hv, "value": hv, "positions": [{"code": c, "quantity": q} for c, q in base_now.items()]}
                plan, fr = acc_cap.plan_trim(bal, E2, {"1d": rq["1일봉"], "basket": rq["사건 바구니"], "idle": rq["빈칸 엔진"]})
                o = [(c, "sell", q, f"흔들림 상한 E {E2:.2f}") for _, c, q in plan]
                res["흔들림 상한"] = {"orders": o, "fills": [(c, s, q, cl[c]) for c, s, q, _ in o],
                                    "note": f"허용 E {E2:.2f}(σ {'없음' if sd2 is None else format(sd2 * 100, '.2f') + '%'} · {why2}) · 든 것 {hv / nav * 100:.0f}%"
                                            + (f" · {fr * 100:.0f}% 덜어냄" if plan else " · 덜어낼 것 없음")}
                for book, c, q in plan:
                    k = {"1d": "1일봉", "basket": "사건 바구니", "idle": "빈칸 엔진"}[book]
                    rq[k] = apply_trades(rq[k], [(c, "sell", q, 0)])
            # 15:20 1일봉(그날 종가 · 전날 시총 150위 안)
            if f_d is None:
                res["1일봉"] = {"orders": None, "note": "그날 주식 종가 기다림"}
            else:
                o, s_daily, fl = daily_research(s_daily, d, f_d, prices, nav)
                res["1일봉"] = {"orders": o, "fills": fl,
                               "note": f"시장 폭 {f_d['breadth']} · 후보 {len(f_d['picks'])}"}
                rq["1일봉"] = apply_trades(rq["1일봉"], fl)
            if any(res[b]["orders"] is None for b in BOTS):
                stop = d
        # ── 실제 ──
        act = actual_day(d, prev, led, books, ov_states)
        for b in BOTS:
            r, a = res[b], act[b]
            gap = None
            if r.get("fills") is not None and a.get("fills") is not None and b in BOOKS and prev:
                cl_now = {}
                cl_prev = {}
                codes = set(a["qty_prev"]) | set(rq_prev.get(b, {})) | {x[0] for x in r["fills"] + a["fills"]}
                for c in codes:
                    cl_now[c], cl_prev[c] = close(c, d), close(c, prev)
                ra = mark_pnl(rq_prev.get(b, {}), r["fills"], cl_prev, cl_now)
                aa = mark_pnl(a["qty_prev"], a["fills"], cl_prev, cl_now)
                gap = None if ra is None or aa is None else round(ra - aa)
            rows_out.append({"date": d, "bot": b,
                             "research": (describe(r["orders"], names) if r["orders"] is not None else "자료 기다림")
                                         + (f" — {r['note']}" if r.get("note") else ""),
                             "actual": a["text"], "result": a.get("result"), "match": ("미확인(실제 15:20 기록 없음)" if a.get("unknown") and r["orders"] is not None
                                       else "다름(실제는 단계 실패 → 새 매수 멈춤)" if a.get("failed") and r["orders"] is not None
                                       else verdict(r["orders"], a["orders"])),
                             "gap": gap, "gap_pct": None if gap is None else round(gap / nav * 100, 2)})
    body = {"made": now.strftime("%Y-%m-%d %H:%M"), "start": START,
            "note": "연구 = 그날 종가로 판단 · 체결(15:10 · 15:20 값 자리) · 그 밖은 그날 앞 자료만. 손익 차이는 어림(비용 없음).",
            "rows": rows_out}
    (OUT / "diff.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "DIFF.md").write_text(render_md(rows_out), encoding="utf-8")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return body



def overlay_need(st, reg, d):
    import overlay_live
    return overlay_live.needs_rebalance(st, reg, d)


def actual_day(d, prev, led, books, ov_states=None):
    """그날 실제(장부 · git 기록). 봇마다 {'orders': 결정 목록 또는 None, 'text', 'result', 'fills', 'qty_prev'}."""
    out = {}
    # 1일봉
    t = last_of_day(led["daily_today"], d)
    if t is None:
        out["1일봉"] = {"orders": None, "text": "안 돎(그날 기록 없음)"}
    else:
        o = [(x["code"], "sell", x["칸"], x.get("why")) for x in t.get("sells", [])] + \
            [(x["code"], "buy", x["칸"], x.get("why")) for x in t.get("buys", [])]
        txt = ("사고팔 것 없음" if not o else " · ".join(f"{x[0]} {'매수' if x[1] == 'buy' else '매도'} {x[2]}칸" for x in o)) \
            + f" — 시장 폭 {t.get('breadth')}" + (" · 늦게 돎" if t.get("late") else "")
        out["1일봉"] = {"orders": o, "text": txt}
    # 바구니
    t = last_of_day(led["basket_today"], d)
    if t is None:
        out["사건 바구니"] = {"orders": None, "text": "안 돎(그날 기록 없음)"}
    else:
        o = [(x["code"], x["side"], x["qty"], x.get("why")) for x in t.get("orders", [])]
        txt = describe(o) + (" — 어제 거래일을 못 알아 사건을 안 봄(t0 없음)" if not t.get("t0") else f" — t0 {t['t0']} · 사건 {len(t.get('events') or [])}건")
        out["사건 바구니"] = {"orders": o, "text": txt}
    # 빈칸 엔진
    t = last_of_day(led["idle_today"], d)
    if t is None:
        out["빈칸 엔진"] = {"orders": None, "text": "안 돎(그날 기록 없음)"}
    else:
        o = [(x["code"], x["side"], x["qty"], x.get("why")) for x in t.get("orders", [])]
        cap = next((w for w in t.get("why", []) if w.startswith("계좌 흔들림 상한") or "흔들림 상한" in w), "")
        out["빈칸 엔진"] = {"orders": o, "text": describe(o) + f" — 시장 폭 {t.get('breadth')} · 쓴 몫 {float(t.get('used') or 0) * 100:.0f}%"
                                                   + (f" · {cap}" if cap else "") + (" · 늦게 돎" if t.get("late") else "")}
    # 덧붙임
    before = [v for _, v in led["overlay_state"] if str(v.get("last_day") or "") < d]
    reg = (ov_states or {}).get(prev)
    need = overlay_need(before[-1] if before else {}, reg, d) if reg else None
    bt = last_of_day(led["basket_today"], d)
    o, why = overlay_actual([v for _, v in led["overlay_state"]], books["덧붙임"], d, prev,
                            first_seen(led["k200"], prev) if prev else None, need, bool(bt is not None and not bt.get("t0")))
    out["덧붙임"] = {"orders": o, "text": (describe(o) + " — " if o else "") + why}
    # 흔들림 상한
    logs = [x for _, v in led["cap_log"] if isinstance(v, list) for x in v if x.get("date") == d]
    lg = logs[-1] if logs else None
    it = last_of_day(led["idle_today"], d)
    room = next((w for w in (it or {}).get("why", []) if "흔들림 상한" in w), None)
    if lg is None:
        out["흔들림 상한"] = {"orders": None if it is None else [], "unknown": it is not None, "text": ("15:20 기록 없음" if it else "안 돎(그날 기록 없음)")
                                                                         + (f" · 15:10 {room}" if room else "")}
    elif lg.get("failed"):
        out["흔들림 상한"] = {"orders": [], "failed": True, "text": "15:20 덜어내기 단계 실패 → 그날 새 매수 멈춤" + (f" · 15:10 {room}" if room else ""),
                            "result": f"실패({lg['failed'].split('.')[0]})"}
    else:
        o = [(x["code"], "sell", 0, None) for x in lg.get("orders", [])]
        out["흔들림 상한"] = {"orders": o, "text": f"허용 E {lg.get('E')} · 든 것 {float(lg.get('held_share') or 0) * 100:.0f}%"
                                                + (f" · {float(lg.get('trim_f') or 0) * 100:.0f}% 덜어냄" if o else " · 덜어낼 것 없음"),
                            "result": " · ".join(f"{x['code']} {x['status']}" for x in lg.get("orders", [])) or None}
    # 주문 결과 · 체결 어림 · 전날 수량
    for b, path in BOOKS.items():
        fills, notes = book_trades(books[b], d)
        out[b]["fills"] = fills
        out[b]["qty_prev"] = held_before(books[b], d)
        if notes:
            out[b]["result"] = " · ".join(notes)
        elif out[b]["orders"]:
            out[b]["result"] = "주문 기록 없음"
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="연구 셈 vs 실제 모의투자 날마다 차이(읽기 전용)")
    ap.add_argument("--until", help="이 날(YYYYMMDD)까지만")
    a = ap.parse_args(argv)
    body = run(a.until)
    days = sorted({r["date"] for r in body["rows"]})
    print(f"그림자 견주기 저장: shadow/diff.json · shadow/DIFF.md · {days[0] if days else '-'} ~ {days[-1] if days else '-'} · 줄 {len(body['rows'])}")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
