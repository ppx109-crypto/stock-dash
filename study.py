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


def money_timeline(code, folder="public-data"):
    """그날 이미 공시된 실적만 쓰도록, 발표일이 붙은 목록을 만듭니다.

    오늘의 실적으로 몇 해 전의 날을 판정하면, 그때는 알 수 없던 정보를 쓰는
    것이 됩니다. 그러면 어떤 규칙이든 좋아 보입니다. 그래서 각 결산의 접수
    일자를 함께 들고 다니며, 그날까지 나온 것 중 가장 최근 것만 씁니다.
    """
    try:
        source = json.loads((Path(folder) / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found = []

    def announced(row):
        stamp = str(row.get("receipt") or "")[:8]
        return stamp if len(stamp) == 8 and stamp.isdigit() else None

    years = source.get("years") or []
    for prior, now in zip(years, years[1:]):
        day = announced(now)
        if day:
            found.append((day, _axis(now.get("revenue"), prior.get("revenue"),
                                     now.get("profit"), prior.get("profit"))))
    halves = {h.get("period"): h for h in (source.get("halves") or []) if h.get("period")}
    for period, now in halves.items():
        year, month = period.split("-")
        prior = halves.get(f"{int(year) - 1}-{month}")
        day = announced(now)
        # 기준이 다른 반기끼리는 견주지 않습니다. 누적과 석 달을 섞으면 뒤집힙니다.
        if prior and day and now.get("measure") == prior.get("measure"):
            found.append((day, _axis(now.get("revenue"), prior.get("revenue"),
                                     now.get("profit"), prior.get("profit"))))
    # 같은 날 연간과 반기가 함께 들어오면 날짜만 보고 줄을 세웁니다. 통째로
    # 견주면 뒤에 붙은 실적끼리 비교하려다 멈춥니다.
    found.sort(key=lambda row: row[0])
    return [(day, axis) for day, axis in found if axis]


def _axis(revenue, prior_revenue, profit, prior_profit):
    axis = {}
    if revenue and prior_revenue and prior_revenue > 0:
        axis["매출성장"] = (revenue / prior_revenue - 1) * 100
    if profit is not None and prior_profit is not None and prior_profit > 0:
        axis["영업이익성장"] = (profit / prior_profit - 1) * 100
    if revenue and profit is not None and revenue > 0:
        axis["영업이익률"] = profit / revenue * 100
    if profit is not None:
        axis["흑자"] = profit > 0
    return axis


def known_by(timeline, day):
    """그날까지 나온 것 중 가장 최근 실적. 없으면 빈 칸입니다."""
    found = {}
    for announced, axis in timeline:
        if announced > day:
            break
        found = axis
    return found


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
        timeline = money_timeline(code)
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
            checks = (verdict.get("trend") or {}).get("checks") or {}
            found.append({"code": code, "name": block["name"], "date": rows[i][0],
                          "group": verdict["group"], "met": verdict.get("met"),
                          "ahead": ahead,
                          **{f"위 EMA{span}": bool(checks.get(f"종가 > EMA{span}"))
                             for span in (5, 20, 40, 60)},
                          **known_by(timeline, rows[i][0])})
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


def combo(rows, rules, horizon=20, floor=30):
    """여러 조건을 한꺼번에 걸었을 때를 봅니다.

    실제 투자는 조건을 하나만 보고 하지 않습니다. 'A그룹이면서 매출도 늘고
    영업이익률도 일정 수준 위'처럼 겹쳐 봅니다. 다만 겹칠수록 해당하는 날이
    줄어드므로, 건수가 floor 미만이면 숫자를 내지 않습니다. 적은 표본에서
    나온 높은 확률은 우연과 구분되지 않기 때문입니다.
    """
    picked = rows
    for key, edge in rules:
        picked = [r for r in picked
                  if isinstance(r.get(key), (int, float)) and r[key] >= edge]
    found = tally(picked, horizon)
    if not found or found["건수"] < floor:
        return None
    return {"조건": " + ".join(f"{k} ≥ {e:g}" for k, e in rules), **found}


def worst_case(rows, horizon=20, share=10):
    """가장 나빴던 쪽 몇 퍼센트가 얼마나 잃었는지.

    상승확률만 보면 지는 쪽에서 얼마나 잃는지가 보이지 않습니다. 확률이 높아도
    지는 날의 손실이 크면 전체로는 손해입니다.
    """
    moves = sorted(r["ahead"][horizon] for r in rows if horizon in r["ahead"])
    if len(moves) < 20:
        return None
    cut = max(1, len(moves) * share // 100)
    return {"하위 %d%% 평균" % share: statistics.fmean(moves[:cut]),
            "하위 %d%% 경계" % share: moves[cut - 1]}


# 왕복 비용. 매수·매도 수수료와 매도 시 거래세를 합친 어림값입니다. 정확한
# 값은 증권사와 시장에 따라 다르므로 환경변수로 바꿀 수 있게 둡니다. 비용을
# 빼지 않으면 '이기는 횟수는 많은데 계좌는 줄어드는' 규칙을 좋게 봅니다.
import os
COST = float(os.getenv("ROUND_TRIP_COST", "0.25"))

GRID = (("매출성장", (None, 0.0, 10.0, 20.0)),
        ("영업이익성장", (None, 0.0, 20.0, 50.0)),
        ("영업이익률", (None, 5.0, 10.0, 15.0)))


def net(block, cost=COST):
    """비용을 뺀 기대수익. 한 번 사고 파는 데 드는 값을 뺍니다."""
    return block["평균수익률"] - cost


def search(rows, horizon, floor=60, cost=COST, baseline=None):
    """조건 조합을 모두 훑어, 비용을 뺀 기대수익이 큰 순으로 돌려줍니다.

    상승확률이 높아도 이기는 폭이 작고 지는 폭이 크면 돈이 되지 않습니다.
    그래서 순서는 기대수익으로 매기고, 상승확률은 함께 보여만 줍니다.
    조합이 좁아질수록 해당하는 날이 줄어드니 floor 미만은 버립니다.
    """
    # 이 그룹에서 조건을 걸지 않았을 때가 견줄 자리입니다.
    inside = tally(rows, horizon)
    found = []
    for a in GRID[0][1]:
        for b in GRID[1][1]:
            for c in GRID[2][1]:
                rules = tuple((k, v) for k, v in
                              (("매출성장", a), ("영업이익성장", b), ("영업이익률", c))
                              if v is not None)
                picked = rows
                for key, edge in rules:
                    picked = [r for r in picked
                              if isinstance(r.get(key), (int, float)) and r[key] >= edge]
                block = tally(picked, horizon)
                if not block or block["건수"] < floor:
                    continue
                worst = worst_case(picked, horizon) or {}
                # 몇 종목에서 나온 숫자인지 함께 셉니다. 천 건이라도 두세
                # 종목에서 나왔다면 그 종목들의 사정일 뿐입니다.
                names = {r.get("code") for r in picked if horizon in r.get("ahead", {})}
                found.append({
                    "조건": " + ".join(f"{k} ≥ {e:g}" for k, e in rules) or "조건 없음",
                    "기간": horizon, "건수": block["건수"], "종목수": len(names),
                    "상승확률": round(block["상승확률"], 1),
                    "평균수익률": round(block["평균수익률"], 2),
                    "중앙수익률": round(block["중앙수익률"], 2),
                    "순기대수익": round(net(block, cost), 2),
                    "최악": round(block["최악"], 1),
                    "하위10%": round(worst.get("하위 10% 평균", 0.0), 2),
                    # 그룹대비가 실적 조건이 따로 보탠 몫입니다. 전체대비에는
                    # 그룹을 고른 효과가 섞여 있어, 그것만 보면 실적의 공으로
                    # 잘못 돌리게 됩니다.
                    "그룹대비": (round(net(block, cost) - net(inside, cost), 2)
                               if inside and rules else None),
                    "전체대비": (round(net(block, cost) - net(baseline, cost), 2)
                               if baseline else None)})
    found.sort(key=lambda r: r["순기대수익"], reverse=True)
    return found


# 미리 알 수 있었는지 볼 신호들. 왼쪽이 화면에 적을 이름, 오른쪽이 판정입니다.
SIGNALS = (
    ("정배열(A그룹)", lambda r: r.get("group") == "A"),
    ("EMA 3개 이상 위", lambda r: (r.get("met") or 0) >= 3),
    ("단기선 위(EMA5)", lambda r: r.get("위 EMA5") is True),
    ("장기선 위(EMA60)", lambda r: r.get("위 EMA60") is True),
    ("매출 성장 > 0", lambda r: _at_least(r, "매출성장", 0)),
    ("매출 성장 ≥ 10%", lambda r: _at_least(r, "매출성장", 10)),
    ("매출 성장 ≥ 20%", lambda r: _at_least(r, "매출성장", 20)),
    ("영업이익 성장 > 0", lambda r: _at_least(r, "영업이익성장", 0)),
    ("영업이익 성장 ≥ 50%", lambda r: _at_least(r, "영업이익성장", 50)),
    ("영업이익률 ≥ 10%", lambda r: _at_least(r, "영업이익률", 10)),
    ("영업이익률 ≥ 15%", lambda r: _at_least(r, "영업이익률", 15)),
    ("증권사 목표가 30% 이상 위", lambda r: _at_least(r, "목표가괴리", 30)),
)


def _at_least(row, key, edge):
    value = row.get(key)
    return isinstance(value, (int, float)) and value >= edge


def precursors(rows, horizon=20, rise=5.0, signals=SIGNALS, floor=100):
    """오른 것들에는 무엇이 미리 있었는지 셉니다.

    두 가지를 함께 봐야 합니다. 신호가 있을 때 오른 비율(적중률)과, 오른 것
    가운데 그 신호가 있던 비율(포착률)입니다. 오른 것의 구할에 있던 신호라도
    오르지 않은 것의 구할에도 있었다면 미리 알려 준 것이 없습니다. 그래서
    신호가 없을 때의 비율을 함께 적고, 그 차이로 판단합니다.
    """
    usable = [r for r in rows if horizon in r.get("ahead", {})]
    if len(usable) < floor:
        return []
    rose = [r for r in usable if r["ahead"][horizon] >= rise]
    base = len(rose) / len(usable) * 100
    found = []
    for name, holds in signals:
        marked = [r for r in usable if holds(r)]
        if len(marked) < floor:
            continue
        hit = [r for r in marked if r["ahead"][horizon] >= rise]
        quiet = [r for r in usable if not holds(r)]
        quiet_hit = [r for r in quiet if r["ahead"][horizon] >= rise]
        found.append({
            "신호": name, "해당": len(marked), "종목수": len({r.get("code") for r in marked}),
            "적중률": round(len(hit) / len(marked) * 100, 1),
            "신호없을때": round(len(quiet_hit) / len(quiet) * 100, 1) if quiet else None,
            "포착률": round(len(hit) / len(rose) * 100, 1) if rose else None,
            "기준": round(base, 1)})
    for row in found:
        row["차이"] = (round(row["적중률"] - row["신호없을때"], 1)
                      if row["신호없을때"] is not None else None)
    found.sort(key=lambda r: (r["차이"] is None, -(r["차이"] or 0)))
    return found


def around_filings(prices, span=60, margin_edge=15.0, floor=10):
    """공시를 가운데 두고 앞뒤 수익률을 견줍니다.

    좋은 실적이 이미 주가에 들어가 있었다면, 오름은 공시 앞쪽에 있어야 합니다.
    공시 뒤에만 보면 '실적이 소용없다'로 읽히지만, 실은 그 전에 다 오른
    것일 수 있습니다. 두 쪽을 함께 놓아야 어느 쪽인지 갈립니다.
    """
    buckets = {"좋음": {"before": [], "after": []},
               "보통": {"before": [], "after": []},
               "적자": {"before": [], "after": []}}
    for code, block in prices.items():
        rows = block["rows"]
        days = [d for d, _ in rows]
        closes = [c for _, c in rows]
        for announced, axis in money_timeline(code):
            i = next((k for k, d in enumerate(days) if d >= announced), None)
            if i is None or i < span or i + span >= len(days):
                continue
            rate = axis.get("영업이익률")
            if axis.get("흑자") is False:
                label = "적자"
            elif isinstance(rate, (int, float)) and rate >= margin_edge:
                label = "좋음"
            else:
                label = "보통"
            buckets[label]["before"].append((closes[i] / closes[i - span] - 1) * 100)
            buckets[label]["after"].append((closes[i + span] / closes[i] - 1) * 100)
    found = {}
    for label, sides in buckets.items():
        if len(sides["before"]) < floor:
            continue
        found[label] = {
            "건수": len(sides["before"]),
            "공시전 평균": round(statistics.fmean(sides["before"]), 2),
            "공시전 중앙": round(statistics.median(sides["before"]), 2),
            "공시후 평균": round(statistics.fmean(sides["after"]), 2),
            "공시후 중앙": round(statistics.median(sides["after"]), 2)}
    return found
