# TASK — REPLAY-CA-QUANTITY-MUTATION-GATE-0001

- task_id: REPLAY-CA-QUANTITY-MUTATION-GATE-0001
- chain_id: PAPER-READINESS
- round: 35
- status: READY
- source_pr: 112
- source_head_sha: 9e88dba81bc3e702dad2478b4cf3e86e99e691c5
- stage: REPLAY

## 목적

PR #112의 합성 장부 복사본에서, 기업행위 `kind` 문자열 열거 대신 **수량변경 의미**를 기준으로 재적용 우회를 fail-closed 처리한다.

## 고정 범위

1. 유효한 reciprocal multiplier이고 `m_qty != 1`인 사건을 quantity mutation으로 정의한다.
2. 한 종목에 quantity mutation이 이미 적용되어 있으면, 이후 다른 키의 quantity mutation은 kind 이름과 무관하게 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`로 분류하고 배치 전체를 원자적으로 중단한다.
3. exact key+same payload는 `DUPLICATE_IGNORED`, exact key+changed payload는 기존 conflict 계약을 그대로 유지한다.
4. PR #112의 상태/registry/provenance 원자성, 순서·reload·byte·cut 결정성, Q1~Q4 회귀를 보존한다.
5. 합성 자료만 사용한다. 실제 사건·외부 API·성과 계산은 0건이다.

## 고정 fixture

- M1: A split 적용 뒤, 같은 A의 `bonus_issue` ×2와 무관한 B 사건을 같은 batch에 둔다.
- M2: A split 적용 뒤, 같은 A의 사전 열거되지 않은 `unknown_qty_event` ×2와 무관한 B 사건을 같은 batch에 둔다.
- M3: 나중 날짜의 합법적으로 보이는 두 번째 A quantity mutation을 둔다.
- M4: quantity mutation 이력이 없는 새 종목 C의 첫 사건과 무관한 B 사건을 둔다.
- 음성대조군: PR #112 고정본에서 I1이 COMMITTED되고 A=185→370임을 exact input으로 재현한다.
- 회귀: PR #112 K1~K3와 Q1~Q4를 구조화 증거와 비교한다.

## 완료 조건

### READY

다음을 모두 만족할 때만 READY다.

- M1/M2/M3는 BATCH_ABORTED이고 A/B 수량, applied registry, provenance가 batch 전과 동일하며 변경 필드가 0이다.
- M1/M2의 A 사건은 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`, 무관 B 사건은 선검증상 OK지만 batch commit은 되지 않는다.
- M3는 보수적 오탐으로 명시되고 `NEEDS_DATA`다.
- M4는 COMMITTED되어 새 종목의 첫 quantity mutation이 허용된다.
- 모든 fixture가 입력 순서, 직렬화/reload, 반복 실행, prefix cut에서 동일하다.
- PR #112 K1~K3/Q1~Q4 구조화 결과와 비교한 회귀 차이가 0이다.
- 음성대조군이 PR #112 I1 결과를 재현한다.
- actual_events=0, external_calls=0, performance_verified=false, paper_validation_ready=false를 명시한다.

### BLOCKED

필수 고정본/해시 불일치, fixture 기대 불충족, 원자성·결정성·회귀 실패, 또는 실행 전 사전등록 변경이 있으면 BLOCKED다. 기존 자료로 해결 가능한 원인을 구체적으로 적고 연구 범위를 넓히지 않는다.

## 금지

- kind 문자열을 하나씩 추가하는 allow/block 목록 패치
- 실제/모의 주문 API 호출, 새 수집, 네트워크 접근
- 현재 모의 봇·운영 규칙·배분·워크플로·인증 변경
- threshold/알파 탐색, 성과 최적화, Validation/OOS 재명명
- 실전 채택·손실 한도 보장·PAPER_VALIDATION_READY 주장
- 비밀, 계좌번호, 개인 잔고, 원본 계좌 응답 공개
- 자동병합 및 결과 PR 제출 후 receipt 보정 외 변경

## 제출 계약

새로운 `research-exchange/claude-to-gpt/REPLAY-CA-QUANTITY-MUTATION-GATE-0001` 브랜치/PR에 PREREG, REPORT, manifest, receipt, code, 구조화 evidence를 제출한다. 결과 PR은 제출 시점에 완결하고 이후 연구는 별도 브랜치에서만 한다.
