from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import requests


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    name: str
    capabilities: tuple[str, ...]
    env_keys: tuple[str, ...] = field(default_factory=tuple)


PROVIDERS = (
    ProviderSpec(
        "opendart",
        "OpenDART",
        (
            "stock.profile",
            "stock.financials",
            "stock.disclosures",
            "stock.business_report",
        ),
        ("DART_CRTFC_KEY",),
    ),
    ProviderSpec(
        "data_go_kr_stock",
        "금융위원회 주식시세정보",
        ("stock.search", "stock.quote"),
        ("DATA_GO_KR_SERVICE_KEY",),
    ),
    ProviderSpec(
        "kiwoom_rest",
        "키움 REST API · 국내주식 시세",
        ("stock.live_quote",),
        ("KIWOOM_APP_KEY", "KIWOOM_APP_SECRET"),
    ),
)


def configured(spec: ProviderSpec) -> bool:
    return all(bool(os.getenv(key, "").strip()) for key in spec.env_keys)


def capabilities() -> set[str]:
    active = set()
    for spec in PROVIDERS:
        if configured(spec):
            active.update(spec.capabilities)
    return active


def _result(provider_id: str, status: str, detail: str, started: float):
    return {
        "provider_id": provider_id,
        "status": status,
        "detail": detail,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "checked_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
    }


def health(spec: ProviderSpec) -> dict:
    started = time.perf_counter()
    if not configured(spec):
        return _result(spec.provider_id, "not_configured", "인증정보 미설정", started)

    try:
        if spec.provider_id == "opendart":
            key = os.getenv("DART_CRTFC_KEY", "").strip()
            response = requests.get(
                "https://opendart.fss.or.kr/api/company.json",
                params={"crtfc_key": key, "corp_code": "00126380"},
                timeout=(5, 12),
            )
            response.raise_for_status()
            payload = response.json()
            code = str(payload.get("status", ""))
            if code == "000":
                return _result(spec.provider_id, "ok", "연결·인증 정상", started)
            known = {
                "010": "키 미등록",
                "011": "키 사용 중지",
                "012": "IP 제한",
                "020": "호출 한도 초과",
                "013": "연결됨 · 자료 없음",
                "800": "기관 점검 중",
            }
            return _result(spec.provider_id, "error", known.get(code, f"응답코드 {code or '확인 필요'}"), started)

        if spec.provider_id == "data_go_kr_stock":
            from providers import price_call, DataError
            key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
            try:
                payload = price_call("getStockPriceInfo",
                                     {"serviceKey": key, "resultType": "json", "numOfRows": 1})
            except DataError as error:
                text = str(error)
                for mark, reason in (("SERVICE_KEY_IS_NOT_REGISTERED", "등록되지 않은 서비스키"),
                                     ("LIMITED_NUMBER_OF_SERVICE_REQUESTS", "호출 한도 초과"),
                                     ("SERVICE_ACCESS_DENIED", "활용 신청 승인 대기"),
                                     ("DEADLINE_HAS_EXPIRED", "서비스키 사용 기간 만료")):
                    if mark in text:
                        return _result(spec.provider_id, "error", reason, started)
                return _result(spec.provider_id, "error", text[:80], started)
            header = payload.get("response", {}).get("header", {})
            code = str(header.get("resultCode", ""))
            if code in {"00", "0"}:
                return _result(spec.provider_id, "ok", "연결·인증 정상", started)
            message = str(header.get("resultMsg", "")).strip()
            return _result(spec.provider_id, "error",
                           f"응답코드 {code or '확인 필요'}" + (f" · {message}" if message else ""), started)

        if spec.provider_id == "kiwoom_rest":
            # 토큰만 받아보고 끝냅니다. 시세·주문은 호출하지 않습니다.
            import quotes
            mode = os.getenv("KIWOOM_ENV", "real").strip() or "real"
            try:
                quotes.Kiwoom().authorize()
                return _result(spec.provider_id, "ok", f"토큰 발급 정상 · {quotes.LABEL.get(mode, mode)} 서버", started)
            except quotes.QuoteError as error:
                detail = str(error)
            # 키가 반대쪽 서버의 것이면 바로 알려줍니다.
            other = "mock" if mode == "real" else "real"
            try:
                client = quotes.Kiwoom()
                client.base, client.mode = (quotes.MOCK if other == "mock" else quotes.REAL), other
                client.authorize()
            except Exception:
                return _result(spec.provider_id, "error", detail, started)
            return _result(spec.provider_id, "error",
                           f"이 키는 {quotes.LABEL[other]} 서버에서 인증됩니다. "
                           f'KIWOOM_ENV를 "{other}"로 바꾸세요.', started)

        return _result(spec.provider_id, "unknown", "진단 미구현", started)
    except requests.Timeout:
        return _result(spec.provider_id, "error", "응답 시간 초과", started)
    except requests.exceptions.SSLError:
        return _result(spec.provider_id, "error", "TLS 보안 연결 실패", started)
    except requests.ConnectionError:
        return _result(spec.provider_id, "error", "네트워크 연결 실패", started)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return _result(spec.provider_id, "error", "정상 응답을 확인하지 못함", started)


def health_all() -> list[dict]:
    return [{**health(spec), "name": spec.name, "capabilities": list(spec.capabilities)} for spec in PROVIDERS]


def missing_capabilities(required: list[str] | tuple[str, ...]) -> list[str]:
    active = capabilities()
    return [cap for cap in required if cap not in active]
