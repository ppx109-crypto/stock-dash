"""공시를 신호에 붙입니다. 그날까지 나온 것만 붙입니다.

숫자로 된 실적은 분기에 한 번이지만 공시는 수시로 납니다. 유상증자를
결정한 날, 자사주를 사기로 한 날은 그날 시장이 처음 아는 일입니다. 크게
밀린 종목 뒤에 그런 일이 있었는지 없었는지가 반등을 가를 수 있습니다.

붙이는 규칙은 하나뿐입니다. **접수일이 그날보다 뒤인 공시는 없는 것으로
칩니다.** 접수일은 그날 공시가 공개된 날이므로, 그날 이후의 것을 쓰면
그대로 미래참조입니다. 여기서 한 번, guard에서 또 한 번 확인합니다.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

HOME = Path("event-data")
WINDOW = 20          # 며칠 전까지를 '최근'으로 볼지. 달력 날짜입니다.
MARK = "공시"        # 붙인 갈래들
AGE = "공시 나이"     # 가장 가까운 공시가 며칠 전인지


@lru_cache(maxsize=None)
def timeline(code):
    """그 종목의 공시를 (접수일, 갈래)로 모아 날짜순으로 둡니다."""
    path = HOME / f"{code}.json"
    if not path.exists():
        return ()
    body = json.loads(path.read_text(encoding="utf-8"))
    found = [(row["date"], row["kind"]) for row in body.get("rows") or []
             if row.get("date") and row.get("kind")]
    return tuple(sorted(found))


def covered(code):
    """이 종목에 공시 자료가 있는지. 없는 종목을 '공시 없음'과 섞으면 안 됩니다."""
    return bool(timeline(code))


def span():
    """자료가 덮는 기간. 이 바깥의 날은 '공시 없음'이 아니라 '모름'입니다."""
    first, last = None, None
    for path in HOME.glob("*.json"):
        got = timeline(path.stem)
        if not got:
            continue
        first = got[0][0] if first is None else min(first, got[0][0])
        last = got[-1][0] if last is None else max(last, got[-1][0])
    return first, last


def _back(day, days):
    return (datetime.strptime(day, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")


def recent(code, day, window=WINDOW):
    """그날까지, 최근 window일 안에 난 공시 갈래들과 가장 가까운 것의 나이."""
    edge = _back(day, window)
    kinds, age = set(), None
    for when, kind in timeline(code):
        if when > day:          # 그날보다 뒤에 접수된 것은 그날 알 수 없습니다.
            break
        if when >= edge:
            kinds.add(kind)
            gap = (datetime.strptime(day, "%Y%m%d")
                   - datetime.strptime(when, "%Y%m%d")).days
            age = gap if age is None else min(age, gap)
    return kinds, age


def tag(rows, window=WINDOW):
    """신호마다 최근 공시를 붙입니다. 자료가 없는 종목·기간은 건드리지 않습니다."""
    first, last = span()
    for row in rows:
        if not covered(row["code"]) or not first or not (first <= row["date"] <= last):
            continue
        kinds, age = recent(row["code"], row["date"], window)
        row[MARK] = sorted(kinds)
        row[AGE] = age
    return rows
