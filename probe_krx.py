"""거래소에서 과거 수급을 받아올 수 있는지 찔러 봅니다.

증권사 투자자 API는 최근 며칠만 줍니다. 그래서 수급 자료가 서른 거래일치
뿐입니다. 지금 규칙은 한 해 열여섯 번 매매하므로 예순 건 문턱을 넘으려면
사 년이 걸립니다. 쌓기를 기다리는 것은 답이 아닙니다.

거래소는 같은 것을 과거치까지 공개하는데, 어느 문으로 어떻게 물어야 하는지
문서로 확인할 길이 없습니다. 그래서 받아 보고 그대로 찍습니다. 한 번 돌 때
여러 길을 함께 물어, 왔다 갔다 하는 횟수를 줄입니다.

조회 전용입니다. 주문과 무관하고 아무것도 저장하지 않습니다.
"""
from __future__ import annotations

import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HOME = "http://data.krx.co.kr"
JSON_DOOR = f"{HOME}/comm/bldAttendant/getJsonData.cmd"
OTP_DOOR = f"{HOME}/comm/fileDn/GenerateOTP.jspx"
FILE_DOOR = f"{HOME}/comm/fileDn/download_csv/download.cmd"
AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/120 Safari/537.36")
BASKET = http.cookiejar.CookieJar()
JAR = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(BASKET))


def screen(menu):
    return f"{HOME}/contents/MDC/MDI/mdiLoader/index.cmd?menuId={menu}"


def get(where, referer=None, seconds=30):
    headers = {"User-Agent": AGENT, "Accept-Language": "ko,en;q=0.9"}
    if referer:
        headers["Referer"] = referer
    try:
        with JAR.open(urllib.request.Request(where, headers=headers),
                      timeout=seconds) as answer:
            return answer.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as refused:
        return f"[HTTP {refused.code}] " + refused.read().decode("utf-8", "replace")
    except Exception as trouble:
        return f"[{type(trouble).__name__}] {str(trouble)[:160]}"


def post(where, body, referer, seconds=30):
    data = urllib.parse.urlencode(body, encoding="utf-8").encode()
    headers = {"User-Agent": AGENT, "Referer": referer,
               "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
               "X-Requested-With": "XMLHttpRequest",
               "Accept": "application/json, text/javascript, */*; q=0.01"}
    try:
        with JAR.open(urllib.request.Request(where, data=data, headers=headers),
                      timeout=seconds) as answer:
            return answer.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as refused:
        return f"[HTTP {refused.code}] " + refused.read().decode("utf-8", "replace")
    except Exception as trouble:
        return f"[{type(trouble).__name__}] {str(trouble)[:160]}"


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "005930"

    print("=== 1. 첫 화면을 열어 쿠키를 받습니다 ===")
    front = get(screen("MDC0201020403"))
    print("길이", len(front), "· 쿠키", [c.name for c in BASKET])
    print("앞부분:", front[:200].replace("\n", " "))
    seen = sorted(set(re.findall(r"MDCSTAT\d{5}", front)))
    print("화면 HTML에서 본 번호:", seen[:20] or "없음")

    print("\n=== 2. 통계 문이 세션을 받아들이는지 (쉬운 화면으로) ===")
    print("받은 것:", post(JSON_DOOR, {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT01501", "locale": "ko_KR",
        "mktId": "ALL", "trdDd": "20240102",
        "share": "1", "money": "1", "csvxls_isNo": "false",
    }, screen("MDC0201020101"))[:300].replace("\n", " "))

    print("\n=== 3. 파일 내려받기 문 (OTP) ===")
    otp = get(OTP_DOOR + "?" + urllib.parse.urlencode({
        "locale": "ko_KR", "mktId": "ALL", "trdDd": "20240102",
        "share": "1", "money": "1", "csvxls_isNo": "false",
        "name": "fileDown", "url": "dbms/MDC/STAT/standard/MDCSTAT01501",
    }), referer=screen("MDC0201020101"))
    print("OTP:", otp[:160].replace("\n", " "))
    if otp and not otp.startswith("["):
        print("파일 앞부분:", post(FILE_DOOR, {"code": otp},
                              screen("MDC0201020101"))[:300].replace("\n", " "))

    print("\n=== 4. 종목 찾기 (세션 없이도 되던 문) ===")
    found = post(JSON_DOOR, {"bld": "dbms/comm/finder/finder_stkisu", "mktsel": "ALL",
                             "typeNo": "0", "searchText": code},
                 screen("MDC0201020403"))
    print("받은 것:", found[:220].replace("\n", " "))
    isin = ""
    try:
        rows = json.loads(found).get("block1") or []
        isin = next((r["full_code"] for r in rows
                     if str(r.get("short_code")) == code), rows[0]["full_code"])
    except Exception:
        pass
    print("표준코드:", isin or "못 찾음")

    print("\n=== 5. 개별종목 투자자별 거래실적 ===")
    for number in ("02303", "02203", "02403"):
        got = post(JSON_DOOR, {
            "bld": f"dbms/MDC/STAT/standard/MDCSTAT{number}", "locale": "ko_KR",
            "isuCd": isin, "isuCd2": isin, "strtDd": "20240102", "endDd": "20240131",
            "inqTpCd": "2", "trdVolVal": "2", "askTrdClssCd": "1", "detailView": "1",
            "share": "1", "money": "1", "csvxls_isNo": "false",
        }, screen("MDC0201020403"))
        print(f"  {number}:", got[:260].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
