"""날마다의 시가총액을 공공데이터포털에서 통째로 받아 둡니다.

지금까지 그날의 시가총액은 **DART 주식총수 × 종가**로 만들었습니다. 주식총수는
보고서가 나올 때만 갱신되고, 그 API는 2016사업연도부터라 앞이 비어 있습니다.
그 탓에 삼성전자가 2017-03-31에야, 현대차는 2022년에야 순위를 받았습니다
(59회차). 그동안 '코스피 100등 안'은 가장 큰 회사들이 빠진 채로 매겨졌고,
그 자리를 더 작은 회사가 차지했습니다.

공공데이터포털 주식시세정보는 **날짜별로 시장 전체의 시가총액**을 줍니다
(`mrktTotAmt`). 보고서를 기다릴 필요가 없고, 우리가 일봉을 안 모은 회사까지
포함해 줄을 세워 줍니다 — 그 회사들이 100등 안을 차지하면 우리 종목은 그만큼
뒤로 밀려야 맞습니다.

두 가지를 적어 둡니다.
  1. **자름** — 그날 시장 전체에서 50·100·200·300등의 시가총액. 우리 종목이
     100등 안인지는 '그날 100등 자름보다 큰가'로 가립니다.
  2. **값** — 우리가 일봉을 모은 종목들의 그날 시가총액.

해마다 한 파일입니다. 이어 받을 수 있게 이미 있는 날은 건너뜁니다.
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from market import board

OUT = Path("cap-data")
CUTS = (50, 100, 200, 300)
MARKET = os.getenv("CAPS_MARKET", "KOSPI")


def trading_days(first, last):
    """일봉이 아는 거래일. 달력을 지어내지 않고 모아 둔 자료에서 가져옵니다."""
    found = set()
    for path in Path("price-data").glob("*.json"):
        if not re.fullmatch(r"[0-9]{6}", path.stem):
            continue
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for day, _ in body.get("closes") or []:
            if first <= str(day) <= last:
                found.add(str(day))
    return sorted(found)


def ours():
    return {p.stem for p in Path("price-data").glob("*.json")
            if re.fullmatch(r"[0-9]{6}", p.stem)}


def kept(year):
    path = OUT / f"{year}.json"
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return body.get("날") or {}


def save(year, days):
    OUT.mkdir(exist_ok=True)
    body = {"해": year, "시장": MARKET, "자름 등수": list(CUTS),
            "설명": "자름은 그날 시장 전체의 그 등수 시가총액. 값은 우리 종목의 시가총액.",
            "날": dict(sorted(days.items()))}
    (OUT / f"{year}.json").write_text(json.dumps(body, ensure_ascii=False),
                                      encoding="utf-8")


def one_day(key, day, mine):
    rows = board(MARKET, day, key)
    caps = {}
    for row in rows:
        code = str(row.get("srtnCd", "")).removeprefix("A").zfill(6)
        try:
            cap = int(str(row.get("mrktTotAmt", "")).replace(",", ""))
        except ValueError:
            continue
        if len(code) == 6 and code.isdigit() and cap > 0:
            caps[code] = cap
    if not caps:
        return None
    ordered = sorted(caps.values(), reverse=True)
    cuts = {str(place): (ordered[place - 1] if len(ordered) >= place else None)
            for place in CUTS}
    return {"셈": len(ordered), "자름": cuts,
            "값": {code: caps[code] for code in mine if code in caps}}


def main():
    key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
    if not key:
        print("DATA_GO_KR_SERVICE_KEY가 없습니다.")
        return 1
    first = os.getenv("CAPS_FIRST", "20150101")
    last = os.getenv("CAPS_LAST", "20261231")
    limit = int(os.getenv("CAPS_LIMIT", "400"))
    mine = ours()
    days = trading_days(first, last)
    print(f"거래일 {len(days)}일 · 우리 종목 {len(mine)} · 시장 {MARKET}")
    by_year = {}
    for day in days:
        by_year.setdefault(day[:4], []).append(day)

    asked = 0
    for year in sorted(by_year):
        have = kept(year)
        todo = [day for day in by_year[year] if day not in have]
        if not todo:
            print(f"{year} · 이미 다 받았습니다({len(have)}일)")
            continue
        print(f"{year} · 받을 날 {len(todo)}일 (이미 {len(have)}일)")
        for day in todo:
            if asked >= limit:
                print(f"이번 판의 몫({limit}일)을 다 썼습니다. 다시 돌리면 이어받습니다.")
                save(year, have)
                return 0
            try:
                got = one_day(key, day, mine)
            except Exception as error:            # 하루가 없어도 나머지는 받습니다
                print(f"  {day} 실패 · {str(error)[:60]}")
                asked += 1
                continue
            asked += 1
            if not got:
                print(f"  {day} · 자료 없음(휴장일 수 있음)")
                continue
            have[day] = got
            if len(have) % 50 == 0:
                save(year, have)
                print(f"  {day}까지 {len(have)}일 저장")
        save(year, have)
        print(f"{year} · 저장 {len(have)}일")
    print(f"\n물어본 날 {asked}일")
    return 0


if __name__ == "__main__":
    sys.exit(main())
