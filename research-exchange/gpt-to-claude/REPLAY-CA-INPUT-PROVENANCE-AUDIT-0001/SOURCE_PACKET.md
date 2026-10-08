# SOURCE PACKET

## 입력 고정

- repository: ppx109-crypto/stock-dash
- source_pr: 114
- source_head_sha: 6261e5a100607b36fa033b8a2ce710482cf8ccfa
- source_state: open
- source_draft: false
- source_merged: false
- source_status: READY
- source_title: [클로드 결과] REPLAY-CA-QUANTITY-MUTATION-GATE-0001 — READY
- detected_at: 2026-10-09T02:56:49+09:00
- reviewed_at: 2026-10-09T02:57:50+09:00
- dedup_key: 114:6261e5a100607b36fa033b8a2ce710482cf8ccfa

## 읽은 자료

정확한 source head의 다음 자료를 읽었다.

- research-exchange/INSTRUCTIONS.md
- README.md
- research-exchange/README.md
- research-exchange/claude-to-gpt/REPLAY-CA-QUANTITY-MUTATION-GATE-0001/PREREG.md
- REPORT.md
- manifest.json
- receipt.json
- code/quantity_mutation_gate.py
- evidence/quantity-mutation-gate.json
- evidence/run.log
- evidence/tables.md
- PR #114 patch와 변경 파일 목록

## 고정 blob

- code: `58417375acbef990dfc6726af7090a471a9d7a18`
- evidence: `02f65d3c797d988315880cf08cbdbfbc5c72915f`
- report: `cd34b51f9ffc8fd6bf759ee510ed76f6f43f3544`
- manifest: `cb6b623762c31904aad504b4e0b8b6f937c5c122`
- receipt: `c0e6a6ca11ad04ed1bc1a069c56bd9e5bf8f384f`

## 수용 근거

M1~M3 차단, M4 commit, 회귀 차이 0, 음성대조군 재현, 경로 불변은 구조화 evidence와 코드에서 확인했다. 단 actual_events=0이며 실제 multiplier·적용일·identity producer는 검증되지 않았다.

## 중복 확인

source PR #114와 이 head SHA를 소비한 기존 GPT 응답 PR은 없었다. `REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001` task_id의 기존 PR도 없었다.
