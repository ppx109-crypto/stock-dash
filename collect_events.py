"""공시 제목을 날짜와 함께 모읍니다.

숫자로 된 실적은 분기마다 한 번뿐이지만, 공시는 수시로 납니다. 유상증자가
결정된 날, 자사주를 사기로 한 날, 최대주주가 바뀐 날은 그날 시장이 처음
아는 일입니다. 급락 뒤 반등을 가를 만한 것이 여기 있을 수 있습니다.

제목만 모읍니다. 본문은 종목당 수십 MB라 받지 않습니다. 제목에 들어 있는
말로 갈래를 나눕니다.
"""
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

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


def recent(provider, codes, days, today=None):
    """시장 전체 공시 목록(종목 지정 없음)에서 최근 days일 치만 받아 대상 종목 파일에 이어 붙입니다.
    종목마다 묻지 않아 하루 수십 번 조회로 끝납니다. 'fetched'(전체 수집 날)는 그대로 두고 'recent'만 적습니다."""
    want = set(codes)
    end = today or date.today().strftime("%Y%m%d")
    begin = (date(int(end[:4]), int(end[4:6]), int(end[6:])) - timedelta(days=days)).strftime("%Y%m%d")
    new, page = {}, 1
    for _ in range(500):
        answer = provider.dart("list.json", bgn_de=begin, end_de=end, page_no=page, page_count=100,
                               sort="date", sort_mth="asc")
        if not answer:
            break
        rows = answer.get("list") or []
        for row in rows:
            code = str(row.get("stock_code") or "").strip()
            kind = kind_of(row.get("report_nm"))
            if code in want and kind and re.fullmatch(r"[0-9]{8}", str(row.get("rcept_dt", ""))):
                new.setdefault(code, []).append({"date": str(row["rcept_dt"]), "kind": kind,
                                                 "title": str(row.get("report_nm", ""))[:60]})
        total = int(answer.get("total_page") or 1)
        if page >= total or not rows:
            break
        page += 1
        time.sleep(PAUSE)
    OUT.mkdir(exist_ok=True)
    added = 0
    for code, rows in new.items():
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
        body["rows"] = [seen[k] for k in sorted(seen)]
        body["recent"] = end
        path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    print(f"최근 {days}일 · 시장 전체 {page}쪽 · 대상 종목 {len(new)} · 새 공시 {added}건")
    return added


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
    provider = Official()
    if RECENT > 0:
        recent(provider, codes, RECENT)
        return 0
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
