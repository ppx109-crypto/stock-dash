"""거래소에서 과거 수급을 받아올 수 있는지 먼저 찔러 봅니다.

증권사 투자자 API는 최근 며칠만 줍니다. 그래서 수급 자료가 8월 12일부터
서른 거래일치뿐입니다. 지금 규칙은 한 해 열여섯 번 매매하므로 서른 거래일
이면 한두 건입니다 — 예순 건 문턱을 넘으려면 사 년이 걸립니다. 쌓기를
기다리는 것은 답이 아닙니다.

거래소는 같은 것을 과거치까지 공개합니다. 다만 응답 형태를 문서로 확인할
길이 없어, 받아 보고 그대로 찍는 것부터 합니다. 이 파일은 무엇을 어떻게
받을 수 있는지 알아내기 위한 것이고, 알아낸 뒤에 제대로 된 수집기를
만듭니다.

조회 전용입니다. 주문과 무관합니다.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

WHERE = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
FROM = ("http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd"
        "?menuId=MDC0201020403")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "Referer": FROM,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


def ask(body, seconds=30):
    """거절당해도 본문을 읽습니다. 거래소는 까닭을 본문에 적어 줍니다."""
    data = urllib.parse.urlencode(body, encoding="utf-8").encode()
    call = urllib.request.Request(WHERE, data=data, headers=HEADERS)
    try:
        with urllib.request.urlopen(call, timeout=seconds) as answer:
            return answer.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as refused:
        body = refused.read().decode("utf-8", "replace")
        return f"[HTTP {refused.code}] {body}"


def show(tag, body, cut=1200):
    print(f"\n=== {tag} ===")
    print("보낸 것:", json.dumps(body, ensure_ascii=False))
    try:
        got = ask(body)
    except Exception as trouble:            # 무엇이든 그대로 보고 판단합니다
        print("실패:", type(trouble).__name__, str(trouble)[:200])
        return None
    print("받은 것 앞부분:", got[:cut])
    try:
        return json.loads(got)
    except ValueError:
        print("(JSON이 아닙니다)")
        return None


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "005930"

    # 1) 종목코드로 표준코드(ISIN)를 찾습니다. 거래소 조회는 이것을 씁니다.
    found = show("종목 찾기", {
        "bld": "dbms/comm/finder/finder_stkisu",
        "mktsel": "ALL", "typeNo": "0", "searchText": code,
    })
    isin = None
    if isinstance(found, dict):
        rows = found.get("block1") or found.get("output") or []
        for row in rows if isinstance(rows, list) else []:
            if str(row.get("short_code") or "").endswith(code):
                isin = row.get("full_code")
                break
        if isin is None and rows:
            isin = (rows[0] or {}).get("full_code")
    print("\n찾은 표준코드:", isin)

    # 2) 개별 종목의 일별 투자자별 거래실적. 어느 화면 번호인지 모르므로
    #    후보를 차례로 물어보고, 거절당하면 그 까닭을 읽습니다.
    common = {"locale": "ko_KR", "isuCd": isin or "", "isuCd2": isin or "",
              "strtDd": "20240102", "endDd": "20240131",
              "share": "1", "money": "1", "csvxls_isNo": "false"}
    for number in ("02203", "02301", "02303", "02403", "02103"):
        bld = f"dbms/MDC/STAT/standard/MDCSTAT{number}"
        show(f"후보 {number} · 단출하게", {"bld": bld, **common}, cut=600)
        show(f"후보 {number} · 갈래를 채워서", {
            "bld": bld, **common,
            "inqTpCd": "2", "trdVolVal": "2", "askTrdClssCd": "1",
            "detailView": "1", "mktId": "ALL", "invstTpCd": "9999",
            "tboxisuCd_finder_stkisu0_0": code,
            "codeNmisuCd_finder_stkisu0_0": "", "param1isuCd_finder_stkisu0_0": "ALL",
        }, cut=600)
    return 0


if __name__ == "__main__":
    sys.exit(main())
