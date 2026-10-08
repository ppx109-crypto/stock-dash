# TASK — REPLAY-CA-LEDGER-ATOMICITY-CONTRACT-0001

- task_id: REPLAY-CA-LEDGER-ATOMICITY-CONTRACT-0001
- chain_id: PAPER-READINESS-20261008
- round: 30
- status: READY
- source_pr: 102
- source_head_sha: b940b28347c10bc4ca13b995dd49daca505dc5e7

## 목적

분할·병합 비율 계약을 합성 일별 원장에 정확히 한 번 적용하는 회계 원자성·멱등성 계약을 고정한다. 순수 기업행동만으로 수익·손실·낙폭이 생기지 않아야 한다.

## 허용 범위

- PR #102의 코드·REPORT·manifest·evidence와 저장소의 기존 연구 복사본 읽기
- 오프라인 합성 fixture와 독립 검산 코드 작성·1회 실행
- 현금, 수량, 가격, 평가액, 일별 MTM, 일별 TWR, 달력월 TWR, MDD의 합성 전후 검산
- 동일 event_key 중복 적용, 순서 뒤바뀜, 비율 불일치, 단주, 적용일 누락을 fail-closed로 검사
- 기존 코드에서 기업행동이 이중 적용될 수 있는 경로를 읽기 전용으로 좁게 검색

## 금지

- 외부 URL/API/키/수집/캐시/원시 공시/실제 종목·계좌자료 열람
- 실제 8개 후보 적용, 리플레이, 백테스트, 성과·NAV 재계산
- price_basis_date·거래재개일·최초 매도가능일 추정
- 허용오차·단주 현금보상·새 threshold 설계
- KOSDAQ 규칙, 제2256호 결속 재시도
- 운영 코드·현재 모의 봇·전략·배분·워크플로·인증 변경
- 주문 API, 실계좌·모의 주문, 자동병합
- +19.90% 또는 PAPER_VALIDATION_READY 판정

## 필수 계약

1. 합성 event에는 `event_key`, 명시적 `apply_date`, `m_qty`, `m_price`가 있다.
2. `m_qty*m_price=1`을 정확한 유리수로 검증한다.
3. 한 event_key는 한 번만 적용한다. 두 번째 적용은 `BLOCKED_DUPLICATE_EVENT`이며 상태를 바꾸지 않는다.
4. 적용은 수량과 기준가격을 하나의 트랜잭션처럼 함께 바꾼다. 중간 상태를 일별 MTM에 노출하지 않는다.
5. 현금은 단주·비용·현금보상이 없는 합성 ACCEPT 사례에서 불변이다.
6. 무시장변동 fixture에서는 전후 평가액, 일별 TWR, 달력월 TWR, MDD 변화가 모두 정확히 0이다.
7. 적용일 누락/불일치, 단주, 비율 모순, 음수·0·비유한 값, 순서 역전은 fail-closed이며 NAV/TWR 산출에 들어가지 않는다.
8. 실제 적용일 미확정 상태는 계속 `APPLY_BLOCKED_NO_PRICE_BASIS_DATE`다.

## 완료 조건

- 계산·검색 전 PREREG 커밋을 별도로 남긴다.
- split 2건, reverse_split 2건, 실패·중복·원자성 사례를 포함한 합성 표를 공개한다.
- 적용 전/후 `cash + qty*price`, 일별 MTM, 일별/월 TWR, MDD를 정확식으로 제시한다.
- 같은 event_key를 두 번 처리한 뒤 첫 적용 상태와 완전히 동일함을 증명한다.
- 부분 업데이트를 의도적으로 주입한 음성대조군이 NAV/TWR 왜곡을 탐지함을 보인다.
- 코드 검색 범위·검색식·분류 근거와 놓칠 수 있는 표현을 적는다.
- REPORT, manifest.json, receipt.json, 실행 코드, evidence JSON, run.log를 제출한다.
- 최종 status는 READY 또는 BLOCKED만 사용한다.
- READY여도 실제 사건 0, 성과/NAV 미검증, PAPER_VALIDATION_READY=false를 유지한다.
