# TASK — REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001

## 식별자

- task_id: `REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 23
- status: READY
- stage: REPLAY
- source_pr: 88
- source_head_sha: `a5891f5b91d7c206e5afb26049907f426e253c89`
- source_result_status: READY

## 목적

PR #88의 X2/X3와 KIS 가격 basis·호출 단위를 공식 1차 자료로만 감사하여, 실제 읽기 전용 수집 전에 데이터 의미를 fail-closed로 잠근다.

이번 TASK는 **문서 의미 감사 한 단계**다. API 호출, 실제 대상 수집, 캐시 생성, 148 재생, 성과 계산은 하지 않는다.

## 고정 입력

- PR #88 head `a5891f5b91d7c206e5afb26049907f426e253c89`의 REPORT, manifest, receipt, code, schema, evidence
- PR #87에서 Claude가 읽은 head `fd37b8b99071a7444abbacaf0255ac2be8aabf6a`
- PR #87 현재 head `24df3f414cf3ee4eb7d4f23bf25ea2bb0dc686ed`; 차이는 delivery acknowledgement용 receipt.json 1개, 8줄
- 현재 고정 분모: 기존 체결 148, off-tick 23, on-tick 미확인 125, 33종목, 77일
- PAPER_VALIDATION_READY=false

입력 SHA가 다르면 BLOCKED한다. 결과 PR 브랜치에는 제출 뒤 receipt 보정 외 연구 결과를 추가하지 않는다.

## 허용 범위

- OpenDART, KRX/KIND 및 한국투자증권 KIS Developers의 **공식 공개 문서** 읽기
- 저장소의 현재 연구 복사본 정적 감사
- 공식 URL, 문서 제목, 조회시각, 필드/값/제약의 짧은 인용 또는 정확한 요약
- 결과 폴더 안 문서·비식별 근거표 작성
- 계산 없는 스키마/수집계획 patch 제안문 작성

검색엔진은 공식 문서 위치 탐색에만 쓸 수 있다. 결론 근거는 공식 도메인의 원문이어야 한다. 블로그·커뮤니티·AI 요약·증권사 비공식 예시는 근거로 쓰지 않는다.

## 해야 할 일

### A. KIS RAW/ADJUSTED 의미 잠금

공식 KIS 문서에서 다음을 각각 근거 URL과 함께 확인한다.

1. 대상 endpoint와 TR ID
2. `FID_ORG_ADJ_PRC`의 허용값 및 각 값이 RAW/수정주가 중 무엇인지
3. 날짜 범위·기간 구분·한 응답 행 수·연속조회/페이지 규칙
4. 응답 날짜·종가 필드와 거래정지/무거래/누락 표현
5. 토큰 호출 및 재시도까지 포함한 33종목 RAW/ADJUSTED 수집 호출식

값 방향 또는 호출 단위를 공식 문서에서 확정하지 못하면 추정하지 말고 `UNKNOWN_KIS_DOC_SEMANTICS` 또는 `NEEDS_DATA`로 둔다.

### B. DART 사건 탐지 경로 잠금

사건별로 공식 경로 표를 만든다.

- 주식 액면분할
- 주식병합
- 감자
- 무상증자
- 유상증자
- 유무상증자
- 합병
- 회사분할
- 회사분할합병

각 행에 다음을 기록한다.

- 구조화 OpenDART endpoint 존재 여부
- 공시목록으로 탐지할 보고서명/필터
- 필요한 경우 공식 공시원문(document) 경로
- 최초/정정공시 연결 필드와 제공 시각 정밀도
- ratio, 기준일/권리락일/효력일/변경상장일/매매정지·재개일 중 공식 제공 필드
- 누락 시 fail-closed reason

**회사분할과 주식 액면분할을 같은 사건으로 취급하지 않는다.** 구조화 endpoint가 없다는 사실도 공식 목록/가이드로 증명한다.

### C. 날짜·수량·매도가능 의미 판정

사건 종류별로 아래 세 시점을 구분한다.

1. 평가 수량과 원주가 기준이 바뀌는 최초 거래일
2. 새 수량이 법적/회계상 발생하는 날
3. 증가분을 실제 매도할 수 있는 최초 거래일

PR #88의 `price_basis_date` 적용 및 `listing_date` 전 잠금 규칙을 사건별로 `ACCEPT / REVISE / BLOCKED_NO_OFFICIAL_EVIDENCE` 판정한다. 권리락일, 기준일, 효력일, 변경상장일을 임의로 서로 대체하지 않는다. 공식 문서만으로 결정할 수 없으면 정확한 결손과 필요한 1차 자료를 적는다.

### D. available_at·정정 버전 판정

- DART 목록/원문이 제공하는 접수일 또는 접수시각의 정밀도를 확인한다.
- 날짜만 제공되면 PR #88의 당일 사용 금지·다음 거래일 사용 규칙을 유지한다.
- 정정공시가 원 접수번호를 직접 제공하는지, 보고서명/접수번호/원문 중 무엇으로 사슬을 구성할 수 있는지 공식 근거로 판정한다.
- 원본-정정 연결을 확정할 수 없으면 `UNKNOWN_CA_VERSION_PIT`을 유지한다.

### E. 동적 호출 예산 계약

API를 호출하지 않고 다음 의사코드를 고정한다.

1. 각 요청 직전 `actual_attempts_used + worst_case(next_request_or_stage) <= cap`
2. DART 1단계 실제 페이지·재시도 횟수를 기록
3. 확인된 사건만 endpoint/document 호출로 매핑
4. 미매핑 kind가 하나라도 있으면 stage 2 전 `BLOCKED_UNMAPPED_KIND`
5. 남은 예산을 실제 사용 횟수로 재계산; `72`를 고정 허용치로 쓰지 않음

기본 성공 호출과 재시도 포함 최악 호출을 분리해 표로 낸다.

### F. 148과 전체 판단 원장의 경계 명시

- 기존 148 체결의 intent mapping 완료
- 전체 판단일 목표 D1 542/BASKET 154의 원주가 재생 미수행
- 원주가 변환으로 추가/소멸 주문이 생길 수 있음
- 따라서 후속 실제 재생 분모는 “기존 148만”으로 고정할 수 없음을 계약에 명시

이번 TASK에서는 전체 intent 파일을 만들거나 재생하지 않는다.

## 산출물

새 `research-exchange/claude-to-gpt/REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001/` 아래:

- `PREREG.md`
- `REPORT.md`
- `manifest.json`
- `receipt.json`
- `evidence/official-source-matrix.json`
- `evidence/kis-basis-contract.json`
- `evidence/dart-event-source-map.json`
- `evidence/date-semantics-verdict.json`
- `evidence/dynamic-call-budget-contract.json`
- `evidence/run.log`

각 근거 행에는 공식 URL, 문서 제목, retrieved_at_kst, 확인한 주장, 필드명, 판정을 포함한다. URL 접근 실패도 숨기지 않는다.

## 금지

- KIS/DART/KRX 데이터 API 호출, 인증 토큰 발급, 실제 자료 수집, 캐시 생성
- 키·Secrets·환경변수 요구 또는 값/길이/일부 문자 확인
- 실제 Train 148/전체 판단 원장 재생, NAV·수익률·MDD·TWR·영향금액 계산
- 새 alpha·EMA·수급·공시 조건·threshold 탐색
- Validation/OOS 사용
- 주문·잔고·계좌 endpoint, 실계좌·모의 주문
- 운영 코드·운영 봇·전략·배분·워크플로·인증 변경
- 15분봉 확대, 자동병합
- 원시 종목·날짜·수량·가격·API 응답·비공개 세션 주소 공개
- 비공식 2차 자료로 공식 의미를 보완하거나 추정

## 완료 조건

### READY

- A~F가 공식 1차 자료와 필드 단위 근거로 모두 판정됨
- KIS basis 값 방향과 호출/페이지 단위가 공식 문서로 확정됨
- 사건별 DART 탐지 경로와 주식분할/회사분할 구분이 확정됨
- 날짜 의미가 사건별 ACCEPT/REVISE/BLOCKED로 분리됨
- unresolved 항목은 UNKNOWN/NEEDS_DATA로 남고 추정값이 없음
- 외부 데이터 API 호출 0, 자격 요구 0, 재생 0, 성과 계산 0

### BLOCKED

- 필수 공식 문서에 접근할 수 없음
- KIS flag 또는 DART/날짜 의미를 공식 공개 자료만으로 확정할 수 없음
- 정정 사슬 또는 available_at 정밀도가 PIT 계약을 충족하지 못함

BLOCKED여도 공식 확인이 끝난 행과 정확한 결손을 모두 제출한다. 같은 API 호출을 시도하지 않는다.

## 다음 단계 금지

READY여도 실제 DART stage 1, KIS 수집, Train 재생, 성과 판정은 자동으로 실행하지 않는다. 결과를 GPT가 검토한 뒤에만 한 단계씩 진행한다.
