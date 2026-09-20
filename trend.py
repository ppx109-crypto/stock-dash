"""일봉 EMA 5·20·40·60으로 A·B·C 그룹을 정합니다.

그룹은 이동평균 하나만 봅니다. 종가가 각 이평선 위에 있는지를 조건 하나로 세고,
넷을 모두 채우면 A, 20·40·60만 채우면 B, 그 밖에는 C입니다. 단기선(EMA5)만
못 채운 상태를 따로 두는 이유는 중기 추세가 살아 있는 눌림과 추세가 꺾인 상태가
전혀 다른 자리이기 때문입니다.

영업이익은 그룹에 넣지 않습니다. 이평선은 매일, 영업이익은 반기마다 바뀌어
한 등급으로 합치면 무엇이 달라졌는지 읽히지 않습니다. 실적은 종목 화면에서
따로 보여 주는 참고 자료로 둡니다.

가격은 공공데이터포털 종가입니다. 수정주가가 아니므로 액면분할·병합 구간에서
이동평균이 왜곡될 수 있어, 하루 사이 가격이 크게 끊기면 세어 둡니다.
"""
from __future__ import annotations

SPANS = (5, 20, 40, 60)
LONG_SPANS = (20, 40, 60)
SPLIT_JUMP = 0.35       # 하루 사이 35% 넘게 끊기면 주가 조정 가능성을 알립니다.
SCREW_VOL_MULTIPLE = 1.6  # 이평선 수렴 안내용. 그룹 판정에는 쓰지 않습니다.

TREND_GRADES = {"정배열": "EMA 4개 모두 충족", "중기정렬": "EMA 20·40·60 충족",
                "혼조": "일부만 충족", "이탈": "EMA 위 없음"}
EARNINGS_GRADES = {"양호": "영업이익 3개 조건 충족", "보통": "1개 미달",
                   "부진": "2개 이상 미달", "미확인": "실적 미수집"}
GROUPS = {
    "A": "투자적기 · EMA 5·20·40·60 모두 위",
    "B": "투자보류 · EMA 20·40·60 위 (단기선만 미달)",
    "C": "대기 · 그 밖의 상태",
}


def ema(values: list[float], span: int) -> list[float]:
    """지수이동평균. 앞쪽 span개의 단순평균으로 시작합니다."""
    if len(values) < span:
        return []
    alpha = 2 / (span + 1)
    out = [sum(values[:span]) / span]
    for value in values[span:]:
        out.append(value * alpha + out[-1] * (1 - alpha))
    return out


def price_breaks(closes: list[float]) -> int:
    """가격이 하루 사이 크게 끊긴 횟수. 수정주가가 아닌 탓일 수 있습니다."""
    return sum(1 for i in range(1, len(closes))
               if closes[i - 1] > 0 and abs(closes[i] - closes[i - 1]) / closes[i - 1] > SPLIT_JUMP)


def daily_volatility(closes: list[float], window: int = 60) -> float:
    """최근 구간의 일간 등락 표준편차. 수렴 안내의 잣대로만 씁니다."""
    recent = closes[-(window + 1):]
    moves = [(recent[i] / recent[i - 1]) - 1 for i in range(1, len(recent)) if recent[i - 1] > 0]
    if len(moves) < 10:
        return 0.0
    mean = sum(moves) / len(moves)
    return (sum((m - mean) ** 2 for m in moves) / (len(moves) - 1)) ** 0.5


def _margin(revenue, profit):
    return profit / revenue if revenue and revenue > 0 and profit is not None else None


def earnings_axis(money: dict | None) -> dict:
    """영업이익·영업이익 증가·영업이익률 개선. 참고용이며 그룹에는 넣지 않습니다."""
    profit = (money or {}).get("operating_profit")
    prior = (money or {}).get("prior_operating_profit")
    if profit is None or prior is None:
        return {"grade": "미확인", "checks": {}, "met": 0, "total": 3,
                "margin": None, "prior_margin": None, "period": None}
    margin, prior_margin = _margin(money.get("revenue"), profit), _margin(money.get("prior_revenue"), prior)
    checks = {
        "영업이익 흑자": profit > 0,
        "영업이익 증가": profit > prior,
        "영업이익률 개선": margin is not None and prior_margin is not None and margin > prior_margin,
    }
    met = sum(checks.values())
    grade = "양호" if met == 3 else ("보통" if met == 2 else "부진")
    return {"grade": grade, "checks": checks, "met": met, "total": 3,
            "margin": round(margin * 100, 2) if margin is not None else None,
            "prior_margin": round(prior_margin * 100, 2) if prior_margin is not None else None,
            "period": f'{money.get("prior_period", "")} → {money.get("period", "")}'.strip(" →")}


def trend_axis(closes: list[float]) -> dict:
    """종가가 EMA 5·20·40·60 각각의 위에 있는지 네 가지를 셉니다."""
    needed = max(SPANS) + 2
    if len(closes) < needed:
        return {"grade": None, "checks": {}, "met": 0, "total": len(SPANS),
                "reason": f"거래일 {len(closes)}개 · {needed}개 이상 필요"}
    lines = {span: ema(closes, span) for span in SPANS}
    now = {span: series[-1] for span, series in lines.items()}
    price = closes[-1]
    checks = {f"종가 > EMA{span}": price > now[span] for span in SPANS}
    met = sum(checks.values())
    long_ok = all(checks[f"종가 > EMA{span}"] for span in LONG_SPANS)
    grade = "정배열" if met == len(SPANS) else ("중기정렬" if long_ok else ("혼조" if met else "이탈"))
    volatility = daily_volatility(closes)
    spread = (max(now.values()) - min(now.values())) / price
    return {"grade": grade, "checks": checks, "met": met, "total": len(SPANS),
            "long_ok": long_ok, "aligned": now[5] > now[20] > now[40] > now[60],
            "slope_up": now[60] > lines[60][-2],
            "screw": spread <= volatility * SCREW_VOL_MULTIPLE if volatility else False,
            "spread": round(spread * 100, 2), "volatility": round(volatility * 100, 2),
            "price": price, "ema": {f"EMA{span}": round(value, 2) for span, value in now.items()},
            "days": len(closes), "price_breaks": price_breaks(closes), "reason": None}


def combine(trend: dict, earnings: dict | None = None) -> str | None:
    """그룹은 이평선만으로 정합니다. 실적은 판정에 넣지 않습니다."""
    if trend["grade"] is None:
        return None
    if trend["met"] == len(SPANS):
        return "A"
    if trend.get("long_ok"):
        return "B"
    return "C"


def assess(closes: list[float], money: dict | None = None) -> dict:
    """가장 최근 시점의 상태를 판정합니다. closes는 과거→최근 순입니다."""
    closes = [float(c) for c in closes if c and c > 0]
    trend = trend_axis(closes)
    earnings = earnings_axis(money)
    group = combine(trend)
    missing = [name for name, ok in trend["checks"].items() if not ok]
    return {"group": group, "reason": GROUPS.get(group, trend.get("reason") or "판정 불가"),
            "trend": trend, "earnings": earnings, "missing": missing,
            "met": trend["met"], "total": trend["total"]}
