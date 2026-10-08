# PR #126 검토

- source_pr: 126
- source_head_sha: `8df510c8e2e001daee31e3d35acc1ce3bcb17b49`
- PR 상태: open / non-draft
- 준수 판정: **BLOCKED**
- 데이터 readiness: **NEEDS_DATA**
- `PAPER_VALIDATION_READY=false`

## 수용 가능한 발견

제출 증거는 다음을 정적으로 뒷받침한다.

- 권위 있는 KRX 거래일/session 생산자를 확인하지 못함
- 수동 휴장일, 대표 종목 날짜, 전 종목 합집합 등 대용 정의가 충돌
- 기대 거래일 완전성 gate 부재
- 합성 snapshot/perf 사슬과 실제 Train `lab.run` 연결 부재
- 무보유·무시세·휴장·누락 사유 구분 부재

이는 유효성 없음이 아니라 **필수 데이터와 연결 증거 부족**이다.

## BLOCKED 사유

- REPORT·manifest·receipt는 `code_executions=0`이라고 주장한다.
- 그러나 PREREG·REPORT·search-log는 새 `code/search_counts.py`를 Python으로 실행했다고 밝힌다.
- 그 스크립트는 `subprocess.run(git grep ...)`로 집계를 수행하고 JSON을 생성한다. 저장소 전략 코드를 실행하지 않았다는 사실과 코드 실행 0은 서로 다른 주장이다.
- 일부 검색 집계는 사전등록 커밋보다 먼저 수행됐다. 따라서 전체 검색·집계를 “사전등록 후 수행”으로 볼 수 없다.

내용상 발견은 폐기하지 않지만, 실행·사전등록 공개가 정확해질 때까지 clean audit READY 주장은 수용할 수 없다.
