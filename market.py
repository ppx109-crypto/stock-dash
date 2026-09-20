"""시가총액 순위. 공공데이터포털 주식시세의 시가총액 항목을 그대로 정렬합니다."""
from __future__ import annotations

import os
from datetime import date, timedelta

from providers import DataError, price_call

MARKETS = ("KOSPI", "KOSDAQ")


def _number(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def board(market: str, target: str, key: str) -> list[dict]:
    """한 시장의 기준일 시세를 모두 읽습니다. 응답이 나뉘면 이어서 받습니다."""
    collected, page = [], 1
    while page <= 20:
        payload = price_call("getStockPriceInfo", {
            "serviceKey": key, "resultType": "json", "numOfRows": 1000, "pageNo": page,
            "basDt": target, "mrktCls": market})
        body = payload["response"].get("body", {})
        items = (body.get("items") or {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        collected.extend(items)
        total = int(body.get("totalCount") or 0)
        if not items or len(collected) >= total:
            break
        page += 1
    return collected


def rank(market: str, target: str, key: str, top: int) -> list[dict]:
    entries = {}
    for row in board(market, target, key):
        code = str(row.get("srtnCd", "")).removeprefix("A").zfill(6)
        cap = _number(row.get("mrktTotAmt"))
        if len(code) != 6 or not code.isdigit() or cap is None or cap <= 0:
            continue
        entries[code] = {"code": code, "name": (row.get("itmsNm") or "").strip(),
                         "market": market, "market_cap": cap, "close": _number(row.get("clpr")),
                         "rate": _number(row.get("fltRt")), "basis_date": str(row.get("basDt"))}
    ordered = sorted(entries.values(), key=lambda r: r["market_cap"], reverse=True)[:top]
    for index, row in enumerate(ordered, 1):
        row["rank"] = index
    return ordered


def daily_closes(code: str, key: str, span_days: int = 260) -> list[tuple[str, float]]:
    """한 종목의 일별 종가를 과거→최근 순으로 돌려줍니다.

    이동평균 60일선에는 62거래일 이상이 필요해 달력 기준으로 넉넉히 받습니다.
    수정주가가 아니므로 분할·병합 구간의 단절은 호출한 쪽에서 판단합니다.
    """
    today = date.today()
    params = {"serviceKey": key, "resultType": "json", "numOfRows": 400,
              "beginBasDt": (today - timedelta(days=span_days)).strftime("%Y%m%d"),
              "endBasDt": today.strftime("%Y%m%d"), "likeSrtnCd": code}
    payload = price_call("getStockPriceInfo", params)
    items = (payload["response"].get("body", {}).get("items") or {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    rows = {}
    for item in items:
        if str(item.get("srtnCd", "")).removeprefix("A").zfill(6) != str(code).zfill(6):
            continue
        close = _number(item.get("clpr"))
        basis = str(item.get("basDt") or "")
        if close and close > 0 and len(basis) == 8:
            rows[basis] = close
    return sorted(rows.items())


def grade_all(codes, research: dict, span_days: int = 260) -> list[dict]:
    """종목별로 추세·실적 축을 매기고 그룹을 붙입니다."""
    from urllib.parse import unquote
    import trend

    key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
    graded = []
    for code in codes:
        code = str(code).zfill(6)
        report = research.get(code) or {}
        money = report.get("financial")
        closes, days = [], []
        note = None
        if key:
            try:
                rows = daily_closes(code, key, span_days)
                days = [day for day, _ in rows]
                closes = [close for _, close in rows]
            except (DataError, KeyError, TypeError, ValueError) as error:
                note = str(error)[:80]
        else:
            note = "공공데이터포털 인증키를 설정하세요."
        result = trend.assess(closes, money)
        # 화면에서 가격선과 이동평균을 함께 그리도록 최근 구간을 같이 넘깁니다.
        # 마지막 거래일은 화면에 기준일로 적어야 하므로 함께 넘깁니다.
        graded.append({"code": code, "name": report.get("name") or code, "note": note,
                       "closes": closes[-130:], "as_of": days[-1] if days else None,
                       "money_period": (money or {}).get("period"), **result})
    return graded


def top_by_market(top: int = 10, markets=MARKETS) -> dict:
    """기준일을 최근 거래일로 잡고 시장별 상위 종목을 돌려줍니다."""
    from urllib.parse import unquote
    key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
    if not key:
        return {"error": "공공데이터포털 인증키를 설정하세요.", "markets": {}, "basis_date": None}
    today = date.today()
    last = None
    for back in range(10):
        target = (today - timedelta(days=back)).strftime("%Y%m%d")
        try:
            result = {market: rank(market, target, key, top) for market in markets}
        except (DataError, KeyError, TypeError, ValueError) as error:
            last = str(error)
            continue
        if all(result[market] for market in markets):
            return {"error": None, "markets": result, "basis_date": target}
    return {"error": last or "최근 10일 안에 시가총액 자료를 찾지 못했습니다.", "markets": {}, "basis_date": None}
