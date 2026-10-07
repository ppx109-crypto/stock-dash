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
import os
from functools import lru_cache
from pathlib import Path

HOME = Path("share-data")
RANK = "시총순위"
SIZE = "시가총액"


ADJ = os.getenv("CAPS_ADJ", "0") == "1"   # 연구용: 주식 쪼개기 · 무상증자를 지금 기준 주식 수로 맞춤(2026-10-08 2차 연구)


@lru_cache(maxsize=None)
def raw_timeline(code):
    """(접수일, 주식수)를 날짜순으로. 접수일에 공개된 수입니다(DART 그대로)."""
    path = HOME / f"{code}.json"
    if not path.exists():
        return ()
    body = json.loads(path.read_text(encoding="utf-8"))
    found = [(str(day), int(count)) for day, count in body.get("날") or []
             if day and count]
    return tuple(sorted(found))


@lru_cache(maxsize=None)
def _bonus_days(code):
    path = Path("event-data") / f"{code}.json"
    if not path.exists():
        return ()
    rows = json.loads(path.read_text(encoding="utf-8")).get("rows") or []
    return tuple(sorted(str(r.get("date")) for r in rows if "무상" in str(r.get("title", ""))))


@lru_cache(maxsize=None)
def _raw_closes(code):
    """원주가(수정 안 한 종가) — 한투 대차 자료(loan-data)에 같이 온 종가 · 2017 ~ · 272종목."""
    path = Path("loan-data") / f"{code}.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8")).get("rows") or []
    return {str(r["date"]): float(r["종가"]) for r in rows if r.get("종가")}


@lru_cache(maxsize=None)
def _adj_closes(code):
    path = Path("price-data") / f"{code}.json"
    if not path.exists():
        return {}
    return {str(d): float(v) for d, v in json.loads(path.read_text(encoding="utf-8")).get("closes") or [] if v}


def _exact_factors(code, days):
    """보고서 날마다 정확한 배수 f = 원주가 ÷ 수정주가(보고서 날 또는 그 뒤 20일 안 첫 거래일).
    지금 기준 주식수 = 그 보고서 주식수 × f (그 뒤 쪼개기 · 무상증자 배수가 f에 다 들어 있음).
    2017 앞 보고서는 2017 첫 날 f를 씀. 하나라도 못 구하면 None(→ 어림 방식)."""
    raw, adj = _raw_closes(code), _adj_closes(code)
    both = sorted(d for d in raw if d in adj)
    if not both:
        return None
    import bisect
    out = []
    for d in days:
        if d < both[0]:
            out.append(raw[both[0]] / adj[both[0]])
            continue
        k = bisect.bisect_left(both, d)
        if k >= len(both) or both[k] > _plus_days(d, 20):
            return None
        out.append(raw[both[k]] / adj[both[k]])
    return out


def _plus_days(day, n):
    from datetime import datetime, timedelta
    return (datetime.strptime(day, "%Y%m%d") + timedelta(days=n)).strftime("%Y%m%d")


@lru_cache(maxsize=None)
def adjusted_timeline(code):
    """주식수를 **지금 기준**(수정주가와 같은 기준)으로 바꾼 줄.

    가격 자료(price-data)는 한투 수정주가라 액면분할 · 무상증자 앞 값이 지금 기준으로 낮춰져 있는데,
    DART 주식수는 그때 값이라 둘을 곱하면 쪼개기 앞 시가총액이 크게 작게 나옴(삼성전자 2017 ~ 19 약 1/50).
    고침: ① 단위 실수(앞 줄 대비 ≈ 1000배 · 1/1000)는 맞춤 ② 이웃 보고 사이 주식수가 1.8배 이상(또는 0.55배 이하) 바뀌면
    쪼개기 · 병합으로 봄 ③ 1.2 ~ 1.8배이면 그 사이 '무상' 공시가 있을 때만 무상증자로 봄 → 그 앞 모든 줄에 그 배수를 곱함.
    그날 시가총액 = 그날 수정주가 × 고친 주식수 = 그날의 진짜 시가총액(어림). 미래 사건 배수를 쓰지만 결과는 그날 실제 값이라 미래 참조 아님.
    """
    raw = list(raw_timeline(code))
    if not raw:
        return ()
    import statistics
    med = statistics.median(c for _, c in raw)
    fixed = []
    for day, count in raw:                       # 단위 실수(가운데값 대비 ≈ 1000배 · 1/1000)
        x = count / med
        if x >= 300:
            count = count / 1000
        elif x <= 1 / 300:
            count = count * 1000
        fixed.append((day, count))
    exact = _exact_factors(code, [d for d, _ in fixed])
    if exact:
        return tuple((d, int(round(c * f))) for (d, c), f in zip(fixed, exact))
    bonus = _bonus_days(code)
    factor = [1.0] * len(fixed)
    for i in range(len(fixed) - 1, 0, -1):
        (d0, c0), (d1, c1) = fixed[i - 1], fixed[i]
        x = c1 / c0
        act = x >= 1.8 or x <= 0.55 or (1.2 <= x < 1.8 and any(d0 < b <= d1 for b in bonus))
        factor[i - 1] = factor[i] * (x if act else 1.0)
    return tuple((d, int(round(c * f))) for (d, c), f in zip(fixed, factor))


def timeline(code):
    return adjusted_timeline(code) if ADJ else raw_timeline(code)


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
