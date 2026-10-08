# PREREG — REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001

- preregistered_at: 2026-10-09T02:57:50+09:00
- source_pr: 114
- source_head_sha: 6261e5a100607b36fa033b8a2ce710482cf8ccfa
- source_code_blob_sha: 58417375acbef990dfc6726af7090a471a9d7a18
- source_evidence_blob_sha: 02f65d3c797d988315880cf08cbdbfbc5c72915f
- source_report_blob_sha: cd34b51f9ffc8fd6bf759ee510ed76f6f43f3544
- run_limit: 1
- mode: read-only static audit
- actual_events: 0

## 사전 가설

H1. PR #114의 quantity gate는 독립 합성 코드이며 실제 입력 producer와 연결되지 않았을 가능성이 높다.

H2. 기존 계약 문서에는 필요한 필드가 선언돼도 실제 Train 사건과 원 source event ID·정정 계보·available_at을 연결하는 데이터 행은 없을 수 있다.

H3. 문서/fixture의 필드 존재를 실제 production provenance로 계산하면 안 된다.

## 고정 검색 집합

TASK.md의 14개 검색어를 모두 사용한다. 검색 대상은 source head의 추적 파일이며 binary, git object, 비밀 파일, 외부 경로는 제외한다. 결과 match마다 path와 line을 보존하고 다음 중 하나로 분류한다.

- producer: 외부/원시 입력에서 필드를 최초 생성
- transformer: 필드를 변환·정규화
- consumer: 필드를 판정·회계에 사용
- test: 합성 fixture/검사
- doc: 주장·계약·설명
- data: 실제 또는 파생 데이터 행

동일 match의 복수 역할은 허용하되 근거를 적는다.

## 판정 규칙

각 필드의 trace가 실제 source→producer→transformer→consumer→evidence를 모두 가지면 `PRESENT_VERIFIED`다. 문서나 합성 fixture만 있거나 actual row 연결이 없으면 `PRESENT_UNLINKED`. match가 없으면 `ABSENT`. 상충하는 정의가 있으면 `CONFLICTING`.

실제 값, 계정, API, 비공개 자료가 있어야만 연결할 수 있으면 `NEEDS_DATA`이며 해당 자료를 읽거나 요청 범위를 확장하지 않는다.

## 성공 해석

READY는 정적 감사의 완결만 뜻한다. `PRESENT_VERIFIED`를 보장하지 않으며, 실제 기업행위·NAV·성과·모의투자 준비 판정이 아니다.
