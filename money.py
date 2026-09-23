"""거래대금. '실제로 살 수 있었나'를 가리는 자입니다.

종가만 보면 하루에 몇천만 원어치 거래되는 종목을 자리 하나만큼 사는 것으로
세게 됩니다. 실제로는 그 주문이 들어가는 순간 값이 밀립니다.

그날까지의 거래대금만 씁니다. 그날을 **포함해** 지난 스무 날의 중앙값을
그 종목의 그날 유동성으로 봅니다. 중앙값을 쓰는 것은, 하루 터진 거래대금이
평소 실력으로 보이지 않게 하려는 것입니다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

HOME = Path("volume-data")
WINDOW = 20
MONEY = "거래대금중앙"        # 그날까지 스무 날 거래대금 중앙값 (원)
SHARE = "자리몫"              # 자리 하나가 그날 거래대금의 몇 %인지


@lru_cache(maxsize=None)
def timeline(code):
    """(날짜, 거래대금)을 날짜순으로. 거래가 없던 날은 0입니다."""
    path = HOME / f"{code}.json"
    if not path.exists():
        return ()
    body = json.loads(path.read_text(encoding="utf-8"))
    names = body.get("칸") or []
    try:
        spot = names.index("거래대금")
    except ValueError:
        return ()
    found = []
    for row in body.get("날") or []:
        if len(row) > spot and row[0] and row[spot] is not None:
            found.append((str(row[0]), float(row[spot])))
    return tuple(sorted(found))


@lru_cache(maxsize=None)
def _rolling(code, window=WINDOW):
    """날마다 '그날까지 스무 날 거래대금 중앙값'을 미리 만들어 둡니다."""
    got = timeline(code)
    found = {}
    for k in range(len(got)):
        window_rows = [value for _, value in got[max(0, k - window + 1):k + 1]]
        if len(window_rows) < window // 2:
            continue
        window_rows.sort()
        found[got[k][0]] = window_rows[len(window_rows) // 2]
    return found


def covered(code):
    """이 종목에 거래대금 자료가 있는지. 없는 것과 '거래가 없는 것'은 다릅니다."""
    return bool(timeline(code))


def known_by(code, day):
    """그날까지의 거래대금 중앙값. 그날 자료가 없으면 None입니다."""
    return _rolling(code).get(day)


def tag(rows, purse=None, slots=3):
    """줄마다 그날의 거래대금 중앙값을 붙입니다.

    purse(지갑, 원)를 주면 자리 하나가 그날 거래대금의 몇 %인지도 적습니다.
    이 몫이 크면 실제로는 그 값에 못 삽니다.
    """
    for row in rows:
        if not covered(row["code"]):
            continue
        got = known_by(row["code"], row["date"])
        if got is None:
            continue
        row[MONEY] = got
        if purse and got > 0:
            row[SHARE] = round(purse / slots / got * 100, 3)
    return rows


def enough(row, floor):
    """그날 거래대금 중앙값이 floor(원) 이상인지. 모르면 아닙니다."""
    got = row.get(MONEY)
    return got is not None and got >= floor
