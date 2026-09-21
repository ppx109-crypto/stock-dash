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
    ProviderSpec(
        "kis_domestic",
        "한국투자증권 · 증권사 목표주가·실시간 시세",
        ("stock.opinion", "stock.live_quote"),
        ("KIS_APP_KEY", "KIS_APP_SECRET"),
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


def _dart_fallback(started: float) -> dict:
    """DART로 나가는 길이 막힌 서버에서 도는 경우를 가려냅니다.

    클라우드 서버에서는 DART 연결 자체가 열리지 않는 일이 있습니다. 그때도 앱은
    GitHub에 모아 둔 수집본으로 자료를 받으므로, 키가 잘못된 것처럼 적으면 안
    됩니다. 수집본이 실제로 닿는지 확인하고 사실대로 적습니다.
    """
    from providers import public_data_bases
    for base in public_data_bases():
        try:
            probe = requests.get(base + "005930.json", timeout=(5, 10))
            if probe.status_code == 200 and probe.json().get("code"):
                return _result("opendart", "fallback",
                               "이 서버에서 DART로 직접 나가는 연결이 열리지 않습니다. "
                               "키 문제가 아니며, 자료는 GitHub 수집본에서 받고 있습니다.", started)
        except (requests.RequestException, ValueError):
            continue
    return _result("opendart", "error",
                   "DART에 닿지 않고 수집본도 받지 못했습니다. 잠시 뒤 다시 눌러 보세요.", started)


def health(spec: ProviderSpec) -> dict:
    started = time.perf_counter()
    if not configured(spec):
        return _result(spec.provider_id, "not_configured", "인증정보 미설정", started)

    try:
        if spec.provider_id == "opendart":
            key = os.getenv("DART_CRTFC_KEY", "").strip()
            # 자료를 실제로 받을 때와 같은 여유를 줍니다. 진단만 빡빡하면 멀쩡한
            # 키가 '확인 필요'로 보입니다. 한 번 늦으면 한 번 더 불러 봅니다.
            payload = None
            for attempt in (1, 2):
                try:
                    response = requests.get(
                        "https://opendart.fss.or.kr/api/company.json",
                        params={"crtfc_key": key, "corp_code": "00126380"},
                        timeout=(10, 30),
                    )
                    response.raise_for_status()
                    payload = response.json()
                    break
                except (requests.Timeout, requests.ConnectionError):
                    if attempt == 2:
                        return _dart_fallback(started)
                    time.sleep(1.5)
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

        if spec.provider_id == "kis_domestic":
            # 토큰을 받고, 삼성전자 현재가·투자의견을 한 번씩 읽어 승인 상태까지 봅니다.
            import broker_kis
            mode = os.getenv("KIS_ENV", "demo").strip() or "demo"
            label = {"real": "실전", "demo": "모의"}.get(mode, mode)
            try:
                # 토큰을 아껴 씁니다. 누를 때마다 새로 발급받으면 증권사가 발급을
                # 제한해, 멀쩡한 키가 인증 실패로 보입니다.
                client = broker_kis.market()
                client.authorize()
            except broker_kis.BrokerError as error:
                return _result(spec.provider_id, "error", f"{label} 서버 인증 실패 · {error}"[:120], started)
            notes = []
            try:
                client.quote("005930")
                notes.append("실시간 시세 정상")
            except broker_kis.BrokerError as error:
                notes.append(f"실시간 시세 미승인 ({error})"[:70])
            try:
                found = client.opinions("005930", days=180)
                notes.append(f"투자의견 {len(found)}건")
            except broker_kis.BrokerError as error:
                notes.append(f"투자의견 미승인 ({error})"[:70])
            status = "ok" if all("미승인" not in note for note in notes) else "error"
            return _result(spec.provider_id, status, f"{label} 서버 · " + " · ".join(notes), started)

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
