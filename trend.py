"""추세와 실적을 각각 등급으로 매기고, 둘을 조합해 A·B·C·D 그룹을 정합니다.

두 축을 따로 두는 이유는 성격이 다르기 때문입니다. 이동평균은 매일 바뀌고
영업이익은 반기마다 바뀝니다. 한 점수로 합치면 추세가 만점인데 실적이 미달인
종목과 그 반대인 종목이 같은 등급으로 묶여, 무엇이 문제인지 읽히지 않습니다.

추세축은 이동평균 다섯 조건, 실적축은 영업이익 세 조건으로 봅니다.
이평선이 서로 붙은 수렴(스크류) 구간은 대소 비교가 노이즈라 정배열로 읽지 않고
방향 대기로 따로 둡니다. 그래서 조건을 못 채웠다고 모두 같은 그룹이 되지는 않습니다.

가격은 공공데이터포털 종가입니다. 수정주가가 아니므로 액면분할·병합 구간에서
이동평균이 왜곡될 수 있어, 하루 사이 가격이 크게 끊기면 세어 둡니다.
"""
from __future__ import annotations

SPANS = (5, 20, 40, 60)
SCREW_BAND = 0.025      # 이평선 간격이 종가의 2.5% 안이면 수렴으로 봅니다.
SPLIT_JUMP = 0.35       # 하루 사이 35% 넘게 끊기면 주가 조정 가능성을 알립니다.

TREND_GRADES = {"정배열": "EMA 5개 조건 충족", "근접": "1~2개 미달",
                "스크류": "이평선 수렴 · 방향 대기", "역배열": "3개 이상 미달"}
EARNINGS_GRADES = {"양호": "영업이익 3개 조건 충족", "보통": "1개 미달",
                   "부진": "2개 이상 미달", "미확인": "실적 미수집"}
GROUPS = {
    "A": "투자적기 · 정배열 + 실적 양호",
    "B": "투자보류 · 한 축이 조금 모자람",
    "C": "대기 · 이평선 수렴(스크류)",
    "D": "관망 · 추세 붕괴 또는 실적 부진",
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


def _margin(revenue, profit):
    return profit / revenue if revenue and revenue > 0 and profit is not None else None


def earnings_axis(money: dict | None) -> dict:
    """영업이익·영업이익 증가·영업이익률 개선 세 가지를 봅니다."""
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
    """이동평균 다섯 조건과 수렴 여부를 봅니다."""
    needed = max(SPANS) + 2
    if len(closes) < needed:
        return {"grade": None, "checks": {}, "met": 0, "total": 5,
                "reason": f"거래일 {len(closes)}개 · {needed}개 이상 필요"}
    lines = {span: ema(closes, span) for span in SPANS}
    now = {span: series[-1] for span, series in lines.items()}
    price = closes[-1]
    slope = now[60] - lines[60][-2]
    spread = (max(now.values()) - min(now.values())) / price
    checks = {
        "종가 > EMA5": price > now[5],
        "EMA5 > EMA20": now[5] > now[20],
        "EMA20 > EMA40": now[20] > now[40],
        "EMA40 > EMA60": now[40] > now[60],
        "EMA60 상승": slope > 0,
    }
    met = sum(checks.values())
    screw = spread <= SCREW_BAND
    grade = "스크류" if screw else ("정배열" if met == 5 else ("근접" if met >= 3 else "역배열"))
    return {"grade": grade, "checks": checks, "met": met, "total": 5, "screw": screw,
            "spread": round(spread * 100, 2), "slope_up": slope > 0, "price": price,
            "ema": {f"EMA{span}": round(value, 2) for span, value in now.items()},
            "days": len(closes), "price_breaks": price_breaks(closes), "reason": None}


def combine(trend: dict, earnings: dict) -> str | None:
    """두 축을 조합해 그룹을 정합니다. 실적을 모르면 A로 올리지 않습니다."""
    if trend["grade"] is None:
        return None
    if trend["grade"] == "스크류":
        return "C"
    if trend["grade"] == "역배열" or earnings["grade"] == "부진":
        return "D"
    if trend["grade"] == "정배열" and earnings["grade"] == "양호":
        return "A"
    return "B"


def assess(closes: list[float], money: dict | None = None) -> dict:
    """가장 최근 시점의 상태를 판정합니다. closes는 과거→최근 순입니다."""
    closes = [float(c) for c in closes if c and c > 0]
    trend = trend_axis(closes)
    earnings = earnings_axis(money)
    group = combine(trend, earnings)
    missing = [name for name, ok in {**trend["checks"], **earnings["checks"]}.items() if not ok]
    return {"group": group, "reason": GROUPS.get(group, trend.get("reason") or "판정 불가"),
            "trend": trend, "earnings": earnings, "missing": missing,
            "met": trend["met"] + earnings["met"], "total": trend["total"] + earnings["total"]}
