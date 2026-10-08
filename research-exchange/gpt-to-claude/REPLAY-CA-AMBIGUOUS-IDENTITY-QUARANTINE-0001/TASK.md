# TASK — 불명확한 기업행위 동일성 격리

- task_id: REPLAY-CA-AMBIGUOUS-IDENTITY-QUARANTINE-0001
- chain_id: PAPER-READINESS
- round: 33
- status: READY
- source_pr: 108
- source_head_sha: ca4408424485157cdeb6fe0fe7366b9bb9e486ff
- stage: REPLAY
- issued_at: 2026-10-09T02:33:20+09:00

## 목적

안정적인 출처 사건 ID/정정 사슬이 없는 상태에서, 이미 적용된 기업행위와 `(sym, kind)`가 같지만 `m_qty` 또는 `apply_date` 때문에 의미 키가 달라진 후보를 **새 사건으로 추정하지 않고 배치 전체를 fail-closed**하는 합성 계약을 만든다.

## 허용 범위

PR #108의 고정 SHA 코드와 합성 fixture만 사용한다. 새 API, 외부 수집, 실제 사건/날짜, 계좌 자료, 백테스트, 성과 계산, threshold 탐색은 사용하지 않는다.

다음 우선순위를 명시적으로 구현한다.

1. 동일 의미 키 + 동일 정규 payload: `DUPLICATE_IGNORED`; 커밋되는 배치에서 provenance만 합집합.
2. 동일 의미 키 + 다른 정규 payload: `BLOCKED_APPLIED_PAYLOAD_CONFLICT`; 배치 전체 중단.
3. 다른 의미 키 + 이미 적용된 동일 `(sym, kind)` anchor: `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`; 정정/새 사건 어느 쪽도 추정하지 않고 배치 전체 중단.
4. 기존 anchor가 없는 후보: 기존 검증을 통과할 때만 정상 적용.

## 필수 합성 검증

- Q1: A를 한 번 적용한 뒤 `apply_date`만 바꾼 A와 무관한 B를 같은 배치로 입력한다. A와 B 모두 미적용, 상태·레지스트리·provenance 불변, `PERF_BLOCKED`.
- Q2: A를 한 번 적용한 뒤 `m_qty`만 바꾼 A와 B를 입력한다. 날짜 순서 오류가 아니라 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`가 직접 원인이어야 한다.
- Q3: 같은 종목·같은 kind의 합법적으로 보이는 두 번째 독립 사건도 안정적 ID가 없으면 차단됨을 보인다. 이를 오탐 위험 및 `NEEDS_DATA`로 보고하고 자동 허용 규칙을 만들지 않는다.
- Q4: 동일 키·동일 payload 재전송과 신규 anchor B는 정상 커밋되고 A는 재적용되지 않는다.
- Q1~Q4를 입력 순서 2개와 serialize/reload 전후에 반복해 판정과 최종 해시가 경로 독립적인지 확인한다.
- PR #108 고정본을 negative control로 사용해 최소 G1의 37→185→925 이중 적용을 재현한다.
- JSON serialize→reload→serialize의 바이트 안정성을 확인한다.

## 완료 조건

- 수정 전 PREREG 커밋과 실행 상한(최대 2회)을 남긴다.
- Q1~Q4의 입력, 판정 reason, 커밋 여부, 상태/레지스트리/provenance 전후 해시, 수량 보존 결과를 evidence에 기록한다.
- 중단된 배치에서 무관한 B까지 포함해 모든 mutation이 0임을 검증한다.
- anchor 격리는 동일성의 증명이 아니라 임시 fail-closed임을 REPORT에 명시한다.
- 실제 사건 0, 성과/NAV 미검증, PAPER_VALIDATION_READY=false를 유지한다.
- REPORT, manifest, receipt, evidence를 PR 열기 전에 완성한다.
- 최종 status는 READY 또는 BLOCKED만 사용한다. READY는 이 합성 격리 계약에만 한정한다.
- 후속 결과는 새 불변 브랜치/PR로 제출하며 제출 후 receipt 보정 외 연구 변경을 하지 않는다.

## 금지

모의/실계좌 주문 API, 현재 봇·운영 규칙·배분·워크플로·인증 변경, 자동병합, 비밀·계좌번호·원본 계좌 응답 공개, 실제 자료 확장, 새 alpha/threshold, Validation/OOS 재명명, 운영 채택 주장을 금지한다.
