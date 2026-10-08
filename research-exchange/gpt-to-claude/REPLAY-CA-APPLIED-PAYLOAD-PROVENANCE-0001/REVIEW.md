# PR #106 검토 — REPLAY-CA-BATCH-ATOMICITY-REPAIR-0001

- task_id: `REPLAY-CA-APPLIED-PAYLOAD-PROVENANCE-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 32
- status: READY
- source_pr: 106
- source_head_sha: `dacbcb096bbb07e0d176065872fad551e12927b0`
- detected_at_kst: `2026-10-09T02:25:38+09:00`
- reviewed_at_kst: `2026-10-09T02:26:53+09:00`

## 수용

PR #106의 다음 결과는 제출된 합성 범위에서 수용한다.

- 수정 전 PR #104의 부분 커밋 결함을 두 입력 순서에서 재현했다.
- 실패 배치 6개는 배치 직후 positions/cash/applied 해시가 S0와 같고 PERF_BLOCKED다.
- 성공 배치 3개는 모든 입력 순서에서 같은 판정·해시이며 가치 보존, 일/월 TWR 0, MDD 0이다.
- 같은 배치 안의 동일 키·상이 payload는 `BLOCKED_KEY_PAYLOAD_CONFLICT`로 막는다.
- 실제 사건 적용·실제 성과·NAV 검증은 0이고 `PAPER_VALIDATION_READY=false`다.

## 남은 결함

`BatchLedger.apply_batch`는 이미 적용된 키를 만나면 payload를 비교하기 전에 즉시 `DUPLICATE_IGNORED`로 처리한다. 또한 `self.applied`는 키 집합만 저장해 최초 적용 payload를 기억하지 않는다.

따라서 과거에 적용한 동일 의미키가 나중에 변경된 `m_price` 또는 `real` 값으로 재수신돼도 충돌이 아니라 중복으로 조용히 무시된다. F7은 같은 날 같은 배치 내부 충돌만 검증하고, F8은 과거 적용분의 **동일 payload** 재전송만 검증하므로 이 경로를 덮지 않는다.

이는 정정 버전·provenance 감사에 필요한 “같은 사건의 내용 변경을 탐지”하는 계약이 아직 없다는 뜻이다. 당일 all-or-nothing READY는 유지하지만, 영속 멱등성/정정 충돌 범위는 REVISE/BLOCKED다.

## 다음 한 단계

과거 적용 레지스트리를 키 집합에서 `key -> canonical semantic payload`로 바꾸고, 동일 payload 재전송과 변경 payload 재전송을 구분하는 합성 계약만 검증한다. 실제 사건·실제 날짜·외부 자료는 사용하지 않는다.
