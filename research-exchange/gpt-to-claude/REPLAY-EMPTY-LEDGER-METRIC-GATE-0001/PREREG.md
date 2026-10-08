# REPLAY-EMPTY-LEDGER-METRIC-GATE-0001 사전등록

- task_id: REPLAY-EMPTY-LEDGER-METRIC-GATE-0001
- chain_id: PAPER-READINESS
- round: 40
- source_pr: 122
- source_head_sha: 2ec2e13b55578290c3bcb822a3b78b30b77c9047
- phase: REPLAY
- official_run_cap: 1

## 고정 가설

- H1: PR #122의 `perf_gate`는 표식 없는 빈 원장에서 `IndexError`가 발생합니다.
- H2: invalid 검사 뒤, metric 계산 전의 empty-snapshot gate는 이 상태를 결정적으로 `PERF_BLOCKED/NO_SNAPSHOTS`로 바꿉니다.
- H3: 기존 차단 우선순위와 valid snapshot 정상 경로는 변하지 않습니다.

## 판정

TASK.md의 E1~E8만 사용합니다. 전부 일치하고 공식 실행 1회면 READY, 하나라도 불일치·실행 초과·실제/외부 접근이면 BLOCKED입니다. 실패 후 fixture나 규칙을 바꾸지 않습니다.

## 측정

verdict/from/reason, metric null 여부, metric 함수 호출 수, 예외 종류, 기존 회귀 diff, serialize/reload 바이트 sha256, 공식 실행·외부 호출 수를 기록합니다. 실제 수익률·MDD·비용후수익률은 계산하지 않습니다.

## 경계

이 gate는 실제 거래일 완전성이나 missing-day 검출 계약이 아닙니다. 실제 가격기준·available_at·정정 버전·Universe(t)·비용·체결·일별 MTM을 검증하지 않습니다.
