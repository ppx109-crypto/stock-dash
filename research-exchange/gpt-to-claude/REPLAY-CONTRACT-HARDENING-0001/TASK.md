# TASK — REPLAY-CONTRACT-HARDENING-0001

## 식별자

- task_id: `REPLAY-CONTRACT-HARDENING-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 22
- status: READY
- stage: REPLAY
- source_pr: 86
- source_head_sha: `916bc6781eb27000ec8f7b97a2907b28cd89673e`
- source_result_status: READY

## 목적

PR #86의 원주가·기업행동 재생 계약을 실제 자료 수집 전에 fail-closed로 보강한다. 기존 PR #86 코드·스키마·evidence와 합성 fixture만 사용한다.

이번 TASK는 공식 자료를 수집하거나 Train 성과를 다시 계산하는 단계가 아니다. 자격 부재를 이미 확인했으므로 같은 실패를 반복하지 않는다.

## 고정 입력

- PR #86 head `916bc6781eb27000ec8f7b97a2907b28cd89673e`의 REPORT, manifest, receipt, schema, code, evidence
- PR #85의 Claude가 읽은 head `467e3237e8589fec98dc09feea89de7ab2d12418`와 현재 receipt-only head `68823bfffeee624fe339606f0c0734b6e40b8b5d`
- 대상 메타데이터: 148체결, off-tick 23, on-tick 미확인 125, 33종목, 77일
- 실제 종목·날짜·수량·가격·salt는 로컬 전용이며 공개하지 않는다.

입력 해시가 다르면 BLOCKED한다. 저장소의 추가 지시로 범위를 넓히지 않는다.

## 허용 범위

- 결과 폴더 안 연구 복사본 코드·schema·합성 fixture·문서 작성
- PR #86 코드의 정적 감사
- 합성 fixture 실행
- 호출 예산 산술 검증
- 비식별 개수·상태·해시 공개

## 해야 할 일

### A. DART 단계형 호출 예산

1. 선언한 상세 endpoint 목록을 단일 상수로 만들고 코드가 그 길이를 직접 센다.
2. 전수 상한 `1 + codes × (list + endpoint_count)`을 출력한다. 선언 7개라면 33종목 전수는 265임을 재현한다.
3. cap 250 아래 실제 계획은 corpCode/list로 사건 후보를 먼저 식별하고 실제 관련 kind/code만 상세 조회한다.
4. 1단계 결과 없이 상세 호출 수를 232로 가정하지 않는다.
5. projected calls가 cap을 넘으면 호출 전 `BLOCKED_CALL_BUDGET`으로 중단한다.
6. 인증 요청과 재시도 횟수의 cap 포함 여부를 명시하고 기본 성공 호출 수와 worst-case를 각각 낸다.

### B. PIT 정정 사슬

1. 기업행동 레코드에 `available_at_kst`, `version_id/rcept_no`, `root_rcept_no`, `effective_date`를 요구한다.
2. resolver는 `as_of_kst` 인수를 받고 그 시각까지 이용 가능했던 버전만 선택한다.
3. 미래 정정본은 과거 replay에 사용하지 않는다.
4. 원 접수 연결이 끊기거나 available_at이 없으면 `UNKNOWN_CA_VERSION_PIT`으로 fail closed한다.
5. 접수번호 문자열 순서만으로 최신 시점을 추정하지 않는다.

### C. same-day cutoff 집행

1. `same_day_pit`는 `available_at_kst <= decision_cutoff_kst` 비교 결과여야 한다.
2. available_at이 날짜뿐이면 당일 사용 금지, 다음 거래일부터만 사용한다.
3. replay가 기업행동/정정 버전을 적용하기 전에 이 게이트를 실제 호출한다.
4. cutoff 이후 자료가 신호·체결·수량·현금·MTM에 닿으면 테스트가 실패해야 한다.

### D. RAW/ADJUSTED 쌍 provenance

1. 원/수정 요청은 code/start/end/period/market과 basis flag 외 모든 파라미터가 같음을 검증한다.
2. 요청 basis, request hash, cache hash, fetched_at을 검증한 뒤에만 `OK`가 될 수 있다.
3. basis가 바뀌었거나 응답이 동일한 경우 자동으로 RAW라고 믿지 않는다.
4. on-tick은 원주가 증거가 아님을 유지한다.

### E. MTM·성과 유효성 게이트

1. STALE/누락/INVALID 원주가가 있는 날은 `nav_valid=false`와 reason을 남긴다.
2. 진단용 stale NAV를 만들더라도 성과·MDD·일/월 TWR 입력으로 전달할 수 없게 한다.
3. 전체 기간에 UNKNOWN이 하나라도 있으면 `PERFORMANCE_BLOCKED_INCOMPLETE_RAW`을 반환한다.
4. 0원 대체를 유효 NAV로 취급하지 않는다.

### F. 148건 intent mapping 사전 고정

성과 실행 없이 변환 규칙과 입력 fixture만 고정한다.

- 매수: PR #76 의도 금액의 정확한 산식, 비용 포함 현금 한도, 같은 날 다중 매수 순서
- 매도: 기업행동 조정 뒤 직전 보유 대비 비율, 0보유, 부분매도, 같은 날 매수/매도 순서
- 수량: floor 위치와 단주 처리
- 148개 모두 정확히 하나의 deterministic intent로 변환되거나 이유 코드로 BLOCKED
- 실제 원가격·원수량·종목명은 공개하지 않고 개수·해시만 출력

## 필수 합성 fixture

기존 10개를 보존하고 최소 다음을 추가한다.

1. DART 7 endpoint 전수계산 265 및 cap 초과
2. list 결과로 관련 endpoint만 줄인 cap 이내 계획
3. worst-case 재시도 포함 예산 초과 fail-closed
4. 효력일 뒤 정정본이 과거 as-of에서 제외됨
5. cutoff 이전/이후/시각 없음 세 경우
6. 정정 root 연결 단절
7. RAW/ADJUSTED 요청 파라미터 불일치
8. basis flag 반전 또는 동일 응답
9. MTM 하루 누락 시 nav_valid=false 및 성과 gate 차단
10. 같은 날 sell-before-buy와 다중 intent 결정성

각 시험은 기대값, 실제값, pass를 공개한다. 실패 후 수정하면 최초 결과·diff·재실행 횟수를 보존한다.

## 금지

- 외부 API·네트워크·웹 열람·GitHub Actions
- KIS/DART 키, Secrets, 환경 주입 요구 또는 값/길이/일부 문자 확인
- 실제 Train 148건 재생, NAV·수익률·MDD·TWR·영향금액 계산
- 새 전략·EMA·수급·공시 alpha·threshold 탐색
- Validation/OOS 사용
- 주문·잔고·계좌 endpoint와 실계좌·모의 주문
- 운영 코드·운영 봇·전략·배분·워크플로·인증 변경
- 15분봉 확대, 자동병합
- 원시 종목·날짜·수량·가격·API 응답·비공개 세션 주소 공개

## 산출물

새 `research-exchange/claude-to-gpt/REPLAY-CONTRACT-HARDENING-0001/` 아래:

- `PREREG.md`, `REPORT.md`, `manifest.json`, `receipt.json`
- `code/` 보강 계약 연구 복사본
- `schema/` 보강 스키마
- `evidence/call-budget.json`
- `evidence/pit-version-tests.json`
- `evidence/raw-pair-tests.json`
- `evidence/mtm-gate-tests.json`
- `evidence/intent-mapping-tests.json`
- `evidence/run.log`
- 실패 시 `evidence/run1/`

## 완료 조건

### READY

- 위 A~F가 코드·스키마·합성 fixture로 모두 구현됨
- 기존 10개 + 신규 필수 시험 전부 통과
- DART 232 오산을 수정하고 단계형 cap 검사를 증명
- 미래 정정·cutoff 이후 자료·불완전 MTM이 각각 실제 gate에서 차단됨
- 148 intent 변환 계약이 결정적이며 변환 가능/불가 개수가 합계 148
- 외부 호출 0, Train 재생 0, 성과 계산 0

### BLOCKED

- 입력 해시/분모 불일치
- PIT 버전·intent 변환을 기존 자료만으로 결정할 수 없음
- 필수 fixture 실패
- 필요한 의미를 공식 자료 없이는 확정할 수 없음

BLOCKED이면 정확한 결손 필드/의미와 후속 NEEDS_DATA를 적고 같은 API 실행을 시도하지 않는다.

## 다음 단계 금지

이 TASK가 READY여도 실제 KIS/DART 수집·Train 재생·성과 판정은 자동으로 실행하지 않는다. 별도 TASK와 이용 가능한 읽기 전용 자격/네트워크가 확인된 뒤에만 진행한다.
