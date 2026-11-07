"""공시 제목을 날짜와 함께 모읍니다.

숫자로 된 실적은 분기마다 한 번뿐이지만, 공시는 수시로 납니다. 유상증자가
결정된 날, 자사주를 사기로 한 날, 최대주주가 바뀐 날은 그날 시장이 처음
아는 일입니다. 급락 뒤 반등을 가를 만한 것이 여기 있을 수 있습니다.

제목만 모읍니다. 본문은 종목당 수십 MB라 받지 않습니다. 제목에 들어 있는
말로 갈래를 나눕니다.

BOOST-0001-D D3(사전등록 판 3 §1.2 · 2b단계): 시장 전체 목록은 쪽 완결성(status · page_no · total_count · total_page)을 보고
끝 쪽까지 다 받았을 때만 저장합니다. 확인 수집은 공시 manifest(event-manifest/ · event_manifest.py)를 남깁니다.
2c단계(GPT 구현 검토 6705430244 §2-A): 확인 범위 = 바구니 입력 창 = t0의 앞 거래일 다음 달력일 ~ t0(event_manifest.query_window ·
판 고정 달력 · 예: 금요일 다음 t0가 월요일이면 토 ~ 월) — 주말 · 휴일 접수도 바구니가 t0 사건으로 읽으므로 같이 묻고 같이 지문에 묶습니다.
  python collect_events.py final [t0]  → D 아침 최종 확인(평일 08:20 · 10:20 · 12:20 · 첫 성공만 · 바구니 문을 여는 유일한 기록)
  EVENT_RECENT_DAYS=5 python collect_events.py → 19:20 정기(최근 5일 이어 받기 + 그날 t0 기록 manifest · 문은 안 엶)
  python collect_events.py verify       → 작업 흐름 저장 단계(git add 앞)에서 이 작업의 manifest와 자료 트리 지문이 맞는지
t0 · 오늘은 판 고정 달력(trade_calendar)과 한국 날짜로 정합니다(러너 UTC 날짜를 쓰지 않음).
"""
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import event_manifest
from providers import Official

OUT = Path("event-data")
FIRST = os.getenv("EVENT_FIRST", "20150101")
PAUSE = float(os.getenv("EVENT_PAUSE", "0.12"))
# 매일 이어 받기(2026-10-03 사용자 승인 · 분위기 점수를 운영 모양으로): 0이면 예전처럼 종목마다 처음부터.
RECENT = int(os.getenv("EVENT_RECENT_DAYS", "0") or 0)

# 제목에 이 말이 있으면 그 갈래로 봅니다. 위에 있는 것부터 맞춰 봅니다.
KINDS = (
    ("유상증자", ("유상증자",)),
    ("무상증자", ("무상증자",)),
    ("전환사채", ("전환사채", "신주인수권부사채", "교환사채")),
    ("자사주취득", ("자기주식취득",)),
    ("자사주처분", ("자기주식처분", "자기주식소각")),
    ("최대주주변경", ("최대주주변경", "최대주주 변경")),
    ("공급계약", ("공급계약", "수주")),
    # 잠정실적(공정공시)은 정식 분기 보고서보다 3주쯤 먼저 나오는 실적 발표입니다. 제목이 '영업(잠정)실적'이라
    # 아래 '영업실적'에 안 걸려 빠져 있었습니다(2026-10-02). 실적 발표 날로 따로 둡니다.
    ("잠정실적", ("(잠정)실적", "잠정실적")),
    ("실적공시", ("영업실적", "매출액또는손익", "결산실적")),
    ("배당", ("현금·현물배당", "배당결정")),
    ("감자", ("감자",)),
    ("소송", ("소송",)),
    ("관리종목", ("관리종목", "상장폐지", "거래정지")),
    # 2026-10-02 DART 찔러 보기(probe_dart_more.py)에서 찾은, 위 어디에도 안 걸려 빠져 있던 갈래들.
    # 위 갈래의 분류는 바꾸지 않으려고 맨 뒤에 둡니다(이미 걸리는 제목은 위에서 먼저 잡힘).
    ("주식소각", ("주식소각",)),                                   # '주식소각결정' — 주주에게 좋은 쪽(처분과 다름)
    ("기업설명회", ("기업설명회",)),                               # IR 개최 안내
    ("대량보유", ("주식등의대량보유",)),                           # 5% 보고(누가 · 늘었는지는 제목에 없음)
    ("임원소유", ("주요주주특정증권등소유상황", "주요주주특정증권등거래계획")),
    ("최대주주지분변동", ("최대주주등소유주식변동",)),
    ("조회공시", ("조회공시", "풍문또는보도")),
    ("시설투자", ("신규시설투자",)),
    ("생산중단", ("생산중단",)),
    ("생산재개", ("생산재개",)),
    ("경영전망", ("장래사업", "경영계획")),
    ("주식매수선택권", ("주식매수선택권",)),
)


def kind_of(title):
    flat = re.sub(r"\s+", "", title or "")
    for name, marks in KINDS:
        if any(re.sub(r"\s+", "", m) in flat for m in marks):
            return name
    return None


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("EVENT_CODES", "").split(",") if c.strip()]
    if picked:
        return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]
    found = []
    # 앱 종목(universe.json)과 1시간봉 연구 종목(hourly-data/universe.json)을 함께 받습니다(2026-09-30: 1시간봉 종목 절반이 빠져 있었음).
    for source in ("universe.json", "hourly-data/universe.json"):
        try:
            chosen = json.loads(Path(source).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for c in chosen.get("codes", []):
            if re.fullmatch(r"[0-9]{6}", str(c)) and str(c) not in found:
                found.append(str(c))
    if found:
        return found
    return sorted(p.stem for p in Path("public-data").glob("*.json")
                  if re.fullmatch(r"[0-9]{6}", p.stem))


def gather(provider, corp, begin, end):
    """한 구간의 공시 제목을 모두 받아옵니다. 여러 쪽으로 나뉘어 옵니다."""
    found, page = [], 1
    for _ in range(40):
        answer = provider.dart("list.json", corp_code=corp, bgn_de=begin, end_de=end,
                               page_no=page, page_count=100, sort="date", sort_mth="asc")
        if not answer:
            break
        rows = answer.get("list") or []
        for row in rows:
            kind = kind_of(row.get("report_nm"))
            if kind and re.fullmatch(r"[0-9]{8}", str(row.get("rcept_dt", ""))):
                found.append({"date": str(row["rcept_dt"]), "kind": kind,
                              "title": str(row.get("report_nm", ""))[:60]})
        total = int(answer.get("total_page") or 1)
        if page >= total or not rows:
            break
        page += 1
        time.sleep(PAUSE)
    return found


# ───────────────────────── BOOST-0001-D D3: 쪽 완결성 · 날짜 확인 수집 · manifest ─────────────────────────
# OpenDART 공시검색 안내(opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001 · 2026-11-07 읽음):
#   응답 칸 status · message · page_no · page_count · total_count(총 건수) · total_page(총 페이지 수) · list[](rcept_no · rcept_dt …).
#   '메시지 설명': 000 정상 · 013 조회된 데이타가 없습니다 · 010 · 011 · 012 · 014 · 020 · 021 · 100 · 101 · 800 · 900 · 901은 오류.
#   → 013은 오류가 아니라 '조회 결과 0건'을 알리는 정보 코드라, **첫 쪽 013 = 정상 0건**(total_count 0 · total_page 0)으로 받아
#     manifest ok가 될 수 있게 함. 둘째 쪽부터 013이면 앞 쪽이 말한 쪽 수보다 일찍 끊긴 것이라 실패.
#   800(시스템 점검) · 900(정의되지 않은 오류) · 연결 오류만 잠깐 쉬고 다시 물음(retry_count) · 나머지 오류 status는 바로 실패.
PAGE_COUNT = event_manifest.QUERY["page_count"]          # 문과 같은 물음 칸(질의 지문)
MAX_PAGES = 500
OK_STATUS, NO_DATA = "000", "013"
AGAIN = ("800", "900")
RETRIES = 2
RETRY_WAIT = float(os.getenv("EVENT_RETRY_WAIT", "5"))
MANIFEST = Path("event-manifest")
KST = ZoneInfo("Asia/Seoul")


class Incomplete(RuntimeError):
    """공시 목록을 끝 쪽까지 다 받지 못함(쪽 빠짐 · 오류 status · 빈 응답 · 칸이 어긋남) → 받은 것도 저장하지 않음."""


def kst_today():
    """오늘 한국 날짜(YYYYMMDD) — 러너의 UTC 날짜를 쓰지 않음(08:20 한국 시각은 UTC로 전날 23:20)."""
    return datetime.now(KST).strftime("%Y%m%d")


def _int(x):
    try:
        return int(str(x).strip())
    except (TypeError, ValueError):
        return None


def _page(provider, params):
    """한 쪽 응답 본문. provider.dart_raw(OpenDART 본문 그대로)를 씀 · 없으면 예전 provider.dart를 본문 꼴로 되돌림
    (예전 꼴: '000'이면 본문 · '013'이면 None · 나머지 status는 예외)."""
    raw = getattr(provider, "dart_raw", None)
    if callable(raw):
        return raw("list.json", **params)
    ans = provider.dart("list.json", **params)
    if ans is None:
        return {"status": NO_DATA, "message": "조회된 데이타가 없습니다."}
    if isinstance(ans, dict) and "status" not in ans:
        return {"status": OK_STATUS, **ans}
    return ans


def fetch_list(provider, begin, end):
    """OpenDART 공시검색(시장 전체 · 종목 지정 없음)을 begin ~ end로 끝 쪽까지 받음 → (줄 목록, 기록 칸).
    쪽마다 status · page_no · total_count · total_page를 보고 하나라도 어긋나면 complete = False(까닭 why) · 줄 목록은 빈 것(쓰지 않음).
    끝까지 받았어도 pages_received == total_page · 받은 줄 수 == total_count · 접수번호 겹침 없음이어야 complete."""
    base = {"bgn_de": begin, "end_de": end, "page_count": PAGE_COUNT, "sort": event_manifest.QUERY["sort"],
            "sort_mth": event_manifest.QUERY["sort_mth"]}
    info = {"query_begin": begin, "query_end": end, "request_started_at_utc": event_manifest.utc_now(),
            "response_received_at_utc": [], "pages": [], "status": None, "total_count": None, "total_page": None,
            "pages_received": 0, "rows_received": 0, "retry_count": 0, "complete": False, "why": ""}
    rows, seen, twice = [], set(), 0
    page = 1
    while True:
        if page > MAX_PAGES:
            info["why"] = f"쪽 수가 {MAX_PAGES}을 넘음"
            break
        ans, err, status = None, None, None
        for turn in range(RETRIES + 1):
            try:
                ans, err = _page(provider, dict(base, page_no=page)), None
            except Exception as e:                     # 연결 · HTTP · 형식 오류(키 · 응답 본문은 찍지 않음)
                ans, err = None, type(e).__name__
            status = str(ans["status"]) if isinstance(ans, dict) and ans.get("status") is not None else None
            if err is None and status not in AGAIN:
                break
            if turn < RETRIES:
                info["retry_count"] += 1
                time.sleep(RETRY_WAIT)
        when = event_manifest.utc_now()
        info["response_received_at_utc"].append(when)
        entry = {"page_no": page, "status": status, "total_count": None, "total_page": None, "rows": 0,
                 "response_received_at_utc": when}
        info["pages"].append(entry)
        if err is not None:
            entry["error"] = err
            info["status"], info["why"] = "응답 없음", f"{page}쪽 응답을 못 받음({err})"
            break
        if status is None:
            info["status"], info["why"] = "빈 응답", f"{page}쪽 빈 응답(status 없음)"
            break
        if status == NO_DATA:
            if page == 1:                              # 정상 0건(위 안내 근거)
                info.update(status=NO_DATA, total_count=0, total_page=0, complete=True)
            else:
                info["status"] = status
                info["why"] = f"{page}쪽에서 '조회된 데이터 없음'(013) — 첫 쪽이 말한 {info['total_page']}쪽보다 일찍 끊김"
            break
        if status != OK_STATUS:
            info["status"], info["why"] = status, f"{page}쪽 오류 status {status}"
            break
        no, tc, tp, got = _int(ans.get("page_no")), _int(ans.get("total_count")), _int(ans.get("total_page")), ans.get("list")
        entry.update(total_count=tc, total_page=tp)
        if no != page or tc is None or tp is None or tc < 0 or tp < 0:
            info["status"], info["why"] = status, f"{page}쪽 page_no · total_count · total_page 칸이 이상함"
            break
        if page == 1:
            info["total_count"], info["total_page"] = tc, tp
            if tc == 0 and tp == 0 and got == []:      # '000'인데 0건으로 답한 경우도 정상 0건
                info.update(status=OK_STATUS, complete=True)
                break
        elif (tc, tp) != (info["total_count"], info["total_page"]):
            info["why"] = f"{page}쪽 총 건수 · 총 쪽 수({tc} · {tp})가 첫 쪽({info['total_count']} · {info['total_page']})과 다름"
            break
        if not isinstance(got, list) or not got or not all(isinstance(r, dict) for r in got):
            info["why"] = f"{page}쪽 목록(list)이 비었거나 꼴이 이상함"
            break
        entry["rows"] = len(got)
        info["pages_received"] += 1
        for row in got:
            key = row.get("rcept_no")
            if key is not None:
                twice += key in seen
                seen.add(key)
            rows.append(row)
        info["rows_received"] = len(rows)
        if page >= tp:
            break
        page += 1
        time.sleep(PAUSE)
    if not info["why"] and not info["complete"]:
        info["status"] = OK_STATUS
        if info["pages_received"] != info["total_page"]:
            info["why"] = f"받은 쪽 {info['pages_received']} ≠ 총 쪽 수 {info['total_page']}"
        elif info["rows_received"] != info["total_count"]:
            info["why"] = f"받은 줄 {info['rows_received']} ≠ 총 건수 {info['total_count']}"
        elif twice:
            info["why"] = f"접수번호가 겹친 줄 {twice}개(쪽이 밀림)"
        else:
            info["complete"] = True
    return (rows if info["complete"] else []), info


def _write_atomic(path, text):
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def merge(new, mark=None):
    """{코드: [사건 줄]}을 event-data/<코드>.json 뒤에 붙임(같은 (날, 갈래, 제목)은 한 번) → 새로 붙은 줄 수.
    mark가 있으면(최근 며칠 이어 받기) 예전처럼 그 파일을 다시 쓰고 'recent'를 적음 · 없으면(날짜 확인 수집) 새 줄이 있을 때만 씀."""
    OUT.mkdir(parents=True, exist_ok=True)
    added = 0
    for code, rows in sorted(new.items()):
        path = OUT / f"{code}.json"
        body = {"code": code, "fetched": "", "rows": []}
        if path.exists():
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        seen = {(r["date"], r["kind"], r["title"]): r for r in body.get("rows", [])}
        before = len(seen)
        for r in rows:
            seen[(r["date"], r["kind"], r["title"])] = r
        added += len(seen) - before
        if mark is None and len(seen) == before:
            continue
        body["rows"] = [seen[k] for k in sorted(seen)]
        if mark is not None:
            body["recent"] = mark
        _write_atomic(path, json.dumps(body, ensure_ascii=False))
    return added


def recent(provider, codes, days, today=None):
    """시장 전체 공시 목록(종목 지정 없음)에서 최근 days일 치만 받아 대상 종목 파일에 이어 붙입니다.
    종목마다 묻지 않아 하루 수십 번 조회로 끝납니다. 'fetched'(전체 수집 날)는 그대로 두고 'recent'만 적습니다.
    BOOST-0001-D D3: 빈 응답 · 오류 응답에서 조용히 멈추지 않고 쪽 완결성(fetch_list)을 봄 — 끝 쪽까지 다 받지 못하면 받은 것도
    저장하지 않고 Incomplete를 올림(작업 실패로 드러남) · 끝 날은 한국 날짜(러너 UTC 날짜 아님)."""
    want = set(codes)
    end = today or kst_today()
    begin = (date(int(end[:4]), int(end[4:6]), int(end[6:])) - timedelta(days=days)).strftime("%Y%m%d")
    found, info = fetch_list(provider, begin, end)
    if not info["complete"]:
        print(f"최근 {days}일 공시 목록을 끝 쪽까지 받지 못해 저장하지 않음 · {info['why']}")
        raise Incomplete(info["why"])
    new = {}
    for row in found:
        code = str(row.get("stock_code") or "").strip()
        kind = kind_of(row.get("report_nm"))
        if code in want and kind and re.fullmatch(r"[0-9]{8}", str(row.get("rcept_dt", ""))):
            new.setdefault(code, []).append({"date": str(row["rcept_dt"]), "kind": kind,
                                             "title": str(row.get("report_nm", ""))[:60]})
    added = merge(new, mark=end)
    print(f"최근 {days}일 · 시장 전체 {info['pages_received']}쪽 · 대상 종목 {len(new)} · 새 공시 {added}건")
    return added


def collect_day(provider, codes, t0, mode, day=None, folder=None, window=None, calendar_folder=None):
    """확인 범위(window = event_manifest.query_window(t0) · 안 주면 판 고정 달력으로 셈: t0의 앞 거래일 다음 달력일 ~ t0)를 끝 쪽까지
    묻고 · 대상 종목(목록 + 이미 파일이 있는 종목) 사건을 저장하고 · 저장된 event-data의 범위 안 사건 목록 지문 = 응답 지문인지 보고 ·
    manifest를 씀 → (본문, 경로). 범위 밖 접수일 줄이 하나라도 오면 실패(범위 안의 다른 날 · 주말 접수는 정상)."""
    want = set(codes) | {p.stem for p in OUT.glob("*.json") if re.fullmatch(r"[0-9]{6}", p.stem)}
    win = window if window is not None else event_manifest.query_window(t0, calendar_folder)
    rid, att = event_manifest.run_tag()
    body = {"kind": event_manifest.KIND, "version": event_manifest.VERSION, "mode": mode, "t0": t0, "D": day,
            "query_begin": win["begin"] if win else None, "query_end": t0, "window_before": win.get("before") if win else None,
            "calendar_sha256": win.get("calendar_sha256") if win else None, "request_started_at_utc": None,
            "response_received_at_utc": [], "status": None, "total_count": None, "total_page": None, "pages_received": 0,
            "rows_received": 0, "retry_count": 0, "pages": [], "normalized_query_digest": None, "normalized_event_digest": None,
            "events": 0, "t0_events": [], "stored_event_digest": None, "event_data_tree_digest": None,
            "GITHUB_RUN_ID": None if rid == "local" else rid, "GITHUB_RUN_ATTEMPT": None if rid == "local" else att,
            "GITHUB_WORKFLOW_SHA": os.getenv("GITHUB_WORKFLOW_SHA"), "persisted": False, "ok": False, "why": "",
            "completed_at_utc": None}
    complete, info = False, {"pages_received": 0, "total_page": None, "total_count": None}
    if not win or str(win.get("end")) != str(t0):
        body["why"] = f"판 고정 달력으로 t0 {t0}의 확인 범위(앞 거래일 다음 날 ~ t0)를 못 정함"
    else:
        begin, end = win["begin"], win["end"]
        found, info = fetch_list(provider, begin, end)
        events, other = [], 0
        for row in found:
            got = str(row.get("rcept_dt", ""))
            if not (re.fullmatch(r"[0-9]{8}", got) and begin <= got <= end):
                other += 1
                continue
            code = str(row.get("stock_code") or "").strip()
            kind = kind_of(row.get("report_nm"))
            if code in want and kind:
                events.append((code, got, kind, str(row.get("report_nm", ""))[:60]))
        complete = info["complete"] and not other
        norm = event_manifest.normalize(events)
        body.update(request_started_at_utc=info["request_started_at_utc"], response_received_at_utc=info["response_received_at_utc"],
                    status=info["status"], total_count=info["total_count"], total_page=info["total_page"],
                    pages_received=info["pages_received"], rows_received=info["rows_received"], retry_count=info["retry_count"],
                    pages=info["pages"], normalized_query_digest=event_manifest.query_digest(begin, end),
                    normalized_event_digest=event_manifest.digest(norm), events=len(norm), t0_events=norm,
                    why=info["why"] or (f"확인 범위 {begin} ~ {end} 밖의 다른 접수일 줄 {other}개" if other else ""))
        if complete:
            try:
                new = {}
                for c, d, k, t in norm:
                    new.setdefault(c, []).append({"date": d, "kind": k, "title": t})
                merge(new)
                stored = event_manifest.stored_events(begin, end, OUT)
                body["stored_event_digest"] = event_manifest.digest(stored)
                body["persisted"] = True
                if body["stored_event_digest"] != body["normalized_event_digest"]:
                    body["why"] = f"저장된 t0 사건 {len(stored)}개가 응답의 t0 사건 {len(norm)}개와 다름(범위 {begin} ~ {end})"
            except Exception as e:
                body["why"] = f"저장 실패 · {type(e).__name__}"
    try:
        body["event_data_tree_digest"] = event_manifest.tree_digest(OUT)
    except Exception as e:
        body["why"] = body["why"] or f"트리 지문 셈 실패 · {type(e).__name__}"
    body["ok"] = bool(complete and body["persisted"] and body["event_data_tree_digest"]
                      and body["stored_event_digest"] == body["normalized_event_digest"])
    body["completed_at_utc"] = event_manifest.utc_now()
    path = event_manifest.write(body, folder if folder is not None else MANIFEST)
    if path is None:
        body["ok"] = False
    print(f"공시 확인({'아침 최종' if mode == 'final' else '19:20 정기'}) t0 {t0} · 범위 {body['query_begin']} ~ {body['query_end']} · "
          f"쪽 {info['pages_received']}/{info['total_page']} · 총 {info['total_count']}건 · 범위 대상 사건 {body['events']} · "
          f"{'성공' if body['ok'] else '실패 · ' + str(body['why'])} · manifest {path.name if path else '못 씀'}")
    return body, path


def final_check(provider, codes, today, t0=None, folder=None, calendar_folder=None):
    """D 아침 최종 확인(평일 08:20 · 10:20 · 12:20): 판 고정 달력으로 오늘(D)이 거래일이고 t0 = 앞 거래일(P)일 때만 ·
    이미 그날 성공한 아침 확인이 있으면 묻지 않고 건너뜀(첫 성공만) → 끝 값(0 성공 · 건너뜀 · 휴장 / 1 실패)."""
    import trade_calendar
    info = trade_calendar.day_info(today, folder=calendar_folder)
    if not info:
        print("판 고정 달력으로 오늘 · 앞 거래일을 못 정해 아침 확인을 못 함(오늘 바구니 새 매수는 막힘)")
        return 1
    if not info["trading"]:
        print(f"{today}은 달력에서 휴장이라 아침 확인을 하지 않음")
        return 0
    p = info["P"]
    if t0 and str(t0) != p:
        print(f"물은 t0 {t0}가 달력 앞 거래일 {p}과 달라 하지 않음")
        return 1
    win = event_manifest.query_window(p, calendar_folder)          # 바구니 입력 창과 같은 범위(t0의 앞 거래일 다음 날 ~ t0)
    if not win:
        print(f"판 고정 달력으로 t0 {p}의 확인 범위를 못 정해 아침 확인을 못 함(오늘 바구니 새 매수는 막힘)")
        return 1
    done = event_manifest.first_ok(p, today, folder if folder is not None else MANIFEST, window=win)
    if done:
        print(f"오늘 아침 확인이 이미 성공함({done}) → 다시 묻지 않음(첫 성공만 씀)")
        return 0
    body, path = collect_day(provider, codes, p, "final", day=today, folder=folder, window=win)
    return 0 if body["ok"] and path else 1


def regular(provider, codes, days, today, folder=None, calendar_folder=None):
    """19:20 정기: 최근 days일 이어 받기(예전 그대로 · 쪽 완결성 검사) + 그날 t0(= 오늘 · 달력 거래일일 때) 기록 manifest(문은 안 엶 ·
    범위는 다음 날 바구니 입력 창과 같은 '오늘의 앞 거래일 다음 날 ~ 오늘')."""
    import trade_calendar
    status = 0
    try:
        recent(provider, codes, days, today=today)
    except Incomplete:
        status = 1
    info = trade_calendar.day_info(today, folder=calendar_folder)
    win = event_manifest.query_window(today, calendar_folder) if info and info["trading"] else None
    if not win:
        print("오늘을 달력에서 거래일로 못 정해 19:20 기록(manifest)은 남기지 않음")
        return status
    body, path = collect_day(provider, codes, today, "regular", folder=folder, window=win)
    return status if body["ok"] and path else 1


def verify_run(folder=None, data=None):
    """작업 흐름 저장 단계(git add 앞): 이 작업 · 시도의 manifest마다 꼴이 맞고 · 지금 event-data 트리 지문 = manifest 칸인지
    (manifest를 쓴 뒤 자료가 바뀌지 않았는지) → 0 맞음(또는 이 작업의 manifest 없음) · 1 틀림."""
    folder = Path(folder) if folder is not None else MANIFEST
    rid, att = event_manifest.run_tag()
    mine = sorted(folder.glob(f"*-{rid}-{att}.json"))
    if not mine:
        print("이 작업의 공시 manifest가 없음(자료만 저장)")
        return 0
    tree = event_manifest.tree_digest(data if data is not None else OUT)
    bad = []
    for p in mine:
        try:
            body = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            body = None
        problems = event_manifest.shape_problems(body, p.name)
        if not problems and body["event_data_tree_digest"] != tree:
            problems.append("manifest를 쓴 뒤 event-data가 바뀜(트리 지문 다름)")
        if problems:
            bad.append(f"{p.name}: " + " · ".join(problems))
    for line in bad:
        print("⚠️ 공시 manifest 검증 실패 ·", line)
    if not bad:
        print("공시 manifest 검증 통과 · " + " · ".join(p.name for p in mine))
    return 1 if bad else 0


HOLD_FROM, HOLD_TO = "0800", "1900"      # 평일 이 사이(한국 시각)에는 정기 · 전체 수집을 건너뜀(아침 최종 확인 ~ 판단 · 3단계 고침)


def daytime_hold(now=None):
    """3단계 고침(2026-11-08 조사): 정기(평일 19:20) · 전체(토요일) 수집이 GitHub 예약 밀림으로 평일 낮(08:00 ~ 19:00 한국 시각)에 돌면
    건너뜀 → 참. 아침 최종 확인(08:20 · 10:20 · 12:20) 뒤에 event-data를 다시 쓰면(정기는 최근 5일 사건이 있는 파일의 'recent' 칸을
    늘 다시 씀) 트리 지문이 바뀌어 그날 바구니 문이 닫히는 헛막음이 생김 — 건너뛴 날 자료는 다음 19:20 정기(최근 5일) · 토요일 전체가 채움.
    EVENT_FORCE=1이면 건너뛰지 않음(사람이 일부러 돌릴 때)."""
    if os.getenv("EVENT_FORCE", "").strip() == "1":
        return False
    now = (now or datetime.now(KST)).astimezone(KST)
    return now.weekday() < 5 and HOLD_FROM <= now.strftime("%H%M") < HOLD_TO


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    mode = argv[0] if argv else os.getenv("EVENT_MODE", "").strip()
    if mode == "verify":
        return verify_run()
    if mode != "final" and daytime_hold():
        print("평일 낮(08:00 ~ 19:00 한국 시각)이라 정기 · 전체 공시 수집을 건너뜀 — 아침 최종 확인 뒤 event-data를 바꾸지 않게"
              "(다음 19:20 정기가 최근 5일을 채움 · 일부러 돌리려면 EVENT_FORCE=1)")
        return 0
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
    provider = Official()
    if mode == "final":
        t0 = argv[1] if len(argv) > 1 else os.getenv("EVENT_T0", "").strip()
        return final_check(provider, codes, kst_today(), t0 if t0 and t0 != "auto" else None)
    if RECENT > 0:
        return regular(provider, codes, RECENT, kst_today())
    OUT.mkdir(exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    saved, empty, failed = 0, 0, []
    for index, code in enumerate(codes, 1):
        path = OUT / f"{code}.json"
        if path.exists():
            try:
                kept = json.loads(path.read_text(encoding="utf-8"))
                if kept.get("fetched") == date.today().isoformat():
                    continue
            except (OSError, ValueError):
                pass
        try:
            corp = provider.corp(code)
            rows = []
            # 한 번에 물으면 쪽수가 넘칩니다. 해마다 나눠 묻습니다.
            for year in range(int(FIRST[:4]), int(today[:4]) + 1):
                begin = max(f"{year}0101", FIRST)
                end = min(f"{year}1231", today)
                rows.extend(gather(provider, corp, begin, end))
                time.sleep(PAUSE)
        except Exception as error:
            failed.append((code, str(error)[:50]))
            continue
        if not rows:
            empty += 1
            continue
        seen = {(r["date"], r["kind"], r["title"]): r for r in rows}
        body = {"code": code, "fetched": date.today().isoformat(),
                "rows": [seen[k] for k in sorted(seen)]}
        path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        saved += 1
        if index % 25 == 0:
            print(f"  {index}/{len(codes)} · 저장 {saved} · 없음 {empty} · 실패 {len(failed)}")
    print(f"\n저장 {saved} · 공시 없음 {empty} · 실패 {len(failed)}")
    for code, why in failed[:10]:
        print("  실패:", code, "·", why)
    return 1 if failed and not saved else 0


if __name__ == "__main__":
    sys.exit(main())
