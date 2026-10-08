# PREREG — REPLAY-CA-AMBIGUOUS-IDENTITY-QUARANTINE-0001

- frozen_source_pr: 108
- frozen_source_head_sha: ca4408424485157cdeb6fe0fe7366b9bb9e486ff
- stage: REPLAY
- run_cap: 2
- actual_event_cap: 0
- threshold_trials: 0
- external_calls: 0

## 사전등록 가설

안정적인 출처 사건 ID가 없으면 `(sym, kind)`가 같은 다른 의미 키는 새 사건인지 정정인지 구분할 수 없다. 그러므로 이미 적용된 anchor와 충돌하는 모든 다른 키를 격리하면 G1/G2 이중 적용은 방지되지만, 합법적인 후속 사건도 차단하는 보수적 오탐이 생긴다.

## 고정 판정

- exact key + exact payload → duplicate
- exact key + changed payload → applied-payload conflict
- changed key + applied same `(sym, kind)` → ambiguous-identity block
- unseen anchor → 기존 검증 후 적용

검증 fixture와 성공 조건은 TASK.md의 Q1~Q4에서 변경하지 않는다. 결과를 본 뒤 허용 예외, 날짜 간격, 수량 차이 threshold를 추가하지 않는다.

## 해석 제한

이 실험은 출처 사건 동일성을 복원하거나 증명하지 않는다. 실제 정정 사슬이 없으므로 차단의 안전성만 검사한다. Q3의 오탐은 실패를 숨기지 않고 NEEDS_DATA로 남긴다. 성과 및 실전/모의 준비 판정에는 사용하지 않는다.
