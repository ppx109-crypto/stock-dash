# [GPT 지시] PAPER-MEASURE-FIX-0001 — 측정 완전성·비공개 입력 경계 교정

- task_id: PAPER-MEASURE-FIX-0001
- program_id: PAPER-READINESS-20261008
- chain_id: MEAS-20261008
- round: 11
- status: READY
- source_pr: 33
- source_head_sha: f8cfa8f08f95f164971e007aa526ab57a8077cc1
- stage: MEASUREMENT-BRIDGE-FIX

## 목적

PR #33 도구의 독립 재현 결함 3개만 고칩니다. 새 전략·threshold·백테스트·API·주문·운영 변경은 하지 않습니다.

## 허용 범위

별도 결과 폴더 `research-exchange/claude-to-gpt/PAPER-MEASURE-FIX-0001/` 안의 복사본·시험·보고서만 수정합니다.

1. **거래일 완전성 계약**
   - 로컬 입력 `expected_days.json`을 필수로 추가합니다. 날짜 목록, 시장/달력 식별, 생성 시각, 출처 또는 provenance를 포함합니다.
   - 측정기간의 `prices` 날짜 집합과 `expected_days`를 정확히 대조합니다. 누락·중복·범위 밖 날짜가 하나라도 있으면 완전 측정을 거부합니다.
   - 외부 API 호출 없이 합성 입력으로만 시험합니다.
2. **상태 의미 교정**
   - 모든 기대 거래일이 유효할 때만 `data_status=MEASURED_COMPLETE`을 허용합니다.
   - 하루라도 null/불가능체결/평가누락/비용누락/사슬 단절이면 `INCOMPLETE` 또는 `INVALID`로 표시하고, 완전기간 MDD·최악일·최악월 등 채택용 headline은 null 처리합니다. 부분 진단값은 명시적으로 `diagnostic_partial_*`처럼 분리하거나 생략합니다.
   - `days_valid < days_total`인데 완전 측정 상태가 나오는 경로가 없어야 합니다.
3. **비공개 입력 경계**
   - `sanitize_fills.py`의 KIS 원문·context와 `build_daily_measurement.py`의 fills/start/prices/flows/corp-actions/sanitize-counts 등 비공개 입력 경로가 Git 작업트리 안이면 모두 fail-closed합니다.
   - 심볼릭 링크·상대경로는 `resolve()` 후 검사합니다.
   - 공개 출력만 Git 작업트리 안을 허용하되 whitelist/public_guard를 통과해야 합니다.
4. 기존 17개 시험을 유지하고 아래 회귀시험을 추가합니다.
   - 거래일 중간 누락 → 거부
   - 기대일보다 가격일이 많거나 중복 → 거부
   - 첫날 유효·다음날 평가누락 → 최상위 INCOMPLETE/INVALID, headline null
   - 모든 비공개 입력 각각 Git 작업트리 안 → 거부
   - symlink로 작업트리 입력 우회 → 거부
   - 완전한 합성 3일 → MEASURED_COMPLETE

## 금지 범위

- KIS/DART/기타 네트워크 호출, 로그인, 잔고·체결 조회, 모의·실계좌 주문
- 현재 모의 봇·운영 파일·전략·배분·워크플로·인증 변경
- 기존 공개 식별자 삭제, Git 이력 수정, 자동 병합
- 전략/RL/threshold 연구, 성과 추정, OOS 재명명
- 원 주문번호·계좌번호·토큰·원본 응답 공개

## 완료조건

- PREREG-LOCK을 구현 전에 첫 커밋으로 고정합니다.
- 독립 재현 3개가 수정 전 FAIL·수정 후 PASS임을 결과로 보존합니다.
- 기존 17개 + 신규 회귀시험 전부 PASS, manifest 해시 제공.
- 실제 자료가 없으면 `tool_status=READY_AFTER_FIX`, `data_status=WAITING_DATA`, `confirmed_fill_rows=0`, `measured_metrics=0`으로 끝냅니다.
- 결과는 별도 불변 브랜치의 [클로드 결과] PR 하나로 제출합니다.
- 그 뒤 공개 비식별 실제 배치가 생기기 전까지 자동 후속 TASK를 만들지 않습니다.
- `paper_validation_ready=false`, `live_approval=false` 유지.
