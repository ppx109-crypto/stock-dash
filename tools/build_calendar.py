"""판 고정 거래 달력 만들기(BOOST-0001-D 사전등록 판 3 §1.4 · D5 · 2b단계 · 2c단계 세션) → calendar/krx-<해>-v<번호>.json(trade_calendar.py가 읽는 꼴).

1차(권위) KRX — 정보데이터시스템(data.krx.co.kr)의 휴장일 조회.
  근거(2026-11-07 읽음): 그 사이트의 날짜 고르기 스크립트 /inc/lib/calendar/calendar.js가 휴장일을 칠할 때 부르는 조회
    GET https://data.krx.co.kr/comm/bldAttendant/executeForResourceBundle.cmd
        ?baseName=krx.mdc.i18n.component&key=B125.bld&search_bas_yy=<해>
    → {"result": {"block1": [{"calnd_dd": "YYYYMMDD"}, ...]}}  (평일 휴장일만 · 주말은 없음 · 로그인 없이 열림)
  2026-11-07 확인 값: 2026년 17일(01-01 · 02-16 ~ 18 · 03-02 · 05-01 · 05-05 · 05-25 · 06-03 · 07-17 · 08-17 · 09-24 · 09-25 ·
  10-05 · 10-09 · 12-25 · 12-31) · 2027년 16일. 공식 휴장일 안내 화면(open.krx.co.kr)은 이 환경에서 막혀 함께 견주지 못함.
  공지 번호가 없는 조회라 notice_no에는 조회 이름 · 해 · 원문 지문 앞자리를 적음.
2차(대조) KIS — 한국투자증권 국내휴장일조회(조회만 · 실전 전용 · 모의투자 미지원).
    GET /uapi/domestic-stock/v1/quotations/chk-holiday · tr_id CTCA0903R · 물음 칸 BASS_DT(기준일자) · CTX_AREA_NK · CTX_AREA_FK
    → output[]: bass_dt(기준일자) · wday_dvsn_cd(요일) · bzdy_yn(영업일) · tr_day_yn(거래일) · opnd_yn(개장일) · sttl_day_yn(결제일).
  주문이 되는 날 = opnd_yn 'Y'(한투 안내: 주문 가능 여부는 개장일여부로 봄). 인증 · 요청은 시세용 연결(broker_kis.market() — KIS_APP_KEY ·
  KIS_APP_SECRET · KIS_ENV=real · 토큰은 KIS_TOKEN_FILE로 하루 한 번 재사용 · 같은 길 _market_rows)을 그대로 씀.
  한투가 원장 부담으로 잦은 호출을 피하라고 해 달에 한 번만 돌리고, 부를 때마다 CAL_KIS_PAUSE초(기본 1초) 쉼.
  연속조회 키에 기대지 않고 기준일자를 '받은 마지막 날 다음 날'로 옮겨 가며 1월 1일 ~ 12월 31일을 다 덮을 때까지 물음.
세션(2c단계 · GPT 구현 검토 6705430244 §2-B · 세션을 지어내지 않음): 두 휴장일 원천은 거래일 여부만 알려 주고 개장 · 마감 시각은
  증명하지 않으므로, 시각은 세션 overlay 파일 calendar/sessions-<해>.json의 **공식 원천 영수증**으로만 적음 — 도구가 그 주소를 직접 받아
  원문 sha256이 overlay에 적힌 값과 같을 때만 반영(주소는 https · krx.co.kr 공식 주소만).
  · regular(평소 세션): KRX 공식 정규장 시간 안내 주소 · 공지 번호(있으면) · 시행 날 · 원문 sha256 · 개장 · 마감.
    없거나 · 못 받거나 · 지문이 다르거나 · **원문 표에서 읽은 정규장 시각이 overlay의 개장 · 마감과 다르면** 판을 새로 쓰지 않음
    (옛 판 유지 · 까닭 출력). 원천(2026-11-07 고정): 한국거래소 규정/제도 사이트(regulation.krx.co.kr)의 유가증권시장
    '매매거래제도일반 · 매매거래의 일반절차 휴장일' 탭 — '매매거래시간 및 호가접수시간' 표의 '정규장' 줄(매매거래시간 09:00 ~ 15:30).
    regular_hours()가 그 표 머리(구분 · 매매거래시간 · 호가접수시간)와 '정규장' 줄을 읽어 개장 · 마감을 뽑음(사람이 옮겨 적은 값만 믿지 않음 ·
    표 꼴이 바뀌면 짐작하지 않고 실패). 원문에 시행 날이 없어 시행 날은 처음 읽어 확인한 날(그 앞 거래일은 unknown).
  · special(특수 세션): 날마다 공식 공지 주소 · 번호 · 시행 날 · 원문 sha256 · 개장 · 마감 → 확인되면 그날 {"open", "close", "session": "special"}.
  · 세션 원천이 없는 거래일은 {"session": "unknown"}(개장 · 마감 없음 → 문이 그날 모든 활성 판단의 새 위험 증가를 막음):
    overlay 특수 세션인데 원천 확인 실패(못 받음 · 지문 다름) · overlay unknown 목록 · collect_kis_intraday.SPECIAL_HOURS에 있는데
    확인된 overlay가 없음(예: 20261119 수능 · 20270104 새해 첫 거래일 — 09:00 ~ 15:30을 쓰지 않음 · SPECIAL_HOURS로 봇이 쉬는 것은 그대로) ·
    새해 첫 거래일(늦게 여는 날)인데 확인된 overlay가 없음 · 평소 영수증 시행 날 앞.
  overlay 꼴: {"kind": "krx-session-overlay", "year": "2026",
               "regular": {"source_url", "notice_no", "source_effective_from", "verified_from", "raw_sha256", "open", "close"},
               "special": [{"date", "source_url", "notice_no", "source_effective_from", "verified_from", "raw_sha256", "open", "close"}],
               "unknown": ["YYYYMMDD"],
               "exceptions_review": {"reviewed_through", "verified_at", "reviewer", "method", "sources": [{"url", "fetched_at_utc", "raw_sha256", "what"}]}}
  3단계 고침(GPT 구현 검토 판 3 · 6709669142): ① source_effective_from = 원천이 밝힌 시행 날(원문에 없으면 null) · verified_from = 사람이
  원문을 읽고 뜻을 확인한 날 → 평소 세션 적용 하한 = max(둘) — '처음 읽은 날'을 원천 시행 날로 적지 않음 ② exceptions_review = 특수 세션
  예외(임시 변경) 공지 검토 지평 — 평소 표는 기본 시각만 증명하고 임시 변경 공지가 '없음'은 증명하지 못하므로, 검토한 끝 날(reviewed_through)
  뒤 거래일은 모두 session unknown · 검토 영수증 sha256(review_sha256)과 지평을 판 지문에 묶음 · 없으면 판을 쓰지 않음 · 판을 갱신할 때
  사람이 다시 검토해 지평을 앞으로 옮김(KRX 공지 목록 완전성 영수증은 이 환경에서 그 사이트들이 막혀 아직 못 만듦).
  주소 · 지문은 사람이 공식 원문을 읽고 적음(처음에는 마른 실행이 받아 둔 원문 · 지문을 보고 적음). 특수 세션 공지는 꼴이 해마다 달라(PDF 등)
  표를 읽지 않고 원문 지문 + 사람이 옮겨 적은 시각만 씀(평소 세션만 원문 표 대조).
판 쓰기: 두 원천이 그해 모든 날에서 거래일 여부가 같고 평소 세션 영수증이 확인될 때만. 다르거나 · 한쪽이라도 조회 실패 · 그해를 다 못 받음 ·
  평소 세션 원천 없음이면 쓰지 않고 까닭을 찍음(어느 쪽도 다른 쪽을 조용히 덮지 않음).
  같은 내용(정규화 지문 = days + 세션 영수증 핵심이 그해 가장 큰 판과 같음)이면 새 판을 만들지 않음 · 다르면 번호를 하나 올린 새 파일
  ('x' 모드 · 옛 판은 덮지 않음).
마른 실행: python tools/build_calendar.py [해 …] --dry-run --out <폴더> → 같은 원천을 받아 같은 검증을 하되 calendar/에는 아무것도 쓰지 않고
  <폴더>/<해>/에 원문(raw/ · KRX 휴장일 · 세션 원천 · 평소 세션이 아직 고정되지 않았으면 후보 주소 원문) · 요약(summary.json: 원문 지문 ·
  정규화 지문 · 만들 판 번호 또는 같은 내용 · unknown 날과 까닭 · 실패 까닭) · 만들 판 후보(candidate.json)를 남김
  (작업 흐름 calendar-dry.yml이 artifact로 올림). 증권사 응답 본문은 남기지 않음(지문 · 다른 날만). 작업 기록에도 요약 한 줄씩
  (원문 이름 · sha256 · 크기 · 원문 표에서 읽은 정규장 시각 · 만들 판 · unknown 날 수)을 찍음(artifact를 못 받는 곳에서도 대조).
사용: python tools/build_calendar.py [해 ...] [--dry-run --out 폴더]   (해를 안 주면 CAL_YEARS 환경 값 · 그것도 없으면 올해, 12월이면 다음 해도)
끝 값: 0 = 모든 해가 새 판을 썼거나(마른 실행은 쓸 수 있거나) 같은 내용 · 1 = 한 해라도 못 씀(그 해는 아무것도 쓰지 않음).
주문 없음 · 키 · 계좌 · 증권사 응답 본문은 찍지 않음.
"""
import ast
import hashlib
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import trade_calendar  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
FOLDER = Path("calendar")
PARSER = "build_calendar 3"                 # 3: 평소 세션 원문 표 대조 · 2: 개장 · 마감은 세션 영수증으로만 · 1: 09:00 ~ 15:30 상수
UTC_FORM = "%Y-%m-%dT%H:%M:%SZ"

KRX_URL = "https://data.krx.co.kr/comm/bldAttendant/executeForResourceBundle.cmd"
KRX_PARAMS = {"baseName": "krx.mdc.i18n.component", "key": "B125.bld"}
KRX_YEAR = "search_bas_yy"
KRX_FIELD = "calnd_dd"
KRX_NAME = "KRX 정보데이터시스템 휴장일 조회(날짜 고르기 휴장일 · B125.bld)"
KRX_REFERER = "https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd"
AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

KIS_PATH = "/uapi/domestic-stock/v1/quotations/chk-holiday"
KIS_TR = "CTCA0903R"
KIS_NAME = "한국투자증권 국내휴장일조회(CTCA0903R)"
KIS_DAY, KIS_OPEN = "bass_dt", "opnd_yn"
KIS_KEEP = ("bass_dt", "wday_dvsn_cd", "bzdy_yn", "tr_day_yn", "opnd_yn", "sttl_day_yn")
KIS_PAUSE = float(os.getenv("CAL_KIS_PAUSE", "1.0"))
KIS_MAX_CALLS = 60
SESSION_NOTE = "개장 · 마감은 세션 overlay의 공식 원천 영수증(주소 · 원문 sha256)으로만 적음 · 원천이 없는 거래일은 session unknown"
OVERLAY_KIND = "krx-session-overlay"
SPECIAL_SOURCE = ROOT / "collect_kis_intraday.py"       # 봇 특수 세션 목록(SPECIAL_HOURS)을 글로 읽음(불러오지 않음)
# 평소 세션 원천 후보(한국거래소 규정/제도 · 유가증권시장 매매거래제도일반 · '매매거래의 일반절차 휴장일' 탭) — 마른 실행이 overlay에
# 평소 세션이 없을 때만 받아 원문 · 지문 · 표에서 읽은 시각을 남김(사람이 읽고 overlay에 적기 전에는 판에 쓰지 않음)
REGULAR_CANDIDATES = ("https://regulation.krx.co.kr/contents/RGL/03/03010100/RGL03010100T1.jsp",)
REGULAR_ROW, REGULAR_COL, ORDER_COL = "정규장", "매매거래시간", "호가접수시간"   # 공식 원문 표: 줄 이름 · 매매 시각 칸 · 호가 접수 칸


class CalendarError(RuntimeError):
    """원천 조회 · 꼴 · 대조 실패 → 그 해는 판을 쓰지 않음."""


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _utc(now=None):
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime(UTC_FORM)


def year_days(year):
    """그해 모든 날(YYYYMMDD · 1월 1일 ~ 12월 31일)."""
    d, out = date(int(year), 1, 1), []
    while d.year == int(year):
        out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def _day(text):
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except (TypeError, ValueError):
        return None


# ───────────────────────── 1차: KRX ─────────────────────────

def krx_url(year):
    return f"{KRX_URL}?baseName={KRX_PARAMS['baseName']}&key={KRX_PARAMS['key']}&{KRX_YEAR}={int(year)}"


def krx_fetch(year, get=None):
    """KRX 휴장일 원문(바이트) → (원문, 주소). 연결 · HTTP 오류는 CalendarError."""
    if get is None:
        import requests
        get = requests.get
    params = dict(KRX_PARAMS)
    params[KRX_YEAR] = str(int(year))
    try:
        r = get(KRX_URL, params=params, headers={"User-Agent": AGENT, "Referer": KRX_REFERER}, timeout=(10, 30))
    except Exception as e:
        raise CalendarError(f"KRX 휴장일 조회 실패 · {type(e).__name__}") from None
    code = getattr(r, "status_code", None)
    if code != 200:
        raise CalendarError(f"KRX 휴장일 조회 실패 · HTTP {code}")
    return bytes(r.content), krx_url(year)


def krx_holidays(raw, year):
    """KRX 원문 → 그해 휴장일 집합(YYYYMMDD). 꼴이 다르거나 · 다른 해 날짜 · 하나도 없으면 CalendarError."""
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise CalendarError("KRX 응답이 JSON이 아님(로그인 요구 · 막힘일 수 있음)") from None
    block = body.get("result", {}).get("block1") if isinstance(body, dict) and isinstance(body.get("result"), dict) else None
    if not isinstance(block, list):
        raise CalendarError("KRX 응답에 result.block1 목록이 없음")
    out = set()
    for item in block:
        d = str(item.get(KRX_FIELD) or "") if isinstance(item, dict) else ""
        if not re.fullmatch(r"\d{8}", d) or d[:4] != f"{int(year):04d}" or _day(d) is None:
            raise CalendarError(f"KRX 휴장일 꼴이 이상함 · {d!r}")
        out.add(d)
    if not out:
        raise CalendarError("KRX 휴장일이 하나도 없음(아직 공지 전이거나 조회 실패)")
    return out


# ───────────────────────── 2차: KIS ─────────────────────────

def kis_fetch(client, year, pause=None, max_calls=KIS_MAX_CALLS):
    """KIS 국내휴장일조회로 그해 모든 날의 개장일 여부 → ({날: 'Y'|'N'}, 원문 줄(칸 고름), 부른 수). 다 못 받으면 CalendarError."""
    pause = KIS_PAUSE if pause is None else float(pause)
    days = year_days(year)
    got, raw, calls, start = {}, [], 0, days[0]
    while start <= days[-1]:
        if calls >= max_calls:
            raise CalendarError(f"KIS 휴장일을 {max_calls}번 물어도 그해를 다 못 받음")
        if calls:
            time.sleep(pause)
        try:
            rows = client._market_rows(KIS_PATH, KIS_TR, {"BASS_DT": start, "CTX_AREA_NK": "", "CTX_AREA_FK": ""}, "국내휴장일",
                                       key="output")
        except Exception as e:
            raise CalendarError(f"KIS 휴장일 조회 실패 · {type(e).__name__}") from None
        calls += 1
        newest = None
        for row in rows:
            d, yn = str(row.get(KIS_DAY) or ""), str(row.get(KIS_OPEN) or "")
            if not re.fullmatch(r"\d{8}", d) or _day(d) is None or yn not in ("Y", "N"):
                raise CalendarError(f"KIS 휴장일 응답 꼴이 이상함 · {d!r} {yn!r}")
            raw.append({k: row.get(k) for k in KIS_KEEP})
            if d < start:
                continue
            if d in got and got[d] != yn:
                raise CalendarError(f"KIS가 같은 날 {d}을 다르게 줌")
            if d[:4] == f"{int(year):04d}":
                got[d] = yn
            newest = d if newest is None else max(newest, d)
        if newest is None:
            raise CalendarError(f"KIS가 {start}부터의 날을 주지 않음(그해를 다 못 받음)")
        start = (_day(newest) + timedelta(days=1)).strftime("%Y%m%d")
    missing = [d for d in days if d not in got]
    if missing:
        raise CalendarError(f"KIS가 그해 날을 다 주지 않음 · 빠진 날 {len(missing)}개(처음 {missing[0]})")
    return got, raw, calls


# ───────────────────────── 세션(2c단계 · 공식 원천 영수증) ─────────────────────────

def known_special(path=None):
    """봇 특수 세션 목록(collect_kis_intraday.SPECIAL_HOURS)을 파일 글에서 읽음(research/boost_audit.special_hours와 같은 길) → {날: 설명}.
    못 읽으면 CalendarError(그 날들을 unknown으로 둘 수 없으므로 판을 쓰지 않음)."""
    path = Path(path) if path is not None else SPECIAL_SOURCE
    try:
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SPECIAL_HOURS" for t in node.targets):
                return {str(k): str(v) for k, v in ast.literal_eval(node.value).items()}
    except (OSError, SyntaxError, ValueError, AttributeError):
        pass
    raise CalendarError("봇 특수 세션 목록(SPECIAL_HOURS)을 못 읽음")


def overlay_path(year, folder=None):
    return (Path(folder) if folder is not None else FOLDER) / f"sessions-{int(year):04d}.json"


def _entry_problems(x, year, special):
    """overlay 한 칸의 꼴 문제(비면 맞음)."""
    if not isinstance(x, dict):
        return ["칸이 dict가 아님"]
    keys = trade_calendar.SESSION_KEYS + (("date",) if special else ())
    bad = [f"{k} 빠짐" for k in keys if k not in x]
    if bad:
        return bad
    if not trade_calendar.official_url(x["source_url"]):
        bad.append("주소가 https · krx.co.kr 공식 주소가 아님")
    if not re.fullmatch(r"[0-9a-f]{64}", str(x["raw_sha256"] or "")):
        bad.append("raw_sha256 꼴")
    o, c = x.get("open"), x.get("close")
    if not (isinstance(o, str) and isinstance(c, str) and re.fullmatch(r"([01]\d|2[0-3])[0-5]\d", o)
            and re.fullmatch(r"([01]\d|2[0-3])[0-5]\d", c) and o < c):
        bad.append("개장 · 마감 꼴")
    if _day(str(x["verified_from"] or "")) is None or not re.fullmatch(r"\d{8}", str(x["verified_from"] or "")):
        bad.append("확인한 날(verified_from) 꼴")
    if x["source_effective_from"] is not None and (_day(str(x["source_effective_from"])) is None
                                                   or not re.fullmatch(r"\d{8}", str(x["source_effective_from"]))):
        bad.append("원천 시행 날(source_effective_from) 꼴")
    if x["notice_no"] is not None and not isinstance(x["notice_no"], str):
        bad.append("공지 번호 꼴")
    if special and not (re.fullmatch(r"\d{8}", str(x["date"] or "")) and str(x["date"])[:4] == f"{int(year):04d}"
                        and _day(str(x["date"])) is not None):
        bad.append("날 꼴(그 해의 날이 아님)")
    return bad


def _review_problems(r):
    """특수 세션 예외 공지 검토 영수증 꼴 문제(비면 맞음): reviewed_through(YYYYMMDD) · verified_at(글) · reviewer(글) · method(글) ·
    sources(목록 · 칸마다 url(https) · fetched_at_utc(글) · raw_sha256(64자 또는 null) · what(글))."""
    if not isinstance(r, dict):
        return ["dict가 아님"]
    bad = [f"{k} 빠짐" for k in ("reviewed_through", "verified_at", "reviewer", "method", "sources") if k not in r]
    if bad:
        return bad
    if _day(str(r["reviewed_through"] or "")) is None or not re.fullmatch(r"\d{8}", str(r["reviewed_through"] or "")):
        bad.append("reviewed_through 꼴")
    for k in ("verified_at", "reviewer", "method"):
        if not (isinstance(r[k], str) and r[k].strip()):
            bad.append(f"{k} 빔")
    src = r["sources"]
    if not isinstance(src, list) or not src:
        bad.append("sources가 빈 목록")
    else:
        for i, x in enumerate(src):
            if not (isinstance(x, dict) and str(x.get("url", "")).startswith("https://") and isinstance(x.get("fetched_at_utc"), str)
                    and isinstance(x.get("what"), str) and (x.get("raw_sha256") is None or re.fullmatch(r"[0-9a-f]{64}", str(x["raw_sha256"])))):
                bad.append(f"sources[{i}] 꼴")
    return bad


def review_digest(review):
    """검토 영수증 sha256(열쇠 차례 · 빈칸 없는 JSON · UTF-8) — 판 지문 · ARMED 세션 검토 영수증이 이 값을 묶음."""
    return _sha(json.dumps(review, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_overlay(year, folder=None):
    """세션 overlay → (본문 또는 None, 파일 sha256 또는 None). 파일이 없으면 (None, None) · 깨졌거나 꼴이 이상하면 CalendarError
    (사람이 적은 공식 원천 목록이 틀렸으면 조용히 넘기지 않고 판을 쓰지 않음)."""
    p = overlay_path(year, folder)
    try:
        raw = p.read_bytes()
    except FileNotFoundError:
        return None, None
    except OSError as e:
        raise CalendarError(f"세션 overlay를 못 읽음 · {type(e).__name__}") from None
    sha = _sha(raw)
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise CalendarError(f"세션 overlay {p.name}가 JSON이 아님") from None
    bad = []
    if not isinstance(body, dict) or body.get("kind") != OVERLAY_KIND or str(body.get("year")) != f"{int(year):04d}":
        bad.append("kind · year가 다름")
    else:
        if body.get("regular") is not None:
            bad += [f"regular {w}" for w in _entry_problems(body["regular"], year, False)]
        special = body.get("special", [])
        if not isinstance(special, list):
            bad.append("special이 목록이 아님")
        else:
            seen = set()
            for i, x in enumerate(special):
                bad += [f"special[{i}] {w}" for w in _entry_problems(x, year, True)]
                d = x.get("date") if isinstance(x, dict) else None
                if d in seen:
                    bad.append(f"special 날 {d} 겹침")
                seen.add(d)
        unknown = body.get("unknown", [])
        if not isinstance(unknown, list) or not all(isinstance(d, str) and re.fullmatch(r"\d{8}", d) and d[:4] == f"{int(year):04d}"
                                                    and _day(d) is not None for d in unknown):
            bad.append("unknown 목록 꼴")
        if body.get("exceptions_review") is not None:
            bad += [f"exceptions_review {w}" for w in _review_problems(body["exceptions_review"])]
    if bad:
        raise CalendarError(f"세션 overlay {p.name} 꼴이 이상함 · " + " · ".join(bad[:5]))
    return body, sha


def fetch_source(url, get):
    """세션 원천 원문(바이트) — 공식 주소(https · krx.co.kr)만 · HTTP 200만 · 다른 곳으로 옮겨 간(redirect) 응답은 안 받음.
    아니면 CalendarError."""
    if not trade_calendar.official_url(url):
        raise CalendarError("세션 원천 주소가 https · krx.co.kr 공식 주소가 아님")
    try:
        r = get(url, headers={"User-Agent": AGENT}, timeout=(10, 30))
    except Exception as e:
        raise CalendarError(f"세션 원천 조회 실패 · {type(e).__name__}") from None
    code = getattr(r, "status_code", None)
    if code != 200:
        raise CalendarError(f"세션 원천 조회 실패 · HTTP {code}")
    final = getattr(r, "url", None)
    if final is not None and not trade_calendar.official_url(final):
        raise CalendarError("세션 원천이 공식 주소 밖으로 옮겨 감(redirect)")
    return bytes(r.content)


class _Rows(HTMLParser):
    """표의 줄마다 (머리 칸 글 목록, 값 칸 글 목록) — th · td 안의 글만(줄바꿈 · 공백은 한 칸으로 · &middot; 같은 글자 참조는 풂)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = ([], [])
        elif tag in ("th", "td") and self.row is not None:
            self.cell = (tag, [])
        elif tag == "br" and self.cell is not None:
            self.cell[1].append(" ")

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None and self.row is not None:
            self.row[0 if self.cell[0] == "th" else 1].append(re.sub(r"\s+", " ", "".join(self.cell[1])).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row, self.cell = None, None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[1].append(data)


def regular_hours(raw):
    """KRX 공식 정규장 시간 안내 원문 → ("HHMM", "HHMM") 개장 · 마감. 표 머리(구분 · 매매거래시간 · 호가접수시간)가 하나 ·
    머리 칸이 '정규장' 하나뿐인 줄이 하나 · 그 줄의 칸 수 = 표 머리 값 칸 수 · 매매거래시간 칸이 'HH:MM ~ HH:MM'이어야 함.
    아니면 CalendarError(표 꼴이 바뀌었으면 사람이 다시 읽고 overlay를 고침 · 시각을 짐작하지 않음)."""
    try:
        text = bytes(raw).decode("utf-8")
    except (UnicodeDecodeError, TypeError):
        raise CalendarError("평소 세션 원문이 UTF-8 글이 아님") from None
    p = _Rows()
    try:
        p.feed(text)
        p.close()
    except Exception:                                   # html.parser는 거의 안 던지지만 꼴이 아주 깨졌으면 실패로
        raise CalendarError("평소 세션 원문 표를 읽지 못함") from None
    heads = [th for th, _ in p.rows if REGULAR_COL in th and ORDER_COL in th]
    if len(heads) != 1:
        raise CalendarError(f"평소 세션 원문에 '{REGULAR_COL} · {ORDER_COL}' 표 머리가 {len(heads)}개(하나여야 함)")
    cols = [h for h in heads[0] if h in (REGULAR_COL, ORDER_COL)]
    rows = [td for th, td in p.rows if th == [REGULAR_ROW]]
    if len(rows) != 1:
        raise CalendarError(f"평소 세션 원문에 '{REGULAR_ROW}' 줄이 {len(rows)}개(하나여야 함)")
    if len(rows[0]) != len(cols):
        raise CalendarError(f"평소 세션 원문의 '{REGULAR_ROW}' 줄 칸 수 {len(rows[0])}가 표 머리 {len(cols)}과 다름")
    cell = rows[0][cols.index(REGULAR_COL)]
    m = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)\s*~\s*([01]\d|2[0-3]):([0-5]\d)", cell)
    if not m:
        raise CalendarError(f"평소 세션 원문의 '{REGULAR_ROW}' {REGULAR_COL} 칸이 'HH:MM ~ HH:MM' 꼴이 아님 · {cell[:30]!r}")
    o, c = m.group(1) + m.group(2), m.group(3) + m.group(4)
    if not o < c:
        raise CalendarError(f"평소 세션 원문의 '{REGULAR_ROW}' 개장 {o}이 마감 {c}보다 늦음")
    return o, c


def regular_check(entry):
    """평소 세션 overlay 칸 → 원문 검사 함수(원문 → '' 맞음 · 까닭). 원문 표에서 읽은 개장 · 마감 = overlay의 개장 · 마감이어야 함."""
    def check(raw):
        try:
            o, c = regular_hours(raw)
        except CalendarError as e:
            return str(e)
        if (o, c) != (entry.get("open"), entry.get("close")):
            return f"공식 원문 표의 정규장 {o} ~ {c}이 overlay에 적힌 {entry.get('open')} ~ {entry.get('close')}과 다름"
        return ""
    return check


def verify_receipt(entry, get, now=None, raws=None, name=None, check=None):
    """overlay 한 칸 → 주소를 받아 원문 sha256이 적힌 값과 같고 · check(원문)가 ''이면(평소 세션: 원문 표 시각 = overlay 시각)
    (영수증, '') · 아니면 (None, 까닭). 영수증 = 날(특수) + 세션 영수증 핵심 칸 + 받은 시각. 받은 원문은 raws[name]에 남김(마른 실행 artifact)."""
    try:
        raw = fetch_source(entry["source_url"], get)
    except CalendarError as e:
        return None, str(e)
    if raws is not None and name:
        raws[name] = raw
    got = _sha(raw)
    if got != entry["raw_sha256"]:
        return None, f"원문 sha256 {got[:16]}이 overlay에 적힌 {str(entry['raw_sha256'])[:16]}과 다름"
    why = check(raw) if check is not None else ""
    if why:
        return None, why
    rec = {"date": entry["date"]} if "date" in entry else {}
    rec.update({k: entry.get(k) for k in trade_calendar.SESSION_KEYS})
    rec["fetched_at_utc"] = _utc(now)
    return rec, ""


def plan_sessions(year, trading, overlay, get, now=None, raws=None, known=None):
    """그해 거래일(trading · 날 차례)마다 세션 칸 → (sessions, {날: days 칸}). 평소 세션 영수증을 못 얻으면 CalendarError
    (판을 새로 쓰지 않음 · 옛 판 유지). 특수 세션은 원천이 확인된 날만 · 나머지 의심 날은 unknown(시각을 지어내지 않음)."""
    reg_entry = (overlay or {}).get("regular")
    if not reg_entry:
        raise CalendarError(f"평소 세션 원천 영수증이 없음(calendar/sessions-{int(year):04d}.json의 regular — KRX 공식 정규장 시간 안내 "
                            "주소 · 원문 sha256 · 개장 · 마감)")
    reg, why = verify_receipt(reg_entry, get, now, raws, "regular-session", check=regular_check(reg_entry))
    if reg is None:
        raise CalendarError(f"평소 세션 원천을 확인하지 못함 · {why}")
    review = (overlay or {}).get("exceptions_review")
    if not review:
        raise CalendarError(f"특수 세션 예외 공지 검토 영수증이 없음(calendar/sessions-{int(year):04d}.json의 exceptions_review — 검토한 끝 날 · "
                            "검토자 · 방법 · 근거)")
    through = review["reviewed_through"]
    floor = trade_calendar.regular_floor(reg)
    tset = set(trading)
    special, failed = {}, {}
    for x in overlay.get("special") or []:
        if x["date"] not in tset:
            raise CalendarError(f"세션 overlay의 특수 세션 날 {x['date']}이 거래일이 아님(휴장 원천과 어긋남)")
        rec, why = verify_receipt(x, get, now, raws, f"special-{x['date']}")
        if rec is None:
            failed[x["date"]] = why
        else:
            special[x["date"]] = rec
    known = known_special() if known is None else known
    watch = set(overlay.get("unknown") or [])
    first = trading[0] if trading else None
    entries, unknown = {}, []
    for d in trading:
        if d > through:                                            # 3단계 고침: 예외 공지 검토 지평 뒤는 특수 세션이 확인돼도 unknown
            entries[d] = {"session": "unknown"}
            unknown.append({"date": d, "why": f"특수 세션 예외 공지 검토 지평({through}) 뒤"})
            continue
        if d in special:
            entries[d] = {"open": special[d]["open"], "close": special[d]["close"], "session": "special"}
            continue
        if d in failed:
            why = f"overlay 특수 세션 원천 확인 실패 · {failed[d]}"
        elif d in watch:
            why = "overlay unknown 목록(공식 공지 기다림)"
        elif d in known:
            why = f"봇 특수 세션 목록(SPECIAL_HOURS · {known[d]})에 있는데 확인된 공식 overlay가 없음"
        elif d == first:
            why = "새해 첫 거래일(늦게 여는 날)인데 확인된 공식 overlay가 없음"
        elif d < floor:
            why = f"평소 세션 적용 하한({floor} = max(확인한 날 verified_from, 원천 시행 날 source_effective_from)) 앞"
        else:
            why = ""
        if why:
            entries[d] = {"session": "unknown"}
            unknown.append({"date": d, "why": why})
        else:
            entries[d] = {"open": reg["open"], "close": reg["close"]}
    exceptions = {"reviewed_through": through, "review_sha256": review_digest(review), "reviewer": review["reviewer"],
                  "verified_at": review["verified_at"]}
    sessions = {"regular": reg, "special": [special[d] for d in sorted(special) if d <= through], "unknown": unknown,
                "exceptions": exceptions, "note": SESSION_NOTE}       # 지평 밖 특수 영수증은 판에 안 넣음(그날은 unknown)
    return sessions, entries


# ───────────────────────── 대조 · 판 쓰기 ─────────────────────────

def trading_days(year, krx_off, kis_open):
    """두 원천 → (거래일 목록(날 차례), 다른 날 [(날, KRX 거래일?, KIS 거래일?)])."""
    trading, diff = [], []
    for d in year_days(year):
        krx = _day(d).weekday() < 5 and d not in krx_off
        kis = kis_open.get(d) == "Y"
        if krx != kis:
            diff.append((d, krx, kis))
        if krx:
            trading.append(d)
    return trading, diff


def next_version(year, days, sessions, folder=None):
    """→ (새 판 번호 또는 None(같은 내용), 정규화 지문, 문장)."""
    sha = trade_calendar.normalized_digest(days, sessions)
    found = trade_calendar.versions(year, folder)
    if found:
        try:
            last = json.loads(Path(found[0][1]).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            last = None
        if isinstance(last, dict) and last.get("normalized_sha256") == sha and isinstance(last.get("days"), dict) \
                and trade_calendar.normalized_digest(last["days"], last.get("sessions")) == sha:
            return None, sha, f"{year}년: 가장 큰 판 v{found[0][0]}과 같은 내용 → 새 판 없음"
    return (found[0][0] + 1 if found else 1), sha, ""


def write_version(year, days, meta, folder=None, dry=False, rec=None):
    """새 판을 씀 → (경로 또는 None, 문장). 같은 내용(그해 가장 큰 판의 정규화 지문과 같음)이면 쓰지 않음 · 옛 판은 덮지 않음.
    dry면 검증까지만 하고 쓰지 않음(rec에 만들 판 번호 · 같은 판 번호를 적음)."""
    folder = Path(folder) if folder is not None else FOLDER
    rec = {} if rec is None else rec
    n, sha, msg = next_version(year, days, meta.get("sessions"), folder)
    body = dict(meta)
    body.update(normalized_sha256=sha, days=days)
    missing = [k for k in trade_calendar.FIELDS if k not in body]
    if missing or not trade_calendar._valid_days(days, year) or not trade_calendar._valid_sessions(body["sessions"], days, year):
        raise CalendarError(f"{year}년 판 꼴이 맞지 않음 · 빠진 칸 {missing}")
    off = sum(1 for d, v in days.items() if v is None and _day(d).weekday() < 5)
    unknown = sum(1 for v in days.values() if isinstance(v, dict) and v.get("session") == "unknown")
    special = sum(1 for v in days.values() if isinstance(v, dict) and v.get("session") == "special")
    if n is None:
        found = trade_calendar.versions(year, folder)
        rec["same_as"] = found[0][0] if found else None
        return None, msg
    rec["version"] = n
    if dry:
        return None, (f"{year}년: 새 판 v{n}을 만들 수 있음(마른 실행 · 쓰지 않음) · 평소 휴장 {off}일 · 특수 세션 {special}일 · "
                      f"세션 unknown {unknown}일 · 정규화 지문 {sha[:12]}")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"krx-{int(year):04d}-v{n}.json"
    with open(path, "x", encoding="utf-8") as f:                 # 같은 이름이 있으면 실패(옛 판을 덮지 않음)
        f.write(json.dumps(body, ensure_ascii=False, indent=1) + "\n")
    back = trade_calendar.load_year(year, folder)
    if not back or back["version"] != n or back["sha256"] != sha:
        path.unlink()                                            # 방금 쓴 새 파일만 지움(옛 판은 그대로)
        raise CalendarError(f"{path.name}을 썼지만 다시 읽어 검증하지 못해 지움")
    return path, (f"{year}년: 새 판 v{n} · 평일 휴장 {off}일 · 특수 세션 {special}일 · 세션 unknown {unknown}일 · "
                  f"정규화 지문 {sha[:12]}")


def build_year(year, client, get=None, folder=None, now=None, dry=False, rec=None, known=None):
    """한 해: KRX → KIS → 날마다 대조 → 세션 영수증(overlay 주소를 받아 지문 확인) → 같으면 판 쓰기 → (경로 또는 None, 문장).
    실패는 CalendarError(아무것도 안 씀). rec(dict)에 원문 · 지문 · 다른 날 · unknown 날 · 만들 판 후보를 차례로 적음(마른 실행 요약)."""
    rec = {} if rec is None else rec
    rec.setdefault("raws", {})
    rec.setdefault("digests", {})
    if get is None:
        import requests
        get = requests.get
    raw, url = krx_fetch(year, get)
    rec["raws"]["krx-holidays.json"] = raw
    rec["digests"]["krx_raw_sha256"] = _sha(raw)
    krx_at = _utc(now)
    off = krx_holidays(raw, year)
    kis, kis_raw, calls = kis_fetch(client, year)
    kis_at = _utc(now)
    kis_sha = _sha(json.dumps(kis_raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    rec["digests"]["kis_raw_sha256"] = kis_sha
    trading, diff = trading_days(year, off, kis)
    rec["diff"] = [{"date": d, "krx_trading": a, "kis_trading": b} for d, a, b in diff]
    if diff:
        shown = " · ".join(f"{d} KRX {'거래' if a else '휴장'} / KIS {'거래' if b else '휴장'}" for d, a, b in diff[:5])
        raise CalendarError(f"두 원천이 다른 날 {len(diff)}개 · {shown}")
    overlay, overlay_sha = load_overlay(year, folder)
    rec["digests"]["overlay_sha256"] = overlay_sha
    sessions, entries = plan_sessions(year, trading, overlay, get, now, rec["raws"], known)
    sessions["overlay"] = overlay_path(year).name
    sessions["overlay_sha256"] = overlay_sha
    rec["unknown"] = sessions["unknown"]
    days = {d: entries.get(d) for d in year_days(year)}
    raw_sha = _sha(raw)
    meta = {"source_url": url, "notice_no": f"B125.bld · {int(year)} · 원문 sha256 {raw_sha[:16]}", "notice_name": KRX_NAME,
            "fetched_at_utc": krx_at, "effective_from": (now or datetime.now(timezone.utc)).astimezone(KST).strftime("%Y%m%d"),
            "parser_version": PARSER, "raw_sha256": raw_sha, "year": f"{int(year):04d}", "session_note": SESSION_NOTE,
            "secondary": {"name": KIS_NAME, "path": KIS_PATH, "tr_id": KIS_TR, "field": KIS_OPEN, "fetched_at_utc": kis_at,
                          "calls": calls, "agree_days": len(days), "raw_sha256": kis_sha},
            "sessions": sessions}
    candidate = dict(meta)
    candidate.update(normalized_sha256=trade_calendar.normalized_digest(days, sessions), days=days)
    rec["candidate"] = candidate
    rec["digests"]["normalized_sha256"] = candidate["normalized_sha256"]
    return write_version(year, days, meta, folder, dry=dry, rec=rec)


def write_dry(out, year, rec, get=None):
    """마른 실행 결과를 <out>/<해>/에 씀(원문 raw/ · summary.json · candidate.json) → 폴더. calendar/는 건드리지 않음."""
    base = Path(out) / f"{int(year):04d}"
    (base / "raw").mkdir(parents=True, exist_ok=True)
    raws = dict(rec.get("raws") or {})
    errors = []
    if "regular-session" not in raws and get is not None:      # 평소 세션 원천이 아직 고정되지 않음 → 사람이 읽고 적도록 후보 원문을 받아 둠
        for i, url in enumerate(REGULAR_CANDIDATES, 1):
            try:
                raws[f"regular-candidate-{i}"] = fetch_source(url, get)
            except CalendarError as e:
                errors.append(f"{url} · {e}")
    files = {}
    for name, b in sorted(raws.items()):
        (base / "raw" / name).write_bytes(b)
        files[name] = {"sha256": _sha(b), "bytes": len(b)}
        if name == "regular-session" or name.startswith("regular-candidate-"):
            try:                                                # 원문 표에서 읽은 정규장 시각(사람이 overlay에 옮겨 적을 값 · 대조용)
                files[name]["regular_hours"] = list(regular_hours(b))
            except CalendarError as e:
                files[name]["regular_hours_error"] = str(e)
    cand = rec.get("candidate")
    summary = {"kind": "calendar-dry-run", "year": f"{int(year):04d}", "parser_version": PARSER, "generated_at_utc": _utc(),
               "ok": not rec.get("error"), "error": rec.get("error"), "message": rec.get("message"),
               "would_write_version": rec.get("version"), "same_as_version": rec.get("same_as"),
               "normalized_sha256": cand.get("normalized_sha256") if cand else None, "digests": rec.get("digests") or {},
               "raw_files": files, "unknown": rec.get("unknown"), "diff": rec.get("diff"),
               "regular_candidates": list(REGULAR_CANDIDATES) if "regular-session" not in raws else [],
               "regular_candidate_errors": errors}
    (base / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if cand:
        (base / "candidate.json").write_text(json.dumps(cand, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for name, f in files.items():                               # 작업 기록에도 원문 요약(artifact를 못 받는 곳에서 대조 · 본문은 안 찍음)
        hours = f.get("regular_hours")
        extra = (f" · 원문 표 정규장 {hours[0]} ~ {hours[1]}" if hours else
                 (f" · 원문 표 못 읽음({f['regular_hours_error']})" if "regular_hours_error" in f else ""))
        print(f"마른 실행 원문 · {int(year):04d} · {name} · sha256 {f['sha256']} · {f['bytes']}바이트{extra}")
    print(f"마른 실행 요약 · {int(year):04d} · 만들 판 {summary['would_write_version']} · 같은 판 {summary['same_as_version']} · "
          f"정규화 지문 {summary['normalized_sha256']} · 세션 unknown {len(summary['unknown'] or [])}일 · "
          f"후보 주소 오류 {len(errors)}개" + (f" · {errors[0]}" if errors else ""))
    return base


def default_years(now=None):
    today = now or datetime.now(KST)
    return [today.year] + ([today.year + 1] if today.month == 12 else [])


def check(folder=None):
    """작업 흐름 커밋 앞: calendar/의 해마다 가장 큰 판이 trade_calendar로 읽히는지(꼴 · 지문) → 0 맞음 · 1 틀림."""
    folder = Path(folder) if folder is not None else FOLDER
    years = sorted({m.group(1) for p in folder.glob("krx-*-v*.json") for m in [re.fullmatch(r"krx-(\d{4})-v\d+\.json", p.name)] if m})
    bad = [y for y in years if trade_calendar.load_year(y, folder) is None]
    for y in bad:
        print(f"⚠️ {y}년 가장 큰 판을 읽을 수 없음(꼴 · 지문)")
    if not bad:
        print("달력 판 확인 통과 · " + (" · ".join(f"{y} v{trade_calendar.load_year(y, folder)['version']}" for y in years) or "판 없음"))
    return 1 if bad else 0


def main(argv=None, client=None, get=None, folder=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["--check"]:
        return check(folder)
    dry, out, rest = False, None, []
    it = iter(argv)
    for a in it:
        if a == "--dry-run":
            dry = True
        elif a == "--out":
            out = next(it, None)
            if not out or out.startswith("--"):
                print("--out 뒤에 폴더를 주세요")
                return 1
        elif a.startswith("--out="):
            out = a.split("=", 1)[1]
        elif a.startswith("--"):
            print(f"모르는 선택 {a!r}")
            return 1
        else:
            rest.append(a)
    if dry != bool(out):
        print("마른 실행은 --dry-run과 --out <폴더>를 함께 줘야 합니다(하나만은 안 됨 · 실제 실행은 calendar/에만 씀)")
        return 1
    text = " ".join(rest).strip() or os.getenv("CAL_YEARS", "").strip()
    parts = [x for x in re.split(r"[,\s]+", text) if x] if text else []
    if any(not re.fullmatch(r"20\d\d", x) for x in parts):
        print(f"해는 네 자리(20xx)로 주세요 · {text!r}")
        return 1
    years = [int(x) for x in parts] or default_years()
    if dry and get is None:
        import requests
        get = requests.get
    if client is None:
        try:
            import broker_kis
            client = broker_kis.market()
        except Exception as e:
            print(f"⚠️ 증권사(시세용) 연결을 만들지 못해 달력 판을 쓰지 않음 · {type(e).__name__}")
            return 1
    bad = 0
    for y in years:
        rec = {}
        try:
            msg = build_year(y, client, get=get, folder=folder, dry=dry, rec=rec)[1]
            rec["message"] = msg
            print(msg)
        except CalendarError as e:
            bad += 1
            rec["error"] = str(e)
            print(f"⚠️ {y}년 달력 판을 쓰지 않음 · {e}")
        except OSError as e:
            bad += 1
            rec["error"] = type(e).__name__
            print(f"⚠️ {y}년 달력 판을 쓰지 못함 · {type(e).__name__}")
        if dry:
            try:
                print(f"마른 실행 결과 · {write_dry(out, y, rec, get).as_posix()}")
            except OSError as e:
                bad += 1
                print(f"⚠️ {y}년 마른 실행 결과를 쓰지 못함 · {type(e).__name__}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
