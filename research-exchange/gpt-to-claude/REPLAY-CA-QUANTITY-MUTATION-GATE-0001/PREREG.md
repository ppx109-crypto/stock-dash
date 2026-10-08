# PREREG — REPLAY-CA-QUANTITY-MUTATION-GATE-0001

- preregistered_at: 2026-10-09T02:50:32+09:00
- source_pr: 112
- source_head_sha: 9e88dba81bc3e702dad2478b4cf3e86e99e691c5
- source_code_blob_sha: be0dda40db1b1b80280e41da279c3e91f6851025
- source_evidence_blob_sha: afc6579dcba3237329c382db0586219233a88c2d
- run_limit: 2
- stage: REPLAY
- actual_events: 0

## 가설

H1. 이미 quantity mutation이 적용된 종목에 다른 키의 quantity mutation이 오면 kind와 무관한 symbol-level ambiguity로 차단하면 `bonus_issue` 및 미지 kind 우회를 모두 막는다.

H2. 이 정책은 실제 event identity가 없는 상태의 임시 fail-closed이며, 합법적인 후속 quantity mutation도 차단한다.

H3. 새 종목의 첫 quantity mutation, exact duplicate, 기존 conflict 우선순위 및 PR #112 회귀는 보존할 수 있다.

## 고정 판정식

- quantity mutation: 입력 검증을 통과하고 `m_qty != 1`, `m_qty * m_price == 1`.
- prior quantity mutation: committed applied registry 안에서 동일 sym의 quantity mutation이 하나 이상 존재.
- prior가 있고 새 사건이 exact applied key가 아니면 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`.
- exact key 비교를 ambiguity보다 먼저 수행한다.

## 고정 시험

M1 bonus_issue, M2 unknown_qty_event, M3 합법적으로 보이는 후속 사건, M4 새 종목 첫 사건, PR #112 I1 음성대조군, K1~K3/Q1~Q4 회귀. 모든 판정은 구조화 JSON에서 산출하며 prose 기대 문자열을 실행 결과로 사용하지 않는다.

## 채택 기준

TASK.md의 READY 조건 전부 충족. 한 항목이라도 실패하면 BLOCKED. 결과를 본 뒤 fixture, 비교 필드, 성공 기준을 바꾸지 않는다.

## 해석 제한

통과해도 합성 장부의 방어 계약만 확인된다. 실제 기업행위 동일성, available_at, 정정 버전, 생존자편향, 비용/체결, 일별 MTM, 기존 OOS 독립성, 과거 수익률은 검증되지 않는다.
