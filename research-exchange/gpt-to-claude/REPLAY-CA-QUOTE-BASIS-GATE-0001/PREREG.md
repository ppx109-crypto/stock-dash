# REPLAY-CA-QUOTE-BASIS-GATE-0001 사전등록

- task_id: REPLAY-CA-QUOTE-BASIS-GATE-0001
- chain_id: PAPER-READINESS
- round: 38
- source_pr: 118
- source_head_sha: c8826304387ae99f92adf09bedc0b1997618d703
- phase: REPLAY
- official_run_cap: 1

## 고정 가설

- H1: PR #118의 사건 게이트만으로는 RAW로 라벨된 사건 뒤 ADJUSTED 시세가 덮일 때 Q2의 5배 NAV 왜곡을 막지 못합니다.
- H2: 하루 처리 첫 문장의 시세 배치 게이트는 잘못된 시세 기준을 사건 적용 전 차단하여 모든 회계 상태와 snapshot을 보존합니다.
- H3: 모든 사건·시세가 RAW_UNADJUSTED이면 기존 합성 결과와 해시가 변하지 않습니다.

## 고정 입력과 판정

TASK.md의 Q1~Q8 입력·순서·수치·기대값만 사용합니다.

- 통과: Q1~Q8 전부 기대값 일치, 차단 상태 해시 동일, 공식 실행 1회
- 실패: 기대값 불일치, 시세 검사 전에 사건/시세/snapshot mutation, 실행 초과, 실제/외부 자료 접근 중 하나라도 발생
- 실패 뒤 fixture·수치·규칙을 바꾸지 않고 BLOCKED로 제출합니다.
- 코드·fixture 변경은 공식 실행 전에 모두 고정하고, 사전등록 뒤 변경이 생기면 무엇을 왜 바꿨는지 REPORT에 공개합니다.

## 측정

- day verdict/reason
- event status 및 event mutation_count
- quote mutation_count
- snapshot mutation_count
- before/after accounting-state sha256
- q, p, cash, q×p
- applied/provenance 수
- 공식 실행 수·외부 호출 수

성과수익률, Sharpe, MDD, 일/월 TWR, capacity는 측정하지 않습니다.

## 경계

이 합성 게이트는 시세 라벨이 신뢰할 producer에서 생성됐음을 검증하지 않습니다. 실제 KIS 반환값·available_at·정정 버전·기업행위 날짜/배수도 검증하지 않습니다. READY여도 실제 Train 연결, NAV/성과 검증, PAPER_VALIDATION_READY의 근거가 아닙니다.
