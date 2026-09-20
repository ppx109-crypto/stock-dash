"""시가총액 상위 종목을 공공데이터포털 주식시세로 집계합니다.

순위를 추정하지 않고, 기준일의 시가총액 원자료를 받아 시장별로 정렬합니다.
개인 목록·계좌 정보는 다루지 않습니다.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path

from providers import DataError, price_call

MARKETS = ("KOSPI", "KOSDAQ")
TOP = int(os.getenv("RANK_TOP", "10"))


def rows_for(market, target, key):
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
        if len(collected) >= total or not items:
            break
        page += 1
    return collected


def number(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def rank(market, target, key):
    entries = {}
    for row in rows_for(market, target, key):
        code = str(row.get("srtnCd", "")).removeprefix("A").zfill(6)
        cap = number(row.get("mrktTotAmt"))
        if not code.isdigit() or len(code) != 6 or cap is None or cap <= 0:
            continue
        # 같은 기업의 우선주는 보통주와 시가총액을 따로 싣습니다. 그대로 둡니다.
        entries[code] = {"code": code, "name": (row.get("itmsNm") or "").strip(),
                         "market": market, "market_cap": cap,
                         "close": number(row.get("clpr")), "basis_date": str(row.get("basDt"))}
    ordered = sorted(entries.values(), key=lambda r: r["market_cap"], reverse=True)
    for index, row in enumerate(ordered[:TOP], 1):
        row["rank"] = index
    return ordered[:TOP]


def main():
    key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
    if not key:
        raise SystemExit("DATA_GO_KR_SERVICE_KEY가 없습니다.")
    today = date.today()
    for back in range(10):
        target = (today - timedelta(days=back)).strftime("%Y%m%d")
        try:
            result = {market: rank(market, target, key) for market in MARKETS}
        except (DataError, KeyError, TypeError, ValueError) as error:
            print(target, "조회 실패:", str(error)[:120])
            continue
        if all(result[market] for market in MARKETS):
            payload = {"basis_date": target, "source": "공공데이터포털 금융위원회 주식시세정보",
                       "collected": today.isoformat(), "top": TOP, "markets": result}
            Path("public-data").mkdir(exist_ok=True)
            Path("public-data/market-ranking.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            for market in MARKETS:
                print(f"[{market}] {target}")
                for row in result[market]:
                    print(f"  {row['rank']:>2}. {row['code']} {row['name']} · 시가총액 {row['market_cap']:,.0f}원")
            return
    raise SystemExit("최근 10일 안에 시가총액 자료를 찾지 못했습니다.")


if __name__ == "__main__":
    main()
