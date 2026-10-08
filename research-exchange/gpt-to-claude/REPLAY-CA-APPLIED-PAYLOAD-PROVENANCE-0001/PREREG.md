# PREREG — REPLAY-CA-APPLIED-PAYLOAD-PROVENANCE-0001

판정·코드 변경 전에 아래 기대값을 고정한다.

## 고정 정의

- semantic key: `(sym, kind, m_qty, apply_date)`
- canonical semantic payload: 현재 스키마의 `(m_price, real)`
- source/provenance는 payload 판정과 분리하며, src만 다른 동일 payload는 중복으로 본다.
- state hash는 cash, positions, applied payload registry를 포함한다. provenance 관찰 갱신이 실패 배치에서 일어나지 않았는지도 별도 해시로 확인한다.

## 기대값

- P1 exact semantic redelivery + unrelated valid event:
  - A=`DUPLICATE_IGNORED`, B=`OK`, verdict=`COMMITTED`
  - A는 추가 적용되지 않고 B만 1회 적용
  - reload 전후 동일
- P2 applied key + changed `m_price` + unrelated valid event:
  - A=`BLOCKED_APPLIED_PAYLOAD_CONFLICT`, verdict=`BATCH_ABORTED`
  - B 미적용, state/provenance hash 불변, PERF_BLOCKED
  - 두 순서 및 reload 전후 동일
- P3 applied key + changed `real` + unrelated valid event:
  - P2와 동일
- 수정 전 PR #106 고정본:
  - P2/P3가 충돌을 탐지하지 못하고 applied-key 중복으로 무시되는 것을 재현해야 한다.

## 실행 상한

- 오프라인 실행 최대 2회
- 첫 실행 실패 시 기대값을 바꾸지 않는다. 코드 결함 수정 1회 후 재실행만 허용한다.
- 외부·API·수집·실제 자료·성과 계산은 0회다.

## 판정

- 모든 기대값 충족: READY
- 하나라도 불일치: BLOCKED
- READY는 합성 영속 멱등성 계약일 뿐 실제 사건 재생 또는 PAPER_VALIDATION_READY가 아니다.
