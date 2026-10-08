# TASK — BASELINE-KIS-DART-AUDIT-0001

## 식별자

- task_id: `BASELINE-KIS-DART-AUDIT-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 19
- status: READY
- source_pr: 80
- source_head_sha: `e088c837a33e39b2790d2a61db317e1b96ee8d08`
- stage: BASELINE
- Train 고정: 2025-09-18 ~ 2026-03-31
- 참조 후보: PR #78의 시점 수정 후보(비용후 +19.90%는 인용값이며 이번 TASK의 성과 판정값이 아님)

## 목적

새 전략이나 수익률을 탐색하지 말고, 저장소에 이미 설정된 **KIS(한국투자)·OpenDART 읽기 전용 자격**으로 PR #80의 U2/U3 및 15분봉-일봉 종가 불일치를 실제 공식 응답과 대조한다.

과거 도착 판 U4는 복원 불가로 고정한다. Universe(t) U1은 KIS/DART만으로 증명되지 않으면 UNKNOWN을 유지한다.

## 사전등록

외부 호출 전에 별도 첫 커밋으로 아래를 고정한다.

1. 실제 사용할 공식 API/endpoint·TR ID·요청 필드·응답 필드
2. 대상 종목/날짜의 비식별 해시 목록
3. 호출 상한과 재시도 상한
4. 원주가/수정주가 판정 규칙
5. 기업행동과 가격 차이를 연결하는 규칙
6. 15분봉-일봉 4/82 불일치 원인 판정 규칙
7. 출력 스키마와 실패/BLOCKED 조건

## 허용 범위

### A. 자격·접근 확인

- 현재 실행환경에 이미 주입된 KIS·DART 자격만 사용한다.
- secret 값, 길이, 일부 문자열, 계좌번호를 읽거나 출력·커밋하지 않는다.
- 저장소/조직 secrets 목록을 열람하거나 새 secret·workflow·인증을 만들지 않는다.
- 환경변수 존재 여부와 read-only 인증 성공/실패만 비식별로 기록한다.
- KIS 주문·잔고·계좌 endpoint는 호출하지 않는다.

### B. 고정 대상

- PR #80이 열거한 실제 체결 종목 39개를 상한으로 한다.
- 우선순위:
  1. 기업행동 공시가 있다고 계수된 8종목
  2. 15분봉 마지막 종가와 일봉 종가가 달랐던 4/82 사례
  3. 나머지 실제 체결 종목
- 날짜는 Train과 필요한 기업행동 효력 확인 기간만 사용한다.
- 종목명·원시 응답은 공개 산출물에 넣지 않고 salted hash 또는 PR #80과 같은 비식별 코드 집계만 쓴다.

### C. KIS 읽기 전용 대조

- 공식 문서에서 확인한 국내주식 **과거 일봉/분봉 조회**만 사용한다.
- 저장 가격 747레코드 중 실제 공식 조회로 덮을 수 있는 분모를 명시한다.
- API가 원주가/수정주가 선택을 지원하면 둘을 모두 같은 날짜에 대조한다. 지원하지 않으면 지원한다고 추정하지 말고 UNKNOWN으로 남긴다.
- 저장값=공식 원주가, 저장값=공식 수정주가, 둘 다 아님, 조회불가를 각각 계수한다.
- 15분봉-일봉 불일치 4건은 마감 동시호가, 봉 누락, basis 차이, timezone/장구분, 기타 UNKNOWN의 사전등록된 분류만 허용한다.
- 호출 상한: 인증 호출 포함 500회, 429/5xx 재시도는 요청별 최대 2회. 캐시를 사용하고 같은 요청을 반복하지 않는다.

### D. OpenDART 읽기 전용 대조

- 실제 체결 종목 중 PR #80이 표시한 기업행동 관련 8종목부터 확인한다.
- 접수번호, 접수일, 보고서명, 정정 여부/원 접수 연결 가능 필드, 효력일을 가능한 범위에서 대조한다.
- 접수 시각이 없으면 날짜만 있다고 명시하고 같은 날 사용을 PIT로 승격하지 않는다.
- 가격 basis와 기업행동을 연결할 때 효력일 전후 공식 가격의 기계적 비율과 공시 조건이 일치하는지만 계수한다.
- DART 호출 상한: 전체 250회. 동일 요청 캐시, 요청별 재시도 최대 2회.

## 금지

- 백테스트·성과·NAV 재실행
- threshold, 규칙, sizing, sleeve, 배분 변경
- 새 알파/OOS/Validation 실행 또는 기간 재명명
- KIS 모의·실계좌 주문, 잔고·계좌·주문 가능 금액 조회
- 운영 봇·워크플로·GitHub Actions·인증 설정 변경
- secret 탐색·출력·커밋
- 원시 API 응답, 종목명, 계좌자료, 비공개 시장데이터 공개
- KRX 또는 유료 데이터 권한을 자동으로 추가
- 호출 상한 초과나 같은 실패의 반복

## 독립 검증 및 출력

경로: `research-exchange/claude-to-gpt/BASELINE-KIS-DART-AUDIT-0001/`

필수 파일:

- `PREREG.md`
- `REPORT.md`
- `manifest.json`
- `receipt.json`
- `evidence/api-coverage.json`
- `evidence/price-basis-summary.json`
- `evidence/corporate-action-summary.json`
- `evidence/m15-daily-mismatch-summary.json`
- `evidence/run.log`
- 사용 코드 스냅샷과 sha256

모든 표에 분모, 조회성공, 조회불가, 일치, 불일치, UNKNOWN을 함께 적는다. 주장·코드·실측을 분리한다. 원시 값 대신 비식별 집계와 해시만 공개한다.

## 완료 조건

### READY

- 사전등록 후 호출했고 상한을 지켰다.
- KIS/DART 공식 endpoint와 실제 response 필드를 근거로 U2/U3 및 4건 불일치의 확인 가능한 범위를 집계했다.
- U1/U4와 해소되지 않은 항목은 UNKNOWN으로 남겼다.
- `+19.90%`를 검증 완료나 PAPER_VALIDATION_READY로 표현하지 않았다.

### BLOCKED

다음 중 하나면 더 넓히지 말고 BLOCKED:

- 기존 실행환경에서 KIS/DART read-only 자격을 사용할 수 없음
- 해당 API가 필요한 역사 범위·원/수정주가·기업행동 정보를 제공하지 않음
- 라이선스/권한/호출 상한 때문에 고정 대상의 의미 있는 분모를 확인할 수 없음

BLOCKED 보고에는 실패 endpoint, HTTP/응답 코드, 호출 수, 정확히 필요한 자격/자료를 비밀 없이 적는다.

## 상태

결과 status는 READY 또는 BLOCKED만 허용한다. PAPER_VALIDATION_READY는 이번 범위에서 금지한다.
