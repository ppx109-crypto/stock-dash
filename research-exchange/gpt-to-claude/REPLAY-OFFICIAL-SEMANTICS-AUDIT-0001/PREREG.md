# PREREG — REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001

- task_id: `REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 23
- stage: REPLAY
- source_pr: 88
- source_head_sha: `a5891f5b91d7c206e5afb26049907f426e253c89`
- registered_at_kst: 2026-10-09T00:57:33+09:00
- status: READY

## 사전 가설

1. PR #88의 PIT/cutoff/MTM gate는 합성 계약으로는 개선됐으나, 기업행동 날짜 의미는 공식 근거가 없어 실제 재생에 쓰기 이르다.
2. OpenDART의 회사분할 구조화 API는 주식 액면분할을 완전하게 대체하지 않는다.
3. `FID_ORG_ADJ_PRC` 값 방향과 페이지/행 한도는 공식 KIS 문서에서 확인되지 않으면 UNKNOWN으로 남겨야 한다.
4. 정확한 접수시각을 얻지 못하면 DART 날짜-only 레코드는 당일 cutoff에 사용할 수 없다.
5. 기존 148 intent 매핑은 기존 체결 감사 분모이며 전체 판단일 목표의 완전 재생 분모가 아니다.

## 근거 우선순위

1. OpenDART 공식 개발가이드·API 서비스 목록·공시원문 안내
2. KRX/KIND 공식 규정·업무 안내·공시
3. 한국투자증권 KIS Developers 공식 API 문서
4. 저장소 고정 SHA의 코드·schema·evidence

공식 원문이 없으면 비공식 자료로 메우지 않고 BLOCKED/NEEDS_DATA로 둔다.

## 고정 출력 판정

- `ACCEPT`
- `REVISE`
- `BLOCKED_NO_OFFICIAL_EVIDENCE`
- `UNKNOWN_KIS_DOC_SEMANTICS`
- `UNKNOWN_CA_VERSION_PIT`
- `BLOCKED_UNMAPPED_KIND`
- `NEEDS_DATA`

## 실행 상한

- 공개 공식 문서 조회만 허용
- 데이터 API 호출: 0
- 인증/키/Secrets 접근: 0
- 실제 대상 수집: 0
- Train replay/performance: 0
- threshold/alpha 실험: 0

조회 결과를 본 뒤 판정 기준·사건 범위·날짜 의미를 바꾸지 않는다.
