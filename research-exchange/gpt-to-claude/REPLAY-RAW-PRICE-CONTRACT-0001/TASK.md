# TASK — REPLAY-RAW-PRICE-CONTRACT-0001

## 식별자

- task_id: `REPLAY-RAW-PRICE-CONTRACT-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 21
- status: READY
- source_pr: 84
- source_head_sha: `5dc08c38e6403e6df806a5cd1fe26b9631eb5c68`
- stage: REPLAY
- Train 고정: 2025-09-18 ~ 2026-03-31
- 현재 후보: PR #78/76 계열의 시점 수정 후보(+19.90%는 인용값이며 검증값 아님)

## 목적

PR #84가 확인한 가격 basis 결함을 고칠 수 있도록, **현재 수정 후보의 일봉 D1+BASKET 체결 148건**을 공식 원주가·기업행동으로 재생하는 데이터 계약과 회계 어댑터를 연구 복사본으로 만든다.

이번 TASK는 준비 단계다. 외부 API 호출, 실제 수집, 실제 Train 재생, NAV·수익률 계산을 하지 않는다.

우선순위는 `IMPOSSIBLE_RAW_FILL` 23건이지만, on-tick 125건도 원주가/수정주가가 UNKNOWN이므로 대상 계약에는 148건 전부를 포함한다.

## 사전등록

코드·fixture 실행 전에 별도 첫 커밋으로 아래를 고정한다.

1. 입력 파일과 sha256
2. 현재 후보 148체결의 재구성 규칙
3. 고유 (종목, 날짜), 방향, sleeve, fill 수의 분모
4. 공개 salted hash 목록과 로컬 전용 실제 대상 파일 경계
5. 공식 원주가·수정주가·기업행동 데이터 스키마
6. 수량·현금·비용·일별 MTM 재생 불변식
7. 합성 fixture 케이스와 기대 판정
8. READY/BLOCKED 조건과 다음 실제 실행의 결손 자격

## 고정 입력

현재 세션에 이미 있는 다음 로컬 사본만 읽는다.

- PR #76 `fixed_local_only.json`
- PR #76 저장 NAV CSV
- PR #82의 대상·가격 스냅샷
- PR #84 REPORT, manifest, `fill-validity.json`, `position-accounting.json`
- PR #84가 고정한 `kernel2.py`, `cost_contract.py`
- 옛 가격 캐시와 Train 거래일 달력

입력 해시가 PR #84 manifest와 다르면 BLOCKED다. 네트워크나 다른 기간으로 대체하지 않는다.

## A. 대상 계약

현재 수정 후보만 사용한다. 통제 원장은 실제 재생 대상에서 제외하고 비교 메타데이터로만 둔다.

반드시 재현할 분모:

- D1 매수 52, 매도 71
- BASKET 매수 12, 매도 13
- 합계 148체결
- 그중 off-tick 23, on-tick UNKNOWN 125

다음을 출력한다.

- 고유 (종목, 날짜) 수
- 방향·sleeve별 체결 수
- off-tick/on-tick 수
- 공개 salted hash 대상 목록
- 실제 코드·날짜·원가격은 로컬 전용 파일에만 두고 커밋하지 않는다.
- salt 값도 커밋하지 않고 sha256만 기록한다.

15분봉 sleeve는 이번 대상 밖이다. 전체 포트폴리오 결론으로 확대하지 않는다.

## B. 공식 데이터 스키마

실제 호출은 하지 않지만, 나중 실행기가 받아야 할 필드를 기계 판독 가능한 JSON Schema로 고정한다.

### KIS 일봉

- endpoint/TR ID
- 요청한 종목·시작일·종료일
- `FID_ORG_ADJ_PRC=1` 원주가와 `0` 수정주가를 같은 날짜에 각각 받은 구분
- 영업일, 시가·고가·저가·종가, 수정 여부 관련 응답 필드가 있으면 이름
- API 응답의 조회시각, 요청 파라미터 해시, 캐시 파일 sha256
- 같은 요청 결과가 원/수정 선택에 따라 실제로 달라졌는지
- 누락·미지원·동일 응답을 UNKNOWN으로 분리

### OpenDART 기업행동

- 접수번호, 접수일, 보고서명
- 정정 여부와 원 접수 연결
- 효력일·기준일·배정/감자/분할/합병 비율
- 날짜만 있고 시각이 없으면 같은 날 PIT로 승격하지 않는 표시
- 원문·원시 응답은 공개 산출물에 넣지 않고 로컬 캐시 sha256·비식별 파생 필드만 공개

KIS/DART 자격 이름만 기록한다. 값·길이·일부 문자열·secret 목록은 읽거나 출력하지 않는다.

## C. 원주가 재생 어댑터

연구 결과 폴더 안의 독립 모듈로 구현한다. 운영 import 경로를 수정하지 않는다.

입력:

- 고정 148체결
- 공식 원주가 일봉
- 공식 기업행동 효력일·비율
- 기존 비용 계약
- 초기 현금과 기존 sleeve 배분

출력 계약:

- 체결가: 해당 날 공식 원주가 종가이며 호가단위 배수
- 매수 수량: 해당 시점 현금·raw notional·비용으로 산정
- 매도 수량: 보유 lot과 기업행동 조정 뒤 수량을 초과하지 않음
- 비용·세금: raw 가격 × raw 수량 notional
- 일별 MTM: raw 종가 × 실제 수량
- 기업행동: 공식 효력일에 명시적 수량/현금 조정 레코드
- 현금·수량 보존식과 음수 수량 금지
- 공식 필드가 없으면 추정·반올림으로 채우지 않고 UNKNOWN

이번 TASK에서는 실제 Train 입력으로 이 어댑터를 실행하지 않는다.

## D. 합성 fixture 검증

외부 데이터가 아닌 작은 합성 fixture만 사용한다.

최소 케이스:

1. 기업행동 없음: 원주가=수정주가
2. 액면분할: 과거 수정주가가 off-tick, 효력일에 수량 증가
3. 주식병합/감자: 효력일에 수량 감소, 현금 잔여 처리 필드
4. 유상·무상증자: 비율·기준일·효력일 중 하나가 없으면 UNKNOWN
5. 원/수정 API 선택이 같은 응답을 반환하면 UNKNOWN_SELECTION_UNSUPPORTED
6. 원주가가 호가단위 밖이면 INVALID_OFFICIAL_RAW
7. 정정공시가 있으면 최신 정정본과 원 접수 연결을 보존
8. 비용·세금 raw notional과 현금 항등식
9. 주문 가능 수량 초과·음수 수량 차단
10. 15분봉 입력이 들어오면 이번 범위 밖으로 거부

두 개의 독립 경로 또는 직접 계산식으로 수량·현금 항등식을 교차검산한다.

## 금지

- KIS·DART·KRX 또는 다른 외부 API/네트워크 호출
- GitHub Secrets 열람, Actions 실행·수정, workflow/auth 변경
- 실제 Train 백테스트·성과·NAV·MDD·TWR 재실행
- 수정 수익률·영향 금액 산출
- threshold, EMA, 수급 조합, 진입·청산 규칙, sizing, sleeve 배분 변경
- 새 알파, OOS, Validation, Shadow 실행 또는 기간 재명명
- 모의·실계좌 주문·잔고·주문가능금액 API
- 운영 코드·봇 재시작·자동병합
- 원가격·종목명·실제 대상표·원시 API/계좌 응답 공개
- on-tick 125건을 원주가로 간주
- off-tick 값을 가까운 호가로 반올림해 공식 원주가처럼 사용

## 출력

경로: `research-exchange/claude-to-gpt/REPLAY-RAW-PRICE-CONTRACT-0001/`

필수 파일:

- `PREREG.md`
- `REPORT.md`
- `manifest.json`
- `receipt.json`
- `schema/raw-price-response.schema.json`
- `schema/corporate-action.schema.json`
- `evidence/target-coverage.json`
- `evidence/data-contract.json`
- `evidence/fixture-test-report.json`
- `evidence/unknown-reasons.json`
- `evidence/run.log`
- 수집기 인터페이스·재생 어댑터·fixture 테스트 코드와 sha256

실제 target map·salt·원가격·원시 응답은 커밋하지 않는다.

## 완료 조건

### READY

- 사전등록 뒤 고정 입력으로 현재 후보 148체결과 23/125 분류를 재현했다.
- 공식 원주가·기업행동 스키마와 공개/로컬 경계를 고정했다.
- 재생 어댑터가 합성 fixture에서 체결·비용·수량·현금·MTM 불변식을 통과했다.
- 실제 외부 호출과 Train 성과 재실행은 0회다.
- 다음 실제 실행에 필요한 자격·환경·예상 호출 상한을 비밀 없이 정확히 적었다.
- +19.90%를 검증 완료 또는 PAPER_VALIDATION_READY로 표현하지 않았다.

### BLOCKED

- PR #84 고정 입력이 없거나 해시가 다름
- 현재 후보 148체결 또는 off-tick 23건을 재현하지 못함
- 필요한 회계 필드가 없어 어댑터 계약을 정의할 수 없음

BLOCKED면 정확한 결손 파일·필드·해시만 적고 범위를 넓히지 않는다.

## 상태

결과 status는 READY 또는 BLOCKED만 허용한다. 후속 실제 수집·REPLAY는 별도 TASK와 별도 브랜치/PR에서만 한다.
