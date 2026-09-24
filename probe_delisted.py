"""지금은 없는 회사의 일봉을 받을 수 있는지 알아봅니다.

조사 대상 507종목은 **오늘의** 시가총액으로 고른 것입니다. 2016년에 100등
안이었다가 그 뒤 상장폐지되었거나 작아진 회사는 표에 아예 없습니다. 그래서
모든 성적이 실제보다 좋게 나옵니다(25회차부터 적어 온 한계입니다).

메우려면 그런 회사의 일봉이 필요합니다. 받을 수 있는지부터 알아야 합니다.
DART가 아는 종목코드 가운데 **지금 시세가 안 나오는 것**을 골라, 증권사에
과거 일봉을 물어봅니다. 조회 전용이며 아무것도 저장하지 않습니다.

이 스크립트는 **재지 않습니다. 셀 뿐입니다.** 몇 종목이나 받아지는지, 얼마나
긴지, 언제 끊겼는지만 냅니다. 그 답에 따라 다음 회차에서 실제로 모읍니다.
"""
import os
import re
import sys
from collections import Counter

import broker_kis
from providers import Official

SAMPLE = int(os.getenv("PROBE_SAMPLE", "60"))   # 물어볼 종목 수
SINCE = os.getenv("PROBE_SINCE", "20150101")


def dart_codes():
    """DART가 아는 종목코드. 우선주는 뺍니다(pick_universe와 같은 잣대)."""
    provider = Official()
    provider.corp("005930")
    found = [code for code in (provider.corps or {})
             if re.fullmatch(r"[0-9]{6}", code or "")]
    return sorted(c for c in found if not c.endswith(("5", "7", "9")))


def already_have():
    from pathlib import Path
    return {p.stem for p in Path("price-data").glob("*.json")
            if re.fullmatch(r"[0-9]{6}", p.stem)}


def main():
    codes = dart_codes()
    if not codes:
        print("DART 목록을 받지 못했습니다.")
        return 1
    have = already_have()
    rest = [c for c in codes if c not in have]
    print(f"DART가 아는 종목 {len(codes):,} · 이미 모은 것 {len(have):,} · "
          f"나머지 {len(rest):,}")
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as error:
        print("증권사 연결 실패 ·", error)
        return 1

    # 나머지를 고르게 훑습니다. 앞쪽만 보면 코드 번호가 작은 옛 회사에
    # 치우칩니다.
    step = max(1, len(rest) // SAMPLE)
    picked = rest[::step][:SAMPLE]
    print(f"{len(picked)}종목에 물어봅니다.\n")

    tally = Counter()
    alive, gone, empty = [], [], []
    for index, code in enumerate(picked, 1):
        try:
            quote = client.quote(code)
            priced = bool(quote.get("market_cap"))
        except broker_kis.BrokerError:
            priced = False
        try:
            bars = client.history(code, days=4000)
        except broker_kis.BrokerError as error:
            tally["일봉 거절"] += 1
            print(f"[{index}/{len(picked)}] {code} · 시세 "
                  f"{'있음' if priced else '없음'} · 일봉 거절 {str(error)[:40]}")
            continue
        if not bars:
            tally["일봉 없음"] += 1
            empty.append(code)
            print(f"[{index}/{len(picked)}] {code} · 시세 "
                  f"{'있음' if priced else '없음'} · 일봉 0일")
            continue
        days = [d for d, _ in bars]
        late = days[-1]
        tally["일봉 있음"] += 1
        (alive if priced else gone).append((code, len(days), days[0], late))
        print(f"[{index}/{len(picked)}] {code} · 시세 "
              f"{'있음' if priced else '없음'} · 일봉 {len(days)}일 · "
              f"{days[0]}~{late}")

    print("\n== 셈 ==")
    for tag, count in tally.most_common():
        print(f"  {tag} {count}")
    print(f"  시세도 있고 일봉도 있음 {len(alive)}")
    print(f"  **시세는 없는데 일봉은 있음 {len(gone)}**  ← 메울 수 있는 종목")
    if gone:
        print("\n  그중 최근 것부터 스무 개:")
        for code, count, begin, end in sorted(gone, key=lambda r: -int(r[3]))[:20]:
            print(f"    {code} · {count}일 · {begin}~{end}")
        fresh = [one for one in gone if one[3] >= SINCE]
        print(f"\n  마지막 일봉이 {SINCE} 뒤인 것 {len(fresh)}종목 "
              f"— 조사 구간에 걸칩니다.")
    print("\n끝. 세기만 했고 아무것도 저장하지 않았습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
