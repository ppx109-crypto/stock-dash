# [GPT 지시] DATA-0001 — 시점별 연구증거 계약과 오프라인 검증기

```yaml
task_id: DATA-0001
program_id: PAPER-READINESS-20261008
chain_id: MEAS-20261008
round: 4
stage: RECOVERY-DATA-CONTRACT
status: READY
source_pr: 19
source_head_sha: 1d295ee32e16e05bbed6fe41f60b8efe44106bf6
source_result_status: BLOCKED
source_verdict: BLOCKED_NEEDS_DATA
paper_validation_ready: false
live_or_paper_order_approved: false
```

## 목표

REPLAY-0002의 G1~G12 결손이 앞으로 다시 생기지 않도록, KIS·DART·전략신호·model-fill·관측 모의체결을 위한 **append-only point-in-time 연구증거 계약**과 순수 오프라인 검증기를 만든다.

이번 단계는 데이터를 받거나 전략을 시험하는 단계가 아니다. 계약·스키마·합성 fixture·validator가 누수와 덮어쓰기를 차단하는지 검증하는 단계다.

## 허용 범위

1. `research-exchange/claude-to-gpt/DATA-0001/` 아래의 문서·스키마·순수 표준라이브러리 검증기·합성 fixture 작성.
2. REPLAY-0001 사건 계약과 REPLAY-0002 G1~G12를 고정 입력으로 참조.
3. 기존 KIS/DART 수집 코드와 파일 형식은 읽기 전용으로 mapping만 작성.
4. 비식별 합성 데이터만 사용한 결정론·변이·누수 시험.
5. 향후 1천만원과 1억원의 수량·용량 검증에 필요한 필드 정의만 수행. 성과나 주문은 계산하지 않는다.

## 금지 범위

1. KIS/DART/외부 API 호출, 네트워크 수집, 실제·모의 주문.
2. 현재 수집기·운영 봇·전략·배분·워크플로·인증·환경변수 수정 또는 재시작.
3. 과거 495행 보간·재생, 백테스트, 성과표, threshold·보유기간·손절·알파 탐색.
4. `nrl-cache.pkl`, 계좌 원문, `.env`, 비밀, 원 주문번호 열람·공개.
5. 수정주가를 원주가라고 표시하거나, git commit 시각을 데이터 available_at으로 대체하기.
6. 현재 종목 목록을 Universe(t)로 대체하거나 결측을 거래정지로 추정하기.
7. `READY`를 PAPER_VALIDATION_READY 또는 실전 승인으로 표현하기.
8. commit message·PR 본문·문서에 비공개 세션 주소 또는 `Claude-Session` trailer 기록.

## 필수 계약

### A. 공통 evidence envelope

모든 레코드에 최소 다음을 요구한다.

- `record_id`, `record_type`, `schema_version`
- `security_id`, `market`, 필요 시 `corp_code`
- `source_system`, `source_endpoint_or_report`, `source_mode`
- `as_of`, `available_at`, `fetched_at` — KST offset 포함
- `version`, `revision_of`, `is_correction`
- `raw_payload_sha256` 또는 원문 비공개 보관 참조, `normalized_sha256`
- `ingest_run_id`, `collector_version`, `created_at`
- 원자료 공개 가능 여부와 비식별 evidence reference

규칙: append-only, 기존 record 수정 금지, correction은 새 record로 연결, `available_at < as_of` 금지, 판단은 `available_at <= decision_at`인 version만 사용.

### B. 시장·Universe·거래가능성

- 원주가 OHLCV와 `adjusted=false`; 조정값은 별도 record type
- 정규장/시간외 session, 호가단위·가격제한 판정 입력
- 날짜별 Universe(t): 상장·상장폐지·신규상장·시장 이전·종목코드 변경
- 거래정지/재개와 효력 시각
- 기업행동: 종류, 비율, 기준일, 효력일, DART 접수번호·접수시각·정정 연결

### C. 수급·재무·DART

- 투자자별 수급의 대상 거래일과 실제 확정·수신 시각
- DART `rcept_no`, `rcept_dt`, 가능한 공시 시각, 정정공시 원본 연결
- 재무 기준일과 실제 available_at을 분리
- 최초판과 정정판을 덮어쓰지 않음

### D. 신호·주문·체결·비용

- `strategy_id`, `strategy_version/hash`, `signal_id`, `signal_at`, `decision_at`, `earliest_order_at`
- 신호에 사용한 모든 input record_id/version 목록과 cutoff hash
- `HISTORICAL_MODEL`과 `OBSERVED_KIS_PAPER` 완전 분리
- model-fill은 봉·가격·규칙·slippage 포함 여부를 기록
- observed paper fill은 비식별 evidence_ref 없으면 거부
- 주문 의도·접수·체결·취소·거절 순서와 KST timestamp
- 수수료·거래세·슬리피지 schedule의 출처·적용 시작/종료일·버전
- 현금·NAV·배분 입력의 시점과 evidence lineage

## 검증기 요구사항

1. JSON Schema만 작성하고 끝내지 말고 실제 validator로 전체 fixture를 검사한다.
2. 최소 30개 합성 사례를 결과 보기 전에 고정한다. 반드시 포함:
   - 정상 최초판/정정판
   - 덮어쓰기·동일 record 충돌
   - timezone 없음
   - available_at 역전·decision 이후 입력
   - revision_of 단절·순환
   - 수정주가를 원주가로 위장
   - Universe 스냅숏 결손
   - 거래정지·기업행동 효력시점
   - DART 장중/장후 공시와 정정
   - observed fill evidence 누락
   - 비용 schedule 공백·중첩
   - 동일 시각 seq 충돌
3. validator에 일부러 결함을 넣는 mutation test를 실행하고 각 결함이 어떤 fixture에서 잡혔는지 기록한다.
4. 실행 2회의 정규화 출력 hash가 같아야 한다.
5. 네트워크·API·운영 모듈·운영 상태 파일 접근 0을 검사한다. 경로 한 곳을 하드코딩하지 말고 허용 디렉터리 기반으로 검사한다.
6. G1~G12 각각이 어느 레코드와 validator rule로 해소되는지 traceability matrix를 낸다.

## 산출물

- `PREREG-LOCK.md`, `PREREG-LOCK.stamp.json`
- `REPORT.md`, `manifest.json`
- `EVIDENCE-CONTRACT.md`
- `schemas/*.schema.json`
- `fixtures/*.json`
- `validator.py`, `tests/run_tests.py`, `TEST-RESULT.json`
- `GAP-TRACEABILITY.json`
- `COLLECTOR-MAPPING.md`: 기존 KIS/DART 코드 → 계약 필드 mapping과 미지원 항목; 실행·수정 금지
- 입력 receipt: PR #19 + 정확한 current head SHA

## 완료 조건

1. 사전 고정된 합성 사례 전부와 공통 불변식 통과.
2. append-only·정정 lineage·decision cutoff·source_mode 분리를 validator가 실제로 강제.
3. G1~G12가 모두 `CONTRACT_COVERED` 또는 정확한 `STILL_NEEDS_EXTERNAL_DATA/AUTHORITY`로 분류.
4. 실제 수집·운영 활성화를 하지 않고 필요한 최소 권한·데이터만 별도 보고.
5. 실제 전략 성과 숫자 없음, `PAPER_VALIDATION_READY=false` 유지.
6. 결과 PR은 별도 불변 브랜치이며 status는 `READY` 또는 `BLOCKED`.
7. 제출 전에 REPORT·manifest·receipt 완성; result_pr은 null 허용.
8. commit/PR metadata에 비공개 세션 주소가 없어야 하며 제출 후 1회 재확인.

