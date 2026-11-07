"""BOOST-0001-D 1단계 · 2a단계(사전등록 판 3 §4-1 반례) 시험.

- 공통 문(gates) · 판 고정 달력(trade_calendar) · 시작 전 점검(gate_smoke) · D6(저장소 맞추기 실패) · D1(15:05 같은 작업 안 다시 셈) ·
  덧붙임 buy_ok(교체면 매도만 + applied = "pending") · 판단 기록 곁 칸 gates · 기록 · 문 파일 쓰기 실패가 매매를 멈추지 않음.
- **문이 모두 열리면 고치기 전 코드와 주문 · 장부 · 알림이 바이트까지 같음**: 같은 가짜 세상(가짜 증권사 · 가짜 시계 · 임시 폴더)을
  고치기 전 판(BASE · origin/main)으로 돌린 결과를 tests/fixtures/boost_d_golden.json에 얼려 두고 지금 코드 결과와 견줌.
  BASE 커밋이 있는 곳(로컬)에서는 그 얼린 결과가 정말 BASE 코드의 결과인지도 다시 돌려 확인(얕은 받기 CI에서는 그 하나만 건너뜀).
- 2a단계: D2(엔진 ETF 마지막 날 = 달력 P → 엔진만 닫음) · D4 두 층(풀 건강도 89% / 90% · 후보 단계 주문 안전 거르기 ·
  낡은 상위 1 + 정상 차순위 1 + 빈 칸 1 → 정상 차순위를 삼) · 수급 수집 목표 P · D7 거래량 건너뛰기 · 감사 셈 문 양방향(끝까지 이은 시험).
- 2b단계: D3 공시 manifest(쪽 완결성 · 빈 응답 · 오류 status · 0건 정상 · digest 불일치 · 아침 최종 확인 첫 성공만 · 바구니 문이
  HEAD의 manifest · 트리 지문 결속) · D5 달력 만드는 도구(두 원천 같음 / 다름 / 조회 실패 / 같은 내용 / 바뀐 공지 / 해 넘김) ·
  엔진 주 끝(달력 · HOLIDAYS 같으면 결과 같음) · 시작 전 점검 파일 작업마다(git pull --rebase 실험) · 수급 수집 목록 + 1일봉 풀.
- 2c단계(GPT 구현 검토 6705430244): A 공시 확인 범위 = 바구니 입력 창(토 · 일 접수 반례 · 범위 · 질의 지문 · 사건 지문 · 바구니 실제 창) ·
  B 세션을 지어내지 않음(평소 · 특수 세션 영수증 · unknown 날 문 닫힘 · 수능 · 연말 · 연초 고정 자료 · 지문 변조 · 원천 누락 · 마른 실행) ·
  C 전체 시험 차이 검사(tools/test_diff.py) · 작업 흐름 · 부트스트랩 문(gates/ARMED.json).
- 실제 증권사 · DART · KRX를 부르지 않음 · 비밀값 없음(가짜 키 글자만)."""
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
SMOKE = f"gate-smoke/{DAY}-local-0.json"                   # 2b단계: 시작 전 점검 파일은 작업마다 다른 이름(로컬 = <날>-local-0)
MANIFEST = f"event-manifest/{P}-local-0.json"              # 2b단계 D3: 가짜 세상의 공시 아침 최종 확인 manifest(t0 = P)
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


REGULAR_URL = "https://regulation.krx.co.kr/contents/RGL/03/03010100/RGL03010100T1.jsp"   # 거래소 규정/제도 · 유가증권시장 매매거래 일반절차 탭
REAL_REGULAR = ROOT / "tests" / "fixtures" / "krx_regular_session_RGL03010100T1.html"     # 2026-11-07에 받은 그 화면 원문 사본
REAL_REGULAR_SHA = "fb10f1d109b37e8ab1f06c277a7f4a091a73fd398e4c7b3890caae12efdc1ffb"


def regular_receipt(year, sha="1" * 64, **kw):
    """평소 세션 영수증(2c단계 · 가짜 원문 지문 · 개장 09:00 · 마감 15:30)."""
    body = {"source_url": REGULAR_URL, "notice_no": None, "effective_from": f"{year}0101", "raw_sha256": sha, "open": "0900",
            "close": "1530"}
    body.update(kw)
    return body


def calendar_body(year, holidays=(), special=None, sha=None, sessions=None, unknown=()):
    """판 고정 달력 판 본문(그 해 모든 날 · 주말 · 휴장 = null · 평일 09:00 ~ 15:30 · 2c단계: 평소 세션 영수증 · unknown = 세션 원천 없는 날)."""
    import trade_calendar
    days, d = {}, date(year, 1, 1)
    while d.year == year:
        k = d.strftime("%Y%m%d")
        days[k] = None if d.weekday() >= 5 or k in holidays else {"open": "0900", "close": "1530"}
        d += timedelta(days=1)
    for k in unknown:
        days[k] = {"session": "unknown"}
    days.update(special or {})
    sessions = sessions if sessions is not None else {"regular": regular_receipt(year), "special": []}
    return {"source_url": "https://example.invalid/krx-holiday-notice", "notice_no": f"시험-{year}",
            "fetched_at_utc": "2026-11-01T00:00:00Z", "effective_from": f"{year}0101", "parser_version": "시험 1",
            "raw_sha256": "0" * 64, "normalized_sha256": sha or trade_calendar.normalized_digest(days, sessions), "days": days,
            "sessions": sessions}


def write_calendar(folder, year, version=1, **kw):
    p = Path(folder) / f"krx-{year}-v{version}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(calendar_body(year, **kw), ensure_ascii=False), encoding="utf-8")
    return p


def arm(gates_folder="gates", calendar_folder="calendar", year=2026, on="20261110", run_id="1", **kw):
    """부트스트랩 문(2c단계): 지금 판의 달력 sha256으로 gates/ARMED.json을 씀(사람이 첫 실행 영수증을 확인한 뒤 적는 파일 흉내)."""
    import trade_calendar
    cal = trade_calendar.load_year(year, calendar_folder)
    body = {"calendar_sha256": cal["sha256"] if cal else "0" * 64, "confirmed_on": on, "run_id": run_id}
    body.update(kw)
    p = Path(gates_folder) / "ARMED.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return body


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
        if opt.get("armed", True):                        # 2c단계 부트스트랩 문: 사람이 확인한 달력 sha256(armed=False면 없음 · dict면 칸 바꿈)
            arm(root / "gates", root / "calendar", **(opt["armed"] if isinstance(opt.get("armed"), dict) else {}))
    if opt.get("smoke", True):
        w(SMOKE, {"date": DAY, "ok": True, "version": 1, "sha256": None, "P": P, "reasons": [], "run_id": None})
    for rel in opt.get("block", ()):                      # 쓰기를 막을 자리(그 이름의 파일을 먼저 만들어 폴더를 못 만들게)
        w(rel, "막음")
    for rel in opt.get("block_dir", ()):                  # 그 이름의 폴더를 먼저 만들어 파일을 못 쓰게
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel, body in (opt.get("extra_files") or {}).items():
        w(rel, body)
    man = opt.get("manifest", "final")                    # 2b단계 D3: 공시 아침 최종 확인 manifest(None = 없음 · 'regular' · dict = 칸 바꿈)
    if man:
        w(MANIFEST, manifest_body(root / "event-data", **({"mode": man} if isinstance(man, str) else man)))
    if opt.get("git", True):                              # 판단 때 HEAD 확인(D3) — 가짜 세상 전체를 한 커밋으로
        git_commit_all(root)
    for rel, body in (opt.get("after_commit") or {}).items():      # 커밋 뒤에 고친 파일(HEAD와 다름)
        w(rel, body)
    return px, Broker(500_000 if room else 50_000_000, positions, px), prices


def tree_sha(folder):
    """사전등록 §1.2 정의 그대로(event_manifest.py와 따로 셈): event-data/*.json 이름 차례 [경로, 파일 sha256] → 빈칸 없는 JSON → sha256."""
    items = [[f"event-data/{p.name}", hashlib.sha256(p.read_bytes()).hexdigest()]
             for p in sorted(Path(folder).glob("*.json"), key=lambda q: q.name)]
    return hashlib.sha256(json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def canon_sha(x):
    """사전등록 §1.2 정의 그대로(event_manifest.py와 따로 셈): 열쇠 차례 · 빈칸 없는 JSON(UTF-8) → sha256."""
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def query_sha(begin, end):
    """정규화 질의 지문(event_manifest.query_digest와 따로 셈 · 키 · 쪽 번호 뺌 · 물음 칸 100 · date · asc)."""
    return canon_sha({"endpoint": "list.json", "bgn_de": begin, "end_de": end, "page_count": 100, "sort": "date", "sort_mth": "asc",
                      "corp_code": None})


def window_events(data, begin, end):
    """data 폴더(event-data)의 접수일 begin ~ end 사건 → [코드, 날, 갈래, 제목 60자] 정렬 · 겹침 없음(event_manifest와 따로 셈)."""
    got = set()
    for f in sorted(Path(data).glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")).get("rows") or []:
            if begin <= str(r.get("date")) <= end:
                got.add((f.stem, str(r["date"]), str(r.get("kind")), str(r.get("title"))[:60]))
    return [list(x) for x in sorted(got)]


def manifest_body(data, t0=P, day=DAY, mode="final", done="2026-11-10T23:25:00Z", begin=None, **kw):
    """공시 manifest 본문(모든 칸 · 기본 = D 아침 08:25 한국 시각에 끝난 성공 · 트리 지문은 data 폴더 그대로 ·
    2c단계: 질의 범위 begin ~ t0(기본 t0 하루 = 가짜 세상 화요일 t0의 바구니 창) · 질의 지문 · 범위 사건 지문을 data 폴더로 셈)."""
    begin = begin or t0
    events = window_events(data, begin, t0)
    body = {"kind": "event-manifest", "version": 1, "mode": mode, "t0": t0, "D": day if mode == "final" else None,
            "query_begin": begin, "query_end": t0, "request_started_at_utc": "2026-11-10T23:20:00Z",
            "response_received_at_utc": ["2026-11-10T23:20:01Z"], "status": "000", "total_count": 1, "total_page": 1,
            "pages_received": 1, "rows_received": 1, "retry_count": 0, "pages": [], "normalized_query_digest": query_sha(begin, t0),
            "normalized_event_digest": canon_sha(events), "events": len(events), "t0_events": events,
            "stored_event_digest": canon_sha(events), "event_data_tree_digest": tree_sha(data), "GITHUB_RUN_ID": None,
            "GITHUB_RUN_ATTEMPT": None, "GITHUB_WORKFLOW_SHA": None, "persisted": True, "ok": True, "why": "", "completed_at_utc": done}
    body.update(kw)
    return body


def git_commit_all(root, message="가짜 세상"):
    """root를 git 저장소로 만들고(없으면) 모든 파일을 한 커밋에(바깥 GIT_* 값에 끌려가지 않게 · 서명 · 갈고리 끔)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_AUTHOR_NAME="시험", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="시험",
               GIT_COMMITTER_EMAIL="t@example.invalid")
    cmds = ([] if (Path(root) / ".git").exists() else [["-c", "init.defaultBranch=main", "init", "-q"]]) + [
        ["add", "-A"], ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", message]]
    for args in cmds:
        subprocess.run(["git", *args], cwd=str(root), env=env, check=True, capture_output=True, timeout=60)


def _snapshot_files(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.relative_to(root).parts:          # 가짜 세상의 git 저장소 속은 빼고(2b단계)
            try:
                out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                out[p.relative_to(root).as_posix()] = None
    return out


def world_run(kind, **opt):
    """가짜 세상에서 봇 한 번(engine* = idle_live.run 15:05 시작 · daily = daily_live.run 15:20 시작) → 결과 dict.
    opt: sync_ok(저장소 맞추기 값을 바꿔 끼움) · refresh(hourly_a.refresh_near를 바꿔 끼움) · missing(시세 없는 코드) ·
    calendar · smoke(파일을 둘지) · live_p · prices_last · m15_body · block · block_dir · start(시 · 분 · 초) · spy(덧붙임 인자 기록) ·
    2a단계: etf_stale(P 줄이 빠진 엔진 ETF) · flow_stale(수급이 P−1에서 끝나는 종목) · flow_files · found(1일봉 후보) · daily_cells.
    2b단계: manifest(공시 아침 확인 · None = 없음 · 'regular' · dict = 칸 바꿈) · git(가짜 세상을 커밋할지) · after_commit(커밋 뒤 고친 파일).
    2c단계: armed(부트스트랩 문 파일 · False = 없음 · dict = 칸 바꿈) · live_seq(증권사 앞 거래일을 부를 때마다 차례로 줄 값)."""
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
    for name in ("gates", "gate_smoke", "trade_calendar", "event_manifest"):   # 새 모듈(고치기 전 코드로 돌 때도 있어도 그만)
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
            seq = list(opt.get("live_seq") or [])          # 2c단계: 증권사 앞 거래일을 부를 때마다 다르게(문 셈 뒤 바뀐 날 흉내)
            st.enter_context(mock.patch.object(data_guard, "prev_trading_day",
                                               lambda client, day: seq.pop(0) if seq else opt.get("live_p", P)))
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
        body["normalized_sha256"] = C.normalized_digest(body["days"], body["sessions"])
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
        arm()
        Path("gate-smoke").mkdir()
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True, "version": 1}), encoding="utf-8")
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
        arm()
        Path("gate-smoke").mkdir()
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        self.assertTrue(gates.begin(DAY, "daily", True, live_p=P).allows_new_risk("daily"))
        cases = {"저장소": dict(sync_ok=False), "다름": dict(live_p="20261109"), "못 받아": dict(live_p=None)}
        for word, kw in cases.items():
            args = {"sync_ok": True, "live_p": P, **kw}
            g = gates.begin(DAY, "daily", args["sync_ok"], live_p=args["live_p"])
            self.assertFalse(g.allows_new_risk("daily"), word)
            self.assertTrue(any(word in r for r in g.reasons()), (word, g.reasons()))
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": False, "reasons": ["달력 없음"]}), encoding="utf-8")
        g = gates.begin(DAY, "engine", True, live_p=P)
        self.assertFalse(any(g.allows_new_risk(d) for d in ("engine", "basket", "overlay")))
        self.assertTrue(any("시작 전 점검" in r for r in g.reasons()))
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
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
        body = json.loads(Path(SMOKE).read_text(encoding="utf-8"))
        self.assertFalse(body["ok"])
        self.assertTrue(any("달력" in r for r in body["reasons"]))
        ok, why, _ = gate_smoke.status(DAY)
        self.assertFalse(ok)
        self.assertIn("점검 실패", why)
        self.assertEqual(gate_smoke.status("20261112")[:2], (False, "시작 전 점검 파일이 없음"))
        Path("gate-smoke/20261112-local-0.json").write_text("{", encoding="utf-8")
        self.assertFalse(gate_smoke.status("20261112")[0])
        Path("gate-smoke/20261113-local-0.json").write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        self.assertIn("오늘 것이 아님", gate_smoke.status("20261113")[1])
        Path(f"gate-smoke/{DAY}-2-0.json").write_text(json.dumps({"date": DAY, "ok": True, "run_id": "1"}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "2"}):                 # 이름은 작업 2 것인데 본문은 작업 1 것
            self.assertIn("이 작업의 것이 아님", gate_smoke.status(DAY)[1])
        Path(f"gate-smoke/{DAY}-1-0.json").write_text(json.dumps({"date": DAY, "ok": True, "run_id": "1"}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "1"}):
            self.assertTrue(gate_smoke.status(DAY)[0])
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "3"}):                 # 다른 작업 파일만 있으면 '없음'(자기 것만 읽음)
            self.assertEqual(gate_smoke.status(DAY)[:2], (False, "시작 전 점검 파일이 없음"))

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
        out = world_run("engine", block=("idle-live/audit", "basket-live/audit", "overlay-live/audit"),
                        block_dir=("idle-live/near-now.json", "gates/20261111.json"))     # 2c단계: gates/ARMED.json이 있어야 해 문 파일 자리를 폴더로 막음
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
        out = world_run("daily", block=("daily-live/audit",), block_dir=("gates/20261111.json",))
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
        body["normalized_sha256"] = C.normalized_digest(body["days"], body["sessions"])
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
            arm()
        Path("gate-smoke").mkdir(exist_ok=True)
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
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
        arm()
        Path("gate-smoke").mkdir(exist_ok=True)
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
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
        body["normalized_sha256"] = C.normalized_digest(body["days"], body["sessions"])
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
        # 2b단계 §3: 점검 파일이 작업마다 다른 새 파일(추적 밖)이라 봇의 저장소 맞추기(git pull --rebase)를 막지 않음 → 예전 로컬 커밋은 뺌
        # (실제 git으로 확인하는 시험: SmokeRunName.test_untracked_new_file_does_not_block_pull_rebase)
        self.assertNotIn('git commit -q -m "Gate smoke"', idle)
        self.assertLess(idle.index("python idle_live.py"), idle.index("git add -A gates gate-smoke"), "점검 · 문 기록은 봇이 돈 뒤 함께 올림")
        for part in (idle, wf[wf.index("python daily_live.py"):]):
            self.assertLess(part.index("mkdir -p gates gate-smoke"), part.index("git add -A gates gate-smoke"))
        self.assertNotIn("tests.test_boost_d", wf, "매매 전 시험 단계는 그대로(무거운 시험은 CI 전체 discover)")


# ───────────────────────── 2b단계: D3 공시 manifest(수집기 · 쪽 완결성 · 아침 최종 확인) ─────────────────────────

def drow(code, title, day=P, no=1):
    """가짜 OpenDART 공시검색 한 줄."""
    return {"corp_name": f"회사{code}", "stock_code": code, "report_nm": title, "rcept_dt": day, "rcept_no": f"{day}{no:06d}"}


ROWS_T0 = [drow("000040", "주요사항보고서(무상증자결정)", no=1), drow("000020", "주요사항보고서(자기주식취득결정)", no=2),
           drow("999999", "주요사항보고서(유상증자결정)", no=3), drow("000040", "주주총회소집공고", no=4),
           drow("000030", "현금ㆍ현물배당결정", no=5)]
CODES_T0 = ["000020", "000030", "000040"]
EVENTS_T0 = [["000020", P, "자사주취득", "주요사항보고서(자기주식취득결정)"], ["000030", P, "배당", "현금ㆍ현물배당결정"],
             ["000040", P, "무상증자", "주요사항보고서(무상증자결정)"]]


class FakeDart:
    """가짜 OpenDART(dart_raw · 본문 그대로): 물은 접수일(bgn_de ~ end_de) 줄을 per줄씩 쪽으로 나눠 줌 · 0줄이면 013 ·
    override[쪽] = 차례로 줄 본문(예외면 올림) · dates=False면 날짜를 가리지 않음(고장 흉내)."""

    def __init__(self, rows=(), per=2, override=None, dates=True):
        self.rows, self.per, self.dates, self.calls = list(rows), per, dates, []
        self.override = {k: list(v) for k, v in (override or {}).items()}

    def dart_raw(self, endpoint, **params):
        assert endpoint == "list.json" and "corp_code" not in params and "crtfc_key" not in params
        self.calls.append(dict(params))
        page = params["page_no"]
        if self.override.get(page):
            got = self.override[page].pop(0)
            if isinstance(got, Exception):
                raise got
            return got
        rows = [r for r in self.rows if not self.dates or params["bgn_de"] <= r["rcept_dt"] <= params["end_de"]]
        if not rows:
            return {"status": "013", "message": "조회된 데이타가 없습니다."}
        return {"status": "000", "message": "정상", "page_no": page, "page_count": self.per, "total_count": len(rows),
                "total_page": -(-len(rows) // self.per), "list": rows[(page - 1) * self.per: page * self.per]}


class EventCwd(TmpCwd):
    """D3 시험 도움: 쉬지 않는 수집기 · 씨앗 공시 파일(다른 날 줄) · 판 고정 달력."""

    def setUp(self):
        super().setUp()
        import collect_events
        self.CE = collect_events
        self.keep = mock.patch.multiple(collect_events, PAUSE=0, RETRY_WAIT=0)
        self.keep.start()
        Path("event-data").mkdir()
        for code in CODES_T0:
            Path(f"event-data/{code}.json").write_text(json.dumps(
                {"code": code, "fetched": "2026-11-07", "rows": [{"date": "20261102", "kind": "공급계약", "title": "단일판매ㆍ공급계약체결"}]},
                ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.keep.stop()
        super().tearDown()

    @staticmethod
    def data_bytes():
        return {p.name: p.read_bytes() for p in sorted(Path("event-data").glob("*.json"))}

    @staticmethod
    def manifests():
        return sorted(p.name for p in Path("event-manifest").glob("*.json")) if Path("event-manifest").exists() else []


class EventFetch(EventCwd):
    def setUp(self):
        super().setUp()
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)        # 2c단계: collect_day는 판 고정 달력으로 확인 범위(P 하루)를 셈

    def test_complete_pages_and_manifest_fields(self):
        import event_manifest as M
        fake = FakeDart(ROWS_T0, per=2)
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "77", "GITHUB_RUN_ATTEMPT": "2", "GITHUB_WORKFLOW_SHA": "c" * 40}):
            body, path = self.CE.collect_day(fake, CODES_T0, P, "final", day=DAY)
        self.assertTrue(body["ok"], body["why"])
        self.assertEqual(path.as_posix(), f"event-manifest/{P}-77-2.json")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), body, "파일 = 본문")
        for k in M.FIELDS:
            self.assertIn(k, body)
        self.assertEqual((body["query_begin"], body["query_end"], body["t0"], body["D"], body["mode"]), (P, P, P, DAY, "final"))
        self.assertEqual((body["status"], body["total_count"], body["total_page"], body["pages_received"], body["rows_received"],
                          body["retry_count"], body["persisted"]), ("000", 5, 3, 3, 5, 0, True))
        self.assertEqual(len(body["response_received_at_utc"]), 3, "쪽마다 받은 시각")
        self.assertTrue(all(M.parse_utc(x) for x in body["response_received_at_utc"] + [body["request_started_at_utc"],
                                                                                        body["completed_at_utc"]]))
        self.assertEqual((body["GITHUB_RUN_ID"], body["GITHUB_RUN_ATTEMPT"], body["GITHUB_WORKFLOW_SHA"]), ("77", "2", "c" * 40))
        self.assertEqual(body["normalized_event_digest"], hashlib.sha256(json.dumps(EVENTS_T0, sort_keys=True, separators=(",", ":"),
                                                                                    ensure_ascii=False).encode()).hexdigest())
        self.assertEqual(body["stored_event_digest"], body["normalized_event_digest"])
        self.assertEqual(body["t0_events"], EVENTS_T0, "manifest의 t0 사건 집합(H-D3 대조용)")
        self.assertEqual(body["event_data_tree_digest"], tree_sha("event-data"), "저장 뒤 트리 지문(사전등록 정의)")
        self.assertRegex(body["normalized_query_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual([(c["bgn_de"], c["end_de"], c["page_no"], c["page_count"], c["sort"], c["sort_mth"]) for c in fake.calls],
                         [(P, P, n, 100, "date", "asc") for n in (1, 2, 3)], "query_begin = query_end = t0 · 끝 쪽까지")
        rows = json.loads(Path("event-data/000040.json").read_text(encoding="utf-8"))["rows"]
        self.assertIn({"date": P, "kind": "무상증자", "title": "주요사항보고서(무상증자결정)"}, rows)
        self.assertFalse(Path("event-data/999999.json").exists(), "대상 밖 종목은 안 씀")

    def test_incomplete_pages_write_no_data(self):
        page2 = FakeDart(ROWS_T0, per=2).dart_raw("list.json", bgn_de=P, end_de=P, page_no=2)
        cases = {
            "쪽 빠짐(둘째 쪽 013)": ({2: [{"status": "013", "message": "조회된 데이타가 없습니다."}]}, "일찍 끊김"),
            "쪽 번호 어긋남": ({3: [dict(page2, page_no=2)]}, "칸이 이상함"),
            "빈 응답": ({1: [{}]}, "빈 응답"),
            "오류 status": ({1: [{"status": "020", "message": "요청 제한"}]}, "오류 status 020"),
            "점검 중(다시 물어도)": ({1: [{"status": "800"}] * 3}, "오류 status 800"),
            "연결 오류(다시 물어도)": ({2: [RuntimeError("끊김")] * 3}, "응답을 못 받음"),
            "줄 수 모자람": ({2: [dict(page2, list=page2["list"][:1])]}, "받은 줄 4 ≠ 총 건수 5"),
            "접수번호 겹침": ({2: [dict(page2, list=ROWS_T0[:2])]}, "겹친 줄 2개"),
            "총 쪽 수 바뀜": ({2: [dict(page2, total_page=4)]}, "첫 쪽"),
        }
        before = self.data_bytes()
        for name, (override, word) in cases.items():
            with self.subTest(name):
                body, path = self.CE.collect_day(FakeDart(ROWS_T0, per=2, override=override), CODES_T0, P, "final", day=DAY)
                self.assertFalse(body["ok"], name)
                self.assertFalse(body["persisted"], "끝 쪽까지 못 받으면 저장하지 않음")
                self.assertIn(word, body["why"])
                self.assertEqual(self.data_bytes(), before, "event-data 그대로(중간판 없음)")
                self.assertFalse(json.loads(path.read_text(encoding="utf-8"))["ok"], "실패 manifest도 남김(감사용)")
                if name.startswith("쪽 빠짐"):
                    self.assertLess(body["pages_received"], body["total_page"])
                if name.startswith("점검 중") or name.startswith("연결 오류"):
                    self.assertEqual(body["retry_count"], 2)
        ok, _ = self.CE.collect_day(FakeDart(ROWS_T0, per=2, override={1: [RuntimeError("한 번 끊김")]}), CODES_T0, P, "final", day=DAY)
        self.assertEqual((ok["ok"], ok["retry_count"]), (True, 1), "한 번 끊겼다 다시 받으면 성공(다시 물은 수를 적음)")

    def test_zero_rows_013_is_normal_and_stale_t0_row_mismatch(self):
        import event_manifest as M
        body, _ = self.CE.collect_day(FakeDart([]), CODES_T0, P, "final", day=DAY)
        self.assertTrue(body["ok"], body["why"])
        self.assertEqual((body["status"], body["total_count"], body["total_page"], body["pages_received"], body["events"]),
                         ("013", 0, 0, 0, 0), "첫 쪽 013 = 정상 0건(OpenDART 안내 '조회된 데이타가 없습니다')")
        self.assertEqual(body["normalized_event_digest"], M.digest([]))
        old = json.loads(Path("event-data/000040.json").read_text(encoding="utf-8"))
        old["rows"].append({"date": P, "kind": "무상증자", "title": "옛 제목(응답에 없음)"})
        Path("event-data/000040.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
        body, _ = self.CE.collect_day(FakeDart(ROWS_T0), CODES_T0, P, "final", day=DAY)
        self.assertEqual((body["ok"], body["persisted"]), (False, True), "저장은 됐지만 저장된 t0 목록 ≠ 응답 → ok 거짓")
        self.assertIn("저장된 t0 사건 4개가 응답의 t0 사건 3개와 다름", body["why"])
        self.assertNotEqual(body["stored_event_digest"], body["normalized_event_digest"])

    def test_other_day_rows_in_t0_query_fail(self):
        body, _ = self.CE.collect_day(FakeDart(ROWS_T0[:2] + [drow("000030", "현금ㆍ현물배당결정", day=DAY, no=9)], dates=False),
                                      CODES_T0, P, "final", day=DAY)
        self.assertFalse(body["ok"])
        self.assertIn("다른 접수일 줄 1개", body["why"])

    def test_recent_incomplete_raises_and_legacy_provider(self):
        before = self.data_bytes()
        with self.assertRaises(self.CE.Incomplete):
            self.CE.recent(FakeDart(ROWS_T0, override={2: [{"status": "020"}]}), CODES_T0, 5, today=DAY)
        self.assertEqual(self.data_bytes(), before, "예전처럼 조용히 앞 쪽만 저장하지 않음")

        class Legacy:                                  # 예전 꼴(Official.dart): 013이면 None · 000이면 본문
            def __init__(self, answer):
                self.answer, self.calls = answer, 0

            def dart(self, endpoint, **params):
                self.calls += 1
                return self.answer
        self.assertEqual(self.CE.recent(Legacy(None), CODES_T0, 5, today=DAY), 0, "013(None) = 정상 0건")
        with self.assertRaises(self.CE.Incomplete):            # 쪽 칸이 없는 본문은 완결성을 못 봄 → 저장 안 함
            self.CE.recent(Legacy({"list": ROWS_T0, "total_page": 1}), CODES_T0, 5, today=DAY)
        self.assertEqual(self.data_bytes(), before)
        fake = FakeDart(ROWS_T0, per=10)
        with mock.patch.object(self.CE, "datetime", Clock((8, 20, 0)).dt_class()):     # 한국 08:20 = UTC 전날 23:20
            self.CE.recent(fake, CODES_T0, 5)
        self.assertEqual((fake.calls[0]["bgn_de"], fake.calls[0]["end_de"]), ("20261106", DAY), "끝 날은 한국 날짜(러너 UTC 날짜 아님)")

    def test_verify_run(self):
        self.assertEqual(self.CE.verify_run(), 0, "이 작업의 manifest가 없으면 자료만")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "5", "GITHUB_RUN_ATTEMPT": "1"}):
            self.CE.collect_day(FakeDart(ROWS_T0), CODES_T0, P, "final", day=DAY)
            self.assertEqual(self.CE.verify_run(), 0)
            Path("event-data/000030.json").write_text("{}", encoding="utf-8")         # manifest를 쓴 뒤 자료가 바뀜
            self.assertEqual(self.CE.verify_run(), 1)
        Path("event-manifest/20261109-9-1.json").write_text("{", encoding="utf-8")      # 다른 작업의 깨진 파일은 안 봄
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "6", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertEqual(self.CE.verify_run(), 0)
        Path(f"event-manifest/{P}-6-1.json").write_text(json.dumps({"kind": "event-manifest"}), encoding="utf-8")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "6", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertEqual(self.CE.verify_run(), 1, "칸이 빠진 manifest")


class EventFinalCheck(EventCwd):
    def test_calendar_holiday_and_t0_guards(self):
        fake = FakeDart(ROWS_T0)
        self.assertEqual(self.CE.final_check(fake, CODES_T0, DAY), 1, "달력이 없으면 실패")
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026 + (DAY,))
        self.assertEqual(self.CE.final_check(fake, CODES_T0, DAY), 0, "휴장이면 하지 않음")
        write_calendar("calendar", 2026, version=2, holidays=HOLIDAYS_2026)
        self.assertEqual(self.CE.final_check(fake, CODES_T0, DAY, t0="20261109"), 1, "t0가 달력 P와 다르면 하지 않음")
        self.assertEqual((fake.calls, self.manifests()), ([], []))

    def test_first_success_only_and_retry_after_failure(self):
        import event_manifest as M
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        bad = FakeDart(ROWS_T0, override={1: [{"status": "800"}] * 3})
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertEqual(self.CE.final_check(bad, CODES_T0, DAY), 1, "08:20 실패")
        self.assertIsNone(M.first_ok(P, DAY))
        good = FakeDart(ROWS_T0)
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "2", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertEqual(self.CE.final_check(good, CODES_T0, DAY), 0, "10:20 다시 → 성공")
        self.assertEqual(M.first_ok(P, DAY), f"{P}-2-1.json")
        again = FakeDart(ROWS_T0)
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "3", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertEqual(self.CE.final_check(again, CODES_T0, DAY, t0=P), 0, "12:20 → 이미 성공 → 건너뜀")
        self.assertEqual(again.calls, [], "다시 묻지 않음")
        self.assertEqual(self.manifests(), [f"{P}-1-1.json", f"{P}-2-1.json"], "첫 성공만(셋째 manifest 없음)")
        body = json.loads(Path(f"event-manifest/{P}-2-1.json").read_text(encoding="utf-8"))
        self.assertEqual((body["mode"], body["D"], body["ok"]), ("final", DAY, True))

    def test_regular_window_and_t0_record(self):
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        fake = FakeDart(ROWS_T0 + [drow("000020", "주요사항보고서(무상증자결정)", day=DAY, no=7)], per=10)
        self.assertEqual(self.CE.regular(fake, CODES_T0, 5, DAY), 0)
        self.assertEqual([(c["bgn_de"], c["end_de"]) for c in fake.calls], [("20261106", DAY), (DAY, DAY)], "이어 받기 + 그날 t0")
        body = json.loads(Path(f"event-manifest/{DAY}-local-0.json").read_text(encoding="utf-8"))
        self.assertEqual((body["mode"], body["t0"], body["D"], body["ok"]), ("regular", DAY, None, True))
        shutil.rmtree("calendar")
        shutil.rmtree("event-manifest")
        self.assertEqual(self.CE.regular(FakeDart([], per=10), CODES_T0, 5, DAY), 0, "달력을 못 읽으면 이어 받기만")
        self.assertEqual(self.manifests(), [])
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        self.assertEqual(self.CE.regular(FakeDart(ROWS_T0, per=10, override={1: [{"status": "020"}]}), CODES_T0, 5, DAY), 1,
                         "이어 받기가 끊기면 작업 실패로 드러냄(그날 기록은 따로 남김)")
        self.assertEqual(self.manifests(), [f"{DAY}-local-0.json"])

    def test_main_dispatch(self):
        got = []
        with mock.patch.object(self.CE, "Official", lambda: "가짜"), mock.patch.object(self.CE, "codes_to_collect", lambda: CODES_T0), \
                mock.patch.object(self.CE, "final_check", lambda prov, codes, today, t0=None: got.append((prov, today, t0)) or 0), \
                mock.patch.object(self.CE, "kst_today", lambda: DAY), mock.patch.object(self.CE, "verify_run", lambda: 7):
            self.assertEqual(self.CE.main(["verify"]), 7)
            self.assertEqual(self.CE.main(["final"]), 0)
            self.assertEqual(self.CE.main(["final", "auto"]), 0)
            self.assertEqual(self.CE.main(["final", P]), 0)
        self.assertEqual(got, [("가짜", DAY, None), ("가짜", DAY, None), ("가짜", DAY, P)])


# ───────────────────────── 2b단계: D3 바구니 문(HEAD의 아침 최종 확인 manifest · 트리 지문) ─────────────────────────

class EventGate(TmpCwd):
    DECIDED = datetime(2026, 11, 11, 15, 10, tzinfo=KST)

    def setUp(self):
        super().setUp()
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        arm()
        Path("gate-smoke").mkdir()
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        Path("event-data").mkdir()
        Path("event-data/000040.json").write_text(json.dumps({"code": "000040", "rows": [
            {"date": P, "kind": "무상증자", "title": "주요사항보고서(무상증자결정)"}]}, ensure_ascii=False), encoding="utf-8")
        Path("event-data/README.txt").write_text("json 아님 · 지문에 안 들어감", encoding="utf-8")

    @staticmethod
    def put(name=MANIFEST, **kw):
        Path(name).parent.mkdir(parents=True, exist_ok=True)
        Path(name).write_text(json.dumps(manifest_body("event-data", **kw), ensure_ascii=False), encoding="utf-8")

    def gate(self):
        import gates
        g = gates.begin(DAY, "engine", True, live_p=P)
        g.check_events(now=self.DECIDED)
        return g

    def assertBasketOnly(self, g, word):
        self.assertFalse(g.allows_new_risk("basket"))
        self.assertTrue(g.allows_new_risk("engine") and g.allows_new_risk("overlay"), "바구니만 닫음")
        why = " / ".join(g.reasons(("basket",)))
        self.assertIn("공시", why)
        self.assertIn(word, why)
        self.assertIn("사건 바구니", g.warn_line())
        self.assertNotIn("빈칸 엔진", g.warn_line())

    def test_tree_digest_definition(self):
        import event_manifest as M
        self.assertEqual(M.tree_digest("event-data"), tree_sha("event-data"))
        other = Path("elsewhere/deep/event-data")
        shutil.copytree("event-data", other)
        (other / "sub").mkdir()
        (other / "sub" / "x.json").write_text("{}", encoding="utf-8")         # 아래 폴더는 안 봄(바구니처럼 *.json만)
        self.assertEqual(M.tree_digest(other), M.tree_digest("event-data"), "폴더 자리와 무관 · 경로는 'event-data/<이름>'")
        empty = hashlib.sha256(b"[]").hexdigest()
        self.assertEqual(M.tree_digest("없는 폴더"), empty)
        Path("event-data/000040.json").write_text("{}", encoding="utf-8")
        self.assertNotEqual(M.tree_digest("event-data"), M.tree_digest(other), "내용이 바뀌면 지문이 바뀜")

    def test_committed_morning_manifest_opens(self):
        self.put()
        git_commit_all(self.root)
        g = self.gate()
        self.assertTrue(g.allows_new_risk("basket"), g.reasons())
        ev = g.snapshot("basket")["checks"]["events"]
        self.assertEqual((ev["id"], ev["ok"], ev["t0"], ev["D"], ev["head"]), (f"{P}-local-0.json", True, P, DAY, {"ok": True, "why": ""}))
        self.assertEqual(ev["tree"], ev["manifest_tree"])
        self.assertEqual(ev["decided_at_utc"], "2026-11-11T06:10:00Z")
        self.assertEqual(g.snapshot("engine")["checks"], {}, "점검 칸은 바구니에만")

    def test_closures_close_basket_only(self):
        cases = {
            "manifest 없음": (dict(manifest=False), "없음"),
            "19:20 정기만": (dict(mode="regular"), "19:20 정기 기록만"),
            "ok 거짓": (dict(ok=False, why="쪽 빠짐"), "ok 거짓"),
            "query_end ≠ t0": (dict(query_end=DAY), "질의 날"),
            "판단 뒤 완료": (dict(done="2026-11-11T06:10:00Z"), "판단 시각보다 늦음"),
            "다른 날 확인": (dict(day="20261110"), "다른 날"),
            "저장 안 됨": (dict(persisted=False), "persisted"),
            "트리 지문 다름": (dict(event_data_tree_digest="0" * 64), "트리 지문"),
            "깨진 manifest": (dict(broken=True), "읽을 수 있는"),
        }
        for name, (kw, word) in cases.items():
            with self.subTest(name):
                shutil.rmtree(".git", ignore_errors=True)
                shutil.rmtree("event-manifest", ignore_errors=True)
                kw = dict(kw)
                if kw.pop("broken", False):
                    Path("event-manifest").mkdir()
                    Path(MANIFEST).write_text("{", encoding="utf-8")
                elif kw.pop("manifest", True):
                    self.put(**kw)
                git_commit_all(self.root)
                self.assertBasketOnly(self.gate(), word)

    def test_head_checks(self):
        import event_manifest as M
        self.put()
        g = self.gate()                                                    # git 저장소가 아님
        self.assertBasketOnly(g, "git 저장소가 아니라")
        git_commit_all(self.root)
        self.assertTrue(self.gate().allows_new_risk("basket"))
        late = f"event-manifest/{P}-9-1.json"                              # 더 먼저 끝난(= 첫 성공) manifest인데 커밋 안 됨 → HEAD와 다름
        self.put(late, GITHUB_RUN_ID="9", GITHUB_RUN_ATTEMPT="1", done="2026-11-10T23:00:00Z")
        self.assertBasketOnly(self.gate(), "HEAD")
        Path(late).unlink()
        body = json.loads(Path("event-data/000040.json").read_text(encoding="utf-8"))
        body["rows"].append({"date": P, "kind": "자사주취득", "title": "커밋 뒤 끼어든 줄"})
        Path("event-data/000040.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        self.put()                                                        # manifest도 바뀐 자료에 맞춰 고쳤지만 둘 다 커밋 안 됨
        ok, why, info = M.morning_check(P, DAY, self.DECIDED)
        self.assertFalse(ok)
        self.assertIn("HEAD", why)
        self.assertEqual(info["tree"], info["manifest_tree"], "지문은 맞아도 HEAD 그대로가 아니면 닫힘")
        git_commit_all(self.root)
        self.assertTrue(self.gate().allows_new_risk("basket"), "같은 내용을 커밋하면 열림")

    def test_first_success_only(self):
        import event_manifest as M
        self.put()                                                         # 08:25 성공(첫 성공)
        self.put(f"event-manifest/{P}-8-1.json", GITHUB_RUN_ID="8", GITHUB_RUN_ATTEMPT="1", done="2026-11-11T01:25:00Z")
        git_commit_all(self.root)
        ok, why, info = M.morning_check(P, DAY, self.DECIDED)
        self.assertTrue(ok, why)
        self.assertEqual(info["id"], f"{P}-local-0.json", "먼저 끝난 첫 성공")
        self.assertEqual(len(info["candidates"]), 2)
        self.put(event_data_tree_digest="f" * 64)                          # 첫 성공의 지문이 지금 자료와 다르면 뒤 성공으로 바꾸지 않음
        git_commit_all(self.root)
        ok, why, info = M.morning_check(P, DAY, self.DECIDED)
        self.assertFalse(ok)
        self.assertEqual(info["id"], f"{P}-local-0.json")
        self.assertIn("트리 지문", why)

    def test_unknown_p_or_error_closes(self):
        import gates
        self.put()
        git_commit_all(self.root)
        g = gates.Gates(DAY, "engine")                                     # 달력 칸 없음 → P 모름
        g.check_events(now=self.DECIDED)
        self.assertFalse(g.allows_new_risk("basket"))
        self.assertTrue(g.allows_new_risk("engine"))
        with mock.patch("event_manifest.morning_check", side_effect=RuntimeError("말썽")):
            self.assertBasketOnly(self.gate(), "셈 오류")


class EngineEventsRun(unittest.TestCase):
    def test_morning_manifest_opens_basket(self):
        out = world_run("engine")
        self.assertIn("000040", [o[0] for o in buys(out)], "바구니 무상증자 매수(문 열림)")
        ev = audit_of(out, "basket")["곁"]["gates"]["checks"]["events"]
        self.assertEqual((ev["id"], ev["ok"], ev["head"]["ok"]), (f"{P}-local-0.json", True, True))
        self.assertEqual(gates_file(out)["checks"]["basket"]["events"]["id"], f"{P}-local-0.json")

    def test_no_or_bad_manifest_closes_basket_only(self):
        changed = {"event-data/000040.json": {"rows": [{"date": P, "kind": "무상증자", "title": "주요사항보고서(무상증자결정)"},
                                                       {"date": P, "kind": "무상증자", "title": "커밋 뒤 끼어든 줄"}]}}
        cases = {"manifest 없음": dict(manifest=None), "19:20 정기만": dict(manifest="regular"),
                 "ok 거짓": dict(manifest={"ok": False}), "판단 뒤 완료": dict(manifest={"done": "2026-11-11T06:11:00Z"}),
                 "커밋 뒤 자료 바뀜": dict(after_commit=changed), "git 아님": dict(git=False)}
        for name, kw in cases.items():
            with self.subTest(name):
                out = world_run("engine", **kw)
                g = gates_file(out)
                self.assertFalse(g["decisions"]["basket"]["open"], g["decisions"]["basket"])
                self.assertTrue(g["decisions"]["engine"]["open"] and g["decisions"]["overlay"]["open"], "엔진 · 덧붙임은 그대로")
                self.assertEqual(sorted(o[0] for o in buys(out)), ["122630", "133690", "148070"], "바구니 매수만 빠짐")
                self.assertIn(("000020", 200), sells(out), "바구니 20거래일 팔기는 그대로")
                warn = [r for rows in out["discord"] for r in rows if r.startswith("⚠️ 새 매수 막음")]
                self.assertEqual(len(warn), 1)
                self.assertIn("사건 바구니", warn[0])
                self.assertNotIn("빈칸 엔진", warn[0])
                self.assertFalse(audit_of(out, "basket")["곁"]["gates"]["open"])

    def test_audit_clean_when_basket_closed(self):
        if str(ROOT / "research") not in sys.path:
            sys.path.insert(0, str(ROOT / "research"))
        import boost_audit
        out = world_run("engine", manifest=None)
        for bot in ("engine", "basket", "overlay"):
            self.assertEqual(boost_audit.orders_check(bot, audit_of(out, bot)), [], bot)


# ───────────────────────── 2b단계: D5 달력 만드는 도구(1차 KRX · 2차 KIS) ─────────────────────────

# data.krx.co.kr 휴장일 조회(B125.bld)가 2026-11-07에 준 값 그대로(고정 자료 · 시험은 인터넷을 안 부름)
KRX_2026 = ("20260101", "20260216", "20260217", "20260218", "20260302", "20260501", "20260505", "20260525", "20260603", "20260717",
            "20260817", "20260924", "20260925", "20261005", "20261009", "20261225", "20261231")
KRX_2027 = ("20270101", "20270208", "20270209", "20270301", "20270503", "20270505", "20270513", "20270719", "20270816", "20270914",
            "20270915", "20270916", "20271004", "20271011", "20271227", "20271231")


def build_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_calendar", ROOT / "tools" / "build_calendar.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def krx_raw(year, holidays):
    return json.dumps({"controller": "bldAttendant", "dir": "comm", "result": {"block1": [{"calnd_dd": d} for d in holidays]},
                       "cmd": "executeForResourceBundle"}, separators=(",", ":")).encode("utf-8")


# 2c단계 세션 원천 고정 자료(가짜 원문 · 시험은 인터넷을 안 부름): 평소 정규장 안내 · 수능날 공지 · 새해 첫 거래일 공지
REGULAR_RAW = ("<html><table><caption>매매거래시간 및 호가접수시간(시험 고정 자료)</caption><thead><tr><th colspan='2'>구분</th>"
               "<th>매매거래시간</th><th>호가접수시간</th></tr></thead><tbody><tr><th colspan='2'>정규장</th><td>09:00 ~ 15:30</td>"
               "<td>08:30 ~ 15:30</td></tr></tbody></table></html>").encode("utf-8")
SUNEUNG_URL = "https://www.krx.co.kr/2026_suneung_ko.pdf"
SUNEUNG_RAW = "%PDF-1.4 2026학년도 수능일 증권 · 파생상품시장 개장 10:00 · 마감 16:30 (시험 고정 자료)".encode("utf-8")
NEWYEAR_URL = "https://www.krx.co.kr/2027_opening_ko.pdf"
NEWYEAR_RAW = "%PDF-1.4 2027년 개장일 10:00 개장 (시험 고정 자료)".encode("utf-8")


class FakeGet:
    """가짜 KRX(requests.get 자리): 휴장일 조회(물음 칸 있음)는 해마다 원문 · 상태 · 예외 ·
    2c단계 세션 원천(물음 칸 없음)은 pages{주소: 원문 또는 예외} — 없는 주소는 HTTP 404 · 기본 pages = 평소 정규장 안내만."""

    def __init__(self, by_year, status=200, boom=None, pages=None, moved=()):
        self.by_year, self.status, self.boom, self.calls = dict(by_year), status, boom, []
        self.pages = {REGULAR_URL: REGULAR_RAW} if pages is None else dict(pages)
        self.moved = set(moved)                             # 이 주소는 공식 주소 밖으로 옮겨 간 응답(redirect 흉내)

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params or {}), dict(headers or {})))
        if params is None:                                  # 세션 원천(공식 안내 · 공지 원문)
            got = self.pages.get(url)
            if isinstance(got, Exception):
                raise got
            final = "https://login.example.net/moved" if url in self.moved else url
            return type("R", (), {"status_code": 200 if got is not None else 404, "content": got or b"", "url": final})()
        if self.boom:
            raise self.boom
        return type("R", (), {"status_code": self.status, "content": self.by_year[int(params["search_bas_yy"])]})()


def overlay_body(year, regular=True, special=(), unknown=None, **kw):
    """세션 overlay(calendar/sessions-<해>.json) — 평소 세션 영수증은 REGULAR_RAW 지문 · special은 [날, 주소, 원문, 개장, 마감]."""
    body = {"kind": "krx-session-overlay", "year": str(year)}
    if regular is True:
        body["regular"] = regular_receipt(year, sha=hashlib.sha256(REGULAR_RAW).hexdigest())
    elif regular:
        body["regular"] = regular
    body["special"] = [{"date": d, "source_url": url, "notice_no": f"시험공지-{d}", "effective_from": d,
                        "raw_sha256": raw if isinstance(raw, str) else hashlib.sha256(raw).hexdigest(), "open": o, "close": c}
                       for d, url, raw, o, c in special]
    if unknown is not None:
        body["unknown"] = list(unknown)
    body.update(kw)
    return body


def write_overlay(year, folder="calendar", **kw):
    p = Path(folder) / f"sessions-{year}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(overlay_body(year, **kw), ensure_ascii=False), encoding="utf-8")
    return p


class FakeKis:
    """가짜 KIS 국내휴장일조회(_market_rows 자리): BASS_DT부터 per일 치(달력 날)를 줌 · opnd_yn은 holidays로 · 바꿀 날 · 끊길 날."""

    def __init__(self, holidays, per=20, flip=(), stop_after=None, boom=None, bad=None):
        self.off, self.per, self.flip, self.stop_after, self.boom, self.bad = set(holidays), per, set(flip), stop_after, boom, bad
        self.calls = []

    def _market_rows(self, path, tr_id, params, what, key=None):
        self.calls.append(dict(params))
        assert (path, tr_id, key) == ("/uapi/domestic-stock/v1/quotations/chk-holiday", "CTCA0903R", "output")
        assert set(params) == {"BASS_DT", "CTX_AREA_NK", "CTX_AREA_FK"}
        if self.boom:
            raise self.boom
        d = date(int(params["BASS_DT"][:4]), int(params["BASS_DT"][4:6]), int(params["BASS_DT"][6:]))
        rows = []
        for _ in range(self.per):
            k = d.strftime("%Y%m%d")
            if self.stop_after and k > self.stop_after:
                break
            trade = d.weekday() < 5 and k not in self.off
            if k in self.flip:
                trade = not trade
            rows.append({"bass_dt": k, "wday_dvsn_cd": f"{(d.weekday() + 1) % 7 + 1:02d}", "bzdy_yn": "Y" if trade else "N",
                         "tr_day_yn": "Y" if trade else "N", "opnd_yn": self.bad if self.bad and k == params["BASS_DT"] else
                         ("Y" if trade else "N"), "sttl_day_yn": "Y" if trade else "N"})
            d += timedelta(days=1)
        return rows


class CalendarToolCwd(TmpCwd):
    """달력 도구 시험 도움(시험 없음): 쉬지 않는 KIS · 평소 세션 overlay · 도구 실행 · 판 파일 목록."""

    def setUp(self):
        super().setUp()
        self.B = build_tool()
        self.keep = mock.patch.object(self.B, "KIS_PAUSE", 0)
        self.keep.start()
        write_overlay(2026)                                # 2c단계: 평소 세션 영수증(공식 안내 원문 지문)이 있어야 판을 씀
        write_overlay(2027)

    def tearDown(self):
        self.keep.stop()
        super().tearDown()

    def run_tool(self, years, krx=None, kis=None, get=None):
        get = get or FakeGet({2026: krx_raw(2026, KRX_2026), 2027: krx_raw(2027, KRX_2027)})
        kis = kis or FakeKis(KRX_2026 + KRX_2027)
        return self.B.main([str(y) for y in years], client=kis, get=get, folder="calendar")

    def files(self):
        return sorted(p.name for p in Path("calendar").glob("krx-*.json")) if Path("calendar").exists() else []


class CalendarBuild(CalendarToolCwd):
    def test_same_sources_write_v1_in_trade_calendar_shape(self):
        import trade_calendar as C
        kis = FakeKis(KRX_2026, per=20)
        get = FakeGet({2026: krx_raw(2026, KRX_2026)})
        self.assertEqual(self.run_tool([2026], kis=kis, get=get), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json"])
        body = json.loads(Path("calendar/krx-2026-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(body["days"], calendar_body(2026, holidays=KRX_2026, unknown=("20260102", "20261119"))["days"],
                         "1단계 합성 판과 같은 꼴 · 같은 날들(2c단계: 새해 첫 거래일 · 수능날은 세션 원천이 없어 unknown)")
        got = C.load_year("2026", "calendar")
        self.assertEqual((got["version"], got["sha256"]), (1, C.normalized_digest(body["days"], body["sessions"])))
        self.assertEqual(body["raw_sha256"], hashlib.sha256(krx_raw(2026, KRX_2026)).hexdigest(), "원문 지문 = KRX 응답 바이트")
        self.assertIn(body["raw_sha256"][:16], body["notice_no"])
        self.assertIn("key=B125.bld", body["source_url"])
        self.assertIn("search_bas_yy=2026", body["source_url"])
        self.assertTrue(body["source_url"].startswith("https://data.krx.co.kr/comm/bldAttendant/executeForResourceBundle.cmd"))
        self.assertRegex(body["fetched_at_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertRegex(body["effective_from"], r"^\d{8}$")
        self.assertEqual(body["parser_version"], "build_calendar 3")
        self.assertEqual((body["secondary"]["tr_id"], body["secondary"]["field"], body["secondary"]["agree_days"]), ("CTCA0903R", "opnd_yn", 365))
        self.assertEqual(body["secondary"]["calls"], len(kis.calls))
        self.assertEqual(len(kis.calls), 19, "기준일자를 받은 마지막 날 다음 날로 옮기며 그해를 다 덮음(20일씩 → 19번)")
        self.assertEqual([c["BASS_DT"] for c in kis.calls[:3]], ["20260101", "20260121", "20260210"])
        self.assertEqual(get.calls[0][1], {"baseName": "krx.mdc.i18n.component", "key": "B125.bld", "search_bas_yy": "2026"})
        self.assertEqual(body["days"]["20261119"], {"session": "unknown"},
                         "수능날: 봇 특수 세션 목록에 있는데 공식 overlay가 없어 unknown(09:00 ~ 15:30을 지어내지 않음 · GPT §2-B)")
        reg = body["sessions"]["regular"]
        self.assertEqual((reg["source_url"], reg["raw_sha256"], reg["open"], reg["close"]),
                         (REGULAR_URL, hashlib.sha256(REGULAR_RAW).hexdigest(), "0900", "1530"), "평소 세션 = 공식 원천 영수증(받은 원문 지문)")
        self.assertRegex(reg["fetched_at_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(body["sessions"]["special"], [])
        self.assertEqual({u["date"] for u in body["sessions"]["unknown"]}, {"20260102", "20261119"})
        info = C.day_info(DAY, folder="calendar")
        self.assertEqual((info["P"], info["trading"]), (P, True))
        self.assertEqual(self.B.check("calendar"), 0)

    def test_mismatch_or_fetch_failure_writes_nothing(self):
        cases = {
            "두 원천 다름(KIS가 성탄절을 개장일로)": dict(kis=FakeKis(KRX_2026, flip=("20261225",))),
            "두 원천 다름(KRX가 한 날을 빠뜨림)": dict(get=FakeGet({2026: krx_raw(2026, KRX_2026[:-1])})),
            "KRX 연결 오류": dict(get=FakeGet({}, boom=ConnectionError("끊김"))),
            "KRX HTTP 500": dict(get=FakeGet({2026: b""}, status=500)),
            "KRX가 로그인 화면(HTML)": dict(get=FakeGet({2026: "<html>로그인</html>".encode("utf-8")})),
            "KRX 휴장일 0개": dict(get=FakeGet({2026: krx_raw(2026, ())})),
            "KRX에 다른 해 날짜": dict(get=FakeGet({2026: krx_raw(2026, KRX_2026 + ("20270101",))})),
            "KIS 연결 오류": dict(kis=FakeKis(KRX_2026, boom=RuntimeError("거절"))),
            "KIS가 그해를 다 안 줌": dict(kis=FakeKis(KRX_2026, stop_after="20261130")),
            "KIS 칸 이상": dict(kis=FakeKis(KRX_2026, bad="?")),
        }
        for name, kw in cases.items():
            with self.subTest(name):
                shutil.rmtree("calendar", ignore_errors=True)
                kw.setdefault("get", FakeGet({2026: krx_raw(2026, KRX_2026)}))
                kw.setdefault("kis", FakeKis(KRX_2026))
                self.assertEqual(self.run_tool([2026], **kw), 1, name)
                self.assertEqual(self.files(), [], "아무 판도 안 씀")
                said = " ".join(" ".join(str(a) for a in c.args) for c in __import__("builtins").print.call_args_list[-2:])
                self.assertIn("2026년 달력 판을 쓰지 않음", said)
        said = " ".join(" ".join(str(a) for a in c.args) for c in __import__("builtins").print.call_args_list)
        self.assertIn("20261225 KRX 휴장 / KIS 거래", said, "다른 날을 까닭에 적음")

    def test_rerun_same_content_and_changed_notice(self):
        import trade_calendar as C
        self.assertEqual(self.run_tool([2026]), 0)
        v1 = Path("calendar/krx-2026-v1.json").read_bytes()
        self.assertEqual(self.run_tool([2026]), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json"], "같은 내용이면 새 판 없음")
        said = " ".join(str(c.args[0]) for c in __import__("builtins").print.call_args_list if c.args)
        self.assertIn("새 판 없음", said)
        extra = KRX_2026 + ("20261120",)                                 # 임시 휴장 공지 → 두 원천 모두 바뀜
        self.assertEqual(self.run_tool([2026], get=FakeGet({2026: krx_raw(2026, extra)}), kis=FakeKis(extra)), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json", "krx-2026-v2.json"])
        self.assertEqual(Path("calendar/krx-2026-v1.json").read_bytes(), v1, "옛 판은 덮지 않음")
        self.assertEqual(C.load_year("2026", "calendar")["version"], 2)
        self.assertEqual(C.day_info("20261123", folder="calendar")["P"], "20261119", "새 판(11-20 휴장)으로 앞 거래일이 바뀜")
        Path("calendar/krx-2026-v2.json").write_text("{", encoding="utf-8")       # 가장 큰 판이 깨지면 확인 실패
        self.assertEqual(self.B.check("calendar"), 1)

    def test_year_boundary(self):
        import idle_live
        import trade_calendar as C
        self.assertEqual(self.run_tool([2026, 2027]), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json", "krx-2027-v1.json"])
        info = C.day_info("20270104", folder="calendar")
        self.assertEqual((info["P"], info["version"], info["p_version"]), ("20261230", 1, 1))
        self.assertEqual(C.next_day("20261230", folder="calendar"), "20270104")
        with mock.patch.object(C, "FOLDER", Path("calendar")):
            self.assertEqual(idle_live.next_trading_day("20261230"), "20270104")
            self.assertEqual(idle_live.next_trading_day("20270430"), "20270504", "KRX 2027-05-03 휴장(HOLIDAYS에 없음)은 달력이 이김")

    def test_years_args_and_client(self):
        self.assertEqual(self.B.default_years(datetime(2026, 11, 7, tzinfo=KST)), [2026])
        self.assertEqual(self.B.default_years(datetime(2026, 12, 1, tzinfo=KST)), [2026, 2027])
        self.assertEqual(self.B.main(["20x6"], client=FakeKis(KRX_2026), get=FakeGet({}), folder="calendar"), 1)
        with mock.patch.dict(os.environ, {"CAL_YEARS": "2026"}):
            self.assertEqual(self.B.main([], client=FakeKis(KRX_2026), get=FakeGet({2026: krx_raw(2026, KRX_2026)}), folder="calendar"), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json"])
        import broker_kis
        with mock.patch.object(broker_kis, "market", side_effect=broker_kis.BrokerError("키 없음")):
            self.assertEqual(self.B.main(["2026"], get=FakeGet({}), folder="calendar"), 1, "증권사 연결을 못 만들면 쓰지 않음")


# ───────────────────────── 2b단계: 빈칸 엔진 '주 끝' — 달력이 있으면 달력 · 없으면 HOLIDAYS ─────────────────────────

class EngineWeekEnd(TmpCwd):
    def table(self, days):
        import idle_live
        return {d: (idle_live.next_trading_day(d), idle_live.week_end(d)) for d in days}

    def test_same_as_holidays_then_calendar_wins(self):
        import idle_live
        days = [d.strftime("%Y%m%d") for d in (date(2026, 10, 1) + timedelta(days=k) for k in range(450))
                if d.weekday() < 5 and d.year <= 2027]
        before = self.table(days)                                         # 달력 없음 = 예전 HOLIDAYS 그대로
        self.assertEqual(before["20261224"], ("20261228", True))
        self.assertEqual(before["20270430"], ("20270503", True))
        h26 = tuple(sorted(h for h in idle_live.HOLIDAYS if h.startswith("2026")))
        h27 = tuple(sorted(h for h in idle_live.HOLIDAYS if h.startswith("2027")))
        write_calendar("calendar", 2026, holidays=h26)
        write_calendar("calendar", 2027, holidays=h27)
        self.assertEqual(self.table(days), before, "달력이 HOLIDAYS와 같은 날들이면 결과가 하나도 안 바뀜")
        write_calendar("calendar", 2027, version=2, holidays=KRX_2027)     # KRX 2027(05-03 · 07-19 더 있음)
        after = self.table(days)
        self.assertEqual(after["20270430"], ("20270504", True), "달력이 이김")
        self.assertEqual({d: v[1] for d, v in after.items()}, {d: v[1] for d, v in before.items()}, "주 끝 판단은 이 해에도 같음(월요일 휴장)")
        write_calendar("calendar", 2027, version=3, sha="f" * 64)          # 다음 해 판이 깨짐 → 그 구간은 HOLIDAYS로
        self.assertEqual(idle_live.next_trading_day("20261230"), "20270104")
        self.assertEqual(idle_live.next_trading_day("20261009"), "20261012", "2026 판은 그대로 씀")


# ───────────────────────── 2b단계: 시작 전 점검 파일 이름(작업마다) · git pull --rebase 실험 ─────────────────────────

class SmokeRunName(TmpCwd):
    def test_names_and_two_runs_same_day(self):
        import gate_smoke
        self.assertEqual(gate_smoke.path_for(DAY).as_posix(), SMOKE)
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2"}):
            self.assertEqual(gate_smoke.path_for(DAY).as_posix(), f"gate-smoke/{DAY}-123-2.json")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "../x", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertEqual(gate_smoke.path_for(DAY).as_posix(), f"gate-smoke/{DAY}-local-1.json", "이상한 값은 이름에 안 씀")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "1"}):
            gate_smoke.main([DAY])                                       # 앞 작업: 달력 없음 → 실패 파일
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "2", "GITHUB_RUN_ATTEMPT": "1"}):
            gate_smoke.main([DAY])                                       # 뒤 작업: 통과 파일(앞 파일을 덮지 않음)
            self.assertTrue(gate_smoke.status(DAY)[0])
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertFalse(gate_smoke.status(DAY)[0], "앞 작업은 자기 실패 파일을 그대로 봄")
        self.assertEqual(sorted(os.listdir("gate-smoke")), [f"{DAY}-1-1.json", f"{DAY}-2-1.json"])
        Path(f"gate-smoke/{DAY}-5-2.json").write_text(json.dumps({"date": DAY, "ok": True, "run_id": "5", "run_attempt": "1"}),
                                                      encoding="utf-8")
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "5", "GITHUB_RUN_ATTEMPT": "2"}):
            self.assertIn("이 작업의 것이 아님", gate_smoke.status(DAY)[1], "본문의 시도 번호가 다름")

    def test_manifest_binding_smoke_catches_broken_verifier(self):
        import event_manifest
        import gate_smoke
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        self.assertTrue(gate_smoke.check(DAY)["ok"], gate_smoke.check(DAY)["reasons"])
        with mock.patch.object(event_manifest, "morning_check", lambda *a, **k: (True, "", {})):    # 무엇이든 통과시키는 고장
            body = gate_smoke.check(DAY)
        self.assertFalse(body["ok"])
        self.assertTrue(any("19:20 정기만 manifest를 통과시킴" in r for r in body["reasons"]), body["reasons"])
        with mock.patch.object(event_manifest, "morning_check", lambda *a, **k: (False, "고장", {})):  # 무엇이든 막는 고장
            self.assertIn("맞는 아침 확인 manifest를 거부함", gate_smoke.check(DAY)["reasons"])

    def test_untracked_new_file_does_not_block_pull_rebase(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_AUTHOR_NAME="시험", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="시험",
                   GIT_COMMITTER_EMAIL="t@example.invalid")

        def git(cwd, *args):
            return subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args], cwd=cwd, env=env,
                                  capture_output=True, text=True, timeout=60)
        git(".", "init", "-q", "--bare", "remote.git")
        git(".", "-c", "init.defaultBranch=main", "clone", "-q", "remote.git", "a")
        Path("a/gate-smoke").mkdir()
        Path(f"a/gate-smoke/{DAY}-1-1.json").write_text("{}", encoding="utf-8")
        Path("a/idle-live").mkdir()
        Path("a/idle-live/state.json").write_text("{}", encoding="utf-8")
        git("a", "checkout", "-q", "-b", "main")
        git("a", "add", "-A")
        git("a", "commit", "-q", "-m", "바탕")
        git("a", "push", "-q", "origin", "main")
        git(".", "clone", "-q", "-b", "main", "remote.git", "b")
        Path("a/idle-live/state.json").write_text('{"x": 1}', encoding="utf-8")       # 다른 작업이 15:10 전에 올린 커밋
        git("a", "commit", "-qam", "다른 작업")
        git("a", "push", "-q", "origin", "main")
        Path(f"b/gate-smoke/{DAY}-2-1.json").write_text('{"ok": true}', encoding="utf-8")    # 이 작업의 새 점검 파일(추적 밖)
        got = git("b", "pull", "-q", "--rebase", "origin", "main")
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(json.loads(Path("b/idle-live/state.json").read_text(encoding="utf-8")), {"x": 1})
        Path(f"b/gate-smoke/{DAY}-1-1.json").write_text('{"다시 씀": 1}', encoding="utf-8")   # 대조: 예전 방식(같은 이름 추적 파일을 고침)
        Path("a/idle-live/state.json").write_text('{"x": 2}', encoding="utf-8")
        git("a", "commit", "-qam", "또 다른 작업")
        git("a", "push", "-q", "origin", "main")
        self.assertNotEqual(git("b", "pull", "-q", "--rebase", "origin", "main").returncode, 0, "추적 파일을 고치면 실패(예전 로컬 커밋이 필요했던 까닭)")


# ───────────────────────── 2b단계: D4 보강 — 수급 수집 목록에 1일봉 풀 ─────────────────────────

class InvestorPool(TmpCwd):
    def setUp(self):
        super().setUp()
        import collect_investor_history as C
        self.C = C
        Path("study").mkdir()
        Path("study/flow_universe.json").write_text(json.dumps({"codes": ["000001", "000002"]}), encoding="utf-8")
        Path("daily-live").mkdir()
        Path("daily-live/state.json").write_text(json.dumps({"positions": {"000009": {"code": "000009"}}}), encoding="utf-8")
        last5 = weekdays_until(P, 5)
        self.prices = {f"{i:06d}": {"name": f"종목{i}", "rows": [(d, 100.0) for d in last5]} for i in range(1, 6)}
        self.prices["000006"] = {"name": "낡음", "rows": [(d, 100.0) for d in weekdays_until(weekdays_until(P, 2)[0], 5)]}
        import caps
        import study
        self.patches = [mock.patch.object(study, "load_prices", lambda *a, **k: copy.deepcopy(self.prices)),
                        mock.patch.object(caps, "tag", lambda rows, top=100: [r.update({caps.RANK: i + 1}) for i, r in enumerate(rows)])]
        for x in self.patches:
            x.start()

    def tearDown(self):
        for x in self.patches:
            x.stop()
        super().tearDown()

    def test_pool_added_only_for_daily_default_set(self):
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        with mock.patch.object(self.C, "target_day", lambda now=None, folder=None: (P, True)):
            self.assertEqual(self.C.daily_pool(), ["000001", "000002", "000003", "000004", "000005", "000009"],
                             "전날(P) 일봉이 있는 종목의 150위 + 보유 · P 일봉이 없는 종목은 빠짐(1일봉 풀과 같은 식)")
            self.assertEqual(self.C.codes_to_collect(), ["000001", "000002", "000003", "000004", "000005", "000009"], "목록 + 풀(겹침 없음)")
            with mock.patch.dict(os.environ, {"INVESTOR_CODES": "000001"}):
                self.assertEqual(self.C.codes_to_collect(), ["000001"], "묶음 수집은 그대로")
            with mock.patch.object(self.C, "FULL", True):
                self.assertEqual(self.C.codes_to_collect(), ["000001", "000002"], "전체 칸 수집은 그대로")
        with mock.patch.object(self.C, "target_day", side_effect=RuntimeError("말썽")):
            self.assertEqual(self.C.codes_to_collect(), ["000001", "000002"], "풀 셈이 말썽이면 예전 목록대로(수집은 멈추지 않음)")

    def test_pool_size_150(self):
        import caps
        self.prices = {f"{i:06d}": {"name": str(i), "rows": [(d, 100.0) for d in weekdays_until(P, 5)]} for i in range(1, 201)}
        Path("daily-live/state.json").write_text(json.dumps({"positions": {"000300": {}}}), encoding="utf-8")
        with mock.patch.object(self.C, "target_day", lambda now=None, folder=None: (P, True)), \
                mock.patch.object(caps, "tag", lambda rows, top=100: [r.update({caps.RANK: i + 1}) for i, r in enumerate(
                    sorted(rows, key=lambda r: r["code"]))]):
            pool = self.C.daily_pool()
        self.assertEqual(len(pool), 151, "150위 + 보유 1")
        self.assertEqual((pool[0], pool[149], pool[150]), ("000001", "000150", "000300"))
        self.assertNotIn("000151", pool)


class Structure2b(unittest.TestCase):
    def test_engine_checks_events_before_basket(self):
        text = (ROOT / "idle_live.py").read_text(encoding="utf-8")
        run = text[text.index("def run(now=None):"):]
        marks = ['gate = gates.begin(day, "engine", sync_ok', "gate.check_etf(etf_last_days(day))", "gate.check_events()",
                 'if not gate.allows_new_risk("basket"):', "basket_live.run("]
        at = [run.index(m) for m in marks]
        self.assertEqual(at, sorted(at), "D3 공시 확인은 바구니를 부르기 전")

    def test_events_workflow(self):
        wf = (ROOT / ".github" / "workflows" / "events.yml").read_text(encoding="utf-8")
        for cron in ("'20 23 * * 0-4'", "'20 1 * * 1-5'", "'20 3 * * 1-5'", "'20 10 * * 1-5'", "'30 3 * * 6'"):
            self.assertIn(f"cron: {cron}", wf)
        self.assertIn('python collect_events.py final "$EVENT_T0"', wf)
        save = wf[wf.index("- name: 자료 · manifest"):]
        self.assertIn("if: always()", save)
        self.assertIn("set -euo pipefail", save)
        self.assertNotIn("|| true", save)
        self.assertNotIn("2>/dev/null", save)
        marks = ["mkdir -p event-data event-manifest", "python collect_events.py verify", "git add -A -- event-data", 'git add -- "$m"',
                 "git commit -q -m"]
        at = [save.index(m) for m in marks]
        self.assertEqual(at, sorted(at), "각각 확인 → 따로 staging → 같은 한 커밋")
        self.assertEqual(save.count("git commit"), 1)
        self.assertIn('event-manifest/*-"$GITHUB_RUN_ID"-"$GITHUB_RUN_ATTEMPT".json', save, "이 작업의 manifest만")

    def test_calendar_workflow(self):
        wf = (ROOT / ".github" / "workflows" / "calendar.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", wf)
        self.assertRegex(wf, r"cron: '\d+ \d+ 1 \* \*'", "매월 1회")
        self.assertIn("python tools/build_calendar.py", wf)
        self.assertIn("KIS_APP_KEY: ${{ secrets.KIS_APP_KEY }}", wf)
        self.assertIn("KIS_APP_SECRET: ${{ secrets.KIS_APP_SECRET }}", wf)
        self.assertEqual([x.strip() for x in wf.splitlines() if "git add" in x and not x.strip().startswith("#")], ["git add -- calendar"])
        self.assertLess(wf.index("python tools/build_calendar.py --check"), wf.index("git add -- calendar"))
        self.assertNotIn("|| true", wf)


# ───────────────────────── 2c단계 A: D3 확인 범위 = 바구니 입력 창(GPT 구현 검토 6705430244 §2-A) ─────────────────────────

FRI, SAT, SUN, MON, TUE = "20261113", "20261114", "20261115", "20261116", "20261117"


class EventWindow(EventCwd):
    """확인 범위(event_manifest.query_window)가 바구니 todays_events 창(앞 거래일 < 접수일 ≤ t0)과 같음 · 토요일 접수 반례."""

    DECIDED = datetime(2026, 11, 17, 15, 10, tzinfo=KST)               # 화요일 15:10(t0 = 월요일)

    def setUp(self):
        super().setUp()
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        write_calendar("calendar", 2027, holidays=KRX_2027)
        arm()
        Path("gate-smoke").mkdir(exist_ok=True)
        Path(f"gate-smoke/{TUE}-local-0.json").write_text(json.dumps({"date": TUE, "ok": True}), encoding="utf-8")

    def gate(self):
        import gates
        g = gates.begin(TUE, "engine", True, live_p=MON)
        g.check_events(now=self.DECIDED)
        return g

    def test_window_equals_basket_todays_events(self):
        import basket_live as B
        import event_manifest as M
        import trade_calendar as C
        trading = sorted(k for y in ("2026", "2027") for k, v in C.load_year(y, "calendar")["days"].items() if v is not None)
        seen, d = 0, date(2026, 1, 6)
        while d <= date(2027, 3, 31):
            D = d.strftime("%Y%m%d")
            d += timedelta(days=1)
            info = C.day_info(D, folder="calendar")
            if not info or not info["trading"]:
                continue
            t0 = info["P"]
            win = M.query_window(t0, "calendar")
            days = [k for k in trading if k < D] + [D]                     # 바구니의 days(etf-data 거래일 + 오늘)와 같은 꼴
            before = days[days.index(t0) - 1]                              # basket_live.run이 쓰는 before
            self.assertEqual((win["begin"], win["end"], win["before"]), (M.day_after(before), t0, before), D)
            lo = date(int(before[:4]), int(before[4:6]), int(before[6:])) - timedelta(days=6)
            span = [(lo + timedelta(days=k)).strftime("%Y%m%d") for k in range(16)]
            events = {x: [(x, "무상증자"), (x, "공급계약")] for x in span}      # 코드 자리에 날을 넣어 어느 날이 들어갔는지 봄
            got = {c for c, _ in B.todays_events(events, t0, before)}
            want = {x for x in span if win["begin"] <= x <= win["end"]}
            self.assertEqual(got, want, f"{D}: 바구니 창(before < 접수일 ≤ t0) = 확인 범위")
            self.assertEqual(want, {x for x in span if before < x <= t0})
            seen += 1
        self.assertGreater(seen, 280)
        cases = {TUE: (SAT, MON), DAY: (P, P), "20261007": ("20261003", "20261006"), "20270105": ("20261231", "20270104")}
        for D, (b, e) in cases.items():
            t0 = C.day_info(D, folder="calendar")["P"]
            got = M.query_window(t0, "calendar")
            self.assertEqual((got["begin"], got["end"]), (b, e), f"{D}: 금요일 다음 월요일 t0 = 토 ~ 월 · 휴일 · 해 넘김")
        self.assertIsNone(M.query_window(SAT, "calendar"), "t0가 휴장이면 범위 없음")
        self.assertIsNone(M.query_window("20251230", "calendar"), "판에 없는 날")
        self.assertIsNone(M.query_window(None, "calendar"))

    def test_saturday_filing_in_manifest_opens_removed_closes(self):
        """토요일 접수 1건이 월요일 t0 바구니 신호에 들어감 → manifest에 있으면 문 열림 · manifest에서 빼면 닫힘."""
        import basket_live as B
        import event_manifest as M
        rows = [drow("000040", "주요사항보고서(무상증자결정)", day=SAT, no=1), drow("000020", "주요사항보고서(자기주식취득결정)", day=MON, no=2)]
        fake = FakeDart(rows, per=1)
        self.assertEqual(self.CE.final_check(fake, CODES_T0, TUE), 0)
        self.assertEqual({(c["bgn_de"], c["end_de"]) for c in fake.calls}, {(SAT, MON)}, "토 ~ 월을 한 범위로 끝 쪽까지 물음")
        path = Path(f"event-manifest/{MON}-local-0.json")
        body = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual((body["query_begin"], body["query_end"], body["window_before"], body["ok"]), (SAT, MON, FRI, True))
        self.assertIn(["000040", SAT, "무상증자", "주요사항보고서(무상증자결정)"], body["t0_events"])
        self.assertEqual(body["normalized_query_digest"], query_sha(SAT, MON), "질의 지문 = 범위 전체(따로 셈)")
        self.assertEqual(body["normalized_event_digest"], canon_sha(window_events("event-data", SAT, MON)), "사건 지문 = 범위 전체(따로 셈)")
        self.assertIn(("000040", "무상증자"), B.todays_events(B.load_events(), MON, FRI), "바구니가 읽는 t0 사건에 토요일 공시가 들어감")
        git_commit_all(self.root)
        g = self.gate()
        self.assertTrue(g.allows_new_risk("basket"), g.reasons())
        ev = g.snapshot("basket")["checks"]["events"]
        self.assertEqual((ev["window"], ev["window_before"], ev["events"]), ([SAT, MON], FRI, 2))
        self.assertEqual(ev["stored_event_digest"], body["normalized_event_digest"])
        # 반례: manifest에서 토요일 공시를 뺌(사건 목록 · 지문만 고침 · 자료 트리는 그대로) → 지금 자료의 범위 사건과 달라 닫힘
        cut = dict(body, t0_events=[e for e in body["t0_events"] if e[1] != SAT])
        cut["normalized_event_digest"] = cut["stored_event_digest"] = canon_sha(cut["t0_events"])
        path.write_text(json.dumps(cut, ensure_ascii=False), encoding="utf-8")
        git_commit_all(self.root)
        g = self.gate()
        self.assertFalse(g.allows_new_risk("basket"))
        self.assertTrue(g.allows_new_risk("engine") and g.allows_new_risk("overlay"), "바구니만 닫음")
        self.assertTrue(any("manifest에 없는 공시" in r for r in g.reasons(("basket",))), g.reasons(("basket",)))
        path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")         # 다시 넣으면 열림
        git_commit_all(self.root)
        self.assertTrue(self.gate().allows_new_risk("basket"))

    def test_t0_only_manifest_closes_and_final_check_requeries(self):
        """예전처럼 t0 하루(월)만 물은 성공 manifest → 범위가 달라 닫힘 · 아침 확인은 그것을 첫 성공으로 치지 않고 범위로 다시 물음."""
        import event_manifest as M
        rows = [drow("000040", "주요사항보고서(무상증자결정)", day=SAT, no=1), drow("000020", "주요사항보고서(자기주식취득결정)", day=MON, no=2)]
        old, _ = self.CE.collect_day(FakeDart(rows, per=1), CODES_T0, MON, "final", day=TUE, window={"begin": MON, "end": MON, "before": SUN})
        self.assertTrue(old["ok"], "t0 하루 범위로는 완결(그 범위 자체는 맞음)")
        git_commit_all(self.root)
        g = self.gate()
        self.assertFalse(g.allows_new_risk("basket"))
        self.assertTrue(any("질의 날" in r and f"{SAT} ~ {MON}" in r for r in g.reasons(("basket",))), g.reasons(("basket",)))
        win = M.query_window(MON, "calendar")
        self.assertIsNone(M.first_ok(MON, TUE, window=win), "범위가 다른 성공은 첫 성공이 아님")
        self.assertEqual(M.first_ok(MON, TUE), f"{MON}-local-0.json", "범위를 안 보면(예전) 건너뛰었을 것")
        again = FakeDart(rows, per=1)
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "2", "GITHUB_RUN_ATTEMPT": "1"}):
            self.assertEqual(self.CE.final_check(again, CODES_T0, TUE), 0)
        self.assertEqual({(c["bgn_de"], c["end_de"]) for c in again.calls}, {(SAT, MON)}, "범위로 다시 물음")
        git_commit_all(self.root)
        g = self.gate()
        self.assertTrue(g.allows_new_risk("basket"), g.reasons())
        self.assertEqual(g.snapshot("basket")["checks"]["events"]["id"], f"{MON}-2-1.json")

    def test_collect_range_pages_zero_and_out_of_range(self):
        win = {"begin": SAT, "end": MON, "before": FRI}
        rows = [drow("000040", "주요사항보고서(무상증자결정)", day=SAT, no=1), drow("000030", "현금ㆍ현물배당결정", day=SUN, no=2),
                drow("000020", "주요사항보고서(자기주식취득결정)", day=MON, no=3)]
        zero, _ = self.CE.collect_day(FakeDart([]), CODES_T0, MON, "final", day=TUE, window=win)
        self.assertEqual((zero["ok"], zero["status"], zero["total_count"], zero["query_begin"]), (True, "013", 0, SAT), "범위 0건(013) = 정상")
        body, _ = self.CE.collect_day(FakeDart(rows, per=1), CODES_T0, MON, "final", day=TUE, window=win)
        self.assertEqual((body["ok"], body["total_page"], body["pages_received"], body["events"]), (True, 3, 3, 3),
                         "범위 안 토 · 일 · 월 접수는 정상(다른 날 줄 아님) · 쪽 넘김 끝까지")
        self.assertEqual(sorted({e[1] for e in body["t0_events"]}), [SAT, SUN, MON])
        out_row = rows + [drow("000030", "현금ㆍ현물배당결정", day=FRI, no=9)]
        before = self.data_bytes()
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "8", "GITHUB_RUN_ATTEMPT": "1"}):
            bad, _ = self.CE.collect_day(FakeDart(out_row, per=10, dates=False), CODES_T0, MON, "final", day=TUE, window=win)
        self.assertFalse(bad["ok"])
        self.assertIn(f"확인 범위 {SAT} ~ {MON} 밖의 다른 접수일 줄 1개", bad["why"], "범위 밖 날만 금지")
        self.assertEqual(self.data_bytes(), before, "범위 밖 줄이 섞이면 저장하지 않음")
        cut, _ = self.CE.collect_day(FakeDart(rows, per=1, override={2: [{"status": "013"}]}), CODES_T0, MON, "final", day=TUE, window=win)
        self.assertFalse(cut["ok"])
        self.assertIn("일찍 끊김", cut["why"])
        none, _ = self.CE.collect_day(FakeDart(rows), CODES_T0, SAT, "final", day=TUE)
        self.assertFalse(none["ok"])
        self.assertIn("확인 범위", none["why"], "달력으로 범위를 못 정하면(휴장 t0) 실패 manifest")

    def test_regular_record_uses_next_day_basket_window(self):
        fake = FakeDart([drow("000040", "주요사항보고서(무상증자결정)", day=SAT, no=1)], per=10)
        self.assertEqual(self.CE.regular(fake, CODES_T0, 5, MON), 0)
        self.assertEqual([(c["bgn_de"], c["end_de"]) for c in fake.calls], [("20261111", MON), (SAT, MON)], "이어 받기 + 다음 날 바구니 창")
        body = json.loads(Path(f"event-manifest/{MON}-local-0.json").read_text(encoding="utf-8"))
        self.assertEqual((body["mode"], body["query_begin"], body["query_end"], body["ok"]), ("regular", SAT, MON, True))

    def test_gate_checks_exact_range_and_query_digest(self):
        Path("event-data/000040.json").write_text(json.dumps({"code": "000040", "rows": [
            {"date": SAT, "kind": "무상증자", "title": "주요사항보고서(무상증자결정)"}]}, ensure_ascii=False), encoding="utf-8")

        def put(**kw):
            shutil.rmtree("event-manifest", ignore_errors=True)
            Path("event-manifest").mkdir()
            kw.setdefault("begin", SAT)
            Path(f"event-manifest/{MON}-local-0.json").write_text(json.dumps(
                manifest_body("event-data", t0=MON, day=TUE, done="2026-11-16T23:25:00Z", **kw), ensure_ascii=False),
                encoding="utf-8")
            git_commit_all(self.root)
            return self.gate()
        self.assertTrue(put().allows_new_risk("basket"))
        for name, kw, word in (("범위가 하루 넓음", dict(begin=FRI), "질의 날"), ("범위가 t0 하루", dict(begin=MON), "질의 날"),
                               ("질의 끝이 다름", dict(query_end=TUE), "질의 날"),
                               ("질의 지문이 t0 하루 것", dict(normalized_query_digest=query_sha(MON, MON)), "질의 지문")):
            with self.subTest(name):
                g = put(**kw)
                self.assertFalse(g.allows_new_risk("basket"))
                self.assertTrue(any(word in r for r in g.reasons(("basket",))), g.reasons(("basket",)))


class BasketWindowGate(TmpCwd):
    """바구니가 실제로 읽을 창(etf-data 거래일에서 t0 바로 앞 날)이 확인 범위와 같아야 열림(check_basket_window)."""

    def gate(self, window=(P, P)):
        import gates
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        arm()
        Path("gate-smoke").mkdir(exist_ok=True)
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")
        g = gates.begin(DAY, "engine", True, live_p=P)
        g._check("basket")["events"] = {"window": list(window) if window else None}
        return g

    def test_same_window_opens_hole_or_missing_closes(self):
        days = weekdays_until(P, 30) + [DAY]
        g = self.gate()
        g.check_basket_window(days)
        self.assertTrue(g.allows_new_risk("basket"), g.reasons())
        self.assertEqual(g.snapshot("basket")["checks"]["basket_window"], {"t0": P, "before": "20261109", "window": [P, P],
                                                                           "checked": [P, P]})
        cases = {"etf-data에 빈 날(앞 거래일 빠짐 → 창이 넓어짐)": ([x for x in days if x != "20261109"], None),
                 "t0가 거래일 목록에 없음": ([x for x in days if x != P], None),
                 "확인 범위 없음": (days, ()),
                 "확인 범위가 다름": (days, ("20261107", P))}
        for name, (got_days, window) in cases.items():
            with self.subTest(name):
                g = self.gate(window=(P, P) if window is None else window)
                g.check_basket_window(got_days)
                self.assertFalse(g.allows_new_risk("basket"))
                self.assertTrue(g.allows_new_risk("engine") and g.allows_new_risk("overlay"), "바구니만 닫음")
                self.assertTrue(any("바구니 사건 창" in r for r in g.reasons(("basket",))), g.reasons(("basket",)))

    def test_unknown_p_or_error(self):
        import gates
        g = gates.Gates(DAY, "engine")
        g.check_basket_window(weekdays_until(P, 5) + [DAY])
        self.assertFalse(g.allows_new_risk("basket"))
        g = self.gate()
        g.check_basket_window(None)
        self.assertFalse(g.allows_new_risk("basket"), "창을 못 셈 → 닫힘")


class BasketWindowRun(unittest.TestCase):
    def test_live_t0_changed_after_gate_buys_nothing(self):
        """문 셈 때 증권사 앞 거래일은 화요일(달력과 같음)인데 바구니 안에서 다시 물으니 월요일 → 확인 안 된 창으로 사지 않음."""
        extra = {"event-data/000030.json": {"code": "000030", "rows": [
            {"date": "20261109", "kind": "무상증자", "title": "주요사항보고서(무상증자결정)"}]}}
        normal = world_run("engine", extra_files=extra)
        self.assertIn("000040", [o[0] for o in buys(normal)])
        self.assertNotIn("000030", [o[0] for o in buys(normal)], "월요일 공시는 화요일 t0 창 밖이라 원래도 안 삼")
        out = world_run("engine", extra_files=extra, live_seq=[P, P, "20261109"])     # 문 셈 · 시장 폭 · 바구니 차례
        g = gates_file(out)
        self.assertTrue(g["decisions"]["basket"]["open"], "문 셈 때는 맞았음")
        self.assertEqual([o[0] for o in buys(out) if o[0] in ("000030", "000040")], [], "바구니 매수 0")
        self.assertIn(("000020", 200), sells(out), "20거래일 팔기는 그대로")
        why = audit_of(out, "basket")["결과"]["why"]
        self.assertTrue(any("공시 확인 범위와 달라" in w for w in why), why)
        import basket_live
        with mock.patch.object(basket_live, "window_matches", lambda *a: True):     # 방어를 끄면 확인 안 된 창의 공시를 삼(반례가 진짜임)
            off = world_run("engine", extra_files=extra, live_seq=[P, P, "20261109"])
        self.assertIn("000030", [o[0] for o in buys(off)])

    def test_window_matches(self):
        import basket_live as B
        snap = {"checks": {"events": {"window": [SAT, MON]}}}
        self.assertTrue(B.window_matches(snap, MON, FRI))
        self.assertFalse(B.window_matches(snap, MON, SAT), "앞 날이 다르면 창이 다름")
        self.assertFalse(B.window_matches(snap, TUE, FRI))
        self.assertFalse(B.window_matches({"checks": {}}, MON, FRI))
        self.assertFalse(B.window_matches(snap, None, None))
        self.assertFalse(B.window_matches({"checks": {"events": {"window": "깨짐"}}}, MON, FRI))


# ───────────────────────── 2c단계 B: D5 세션을 지어내지 않음(GPT 구현 검토 6705430244 §2-B) ─────────────────────────

SUNEUNG = "20261119"


def suneung_receipt(**kw):
    body = {"date": SUNEUNG, "source_url": SUNEUNG_URL, "notice_no": "시험공지-수능", "effective_from": SUNEUNG,
            "raw_sha256": hashlib.sha256(SUNEUNG_RAW).hexdigest(), "open": "1000", "close": "1630"}
    body.update(kw)
    return body


class SessionCalendar(TmpCwd):
    """판 고정 달력 읽기: 세션 unknown · 특수 세션 영수증 · 지어낸 시각 거부 · 문이 unknown · 특수 날을 닫음."""

    def smoke(self, day):
        Path("gate-smoke").mkdir(exist_ok=True)
        Path(f"gate-smoke/{day}-local-0.json").write_text(json.dumps({"date": day, "ok": True}), encoding="utf-8")

    def test_unknown_day_closes_all_normal_day_opens(self):
        import gates
        import trade_calendar as C
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026, unknown=(DAY,))
        arm()
        info = C.day_info(DAY)
        self.assertEqual((info["trading"], info["session"], info["open"], info["close"], info["session_sha256"], info["P"]),
                         (True, "unknown", None, None, None, P), "세션 원천 없는 날 = 거래일 · 개장 · 마감 없음")
        self.assertEqual(C.day_info("20261112")["P"], DAY, "unknown 날도 거래일(앞 거래일 셈)")
        self.smoke(DAY)
        for run in ("engine", "daily"):
            g = gates.begin(DAY, run, True, live_p=P)
            self.assertFalse(any(g.allows_new_risk(d) for d in g.active), run)
            self.assertTrue(any("세션 원천이 없음" in r for r in g.reasons()), g.reasons())
            snap = g.snapshot(g.active[0])
            self.assertEqual((snap["session"], snap["session_kind"], snap["session_sha256"]), ({"open": None, "close": None}, "unknown", None))
        self.smoke("20261112")
        g = gates.begin("20261112", "engine", True, live_p=DAY)
        self.assertTrue(all(g.allows_new_risk(d) for d in g.active), g.reasons())
        snap = g.snapshot("engine")
        self.assertEqual((snap["session"], snap["session_kind"], snap["session_sha256"]),
                         ({"open": "0900", "close": "1530"}, "regular", "1" * 64), "정상 날: 평소 세션 영수증 지문")

    def test_special_session_receipt_and_gate(self):
        import gates
        import trade_calendar as C
        sessions = {"regular": regular_receipt(2026), "special": [suneung_receipt()]}
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026, sessions=sessions,
                       special={SUNEUNG: {"open": "1000", "close": "1630", "session": "special"}})
        arm(on="20261118")
        info = C.day_info(SUNEUNG)
        self.assertEqual((info["session"], info["open"], info["close"], info["session_sha256"]),
                         ("special", "1000", "1630", hashlib.sha256(SUNEUNG_RAW).hexdigest()))
        self.assertEqual(C.day_info("20261120")["P"], SUNEUNG)
        self.smoke(SUNEUNG)
        g = gates.begin(SUNEUNG, "engine", True, live_p="20261118")
        self.assertFalse(any(g.allows_new_risk(d) for d in g.active))
        self.assertTrue(any("10:00 ~ 16:30" in r and "봇 기준 09:00 ~ 15:30과 다름" in r for r in g.reasons()), g.reasons())

    def test_synthesized_or_mismatched_sessions_are_rejected(self):
        import trade_calendar as C
        reg, spec = regular_receipt(2026), suneung_receipt()
        both = {"regular": reg, "special": [spec]}
        cases = {
            "평소 꼴 날에 지어낸 10:00 ~ 16:30": dict(special={SUNEUNG: {"open": "1000", "close": "1630"}}),
            "특수 꼴인데 영수증 없음": dict(special={SUNEUNG: {"open": "1000", "close": "1630", "session": "special"}}),
            "영수증은 있는데 그날이 평소 꼴": dict(sessions=both),
            "영수증은 있는데 그날이 unknown": dict(sessions=both, unknown=(SUNEUNG,)),
            "특수 시각이 영수증과 다름": dict(sessions=both, special={SUNEUNG: {"open": "1000", "close": "1530", "session": "special"}}),
            "같은 날 영수증 둘": dict(sessions={"regular": reg, "special": [spec, spec]},
                                 special={SUNEUNG: {"open": "1000", "close": "1630", "session": "special"}}),
            "공식 주소 아님": dict(sessions={"regular": dict(reg, source_url="https://example.com/hours"), "special": []}),
            "https 아님": dict(sessions={"regular": dict(reg, source_url="http://global.krx.co.kr/hours"), "special": []}),
            "krx 흉내 주소": dict(sessions={"regular": dict(reg, source_url="https://krx.co.kr.example.net/hours"), "special": []}),
            "원문 지문 꼴": dict(sessions={"regular": dict(reg, raw_sha256="xyz"), "special": []}),
            "평소 영수증 시행 날 앞의 평소 날": dict(sessions={"regular": dict(reg, effective_from="20260601"), "special": []}),
            "평소 영수증 시각이 판과 다름": dict(sessions={"regular": dict(reg, close="1600"), "special": []}),
            "평소 영수증 없음": dict(sessions={"special": []}),
            "unknown 꼴에 다른 칸": dict(special={DAY: {"session": "unknown", "open": "0900"}}),
            "모르는 세션 갈래": dict(special={DAY: {"open": "0900", "close": "1530", "session": "half"}}),
        }
        for name, kw in cases.items():
            with self.subTest(name):
                shutil.rmtree("calendar", ignore_errors=True)
                write_calendar("calendar", 2026, **kw)
                self.assertIsNone(C.load_year("2026"), name)
                self.assertIsNone(C.day_info(DAY), name)
        body = calendar_body(2026)
        del body["sessions"]
        Path("calendar/krx-2026-v2.json").write_text(json.dumps(body), encoding="utf-8")
        self.assertIsNone(C.load_year("2026"), "세션 칸 없는 판(예전 꼴 · 09:00 ~ 15:30 상수)은 못 씀")

    def test_session_receipts_are_bound_to_calendar_sha(self):
        import trade_calendar as C
        a = calendar_body(2026)
        b = calendar_body(2026, sessions={"regular": regular_receipt(2026, sha="3" * 64), "special": []})
        self.assertNotEqual(a["normalized_sha256"], b["normalized_sha256"], "평소 영수증 원문 지문이 바뀌면 판 지문이 바뀜")
        c = calendar_body(2026, sessions={"regular": dict(regular_receipt(2026), fetched_at_utc="2026-11-01T00:00:00Z"), "special": [],
                                           "unknown": [], "note": "설명", "overlay_sha256": "9" * 64})
        self.assertEqual(c["normalized_sha256"], a["normalized_sha256"], "받은 시각 · 설명 칸은 판 지문에 안 들어감")
        tampered = copy.deepcopy(a)
        tampered["sessions"]["regular"]["raw_sha256"] = "3" * 64                  # 영수증만 고치고 지문은 옛 그대로
        Path("calendar").mkdir()
        Path("calendar/krx-2026-v1.json").write_text(json.dumps(tampered), encoding="utf-8")
        self.assertIsNone(C.load_year("2026"), "영수증을 고치면 지문이 안 맞아 못 씀")
        for x in ("https://krx.co.kr/a", "https://global.krx.co.kr/b", "https://www.krx.co.kr/c.pdf", "https://kind.krx.co.kr/d"):
            self.assertTrue(C.official_url(x), x)
        for x in ("http://krx.co.kr/a", "https://krx.co.kr.evil.example/a", "https://evilkrx.co.kr/a", "ftp://krx.co.kr/a", None, ""):
            self.assertFalse(C.official_url(x), x)


class SessionBuild(CalendarToolCwd):
    """달력 도구(2c단계): 세션은 overlay 공식 원천을 받아 지문이 맞을 때만 · 아니면 unknown · 평소 세션 원천이 없으면 새 판 없음."""

    def pages(self, **extra):
        got = {REGULAR_URL: REGULAR_RAW, SUNEUNG_URL: SUNEUNG_RAW, NEWYEAR_URL: NEWYEAR_RAW}
        got.update(extra)
        return got

    def days(self, year=2026):
        return json.loads(Path(f"calendar/krx-{year}-v1.json").read_text(encoding="utf-8"))

    def test_suneung_special_unknown_tamper_and_missing_source(self):
        import trade_calendar as C
        sha = hashlib.sha256(SUNEUNG_RAW).hexdigest()
        cases = {
            "공식 overlay 확인": (dict(special=[(SUNEUNG, SUNEUNG_URL, SUNEUNG_RAW, "1000", "1630")]), {}, "special"),
            "overlay 없음(SPECIAL_HOURS)": (dict(), {}, "unknown"),
            "overlay 지문 변조": (dict(special=[(SUNEUNG, SUNEUNG_URL, "f" * 64, "1000", "1630")]), {}, "unknown"),
            "원천 누락(404)": (dict(special=[(SUNEUNG, SUNEUNG_URL, SUNEUNG_RAW, "1000", "1630")]), {SUNEUNG_URL: None}, "unknown"),
            "원천 연결 오류": (dict(special=[(SUNEUNG, SUNEUNG_URL, SUNEUNG_RAW, "1000", "1630")]),
                         {SUNEUNG_URL: ConnectionError("끊김")}, "unknown"),
            "공식 주소 밖으로 옮겨 감": (dict(special=[(SUNEUNG, SUNEUNG_URL, SUNEUNG_RAW, "1000", "1630")]), {"moved": True}, "unknown"),
        }
        for name, (ov, pages, kind) in cases.items():
            with self.subTest(name):
                shutil.rmtree("calendar", ignore_errors=True)
                write_overlay(2026, **ov)
                moved = pages.pop("moved", False)
                pg = self.pages(**pages)
                pg = {k: v for k, v in pg.items() if v is not None}
                get = FakeGet({2026: krx_raw(2026, KRX_2026)}, pages=pg, moved={SUNEUNG_URL} if moved else ())
                self.assertEqual(self.run_tool([2026], get=get, kis=FakeKis(KRX_2026)), 0, name)
                body = self.days()
                entry = body["days"][SUNEUNG]
                info = C.day_info(SUNEUNG, folder="calendar")
                if kind == "special":
                    self.assertEqual(entry, {"open": "1000", "close": "1630", "session": "special"})
                    self.assertEqual(info["session_sha256"], sha)
                    rec = body["sessions"]["special"][0]
                    self.assertEqual((rec["date"], rec["source_url"], rec["raw_sha256"], rec["notice_no"]),
                                     (SUNEUNG, SUNEUNG_URL, sha, f"시험공지-{SUNEUNG}"))
                    self.assertIn(SUNEUNG_URL, [c[0] for c in get.calls], "도구가 그 주소를 직접 받음")
                else:
                    self.assertEqual(entry, {"session": "unknown"}, "09:00 ~ 15:30을 쓰지 않음")
                    self.assertEqual((info["session"], info["open"], info["close"]), ("unknown", None, None))
                    why = [u["why"] for u in body["sessions"]["unknown"] if u["date"] == SUNEUNG][0]
                    word = {"overlay 없음(SPECIAL_HOURS)": "SPECIAL_HOURS", "overlay 지문 변조": "원문 sha256",
                            "원천 누락(404)": "HTTP 404", "원천 연결 오류": "ConnectionError", "공식 주소 밖으로 옮겨 감": "redirect"}[name]
                    self.assertIn(word, why)
                    self.assertEqual(body["sessions"]["special"], [])
                self.assertEqual(body["days"]["20261118"], {"open": "0900", "close": "1530"}, "다른 날은 평소 세션 영수증")

    def test_year_end_new_year_and_special_hours_days(self):
        import collect_kis_intraday as CI
        import trade_calendar as C
        self.assertEqual(self.run_tool([2026, 2027], get=FakeGet({2026: krx_raw(2026, KRX_2026), 2027: krx_raw(2027, KRX_2027)},
                                                                  pages=self.pages())), 0)
        d26, d27 = self.days(2026)["days"], self.days(2027)["days"]
        self.assertEqual((d26["20261230"], d26["20261231"]), ({"open": "0900", "close": "1530"}, None), "연말: 마지막 거래일 평소 · 12-31 휴장")
        self.assertEqual(d26["20260102"], {"session": "unknown"}, "연초: 새해 첫 거래일(늦게 여는 날) · overlay 없음")
        self.assertEqual(d27["20270104"], {"session": "unknown"}, "2027 새해 첫 거래일 · SPECIAL_HOURS · overlay 없음")
        info = C.day_info("20270104", folder="calendar")
        self.assertEqual((info["P"], info["session"], info["open"]), ("20261230", "unknown", None))
        self.assertEqual(C.day_info("20270105", folder="calendar")["P"], "20270104")
        for day in CI.SPECIAL_HOURS:
            got = (d26 if day.startswith("2026") else d27).get(day) if day[:4] in ("2026", "2027") else None
            if got is not None:
                self.assertNotEqual(got, {"open": "0900", "close": "1530"}, f"{day}: 봇 특수 세션 목록에 있는 날은 평소 시각을 쓰지 않음")
        write_overlay(2027, special=[("20270104", NEWYEAR_URL, NEWYEAR_RAW, "1000", "1530")])
        self.assertEqual(self.run_tool([2027], get=FakeGet({2027: krx_raw(2027, KRX_2027)}, pages=self.pages()),
                                       kis=FakeKis(KRX_2027)), 0)
        self.assertEqual(json.loads(Path("calendar/krx-2027-v2.json").read_text(encoding="utf-8"))["days"]["20270104"],
                         {"open": "1000", "close": "1530", "session": "special"}, "공식 공지가 확인된 뒤에만 특수 세션")
        self.assertEqual(C.day_info("20270104", folder="calendar")["session"], "special")

    def test_regular_source_missing_or_bad_keeps_old_version(self):
        self.assertEqual(self.run_tool([2026]), 0)
        v1 = Path("calendar/krx-2026-v1.json").read_bytes()
        extra = KRX_2026 + ("20261120",)                                   # 새 휴장 공지가 있어도 평소 세션 원천이 없으면 새 판을 안 씀
        sha = hashlib.sha256(REGULAR_RAW).hexdigest()
        cases = {
            "평소 세션 영수증 없음": (dict(regular=False), {}, "평소 세션 원천 영수증이 없음"),
            "overlay 파일 없음": (None, {}, "평소 세션 원천 영수증이 없음"),
            "평소 원문 지문 변조": (dict(regular=regular_receipt(2026, sha="e" * 64)), {}, "평소 세션 원천을 확인하지 못함"),
            "평소 원천 못 받음": (dict(), {"pages": {}}, "HTTP 404"),
            "공식 주소 아님": (dict(regular=regular_receipt(2026, sha=sha, source_url="https://example.com/hours")), {}, "꼴이 이상함"),
            "overlay 깨짐": ("{", {}, "JSON이 아님"),
            "특수 세션 날이 휴장": (dict(special=[("20261225", SUNEUNG_URL, SUNEUNG_RAW, "1000", "1630")]), {}, "거래일이 아님"),
        }
        for name, (ov, kw, word) in cases.items():
            with self.subTest(name):
                op = Path("calendar/sessions-2026.json")
                if ov is None:
                    op.unlink(missing_ok=True)
                elif isinstance(ov, str):
                    op.write_text(ov, encoding="utf-8")
                else:
                    write_overlay(2026, **ov)
                get = FakeGet({2026: krx_raw(2026, extra)}, pages=kw.get("pages"))
                self.assertEqual(self.run_tool([2026], get=get, kis=FakeKis(extra)), 1, name)
                self.assertEqual(self.files(), ["krx-2026-v1.json"], "옛 판 유지 · 새 판 없음")
                self.assertEqual(Path("calendar/krx-2026-v1.json").read_bytes(), v1)
                said = " ".join(" ".join(str(a) for a in c.args) for c in __import__("builtins").print.call_args_list[-2:])
                self.assertIn("2026년 달력 판을 쓰지 않음", said)
                self.assertIn(word, said)

    def test_same_content_no_new_version_and_core_change(self):
        self.assertEqual(self.run_tool([2026]), 0)
        self.assertEqual(self.run_tool([2026]), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json"], "받은 시각만 다르면 같은 내용")
        write_overlay(2026, memo="설명 칸만 더함")
        self.assertEqual(self.run_tool([2026]), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json"], "overlay 설명 칸만 바뀌면 새 판 없음")
        write_overlay(2026, regular=regular_receipt(2026, sha=hashlib.sha256(REGULAR_RAW).hexdigest(), notice_no="KRX 공지 1"))
        self.assertEqual(self.run_tool([2026]), 0)
        self.assertEqual(self.files(), ["krx-2026-v1.json", "krx-2026-v2.json"], "영수증 핵심(공지 번호)이 바뀌면 새 판")

    def test_dry_run_writes_only_out_folder(self):
        import trade_calendar as C
        self.assertEqual(self.B.main(["2026", "--dry-run", "--out", "dry"], client=FakeKis(KRX_2026),
                                     get=FakeGet({2026: krx_raw(2026, KRX_2026)}), folder="calendar"), 0)
        self.assertEqual(self.files(), [], "calendar/에는 아무 판도 안 씀")
        summary = json.loads(Path("dry/2026/summary.json").read_text(encoding="utf-8"))
        cand = json.loads(Path("dry/2026/candidate.json").read_text(encoding="utf-8"))
        self.assertEqual((summary["ok"], summary["would_write_version"], summary["same_as_version"]), (True, 1, None))
        self.assertEqual(summary["normalized_sha256"], cand["normalized_sha256"])
        self.assertEqual(summary["normalized_sha256"], C.normalized_digest(cand["days"], cand["sessions"]))
        self.assertEqual(summary["raw_files"]["krx-holidays.json"]["sha256"], hashlib.sha256(krx_raw(2026, KRX_2026)).hexdigest())
        self.assertEqual(summary["raw_files"]["regular-session"]["sha256"], hashlib.sha256(REGULAR_RAW).hexdigest())
        self.assertEqual(Path("dry/2026/raw/regular-session").read_bytes(), REGULAR_RAW, "원문 그대로")
        self.assertEqual(cand["days"][SUNEUNG], {"session": "unknown"})
        self.assertIn(SUNEUNG, [u["date"] for u in summary["unknown"]])
        self.assertRegex(summary["digests"]["kis_raw_sha256"], r"^[0-9a-f]{64}$")
        for f in Path("dry").rglob("*"):
            if f.is_file():
                for key in (b'"bass_dt"', b'"wday_dvsn_cd"', b'"sttl_day_yn"'):
                    self.assertNotIn(key, f.read_bytes(), f"{f}: 증권사 응답 본문(줄)은 남기지 않음 · 지문만")
        self.assertEqual(self.run_tool([2026]), 0)
        v1 = json.loads(Path("calendar/krx-2026-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(v1["normalized_sha256"], cand["normalized_sha256"], "마른 실행 후보 = 실제 판(받은 시각 빼고)")
        self.assertEqual(self.B.main(["2026", "--dry-run", "--out", "dry2"], client=FakeKis(KRX_2026),
                                     get=FakeGet({2026: krx_raw(2026, KRX_2026)}), folder="calendar"), 0)
        again = json.loads(Path("dry2/2026/summary.json").read_text(encoding="utf-8"))
        self.assertEqual((again["would_write_version"], again["same_as_version"]), (None, 1))
        self.assertEqual(self.files(), ["krx-2026-v1.json"])
        for bad in (["2026", "--out", "dry3"], ["2026", "--dry-run"], ["--dry-run", "--out"], ["2026", "--모름"]):
            self.assertEqual(self.B.main(bad, client=FakeKis(KRX_2026), get=FakeGet({}), folder="calendar"), 1, bad)
        self.assertFalse(Path("dry3").exists())

    def test_dry_run_without_overlay_saves_candidate_source(self):
        Path("calendar/sessions-2026.json").unlink()
        self.assertEqual(self.B.main(["2026", "--dry-run", "--out", "dry"], client=FakeKis(KRX_2026),
                                     get=FakeGet({2026: krx_raw(2026, KRX_2026)}), folder="calendar"), 1)
        summary = json.loads(Path("dry/2026/summary.json").read_text(encoding="utf-8"))
        self.assertFalse(summary["ok"])
        self.assertIn("평소 세션 원천 영수증이 없음", summary["error"])
        self.assertEqual(summary["regular_candidates"], [REGULAR_URL])
        self.assertEqual(summary["raw_files"]["regular-candidate-1"]["sha256"], hashlib.sha256(REGULAR_RAW).hexdigest(),
                         "사람이 읽고 overlay에 적을 원문 · 지문")
        self.assertFalse(Path("dry/2026/candidate.json").exists())
        self.assertEqual(self.files(), [])


class RegularSource(CalendarToolCwd):
    """2c단계 고침(2026-11-07 · 마른 실행 실패 '평소 세션 원천 영수증이 없음'): 평소 세션 원천 = 거래소 규정/제도의 정규장 표.
    실제 원문 사본으로 표 읽기 · 저장소 overlay(2026 · 2027)가 그 원문을 고정 · 원문 표 시각 ≠ overlay 시각 · 표 꼴이 바뀌면 새 판 없음."""

    def page(self):
        return REAL_REGULAR.read_bytes()

    def test_real_page_parses_and_repo_overlays_pin_it(self):
        raw = self.page()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), REAL_REGULAR_SHA, "원문 사본 = 2026-11-07에 받은 바이트(줄 끝 바꿈 없음)")
        self.assertEqual(self.B.regular_hours(raw), ("0900", "1530"), "표 '정규장' 줄의 매매거래시간 칸")
        self.assertEqual(self.B.REGULAR_CANDIDATES, (REGULAR_URL,))
        for year in (2026, 2027):
            with self.subTest(year):
                body, _ = self.B.load_overlay(year, folder=ROOT / "calendar")
                reg = body["regular"]
                self.assertEqual((reg["source_url"], reg["raw_sha256"], reg["open"], reg["close"], reg["effective_from"],
                                  reg["notice_no"]), (REGULAR_URL, REAL_REGULAR_SHA, "0900", "1530", "20261107", None))
                self.assertEqual(self.B.regular_check(reg)(raw), "", "저장소 overlay 시각 = 원문 표 시각")
                self.assertEqual((body["special"], body["unknown"]), ([], []), "특수 세션은 공식 공지가 확인된 뒤에만 적음")

    def test_build_with_real_page_and_changed_pages_keep_old_version(self):
        raw = self.page()
        write_overlay(2026, regular=regular_receipt(2026, sha=REAL_REGULAR_SHA, effective_from="20261107"))
        get = FakeGet({2026: krx_raw(2026, KRX_2026)}, pages={REGULAR_URL: raw})
        self.assertEqual(self.run_tool([2026], get=get, kis=FakeKis(KRX_2026)), 0)
        v1 = Path("calendar/krx-2026-v1.json").read_bytes()
        body = json.loads(v1)
        self.assertEqual((body["parser_version"], body["days"]["20261118"]), ("build_calendar 3", {"open": "0900", "close": "1530"}))
        self.assertEqual(body["days"]["20261106"], {"session": "unknown"}, "시행 날(처음 확인한 날 11-07) 앞 거래일은 unknown")
        self.assertEqual(body["days"][SUNEUNG], {"session": "unknown"}, "수능 날은 공식 공지 overlay 전까지 unknown")
        self.assertIn(REGULAR_URL, [c[0] for c in get.calls], "도구가 정규장 안내 주소를 직접 받음")
        text = raw.decode("utf-8")
        swap = (text.replace('<th scope="col">매매거래시간</th>', "@@").replace('<th scope="col">호가접수시간</th>', '<th scope="col">매매거래시간</th>')
                .replace("@@", '<th scope="col">호가접수시간</th>'))
        cases = {
            "overlay 마감 16:00": (dict(close="1600"), text, "0900 ~ 1530이 overlay에 적힌 0900 ~ 1600과 다름"),
            "overlay 개장 10:00": (dict(open="1000"), text, "overlay에 적힌 1000 ~ 1530과 다름"),
            "표 열 차례 바뀜(호가접수시간을 읽게 됨)": ({}, swap, "0830 ~ 1530이 overlay에 적힌 0900 ~ 1530과 다름"),
            "정규장 줄 없음": ({}, text.replace(">정규장<", ">정규 시장<"), "'정규장' 줄이 0개"),
            "정규장 줄 둘": ({}, text.replace("</tbody>", "<tr><th>정규장</th><td>09:00 ~ 15:30</td><td>08:30 ~ 15:30</td></tr></tbody>"),
                        "'정규장' 줄이 2개"),
            "표 머리 없음": ({}, text.replace("호가접수시간", "접수시간"), "표 머리가 0개"),
            "시각 꼴 바뀜": ({}, text.replace("<td>09:00 ~ 15:30</td>", "<td>9시 ~ 15시 30분</td>"), "'HH:MM ~ HH:MM' 꼴이 아님"),
            "칸 수 다름": ({}, text.replace("<td>08:30 ~ 15:30</td>", ""), "줄 칸 수 1가 표 머리 2과 다름"),
            "UTF-8 아님": ({}, None, "UTF-8 글이 아님"),
        }
        extra = KRX_2026 + ("20261120",)                                   # 새 휴장 공지가 있어도 평소 세션이 확인 안 되면 새 판을 안 씀
        for name, (kw, page, word) in cases.items():
            with self.subTest(name):
                data = page.encode("utf-8") if page is not None else raw.decode("utf-8").encode("euc-kr", "replace")
                write_overlay(2026, regular=regular_receipt(2026, sha=hashlib.sha256(data).hexdigest(), effective_from="20261107", **kw))
                get = FakeGet({2026: krx_raw(2026, extra)}, pages={REGULAR_URL: data})
                self.assertEqual(self.run_tool([2026], get=get, kis=FakeKis(extra)), 1, name)
                self.assertEqual(self.files(), ["krx-2026-v1.json"], "옛 판 유지 · 새 판 없음")
                self.assertEqual(Path("calendar/krx-2026-v1.json").read_bytes(), v1)
                said = " ".join(" ".join(str(a) for a in c.args) for c in __import__("builtins").print.call_args_list[-2:])
                self.assertIn("2026년 달력 판을 쓰지 않음 · 평소 세션 원천을 확인하지 못함", said)
                self.assertIn(word, said)

    def test_dry_run_logs_digest_and_hours(self):
        import builtins
        raw = self.page()
        write_overlay(2026, regular=regular_receipt(2026, sha=REAL_REGULAR_SHA, effective_from="20261107"))
        get = FakeGet({2026: krx_raw(2026, KRX_2026)}, pages={REGULAR_URL: raw})
        self.assertEqual(self.B.main(["2026", "--dry-run", "--out", "dry"], client=FakeKis(KRX_2026), get=get, folder="calendar"), 0)
        said = [" ".join(str(a) for a in c.args) for c in builtins.print.call_args_list]
        self.assertIn(f"마른 실행 원문 · 2026 · regular-session · sha256 {REAL_REGULAR_SHA} · 4278바이트 · 원문 표 정규장 0900 ~ 1530",
                      said)
        self.assertTrue(any(x.startswith("마른 실행 요약 · 2026 · 만들 판 1 · 같은 판 None · 정규화 지문 ") for x in said), said[-3:])
        summary = json.loads(Path("dry/2026/summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["raw_files"]["regular-session"]["regular_hours"], ["0900", "1530"])
        Path("calendar/sessions-2026.json").unlink()                       # overlay가 없으면 후보 주소 원문 · 지문 · 표 시각을 남김(판은 안 씀)
        builtins.print.reset_mock()
        self.assertEqual(self.B.main(["2026", "--dry-run", "--out", "dry2"], client=FakeKis(KRX_2026), get=get, folder="calendar"), 1)
        said = [" ".join(str(a) for a in c.args) for c in builtins.print.call_args_list]
        self.assertIn(f"마른 실행 원문 · 2026 · regular-candidate-1 · sha256 {REAL_REGULAR_SHA} · 4278바이트 · 원문 표 정규장 0900 ~ 1530",
                      said)
        self.assertEqual(self.files(), [])


# ───────────────────────── 2c단계: 부트스트랩 문(GPT 구현 검토 6705430244 §4-4 · gates/ARMED.json) ─────────────────────────

class Arming(TmpCwd):
    def setUp(self):
        super().setUp()
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        Path("gate-smoke").mkdir()
        Path(SMOKE).write_text(json.dumps({"date": DAY, "ok": True}), encoding="utf-8")

    def begin(self, run="engine"):
        import gates
        return gates.begin(DAY, run, True, live_p=P)

    def assertShut(self, g, word):
        self.assertFalse(any(g.allows_new_risk(d) for d in g.active), g.reasons())
        hit = [r for r in g.reasons() if r.startswith("첫 실행 확인 전")]
        self.assertTrue(hit and any(word in r for r in hit), (word, g.reasons()))

    def test_missing_mismatch_bad_future_and_ok(self):
        import trade_calendar as C
        for run in ("engine", "daily"):
            self.assertShut(self.begin(run), "없음")
        self.assertFalse(self.begin().snapshot("engine")["armed"]["ok"])
        sha = C.load_year("2026")["sha256"]
        cases = {"달력 sha256 다름": ({"calendar_sha256": "f" * 64}, "다름"), "확인 날이 오늘보다 뒤": ({"confirmed_on": "20261112"}, "뒤"),
                 "확인 날 꼴": ({"confirmed_on": "2026-11-10"}, "확인 날 칸"), "작업 번호 없음": ({"run_id": None}, "작업 번호 칸"),
                 "작업 번호 꼴": ({"run_id": "12a"}, "작업 번호 칸"), "sha256 꼴": ({"calendar_sha256": sha.upper()}, "달력 sha256 칸")}
        for name, (kw, word) in cases.items():
            with self.subTest(name):
                arm(**kw)
                self.assertShut(self.begin(), word)
        Path("gates/ARMED.json").write_text("{", encoding="utf-8")
        self.assertShut(self.begin(), "깨짐")
        Path("gates/ARMED.json").write_text("[]", encoding="utf-8")
        self.assertShut(self.begin(), "꼴")
        body = arm(run_id=4321)                                             # 작업 번호는 수로 적어도 됨
        g = self.begin()
        self.assertTrue(all(g.allows_new_risk(d) for d in g.active), g.reasons())
        got = g.snapshot("basket")["armed"]
        self.assertEqual((got["ok"], got["calendar_sha256"], got["confirmed_on"], got["run_id"], got["current_calendar_sha256"]),
                         (True, sha, "20261110", 4321, sha))
        self.assertEqual(body["calendar_sha256"], sha)
        write_calendar("calendar", 2026, version=2, holidays=HOLIDAYS_2026 + ("20261120",))   # 새 판 → 다시 확인 전까지 닫힘
        self.assertShut(self.begin(), "새 판이면 다시 확인")

    def test_gates_file_keeps_armed_and_daily_reads_own(self):
        import gates
        arm()
        g = self.begin("engine")
        g.save()
        body = json.loads(Path(f"gates/{DAY}.json").read_text(encoding="utf-8"))
        self.assertTrue(body["runs"]["engine"]["armed"]["ok"])
        Path("gates/ARMED.json").unlink()
        d = gates.begin(DAY, "daily", True, live_p=P)
        self.assertFalse(d.allows_new_risk("daily"), "1일봉 실행도 자기 차례에 ARMED를 다시 봄")
        self.assertTrue(d.allows_new_risk("engine"), "엔진 실행이 적은 판단은 그대로")


class ArmingRun(unittest.TestCase):
    def test_unarmed_world_blocks_new_risk_only(self):
        for name, armed in (("ARMED 없음", False), ("다른 달력 sha256", {"calendar_sha256": "f" * 64})):
            with self.subTest(name):
                out = world_run("engine", armed=armed)
                g = gates_file(out)
                for d in ("engine", "basket", "overlay"):
                    self.assertFalse(g["decisions"][d]["open"], d)
                    self.assertTrue(any(r.startswith("첫 실행 확인 전") for r in g["decisions"][d]["reasons"]))
                self.assertEqual(buys(out), [], "엔진 · 바구니 · 덧붙임 매수 0")
                self.assertIn(("000020", 200), sells(out), "바구니 20거래일 팔기는 그대로")
                self.assertIn(("138230", 1000), sells(out), "엔진 규칙 매도는 그대로")
                daily = world_run("daily", armed=armed)
                self.assertEqual(daily["orders"], [["000010", "sell", 100]], "1일봉 매수 0 · 팔기는 그대로")


# ───────────────────────── 2c단계: 시작 전 점검(범위 · 첫 실행 확인 문 · 세션) ─────────────────────────

class Smoke2c(TmpCwd):
    def test_smoke_catches_broken_window_and_armed_checks(self):
        import event_manifest
        import gate_smoke
        import gates
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026)
        self.assertTrue(gate_smoke.check(DAY)["ok"], gate_smoke.check(DAY)["reasons"])
        real = event_manifest.morning_check

        def t0_only(t0, day, decided_at, folder=None, data=None, git=True, calendar_folder=None, window=None):
            return real(t0, day, decided_at, folder=folder, data=data, git=git, window={"begin": t0, "end": t0, "before": None})
        with mock.patch.object(event_manifest, "morning_check", t0_only):    # 범위를 t0 하루로만 보는 고장(예전 셈)
            reasons = gate_smoke.check(DAY)["reasons"]
        self.assertIn("맞는 아침 확인 manifest를 거부함", reasons, "주말 낀 범위 manifest를 못 여는 고장을 잡음")
        with mock.patch.object(gates, "armed_status", lambda *a, **k: (True, "", {})):
            reasons = gate_smoke.check(DAY)["reasons"]
        self.assertTrue(any("ARMED.json이 없는데 통과시킴" in r for r in reasons), reasons)
        with mock.patch.object(gates, "armed_status", lambda *a, **k: (False, "첫 실행 확인 전(고장)", {})):
            reasons = gate_smoke.check(DAY)["reasons"]
        self.assertTrue(any("'맞는 확인'을 거부함" in r for r in reasons), reasons)
        self.assertFalse(Path("gates").exists(), "점검은 실제 gates/를 안 건드림")

    def test_smoke_reports_unknown_session(self):
        import gate_smoke
        write_calendar("calendar", 2026, holidays=HOLIDAYS_2026, unknown=(DAY,))
        body = gate_smoke.check(DAY)
        self.assertFalse(body["ok"])
        self.assertEqual(body["session"], "unknown")
        self.assertIn("달력에 오늘 세션 원천이 없음(session unknown)", body["reasons"])


class Structure2c(unittest.TestCase):
    def test_engine_checks_basket_window_before_basket(self):
        text = (ROOT / "idle_live.py").read_text(encoding="utf-8")
        run = text[text.index("def run(now=None):"):]
        marks = ["gate.check_events()", 'days = [str(d) for d, c in _load(Path("etf-data") / f"{K200}.json"',
                 "gate.check_basket_window(days)", 'if not gate.allows_new_risk("basket"):', "basket_live.run("]
        at = [run.index(m) for m in marks]
        self.assertEqual(at, sorted(at), "바구니 창 검사는 같은 days로 · 바구니를 부르기 전")

    def test_snapshot_keys(self):
        import gate_smoke
        for k in ("session_kind", "session_sha256", "armed"):
            self.assertIn(k, gate_smoke.SNAP_KEYS)


# ───────────────────────── 2c단계 C: 필수 CI · 전체 시험 차이 검사 · 달력 마른 실행 작업 흐름 ─────────────────────────

D_BUNDLE = ("tests.test_boost_d tests.test_audit_log tests.test_boost_audit tests.test_daily_live tests.test_paper_trade "
            "tests.test_idle_live tests.test_idle_signal tests.test_basket_live tests.test_acc_cap tests.test_overlay_live "
            "tests.test_hourly_a tests.test_collect_events tests.test_investor_history")


def diff_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_diff", ROOT / "tools" / "test_diff.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MINI_TESTS = '''import unittest


class T(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(True)

    def test_old_fail(self):
        self.assertEqual(1, 2)

    @unittest.skip("건너뜀")
    def test_skip(self):
        raise RuntimeError

    @unittest.expectedFailure
    def test_expected(self):
        self.assertEqual(1, 2)
'''


class CiDiff(TmpCwd):
    def git(self, *args, cwd="repo"):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_AUTHOR_NAME="시험", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="시험",
                   GIT_COMMITTER_EMAIL="t@example.invalid")
        got = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args], cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(got.returncode, 0, got.stderr)
        return got.stdout.strip()

    def test_compare_sets(self):
        T = diff_tool()
        got = T.compare({"a.T.x", "b.T.y"}, {"a.T.x"})
        self.assertEqual((got["green"], got["new_failures"], got["fixed"]), (True, [], ["b.T.y"]))
        got = T.compare({"a.T.x"}, {"a.T.x", "c.T.z"})
        self.assertEqual((got["green"], got["new_failures"], got["base_failed"], got["head_failed"]),
                         (False, ["c.T.z"], ["a.T.x"], ["a.T.x", "c.T.z"]))
        self.assertTrue(T.compare(set(), set())["green"])
        md = T.summary_md(got, {"base": "b" * 40, "head": "h" * 40, "base_tests": 3, "head_tests": 4})
        self.assertIn("- `c.T.z`", md)
        self.assertIn("red", md)

    def test_runner_collects_failures_errors_and_import_errors(self):
        T = diff_tool()
        Path("mini/tests").mkdir(parents=True)
        Path("mini/tests/test_x.py").write_text(MINI_TESTS + '''

    def test_error(self):
        raise RuntimeError("오류")

    @unittest.expectedFailure
    def test_unexpected_pass(self):
        self.assertTrue(True)
''', encoding="utf-8")
        Path("mini/tests/test_broken.py").write_text("import 없는_모듈_입니다\n", encoding="utf-8")
        body = T.run_suite(Path("mini").resolve(), Path("out/x.json").resolve())
        self.assertEqual(body["tests_run"], 7)
        bad = T.failed_set(body)
        self.assertEqual(sorted(bad), ["test_x.T.test_error", "test_x.T.test_old_fail", "test_x.T.test_unexpected_pass",
                                       "unittest.loader._FailedTest.test_broken"])
        self.assertIn("test_x.T.test_old_fail", bad)
        self.assertIn("test_x.T.test_error", bad)
        self.assertIn("test_x.T.test_unexpected_pass", bad)
        self.assertTrue(any("test_broken" in x for x in bad), "불러오기 실패도 오류로 셈")
        self.assertNotIn("test_x.T.test_skip", bad)
        self.assertNotIn("test_x.T.test_expected", bad)
        self.assertNotIn("test_x.T.test_pass", bad)

    def test_end_to_end_green_red_with_worktree(self):
        T = diff_tool()
        Path("repo/tests").mkdir(parents=True)
        self.git("-c", "init.defaultBranch=main", "init", "-q", cwd="repo")
        Path("repo/tests/test_x.py").write_text(MINI_TESTS, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "기준")
        base = self.git("rev-parse", "HEAD")
        rc = T.main(["--base", base, "--out", str(Path("out1").resolve()), "--root", str(Path("repo").resolve())])
        diff = json.loads(Path("out1/diff.json").read_text(encoding="utf-8"))
        self.assertEqual((rc, diff["green"], diff["base_failed"], diff["head_failed"]), (0, True, ["test_x.T.test_old_fail"],
                                                                                       ["test_x.T.test_old_fail"]),
                         "같은 기존 실패만 있으면 green")
        Path("repo/tests/test_x.py").write_text(MINI_TESTS + '''
    def test_new_fail(self):
        self.assertEqual("새", "실패")
''', encoding="utf-8")
        rc = T.main(["--base", base, "--out", str(Path("out2").resolve()), "--root", str(Path("repo").resolve())])
        diff = json.loads(Path("out2/diff.json").read_text(encoding="utf-8"))
        self.assertEqual((rc, diff["green"], diff["new_failures"], diff["head_dirty"]), (1, False, ["test_x.T.test_new_fail"], True),
                         "커밋 안 한 고침의 새 실패도 red")
        self.assertIn("test_x.T.test_new_fail", Path("out2/summary.md").read_text(encoding="utf-8"))
        Path("repo/tests/test_x.py").write_text(MINI_TESTS.replace("self.assertEqual(1, 2)\n\n    @unittest.skip",
                                                                   "self.assertEqual(1, 1)\n\n    @unittest.skip"), encoding="utf-8")
        rc = T.main(["--base", base, "--out", str(Path("out3").resolve()), "--root", str(Path("repo").resolve())])
        diff = json.loads(Path("out3/diff.json").read_text(encoding="utf-8"))
        self.assertEqual((rc, diff["fixed"], diff["head_failed"]), (0, ["test_x.T.test_old_fail"], []), "기존 실패를 고치면 green")
        self.assertEqual(self.git("worktree", "list").count("\n"), 0, "기준 판 worktree는 지움")
        self.assertEqual(T.main(["--base", "없는커밋", "--out", str(Path("out4").resolve()), "--root", str(Path("repo").resolve())]), 1)
        with mock.patch.object(T, "run_suite", lambda *a, **k: None):
            self.assertEqual(T.main(["--base", base, "--out", str(Path("out5").resolve()), "--root", str(Path("repo").resolve())]), 1,
                             "한 판이라도 끝까지 못 돌리면 red")

    def test_workflow_files(self):
        wf = (ROOT / ".github" / "workflows" / "boost-d-ci.yml").read_text(encoding="utf-8")
        self.assertIn("pull_request:", wf)
        self.assertIn("workflow_dispatch:", wf)
        self.assertIn("claude/boost-d-fixes", wf)
        self.assertIn(f"python -m unittest -v {D_BUNDLE}", wf, "D 묶음 그대로(필수 job)")
        self.assertIn("python tools/test_diff.py", wf)
        self.assertIn("github.event.pull_request.base.sha", wf)
        self.assertIn("git merge-base origin/main HEAD", wf)
        self.assertIn("actions/upload-artifact@v4", wf)
        self.assertIn("fetch-depth: 0", wf)
        self.assertNotIn("secrets.", wf, "키 없음")
        self.assertNotIn("continue-on-error", wf, "실패를 숨기지 않음")
        dry = (ROOT / ".github" / "workflows" / "calendar-dry.yml").read_text(encoding="utf-8")
        self.assertIn("python tools/build_calendar.py --dry-run --out calendar-dry", dry)
        for word in ("git push", "git commit", "git add"):
            self.assertNotIn(word, dry, "커밋 · 올리기 없음")
        cal = (ROOT / ".github" / "workflows" / "calendar.yml").read_text(encoding="utf-8")
        for line in ("KIS_APP_KEY: ${{ secrets.KIS_APP_KEY }}", "KIS_APP_SECRET: ${{ secrets.KIS_APP_SECRET }}", "KIS_ENV: real"):
            self.assertIn(line, dry, "달력 작업과 같은 Secrets 이름(시세용 연결 broker_kis.market)")
            self.assertIn(line, cal)
        self.assertIn("actions/upload-artifact@v4", dry)
        self.assertIn("contents: read", dry)
        self.assertIn("tools/build_calendar.py", dry)
        self.assertIn("trade_calendar.py", dry)


if __name__ == "__main__" and "--golden" in sys.argv:
    make_golden()
    print("얼린 결과를 씀 ·", GOLDEN)
    sys.exit(0)

if __name__ == "__main__":
    unittest.main()
