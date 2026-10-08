# PR #108 검토 — 적용 payload 영속성

- task_id: REPLAY-CA-AMBIGUOUS-IDENTITY-QUARANTINE-0001
- chain_id: PAPER-READINESS
- round: 33
- status: READY
- source_pr: 108
- source_head_sha: ca4408424485157cdeb6fe0fe7366b9bb9e486ff
- reviewed_at: 2026-10-09T02:33:20+09:00
- stage: REPLAY

## 판정

PR #108의 READY는 **합성 영속 멱등성 계약**에 한해 받아들인다. 적용 완료 키에 대해 정규화한 `m_price` 또는 `real`이 바뀐 재전송을 `BLOCKED_APPLIED_PAYLOAD_CONFLICT`로 배치 전체 중단하고, 상태와 provenance를 불변으로 유지한 결과는 증거와 일치한다. 동일 내용 재전송의 중복 무시와 결정적 직렬화도 이 좁은 범위에서 재현됐다.

성과, 실제 기업행위, +19.90%, NAV, 손실 한도, PAPER_VALIDATION_READY는 검증되지 않았다. 실제 사건 수는 0이다.

## 핵심 잔여 결함

현재 의미 키는 `(sym, kind, m_qty, apply_date)`다. 따라서 키 자체에 포함된 가변 필드가 바뀌면 기존 payload 레지스트리 비교를 우회한다.

- G1: 적용일만 바뀐 같은 것으로 보이는 사건이 새 키가 되어 A 수량이 37→185→925로 이중 적용됐다.
- G2: `m_qty` 변경은 동일성 충돌로 차단된 것이 아니라 과거 날짜 순서 검사에 우연히 걸렸다.
- 안정적인 출처 사건 ID/정정 사슬은 PR #90에서 UNKNOWN/NEEDS_DATA였으므로 이를 추정하거나 새 OOS로 간주할 수 없다.

따라서 PR #108은 필요한 개선이지만 기업행위 동일성 계약은 아직 안전하지 않다.

## 다음 한 단계

외부 ID가 없을 때 `(sym, kind)`가 같은데 의미 키가 다른 후보를 새 사건이나 정정으로 추정하지 않고 전부 격리하는 합성 fail-closed 계약을 검증한다. 이 규칙은 합법적인 후속 사건도 막을 수 있는 보수적 임시 장치이며, 그 오탐을 명시적으로 증거화한다. 운영 적용이나 threshold 연구가 아니다.
