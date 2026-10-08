# PR #122 검토 — REPLAY-BLOCKED-DAY-METRIC-GATE-0001

- task_id: REPLAY-EMPTY-LEDGER-METRIC-GATE-0001
- chain_id: PAPER-READINESS
- round: 40
- status: READY
- source_pr: 122
- source_head_sha: 2ec2e13b55578290c3bcb822a3b78b30b77c9047
- reviewed_at_kst: 2026-10-09T03:44:37+09:00

## 판정

**합성 차단일 성과 게이트 범위에 한해 READY**입니다.

- 기존 snapshot-only 함수가 마지막 차단일을 놓치는 음성대조를 재현했습니다.
- 새 `perf_gate(ledger)`는 `blocked_from`을 먼저 읽고 차단 상태에서 metric 함수를 호출하지 않았습니다.
- invalid snapshot 방어, 기존 차단/정상 fixture 회귀, reload·바이트·호출경계가 고정 기대와 일치했습니다.
- 공식 실행 1회, actual_events=0, external_calls=0입니다.

실제 가격기준·기업행위·NAV·성과는 검증하지 않았습니다. `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false`를 유지합니다.

## 주장·코드·실측

- 주장: 차단 표식 또는 invalid snapshot이 있으면 모든 성과 metric을 미산출로 막습니다.
- 코드: `perf_gate(ledger)`의 차단 return이 일별수익률·MDD·월 TWR 호출보다 앞입니다.
- 합성 실측: M1~M8과 PR #114 회귀가 통과했습니다.
- 실제 실측: 실제 사건·시세·포지션·NAV·비용·체결은 0입니다.

## 확인된 잔여 결함

`blocked_from is None`이고 `ledger.snaps == []`인 원장은 새 함수에서도 `_mdd`의 첫 snapshot 접근에서 `IndexError`가 발생합니다.

- 차단 표식이 없는 빈 원장은 정상 성과를 계산할 근거가 없습니다.
- 예외는 READY/BLOCKED 상태가 아니므로 호출자가 예외를 삼키면 다시 정상처럼 오해될 수 있습니다.
- 이는 실제 수익성이 없다는 결론이 아니라, 측정 가능성 판정이 fail-closed가 아니라는 코드 결함입니다.

다음 단계는 실제 가격기준을 고르지 않고 이 빈 원장 상태 하나만 `NO_SNAPSHOTS`로 차단합니다.
