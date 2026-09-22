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

# 제목에 이 말이 있으면 그 갈래로 봅니다. 위에 있는 것부터 맞춰 봅니다.
KINDS = (
    ("유상증자", ("유상증자",)),
    ("무상증자", ("무상증자",)),
    ("전환사채", ("전환사채", "신주인수권부사채", "교환사채")),
    ("자사주취득", ("자기주식취득",)),
    ("자사주처분", ("자기주식처분", "자기주식소각")),
    ("최대주주변경", ("최대주주변경", "최대주주 변경")),
    ("공급계약", ("공급계약", "수주")),
    ("실적공시", ("영업실적", "매출액또는손익", "결산실적")),
    ("배당", ("현금·현물배당", "배당결정")),
    ("감자", ("감자",)),
    ("소송", ("소송",)),
    ("관리종목", ("관리종목", "상장폐지", "거래정지")),
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
    try:
        chosen = json.loads(Path("universe.json").read_text(encoding="utf-8"))
        found = [c for c in chosen.get("codes", []) if re.fullmatch(r"[0-9]{6}", str(c))]
        if found:
            return found
    except (OSError, ValueError):
        pass
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


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
    provider = Official()
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
