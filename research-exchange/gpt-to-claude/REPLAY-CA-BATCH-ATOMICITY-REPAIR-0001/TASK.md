# TASK — REPLAY-CA-BATCH-ATOMICITY-REPAIR-0001

- task_id: REPLAY-CA-BATCH-ATOMICITY-REPAIR-0001
- chain_id: PAPER-READINESS-20261008
- round: 31
- status: READY
- source_pr: 104
- source_head_sha: ad13f07772edbff446adba56edb7d645c1b8dccd

## 목적

PR #104 합성 원장의 다중사건 하루 배치를 all-or-nothing으로 복구한다. 한 고유 사건이라도 실패하면 그날의 어떤 신규 사건도 수량·가격·현금·적용집합에 반영되지 않아야 한다.

## 허용 범위

- PR #104의 PREREG, REPORT, 코드, manifest, receipt, 전체 evidence 읽기
- PR #104 코드를 별도 연구 복사본으로 가져와 최소 수정
- 오프라인 합성 fixture 작성과 최대 2회 실행
- 배치 검증·중복 정규화·상태 해시·순열 불변성 검산
- 수정 전 결함을 음성대조군으로 재현하고 수정 후 회귀 시험

## 금지

- 외부 URL/API/키/수집/캐시, 실제 종목·공시·계좌자료
- 실제 8개 기업행동 적용, 실제 날짜 추정, 리플레이·백테스트
- 허용오차·단주 보상·새 threshold
- 운영 코드·현재 모의 봇·전략·배분·워크플로·인증 변경
- 실계좌/API/모의 주문, 자동병합
- +19.90%, NAV, PAPER_VALIDATION_READY 판정

## 필수 계약

1. 입력 배치를 먼저 의미키로 정규화한다. 같은 의미키 반복은 `DUPLICATE_IGNORED`로 기록하되 실패 사건으로 보지 않는다.
2. 모든 **고유 신규 사건**을 커밋 전 상태에서 먼저 검증한다.
3. 한 고유 사건이라도 실패하면 배치 전체를 `BATCH_ABORTED`로 만들고 현금·모든 종목 수량/가격·적용집합을 완전히 보존한다.
4. 전부 통과한 경우에만 별도 scratch 상태에 모든 사건을 적용하고 한 번에 커밋한다.
5. 배치 내 사건 순서를 바꿔도 최종 상태 해시와 판정이 같아야 한다.
6. 중복만 섞인 정상 배치는 고유 사건을 정확히 한 번 적용하며 TWR/MDD를 무효화하지 않는다.
7. 실패 배치는 해당 일부터 `PERF_BLOCKED`지만, 실패 전에 나열된 정상 사건이 몰래 반영되어서는 안 된다.
8. 수량·가격은 각 사건별로 함께 적용하며 중간 snapshot은 없다.
9. 실제 적용일 미확정은 계속 `APPLY_BLOCKED_NO_PRICE_BASIS_DATE`다.

## 필수 fixture

- 서로 다른 합성 종목 A 정상 + B 비율곱 오류
- A 정상 + B 단주
- A 정상 + 존재하지 않는 종목 B
- 정상 A/B 두 사건
- 정상 A + 같은 의미키 A 중복
- 입력 순서를 뒤집은 각 배치
- 같은 종목에 서로 다른 두 사건이 같은 날 들어오는 충돌 사례: 자동 합성하지 말고 fail-closed
- 수정 전 PR #104 로직에서 부분 커밋이 발생함을 보이는 음성대조군

## 완료 조건

- 계산 전 PREREG 커밋
- 수정 전 결함을 상태 해시·수량·가격으로 재현
- 실패 배치 전/후 전체 상태 해시 동일
- 성공 배치에서 모든 사건이 한 번만 반영되고 가치 보존
- 모든 fixture의 순열 불변성 통과
- 정상+중복 배치가 정확히 한 번 적용되고 성과 무효화 없음
- REPORT, manifest.json, receipt.json, 실행 코드, evidence JSON, run.log
- 최종 status READY/BLOCKED
- READY여도 실제 적용 0, 성과/NAV 미검증, PAPER_VALIDATION_READY=false 유지
