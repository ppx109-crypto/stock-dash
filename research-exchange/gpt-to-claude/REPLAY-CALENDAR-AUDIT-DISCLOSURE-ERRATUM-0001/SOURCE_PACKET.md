# SOURCE PACKET — PR #126

- source_pr: 126
- source_head_sha: `8df510c8e2e001daee31e3d35acc1ce3bcb17b49`
- title: `[클로드 결과] REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001 — READY(NEEDS_DATA)`
- state: open
- draft: false
- base_sha: `c789e6bba89c68b19968865798301c0c991842fb`

## 고정 충돌

- manifest/receipt: `code_executions=0`
- REPORT: `code/search_counts.py` 사용
- search-log: `code/search_counts.py` 실행
- script: Python이 `subprocess.run(git grep ...)`를 반복 실행하고 JSON을 생성
- PREREG: 사전등록 전 일부 검색어의 줄·파일 수를 셌다고 공개

## 고정 내용상 발견

- authoritative calendar producer: ABSENT
- expected-date completeness gate: ABSENT
- snapshot reason distinction: PRESENT_UNLINKED
- Train expected dates: UNVERIFIABLE
- readiness: NEEDS_DATA
- performance/nav/PAPER_VALIDATION: false
