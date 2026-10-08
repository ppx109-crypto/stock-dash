# REPLAY-CA-PRICE-BASIS-GATE-0001 사전등록

- task_id: REPLAY-CA-PRICE-BASIS-GATE-0001
- chain_id: PAPER-READINESS
- round: 37
- source_pr: 116
- source_head_sha: dc4335554b45ba8f257596acab44a0f6d2e985ff
- phase: REPLAY
- official_run_cap: 1

## 가설

- H1: PR #114 게이트는 가격기준 구분 없이 ADJUSTED 입력에 연결하면 P2 음성대조에서 이중 조정 왜곡을 만든다.
- H2: mutation 전 fail-closed 검사를 두면 ADJUSTED/UNKNOWN 입력은 상태 변화 0으로 차단된다.
- H3: RAW_UNADJUSTED 입력에서는 PR #114의 정상 수량·가격 불변식과 중복 거부 의미가 유지된다.

## 고정 입력·판정

TASK.md의 P1~P5 수치·순서·기대값을 그대로 사용합니다. 새 사건 종류, 새 배수, 임의 표본, 실제 자료를 추가하지 않습니다.

- 통과: 모든 고정 케이스 기대값 일치, 차단 전후 상태 해시 동일, 공식 실행 1회
- 실패: 기대값 불일치, mutation 선행, 실행 초과, 실제/외부 자료 접근 중 하나라도 발생
- 실패 후 수치·규칙을 바꿔 재실행하지 않습니다. BLOCKED로 제출합니다.

## 측정

- 배치별 status/reason
- mutation_count
- before/after state sha256
- q, p, cash, q×p
- applied-key 수
- 공식 실행 수와 외부 호출 수

성과수익률, Sharpe, MDD, 일/월 TWR, capacity는 측정하지 않습니다.

## 경계

이 실험은 가격기준 라벨이 신뢰할 원천에서 생성됐음을 검증하지 않습니다. 실제 가격의 adjusted/raw 의미, available_at, 정정 버전, 사건 날짜와 배수도 검증하지 않습니다. 따라서 READY여도 실제 Train 연결·성과·PAPER_VALIDATION_READY 근거가 아닙니다.
