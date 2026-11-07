"""판 고정 거래 달력 읽기 · 검증(BOOST-0001-D 사전등록 판 3 §1.4 · D5 · 1단계: 읽기 · 검증만 · 만드는 도구는 다음 단계).
2a단계: last_days(D4 '최근 5거래일') · latest_done(수급 · 거래량 수집기 목표 날)을 더함 — 둘 다 같은 판만 읽음.
2b단계: next_day(빈칸 엔진 주 끝) · 판을 만드는 도구는 tools/build_calendar.py(1차 KRX 휴장일 · 2차 KIS 국내휴장일조회가 날마다 같을 때만 새 판).
2c단계(GPT 구현 검토 6705430244 §2-B · 세션을 지어내지 않음): 판마다 세션 영수증(sessions)이 있어야 읽힘 —
  평소 세션은 KRX 공식 정규장 시간 안내의 주소 · 원문 sha256 · 개장 · 마감, 특수 세션은 공지 주소 · 번호 · 시행 날 · 원문 sha256 · 개장 · 마감.
  세션 원천이 없는 거래일은 {"session": "unknown"}(개장 · 마감 없음) → day_info가 session = "unknown"을 돌려주고 문(gates)이 그날 새 위험 증가를 막음.

- 파일: calendar/krx-<해>-v<번호>.json. 공지가 바뀌면 새 번호 판을 더하고 옛 판은 덮지 않음 → 그 해의 **가장 큰 번호 판**만 씀
  (가장 큰 판이 깨졌거나 지문이 안 맞으면 작은 판으로 내려가지 않고 '못 정함' · 옛 공지로 조용히 돌아가지 않게).
- 칸(모두 있어야 함): source_url(원천 주소) · notice_no(공지 번호) · fetched_at_utc · effective_from(시행 날) · parser_version ·
  raw_sha256(원문 지문) · normalized_sha256(정규화 달력 지문) · days(날마다 개장 · 마감) · sessions(세션 영수증).
- days: {"YYYYMMDD": 값}. 값 = null(휴장) · {"open": "HHMM", "close": "HHMM"}(평소 세션 · 평소 영수증의 개장 · 마감과 같아야 함) ·
  {"open", "close", "session": "special"}(특수 세션 · 같은 날 특수 영수증과 같아야 함) · {"session": "unknown"}(거래일 · 세션 원천 없음).
  판에 없는 날은 '못 정함'(휴장으로 보지 않음).
- sessions: {"regular": 영수증, "special": [영수증 + "date"], ...설명 칸}. 영수증 = source_url(https · krx.co.kr 공식 주소) · notice_no ·
  effective_from · raw_sha256 · open · close(+ 받은 시각 등 설명 칸). 평소 세션은 effective_from 날부터만 씀(그 앞 거래일은 unknown이어야 함).
- 정규화 지문 = {"days": days, "sessions": 세션 영수증 핵심(받은 시각 · 설명 칸 뺌)}을 열쇠 차례 · 빈칸 없는 JSON(UTF-8)으로 만든 sha256 ·
  읽을 때마다 다시 셈해 파일에 적힌 값과 맞아야 씀(세션 영수증도 판 지문에 묶임).
- 1차 권위는 KRX 공식 공지(판) · 2차 대조(실시간 API의 앞 거래일)는 호출부가 넘긴 값과 견주기만 함(cross_check).
  어느 쪽도 다른 쪽을 조용히 덮지 않음: 못 정하거나 다르면 호출부가 모든 활성 판단의 새 위험 증가를 막음.
- 증권사 · 인터넷을 부르지 않음(저장소 안 파일만 읽음).
"""
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

FOLDER = Path("calendar")
FIELDS = ("source_url", "notice_no", "fetched_at_utc", "effective_from", "parser_version", "raw_sha256",
          "normalized_sha256", "days", "sessions")
SESSION_KEYS = ("source_url", "notice_no", "effective_from", "raw_sha256", "open", "close")    # 세션 영수증 핵심(판 지문에 들어감)
OFFICIAL_HOST = "krx.co.kr"                # 세션 원천은 한국거래소 공식 주소만(krx.co.kr · *.krx.co.kr · https)
_NAME = re.compile(r"krx-(\d{4})-v(\d+)\.json")
_HHMM = re.compile(r"([01]\d|2[0-3])[0-5]\d")
_SHA = re.compile(r"[0-9a-f]{64}")
BACK = 31                     # 앞 거래일(P)을 찾아 거꾸로 볼 날 수(이보다 길게 쉬는 장은 없음 · 못 찾으면 못 정함)


def official_url(url):
    """한국거래소 공식 주소인가(https · 호스트 krx.co.kr 또는 *.krx.co.kr)."""
    try:
        u = urlsplit(str(url))
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and (host == OFFICIAL_HOST or host.endswith("." + OFFICIAL_HOST))


def session_core(sessions):
    """판 지문에 넣는 세션 영수증 핵심: 평소 세션 + 특수 세션(날 차례) · 받은 시각 · 설명 칸은 뺌."""
    sessions = sessions if isinstance(sessions, dict) else {}
    reg = sessions.get("regular") if isinstance(sessions.get("regular"), dict) else {}
    special = [x for x in sessions.get("special") or [] if isinstance(x, dict)]
    rows = []
    for x in special:
        row = {"date": x.get("date")}
        row.update({k: x.get(k) for k in SESSION_KEYS})
        rows.append(row)
    return {"regular": {k: reg.get(k) for k in SESSION_KEYS}, "special": sorted(rows, key=lambda r: str(r["date"]))}


def normalized_digest(days, sessions):
    """정규화 달력 지문({"days": days, "sessions": 세션 영수증 핵심}을 열쇠 차례 · 빈칸 없는 JSON으로 → sha256)."""
    text = json.dumps({"days": days, "sessions": session_core(sessions)}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def versions(year, folder=None):
    """그 해 판 파일 [(번호, 경로)] — 큰 번호 먼저."""
    folder = Path(folder) if folder is not None else FOLDER
    out = []
    try:
        for p in folder.glob(f"krx-{int(year):04d}-v*.json"):
            m = _NAME.fullmatch(p.name)
            if m and int(m.group(1)) == int(year):
                out.append((int(m.group(2)), p))
    except (OSError, ValueError):
        return []
    return sorted(out, key=lambda x: -x[0])


def _hhmm_pair(v):
    o, c = v.get("open"), v.get("close")
    return isinstance(o, str) and isinstance(c, str) and bool(_HHMM.fullmatch(o)) and bool(_HHMM.fullmatch(c)) and o < c


def _real_day(k, year=None):
    if not (isinstance(k, str) and re.fullmatch(r"\d{8}", k)) or (year is not None and k[:4] != f"{int(year):04d}"):
        return False
    try:
        date(int(k[:4]), int(k[4:6]), int(k[6:]))
    except ValueError:
        return False
    return True


def _valid_days(days, year):
    """열쇠 = 그 해의 실제 날짜(YYYYMMDD) · 값 = null(휴장) · {"open", "close"}(평소) · {"open", "close", "session": "special"} ·
    {"session": "unknown"} (HHMM · 개장 < 마감). 세션 영수증과 맞는지는 _valid_sessions가 봄."""
    if not isinstance(days, dict) or not days:
        return False
    for k, v in days.items():
        if not _real_day(k, year):
            return False
        if v is None:
            continue
        if not isinstance(v, dict):
            return False
        if set(v) == {"open", "close"} or (set(v) == {"open", "close", "session"} and v.get("session") == "special"):
            if not _hhmm_pair(v):
                return False
        elif not (set(v) == {"session"} and v.get("session") == "unknown"):
            return False
    return True


def _receipt_ok(x, year=None, special=False):
    """세션 영수증 꼴: 공식 주소 · 원문 sha256 · 시행 날 · 개장 < 마감 · 공지 번호(글 또는 없음) · 특수면 그 해의 날."""
    if not isinstance(x, dict) or any(k not in x for k in SESSION_KEYS):
        return False
    if not official_url(x.get("source_url")) or not _SHA.fullmatch(str(x.get("raw_sha256") or "")):
        return False
    if not _real_day(x.get("effective_from")) or not _hhmm_pair(x):
        return False
    if x.get("notice_no") is not None and not isinstance(x.get("notice_no"), str):
        return False
    return not special or _real_day(x.get("date"), year)


def _valid_sessions(sessions, days, year):
    """세션 영수증과 days가 서로 맞는가 — 평소 꼴 날 = 평소 영수증의 개장 · 마감(시행 날부터) · 특수 꼴 날 = 같은 날 특수 영수증 하나 ·
    unknown 날 = 특수 영수증 없음 · 특수 영수증마다 그날이 특수 꼴(세션을 지어낸 판 · 영수증 없는 시각은 못 씀)."""
    if not isinstance(sessions, dict):
        return False
    reg, special = sessions.get("regular"), sessions.get("special")
    if not _receipt_ok(reg) or not isinstance(special, list):
        return False
    by_day = {}
    for x in special:
        if not _receipt_ok(x, year, special=True) or x["date"] in by_day:
            return False
        by_day[x["date"]] = x
    for k, v in days.items():
        if v is None:
            continue
        kind = v.get("session")
        if kind is None:
            if (v["open"], v["close"]) != (reg["open"], reg["close"]) or k < reg["effective_from"] or k in by_day:
                return False
        elif kind == "special":
            x = by_day.get(k)
            if x is None or (v["open"], v["close"]) != (x["open"], x["close"]):
                return False
        elif k in by_day:                                      # unknown인데 그날 특수 영수증이 있음(어긋남)
            return False
    return all(isinstance(days.get(k), dict) and days[k].get("session") == "special" for k in by_day)


def load_year(year, folder=None):
    """그 해의 가장 큰 번호 판을 읽고 검증 → {"year", "version", "path", "sha256", "days", "sessions", "meta"} 또는 None(못 씀)."""
    found = versions(year, folder)
    if not found:
        return None
    version, path = found[0]
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(body, dict) or any(k not in body for k in FIELDS):
        return None
    days, sessions = body.get("days"), body.get("sessions")
    if not _valid_days(days, year) or not _valid_sessions(sessions, days, year):
        return None
    sha = normalized_digest(days, sessions)
    if str(body.get("normalized_sha256")) != sha or not _SHA.fullmatch(str(body.get("raw_sha256") or "")):
        return None
    meta = {k: body.get(k) for k in FIELDS if k not in ("days", "sessions")}
    return {"year": f"{int(year):04d}", "version": version, "path": str(path), "sha256": sha, "days": days, "sessions": sessions,
            "meta": meta}


def session_of(cal, day):
    """판(load_year 결과)에서 그날 세션 → (갈래, 원천 sha256). 갈래 = None(휴장) · "regular" · "special" · "unknown"."""
    entry = cal["days"].get(day)
    if entry is None:
        return None, None
    kind = entry.get("session") or "regular"
    if kind == "regular":
        return kind, cal["sessions"]["regular"]["raw_sha256"]
    if kind == "special":
        got = [x for x in cal["sessions"]["special"] if x.get("date") == day]
        return kind, got[0]["raw_sha256"] if got else None
    return "unknown", None


def day_info(day, folder=None):
    """D의 달력 정보 → {"D", "trading", "open", "close", "session", "session_sha256", "P", "sha256", "version", "file",
    "p_sha256", "p_version", "p_file"} 또는 None(못 정함: 판 없음 · 지문 불일치 · 그 날이 판에 없음 · P를 찾다 판에 없는 날을 만남).
    P = D 앞 마지막 거래일(1월 첫 거래일이면 전해 판에서 찾음 · 그 판의 지문도 함께 돌려줌 · 세션이 unknown인 날도 거래일).
    session = None(휴장) · "regular" · "special" · "unknown"(세션 원천 없음 → open · close = None · 부르는 쪽이 새 위험 증가를 막음)."""
    try:
        day = str(day)
        d = date(int(day[:4]), int(day[4:6]), int(day[6:]))
    except (TypeError, ValueError):
        return None
    years = {day[:4]: load_year(day[:4], folder)}
    cur = years[day[:4]]
    if cur is None or day not in cur["days"]:
        return None
    entry = cur["days"][day]
    p, py = None, None
    for _ in range(BACK):
        d -= timedelta(days=1)
        k = d.strftime("%Y%m%d")
        if k[:4] not in years:
            years[k[:4]] = load_year(k[:4], folder)
        y = years[k[:4]]
        if y is None or k not in y["days"]:
            return None
        if y["days"][k] is not None:
            p, py = k, y
            break
    if p is None:
        return None
    kind, src = session_of(cur, day)
    return {"D": day, "trading": entry is not None, "open": entry.get("open") if entry else None,
            "close": entry.get("close") if entry else None, "session": kind, "session_sha256": src, "P": p,
            "sha256": cur["sha256"], "version": cur["version"], "file": cur["path"],
            "p_sha256": py["sha256"], "p_version": py["version"], "p_file": py["path"]}


def last_days(day, n, folder=None):
    """D 앞 거래일 n개(오래된 → 새 · 마지막 = P) — 판 고정 달력만으로(D4 '최근 5거래일').
    못 정하면 None(판 없음 · 지문 불일치 · 판에 없는 날을 만남 · 해가 바뀌면 전해 판도 있어야 함)."""
    try:
        day, n = str(day), int(n)
        d = date(int(day[:4]), int(day[4:6]), int(day[6:]))
    except (TypeError, ValueError):
        return None
    if n < 1:
        return None
    years, out = {}, []
    for _ in range(BACK * n):
        d -= timedelta(days=1)
        k = d.strftime("%Y%m%d")
        if k[:4] not in years:
            years[k[:4]] = load_year(k[:4], folder)
        y = years[k[:4]]
        if y is None or k not in y["days"]:
            return None
        if y["days"][k] is not None:
            out.append(k)
            if len(out) == n:
                return out[::-1]
    return None


def next_day(day, folder=None):
    """D 다음 거래일 — 판 고정 달력만으로(2b단계 · 빈칸 엔진 '주 끝' 판단). 해를 넘기면 다음 해 판도 있어야 함.
    못 정하면 None(판 없음 · 지문 불일치 · 판에 없는 날을 만남 · BACK일 안에 거래일 없음 → 부르는 쪽은 예전 방식)."""
    try:
        day = str(day)
        d = date(int(day[:4]), int(day[4:6]), int(day[6:]))
    except (TypeError, ValueError):
        return None
    years = {}
    for _ in range(BACK):
        d += timedelta(days=1)
        k = d.strftime("%Y%m%d")
        if k[:4] not in years:
            years[k[:4]] = load_year(k[:4], folder)
        y = years[k[:4]]
        if y is None or k not in y["days"]:
            return None
        if y["days"][k] is not None:
            return k
    return None


def latest_done(today, folder=None):
    """수집기 목표 날(D4 수급 · D7 거래량): today(한국 날짜 YYYYMMDD) 앞 마지막 거래일 = 장이 끝나 자료가 다 나왔을 가장 늦은 거래일(P).
    밤(자정 뒤)에 도는 수집이면 바로 그날 장, 자정 전에 돌면 그 앞 거래일(예전 '실행 시각의 어제'와 같은 날).
    판 고정 달력으로 못 정하면 None(부르는 쪽은 예전 방식 그대로 · 수집을 멈추지 않음)."""
    info = day_info(today, folder=folder)
    return info["P"] if info else None


def cross_check(info, live_p):
    """2차 대조: 호출부가 실시간 API로 얻은 앞 거래일(live_p)과 달력 P가 같은가 → (같음, 까닭). 견주기만 하고 아무것도 덮지 않음."""
    if not info:
        return False, "판 고정 달력으로 앞 거래일을 못 정함"
    if not live_p:
        return False, "증권사에서 앞 거래일을 못 받아 달력과 견주지 못함"
    if str(live_p) != str(info.get("P")):
        return False, f"달력 앞 거래일 {info.get('P')}와 증권사 앞 거래일 {live_p}가 다름"
    return True, ""
