# SOURCE PACKET — PR #108

- repository: ppx109-crypto/stock-dash
- source_pr: 108
- source_head_sha: ca4408424485157cdeb6fe0fe7366b9bb9e486ff
- source_branch: research-exchange/replay-ca-applied-payload-provenance-0001
- state_at_review: open
- draft_at_review: false
- merged_at_review: false
- source_status: READY
- base_sha: c789e6bba89c68b19968865798301c0c991842fb

## 읽은 자료

- `research-exchange/INSTRUCTIONS.md`
- 루트 `README.md`
- `research-exchange/README.md`
- PR #108의 PREREG, REPORT, manifest, receipt
- `code/payload_registry.py`
- `evidence/applied-payload-provenance.json`
- `evidence/run.log`

## 확정된 좁은 결과

PR #108은 적용 레지스트리를 의미 키→정규 payload로 영속화했다. 이미 적용된 동일 키가 같은 payload면 중복으로 무시하고, `m_price` 또는 `real`이 다르면 배치 전체를 중단한다. P1~P3는 두 입력 순서와 reload 유무 네 경로에서 동일한 결과를 냈다. 수정 전 PR #106 고정본은 P2/P3 충돌을 무시하고 B를 커밋하는 negative control이었다.

## 확정된 잔여 위험

코드의 의미 키는 `(sym, kind, str(m_qty), apply_date)`다. G1에서 적용일 변경은 새 키가 되어 수량 37→185→925 이중 적용이 발생했다. G2의 수량 변경은 동일성 충돌이 아니라 순서 검사로 우연히 막혔다. 실제 기업행위/정정 사슬은 0건이며, 성과/NAV/PAPER_VALIDATION_READY는 검증되지 않았다.
