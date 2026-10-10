# SOURCE-0001 PREREG-LOCK — 분류 규칙 먼저 고정

- 지시: PR #26 head `9bfc62720e1e89b10552268a997bbb6766c9aa48`. source PR #25 head `bb188d57827341463efc24aec9a05c9cd88329f8`.
- 저장소 기준: `origin/main` @`e9a22eea26871fa2a1d8221b04c304d6a3805382`(2026-10-08 09:09 KST 커밋). 이 커밋의 코드 선언 · 스키마 · 경로만 읽고 값은 읽지 않습니다.
- 이 문서는 증거를 모으기 전에 결과 가지의 첫 커밋으로 잠급니다.
- 앞 단계(REPLAY-0002 · DATA-0001)의 결손 판정은 이미 공개된 결과이며, 이번 판정의 사전검정이 아닙니다.

## 1. 항목(TASK 정의 그대로)
- A1: point-in-time OHLCV · 거래대금
- A2: Universe(t), 상장폐지 · 거래정지 · 관리종목 · 합병/분할/이전상장 · 기업행위
- A3: DART `rcept_no`, 공시 시각, 정정 계보, 보고서 기준일 · available_at
- A4: 비식별 모의 신호 · 이론가격 · 실제 체결 · 수수료 · 세금 · 슬리피지 · 미체결
- A5: 시점별 수수료 · 거래세 · 호가/유동성 · 시장충격 비용
- A6: calm cutoff와 일/월 TWR · daily MTM MDD에 필요한 달력 · 지수 · 시장상태

필요하면 항목마다 여러 행(하위 자료)으로 나눕니다.

## 2. 증거 등급(PREREG 우선순위)
- E1: 저장소 정확한 커밋의 코드 · 스키마 · manifest(파일:행)
- E2: KIS · DART · KRX · 법령 공식 문서(URL · 문서명 · 확인 시각 KST)
- E3: 비식별 메타데이터 · coverage 요약. 앞 단계에서 이미 공개된 것만 쓰고, 새로 값을 읽지 않습니다.
- E4: 설명 문서의 주장. E4만 있으면 AVAILABLE로 올리지 않습니다.

## 3. 판정(행마다 하나, 빈 판정 없음)
- `AVAILABLE_EXISTING_READONLY`: 저장소에 이미 있는 자료가 시점 · 버전 · 출처 조건까지 갖춰 그대로 쓸 수 있음(E1 + E3 필요)
- `AVAILABLE_PUBLIC_OFFICIAL`: 공식 공개 출처에 그 필드와 시점 정보가 있음(E2 필요). **endpoint가 있다는 것과 과거 원자료를 확보했다는 것은 다르게 적습니다** — 이 판정은 "받을 수 있음"이지 "보유함"이 아닙니다.
- `NEEDS_USER_APPROVAL`: 공식 출처는 있으나 수집 · 운영 변경 · 키 사용이 필요
- `NEEDS_PAID_OR_LICENSED_SOURCE`: 공식 문서상 유료 · 계약 · 재배포 제한이 확인됨
- `NOT_VERIFIED`: 위 어느 쪽도 증거로 확인하지 못함
- 판정은 행마다 `existing_history`(지금 보유 여부)와 `obtainable`(앞으로 받을 수 있는지)을 따로 적고, 최종 판정은 BASELINE 재현에 가장 가까운 것 하나로 정합니다. 둘이 다르면 둘 다 보입니다.

## 4. 고정 규칙(PREREG)
- 일중 데이터 · 일별 수급 · DART 공시는 실제 확정 · 접수 시각을 available_at으로 둡니다. 날짜만 있으면 다음 거래일부터 씁니다(CLAUDE.md).
- 정정공시는 원 공시와 별도 판으로 둡니다. 현재 생존 종목 목록은 Universe(t)가 아닙니다. 비용은 고정 bps 하나로 완료 판정하지 않습니다.
- 공식 문서 확인은 문서 페이지 읽기만 합니다. 데이터 API는 0회 호출합니다(목록 · 시세 · 공시 조회 포함). 인증이 필요한 페이지는 열지 않고 NOT_VERIFIED로 둡니다.
- 인증은 종류만 적습니다(API key 등). 값 · 계정 · 토큰은 읽거나 적지 않습니다.

## 5. status
- `READY`: A1~A6 모든 행에 판정과 근거가 있고, 결손과 최소 승인 목록이 완전할 때. 데이터 확보나 전략 검증의 READY가 아닙니다.
- `BLOCKED`: 그 밖. `paper_validation_ready=false`, `live_approval=false`
