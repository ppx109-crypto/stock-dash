"""조사할 종목을 시가총액 순으로 고릅니다.

쉰 종목으로는 조합마다 아홉 종목쯤에서 숫자가 나와, 그 종목들의 사정인지
규칙의 힘인지 갈리지 않습니다. 대상을 넓히면 그 구분이 가능해집니다.

DART에서 상장사 전체 목록을 받고, 증권사 시세로 시가총액을 읽어 위에서부터
자릅니다. 둘 다 이미 쓰고 있는 자료원이라 새 열쇠가 필요하지 않습니다.
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis
from providers import Official

OUT = Path("universe.json")
WANT = int(os.getenv("UNIVERSE_SIZE", "200"))
PAUSE = float(os.getenv("UNIVERSE_PAUSE", "0.12"))


def listed():
    """DART가 아는 상장사의 종목코드. 우선주와 비어 있는 칸은 뺍니다."""
    provider = Official()
    provider.corp("005930")          # corps를 채우기 위한 한 번의 조회입니다.
    found = [code for code in (provider.corps or {})
             if re.fullmatch(r"[0-9]{6}", code or "")]
    # 우선주는 보통주와 흐름이 같아 표본만 부풀립니다. 끝자리로 걸러냅니다.
    return sorted(c for c in found if not c.endswith(("5", "7", "9")))


def main():
    codes = listed()
    if not codes:
        print("상장사 목록을 받지 못했습니다.")
        return 1
    print(f"상장사 {len(codes):,}종목에서 시가총액을 읽습니다.")
    client = broker_kis.market()
    sized, failed = [], 0
    for index, code in enumerate(codes, 1):
        try:
            found = client.quote(code)
        except broker_kis.BrokerError:
            failed += 1
            continue
        if found.get("market_cap"):
            sized.append({"code": code, "name": found.get("name") or code,
                          "market_cap": found["market_cap"]})
        if index % 200 == 0:
            print(f"  {index:,}/{len(codes):,} · 읽은 종목 {len(sized):,} · 건너뜀 {failed:,}")
        time.sleep(PAUSE)
    sized.sort(key=lambda r: r["market_cap"], reverse=True)
    picked = sized[:WANT]
    if not picked:
        print("시가총액을 하나도 읽지 못했습니다.")
        return 1
    OUT.write_text(json.dumps({
        "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
        "asked": WANT, "read": len(sized), "skipped": failed,
        "codes": [r["code"] for r in picked], "rows": picked},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n시가총액을 읽은 종목 {len(sized):,} · 고른 종목 {len(picked):,}")
    print("맨 위:", ", ".join(f'{r["name"]}({r["market_cap"]:,.0f}억)' for r in picked[:5]))
    print("맨 아래:", ", ".join(f'{r["name"]}({r["market_cap"]:,.0f}억)' for r in picked[-3:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
