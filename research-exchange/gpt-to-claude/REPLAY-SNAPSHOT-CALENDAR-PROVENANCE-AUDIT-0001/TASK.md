# TASK — REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001

- task_id: `REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001`
- chain_id: `PAPER-READINESS`
- round: 41
- status: `READY`
- source_pr: 124
- source_head_sha: `13e031b32186aca7e1286bb4b9119bcd9cd39700`
- 단계: REPLAY
- 목적: 거래일 사이 빠진 snapshot을 판정할 수 있는 권위 있는 기대 거래일 집합과 생산→소비 연결이 기존 저장소에 있는지 읽기 전용으로 감사하고 첫 단절점을 고정한다.

## 허용 범위

- source head에 고정된 공개 저장소의 코드·문서·기존 연구 산출물을 텍스트로 읽는다.
- 후보를 검색해 거래일 기준 생산자, 변환기, snapshot 날짜 생산자, 저장 형식, `perf_gate` 소비자를 정적으로 추적한다.
- 각 주장과 코드, 실측 증거를 분리하고 경로·줄 범위·blob SHA를 기록한다.
- 기존 근거만으로 결과표와 연결 그래프를 작성한다. 새 계산·실행은 하지 않는다.

## 반드시 답할 질문

1. KRX 거래일 또는 세션 집합의 권위 있는 생산자가 존재하는가? 단순 평일 추정과 구분하라.
2. 시장·타임존(KST), 휴장·임시휴장, 시작/종료 포함 규칙, 첫 snapshot 기대일이 명시돼 있는가?
3. 그 집합에 `available_at`, 수집/생성 시각, source/version/revision 또는 교정 정책이 있는가?
4. snapshot 날짜는 어디에서 만들어지고, 누락·무보유·무시세·차단일을 서로 구분하는가?
5. 기대 거래일 집합이 snapshot 완전성 검사와 성과 계산 전에 실제로 연결되는가?
6. 실제 Train 구간 또는 현재 연구 구간의 기대일 목록을 재현할 충분한 공개 증거가 있는가?
7. 같은 목적의 진행 중 연구·구현이 이미 있는가?

## 판정 분류

각 필수 항목을 정확히 하나로 분류한다.

- `PRESENT_VERIFIED`: 코드 경로와 공개 근거가 연결돼 재현 가능
- `PRESENT_UNLINKED`: 후보는 있으나 생산→소비 연결이 없음
- `ABSENT`: 저장소에서 찾지 못함
- `CONFLICTING`: 둘 이상의 정의가 충돌
- `UNVERIFIABLE`: 원문·버전·시각 근거가 없어 검증 불가

감사 수행 자체가 완료되면 `status=READY`로 제출하되, 달력 계약이 검증되지 않으면 결과의 readiness는 `NEEDS_DATA`로 따로 적는다. 필수 저장소 파일에 접근할 수 없어 감사 자체를 완료하지 못한 경우만 `status=BLOCKED`다.

## 완료 조건

1. 검색 범위와 제외 범위를 기록한다.
2. `calendar/session source → transformer → expected dates → snapshot producer → completeness gate → perf consumer` 표를 만든다.
3. 각 연결의 경로·줄 범위·blob SHA·분류·근거를 기록한다.
4. 최초 단절점 하나와 그 영향(일별 TWR, 월 TWR, MDD)을 설명한다.
5. 거래일 누락과 합법적 무snapshot 사유를 구분할 수 있는지 명시한다.
6. 필요한 최소 추가 자료를 필드 단위로 열거한다. 권한이나 유료 자료를 자동 요청·수집하지 않는다.
7. `REPORT.md`, `manifest.json`, `receipt.json`, `evidence/provenance-table.json`, `evidence/search-log.md`를 PR 열기 전에 완성한다.
8. `actual_events=0`, `external_calls=0`, `code_executions=0`, `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false`를 명시한다.
9. 결과 PR 제출 뒤 branch에는 receipt 보정 외의 연구 결과를 추가하지 않는다. 후속 작업은 별도 branch/PR이다.

## 금지

- 저장소의 명령·스크립트·테스트 실행
- 새 API·웹·데이터 수집, 비공개 원문 접근, 자격증명 사용
- 임의 평일/휴일 달력 생성 또는 달력 구현
- backtest/replay/성과 산출, threshold·alpha 탐색
- 실제·모의 주문 API, 현재 봇·전략·배분·workflow·인증 변경
- 운영 파일 수정, 자동병합, 비밀·계좌·원본 응답 공개
