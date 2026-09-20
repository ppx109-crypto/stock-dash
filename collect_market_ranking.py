"""시가총액 상위 종목을 공공데이터포털 주식시세로 집계해 저장합니다.

순위를 추정하지 않고 기준일의 시가총액 원자료를 정렬합니다.
개인 목록·계좌 정보는 다루지 않습니다.
"""
import json
import os
from datetime import date
from pathlib import Path

from market import MARKETS, top_by_market


def main():
    if not os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip():
        raise SystemExit("DATA_GO_KR_SERVICE_KEY가 없습니다.")
    top = int(os.getenv("RANK_TOP", "10"))
    result = top_by_market(top)
    if result["error"]:
        raise SystemExit(result["error"])
    payload = {"basis_date": result["basis_date"], "top": top,
               "source": "공공데이터포털 금융위원회 주식시세정보",
               "collected": date.today().isoformat(), "markets": result["markets"]}
    Path("public-data").mkdir(exist_ok=True)
    Path("public-data/market-ranking.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in MARKETS:
        print(f"[{name}] {result['basis_date']}")
        for row in result["markets"][name]:
            print(f"  {row['rank']:>2}. {row['code']} {row['name']} · 시가총액 {row['market_cap']:,.0f}원")


if __name__ == "__main__":
    main()
