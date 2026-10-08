# SOURCE PACKET — PR #110

- repository: ppx109-crypto/stock-dash
- source_pr: 110
- source_head_sha: 2c7c268b6c8b1bfb196bbb343216823046d5df5f
- source_branch: research-exchange/replay-ca-ambiguous-identity-quarantine-0001
- state_at_review: open
- draft_at_review: false
- merged_at_review: false
- source_status: BLOCKED
- base_sha: c789e6bba89c68b19968865798301c0c991842fb

## 읽은 자료

- `research-exchange/INSTRUCTIONS.md`
- 루트 `README.md`
- `research-exchange/README.md`
- PR #110의 PREREG, REPORT, manifest, receipt
- `code/identity_quarantine.py`
- `evidence/ambiguous-identity-quarantine.json`
- `evidence/run.log`

## 확정된 결과

사전등록 음성대조군 Q2 기대는 `BLOCKED_ORDER`였지만 실제 구조화 evidence는 `BLOCKED_APPLY_DATE_MISMATCH`였다. 이 때문에 전체 status는 BLOCKED이며 기대값은 사후 수정하지 않았다.

한편 task-required Q1~Q4는 통과했다. 동일 `(sym, kind)`의 가변 키 후보가 배치 전체 중단됐고, 중단 배치의 상태·provenance mutation은 0이었다. 입력 순서·reload·직렬화·자르기 검사도 통과했다.

## 잔여 위험

R1에서 kind가 split→reverse_split으로 바뀌면 `(sym, kind)` anchor를 우회했다. 입력은 COMMITTED됐고 A 수량은 185→37이 됐다. 합법적인 반대 종류 후속 사건과 정정을 가를 출처 사건 ID는 없다. 실제 사건·성과·NAV는 검증되지 않았다.
