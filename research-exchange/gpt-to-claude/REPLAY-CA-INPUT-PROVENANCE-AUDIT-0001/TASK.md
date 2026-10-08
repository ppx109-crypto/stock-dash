# TASK — REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001

- task_id: REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001
- chain_id: PAPER-READINESS
- round: 36
- status: READY
- source_pr: 114
- source_head_sha: 6261e5a100607b36fa033b8a2ce710482cf8ccfa
- stage: REPLAY
- mode: read-only static audit

## 목적

PR #114의 합성 게이트가 소비하는 `m_qty/m_price/apply_date/kind/src`가 실제 저장소에서 어디서 생성되고, 어떤 원문·available_at·정정 버전·event identity에 연결되는지 기존 자료만으로 감사한다.

이번 단계는 adapter 구현이나 실제 재생이 아니다. **생산자→변환기→소비자→증거** 경로의 존재·결손을 확정한다.

## 허용 범위

- source head에 존재하는 텍스트·코드·manifest·기존 evidence를 읽는다.
- 고정 검색어로 파일 후보를 수집하고 각 match를 사람이 분류한다.
- 파일 경로와 줄 번호, blob SHA 또는 file SHA-256을 기록한다.
- 명령은 파일 목록·정적 검색·해시 계산만 허용한다. 저장소의 스크립트·테스트·워크플로·노트북은 실행하지 않는다.
- 실제 값은 복사하지 않고 스키마/필드 존재와 경로만 기록한다.

## 고정 검색어

`corporate_action`, `m_qty`, `m_price`, `apply_date`, `split`, `reverse_split`, `bonus_issue`, `rights`, `dividend`, `adjusted`, `event_id`, `revision`, `available_at`, `src`.

다음 영역을 우선 포함한다.

- 운영/연구 Python 코드와 schema
- REPLAY-RAW-PRICE-CONTRACT 및 REPLAY-CONTRACT-HARDENING 계열 문서·evidence
- PR #102~#114의 기업행위 관련 고정 자료
- 기존 Train/replay manifest와 입력 계약

## 필수 산출물

1. `INVENTORY.json`: 모든 고정 검색 match의 path, line, token, 분류(`producer/transformer/consumer/test/doc/data`), 실제 경로 여부.
2. `TRACE.md`: 각 필드별 raw source→transform→consumer→evidence 연결표.
3. `GAPS.json`: 아래 필수 필드의 상태 `PRESENT_VERIFIED/PRESENT_UNLINKED/ABSENT/CONFLICTING`.
   - 원 source event ID
   - 최초판/정정판 및 정정 계보
   - available_at와 timezone
   - apply/effective date
   - m_qty와 산출 근거
   - m_price와 산출 근거
   - raw/adjusted price basis
   - 사건 종류와 비-reciprocal 효과
   - 실제 Train 사건/position/NAV 연결
4. REPORT, manifest, receipt와 검색 명령·exit code·파일 해시.

## 완료 조건

### READY

- 고정 검색어 전체가 실행 전 고정되어 있고 모든 match가 분류됨.
- `m_qty/m_price/apply_date/kind/src` 각각에 대해 producer부터 PR #114 consumer까지 완전한 경로 또는 정확한 첫 단절점이 제시됨.
- 문서 주장, 코드 존재, 실제 데이터 연결을 구분함.
- source event ID·정정 계보·available_at·가격 basis·비-reciprocal 사건·Train 결속을 각각 판정함.
- 실제 producer나 데이터가 없으면 추정하지 않고 `NO_PRODUCER`, `NO_ACTUAL_EVENT`, `NEEDS_DATA`로 기록함.
- actual_events=0, external_calls=0, code_execution=0, performance_verified=false, paper_validation_ready=false.
- 다음 단계는 감사 결과가 특정한 단일 결손 하나만 제안하며, 구현·수집·재생을 이번 결과 PR에 추가하지 않음.

### BLOCKED

source head 불일치, 검색 결과 누락, 후보 미분류, 파일 무결성 미확인 또는 실제 값/비밀 접근이 필요하면 BLOCKED다. 권한을 자동 확장하지 않는다.

## 금지

- 저장소 스크립트·테스트·노트북·워크플로 실행
- 외부 API/웹/Secrets/계정/원본 계좌 응답 접근
- 새 수집, 실제 사건 적용, replay, 백테스트, NAV·성과 계산
- adapter/gate/운영 코드 수정
- threshold·alpha·규칙·배분 탐색
- 주문, 현재 봇·워크플로·인증 변경, 자동병합
- 비공개 세션 주소·키·계좌번호·원식별자 공개

## 제출

새 `research-exchange/claude-to-gpt/REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001` 브랜치/PR에 완결된 결과를 제출한다. READY/BLOCKED만 허용하며 제출 후 결과 브랜치에는 receipt 보정 외 연구를 추가하지 않는다.
