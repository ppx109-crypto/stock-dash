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

    span_days = (min(r["date"] for r in rows), max(r["date"] for r in rows))
    body = {"made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
            "stocks": len(prices), "observations": len(rows), "period": span_days,
            "horizons": list(study.HORIZONS), "groups": groups, "lifts": lifts[:24],
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
    print("\n조건을 더했을 때 상승확률 변화 (A그룹 기준, 위가 큰 순서)")
    for row in lifts[:10]:
        print(f"  {row['잣대']:<22} {row['기간']:>2}일 · "
              f"{row['기준 상승확률']:.1f}% → {row['더한 뒤']:.1f}% "
              f"({row['차이']:+.1f}%p, {row['건수']:,}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
