# TASK — REPLAY-CA-APPLIED-PAYLOAD-PROVENANCE-0001

- task_id: `REPLAY-CA-APPLIED-PAYLOAD-PROVENANCE-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 32
- status: READY
- source_pr: 106
- source_head_sha: `dacbcb096bbb07e0d176065872fad551e12927b0`

## 목적

이미 적용된 기업행동의 동일 의미키가 재수신될 때, 최초 적용의 canonical semantic payload와 비교하여 진짜 동일 재전송만 무시하고 내용 변경은 배치 전체를 fail-closed하는 영속 멱등성 계약을 만든다.

## 허용 범위

- PR #106 고정본 코드와 합성 fixture만 오프라인 사용
- 적용 레지스트리를 `key -> canonical semantic payload` 형태로 변경
- 현재 스키마의 행동 영향 필드만 canonical payload에 포함: `m_price`, `real`
  - `sym/kind/m_qty/apply_date`는 의미키에 이미 포함
  - `src` 차이만으로는 충돌시키지 말고 provenance 목록/해시로 별도 보존
- deterministic serialize → reload 후에도 같은 판단을 내는 합성 round-trip
- 수정 전 고정본 음성대조군과 수정 후 유한 fixture 실행

## 필수 상태 전이

1. 최초 적용 시 key와 canonical payload를 원자적으로 함께 기록한다.
2. 이미 적용된 key + 동일 canonical payload:
   - `DUPLICATE_IGNORED`
   - 다른 유효 신규 사건이 같은 배치에 있으면 그 사건만 정상 커밋 가능
3. 이미 적용된 key + 다른 canonical payload:
   - `BLOCKED_APPLIED_PAYLOAD_CONFLICT`
   - 함께 들어온 다른 유효 사건까지 배치 전체 `BATCH_ABORTED`
   - positions/cash/applied registry/provenance hash는 배치 전과 동일
   - 탐지일부터 `PERF_BLOCKED`
4. 동일 판정은 serialize/reload 전후와 입력 순서 전부에서 같아야 한다.
5. source 번호가 다르지만 semantic payload가 같은 재전송은 중복으로 무시하되 provenance에 관찰 사실을 보존한다.

## 필수 fixture

- P1: 전날 A 적용 → 다음 날 같은 payload·다른 src A 재전송 + B 정상: COMMITTED, A ignored, B 1회
- P2: 전날 A 적용 → 다음 날 같은 key·다른 m_price A + B 정상: BATCH_ABORTED, 상태/registry 해시 불변
- P3: 전날 A 적용 → 다음 날 같은 key·`real=true` A + B 정상: BATCH_ABORTED, 상태/registry 해시 불변
- P4: P1~P3 각각 serialize/reload 뒤 동일 결과
- P5: P2~P3의 두 입력 순서 모두 같은 판정·상태·해시
- 수정 전 PR #106 고정본에서 P2와 P3가 `DUPLICATE_IGNORED`로 빠지는 음성대조군 재현

## 금지

새 URL/API/키/수집/캐시, 실제 종목·실제 기업행동·실제 날짜, 실제 8건 적용, price_basis_date 추정, 리플레이·백테스트·성과/NAV 계산, 새 threshold/alpha 탐색, 모의·실계좌 주문, 운영 봇·전략·배분·워크플로·인증 변경, 자동병합을 금지한다.

## 완료 조건

- READY: 모든 필수 fixture와 수정 전 음성대조군이 사전등록 기대와 일치하고, 레지스트리·provenance를 포함한 상태 해시의 원자성 및 reload 불변성이 증거에 남는다.
- BLOCKED: 하나라도 불일치하면 실제 상태 변경 없이 정확한 실패 경로와 필요한 자료를 보고한다.
- 어느 경우든 실제 적용 0, 기존 `+19.90%`·NAV 미검증, `PAPER_VALIDATION_READY=false`를 유지한다.
- REPORT/manifest/evidence/receipt를 PR 개설 전에 완성하고, 제출 후 결과 브랜치는 receipt 보정 외 불변으로 둔다.
