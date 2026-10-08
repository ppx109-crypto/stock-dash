# PR #112 검토 — REPLAY-CA-KIND-FLIP-QUARANTINE-0001

- task_id: REPLAY-CA-QUANTITY-MUTATION-GATE-0001
- chain_id: PAPER-READINESS
- round: 35
- status: READY
- source_pr: 112
- source_head_sha: 9e88dba81bc3e702dad2478b4cf3e86e99e691c5
- reviewed_at: 2026-10-09T02:50:32+09:00

## 판정

PR #112는 **합성 split/reverse_split family 격리 계약에 한해 READY**다. 이는 실제 기업행위 동일성, 과거 성과, NAV 또는 PAPER_VALIDATION_READY 판정이 아니다.

## 주장·코드·실측 구분

### 주장

보고서는 split과 reverse_split을 같은 family로 묶으면 기존 split 뒤 kind를 reverse_split으로 바꿔 재적용하는 우회를 차단한다고 주장한다. 동시에 family 밖 kind는 우회할 수 있고 실제 사건 0건이라고 명시한다.

### 코드

정확한 source head의 코드를 읽었다. `FAMILY`는 `split`과 `reverse_split`만 `capital_reorganization`으로 묶는다. 이미 적용된 `(sym, family)`와 새 키의 anchor가 같으면 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`로 배치 전체를 중단한다. exact key+same payload는 duplicate, exact key+changed payload는 conflict로 유지된다.

### 구조화 실측

- K1: A split 뒤 A reverse_split + 무관 B는 BATCH_ABORTED, A=185/B=75, batch 전후 state/provenance hash 동일, 변경 필드 0, PERF_BLOCKED.
- K2: 독립적으로 보이는 후속 reverse_split도 차단되어 영구 오탐이 확인됨(NEEDS_DATA).
- K3: 첫 수량변경인 C split과 B reverse_split은 COMMITTED, A=185/B=15/C=80.
- Q1~Q4: PR #110 증거 대비 비교 필드 차이 0, 순서/reload/byte/cut 회귀 통과.
- 음성대조군: PR #110 로직에서는 K1이 COMMITTED되어 A=185→37.
- 잔여 반례 I1: A split 뒤 `bonus_issue` ×2는 COMMITTED되어 A=185→370.

## 핵심 결론

두 kind 이름만 묶는 방식은 닫힌 방어가 아니다. 같은 경제적 수량변경을 다른 kind 문자열로 옮기면 다시 적용된다. 다음 한 단계는 kind 목록을 추가하는 패치가 아니라, **이미 수량변경이 적용된 종목의 후속 수량변경을 kind와 무관하게 격리하는 의미 기반 fail-closed 계약**을 합성 자료에서 검증하는 것이다.

이 격리는 실제 event identity를 증명하지 못하며 합법적인 두 번째 기업행위도 차단한다. 그러므로 결과는 계속 NEEDS_DATA이고, 실제 사건 식별자/정정 계보/available_at이 없으면 REPLAY 유효성을 주장할 수 없다.
