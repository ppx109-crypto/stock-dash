"""BOOST-0001-D 1단계 · 2a단계(사전등록 판 3 §4-1 반례) 시험.

- 공통 문(gates) · 판 고정 달력(trade_calendar) · 시작 전 점검(gate_smoke) · D6(저장소 맞추기 실패) · D1(15:05 같은 작업 안 다시 셈) ·
  덧붙임 buy_ok(교체면 매도만 + applied = "pending") · 판단 기록 곁 칸 gates · 기록 · 문 파일 쓰기 실패가 매매를 멈추지 않음.
- **문이 모두 열리면 고치기 전 코드와 주문 · 장부 · 알림이 바이트까지 같음**: 같은 가짜 세상(가짜 증권사 · 가짜 시계 · 임시 폴더)을
  고치기 전 판(BASE · origin/main)으로 돌린 결과를 tests/fixtures/boost_d_golden.json에 얼려 두고 지금 코드 결과와 견줌.
  BASE 커밋이 있는 곳(로컬)에서는 그 얼린 결과가 정말 BASE 코드의 결과인지도 다시 돌려 확인(얕은 받기 CI에서는 그 하나만 건너뜀).
- 2a단계: D2(엔진 ETF 마지막 날 = 달력 P → 엔진만 닫음) · D4 두 층(풀 건강도 89% / 90% · 후보 단계 주문 안전 거르기 ·
  낡은 상위 1 + 정상 차순위 1 + 빈 칸 1 → 정상 차순위를 삼) · 수급 수집 목표 P · D7 거래량 건너뛰기 · 감사 셈 문 양방향(끝까지 이은 시험).
- 실제 증권사 · DART를 부르지 않음 · 비밀값 없음(가짜 키 글자만)."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
BASE = "f1ee92c6f1f61af54d73ac1183c71c822f458123"          # 고치기 전 판(origin/main · 이 가지가 갈라진 곳)
CHANGED = ("paper_trade.py", "idle_live.py", "daily_live.py", "basket_live.py", "overlay_live.py", "hourly_a.py")
GOLDEN = ROOT / "tests" / "fixtures" / "boost_d_golden.json"
SCENARIOS = ("engine", "engine_room", "engine_swap", "daily", "daily_multi")
DAY, P = "20261111", "20261110"                            # 수요일 · 앞 거래일(화)
HOLIDAYS_2026 = ("20261005", "20261009", "20261225", "20261231")
MARK = "@@BOOSTD@@"
NEW_ONLY = ("gates/", "idle-live/near-now.json")           # 새 코드만 쓰는 기록(문 상태 · D1 사본) — 바이트 비교에서 뺌
ENV = {"PAPER_TRADING": "on", "PAPER_START": "", "KIS_PAPER_APP_KEY": "가짜", "IDLE_START": "", "DAILY_START": "",
       "MIX54": "on", "MIX54_START": "20261001", "PAPER_ROOM_WAIT": "0", "OVERLAY_FILL_TRIES": "2",
       "OVERLAY_BUY_RETRY_WAIT": "0"}
DROP_ENV = ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "LIVE_GIT_SYNC", "ACC_CAP", "ACC_CAP_START", "DISCORD_WEBHOOK_URL",
            "DISCORD_DIGEST", "DISCORD_BUFFER", "RUNNER_TEMP", "KIS_APP_KEY", "KIS_APP_SECRET", "KIS_PAPER_APP_SECRET",
            "KIS_PAPER_ACCOUNT", "PAPER_SHARE_1H", "PAPER_SHARE_1D", "PAPER_SHARE_15M", "PAPER_SHARE_BASKET")


# ───────────────────────── 가짜 세상 ─────────────────────────

def weekdays_until(end, n):
    """end(포함)까지 평일 n개(가짜 거래일)."""
    out, d = [], date(int(end[:4]), int(end[4:6]), int(end[6:]))
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return out[::-1]


def calendar_body(year, holidays=(), special=None, sha=None):
    """판 고정 달력 판 본문(그 해 모든 날 · 주말 · 휴장 = null · 평일 09:00 ~ 15:30)."""
    import trade_calendar
    days, d = {}, date(year, 1, 1)
    while d.year == year:
        k = d.strftime("%Y%m%d")
        days[k] = None if d.weekday() >= 5 or k in holidays else {"open": "0900", "close": "1530"}
        d += timedelta(days=1)
    days.update(special or {})
    return {"source_url": "https://example.invalid/krx-holiday-notice", "notice_no": f"시험-{year}",
            "fetched_at_utc": "2026-11-01T00:00:00Z", "effective_from": f"{year}0101", "parser_version": "시험 1",
            "raw_sha256": "0" * 64, "normalized_sha256": sha or trade_calendar.normalized_digest(days), "days": days}


def write_calendar(folder, year, version=1, **kw):
    p = Path(folder) / f"krx-{year}-v{version}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(calendar_body(year, **kw), ensure_ascii=False), encoding="utf-8")
    return p


STOCKS = {"000010": ("가", 50000.0), "000020": ("나", 10000.0), "000030": ("다", 20000.0), "000040": ("라", 5000.0)}
FOUND = {"date": DAY, "breadth": 40.0, "picks": [{"code": "000030", "name": "다", "갈래": ["추세 규칙"]}], "b_group": []}
# 1일봉 후보 여럿(기울기 차례 · 빈 칸 자르기까지 고치기 전과 같은지 · 2a단계 얼린 장면 daily_multi)
FOUND_MULTI = {"date": DAY, "breadth": 40.0, "b_group": [], "picks": [
    {"code": "000040", "name": "라", "갈래": ["정배열 추세"], "추세 기울기": 2.0},
    {"code": "000030", "name": "다", "갈래": ["추세 규칙"], "추세 기울기": 3.0},
    {"code": "000020", "name": "나", "갈래": ["정배열 추세"], "추세 기울기": 1.0}]}
FLOW_COLS = ["date", "개인", "외국인", "기관", "투신", "연기금", "사모", "종가"]


def flow_body(code, end=P, n=10, hole=None, empty=None):
    """가짜 investor-data 한 종목(end까지 평일 n줄 · 외국인 · 투신 +, 개인 −) · hole = 뺄 날 · empty = 칸을 비울 (날, 칸)."""
    rows = []
    for d in weekdays_until(end, n):
        if d == hole:
            continue
        row = [d, -10.0, 5.0, 3.0, 4.0, 1.0, 1.0, 100.0]
        if empty and empty[0] == d:
            row[FLOW_COLS.index(empty[1])] = None
        rows.append(row)
    return {"code": code, "cols": FLOW_COLS, "rows": rows, "처음까지": True}


class Clock:
    """가짜 시계(한국 시각) — time.sleep은 기다리지 않고 시계만 앞으로."""

    def __init__(self, hms):
        self.t = datetime(int(DAY[:4]), int(DAY[4:6]), int(DAY[6:]), *hms, tzinfo=KST).timestamp()
        self.lock = threading.Lock()

    def sleep(self, s):
        with self.lock:
            self.t += float(s or 0)

    def dt_class(self):
        real, clock = datetime, self

        class FakeDT(real):
            @classmethod
            def now(cls, tz=None):
                return real.fromtimestamp(clock.t, tz)
        return FakeDT


class Client:
    """가짜 시세 연결(조회만)."""

    def __init__(self, px, missing=()):
        self.px, self.missing = dict(px), set(missing)

    def authorize(self):
        return None

    def quote(self, code):
        import broker_kis
        if code in self.missing or code not in self.px:
            raise broker_kis.BrokerError("가짜 시세 없음")
        return {"price": self.px[code], "rate": 0.0, "volume": 1000.0, "name": code}


class Broker:
    """가짜 모의 계좌: 시장가는 지금 값에 바로 체결 · 비용 0.05% · 살 수 있는 수량 = 현금 ÷ (값 × 1.36)."""

    def __init__(self, cash, positions, px):
        self.cash, self.pos, self.px, self.orders = float(cash), dict(positions), dict(px), []

    def raw(self):
        ps = [{"code": c, "name": c, "quantity": q, "price": self.px[c], "value": q * self.px[c]} for c, q in sorted(self.pos.items()) if q > 0]
        return {"cash": self.cash, "value": sum(p["value"] for p in ps), "positions": ps}

    def balance(self, raw=False):
        import overlay_live
        return self.raw() if raw else overlay_live.base_view(self.raw())

    def buyable(self, code):
        return max(0, int(self.cash // (self.px[code] * 1.36)))

    def order(self, code, side, qty):
        import broker_kis
        qty = int(qty)
        if side == "buy":
            try:                          # 진짜 PaperBroker.order처럼 사기 전에 덧붙임 자리 내주기 · 매수가능 수량
                import overlay_live
                overlay_live.yield_for(self, code, qty)
            except Exception:
                pass
            can = self.buyable(code)
            if can < qty:
                if can < 1:
                    raise broker_kis.BrokerError("살 수 있는 수량이 0주")
                qty = can
            self.cash -= qty * self.px[code] * 1.0005
            self.pos[code] = self.pos.get(code, 0) + qty
        else:
            qty = min(qty, self.pos.get(code, 0))
            self.cash += qty * self.px[code] * 0.9995
            self.pos[code] = self.pos.get(code, 0) - qty
        self.last_qty = qty
        self.orders.append([code, side, qty])
        return str(len(self.orders))


def build_world(root, kind, opt):
    """임시 폴더에 가짜 자료 · 장부를 씀 → (시세표, 계좌, 주식 일봉)."""
    def w(rel, body):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    days = weekdays_until(P, 60)
    flat = kind == "engine_swap"                          # 횡보(KODEX 200 평평) → 덧붙임 교체(레버리지 → 인버스)
    series = {"069500": [100.0] * 60 if flat else [100.0 + 0.5 * k for k in range(60)],
              "138230": [100.0] * 60, "251340": [100.0] * 60, "229200": [100.0] * 60,
              "133690": [100.0] * 40 + [100.0 + 5.0 * (k + 1) / 20 for k in range(20)],
              "132030": [100.0] * 40 + [100.0 - 1.0 * (k + 1) / 20 for k in range(20)],
              "148070": [100.0] * 40 + [100.0 + 3.0 * (k + 1) / 20 for k in range(20)]}
    for code, xs in series.items():
        rows = [[d, x] for d, x in zip(days, xs)]
        w(f"etf-data/{code}.json", {"closes": rows[:-1] if code in opt.get("etf_stale", ()) else rows})   # etf_stale: P 줄이 빠짐(D2)
    px = {"069500": 100.0 if flat else 130.5, "138230": 100.0, "251340": 100.0, "229200": 100.0, "133690": 105.0,
          "132030": 99.0, "148070": 103.0, "122630": 10000.0, "114800": 5000.0}
    last5 = days[-5:] if opt.get("prices_last") is None else weekdays_until(opt["prices_last"], 5)
    prices = {}
    for i in range(50):
        code = f"{100 + i:06d}"
        prices[code] = {"name": f"종목{i}", "rows": [(d, 1000.0 + 10 * i + k) for k, d in enumerate(last5)]}
        px[code] = prices[code]["rows"][-1][1]
    for code, (name, v) in STOCKS.items():
        prices[code] = {"name": name, "rows": [(d, v) for d in last5]}
        px[code] = v
    for code in prices:                                   # 수급(D4): 기본은 모두 P까지 · flow_stale은 P−1에서 끝남 · flow_files로 바꿔 끼움
        w(f"investor-data/{code}.json", (opt.get("flow_files") or {}).get(code) or
          flow_body(code, end=weekdays_until(P, 2)[0] if code in opt.get("flow_stale", ()) else P))
    w("event-data/000040.json", {"rows": [{"date": P, "kind": "무상증자", "title": "주요사항보고서(무상증자결정)"}]})
    room = kind == "engine_room"                          # 현금이 적어 15:10 예방 자리 내주기(엔진 것을 팖)가 생김
    engine_qty, daily_qty = (10000, 10) if room else (1000, 100)
    w("idle-live/state.json", {"positions": {"138230": {"kind": "달러", "price": 100.0, "day": days[-4], "days": 3}},
                               "cool": 0, "last_day": P})
    w("idle-live/paper-orders.json", {"orders": [], "held": {"138230": engine_qty}})
    w("basket-live/state.json", {"positions": {"000020": {"day": days[-21], "price": 9000.0, "kind": "무상증자", "react": 0.0}},
                                 "last": {}})
    w("basket-live/paper-orders.json", {"orders": [], "held": {"000020": 200}})
    w("daily-live/paper-orders.json", {"orders": [], "held": {"000010": daily_qty}})
    cells = opt.get("daily_cells", 4)                     # 1일봉이 든 칸(daily_cells를 주면 팔지 않고 들고 감 → 빈 칸 = 10 − 이것)
    held_days = 1 if "daily_cells" in opt else 9          # 9 → 오늘 10거래일 기간 청산 · 1 → 그대로 들고 감
    d_pos = {"000010": {
        "code": "000010", "name": "가", "kind": "추세", "price": 45000.0, "peak": 50000.0, "max_close": 50000.0, "last_close": 50000.0,
        "칸": cells, "처음칸": cells, "days": held_days, "bought": days[-1 - held_days], "why": "① 추세 조건"}}
    if kind == "daily_multi":                             # 팔지 않는 둘째 종목 4칸 → 빈 칸 6(기울기 차례 · 자르기가 결과를 가름)
        d_pos["000100"] = {"code": "000100", "name": "종목0", "kind": "추세", "price": 1000.0, "peak": 1004.0, "max_close": 1004.0,
                           "last_close": 1004.0, "칸": 4, "처음칸": 4, "days": 1, "bought": days[-2], "why": "① 추세 조건"}
    w("daily-live/state.json", {"positions": d_pos, "closed": []})
    # 장중 판정(옛 꼴 · 15:05 · 오늘) — 고치기 전 코드는 이것으로 비켜 두기를 셈 · 새 코드는 검증 칸이 없어 쓰지 않고 15:05 다시 셈을 씀
    w("m15-live/near-now.json", opt.get("m15_body") or {
        "date": DAY, "at": f"{DAY[:4]}-{DAY[4:6]}-{DAY[6:]} 15:05", "breadth": 40.0,
        "picks": copy.deepcopy(FOUND["picks"]), "near": [], "picks_daily": copy.deepcopy(FOUND["picks"]), "near_daily": []})
    positions = {"000010": daily_qty, "000020": 200, "138230": engine_qty}
    if kind == "engine_swap":                             # 덧붙임이 레버리지 1,000주를 든 채 횡보로 바뀜
        positions["122630"] = 1000
        w("overlay-live/state.json", {"held": {"122630": 1000}, "B": 10000000.0, "applied": "상승",
                                      "rebalanced_month": "202611", "last_day": P, "signal_day": days[-2]})
    if opt.get("calendar", True):
        write_calendar(root / "calendar", 2026, holidays=HOLIDAYS_2026)
    if opt.get("smoke", True):
        w(f"gate-smoke/{DAY}.json", {"date": DAY, "ok": True, "version": 1, "sha256": None, "P": P, "reasons": [], "run_id": None})
    for rel in opt.get("block", ()):                      # 쓰기를 막을 자리(그 이름의 파일을 먼저 만들어 폴더를 못 만들게)
        w(rel, "막음")
    for rel in opt.get("block_dir", ()):                  # 그 이름의 폴더를 먼저 만들어 파일을 못 쓰게
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel, body in (opt.get("extra_files") or {}).items():
        w(rel, body)
    return px, Broker(500_000 if room else 50_000_000, positions, px), prices


def _snapshot_files(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            try:
                out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                out[p.relative_to(root).as_posix()] = None
    return out


def world_run(kind, **opt):
    """가짜 세상에서 봇 한 번(engine* = idle_live.run 15:05 시작 · daily = daily_live.run 15:20 시작) → 결과 dict.
    opt: sync_ok(저장소 맞추기 값을 바꿔 끼움) · refresh(hourly_a.refresh_near를 바꿔 끼움) · missing(시세 없는 코드) ·
    calendar · smoke(파일을 둘지) · live_p · prices_last · m15_body · block · block_dir · start(시 · 분 · 초) · spy(덧붙임 인자 기록) ·
    2a단계: etf_stale(P 줄이 빠진 엔진 ETF) · flow_stale(수급이 P−1에서 끝나는 종목) · flow_files · found(1일봉 후보) · daily_cells."""
    import importlib
    import acc_cap  # noqa: F401  (가짜 시계를 끼우기 전에 모두 불러 둠 · 실행 중 처음 불러 가짜 시계가 남지 않게)
    import audit_log  # noqa: F401
    import basket_live  # noqa: F401
    import broker_kis
    import caps
    import collect_kis_intraday
    import daily_live
    import data_guard
    import final_group
    import hourly_a
    import idle_live
    import lab
    import notify_discord
    import overlay_live
    import paper_trade
    import study
    for name in ("gates", "gate_smoke", "trade_calendar"):          # 새 모듈(고치기 전 코드로 돌 때도 있어도 그만)
        try:
            importlib.import_module(name)
        except ImportError:
            pass
    base = Path(tempfile.mkdtemp(prefix="boostd-"))
    root, runner = base / "repo", base / "runner"
    root.mkdir()
    runner.mkdir()
    old_cwd = os.getcwd()
    clock = Clock(opt.get("start") or ((15, 20, 0) if kind.startswith("daily") else (15, 5, 0)))
    sent = []
    spy = opt.get("spy")
    try:
        px, broker, prices = build_world(root, kind, opt)
        before = _snapshot_files(root)
        client = Client(px, opt.get("missing", ()))
        fake_dt = clock.dt_class()
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ))
            for k in DROP_ENV:
                os.environ.pop(k, None)
            os.environ.update(ENV)
            os.environ["RUNNER_TEMP"] = str(runner)
            os.chdir(root)
            st.callback(os.chdir, old_cwd)
            st.enter_context(mock.patch("datetime.datetime", fake_dt))
            for name in ("idle_live", "paper_trade", "daily_live", "overlay_live", "hourly_a", "audit_log", "gates", "gate_smoke", "acc_cap"):
                m = sys.modules.get(name)
                if m is not None and getattr(m, "datetime", None) is datetime:
                    st.enter_context(mock.patch.object(m, "datetime", fake_dt))
            # 봇 모듈의 time.sleep만 가짜 시계로(subprocess 등 표준 모듈의 짧은 기다림은 진짜 · 시계가 흔들리지 않게)
            import time as real_time
            fake_time = type("FakeTime", (), {k: staticmethod(getattr(real_time, k)) for k in dir(real_time)
                                              if not k.startswith("_") and callable(getattr(real_time, k))})
            fake_time.sleep = staticmethod(clock.sleep)
            for name in ("idle_live", "daily_live", "paper_trade", "overlay_live", "acc_cap", "collect_kis_intraday"):
                m = sys.modules.get(name)
                if m is not None and getattr(m, "time", None) is real_time:
                    st.enter_context(mock.patch.object(m, "time", fake_time))
            st.enter_context(mock.patch.object(broker_kis, "market", lambda: client))
            st.enter_context(mock.patch.object(paper_trade, "PaperBroker", lambda: broker))
            st.enter_context(mock.patch.dict(paper_trade.SHARES, {"1h": 0.0, "1d": 0.5, "15m": 0.0}))
            st.enter_context(mock.patch.object(paper_trade, "BASKET_SHARE", 0.3))
            st.enter_context(mock.patch.object(study, "load_prices", lambda *a, **k: copy.deepcopy(prices)))
            st.enter_context(mock.patch.object(caps, "tag", lambda rows, top=100: [r.update({caps.RANK: i + 1}) for i, r in enumerate(rows)]))
            found = opt.get("found") or (FOUND_MULTI if kind == "daily_multi" else FOUND)
            st.enter_context(mock.patch.object(final_group, "compute", lambda prices=None, flow_day=None, calm=None: copy.deepcopy(found)))
            st.enter_context(mock.patch.object(collect_kis_intraday, "market_open_today", lambda client, today, bots=True: True))
            st.enter_context(mock.patch.object(data_guard, "prev_trading_day", lambda client, day: opt.get("live_p", P)))
            st.enter_context(mock.patch.object(daily_live, "target_cut", lambda code, day, back_days=45: False))
            st.enter_context(mock.patch.object(daily_live, "steady3", lambda code, day: False))
            st.enter_context(mock.patch.object(daily_live, "volume_ratio", lambda code, day, v: None))
            st.enter_context(mock.patch.object(daily_live, "kin_checker", lambda *a, **k: (lambda code, holding: True)))
            st.enter_context(mock.patch.object(lab, "moves", lambda live: {}))
            st.enter_context(mock.patch.object(notify_discord, "post", lambda rows, paper=True: sent.append([str(r) for r in rows]) or True))
            if "sync_ok" in opt or "sync_spy" in opt:
                def sync():
                    if "sync_spy" in opt:                 # 저장소 맞추기 때 저장소 안 파일 모습(15:05 다시 셈이 저장소를 안 건드렸는지)
                        opt["sync_spy"].append(_snapshot_files(root))
                    return opt.get("sync_ok", True)
                st.enter_context(mock.patch.object(paper_trade, "sync_repo", sync))
            if opt.get("refresh") is not None:
                st.enter_context(mock.patch.object(hourly_a, "refresh_near", opt["refresh"]))
            if spy is not None:
                real = overlay_live.run
                st.enter_context(mock.patch.object(overlay_live, "run", lambda *a, **k: spy.append(dict(k)) or real(*a, **k)))
            st.enter_context(mock.patch("builtins.print"))
            now = datetime.fromtimestamp(clock.t, KST)
            rc = (daily_live.run(now) if kind.startswith("daily") else idle_live.run(now))
        after = _snapshot_files(root)
        files, audit = {}, {}
        for rel, text in after.items():
            if "/audit/" in rel:
                body = json.loads(text)
                audit[rel] = {"입력": body.get("입력"), "결과": body.get("결과"), "곁": body.get("곁"), "주문 결과": body.get("주문 결과"),
                              "날": body.get("날"), "오늘 장부 주문": body.get("오늘 장부 주문")}
            elif before.get(rel) != text:
                files[rel] = text
        return {"rc": rc, "orders": broker.orders, "discord": sent, "files": files, "audit": audit, "runner": str(runner),
                "root": str(root), "cash": broker.cash, "positions": broker.pos, "before": before}
    finally:
        os.chdir(old_cwd)
        for m in list(sys.modules.values()):              # 실행 중 처음 불린 모듈에 가짜 시계가 남았으면 되돌림
            try:
                if getattr(getattr(m, "datetime", None), "__name__", "") == "FakeDT":
                    m.datetime = datetime
            except Exception:
                pass
        shutil.rmtree(base, ignore_errors=True)


def _sha(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def comparable(out):
    """바이트 비교 몫: 주문 · 알림 · 장부 파일 글 그대로(새 기록 빼고) · 판단 기록의 입력 · 결과(지문)."""
    return {"rc": out["rc"], "orders": out["orders"], "discord": out["discord"],
            "files": {k: v for k, v in out["files"].items() if not k.startswith(NEW_ONLY)},
            "audit": {k: {"입력": _sha(v["입력"]), "결과": _sha(v["결과"])} for k, v in out["audit"].items()}}


def subrun(kind, code_dir):
    """새 파이썬에서(모듈 상태 · 환경을 깨끗이) code_dir의 봇 코드로 world_run → comparable 결과."""
    env = {k: v for k, v in os.environ.items() if k not in DROP_ENV}
    code = ("import sys, json\n"
            f"sys.path[:] = [{str(code_dir)!r}, {str(ROOT)!r}, {str(ROOT / 'research')!r}] + [p for p in sys.path if p not in ('', '.')]\n"
            "from tests.test_boost_d import world_run, comparable, MARK\n"
            f"print(MARK + json.dumps(comparable(world_run({kind!r})), ensure_ascii=False, sort_keys=True))\n")
    out = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=600)
    line = [x for x in out.stdout.splitlines() if x.startswith(MARK)]
    if out.returncode != 0 or not line:
        raise AssertionError(f"하위 실행 실패({kind}) · {out.stderr[-2000:]}")
    return json.loads(line[-1][len(MARK):])


def base_code_dir(dest):
    """BASE 커밋의 바뀐 파일들을 dest에 꺼냄(없으면 None — 얕은 받기)."""
    have = subprocess.run(["git", "cat-file", "-e", f"{BASE}^{{commit}}"], cwd=str(ROOT), capture_output=True)
    if have.returncode != 0:
        return None
    for name in CHANGED:
        got = subprocess.run(["git", "show", f"{BASE}:{name}"], cwd=str(ROOT), capture_output=True)
        if got.returncode != 0:
            return None
        (Path(dest) / name).write_bytes(got.stdout)
    return Path(dest)


def make_golden(path=GOLDEN):
    """BASE 코드로 SCENARIOS를 돌려 얼린 결과를 씀(처음 한 번 · python -m tests.test_boost_d --golden)."""
    with tempfile.TemporaryDirectory() as tmp:
        code = base_code_dir(tmp)
        if code is None:
            raise SystemExit("BASE 커밋이 없어 얼린 결과를 만들 수 없음")
        body = {"base": BASE, "scenarios": {k: subrun(k, code) for k in SCENARIOS}}
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return body


# ───────────────────────── 도움 ─────────────────────────

ENGINE_BUYS = {"133690", "148070", "000040", "122630", "114800"}      # 엔진 돌리기 · 바구니 무상증자 · 덧붙임(가짜 세상에서 문이 열리면 사는 것)


def gates_file(out):
    return json.loads(out["files"]["gates/20261111.json"])


def buys(out):
    return [o for o in out["orders"] if o[1] == "buy"]


def sells(out):
    return sorted((o[0], o[2]) for o in out["orders"] if o[1] == "sell")


def audit_of(out, bot):
    home = {"engine": "idle-live", "basket": "basket-live", "overlay": "overlay-live", "daily": "daily-live"}[bot]
    return out["audit"][f"{home}/audit/{DAY}-{bot}.json"]


def good_body(day=DAY, p=P, **kw):
    """D1 계약 칸을 모두 채운 합성 판정 본문."""
    import hourly_a
    pool = ["000001", "000002", "000003"]
    body = {"date": day, "at": f"{day[:4]}-{day[4:6]}-{day[6:]} 15:05", "breadth": 40.0, "picks": [], "near": [],
            "picks_daily": [{"code": "000001", "name": "가"}], "near_daily": [], "expected_p": p, "source_p": p,
            "pool": pool, "pool_digest": hourly_a.pool_digest(pool), "quotes_expected": 3, "quotes_got": 3}
    body.update(kw)
    return body


class TmpCwd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.tmp.name)
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ)
        self.env.start()
        for k in DROP_ENV:
            os.environ.pop(k, None)
        self.quiet = mock.patch("builtins.print")
        self.quiet.start()

    def tearDown(self):
        self.quiet.stop()
        self.env.stop()
        os.chdir(self.old)
        self.tmp.cleanup()


# ───────────────────────── 판 고정 달력 ─────────────────────────

class Calendar(TmpCwd):
    def test_biggest_version_and_fields(self):
        import trade_calendar as C
        write_calendar("calendar", 2026, version=1)
        write_calendar("calendar", 2026, version=2, holidays=(P,))          # 새 공지: P가 휴장 → 앞 거래일이 하루 앞으로
        info = C.day_info(DAY)
        self.assertEqual((info["version"], info["P"], info["trading"], info["open"], info["close"]), (2, "20261109", True, "0900", "1530"))
        self.assertEqual(info["sha256"], C.load_year("2026")["sha256"])
        self.assertRegex(info["sha256"], r"^[0-9a-f]{64}$")
        write_calendar("calendar", 2026, version=10)                         # 번호는 글자 차례가 아니라 수 차례(10 > 2)
        self.assertEqual(C.day_info(DAY)["version"], 10)

    def test_fingerprint_mismatch_is_none_without_fallback(self):
        import trade_calendar as C
        write_calendar("calendar", 2026, version=1)
        write_calendar("calendar", 2026, version=2, sha="f" * 64)            # 가장 큰 판의 지문이 안 맞음
        self.assertIsNone(C.load_year("2026"))
        self.assertIsNone(C.day_info(DAY), "작은 판(v1)으로 조용히 내려가지 않음")
        body = calendar_body(2026)
        body["days"][DAY] = {"open": "1000", "close": "1530"}               # 지문은 옛 그대로 · 날 하나를 고침
        Path("calendar/krx-2026-v3.json").write_text(json.dumps(body), encoding="utf-8")
        self.assertIsNone(C.day_info(DAY))

    def test_missing_file_day_or_field_is_none(self):
        import trade_calendar as C
        self.assertIsNone(C.day_info(DAY), "판 없음")
        body = calendar_body(2026)
        del body["days"][DAY]
        body["normalized_sha256"] = C.normalized_digest(body["days"])
        Path("calendar").mkdir()
        Path("calendar/krx-2026-v1.json").write_text(json.dumps(body), encoding="utf-8")
        self.assertIsNone(C.day_info(DAY), "판에 없는 날")
        self.assertIsNotNone(C.day_info("20261113"))
        body = calendar_body(2026)
        del body["notice_no"]
        Path("calendar/krx-2026-v2.json").write_text(json.dumps(body), encoding="utf-8")
        self.assertIsNone(C.day_info("20261113"), "칸 빠짐")
        for bad in ({"open": "1530", "close": "0900"}, {"open": "9", "close": "1530"}, {"open": "0900"}):
            body = calendar_body(2026, special={DAY: bad})
            Path("calendar/krx-2026-v3.json").write_text(json.dumps(body), encoding="utf-8")
            self.assertIsNone(C.load_year("2026"), bad)
        self.assertIsNone(C.day_info("2026-11-11"), "날짜 꼴이 아님")

    def test_year_boundary_p_uses_previous_year_version(self):
        import trade_calendar as C
        write_calendar("calendar", 2026, version=3, holidays=("20261231",))
        write_calendar("calendar", 2027, version=1, holidays=("20270101",))
        info = C.day_info("20270104")                                      # 2027년 첫 거래일(월)
        self.assertEqual(info["P"], "20261230")
        self.assertEqual((info["version"], info["p_version"]), (1, 3))
        self.assertEqual(info["p_sha256"], C.load_year("2026")["sha256"])
        self.assertNotEqual(info["p_sha256"], info["sha256"])
        Path("calendar/krx-2026-v3.json").unlink()                         # 전해 판이 없으면 P를 못 정함
        self.assertIsNone(C.day_info("20270104"))

    def test_holiday_today_and_cross_check(self):
        import trade_calendar as C
        write_calendar("calendar", 2026, holidays=(DAY,))
        info = C.day_info(DAY)
        self.assertEqual((info["trading"], info["open"], info["P"]), (False, None, P))
        self.assertEqual(C.cross_check(info, P), (True, ""))
        ok, why = C.cross_check(info, "20261109")
        self.assertFalse(ok)
        self.assertIn("다름", why)
        self.assertFalse(C.cross_check(info, None)[0], "실시간 값을 못 받으면 불일치로 봄")
        self.assertFalse(C.cross_check(None, P)[0])


# ───────────────────────── 공통 문 ─────────────────────────

class GateBox(TmpCwd):
    def test_close_allow_and_unknown(self):
        import gates
        g = gates.Gates(DAY, "engine")
        self.assertTrue(all(g.allows_new_risk(d) for d in ("engine", "basket", "overlay")))
        self.assertFalse(g.allows_new_risk("daily"), "다른 실행의 판단은 기록이 없으면 닫힘으로 봄")
        self.assertFalse(g.allows_new_risk("없는 판단"))
        g.close("basket", "까닭 하나")
        g.close(("basket", "engine"), "까닭 하나")
        g.close(["basket"], "까닭 둘")
        self.assertFalse(g.allows_new_risk("basket"))
        self.assertEqual(g.reasons(("basket",)), ["까닭 하나", "까닭 둘"])
        self.assertTrue(g.allows_new_risk("overlay"))
        with self.assertRaises(ValueError):
            g.close("엔진", "오타")
        self.assertIn("빈칸 엔진 · 사건 바구니", g.warn_line())
        self.assertIsNone(gates.Gates(DAY, "daily").warn_line())

    def test_file_shared_between_runs_and_rerun_resets_own(self):
        import gates
        g = gates.Gates(DAY, "engine")
        g.set_sync(True)
        g.close("basket", "바구니 까닭")
        g.save()
        d = gates.Gates(DAY, "daily")
        self.assertFalse(d.allows_new_risk("basket"), "엔진 실행이 닫은 것은 그대로")
        self.assertTrue(d.allows_new_risk("engine") and d.allows_new_risk("daily"))
        d.set_sync(False)
        d.save()
        body = json.loads(Path(f"gates/{DAY}.json").read_text(encoding="utf-8"))
        self.assertEqual((body["runs"]["engine"]["sync_ok"], body["runs"]["daily"]["sync_ok"]), (True, False))
        self.assertFalse(body["decisions"]["daily"]["open"])
        self.assertEqual(body["decisions"]["basket"]["reasons"], ["바구니 까닭"])
        again = gates.Gates(DAY, "engine")                                 # 엔진이 다시 돌면 자기 판단은 새로 셈
        self.assertTrue(again.allows_new_risk("basket"))
        self.assertFalse(again.allows_new_risk("daily"), "1일봉 실행이 닫은 것은 그대로")

    def test_corrupt_or_unwritable_file(self):
        import gates
        Path("gates").mkdir()
        Path(f"gates/{DAY}.json").write_text("{깨짐", encoding="utf-8")
        g = gates.Gates(DAY, "daily")
        self.assertTrue(g.allows_new_risk("daily"))
        self.assertFalse(g.allows_new_risk("engine"))
        shutil.rmtree("gates")
        Path("gates").write_text("파일이라 폴더를 못 만듦")
        g = gates.Gates(DAY, "engine")
        g.close("engine", "까닭")
        self.assertIsNone(g.save(), "쓰기 실패는 None(예외 없음)")
        self.assertFalse(g.allows_new_risk("engine"), "메모리의 문 상태는 그대로")
        self.assertEqual(sorted(os.listdir(".")), ["gates"], "반쯤 쓴 파일이 안 남음")

    def test_snapshot_fields_and_d1_binding(self):
        import gates
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        Path("gate-smoke").mkdir()
        Path(f"gate-smoke/{DAY}.json").write_text(json.dumps({"date": DAY, "ok": True, "version": 1}), encoding="utf-8")
        g = gates.begin(DAY, "engine", True, live_p=P)
        self.assertTrue(all(g.allows_new_risk(d) for d in ("engine", "basket", "overlay")), g.reasons())
        g.bind_d1({"ok": True, "id": "a" * 64, "expected_p": P, "at": "2026-11-11 15:05", "path": "/숨김"})
        g.set_reserve(1234.5, {"source": "d1", "sha256": "a" * 64})
        snaps = [g.snapshot(d) for d in ("engine", "basket", "overlay")]
        self.assertEqual(tuple(snaps[0]), __import__("gate_smoke").SNAP_KEYS)
        for s in snaps:
            self.assertEqual((s["open"], s["D"], s["P"], s["session"], s["sync_ok"], s["cross_ok"], s["live_p"]),
                             (True, DAY, P, {"open": "0900", "close": "1530"}, True, True, P))
            self.assertRegex(s["calendar_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(len({json.dumps(s["d1"], sort_keys=True) for s in snaps}), 1, "세 판단의 D1 칸(성공 id · 비켜 두기)이 같음")
        self.assertEqual((snaps[0]["d1"]["id"], snaps[0]["d1"]["reserve"]), ("a" * 64, 1234.5))
        self.assertNotIn("path", snaps[0]["d1"], "임시 경로는 기록에 안 남김")
        bad = gates.begin(DAY, "engine", True, live_p=P)
        bad.bind_d1({"ok": True, "id": "a" * 64, "expected_p": "20261109"})      # 다시 셈의 P가 달력 P와 다름
        self.assertFalse(any(bad.allows_new_risk(d) for d in gates.D1_DECISIONS))
        self.assertFalse(bad.snapshot("engine")["d1"]["ok"])

    def test_begin_closes_for_each_cause(self):
        import gates
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        Path("gate-smoke").mkdir()
        Path(f"gate-smoke/{DAY}.json").write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        self.assertTrue(gates.begin(DAY, "daily", True, live_p=P).allows_new_risk("daily"))
        cases = {"저장소": dict(sync_ok=False), "다름": dict(live_p="20261109"), "못 받아": dict(live_p=None)}
        for word, kw in cases.items():
            args = {"sync_ok": True, "live_p": P, **kw}
            g = gates.begin(DAY, "daily", args["sync_ok"], live_p=args["live_p"])
            self.assertFalse(g.allows_new_risk("daily"), word)
            self.assertTrue(any(word in r for r in g.reasons()), (word, g.reasons()))
        Path(f"gate-smoke/{DAY}.json").write_text(json.dumps({"date": DAY, "ok": False, "reasons": ["달력 없음"]}), encoding="utf-8")
        g = gates.begin(DAY, "engine", True, live_p=P)
        self.assertFalse(any(g.allows_new_risk(d) for d in ("engine", "basket", "overlay")))
        self.assertTrue(any("시작 전 점검" in r for r in g.reasons()))
        Path(f"gate-smoke/{DAY}.json").write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        shutil.rmtree("calendar")
        g = gates.begin(DAY, "engine", True, live_p=P)
        self.assertTrue(any("달력" in r for r in g.reasons()) and not g.allows_new_risk("engine"))
        with mock.patch("trade_calendar.day_info", side_effect=RuntimeError("말썽")):
            g = gates.begin(DAY, "daily", True, live_p=P)
        self.assertFalse(g.allows_new_risk("daily"), "문 셈이 말썽이면 닫힘")


# ───────────────────────── 시작 전 점검 ─────────────────────────

class Smoke(TmpCwd):
    def test_ok_then_status(self):
        import gate_smoke
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        body = gate_smoke.check(DAY)
        self.assertTrue(body["ok"], body["reasons"])
        self.assertEqual((body["version"], body["P"]), (1, P))
        self.assertIsNotNone(gate_smoke.write(body))
        self.assertEqual(gate_smoke.status(DAY)[0], True)
        self.assertFalse(Path("gates").exists(), "점검은 실제 gates/를 안 건드림")

    def test_fail_and_rejections(self):
        import gate_smoke
        self.assertEqual(gate_smoke.main([DAY]), 0, "점검이 실패해도 작업을 멈추지 않음")
        body = json.loads(Path(f"gate-smoke/{DAY}.json").read_text(encoding="utf-8"))
        self.assertFalse(body["ok"])
        self.assertTrue(any("달력" in r for r in body["reasons"]))
        ok, why, _ = gate_smoke.status(DAY)
        self.assertFalse(ok)
        self.assertIn("점검 실패", why)
        self.assertEqual(gate_smoke.status("20261112")[:2], (False, "시작 전 점검 파일이 없음"))
        Path("gate-smoke/20261112.json").write_text("{", encoding="utf-8")
        self.assertFalse(gate_smoke.status("20261112")[0])
        Path("gate-smoke/20261113.json").write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        self.assertIn("오늘 것이 아님", gate_smoke.status("20261113")[1])
        Path(f"gate-smoke/{DAY}.json").write_text(json.dumps({"date": DAY, "ok": True, "run_id": "1"}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "2"}):
            self.assertIn("이 작업의 것이 아님", gate_smoke.status(DAY)[1])
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "1"}):
            self.assertTrue(gate_smoke.status(DAY)[0])

    def test_old_output_check_catches_broken_verifier(self):
        import gate_smoke
        import paper_trade
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        with mock.patch.object(paper_trade, "d1_check", lambda body, day, p: (True, "")):     # 옛 출력을 받아들이는 고장
            body = gate_smoke.check(DAY)
        self.assertFalse(body["ok"])
        self.assertTrue(any("어제 날짜" in r for r in body["reasons"]), body["reasons"])


# ───────────────────────── D1: refresh_near 계약 판 ─────────────────────────

class RefreshContract(TmpCwd):
    NOW = datetime(2026, 11, 11, 15, 5, tzinfo=KST)

    def run_refresh(self, missing=(), last=P, clock=None, **kw):
        import caps
        import collect_kis_intraday as I
        import daily_live
        import final_group
        import hourly_a as A
        import study
        prices = {f"{i:06d}": {"name": f"종목{i}", "rows": [(last, 100.0 + i)]} for i in range(1, 11)}
        client = Client({c: 110.0 for c in prices}, missing)
        with mock.patch.object(study, "load_prices", return_value=prices), \
                mock.patch.object(caps, "tag", side_effect=lambda rows, n: [r.update({caps.RANK: 1}) for r in rows]), \
                mock.patch.object(I, "market_open_today", return_value=True), \
                mock.patch.object(daily_live, "target_cut", return_value=False), \
                mock.patch.object(A, "_clock", clock or (lambda: self.NOW)), \
                mock.patch.object(final_group, "compute", side_effect=lambda live, calm=None: dict(FOUND, live=sorted(live))):
            out = Path("out") / "near.json"
            rc = A.refresh_near(self.NOW, client=client, out=out, **kw)
            return rc, (json.loads(out.read_text(encoding="utf-8")) if out.exists() else None)

    def test_without_args_same_as_before(self):
        rc, body = self.run_refresh(missing=("000001",))                    # 10개 중 1개 빠짐 → 80% 허용(예전 그대로)
        self.assertEqual(rc, 0)
        self.assertEqual(sorted(body), sorted(["date", "at", "breadth", "picks", "near", "picks_daily", "near_daily"]),
                         "인자를 안 주면 새 칸 없음(m15-live · hourly-live 쓰임새 그대로)")

    def test_contract_fields_and_atomic(self):
        import hourly_a as A
        rc, body = self.run_refresh(expected_p=P, deadline=self.NOW + timedelta(minutes=4))
        self.assertEqual(rc, 0)
        self.assertEqual((body["expected_p"], body["source_p"], body["quotes_expected"], body["quotes_got"]), (P, P, 10, 10))
        self.assertEqual(body["pool_digest"], A.pool_digest(body["pool"]))
        self.assertEqual(sorted(os.listdir("out")), ["near.json"], "임시 조각 파일이 안 남음")

    def test_contract_rejects(self):
        self.assertEqual(self.run_refresh(expected_p=P, missing=("000007",)), (1, None), "시세 하나 빠짐")
        self.assertEqual(self.run_refresh(expected_p=P, last="20261109"), (1, None), "어제 일봉 마지막 날 ≠ 달력 P")
        self.assertEqual(self.run_refresh(expected_p=P, deadline=self.NOW + timedelta(minutes=4),
                                          clock=lambda: self.NOW + timedelta(minutes=5)), (2, None), "마감 지남")
        ticks = iter([self.NOW] * 4 + [self.NOW + timedelta(minutes=9)] * 100)      # 시세를 받는 도중 마감을 넘김
        self.assertEqual(self.run_refresh(expected_p=P, deadline=self.NOW + timedelta(minutes=4), clock=lambda: next(ticks)), (2, None))


# ───────────────────────── D1: 다시 셈 · 검증 · 근거 · 사본 ─────────────────────────

class D1Recompute(TmpCwd):
    NOW = datetime(2026, 11, 11, 15, 5, tzinfo=KST)

    def setUp(self):
        super().setUp()
        import paper_trade
        self.P = paper_trade
        self.base = self.root / "runner"
        self.base.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        os.chdir(self.repo)
        self.clock = mock.patch.object(paper_trade, "_clock", lambda: self.NOW)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def recompute(self, refresh, **kw):
        return self.P.d1_recompute(DAY, None, kw.pop("p", P), now=self.NOW, base=str(self.base), refresh=refresh, **kw)

    @staticmethod
    def writer(body=None, rc=0):
        def refresh(now, client, out=None, expected_p=None, deadline=None):
            Path(out).write_text(json.dumps(body or good_body(), ensure_ascii=False), encoding="utf-8")
            return rc
        return refresh

    def test_success_outside_repo(self):
        res = self.recompute(self.writer())
        self.assertTrue(res["ok"], res["why"])
        path = Path(res["path"])
        self.assertTrue(path.is_file())
        self.assertTrue(str(path).startswith(str(self.base)), "저장소 밖(RUNNER_TEMP 자리)")
        self.assertEqual(os.listdir(self.repo), [], "저장소 안 파일을 안 건드림(15:10 git pull이 안 막힘)")
        self.assertEqual(res["id"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual((res["source_p"], res["quotes_expected"], res["quotes_got"]), (P, 3, 3))

    def test_timeout(self):
        gate = threading.Event()

        def slow(now, client, out=None, expected_p=None, deadline=None):
            gate.wait(5)
            return 0
        try:
            res = self.recompute(slow, deadline=self.NOW + timedelta(seconds=0.3))
        finally:
            gate.set()
        self.assertFalse(res["ok"])
        self.assertIn("시간 초과", res["why"])

    def test_failures(self):
        def boom(*a, **k):
            raise RuntimeError("가짜 말썽")
        cases = {"예외": boom, "출력 없음": lambda *a, **k: 0, "반환 값 1": self.writer(rc=1),
                 "옛 출력": self.writer(good_body(date=P)), "14:30": self.writer(good_body(at="2026-11-11 14:29")),
                 "source_p": self.writer(good_body(source_p="20261109")),
                 "expected_p": self.writer(good_body(expected_p="20261109")),
                 "시세 빠짐": self.writer(good_body(quotes_got=2)), "풀 지문": self.writer(good_body(pool_digest="0" * 64))}
        for word, fn in cases.items():
            res = self.recompute(fn)
            self.assertFalse(res["ok"], word)
            self.assertIn(word.split()[0], res["why"], (word, res["why"]))
            self.assertIsNone(res["path"])
        self.assertIn("앞 거래일", self.recompute(self.writer(), p=None)["why"])

    def test_old_file_only_is_never_used(self):
        """다시 셈이 0을 돌려줬지만 새 파일을 안 썼고 저장소 안에는 그날 판정(옛 꼴 · m15)과 어제 사본이 있음 → 실패 · 근거 없음."""
        Path("m15-live").mkdir()
        Path("m15-live/near-now.json").write_text(json.dumps({"date": DAY, "at": "2026-11-11 14:45", "picks_daily": [{"code": "000001"}]}))
        Path("idle-live").mkdir()
        Path("idle-live/near-now.json").write_text(json.dumps(good_body(date=P, at="2026-11-10 15:05", p="20261109")))
        res = self.recompute(lambda *a, **k: 0)
        self.assertFalse(res["ok"])
        self.assertIn("출력 없음", res["why"])
        self.assertIsNone(self.P.d1_basis(res, DAY, P))

    def test_after_deadline_or_start_late(self):
        later = self.NOW + timedelta(minutes=5)

        def late_writer(now, client, out=None, expected_p=None, deadline=None):
            Path(out).write_text(json.dumps(good_body()), encoding="utf-8")
            self.clock.stop()
            self.clock = mock.patch.object(self.P, "_clock", lambda: later)
            self.clock.start()
            return 0
        res = self.recompute(late_writer)
        self.assertFalse(res["ok"])
        self.assertIn("마감", res["why"])
        called = []
        res = self.recompute(lambda *a, **k: called.append(1) or 0)
        self.assertEqual((res["ok"], called), (False, []), "시작 때 이미 마감이면 부르지도 않음")

    def test_basis_latest_verified_and_tamper(self):
        res = self.recompute(self.writer())
        b = self.P.d1_basis(res, DAY, P, others=())
        self.assertEqual((b["source"], b["sha256"]), ("d1", res["id"]))
        Path("m15-live").mkdir()
        Path("m15-live/near-now.json").write_text(json.dumps(good_body(at="2026-11-11 15:07")))     # 검증을 통과하는 더 늦은 판정
        Path("m15-live/old.json").write_text(json.dumps({"date": DAY, "at": "2026-11-11 15:08", "picks_daily": []}))  # 검증 칸 없음
        b = self.P.d1_basis(res, DAY, P, others=(Path("m15-live/near-now.json"), Path("m15-live/old.json")))
        self.assertEqual((b["source"], b["at"]), ("m15-live/near-now.json", "2026-11-11 15:07"))
        Path(res["path"]).write_text(json.dumps(good_body(picks_daily=[])))                       # 검증 뒤 D1 파일이 바뀜
        self.assertIsNone(self.P.d1_basis(res, DAY, P, others=()))
        self.assertIsNone(self.P.d1_basis({"ok": False}, DAY, P))

    def test_keep_copy(self):
        res = self.recompute(self.writer())
        self.assertTrue(self.P.d1_keep(res))
        self.assertEqual(Path("idle-live/near-now.json").read_bytes(), Path(res["path"]).read_bytes())
        self.assertFalse(self.P.d1_keep({"ok": False}))
        Path("idle-live/near-now.json").unlink()
        Path("idle-live/near-now.json").mkdir()                             # 쓸 수 없는 자리 → 거짓 · 예외 없음 · 조각 안 남김
        self.assertFalse(self.P.d1_keep(res))
        self.assertEqual(os.listdir("idle-live"), ["near-now.json"])
        tampered = dict(res, id="0" * 64)
        self.assertFalse(self.P.d1_keep(tampered, dest=Path("x.json")))


# ───────────────────────── 덧붙임 buy_ok ─────────────────────────

class OverlayBuyOk(unittest.TestCase):
    """덧붙임 단독(가짜 계좌 · tests/test_overlay_live와 같은 틀): 매수 다리만 빠지고 매도 · 줄이기 · prepare는 그대로 · 교체는 매도만 + pending."""

    def setUp(self):
        from tests import test_overlay_live as T
        self.T = T
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.tmp.name)
        self.patches = [mock.patch.dict(os.environ, {"MIX54": "on", "MIX54_START": "20261001", "PAPER_ROOM_WAIT": "0"}),
                        mock.patch("overlay_live.time.sleep"), mock.patch("builtins.print")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        os.chdir(self.old)
        self.tmp.cleanup()

    def go(self, b, kind, day="20261012", prev="20261008", reserve=0.0, buy_ok=True):
        import overlay_live as O
        b.now = self.T.Run.NOW
        with mock.patch.object(O, "closes", lambda before=None, code=O.SIGNAL: self.T.rows_for(kind, end=prev)):
            return O.run(b, None, day, reserve=reserve, now=self.T.Run.NOW, quote=b.px.get, prev_day=prev, buy_ok=buy_ok)

    def start_up(self):
        import overlay_live as O
        b = self.T.FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        self.go(b, "상승")
        b.orders.clear()
        self.assertEqual(O.load_state()["held"], {"122630": 4000})
        return b

    def test_buy_signal_blocked_then_next_day(self):
        import overlay_live as O
        b = self.T.FakeBroker(1_000_000, prices={"122630": 100.0, "114800": 50.0})
        lines = self.go(b, "상승", buy_ok=False)
        self.assertEqual(b.orders, [], "매수 신호여도 사지 않음")
        st = O.load_state()
        self.assertEqual((st["applied"], st["held"], st["B"]), ("pending", {}, 0.0))
        self.assertTrue(any("새 매수 막음" in x for x in lines))
        self.assertTrue(O.needs_rebalance(st, "상승", "20261013"), "다음 거래일에 다시 판단")
        self.go(b, "상승", day="20261013", prev="20261012")
        self.assertEqual(b.orders, [("122630", "buy", 4000)])
        self.assertEqual(O.load_state()["applied"], "상승")

    def test_reduce_and_sell_all_allowed(self):
        import overlay_live as O
        b = self.start_up()
        st = O.load_state()
        st["rebalanced_month"] = "202609"                                   # 달 첫 맞춤 날(목표가 줄어 줄이기만 생김)
        O.save_state(st)
        self.go(b, "상승", day="20261013", prev="20261012", reserve=500_000, buy_ok=False)
        self.assertEqual([o[:2] for o in b.orders], [("122630", "sell")], "줄이기는 그대로")
        self.assertEqual(O.load_state()["applied"], "상승", "매수 다리를 뺀 것이 없으면 맞춤 끝")
        b.orders.clear()
        self.go(b, "하락", day="20261014", prev="20261013", buy_ok=False)
        self.assertEqual([o[:2] for o in b.orders], [("122630", "sell")], "다 팔기도 그대로")
        st = O.load_state()
        self.assertEqual((st["held"], st["B"], st["applied"]), ({}, 0.0, "하락"))

    def test_swap_sells_only_and_pending(self):
        import overlay_live as O
        b = self.start_up()
        lines = self.go(b, "횡보", day="20261013", prev="20261012", buy_ok=False)
        self.assertEqual(b.orders, [("122630", "sell", 4000)], "교체 날은 옛 종목 매도까지만")
        st = O.load_state()
        self.assertEqual((st["applied"], st["held"], st["B"], st["rebalanced_month"]), ("pending", {}, 0.0, "202610"))
        self.assertTrue(any("새 매수 막음" in x for x in lines))
        b.orders.clear()
        self.go(b, "횡보", day="20261014", prev="20261013")
        self.assertEqual([o[:2] for o in b.orders], [("114800", "buy")], "다음 날(문 열림) 다시 판단해 삼")
        self.assertEqual(O.load_state()["applied"], "횡보")

    def test_prepare_still_runs_when_blocked(self):
        import overlay_live as O
        b = self.start_up()
        st = O.load_state()
        st["last_day"] = "20261012"
        O.save_state(st)
        self.go(b, "상승", day="20261013", prev="20261012", reserve=600_000, buy_ok=False)   # 맞추지 않는 날 · 1일봉 몫 덜어 두기
        self.assertEqual([o[:2] for o in b.orders], [("122630", "sell")])
        self.assertGreaterEqual(b.cash * 0.98 + 1e-6, 600_000 * 1.36)


class BasketZeroMoney(unittest.TestCase):
    def test_zero_money_sells_only(self):
        import basket_live as B
        days = weekdays_until(DAY, 30)
        pos = {d: i for i, d in enumerate(days)}
        st = {"positions": {"A": {"day": days[-21], "price": 900.0, "kind": "무상증자"}}}
        args = (st, DAY, P, lambda d: len(days) - 1 - pos[d], [("C", "무상증자")], {"C": 0.0}, {"A", "C"}, {"A": 10},
                {"A": 1000.0, "C": 1000.0})
        orders, _, _ = B.step(*args, capital=1e7, avail=1e7)
        self.assertEqual([o[:2] for o in orders], [("A", "sell"), ("C", "buy")])
        orders, new, why = B.step(*args, capital=0.0, avail=0.0)
        self.assertEqual([o[:2] for o in orders], [("A", "sell")], "돈 0이면 사지 않고 20거래일 팔기만")
        self.assertNotIn("C", new["positions"])


# ───────────────────────── 엔진 실행(빈칸 엔진 · 바구니 · 덧붙임) ─────────────────────────

class EngineRun(unittest.TestCase):
    def assertBlocked(self, out, word):
        g = gates_file(out)
        for d in ("engine", "basket", "overlay"):
            self.assertFalse(g["decisions"][d]["open"], d)
            self.assertTrue(any(word in r for r in g["decisions"][d]["reasons"]), (d, word, g["decisions"][d]["reasons"]))
        self.assertEqual(buys(out), [], "엔진 · 바구니 · 덧붙임 매수 0")
        self.assertIn(("000020", 200), sells(out), "바구니 20거래일 팔기는 그대로")
        self.assertIn(("138230", 1000), sells(out), "엔진 규칙 매도는 그대로")
        warn = [r for rows in out["discord"] for r in rows if r.startswith("⚠️ 새 매수 막음")]
        self.assertEqual(len(warn), 1, out["discord"])
        for bot in ("engine", "basket", "overlay"):
            snap = audit_of(out, bot)["곁"]["gates"]
            self.assertFalse(snap["open"], bot)

    def test_open_gates_records_and_d1_binding(self):
        spy = []
        out = world_run("engine", sync_spy=spy)
        self.assertEqual(sorted(o[0] for o in buys(out)), ["000040", "122630", "133690", "148070"])
        g = gates_file(out)
        self.assertTrue(all(g["decisions"][d]["open"] for d in ("engine", "basket", "overlay")), g)
        self.assertEqual(spy[0], out["before"], "15:05 다시 셈은 저장소 안 파일을 안 고침(15:10 저장소 맞추기 전)")
        kept = out["files"]["idle-live/near-now.json"]
        body = json.loads(kept)
        self.assertEqual((body["date"], body["expected_p"], body["source_p"], body["quotes_got"]), (DAY, P, P, body["quotes_expected"]))
        sha = hashlib.sha256(kept.encode("utf-8")).hexdigest()
        snaps = {bot: audit_of(out, bot)["곁"]["gates"] for bot in ("engine", "basket", "overlay")}
        reserve = audit_of(out, "engine")["곁"]["reserve"]
        self.assertGreater(reserve, 0)
        for bot, s in snaps.items():
            self.assertTrue(s["open"], bot)
            self.assertEqual((s["d1"]["ok"], s["d1"]["id"], s["d1"]["reserve"], s["P"], s["sync_ok"]), (True, sha, reserve, P, True), bot)
        self.assertEqual(len({json.dumps(s["d1"], sort_keys=True) for s in snaps.values()}), 1, "세 기록의 D1 칸이 같은 값")
        self.assertEqual(audit_of(out, "overlay")["주문 결과"]["target"]["reserve"], reserve * 1.36)
        self.assertFalse(any(r.startswith("⚠️") for rows in out["discord"] for r in rows))

    def test_sync_fail_blocks_new_risk_only(self):
        out = world_run("engine", sync_ok=False)
        self.assertBlocked(out, "저장소")
        g = gates_file(out)
        self.assertEqual(g["runs"]["engine"]["sync_ok"], False)
        self.assertTrue(g["d1"]["ok"], "D1은 따로 성공해도 sync 실패로 막힘")
        self.assertNotIn("000040", json.loads(out["files"]["basket-live/state.json"])["positions"])
        self.assertEqual(sorted(json.loads(out["files"]["idle-live/state.json"])["positions"]), [], "안 산 엔진 종목은 상태에도 없음")
        self.assertEqual(json.loads(out["files"]["overlay-live/state.json"])["applied"], "pending")

    def test_d1_failures_close_three(self):
        gate = threading.Event()

        def slow(now, client, out=None, expected_p=None, deadline=None):
            gate.wait(5)
            return 0

        def boom(*a, **k):
            raise RuntimeError("가짜 말썽")
        old_m15 = {"date": DAY, "at": f"{DAY[:4]}-{DAY[4:6]}-{DAY[6:]} 14:45", "breadth": 40.0, "picks": [],
                   "near": [], "picks_daily": copy.deepcopy(FOUND["picks"]), "near_daily": []}
        cases = {"시간 초과": dict(refresh=slow, start=(15, 9, 29)),
                 "예외": dict(refresh=boom),
                 "출력 없음": dict(refresh=lambda *a, **k: 0),
                 "옛 파일만": dict(refresh=lambda *a, **k: 0, m15_body=old_m15,
                                extra_files={"idle-live/near-now.json": good_body(date=P, at="2026-11-10 15:05", p="20261109")}),
                 "source_p ≠ P": dict(prices_last="20261109"),
                 "시세 하나 빠짐": dict(missing=("000149",))}
        try:
            for name, kw in cases.items():
                with self.subTest(name):
                    out = world_run("engine", **kw)
                    self.assertBlocked(out, "15:05")
                    g = gates_file(out)
                    self.assertEqual((g["d1"]["ok"], g["d1"]["reserve"], g["d1"]["id"]), (False, 0.0, None), name)
                    if name == "옛 파일만":
                        self.assertEqual(json.loads(out["files"]["idle-live/near-now.json"] if "idle-live/near-now.json" in out["files"]
                                                    else out["before"]["idle-live/near-now.json"])["date"], P, "옛 사본을 덮지도 쓰지도 않음")
        finally:
            gate.set()

    def test_d1_fail_overlay_swap_sells_only(self):
        spy = []
        out = world_run("engine_swap", refresh=lambda *a, **k: 0, spy=spy)
        self.assertEqual(spy[0]["buy_ok"], False)
        self.assertIn(("122630", 1000), sells(out), "덧붙임 옛 종목 매도는 그대로")
        self.assertFalse(any(o[0] == "114800" for o in out["orders"]), "새 종목 매수는 막음")
        st = json.loads(out["files"]["overlay-live/state.json"])
        self.assertEqual((st["applied"], st["held"]), ("pending", {}))
        self.assertEqual(audit_of(out, "overlay")["주문 결과"]["gate_dropped"][0][:2], ["114800", "buy"])

    def test_calendar_cross_check_and_smoke_close_all(self):
        for name, kw, word in (("달력 없음", dict(calendar=False), "달력"), ("앞 거래일 다름", dict(live_p="20261109"), "다름"),
                               ("점검 파일 없음", dict(smoke=False), "시작 전 점검")):
            with self.subTest(name):
                self.assertBlocked(world_run("engine", **kw), word)

    def test_record_and_gate_write_failures_do_not_stop_trading(self):
        normal = world_run("engine")
        out = world_run("engine", block=("idle-live/audit", "basket-live/audit", "overlay-live/audit", "gates"),
                        block_dir=("idle-live/near-now.json",))
        self.assertEqual(out["rc"], 0)
        self.assertEqual(out["orders"], normal["orders"])
        self.assertEqual(out["audit"], {}, "기록은 못 남겨도")
        self.assertNotIn("gates/20261111.json", out["files"])


class DailyRun(unittest.TestCase):
    def test_sync_fail_sells_only(self):
        out = world_run("daily", sync_ok=False)
        self.assertEqual(out["orders"], [["000010", "sell", 100]], "1일봉 매수 0 · 팔기는 그대로")
        self.assertEqual(audit_of(out, "daily")["입력"]["cands"], [], "자료 덜 들어온 날과 같은 cands = [] 길")
        g = gates_file(out)
        self.assertEqual((g["decisions"]["daily"]["open"], g["runs"]["daily"]["sync_ok"]), (False, False))
        self.assertTrue(any(r.startswith("⚠️ 새 매수 막음(1일봉)") for r in out["discord"][0]), out["discord"][0])
        self.assertFalse(audit_of(out, "daily")["곁"]["gates"]["open"])

    def test_open_and_calendar_missing(self):
        out = world_run("daily")
        self.assertEqual(out["orders"], [["000010", "sell", 100], ["000030", "buy", 571]])
        self.assertTrue(audit_of(out, "daily")["곁"]["gates"]["open"])
        out = world_run("daily", calendar=False)
        self.assertEqual(out["orders"], [["000010", "sell", 100]])

    def test_record_and_gate_write_failures_do_not_stop_daily(self):
        normal = world_run("daily")
        out = world_run("daily", block=("daily-live/audit", "gates"))
        self.assertEqual((out["rc"], out["orders"]), (0, normal["orders"]))
        self.assertEqual(out["audit"], {})


# ───────────────────────── 문이 모두 열리면 고치기 전과 바이트까지 같음 ─────────────────────────

class SameAsBefore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_golden_covers_buys_and_sells(self):
        self.assertEqual(self.golden["base"], BASE)
        self.assertEqual(sorted(self.golden["scenarios"]), sorted(SCENARIOS))
        for k, v in self.golden["scenarios"].items():
            sides = {o[1] for o in v["orders"]}
            self.assertEqual(sides, {"buy", "sell"}, k)

    def test_open_gates_same_orders_files_and_alerts(self):
        for k in SCENARIOS:
            with self.subTest(k):
                self.assertEqual(subrun(k, ROOT), self.golden["scenarios"][k])

    def test_golden_is_base_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = base_code_dir(tmp)
            if code is None:
                self.skipTest("BASE 커밋이 없음(얕은 받기) — 얼린 결과와 새 코드 비교는 위 시험이 함")
            for k in SCENARIOS:
                with self.subTest(k):
                    self.assertEqual(subrun(k, code), self.golden["scenarios"][k])


class Structure(unittest.TestCase):
    def test_engine_order_of_steps(self):
        """엔진 실행 차례: 15:05 다시 셈 → 15:10 기다림 → 저장소 맞추기(값을 받음) → 문 → 사본(맞추기 뒤에만)."""
        text = (ROOT / "idle_live.py").read_text(encoding="utf-8")
        run = text[text.index("def run(now=None):"):]
        marks = ["_wait_until(paper_trade.D1_AT)", "d1 = d1_recount(day)", "_wait_until(DECIDE_AT)", "sync_ok = paper_trade.sync_repo()",
                 'gate = gates.begin(day, "engine", sync_ok', "gate.bind_d1(d1)", "paper_trade.d1_keep(d1)"]
        at = [run.index(m) for m in marks]
        self.assertEqual(at, sorted(at))
        daily = (ROOT / "daily_live.py").read_text(encoding="utf-8")
        self.assertIn("sync_ok = _pt.sync_repo()", daily)
        self.assertLess(daily.index("cands = []           # 자료가 덜"), daily.index('if not gate.allows_new_risk("daily"):'))


# ───────────────────────── 2a단계: 달력 최근 거래일 · 수집기 목표 날 ─────────────────────────

class CalendarDays(TmpCwd):
    def test_last_days_holidays_year_boundary_and_gaps(self):
        import trade_calendar as C
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        self.assertEqual(C.last_days(DAY, 5), weekdays_until(P, 5))
        self.assertEqual(C.last_days("20261012", 5), ["20261001", "20261002", "20261006", "20261007", "20261008"],
                         "휴장(10-05 대체공휴일 · 10-09 한글날)은 건너뜀")
        self.assertIsNone(C.last_days("20270105", 5), "새해 판이 없으면 못 정함")
        write_calendar("calendar", 2027, holidays=("20270101",))
        self.assertEqual(C.last_days("20270105", 5), ["20261224", "20261228", "20261229", "20261230", "20270104"], "해를 넘겨 전해 판에서")
        self.assertIsNone(C.last_days(DAY, 0))
        self.assertIsNone(C.last_days("2026-11-11", 5))
        body = calendar_body(2026, holidays=HOLIDAYS_2026)
        del body["days"]["20261105"]                                    # P − 3이 판에 없음
        body["normalized_sha256"] = C.normalized_digest(body["days"])
        Path("calendar/krx-2026-v2.json").write_text(json.dumps(body), encoding="utf-8")
        self.assertEqual(C.day_info(DAY)["P"], P, "앞 거래일(P)은 그대로 정해짐")
        self.assertIsNone(C.last_days(DAY, 5), "판에 없는 날을 만나면 못 정함(휴장으로 보지 않음)")

    def test_latest_done(self):
        import trade_calendar as C
        self.assertIsNone(C.latest_done(DAY), "판이 없으면 None(수집기는 예전 방식)")
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        self.assertEqual(C.latest_done(DAY), P, "수요일 새벽 → 화요일 장")
        self.assertEqual(C.latest_done("20261114"), "20261113", "토요일 새벽 → 금요일 장")
        self.assertEqual(C.latest_done("20261010"), "20261008", "한글날(금) 다음 토요일 → 목요일 장")


# ───────────────────────── 2a단계: D2 엔진 ETF 마지막 날 ─────────────────────────

class GateEtf(TmpCwd):
    def gate(self, calendar=True):
        import gates
        if calendar:
            write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        Path("gate-smoke").mkdir(exist_ok=True)
        Path(f"gate-smoke/{DAY}.json").write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        return gates.begin(DAY, "engine", True, live_p=P)

    def test_engine_only_with_code_and_day(self):
        import idle_live
        self.assertEqual(set(idle_live.CODES), {"069500", "138230", "251340", "229200", "133690", "132030", "148070"})
        ok = {c: P for c in idle_live.CODES}
        g = self.gate()
        g.check_etf(ok)
        self.assertTrue(all(g.allows_new_risk(d) for d in ("engine", "basket", "overlay")), g.reasons())
        self.assertEqual(g.snapshot("engine")["checks"], {"etf_last": {"P": P, "last": dict(sorted(ok.items()))}})
        g = self.gate()
        g.check_etf(dict(ok, **{"133690": "20261109", "148070": None}))
        self.assertFalse(g.allows_new_risk("engine"))
        self.assertTrue(g.allows_new_risk("basket") and g.allows_new_risk("overlay"), "엔진만 닫음")
        why = " / ".join(g.reasons(("engine",)))
        self.assertIn("133690 20261109", why)
        self.assertIn("148070 없음", why)
        self.assertEqual(g.snapshot("basket")["checks"], {})
        self.assertIn("빈칸 엔진", g.warn_line())
        self.assertNotIn("사건 바구니", g.warn_line())

    def test_unknown_p_closes_without_extra_reason(self):
        import gates
        g = gates.Gates(DAY, "engine")                                   # 달력 칸 없음 → P 모름 · 문은 열린 채
        g.check_etf({"069500": P})
        self.assertFalse(g.allows_new_risk("engine"), "P를 모르면 엔진은 닫힘(fail-closed)")
        g = self.gate(calendar=False)                                    # 달력이 없으면 이미 D5 길로 닫힘
        before = g.reasons(("engine",))
        g.check_etf({"069500": P})
        self.assertEqual(g.reasons(("engine",)), before, "D5 까닭에 D2 까닭을 더하지 않음")
        g = self.gate()
        g.check_etf(None)                                                # 셈 말썽 → 닫힘
        self.assertFalse(g.allows_new_risk("engine"))

    def test_etf_last_days_same_filter_as_history(self):
        import idle_live
        Path("etf-data").mkdir()
        p1, p2 = weekdays_until(P, 3)[:2]
        Path("etf-data/069500.json").write_text(json.dumps({"closes": [[p1, 100.0], [p2, 101.0], [P, None], [DAY, 102.0]]}),
                                                encoding="utf-8")
        got = idle_live.etf_last_days(DAY)
        self.assertEqual(got["069500"], p2, "빈 값(P) · 오늘 줄은 history처럼 뺌")
        self.assertEqual(len(idle_live.history("069500", DAY)), 2)
        self.assertEqual(sorted(got), sorted(idle_live.CODES))
        self.assertTrue(all(got[c] is None for c in idle_live.CODES if c != "069500"), "파일 없음 → None")


# ───────────────────────── 2a단계: D4 수급 두 층 ─────────────────────────

class FlowCwd(TmpCwd):
    """D4 시험 도움(시험 없음): 달력 · 점검 파일을 둔 1일봉 문 · 가짜 investor-data 쓰기."""

    def gate(self):
        import gates
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        Path("gate-smoke").mkdir(exist_ok=True)
        Path(f"gate-smoke/{DAY}.json").write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        return gates.begin(DAY, "daily", True, live_p=P)

    @staticmethod
    def put(code, body):
        Path("investor-data").mkdir(exist_ok=True)
        Path(f"investor-data/{code}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")


class GateFlow(FlowCwd):
    def test_pool_health_89_closes_90_opens(self):
        import final_group
        import gates
        codes = [f"{i:06d}" for i in range(1, 101)]
        days5 = weekdays_until(P, 5)
        for fresh, want in ((89, False), (90, True)):
            for i, c in enumerate(codes):
                self.put(c, flow_body(c, end=P if i < fresh else days5[-2]))
            g = self.gate()
            g.check_flow_pool(reversed(codes), DAY, final_group.flow_rows)
            self.assertEqual(g.allows_new_risk("daily"), want, (fresh, g.reasons()))
            fp = g.snapshot("daily")["checks"]["flow_pool"]
            self.assertEqual((fp["P"], fp["days"], fp["n"], fp["exact"], fp["ratio"]), (P, days5, 100, fresh, fresh / 100))
            self.assertEqual((fp["pool"], fp["sha256"]), (codes, gates.pool_digest(codes)), "풀 목록(정렬) · 지문")
            self.assertEqual(fp["stale"], [[c, days5[-2]] for c in codes[fresh:]])
            if not want:
                self.assertTrue(any("수급 풀 건강도" in r and "89/100" in r for r in g.reasons(("daily",))), g.reasons())

    def test_pool_without_5_days_empty_or_error_closes(self):
        import final_group
        import trade_calendar as C
        self.put("000001", flow_body("000001"))
        g = self.gate()
        body = calendar_body(2026, holidays=HOLIDAYS_2026)
        del body["days"]["20261105"]
        body["normalized_sha256"] = C.normalized_digest(body["days"])
        Path("calendar/krx-2026-v2.json").write_text(json.dumps(body), encoding="utf-8")
        g.check_flow_pool(["000001"], DAY, final_group.flow_rows)       # P는 알지만 최근 5거래일을 못 정함
        self.assertFalse(g.allows_new_risk("daily"))
        self.assertTrue(any("최근 5거래일" in r for r in g.reasons(("daily",))))
        self.assertEqual(g.keep_flow_exact([{"code": "000001", "name": "가"}], DAY, final_group.flow_rows)[0], [], "거르기도 모두 뺌")
        Path("calendar/krx-2026-v2.json").unlink()
        g = self.gate()
        g.check_flow_pool([], DAY, final_group.flow_rows)
        self.assertFalse(g.allows_new_risk("daily"), "빈 풀")

        def boom(code):
            raise RuntimeError("가짜 말썽")
        g = self.gate()
        g.check_flow_pool(["000001"], DAY, boom)
        self.assertFalse(g.allows_new_risk("daily"))
        self.assertTrue(any("셈 오류" in r for r in g.reasons(("daily",))))
        g = self.gate()
        g.check_flow_pool(["000001"], DAY, final_group.flow_rows)
        self.assertTrue(g.allows_new_risk("daily"))
        self.assertEqual(g.keep_flow_exact([{"code": "000001"}], DAY, boom), ([], [{"code": None, "name": None, "why": "거르기 오류 · RuntimeError"}]))
        self.assertFalse(g.allows_new_risk("daily"), "거르기 말썽 → 닫힘")

    def test_keep_exact_order_reasons_and_old_path(self):
        import final_group
        days5 = weekdays_until(P, 5)
        files = {"000001": flow_body("000001"), "000002": flow_body("000002", end=days5[-2]),
                 "000003": flow_body("000003", hole=days5[1]), "000004": flow_body("000004", empty=(days5[2], "투신")),
                 "000005": flow_body("000005")}
        for c, b in files.items():
            self.put(c, b)
        g = self.gate()
        g.check_flow_pool(["000001", "000005"], DAY, final_group.flow_rows)
        self.assertTrue(g.allows_new_risk("daily"))
        cands = [{"code": c, "name": f"종목{c[-1]}", "추세 기울기": 9.0 - i, "칸": 2} for i, c in enumerate(files)]
        keep, missed = g.keep_flow_exact(cands, DAY, final_group.flow_rows)
        self.assertEqual([c["code"] for c in keep], ["000001", "000005"])
        self.assertIs(keep[0], cands[0], "후보 dict · 차례 그대로(모두 맞으면 지금과 같은 후보)")
        whys = {m["code"]: m["why"] for m in missed}
        self.assertEqual(sorted(whys), ["000002", "000003", "000004"])
        self.assertIn(f"마지막 날 {days5[-2]}", whys["000002"])
        self.assertIn(f"줄 빠짐 · {days5[1]}", whys["000003"])
        self.assertIn(f"칸 빔 · {days5[2]} 투신", whys["000004"])
        self.assertEqual(g.snapshot("daily")["checks"]["flow_missed"], missed)
        self.assertTrue(g.allows_new_risk("daily"), "후보를 빼도 문은 그대로")
        rows = final_group.flow_rows("000002")
        self.assertIsNotNone(final_group.flow_before(rows, DAY), "10일 낡음 허용 길은 P−1 자료를 받아 줌 → 거르기가 막아야 하는 것")
        self.assertIsNotNone(final_group.flow_before(final_group.flow_rows("000003"), DAY), "중간이 빠져도 받아 줌")
        exact = final_group.flow_before(final_group.flow_rows("000001"), DAY)
        self.assertEqual((exact["외국인"], exact["투신"], exact["개인"], exact["끝날"]), (25.0, 20.0, -50.0, P),
                         "통과한 종목은 달력 최근 5거래일 그대로 더한 값")
        fresh = __import__("gates").Gates(DAY, "daily")                  # check_flow_pool 없이 → 모두 뺌
        self.assertEqual(fresh.keep_flow_exact(cands, DAY, final_group.flow_rows)[0], [])


class FlowBeforeCut(FlowCwd):
    """사전등록 §1.3 (나) 합성 반례: 낡은 상위 1 + 정상 차순위 1 + 빈 칸 1 → 정상 차순위를 삼(거르기는 decide 정렬 · 자르기 앞)."""

    def test_stale_top_normal_second_one_slot(self):
        import daily_live
        import final_group
        self.put("A00001", flow_body("A00001", end=weekdays_until(P, 2)[0]))
        self.put("B00001", flow_body("B00001"))
        g = self.gate()
        g.check_flow_pool(["B00001"], DAY, final_group.flow_rows)
        state = {"positions": {"X00001": {"code": "X00001", "name": "엑스", "kind": "추세", "price": 100.0, "peak": 100.0,
                                          "max_close": 100.0, "last_close": 100.0, "칸": 9, "처음칸": 9, "days": 1, "bought": P, "why": ""}}}
        cands = [{"code": "A00001", "name": "낡음", "추세문": True, "추세 기울기": 9.0, "칸": 4},
                 {"code": "B00001", "name": "정상", "추세문": True, "추세 기울기": 1.0, "칸": 4}]
        px = {"X00001": 100.0, "A00001": 10.0, "B00001": 10.0}

        def kin(code, holding):
            return True
        sells, before = daily_live.decide(state, cands, px, {}, {}, kin)
        self.assertEqual((sells, [b["code"] for b in before]), ([], ["A00001"]), "거르기 없으면 빈 칸 1을 낡은 위 후보가 차지")
        self.assertEqual([b for b in before if b["code"] != "A00001"], [], "매수 목록에서 뒤늦게 버리면 정상 차순위도 사라짐(쓰지 않는 방식)")
        keep, missed = g.keep_flow_exact(cands, DAY, final_group.flow_rows)
        _, after = daily_live.decide(state, keep, px, {}, {}, kin)
        self.assertEqual([(b["code"], b["칸"]) for b in after], [("B00001", 1)], "후보 단계 거르기 → 정상 차순위를 삼")
        self.assertEqual([m["code"] for m in missed], ["A00001"])


class DailyFlowRun(unittest.TestCase):
    STALE6 = ("000100", "000101", "000102", "000103", "000104", "000105")

    def test_pool_health_88_9_closes_90_7_opens(self):
        out = world_run("daily", flow_stale=self.STALE6)               # 48/54 = 88.9%
        self.assertEqual(out["orders"], [["000010", "sell", 100]], "1일봉 매수 0 · 팔기는 그대로")
        g = gates_file(out)
        self.assertFalse(g["decisions"]["daily"]["open"])
        self.assertTrue(any("수급 풀 건강도" in r and "48/54" in r for r in g["decisions"]["daily"]["reasons"]), g["decisions"]["daily"])
        snap = audit_of(out, "daily")["곁"]["gates"]
        self.assertEqual((snap["open"], snap["checks"]["flow_pool"]["n"], snap["checks"]["flow_pool"]["exact"]), (False, 54, 48))
        self.assertEqual(audit_of(out, "daily")["입력"]["cands"], [])
        self.assertTrue(any(r.startswith("⚠️ 새 매수 막음(1일봉)") for r in out["discord"][0]))
        out = world_run("daily", flow_stale=self.STALE6[:5])            # 49/54 = 90.7%
        self.assertEqual(out["orders"], [["000010", "sell", 100], ["000030", "buy", 571]])
        self.assertTrue(gates_file(out)["decisions"]["daily"]["open"])

    def test_stale_only_pick_is_missed_opportunity(self):
        out = world_run("daily", flow_stale=("000030",))
        self.assertEqual(out["orders"], [["000010", "sell", 100]], "낡은 후보는 안 삼 · 팔기는 그대로")
        snap = audit_of(out, "daily")["곁"]["gates"]
        self.assertTrue(snap["open"], "풀 53/54 → 문은 열림(종목 검사가 따로 막음)")
        self.assertEqual([m["code"] for m in snap["checks"]["flow_missed"]], ["000030"])
        self.assertIn("수급 마지막 날 20261109 ≠ 앞 거래일 20261110", snap["checks"]["flow_missed"][0]["why"])
        self.assertEqual(audit_of(out, "daily")["입력"]["cands"], [])
        self.assertTrue(any("빠진 기회" in r for r in out["discord"][0]), out["discord"][0])
        self.assertFalse(any(r.startswith("⚠️ 새 매수 막음") for r in out["discord"][0]))

    def test_stale_top_normal_second_one_slot_buys_second(self):
        found = {"date": DAY, "breadth": 40.0, "b_group": [], "picks": [
            {"code": "000040", "name": "라", "갈래": ["정배열 추세"], "추세 기울기": 9.0},
            {"code": "000030", "name": "다", "갈래": ["추세 규칙"], "추세 기울기": 1.0}]}
        out = world_run("daily", found=found, flow_stale=("000040",), daily_cells=9)
        self.assertEqual([o[:2] for o in out["orders"]], [["000030", "buy"]], "정상 차순위를 삼(낡은 위 후보가 빈 칸을 차지하지 않음)")
        self.assertEqual([c["code"] for c in audit_of(out, "daily")["입력"]["cands"]], ["000030"])
        self.assertEqual([b["칸"] for b in audit_of(out, "daily")["결과"]["buys"]], [1])
        out = world_run("daily", found=found, daily_cells=9)            # 대조: 둘 다 정상 자료면 빈 칸 1을 위 후보가 차지(지금과 같음)
        self.assertEqual([o[:2] for o in out["orders"]], [["000040", "buy"]])


class EngineEtfRun(unittest.TestCase):
    def test_stale_etf_closes_engine_only(self):
        out = world_run("engine", etf_stale=("133690",))
        g = gates_file(out)
        self.assertFalse(g["decisions"]["engine"]["open"])
        self.assertTrue(g["decisions"]["basket"]["open"] and g["decisions"]["overlay"]["open"], g["decisions"])
        self.assertTrue(any("133690 20261109" in r for r in g["decisions"]["engine"]["reasons"]), g["decisions"]["engine"]["reasons"])
        self.assertEqual(sorted(o[0] for o in buys(out)), ["000040", "122630"], "바구니 · 덧붙임 매수는 그대로 · 엔진 매수만 빠짐")
        self.assertIn(("138230", 1000), sells(out), "엔진 규칙 매도는 그대로")
        snap = audit_of(out, "engine")["곁"]["gates"]
        self.assertEqual((snap["open"], snap["checks"]["etf_last"]["last"]["133690"], snap["checks"]["etf_last"]["P"]),
                         (False, "20261109", P))
        self.assertTrue(audit_of(out, "basket")["곁"]["gates"]["open"] and audit_of(out, "overlay")["곁"]["gates"]["open"])
        warn = [r for rows in out["discord"] for r in rows if r.startswith("⚠️ 새 매수 막음")]
        self.assertEqual(len(warn), 1, out["discord"])
        self.assertIn("빈칸 엔진", warn[0])
        self.assertNotIn("사건 바구니", warn[0])


# ───────────────────────── 2a단계: 감사 셈이 문이 뺀 주문을 거짓 '주문 빠짐'으로 세지 않음(끝까지 이은 시험) ─────────────────────────

class AuditAfterGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(ROOT / "research") not in sys.path:
            sys.path.insert(0, str(ROOT / "research"))
        import boost_audit
        cls.B = boost_audit

    def clean(self, out, bots):
        for bot in bots:
            self.assertEqual(self.B.orders_check(bot, audit_of(out, bot)), [], bot)

    def test_blocked_runs_have_no_false_missing(self):
        self.clean(world_run("engine"), ("engine", "basket", "overlay"))                      # 문 열림(바탕)
        out = world_run("engine", sync_ok=False)                                              # 모두 닫힘
        self.assertTrue(any(o[1] == "buy" for o in audit_of(out, "engine")["결과"]["orders"]), "판단 원본엔 엔진 매수가 있음")
        self.assertTrue(audit_of(out, "overlay")["주문 결과"]["gate_dropped"])
        self.clean(out, ("engine", "basket", "overlay"))
        self.clean(world_run("engine", etf_stale=("133690",)), ("engine", "basket", "overlay"))   # D2: 엔진만 닫힘
        self.clean(world_run("engine_swap", refresh=lambda *a, **k: 0), ("engine", "basket", "overlay"))  # D1 실패 · 교체는 매도만
        self.clean(world_run("daily", sync_ok=False), ("daily",))
        self.clean(world_run("daily", flow_stale=("000030",)), ("daily",))

    def test_forbidden_buy_line_after_gate_is_caught(self):
        out = world_run("engine", sync_ok=False)
        eng = copy.deepcopy(audit_of(out, "engine"))
        book = next(iter(eng["오늘 장부 주문"]))
        eng["오늘 장부 주문"][book].append({"key": f"{DAY}:buy:133690", "code": "133690", "side": "buy", "status": "접수"})
        self.assertEqual([t for t, _ in self.B.orders_check("engine", eng)], ["금지 주문"])
        ov = copy.deepcopy(audit_of(out, "overlay"))
        code = ov["주문 결과"]["gate_dropped"][0][0]
        book = next(iter(ov["오늘 장부 주문"]))
        ov["오늘 장부 주문"][book].append({"key": f"{DAY}:buy:{code}", "code": code, "side": "buy", "status": "접수"})
        self.assertEqual([t for t, _ in self.B.orders_check("overlay", ov)], ["금지 주문"])


# ───────────────────────── 2a단계: 수급 수집 목표 P · D7 거래량 건너뛰기 ─────────────────────────

class InvestorTarget(TmpCwd):
    DAYS = weekdays_until(P, 40)

    class Fake:
        """날짜를 주면 그날까지(그리고 upto까지) 서른 거래일을 주는 증권사 흉내(오래된 날 먼저)."""

        def __init__(self, days, upto):
            self.days, self.upto, self.asks = days, dict(upto), []

        def investor_daily(self, code, day):
            self.asks.append((code, day))
            got = [d for d in self.days if d <= min(day, self.upto.get(code, day))]
            return [{"date": d, "개인": -1.0, "외국인": 1.0, "기관": 0.0, "투신": 2.0, "연기금": 0.0, "사모": 0.0, "종가": 100.0}
                    for d in got[-30:]]

    def setUp(self):
        super().setUp()
        import collect_investor_history as C
        self.C = C
        self.keep = mock.patch.multiple(C, OUT=Path("investor-data"), START=self.DAYS[0])
        self.keep.start()

    def tearDown(self):
        self.keep.stop()
        super().tearDown()

    def seed(self, code, last):
        body = {"code": code, "cols": list(self.C.COLS), "rows": [[d, -1.0, 1.0, 0.0, 2.0, 0.0, 0.0, 100.0] for d in self.DAYS if d <= last],
                "처음까지": True}
        self.C.save(body)
        return Path(f"investor-data/{code}.json").read_bytes()

    def test_target_day(self):
        C = self.C
        mon = datetime(2026, 11, 9, 1, 0, tzinfo=KST)                 # 월요일 새벽
        self.assertEqual(C.target_day(mon), ("20261108", False), "달력이 없으면 실행 시각의 어제(예전 방식 · 확인 없음)")
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        self.assertEqual(C.target_day(mon), ("20261106", True), "달력 P = 금요일")
        self.assertEqual(C.target_day(datetime(2026, 11, 11, 2, 30, tzinfo=KST)), (P, True))

    def test_fill_checks_last_day_and_keeps_file(self):
        C = self.C
        p1 = self.DAYS[-2]
        self.seed("000001", self.DAYS[-4])
        added, _ = C.fill(self.Fake(self.DAYS, {}), "000001", P, expect=P)
        self.assertEqual((added, C.load("000001")["rows"][-1][0]), (3, P), "응답 마지막 날 = P → 붙임")
        raw = self.seed("000002", self.DAYS[-4])
        with self.assertRaises(C.NotLatest) as got:
            C.fill(self.Fake(self.DAYS, {"000002": p1}), "000002", P, expect=P)
        self.assertEqual(got.exception.args[0], p1)
        self.assertEqual(Path("investor-data/000002.json").read_bytes(), raw, "응답 마지막 날 ≠ P → 파일을 고치지 않음")
        with self.assertRaises(C.NotLatest):
            C.fill(self.Fake(self.DAYS, {"000003": p1}), "000003", P, expect=P)
        self.assertFalse(Path("investor-data/000003.json").exists(), "새 종목도 만들지 않음")
        C.fill(self.Fake(self.DAYS, {"000002": p1}), "000002", P)          # 달력을 못 읽은 날(확인 없음) → 예전처럼 붙임
        self.assertEqual(C.load("000002")["rows"][-1][0], p1)

    def test_main_one_line_and_file_untouched(self):
        import builtins
        import broker_kis
        C = self.C
        self.seed("000001", self.DAYS[-4])
        raw = self.seed("000002", self.DAYS[-4])
        fake = self.Fake(self.DAYS, {"000002": self.DAYS[-2]})
        with mock.patch.object(C, "codes_to_collect", lambda: ["000001", "000002"]), \
                mock.patch.object(broker_kis, "market", lambda: fake), mock.patch.object(C, "target_day", lambda: (P, True)):
            self.assertEqual(C.main(), 0)
        self.assertEqual(C.load("000001")["rows"][-1][0], P)
        self.assertEqual(Path("investor-data/000002.json").read_bytes(), raw)
        said = [" ".join(str(a) for a in c.args) for c in builtins.print.call_args_list]
        self.assertEqual(len([s for s in said if s.startswith("000002 · 응답 마지막 날")]), 1, said)
        self.assertTrue(any(s.startswith("수급 목표 날 20261110 · 판 고정 달력") for s in said), said)
        self.assertTrue(any("목표 날 아님(그대로) 1" in s for s in said), said)
        self.assertEqual({d for _, d in fake.asks}, {P}, "목표 P를 밝혀 물음")


class VolumeDone(TmpCwd):
    def put(self, code, last, fetched="2026-11-11", n=130, empty=None):
        import collect_volumes as V
        rows = [[d, 1000, 2000, 110.0, 90.0] for d in weekdays_until(last, n)]
        if empty:
            rows[-1][1 + V.KEEP.index(empty)] = None
        Path("volume-data").mkdir(exist_ok=True)
        Path(f"volume-data/{code}.json").write_text(json.dumps({"code": code, "칸": ["날짜", *V.KEEP], "날": rows, "fetched": fetched}),
                                                    encoding="utf-8")

    def test_done_today(self):
        import collect_volumes as V
        today, p1 = "2026-11-11", weekdays_until(P, 2)[0]
        self.put("000001", P)
        self.assertTrue(V.done_today("000001", today, P))
        self.put("000002", p1)
        self.assertFalse(V.done_today("000002", today, P), "마지막 줄이 기대 날 앞 → 다시 받음")
        self.assertTrue(V.done_today("000002", today), "기대 날을 모르면(달력 못 읽음) 예전 그대로")
        self.put("000003", P, empty="거래대금")
        self.assertFalse(V.done_today("000003", today, P), "마지막 줄 칸이 빔")
        self.put("000004", P, fetched="2026-11-10")
        self.assertFalse(V.done_today("000004", today, P))
        self.put("000005", P, n=100)
        self.assertFalse(V.done_today("000005", today, P))
        Path("volume-data/000006.json").write_text("[1, 2]", encoding="utf-8")
        self.assertFalse(V.done_today("000006", today, P), "꼴이 다르면 다시 받음")
        self.assertFalse(V.done_today("000009", today, P), "파일 없음")

    def test_expected_day(self):
        import collect_volumes as V
        now = datetime(2026, 11, 11, 2, 30, tzinfo=KST)
        self.assertIsNone(V.expected_day(now))
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        self.assertEqual(V.expected_day(now), P)

    def test_main_recollects_only_stale(self):
        import broker_kis
        import collect_volumes as V
        today = datetime.now(KST).strftime("%Y-%m-%d")
        self.put("000001", P, fetched=today)
        self.put("000002", weekdays_until(P, 2)[0], fetched=today)
        asked = []

        class Client:
            def daily(self, code, start, end, detail=False):
                asked.append(code)
                return [(d, {"거래량": 1000, "거래대금": 2000, "고가": 110.0, "저가": 90.0}) for d in weekdays_until(P, 30)]

            def history(self, code, days=0, detail=False):
                asked.append(code)
                return [(d, {"거래량": 1000, "거래대금": 2000, "고가": 110.0, "저가": 90.0}) for d in weekdays_until(P, 130)]
        with mock.patch.object(V, "codes_to_collect", lambda: ["000001", "000002"]), \
                mock.patch.object(broker_kis, "market", lambda: Client()), mock.patch.object(V, "expected_day", lambda: P), \
                mock.patch.dict(os.environ, {"VOLUME_SKIP_DONE": "1"}):
            self.assertEqual(V.main(), 0)
        self.assertEqual(asked, ["000002"], "다 받은 종목은 건너뛰고 마지막 줄이 낡은 종목만 다시 받음")


class Structure2a(unittest.TestCase):
    def test_d2_d4_placement(self):
        text = (ROOT / "idle_live.py").read_text(encoding="utf-8")
        run = text[text.index("def run(now=None):"):]
        marks = ['gate = gates.begin(day, "engine", sync_ok', "gate.check_etf(etf_last_days(day))", '_audit.record(STATE, day, "engine"',
                 'if not gate.allows_new_risk("engine"):']
        at = [run.index(m) for m in marks]
        self.assertEqual(at, sorted(at), "D2는 판단 기록 · 엔진 매수 빼기 앞")
        daily = (ROOT / "daily_live.py").read_text(encoding="utf-8")
        run = daily[daily.index("def run(now=None):"):]
        marks = ['gate = gates.begin(day, "daily", sync_ok', "gate.check_flow_pool(pool, day, flow_of)",
                 "cands, flow_missed = gate.keep_flow_exact(cands, day, flow_of)", "cands = []           # 자료가 덜",
                 "daily_in = _audit.safe(", "sells, buys = decide(state, cands,"]
        at = [run.index(m) for m in marks]
        self.assertEqual(at, sorted(at), "D4 (나)는 decide(정렬 · 자르기) 앞 · 판단 기록 입력 앞")

    def test_workflow_smoke_before_first_order(self):
        wf = (ROOT / ".github" / "workflows" / "daily-live.yml").read_text(encoding="utf-8")
        smoke, first = wf.index("python gate_smoke.py"), wf.index("python idle_live.py")
        self.assertLess(smoke, first, "시작 전 점검은 첫 15:10 주문 단계 앞")
        step = wf[wf.rindex("- name:", 0, smoke):wf.index("- name:", smoke)]
        self.assertIn("continue-on-error: true", step)
        self.assertIn("timeout-minutes:", step)
        idle = wf[wf.rindex("- name:", 0, first):wf.index("python daily_live.py")]
        self.assertLess(idle.index('git commit -q -m "Gate smoke"'), idle.index("python idle_live.py"),
                        "점검 파일은 봇의 저장소 맞추기(git pull --rebase) 전에 로컬 커밋")
        for part in (idle, wf[wf.index("python daily_live.py"):]):
            self.assertLess(part.index("mkdir -p gates gate-smoke"), part.index("git add -A gates gate-smoke"))
        self.assertNotIn("tests.test_boost_d", wf, "매매 전 시험 단계는 그대로(무거운 시험은 CI 전체 discover)")


if __name__ == "__main__" and "--golden" in sys.argv:
    make_golden()
    print("얼린 결과를 씀 ·", GOLDEN)
    sys.exit(0)

if __name__ == "__main__":
    unittest.main()
