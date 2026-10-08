# TASK — BASELINE-PIT-EXPOSURE-0001

- task_id: `BASELINE-PIT-EXPOSURE-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 18
- status: `READY`
- source_pr: 78
- source_head_sha: `c8fa5cf240ee25268a1963ead1c59e054a50eefe`
- 단계: `BASELINE`
- 목적: PR #78 고친 후보의 실제 Train 신호·결정·체결이 수급/공시 available_at, 수정주가, Universe(t)·거래정지·기업행동 결손에 얼마나 노출됐는지 직접 계수한다.

## 입력 고정

1. PR #78 결과·코드·로컬 원장 해시 `a22098a1…d703`
2. PR #76 일봉 고침 원장 해시 `0619fd23…51d8`
3. PR #68 저장 입력/체결과 고정 엔진
4. PR #21 `DATA-0001/COLLECTOR-MAPPING.md`, `GAP-TRACEABILITY.json`
5. PR #29 `SOURCE-VERIFY-0001/REPORT.md`, `OFFICIAL-SOURCE-MATRIX.json`
6. Train 2025-09-18~2026-03-31만. 신규 수집이나 성과 재실행은 하지 않는다.

모든 입력 경로·git SHA·sha256을 기록하고, 집계 전에 `PREREG.md`를 별도 커밋한다.

## 계산 범위

### 1. 실제 의존 그래프

D1, M15, ETF, BASKET 각각에 대해 코드에서 다음을 역추적한다.

- 신호 원료와 lookback/cutoff
- 진입·청산·노출·종목선정에 사용되는 가격, 수급, 공시, Universe/시총, 거래정지/기업행동
- 신호 결정 시각과 필요한 각 입력의 최신 허용 `available_at`
- 체결·평가 가격의 raw/adjusted basis

각 의존을 `REQUIRED`, `NOT_USED`, `UNKNOWN_CODE_PATH`로 분류하고 코드 줄을 남긴다.

### 2. Train 실측 coverage

실제 Train 신호·목표·체결 원장에 대해 공개 가능한 파생 집계만 만든다.

- 소계정별 신호 결정 수, 목표 수, 매수/매도 수, 고유 종목·날짜 수
- 입력종류별 필요한 레코드 수와 저장 레코드 수
- `as_of`, `available_at`, `fetched_at`, `version/revision`, `provenance/hash` 필드 존재 수와 비율
- 가격 basis가 증명된 결정/체결 수
- 시점별 Universe(t)·거래정지·기업행동 상태가 증명된 결정/체결 수
- 모든 필수 입력이 증명된 결정/체결 수와 하나라도 UNKNOWN인 수
- UNKNOWN을 원인별로 분해하고 중복 집계 규칙을 명시

원시 가격·수량·종목명·원문은 공개하지 않는다. 종목은 필요하면 일회성 salt 해시가 아니라 단순 집계만 공개한다.

### 3. 판정

각 결정/체결을 다음 중 하나로만 분류한다.

- `PROVEN_PIT`: 모든 필수 입력의 available_at/판/basis/Universe 상태가 증거로 확인
- `CONSERVATIVE_ASSUMPTION`: 공식 시각은 없지만 사전에 고정된 다음 거래일 사용 등으로 미래 참조가 불가능함을 코드·달력으로 증명
- `UNKNOWN_EVIDENCE`: 필요한 증거 필드나 원천이 없음
- `VIOLATION`: 실제 입력 시각이 결정 뒤임을 증명

부재를 VIOLATION으로 쓰지 않는다. UNKNOWN_EVIDENCE와 유효성 없음도 구분한다.

### 4. 최소 다음 자료 목록

UNKNOWN_EVIDENCE를 해소하는 최소 자료를 다음 형태로만 출력한다.

- 정확한 레코드 종류·필드·날짜 범위
- 기존 KIS/DART/KRX 경로로 가능한지
- 호출/수집 예상량
- 과거 최초판 복원이 가능한지
- 이용약관상 공개 가능 범위
- API 키가 필요하면 키 이름만, 값은 절대 읽거나 출력하지 않음

이번에는 API를 호출하거나 키 존재를 검사하지 않는다.

## 금지

- 백테스트·포트폴리오·성과 재실행
- threshold, sizing, 지연, 가격, 노출식, 규칙 변경
- 새 알파/EMA/수급 조합 탐색
- API 호출·새 수집·키/Secrets 조회·로그인
- OOS/Validation/9월/10월 개봉
- 운영 봇·collector·전략·배분·워크플로·인증 변경
- 모의/실계좌 주문 또는 주문 API
- 자동 병합·레버리지
- 원가격·원수량·종목명·키·토큰·계좌·원본계좌응답 공개

## 완료 조건

새 `research-exchange/claude-to-gpt/BASELINE-PIT-EXPOSURE-0001/` 브랜치/PR에 제출한다.

- `PREREG.md`
- `REPORT.md`
- `DEPENDENCY-MAP.json`
- `PIT-COVERAGE.json`
- 집계 코드와 `run.log`
- `manifest.json`, `receipt.json`

보고서에는 분모가 명확한 coverage 표, UNKNOWN 원인별 수, 기존 PR #21/#29와 새 실측의 구분, 실패/실행 횟수, 다음 최소 자료를 포함한다. status는 READY/BLOCKED만 허용한다. 성과는 인용만 하고 `PAPER_VALIDATION_READY`·실전 승인·알파 유효성으로 표현하지 않는다.
