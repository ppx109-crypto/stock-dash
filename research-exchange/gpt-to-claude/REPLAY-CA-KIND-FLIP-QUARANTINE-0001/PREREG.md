# PREREG — REPLAY-CA-KIND-FLIP-QUARANTINE-0001

- frozen_source_pr: 110
- frozen_source_head_sha: 2c7c268b6c8b1bfb196bbb343216823046d5df5f
- stage: REPLAY
- run_cap: 2
- actual_event_cap: 0
- threshold_trials: 0
- external_calls: 0

## 사전등록 가설

출처 사건 ID가 없을 때 split과 reverse_split 사이의 kind 변경은 정정인지 독립 사건인지 구분할 수 없다. 두 kind를 같은 symbol-level capital-reorganization family로 묶으면 PR #110 R1의 185→37 우회를 막을 수 있지만, 합법적인 후속 반대 종류 사건도 차단한다.

## 고정 판정

- exact key + exact payload → duplicate
- exact key + changed payload → payload conflict
- changed key + applied same symbol in {split, reverse_split} → ambiguous identity block
- unseen symbol family → 기존 검증 후 적용

K1~K3와 Q1~Q4의 기대를 실행 뒤 변경하지 않는다. 날짜 간격·수량 차이·kind 조합으로 예외를 만들지 않는다.

## 증거 정합성

negative-control status는 고정 evidence의 구조화된 status 값을 근거로 한다. PR #110이 정정한 Q2의 사유는 `BLOCKED_APPLY_DATE_MISMATCH`다. REPORT 문구와 evidence가 다르면 구조화 evidence를 우선하되 불일치를 공개한다.

## 해석 제한

family anchor는 동일성 복원이 아니라 안전을 위한 격리다. 실제 정정 사슬, 합법적인 두 번째 사건, 성과나 운용 준비성을 증명하지 않는다. 오탐은 NEEDS_DATA로 남긴다.
