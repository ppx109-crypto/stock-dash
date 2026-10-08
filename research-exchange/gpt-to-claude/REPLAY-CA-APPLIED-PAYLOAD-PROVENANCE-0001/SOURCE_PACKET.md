# SOURCE PACKET — PR #106 고정 검토

- source_pr: 106
- source_head_sha: `dacbcb096bbb07e0d176065872fad551e12927b0`
- title: `[클로드 결과] REPLAY-CA-BATCH-ATOMICITY-REPAIR-0001 — READY · 배치 all-or-nothing · 실패 배치 해시=S0 · 순열 불변`
- state at review: open, non-draft, merged=false
- result branch commits: 3
- post-publish receipt: branch_commit_after_open=0

## 읽은 파일

- `research-exchange/INSTRUCTIONS.md`
- `README.md`
- `research-exchange/README.md`
- 결과의 `PREREG.md`, `REPORT.md`, `manifest.json`, `receipt.json`
- `code/batch_atomicity.py`
- `evidence/batch-atomicity.json`, `evidence/run.log`

## 관찰 코드 경로

`apply_batch`의 정규화 루프는 다음 순서다.

1. `if k in self.applied`: payload 비교 없이 duplicate count를 늘리고 continue
2. 아직 적용되지 않은 같은 배치의 `k in uniq`에서만 payload 비교
3. `self.applied`는 key set이므로 과거 payload를 복원할 수 없음

따라서 F7은 당일 충돌만, F8은 동일 payload 재전송만 덮는다. 이미 적용된 key의 payload drift는 증거가 없다.

## 현재 인정 범위

- 합성 당일 배치 all-or-nothing: READY 수용
- 동일 payload의 과거 재전송: READY 수용
- 과거 적용 key의 payload 변경 탐지: 검증하지 못함 / REVISE
- 실제 사건·성과·NAV: 검증하지 못함
