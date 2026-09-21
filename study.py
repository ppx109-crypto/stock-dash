"""A그룹 조건이 실제로 얼마나 맞았는지 과거 일봉으로 재 봅니다.

무엇을 재는가
    어느 날 종가 기준으로 그룹을 판정하고, 그로부터 5·20·60거래일 뒤의
    수익률을 봅니다. 'A그룹에 든 날 샀다면 어떻게 됐나'를 그대로 세는 것입니다.

무엇을 재지 않는가
    수수료·세금·슬리피지는 넣지 않았습니다. 배당도 넣지 않았습니다. 따라서
    여기 수치는 실제 손익이 아니라 신호의 방향과 크기를 보는 눈금입니다.

조심할 점
    같은 종목의 이어지는 날들은 서로 겹칩니다(오늘 A그룹이면 내일도 대개
    A그룹). 그래서 '몇 번 중 몇 번'의 분모는 독립된 기회의 수가 아닙니다.
    종목 수가 쉰 남짓이라 한 종목의 큰 흐름이 전체를 끌 수 있습니다.
"""
import json
import statistics
from pathlib import Path

import trend

HORIZONS = (5, 20, 60)
PRICES = Path("price-data")
REPORTS = Path("research")


def load_prices(folder=PRICES):
    """종목코드 → [(날짜, 종가)]. 오래된 날이 먼저입니다."""
    found = {}
    for path in sorted(Path(folder).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = [(str(d), float(c)) for d, c in (data.get("closes") or [])
                if c and float(c) > 0]
        if len(rows) >= 120:
            found[str(data.get("code") or path.stem)] = {
                "name": data.get("name") or path.stem, "rows": sorted(rows)}
    return found


def load_reports():
    """종목코드 → 조사 자료. 앱이 읽는 것과 같은 묶음을 그대로 씁니다.

    research 폴더에는 종목별 파일이 아니라 여러 종목을 담은 묶음이 있습니다.
    앱과 같은 경로로 읽어야 화면의 숫자와 여기 숫자가 어긋나지 않습니다.
    """
    try:
        from chat_research import published
        return {str(code): report for code, report in (published() or {}).items()}
    except Exception:
        return {}


def money_axis(report):
    """실적에서 판단에 쓸 세 가지를 꺼냅니다. 없으면 None입니다."""
    money = (report or {}).get("financial") or {}
    if not money:
        return {}
    revenue, prior_revenue = money.get("revenue"), money.get("prior_revenue")
    profit, prior_profit = money.get("operating_profit"), money.get("prior_operating_profit")
    axis = {}
    if revenue and prior_revenue and prior_revenue > 0:
        axis["매출성장"] = (revenue / prior_revenue - 1) * 100
    if profit is not None and prior_profit not in (None, 0) and prior_profit > 0:
        axis["영업이익성장"] = (profit / prior_profit - 1) * 100
    if revenue and profit is not None and revenue > 0:
        axis["영업이익률"] = profit / revenue * 100
    if profit is not None:
        axis["흑자"] = profit > 0
    return axis


def observations(prices, reports, horizons=HORIZONS, warmup=60):
    """하루하루 그룹을 판정하고 그 뒤 수익률을 붙입니다."""
    found = []
    for code, block in prices.items():
        rows = block["rows"]
        axis = money_axis(reports.get(code))
        closes = [c for _, c in rows]
        for i in range(warmup, len(rows) - min(horizons)):
            verdict = trend.assess(closes[: i + 1], None)
            if not verdict.get("group"):
                continue
            ahead = {}
            for span in horizons:
                if i + span < len(rows):
                    ahead[span] = (closes[i + span] / closes[i] - 1) * 100
            if not ahead:
                continue
            found.append({"code": code, "name": block["name"], "date": rows[i][0],
                          "group": verdict["group"], "met": verdict.get("met"),
                          "ahead": ahead, **axis})
    return found


def tally(rows, horizon):
    """한 무리의 승률과 수익률을 냅니다."""
    moves = [r["ahead"][horizon] for r in rows if horizon in r["ahead"]]
    if not moves:
        return None
    wins = sum(1 for m in moves if m > 0)
    return {"건수": len(moves), "상승확률": wins / len(moves) * 100,
            "평균수익률": statistics.fmean(moves),
            "중앙수익률": statistics.median(moves),
            "최악": min(moves), "최고": max(moves)}


def by_group(rows, horizons=HORIZONS):
    found = {}
    for group in ("A", "B", "C"):
        picked = [r for r in rows if r["group"] == group]
        found[group] = {h: tally(picked, h) for h in horizons}
    found["전체"] = {h: tally(rows, h) for h in horizons}
    return found


def split(rows, key, edge, horizons=HORIZONS):
    """한 잣대를 기준으로 위아래를 갈라 봅니다."""
    high = [r for r in rows if isinstance(r.get(key), (int, float)) and r[key] >= edge]
    low = [r for r in rows if isinstance(r.get(key), (int, float)) and r[key] < edge]
    return {f"{key} {edge} 이상": {h: tally(high, h) for h in horizons},
            f"{key} {edge} 미만": {h: tally(low, h) for h in horizons}}


def lift(rows, key, edge, horizon=20):
    """그 잣대를 더했을 때 상승확률이 몇 %포인트 오르는지."""
    base = tally(rows, horizon)
    high = tally([r for r in rows
                  if isinstance(r.get(key), (int, float)) and r[key] >= edge], horizon)
    if not base or not high:
        return None
    return {"잣대": f"{key} ≥ {edge}", "기준 상승확률": base["상승확률"],
            "더한 뒤": high["상승확률"], "차이": high["상승확률"] - base["상승확률"],
            "건수": high["건수"]}
