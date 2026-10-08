# REPLAY-BLOCKED-DAY-METRIC-GATE-0001 사전등록

- task_id: REPLAY-BLOCKED-DAY-METRIC-GATE-0001
- chain_id: PAPER-READINESS
- round: 39
- source_pr: 120
- source_head_sha: 8ed1d7d24a7fd564c200f2978bd51659f1af4316
- phase: REPLAY
- official_run_cap: 1

## 고정 가설

- H1: PR #120의 snapshot-only `perf(snaps)`는 마지막 날 quote-basis 차단을 놓칠 수 있습니다.
- H2: ledger의 `blocked_from`을 성과 계산 전 필수로 읽으면 snapshot 부재와 무관하게 차단일부터 모든 metric을 fail-closed로 막습니다.
- H3: 차단 표식이 없고 snapshot이 모두 valid인 RAW 합성 경로의 기존 결과는 변하지 않습니다.

## 고정 입력과 판정

TASK.md의 M1~M8 입력·순서·기대값만 사용합니다.

- 통과: M1 음성대조 재현, M2~M5 차단, M6 무회귀, M7~M8 결정성·호출경계 충족, 공식 실행 1회
- 실패: 기대값 불일치, 차단 검사 전 metric 계산, 실행 초과, 실제/외부 자료 접근 중 하나라도 발생
- 실패 뒤 fixture·수치·규칙을 바꾸지 않고 BLOCKED로 제출합니다.
- 사전등록 뒤 코드·fixture 변경이 있으면 공식 실행 전에만 하고 이유와 diff를 REPORT에 공개합니다.

## 측정

- perf verdict/from/reason
- blocked_from 및 snapshot 날짜·valid
- metric 계산 호출 수와 산출 여부
- serialize/reload 전후 상태·출력·바이트 sha256
- 기존 RAW 정상 결과 diff count
- 공식 실행 수·외부 호출 수

실제 일/월 TWR, 실제 MDD, 비용후수익률, Sharpe, capacity는 계산하지 않습니다.

## 경계

이 합성 metric gate는 실제 시세 가격기준, available_at, 정정 버전, Universe(t), 비용·체결, 실제 일별 MTM의 완전성을 검증하지 않습니다. READY여도 실제 성과, NAV, PAPER_VALIDATION_READY의 근거가 아닙니다.
