# PR #114 검토 — REPLAY-CA-QUANTITY-MUTATION-GATE-0001

- task_id: REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001
- chain_id: PAPER-READINESS
- round: 36
- status: READY
- source_pr: 114
- source_head_sha: 6261e5a100607b36fa033b8a2ce710482cf8ccfa
- reviewed_at: 2026-10-09T02:57:50+09:00

## 판정

PR #114는 **합성 quantity-mutation fail-closed 계약에 한해 READY**다. 실제 기업행위 입력, 실제 사건 동일성, NAV, 성과 또는 PAPER_VALIDATION_READY 판정은 아니다.

## 주장·코드·실측

### 주장

보고서는 kind 문자열과 무관하게, 이미 quantity mutation이 적용된 종목의 후속 다른-key quantity mutation을 배치 전체 차단한다고 주장한다. 합법적인 두 번째 사건도 영구 차단되는 오탐과 입력 multiplier가 실제 효과와 맞다는 미검증 가정을 명시한다.

### 코드

정확한 source head에서 `GateLedger`를 읽었다.

- quantity mutation은 유효 양의 유리수, `m_qty*m_price=1`, `m_qty!=1`이다.
- exact key duplicate/conflict를 먼저 판정한다.
- committed registry에 quantity mutation이 있는 sym의 후속 다른-key quantity mutation을 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`로 처리한다.
- 한 건이라도 막히면 batch를 commit하지 않는다.
- kind 목록은 사용하지 않는다.

### 구조화 실측

- M1 bonus_issue, M2 미지 kind, M3 후속 사건: BATCH_ABORTED, A=185/B=75, state/provenance hash 불변, 변경 필드 0.
- M4 새 종목 첫 사건: COMMITTED, A=185/B=15/C=80.
- PR #112 K1~K3/Q1~Q4 대비 비교 차이 0.
- 순서/reload/repeat/byte/cut 시험 통과.
- PR #112 음성대조군에서 I1은 COMMITTED, A=185→370.
- actual_events=0, external_calls=0, performance_verified=false, paper_validation_ready=false.

## 미해결 핵심

현재 게이트는 `m_qty`, `m_price`, `apply_date`, `kind`, `src`가 이미 신뢰할 수 있게 생성됐다고 가정한다. 그러나 이번 제출은 다음을 증명하지 않는다.

1. 실제 원문에서 multiplier와 적용일을 만드는 producer/transform 경로
2. source event ID, 정정 계보, available_at의 보존
3. 가격만 조정되는 사건, 현금배당·권리·합병 등 비-reciprocal 사건의 표현
4. 실제 Train 자료 또는 운영 복사본이 이 adapter를 호출한다는 연결
5. 실제 사건 8건 및 기존 148건 재생 대상과의 결속

따라서 추가 합성 차단 규칙을 만들지 않는다. 다음 한 단계는 저장소의 기존 파일만 읽어 입력 생성·소비·provenance 경로를 정적 감사하고, 경로가 없으면 `NO_PRODUCER/NEEDS_DATA`로 확정하는 것이다.
