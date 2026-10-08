# TASK — BASELINE-ADJUSTMENT-CONSISTENCY-0001

## 식별자

- task_id: `BASELINE-ADJUSTMENT-CONSISTENCY-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 20
- status: READY
- source_pr: 82
- source_head_sha: `c18f10d465816c0c394c44290c945d481dc7b20f`
- stage: BASELINE
- Train 고정: 2025-09-18 ~ 2026-03-31
- 참조 후보: PR #78의 비용후 +19.90%는 인용값이며 이번 TASK의 성과 판정값이 아님

## 목적

PR #82가 로컬에서 확인한 off-tick 저장가격 74/747이 모의 연구의 어떤 계산에 실제로 사용됐는지 감사한다.

새 성과를 만들거나 고친 백테스트를 돌리지 말고, 기존 스냅샷·원장·신호·거래목록에서 다음만 계수한다.

1. 신호 입력
2. 모의 진입 체결가격
3. 모의 청산 체결가격
4. 거래비용·세금 산정 notional
5. 보유 중 일별 MTM 평가
6. 기업행동 전후 수량·현금 보존

공식 원주가가 없으므로 영향 금액·수익률을 추정하지 않는다. 내부 증거로 증명되는 범위와 UNKNOWN을 분리한다.

## 사전등록

계산 전에 별도 첫 커밋으로 아래를 고정한다.

1. 입력 파일과 sha256
2. 747개 (종목, 날짜) 분모의 재구성 규칙과 중복 제거 규칙
3. off-tick 판정 함수와 2023-01-25 이후 호가표
4. 역할별 매핑 규칙: signal / entry / exit / fee-tax-notional / open-position-MTM / corporate-action-window
5. 거래·보유·날짜별 독립 분모
6. 내부 회계 판정 규칙
7. 비식별 출력 스키마와 READY/BLOCKED 조건

사전등록 뒤 역할 또는 판정 규칙을 바꾸지 않는다. 버그 수정이 필요하면 첫 결과를 보존하고 수정 사유·전후 해시·재실행 횟수를 모두 기록한다.

## 허용 범위

### A. 고정 입력

PR #82 manifest가 해시로 고정한 다음 로컬 사본만 사용한다.

- PR #68 `control_trades`
- PR #74 `signals_old`
- PR #76 일별 원장
- 옛 `nrl-cache.pkl`
- PR #80/82의 targets와 거래·가격 역할을 재구성하는 기존 스냅샷
- PR #82의 `tick_check.py`, `tick-check.json`, REPORT, manifest

필수 입력이 현재 세션에 없으면 네트워크·workflow·다른 브랜치 계산으로 대체하지 말고 BLOCKED로 정확히 보고한다.

### B. 역할별 노출

off-tick 74개 레코드에 대해 비식별 해시로 다음을 계수한다.

- 고유 가격 레코드, 고유 종목, 고유 거래, 고유 보유일
- 신호에만 사용 / 체결에 사용 / MTM에만 사용 / 둘 이상 중복
- 진입·청산 각각의 off-tick 체결 건수와 해당 거래 수
- off-tick 가격을 기준으로 수수료·세금 notional을 계산한 건수
- 보유 중 off-tick MTM이 들어간 포지션-일 수
- 기업행동 8종목 및 Train 안의 저장 공시일 주변 ±5 거래일과 겹친 건수

분모에는 항상 UNKNOWN·자료없음을 함께 적고, 74건을 독립 거래 74개처럼 표현하지 않는다.

### C. 내부 체결 유효성

공식 원주가 없이도 다음은 판정할 수 있다.

- off-tick 값으로 체결된 진입·청산은 `IMPOSSIBLE_RAW_FILL`
- on-tick 값은 `UNKNOWN_RAW_OR_ADJUSTED`
- 가격이 없거나 매핑 불가하면 `UNKNOWN_MISSING_MAPPING`

슬리피지나 지정가로 off-tick 체결을 정당화하지 않는다. KRX 가격단위 밖의 실제 체결은 불가능하다는 한정된 뜻으로만 쓴다.

### D. 수량·현금·기업행동 일관성

기업행동 관련 종목의 실제 보유구간만 대상으로 한다.

- 거래 원장에 명시된 매수·매도 외 수량 변화, 현금 유입·유출, 수수료·세금 변화를 날짜순으로 재구성한다.
- 저장 공시일은 효력일이 아니므로 ±5 거래일 창은 탐색용 표시일 뿐 원인 확정에 쓰지 않는다.
- 수량 변화가 없는데 가격계열이 기계적으로 재배율된 흔적, 또는 거래 없이 수량·현금이 바뀐 흔적을 각각 계수한다.
- 원장 식별식 `기말현금 = 기초현금 - 매수대금 + 매도대금 - 비용 + 명시적 현금조정`과 `기말수량 = 기초수량 + 매수수량 - 매도수량 + 명시적 수량조정`을 행 단위로 검사한다.
- 명시적 기업행동 조정 레코드가 없으면 그 사실을 보고하되, 공식 효력일·비율 없이 특정 사건의 오류라고 단정하지 않는다.
- 수정주가를 사용했더라도 수익률이 자동으로 틀렸다고 단정하지 않는다. 반대로 수익률 연속성이 맞아 보여도 실제 체결 가능 수량·notional·비용·용량이 검증됐다고 올리지 않는다.

판정은 다음으로 제한한다.

- `INTERNAL_CONSISTENCY_PASS`
- `INTERNAL_INCONSISTENCY_PROVED`
- `IMPOSSIBLE_RAW_FILL`
- `UNKNOWN_NEEDS_OFFICIAL_RAW_AND_CA_EFFECTIVE_DATE`
- `UNKNOWN_MISSING_INPUT`

## 독립 검산

- 역할별 합계가 74와 맞는지, 중복 역할은 별도 교차표로 보인다.
- 고유 거래·포지션·보유일 분모를 각각 분리한다.
- 체결·비용·수량·현금 집계를 두 개의 독립 코드 경로 또는 직접 집계와 원장 집계로 교차검산한다.
- 최초 코드 커밋과 최종 코드 blob sha256을 비교한다.
- 모든 실행 명령, 실행 횟수, 실패 횟수, 입력 sha256을 manifest에 기록한다.

## 금지

- KIS·DART·KRX 등 외부 API/네트워크 호출
- GitHub Secrets 열람, GitHub Actions 실행·수정, workflow/auth 변경
- 백테스트·성과·NAV·포트폴리오 재실행 또는 수정 수익률 산출
- threshold, 규칙, EMA, 수급 조합, sizing, sleeve, 배분 변경
- 새 알파, OOS, Validation, Shadow 실행 또는 기간 재명명
- 모의·실계좌 주문·잔고·주문가능금액 API
- 운영 봇 재시작·코드 변경·자동병합
- 원가격·종목명·비공개 원장·원시 계좌/API 응답 공개
- 결손을 추정값으로 채우기, 같은 외부 자격 실패 반복

## 출력

경로: `research-exchange/claude-to-gpt/BASELINE-ADJUSTMENT-CONSISTENCY-0001/`

필수 파일:

- `PREREG.md`
- `REPORT.md`
- `manifest.json`
- `receipt.json`
- `evidence/off-tick-role-coverage.json`
- `evidence/fill-validity.json`
- `evidence/position-accounting.json`
- `evidence/corporate-action-crossings.json`
- `evidence/run.log`
- 사용 코드 스냅샷과 sha256

공개 산출물은 salted hash·개수·비율·정규화 값만 사용한다. 주장·코드·실측을 분리하고, 증거가 없으면 검증하지 못함으로 남긴다.

## 완료 조건

### READY

- 사전등록 뒤 고정 입력만 사용했다.
- 74개 레코드의 역할별 노출과 고유 거래·포지션·보유일 분모를 재현했다.
- off-tick 모의 체결, 비용 notional, MTM, 수량·현금 일관성을 사전등록 판정으로 분류했다.
- 공식 원주가·효력일이 필요한 부분은 UNKNOWN으로 남겼다.
- +19.90%를 재계산·검증 완료 또는 PAPER_VALIDATION_READY로 표현하지 않았다.

### BLOCKED

- 고정 입력이 없거나 해시가 다름
- 역할 매핑이나 수량·현금 원장을 재구성할 필수 필드가 없음
- 74개 분모를 재현하지 못함

BLOCKED면 결손 파일·필드·해시 불일치와 확인 가능한 분모만 적고 범위를 넓히지 않는다.

## 상태

결과 status는 READY 또는 BLOCKED만 허용한다. 후속 연구는 이 결과 PR 브랜치가 아닌 별도 브랜치/PR에서만 한다.
