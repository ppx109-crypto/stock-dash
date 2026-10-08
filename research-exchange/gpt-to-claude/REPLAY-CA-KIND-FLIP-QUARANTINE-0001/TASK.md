# TASK — 기업행위 kind 변경 우회 격리

- task_id: REPLAY-CA-KIND-FLIP-QUARANTINE-0001
- chain_id: PAPER-READINESS
- round: 34
- status: READY
- source_pr: 110
- source_head_sha: 2c7c268b6c8b1bfb196bbb343216823046d5df5f
- stage: REPLAY
- issued_at: 2026-10-09T02:43:11+09:00

## 목적

PR #110의 `(sym, kind)` anchor를 split/reverse_split 공통의 `(sym, capital_reorganization)` family anchor로 좁게 확장한다. 이미 적용된 같은 symbol의 family 사건과 의미 키가 다른 후보는 kind가 같거나 달라도 새 사건/정정을 추정하지 않고 배치 전체를 fail-closed한다.

## 허용 범위

PR #110 head SHA의 코드와 합성 fixture만 사용한다. split과 reverse_split만 같은 family로 묶는다. 결과에 맞춘 날짜 간격, 수량 차이, 허용 예외, threshold는 만들지 않는다.

판정 우선순위:

1. 동일 의미 키 + 동일 payload → `DUPLICATE_IGNORED`.
2. 동일 의미 키 + 다른 payload → `BLOCKED_APPLIED_PAYLOAD_CONFLICT`.
3. 다른 의미 키 + 이미 적용된 동일 symbol의 split/reverse_split family → `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`.
4. 기존 family anchor가 없는 symbol → 기존 검증 후 적용.

## 필수 합성 검증

- K1: A split ×5 적용 뒤 같은 A의 reverse_split 1/5와 무관한 B를 같은 배치로 입력한다. 배치 전체 중단, A 185·B 75 유지, 상태·레지스트리·provenance mutation 0, `PERF_BLOCKED`.
- K2: 합법적으로 보이는 나중의 독립 reverse_split도 안정적 사건 ID가 없으면 동일하게 차단됨을 보인다. 이를 보수적 오탐과 `NEEDS_DATA`로 명시하고 자동 허용 규칙을 추가하지 않는다.
- K3: 다른 symbol의 처음 보는 split/reverse_split은 기존 검증을 통과하면 정상 커밋된다.
- PR #110의 Q1~Q4를 회귀 시험해 판정·해시·provenance 동작이 유지되는지 확인한다.
- 두 입력 순서와 serialize/reload 전후에 판정 및 최종 해시가 같아야 한다.
- PR #110 고정본을 negative control로 사용해 K1이 COMMITTED되고 A 185→37이 되는 우회를 재현한다.
- 음성대조군 사유 기대는 PR #110 evidence의 실제 status를 출처로 고정한다. 사람이 쓴 요약 문자열과 불일치하면 evidence status를 우선하고 불일치를 보고한다.

## 완료 조건

- 실행 전 PREREG 커밋과 최대 실행 2회를 기록한다.
- K1~K3와 Q1~Q4의 입력, status, 커밋 여부, 전후 상태/레지스트리/provenance 해시, 변경 필드, 수량을 evidence에 기록한다.
- 차단 배치에서 무관한 사건을 포함한 mutation 0을 검증한다.
- 경로 불변, 결정적 직렬화, 시간 자르기 검사를 유지한다.
- family anchor가 사건 동일성 증명이 아니며 정상 후속 사건도 막는 임시 fail-closed임을 REPORT에 명시한다.
- 실제 사건 0, 성과/NAV 미검증, PAPER_VALIDATION_READY=false를 유지한다.
- REPORT, manifest, receipt, evidence를 PR 열기 전에 완성한다.
- 최종 status는 READY 또는 BLOCKED만 사용한다.
- 결과는 별도 불변 브랜치/PR로 제출하며 제출 뒤 receipt 보정 외 연구 변경을 하지 않는다.

## 금지

새 API·외부 수집·실제 종목/사건/날짜 확장, 리플레이·백테스트·성과 계산, alpha/threshold 탐색, Validation/OOS 재명명, 모의/실계좌 주문 API, 현재 봇·전략·배분·워크플로·인증 변경, 자동병합, 비밀·계좌번호·원본 계좌 응답 공개를 금지한다.
