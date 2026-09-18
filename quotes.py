"""키움 REST API 국내주식 시세. 조회 전용이며 주문 기능은 두지 않습니다.

토큰 발급은 POST /oauth2/token, 시세는 POST /api/dostk/stkinfo (api-id ka10001)입니다.
키가 없으면 호출하지 않고 연결 안 됨 상태만 돌려줍니다.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

PUBLIC_PRICE = ("https://apis.data.go.kr/1160100/service/"
                "GetStockSecuritiesInfoService/getStockPriceInfo")
REAL = "https://api.kiwoom.com"
MOCK = "https://mockapi.kiwoom.com"
LABEL = {"real": "실전", "mock": "모의"}


class QuoteError(RuntimeError):
    pass


def _number(value):
    """키움 수치는 '+72,400'처럼 부호와 쉼표가 붙어 옵니다."""
    try:
        text = str(value).replace(",", "").strip()
        if not text or text in ("+", "-"):
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


class Kiwoom:
    def __init__(self):
        self.key = os.getenv("KIWOOM_APP_KEY", "").strip()
        self.secret = os.getenv("KIWOOM_APP_SECRET", "").strip()
        self.mode = os.getenv("KIWOOM_ENV", "real").strip()
        if not self.key or not self.secret:
            raise QuoteError("키움 앱키와 시크릿키를 설정하세요.")
        if self.mode not in ("real", "mock"):
            raise QuoteError("KIWOOM_ENV는 real 또는 mock으로 입력하세요.")
        self.base = REAL if self.mode == "real" else MOCK
        self.token = None
        self.expires = 0.0

    def authorize(self):
        if self.token and time.time() < self.expires:
            return
        try:
            response = requests.post(self.base + "/oauth2/token", timeout=(5, 20),
                headers={"Content-Type": "application/json;charset=UTF-8"},
                json={"grant_type": "client_credentials", "appkey": self.key, "secretkey": self.secret})
            data = response.json() if response.content else {}
        except (requests.RequestException, ValueError):
            raise QuoteError("키움 인증 요청이 실패했습니다. 네트워크와 서비스 상태를 확인하세요.") from None
        if not isinstance(data, dict):
            raise QuoteError(f"키움 인증 응답 형식을 읽을 수 없습니다 · HTTP {response.status_code}")
        token = data.get("token") or data.get("access_token")
        if not token:
            # 키움이 알려준 사유를 그대로 전달합니다.
            reason = str(data.get("return_msg") or data.get("message") or "").strip()
            code = data.get("return_code")
            detail = f"HTTP {response.status_code}"
            if code not in (None, ""):
                detail += f" · 코드 {code}"
            if reason:
                detail += f" · {reason}"
            raise QuoteError(f"키움이 토큰을 돌려주지 않았습니다 ({detail}). "
                             f"현재 {LABEL.get(self.mode, self.mode)} 서버로 요청했습니다.")
        self.token = token
        # 만료 시각 형식이 바뀌어도 동작하도록 짧게 잡고 갱신합니다.
        self.expires = time.time() + 1800

    def quote(self, code: str) -> dict:
        self.authorize()
        try:
            response = requests.post(self.base + "/api/dostk/stkinfo", timeout=(5, 15),
                headers={"Content-Type": "application/json;charset=UTF-8", "api-id": "ka10001",
                         "cont-yn": "N", "next-key": "", "authorization": "Bearer " + self.token},
                json={"stk_cd": code})
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            raise QuoteError("키움 시세 조회에 실패했습니다.") from None
        if not isinstance(data, dict) or data.get("return_code") not in (0, "0"):
            raise QuoteError(str(data.get("return_msg") or "키움이 시세를 돌려주지 않았습니다."))
        price = _number(data.get("cur_prc"))
        if price is None:
            raise QuoteError("시세 응답에 현재가가 없습니다.")
        change = _number(data.get("pred_pre")) or _number(data.get("prdy_vrss"))
        rate = _number(data.get("flu_rt")) or _number(data.get("prdy_ctrt"))
        return {"code": code, "name": (data.get("stk_nm") or "").strip(),
                "price": abs(price), "change": change, "rate": rate}


def public_rows(codes) -> tuple[list, str]:
    """공공데이터포털 주식시세. 실시간이 아니라 마지막 거래일 종가입니다."""
    from urllib.parse import unquote
    key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
    if not key:
        raise QuoteError("공공데이터포털 인증키를 설정하세요.")
    rows, basis_date = [], ""
    for code in codes:
        row = None
        for back in range(10):
            target = (datetime.now(ZoneInfo("Asia/Seoul")).date() - timedelta(days=back)).strftime("%Y%m%d")
            try:
                payload = requests.get(PUBLIC_PRICE, timeout=(5, 15), params={
                    "serviceKey": key, "resultType": "json", "numOfRows": 50,
                    "basDt": target, "likeSrtnCd": code}).json()
                header = payload["response"]["header"]
            except (requests.RequestException, ValueError, KeyError, TypeError):
                raise QuoteError("공공데이터포털 시세 응답을 읽지 못했습니다.") from None
            if str(header.get("resultCode")) not in ("00", "0"):
                raise QuoteError("공공데이터포털: " + str(header.get("resultMsg") or "인증키와 활용 신청 상태를 확인하세요."))
            items = (payload["response"].get("body", {}).get("items") or {}).get("item", [])
            if isinstance(items, dict):
                items = [items]
            for item in items:
                if str(item.get("srtnCd", "")).removeprefix("A").zfill(6) == str(code):
                    row = item
                    break
            if row:
                break
        if not row:
            continue
        price = _number(row.get("clpr"))
        if price is None or price <= 0:
            continue
        basis_date = str(row.get("basDt") or basis_date)
        rows.append({"code": code, "name": (row.get("itmsNm") or "").strip(), "price": abs(price),
                     "change": _number(row.get("vs")), "rate": _number(row.get("fltRt"))})
    label = "전일 종가 · 공공데이터포털"
    if basis_date and len(basis_date) == 8:
        label += f" · {basis_date[:4]}-{basis_date[4:6]}-{basis_date[6:]} 기준"
    return rows, label


def snapshot(codes) -> dict:
    """여러 종목 시세를 한 번에 읽습니다. 실패한 종목은 빼고 돌려줍니다."""
    codes = [c for c in codes if c and not str(c).startswith("pending-")]
    if not codes:
        return {"rows": [], "state": "종목 없음", "at": None}
    codes = codes[:12]
    try:
        client = Kiwoom()
    except QuoteError as kiwoom_error:
        # 키움 키가 없으면 공공데이터포털 종가로 대신합니다.
        try:
            rows, label = public_rows(codes)
        except QuoteError as public_error:
            return {"rows": [], "state": f"{kiwoom_error} / {public_error}", "at": None}
        at = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%H:%M:%S")
        if not rows:
            return {"rows": [], "state": "공공데이터포털에서 최근 10일 시세를 찾지 못했습니다.", "at": at}
        return {"rows": rows, "state": label, "at": at, "mode": "public"}
    rows, failed = [], 0
    for code in codes:
        try:
            rows.append(client.quote(code))
        except QuoteError:
            failed += 1
    at = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%H:%M:%S")
    if not rows:
        return {"rows": [], "state": "시세를 받지 못했습니다. 키움 사용 신청과 키 종류를 확인하세요.", "at": at}
    # 모의 서버 값은 실제 체결가와 다를 수 있으므로 반드시 구분해 보여줍니다.
    state = "실시간 · 키움 실전" if client.mode == "real" else "키움 모의 서버 · 실제 시세와 다를 수 있음"
    if failed:
        state += f" · {failed}개 실패"
    return {"rows": rows, "state": state, "at": at, "mode": client.mode}
