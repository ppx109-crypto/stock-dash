"""운영 판단 전에 자료가 다 들어왔는지 확인합니다(사용자 요청 2026-10-02 "자료 확인장치는 확인하고 판단하게").

2026-10-02 새벽 사고: 일봉 479종목에 10-01 종가가 빠졌는데, '가장 늦은 날짜'만 보던 확인이 19종목 때문에 통과해
시장 폭 11.8%로 틀린 후보가 나왔습니다. 그래서 두 가지를 봅니다.
1) 일봉의 마지막 날이 '어제 거래일'인 종목이 충분한가(SHARE 넘게). 거래정지 · 상장폐지처럼 오래 멈춘 종목은 세지 않습니다.
2) 1시간봉 후보(plan)의 기준일이 바로 '어제 거래일'인가(하루 넘게 낡은 후보로 사지 않음).
'어제 거래일'은 증권사 코스피 지수 일봉에서 오늘보다 앞선 가장 늦은 날로 정합니다. 조회가 안 되면 일봉 자료에서 가장 많은 종목이 가진 마지막 날로 대신합니다."""
from collections import Counter
from datetime import datetime, timedelta

SHARE = 0.9           # 어제 종가까지 있는 종목이 이만큼은 되어야 판단
STALE_DAYS = 30       # 마지막 날이 기대일보다 이만큼(달력 일) 넘게 앞선 종목은 멈춘 종목으로 보고 세지 않음


def _minus(day, days):
    return (datetime.strptime(day, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")


def prev_trading_day(client, day):
    """오늘(day)보다 앞선 가장 늦은 거래일. 조회가 안 되면 None."""
    try:
        rows = client.index_daily("0001", _minus(day, 20), day)
    except Exception:
        return None
    days = sorted(str(r.get("date", "")) for r in rows or [] if str(r.get("date", "")) < day and r.get("종가"))
    return days[-1] if days else None


def last_days(prices):
    """종목마다 일봉의 마지막 날(study.load_prices 꼴: {code: {"rows": [(날, 종가), ...]}})."""
    return {c: str(v["rows"][-1][0]) for c, v in prices.items() if v.get("rows")}


def daily_ready(prices, expect=None, share=SHARE):
    """일봉이 expect(어제 거래일)까지 충분히 들어왔나 → (됨, 기대일, 문장).
    expect가 없으면 가장 많은 종목이 가진 마지막 날을 씀(그때는 자료끼리만 견줌)."""
    lasts = last_days(prices)
    if not lasts:
        return False, expect, "일봉 자료가 없습니다."
    if not expect:
        expect = Counter(lasts.values()).most_common(1)[0][0]
    edge = _minus(expect, STALE_DAYS)
    pool = [d for d in lasts.values() if d >= edge]
    have = sum(d >= expect for d in pool)
    rate = have / len(pool) if pool else 0.0
    text = f"{expect[:4]}-{expect[4:6]}-{expect[6:]} 종가까지 있는 종목 {have}/{len(pool)}({rate * 100:.0f}%)"
    if rate < share:
        return False, expect, text + f" — {share * 100:.0f}%보다 적어 자료가 덜 들어왔습니다."
    return True, expect, text


def plan_ready(plan, expect):
    """1시간봉 후보의 기준일이 어제 거래일(expect)인가 → (됨, 문장). expect를 모르면 기준일이 있는지만 봄."""
    base = str((plan or {}).get("base") or "")
    if not base:
        return False, "1시간봉 후보(plan)가 없습니다."
    if expect and base != expect:
        return False, (f"1시간봉 후보 기준일 {base[:4]}-{base[4:6]}-{base[6:]}이 어제 거래일 "
                       f"{expect[:4]}-{expect[4:6]}-{expect[6:]}과 달라(낡은 후보) 오늘은 새로 사지 않습니다.")
    return True, f"후보 기준일 {base} 맞음"
