"""장중 실시간 확인(사용자 2026-10-07 "장중 실시간으로 변하는지 확인해줘") — 대시보드가 쓰는 같은 한투 함수로
코스피 지수 지금 값(index_now) · 종목 지금 값(quote)을 1분 간격으로 세 번 받아 값이 바뀌는지 찍음.
찍는 것은 값(지수 · 가격 · 오늘 등락)뿐 · 키 · 계좌 · 응답 본문은 찍지 않음. python live_check.py [코드 …]"""
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import broker_kis

KST = ZoneInfo("Asia/Seoul")


def main(codes):
    client = broker_kis.market()
    seen = {}
    for n in range(3):
        at = datetime.now(KST).strftime("%H:%M:%S")
        try:
            k = client.index_now("0001")
            got = [f"코스피 {k['value']:,.2f} ({k['diff']:+.2f} · {k['rate']:+.2f}%)"]
            seen.setdefault("코스피", []).append(k["value"])
        except broker_kis.BrokerError as e:
            got = [f"코스피 지금 값 실패 · {e}"]
        for c in codes:
            try:
                q = client.quote(c)
                got.append(f"{q.get('name') or c} {q['price']:,.0f}원 ({q['change']:+,.0f} · {q['rate']:+.2f}%)")
                seen.setdefault(c, []).append(q["price"])
            except broker_kis.BrokerError as e:
                got.append(f"{c} 실패 · {e}")
        print(f"[{at}] " + " | ".join(got), flush=True)
        if n < 2:
            time.sleep(60)
    moved = {k: len(set(v)) > 1 for k, v in seen.items()}
    print("값이 바뀐 것: " + " · ".join(f"{k} {'예' if m else '아니오'}" for k, m in moved.items()))
    print("판정: " + ("장중 실시간으로 바뀜" if any(moved.values()) else "세 번 모두 같은 값(장이 닫혔거나 움직임이 없음)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["069500", "005930", "251340"]))
