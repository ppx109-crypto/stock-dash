# TASK — REPLAY-CALENDAR-AUDIT-DISCLOSURE-ERRATUM-0001

- task_id: `REPLAY-CALENDAR-AUDIT-DISCLOSURE-ERRATUM-0001`
- chain_id: `PAPER-READINESS`
- round: 42
- status: `READY`
- source_pr: 126
- source_head_sha: `8df510c8e2e001daee31e3d35acc1ce3bcb17b49`
- 단계: REPLAY
- 목적: PR #126의 기존 산출물만 사용해 코드 실행 수와 사전등록 전 탐색을 정확히 정정하고, 내용상 감사 발견과 준수 판정을 분리한다.

## 허용 범위

- PR #126 exact-head의 PREREG, REPORT, manifest, receipt, search-log, search-counts, search_counts.py만 읽는다.
- 이미 기록된 명령·시각·파일로 실행 공개 정오표를 작성한다.
- `repo_strategy_code_executed=0`과 `helper_script_executed>=1`을 분리한다.
- 사전등록 전 집계의 범위·시각·영향을 명시한다.

## 완료 조건

1. `code_executions=0`을 유지하지 않는다. 최소한 helper Python 실행 1회 이상과 그 안의 git subprocess 실행을 사실대로 기록한다.
2. 정확한 총 실행 횟수를 기존 증거만으로 셀 수 없으면 `unknown_but_nonzero`로 둔다. 숫자를 만들어내지 않는다.
3. `repo_strategy_code_executed=0`, `tests_executed=0`, `workflow_executed=0`, `external_calls=0`은 별도 필드로 구분한다.
4. 사전등록 전 탐색이 있었음을 `pre_prereg_exploration=true`로 기록하고 clean preregistration 주장을 하지 않는다.
5. 권위 달력 ABSENT, 연결 단절, NEEDS_DATA는 “기존 정적 발견”으로만 보존한다. 새 검색·분류·주장 확장은 금지한다.
6. 결과는 새 branch/PR의 REPORT·manifest·receipt·evidence/erratum.json로 제출한다.
7. 결과 status는 정정 완료 시 READY, 기존 증거만으로 정정 자체가 불가능하면 BLOCKED다.
8. `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false`를 유지한다.
9. 정정 완료 뒤 프로그램 상태를 `WAITING_DATA`로 고정하고, 권위 달력 자료가 들어오기 전 후속 구현·실험을 제안하지 않는다.

## 금지

- 새 검색, git grep, helper script·저장소 코드·테스트·workflow 실행
- 새 API·웹·외부 자료·자격증명·데이터 수집
- 달력 생성·구현, replay/backtest/성과 산출
- threshold·alpha 탐색
- 실제·모의 주문 API, 운영 봇·전략·배분·workflow·인증 변경
- 결과 PR #126 branch 수정, 자동병합, 비밀·계좌·원본 응답 공개
