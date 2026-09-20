"""수집한 DART 반기 자료를 조사 파일 하나로 묶습니다.

public-data/{종목코드}.json의 halves(반기 누적)에서 올해와 전년 같은 기간을 꺼내
research/public-issuers-{날짜}.json을 다시 씁니다. 화면의 실적 축은 이 파일을
읽으므로, 종목을 새로 수집하면 이 스크립트를 한 번 돌려야 화면에 반영됩니다.

숫자는 옮겨 적지 않고 수집본의 값을 그대로 씁니다. 같은 개월 수의 누적끼리만
비교하고, 두 기간을 맞출 수 없는 종목은 넣지 않습니다.
"""
import json
import re
from datetime import date
from pathlib import Path

from chat_research import parse_bundle

BASIS = {"CFS": "연결", "OFS": "별도"}
SUMMARY = ("{year}년 반기 누적과 전년 같은 누적 기간을 DART 재무제표(누적 열)로 "
           "비교했습니다. 수급·수정주가 추세·적정주가는 이번 조사에서 확인하지 못했습니다.")
DART = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="


def pair(halves):
    """가장 최근 반기와, 한 해 전 같은 달의 반기를 짝지읍니다."""
    by_period = {h["period"]: h for h in halves if h.get("period")}
    for period in sorted(by_period, reverse=True):
        year, month = period.split("-")
        prior = by_period.get(f"{int(year) - 1}-{month}")
        if prior:
            return prior, by_period[period]
    return None, None


def report_for(path):
    source = json.loads(path.read_text(encoding="utf-8"))
    code = str(source.get("code", ""))
    if not re.fullmatch(r"[0-9]{6}", code):
        return None
    prior, now = pair(source.get("halves") or [])
    if not now or not prior:
        return None
    url = DART + str(now.get("receipt", ""))
    basis = BASIS.get(source.get("basis"), "연결")
    return {
        "code": code,
        "name": source.get("name") or code,
        "as_of": date.today().isoformat(),
        "summary": {"text": SUMMARY.format(year=now["period"][:4]), "source": url},
        "financial": {
            "period": now["period"], "prior_period": prior["period"],
            "revenue": now["revenue"], "prior_revenue": prior["revenue"],
            "operating_profit": now["profit"], "prior_operating_profit": prior["profit"],
            "source": url, "basis": basis, "currency": "KRW", "unit": "억원",
        },
        "data_gaps": ["외국인·기관 순매수 미수집", "수정주가 추세 미수집", "적정주가 평가 미수집"],
    }


def build(folder="public-data", out="research"):
    reports = []
    for path in sorted(Path(folder).glob("*.json")):
        if path.name == "market-ranking.json":
            continue
        try:
            found = report_for(path)
        except (ValueError, KeyError, TypeError):
            found = None
        if found:
            reports.append(found)
    bundle = {"schema_version": 1, "reports": sorted(reports, key=lambda r: r["code"])}
    raw = json.dumps(bundle, ensure_ascii=False, indent=1).encode("utf-8")
    parse_bundle(raw)          # 저장하기 전에 같은 잣대로 검증합니다.
    target = Path(out, f"public-issuers-{date.today().isoformat()}.json")
    target.write_bytes(raw)
    return target, len(reports)


if __name__ == "__main__":
    path, count = build()
    print(f"{path} · {count}종목")
