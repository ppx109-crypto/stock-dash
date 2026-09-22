"""조사를 돌려 결과를 파일로 남깁니다. 앱은 그 파일을 읽어 화면에 씁니다."""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import study

OUT = Path("study")
EDGES = (("매출성장", 0.0), ("매출성장", 10.0), ("영업이익성장", 0.0),
         ("영업이익성장", 20.0), ("영업이익률", 5.0), ("영업이익률", 10.0))


def rounded(block):
    if not block:
        return None
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in block.items()}


def main():
    prices = study.load_prices()
    if not prices:
        print("price-data에 일봉이 없습니다. 먼저 수집기를 돌리세요.")
        return 1
    reports = study.load_reports()
    print(f"일봉 {len(prices)}종목 · 조사자료 {len(reports)}종목")
    rows = study.observations(prices, reports)
    print(f"관측 {len(rows):,}건")
    if not rows:
        print("판정할 수 있는 날이 없습니다.")
        return 1

    groups = {g: {str(h): rounded(t) for h, t in spans.items()}
              for g, spans in study.by_group(rows).items()}
    a_rows = [r for r in rows if r["group"] == "A"]
    lifts = []
    for key, edge in EDGES:
        for span in study.HORIZONS:
            found = study.lift(a_rows, key, edge, span)
            if found and found["건수"] >= 30:
                lifts.append({**found, "기간": span,
                              "기준 상승확률": round(found["기준 상승확률"], 2),
                              "더한 뒤": round(found["더한 뒤"], 2),
                              "차이": round(found["차이"], 2)})
    lifts.sort(key=lambda r: r["차이"], reverse=True)

    # 종목마다 오늘의 그룹과, 그 그룹이 과거에 어땠는지를 함께 남깁니다.
    today = []
    for code, block in prices.items():
        closes = [c for _, c in block["rows"]]
        verdict = __import__("trend").assess(closes, None)
        axis = study.money_axis(reports.get(code))
        today.append({"code": code, "name": block["name"], "group": verdict.get("group"),
                      "met": verdict.get("met"), "as_of": block["rows"][-1][0],
                      **{k: (round(v, 2) if isinstance(v, float) else v)
                         for k, v in axis.items()}})
    today.sort(key=lambda r: (r["group"] or "Z", -(r.get("영업이익성장") or -999)))

    # 조건을 겹쳤을 때. 실제 투자는 조건 하나만 보고 하지 않습니다.
    combos = []
    for rules in ((("매출성장", 0.0), ("영업이익률", 5.0)),
                  (("매출성장", 10.0), ("영업이익률", 10.0)),
                  (("영업이익성장", 0.0), ("영업이익률", 5.0)),
                  (("매출성장", 0.0), ("영업이익성장", 0.0)),
                  (("매출성장", 0.0), ("영업이익성장", 0.0), ("영업이익률", 10.0))):
        for span in study.HORIZONS:
            found = study.combo(a_rows, rules, span)
            if found:
                combos.append({"조건": found["조건"], "기간": span, "건수": found["건수"],
                               "상승확률": round(found["상승확률"], 2),
                               "평균수익률": round(found["평균수익률"], 2),
                               "중앙수익률": round(found["중앙수익률"], 2),
                               "최악": round(found["최악"], 2)})
    combos.sort(key=lambda r: (r["기간"], -r["상승확률"]))

    # 지는 쪽이 얼마나 잃는지. 상승확률만 보면 이것이 보이지 않습니다.
    downside = {}
    for group, picked in (("A", a_rows), ("C", [r for r in rows if r["group"] == "C"]),
                          ("전체", rows)):
        for span in study.HORIZONS:
            found = study.worst_case(picked, span)
            if found:
                downside[f"{group}·{span}일"] = {k: round(v, 2) for k, v in found.items()}

    # 실적이 실제로 붙은 관측이 얼마나 되는지. 공시 전 구간은 그룹만 봅니다.
    with_money = sum(1 for r in a_rows if "매출성장" in r)

    # 어떤 조합이 돈이 되는가.
    #
    # 실적 조건은 공시가 나온 뒤 구간에만 붙습니다. 그 구간의 성적을 삼십 년
    # 전체와 견주면, 조건이 좋아서인지 그 시기가 좋아서인지 갈리지 않습니다.
    # 그래서 견줄 자리를 같은 시기로 맞춥니다. 실적이 붙은 가장 이른 날부터의
    # 모든 관측이 기준선입니다.
    known = [r for r in rows if "매출성장" in r or "영업이익률" in r]
    since = min((r["date"] for r in known), default=None)
    window = [r for r in rows if since and r["date"] >= since]
    best = {}
    for group, picked in (("A", a_rows), ("B", [r for r in rows if r["group"] == "B"]),
                          ("C", [r for r in rows if r["group"] == "C"])):
        for span in study.HORIZONS:
            base = study.tally(window, span)
            same_time = [r for r in picked if since and r["date"] >= since]
            found = study.search(same_time, span, baseline=base)
            if found:
                best[f"{group}·{span}일"] = found[:8]

    # 목표가는 한 해치뿐이라, 실적과 같은 격자에 넣으면 겹치는 날이 모자라
    # 늘 탈락합니다. 그래서 목표가가 붙은 구간만 따로 떼어 그 안에서 다시
    # 훑습니다. 견줄 자리도 그 구간의 모든 관측으로 맞춥니다.
    with_target = [r for r in rows if "목표가괴리" in r]
    target_best = {}
    target_since = min((r["date"] for r in with_target), default=None)
    if target_since:
        span_rows = [r for r in rows if r["date"] >= target_since]
        for group, picked in (("전체", with_target),
                              ("A", [r for r in with_target if r["group"] == "A"]),
                              ("C", [r for r in with_target if r["group"] == "C"])):
            for span in study.HORIZONS:
                base = study.tally(span_rows, span)
                found = study.search(picked, span, floor=60, baseline=base)
                if found:
                    target_best[f"{group}·{span}일"] = found[:8]

    # 오른 것들에는 무엇이 미리 있었는가. 물음의 방향이 반대라 따로 셉니다.
    ahead_of = {}
    for span in study.HORIZONS:
        for rise in (5.0, 10.0):
            found = study.precursors(window or rows, span, rise)
            if found:
                ahead_of[f"{span}일 · {rise:g}% 이상"] = found

    # 좋은 실적이 공시 전에 이미 주가에 들어가 있었는지.
    around = study.around_filings(prices)

    span_days = (min(r["date"] for r in rows), max(r["date"] for r in rows))
    body = {"made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
            "stocks": len(prices), "observations": len(rows), "period": span_days,
            "horizons": list(study.HORIZONS), "groups": groups, "lifts": lifts[:24], "combos": combos[:30],
            "downside": downside, "with_money": with_money, "a_total": len(a_rows),
            "best": best, "cost": study.COST, "since": since,
            "target_best": target_best, "target_since": target_since,
            "target_rows": len(with_target),
            "ahead_of": ahead_of, "around": around,
            "window": len(window),
            "today": today}
    OUT.mkdir(exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(body, ensure_ascii=False, indent=1),
                                     encoding="utf-8")

    print(f"\n기간 {span_days[0]}~{span_days[1]}")
    for group, spans in groups.items():
        for span, tal in spans.items():
            if tal:
                print(f"  {group}그룹 {span:>2}일 · {tal['건수']:>6,}건 · "
                      f"상승 {tal['상승확률']:.1f}% · 평균 {tal['평균수익률']:+.2f}%")
    print(f"\nA그룹 관측 {len(a_rows):,}건 중 실적이 이미 공시돼 있던 것 {with_money:,}건")
    print(f"\n돈이 되는 조합 · 견줄 자리도 같은 시기({since}~)로 맞춤 "
          f"· 그 구간 관측 {len(window):,}건 · 왕복 비용 {study.COST}% 차감")
    for key, found in best.items():
        top = found[0]
        print(f"  [{key}] {top['조건']}")
        print(f"      순기대수익 {top['순기대수익']:+.2f}% · 상승 {top['상승확률']:.1f}% · "
              f"중앙 {top['중앙수익률']:+.2f}% · 하위10% {top['하위10%']:+.1f}% · "
              f"{top['건수']:,}건/{top.get('종목수', 0)}종목")
        print(f"      그룹대비 {top['그룹대비']:+.2f}%p"
              if top.get('그룹대비') is not None else "      그룹대비 —",
              f"· 전체대비 {top['전체대비']:+.2f}%p"
              if top.get('전체대비') is not None else "")

    key = f"20일 · 5% 이상"
    if key in ahead_of:
        print(f"\n5% 이상 오르기 전에 무엇이 있었는가 (20거래일 기준)")
        print(f"  {'신호':<22}{'적중률':>8}{'신호없을때':>10}{'차이':>8}{'포착률':>8}  해당")
        for row in ahead_of[key]:
            print(f"  {row['신호']:<22}{row['적중률']:>7.1f}%{row['신호없을때']:>9.1f}%"
                  f"{row['차이']:>+7.1f}%p{row['포착률']:>7.1f}%  {row['해당']:,}건/"
                  f"{row['종목수']}종목")
        print(f"  (아무 날이나 골랐을 때 {ahead_of[key][0]['기준']:.1f}%)")

    if around:
        print("\n공시를 가운데 둔 앞뒤 60거래일 (실적이 미리 들어가 있었는지)")
        for label, block in around.items():
            print(f"  {label:<4} 공시전 중앙 {block['공시전 중앙']:+6.2f}% · "
                  f"공시후 중앙 {block['공시후 중앙']:+6.2f}% · {block['건수']}건")

    if target_best:
        print(f"\n증권사 목표가가 붙은 구간만 ({target_since}~, {len(with_target):,}건)")
        for key, found in target_best.items():
            top = found[0]
            extra = ""
            if top.get("그룹대비") is not None:
                extra += f" · 그룹대비 {top['그룹대비']:+.2f}%p"
            if top.get("전체대비") is not None:
                extra += f" · 전체대비 {top['전체대비']:+.2f}%p"
            print(f"  [{key}] {top['조건']}")
            print(f"      순기대 {top['순기대수익']:+.2f}% · 상승 {top['상승확률']:.1f}% · "
                  f"중앙 {top['중앙수익률']:+.2f}% · 하위10% {top['하위10%']:+.1f}% · "
                  f"{top['건수']:,}건/{top.get('종목수', 0)}종목{extra}")

    print("\n조건을 겹쳤을 때 (A그룹 기준)")
    for row in combos[:12]:
        print(f"  {row['조건']:<40} {row['기간']:>2}일 · 상승 {row['상승확률']:.1f}% · "
              f"평균 {row['평균수익률']:+.2f}% · 최악 {row['최악']:+.1f}% ({row['건수']:,}건)")
    print("\n지는 쪽이 얼마나 잃었는가 (하위 10%)")
    for key, value in downside.items():
        print(f"  {key:<10}", value)
    print("\n조건을 더했을 때 상승확률 변화 (A그룹 기준, 위가 큰 순서)")
    for row in lifts[:10]:
        print(f"  {row['잣대']:<22} {row['기간']:>2}일 · "
              f"{row['기준 상승확률']:.1f}% → {row['더한 뒤']:.1f}% "
              f"({row['차이']:+.1f}%p, {row['건수']:,}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
