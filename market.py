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
