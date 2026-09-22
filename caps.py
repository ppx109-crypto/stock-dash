"""그날의 시가총액과 그날의 순위. 그날까지 알려진 것만으로 만듭니다.

'살 때 코스피 100등 안'을 지나간 자료로 가리려면 그날의 시가총액이 있어야
합니다. 오늘의 순위로 과거를 고르면 그 자체가 미래참조입니다 — 지금 큰
회사는 그동안 커진 회사이고, 그 사실을 그때는 알 수 없었습니다.

주식수는 DART 보고서의 **접수일**과 함께 옵니다. 그날까지 접수된 것 중
가장 최근 것만 씁니다. 거기에 그날 종가를 곱합니다.

**남아 있는 치우침**: 조사 대상 200종목은 오늘의 시가총액으로 고른 것입니다.
2016년에 100등 안이었다가 지금은 작아진 회사는 아예 들어 있지 않습니다.
그래서 여기서 만드는 순위는 '그때의 진짜 코스피 100등'이 아니라
'오늘 살아남은 200종목 안에서의 그때 순위'입니다. 살아남은 것만 보는
쪽이라 성적이 실제보다 좋게 나옵니다. 감출 수 없는 한계이므로 적어 둡니다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

HOME = Path("share-data")
RANK = "시총순위"
SIZE = "시가총액"


@lru_cache(maxsize=None)
def timeline(code):
    """(접수일, 주식수)를 날짜순으로. 접수일에 공개된 수입니다."""
    path = HOME / f"{code}.json"
    if not path.exists():
        return ()
    body = json.loads(path.read_text(encoding="utf-8"))
    found = [(str(day), int(count)) for day, count in body.get("날") or []
             if day and count]
    return tuple(sorted(found))


def known_by(code, day):
    """그날까지 접수된 주식수 중 가장 최근 것. 없으면 None입니다."""
    found = None
    for when, count in timeline(code):
        if when > day:
            break
        found = count
    return found


def first_day(code):
    got = timeline(code)
    return got[0][0] if got else None


def tag(rows, top=100):
    """줄마다 그날의 시가총액과 순위를 붙입니다.

    그날 시가총액을 낼 수 있는 종목끼리만 줄을 세웁니다. 주식수가 아직
    한 번도 접수되지 않은 종목은 순위를 붙이지 않습니다('모름'이지
    '바깥'이 아닙니다).
    """
    by_day = {}
    for row in rows:
        count = known_by(row["code"], row["date"])
        if count is None or not row.get("price"):
            continue
        row[SIZE] = count * row["price"]
        by_day.setdefault(row["date"], []).append(row)
    for day, here in by_day.items():
        here.sort(key=lambda one: -one[SIZE])
        for place, one in enumerate(here, 1):
            one[RANK] = place
    return rows


def inside(row, top=100):
    """그날 순위가 top 안인지. 순위를 모르면 아닙니다."""
    place = row.get(RANK)
    return place is not None and place <= top
