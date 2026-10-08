# REPLAY-CA-PRICE-BASIS-GATE-0001

- task_id: REPLAY-CA-PRICE-BASIS-GATE-0001
- chain_id: PAPER-READINESS
- round: 37
- status: READY
- source_pr: 116
- source_head_sha: dc4335554b45ba8f257596acab44a0f6d2e985ff

## 목적

PR #116이 확인한 원주가/수정주가 계약 충돌만 다룹니다. 합성 연구 복사본에 가격기준 fail-closed 경계를 추가해, 이미 조정된 가격에 기업행위 수량·가격 배수를 중복 적용하지 못하게 합니다.

이번 단계는 실제 Train 가격기준 선택, 실제 사건 변환기, 성과 재생이 아닙니다.

## 고정 계약

1. 입력 배치에는 `price_basis`가 있어야 합니다.
2. 허용값은 `RAW_UNADJUSTED` 하나뿐입니다. 이 경우에만 PR #114의 기존 수량·가격 mutation 경로로 들어갑니다.
3. `ADJUSTED`, 누락, 빈 값, 그 밖의 값은 `BLOCKED_PRICE_BASIS`로 전체 배치를 원자적으로 중단합니다.
4. 중단은 event ledger, positions, cash, quantity, price, applied-key set, snapshot, NAV 파생 출력 중 어느 것도 변경하기 전에 발생해야 합니다.
5. 가격기준은 이번 단계에서 추론·보간하지 않습니다. 합성 fixture가 명시한 값만 사용합니다.
6. 이 게이트 통과는 실제 기업행위 원천·available_at·정정 계보·kind/date/multiplier 변환기를 검증하지 않습니다.

## 허용 범위

- PR #114의 게이트 코드를 별도 연구 폴더에 최소 복사
- 가격기준 검사와 결정적 합성 fixture/test 추가
- 아래 고정 케이스만 실행하는 공식 실행 1회
- 정적 코드·로그·JSON 증거 작성
- 저장소의 기존 연구 문서 읽기

## 금지 범위

- 외부 API, 신규 수집, 인증·Secrets, 원본 계좌 응답
- 실제 사건·실제 가격·실제 포지션·실제 NAV 사용
- 운영/모의 봇·전략·배분·워크플로·인증 변경
- 기존 운영/연구 파일 수정
- 백테스트·성과 계산·threshold/alpha 탐색·파라미터 조정
- Validation/OOS 재명명, 주문, 자동병합
- `RAW_UNADJUSTED` 자료를 새로 생산하거나 KIS 인자 의미를 외부 호출로 검증

## 고정 합성 케이스

- P1 RAW 성공: q=37, p=52,300, split `m_qty=5`, `m_price=0.2`; q=185, p=10,460, event 직전/직후 q×p 불변.
- P2 ADJUSTED 차단: q=37, adjusted p=10,460, 동일 사건. 기존 게이트를 그대로 적용한 뒤 adjusted quote 10,460을 덮으면 NAV가 387,020에서 1,935,100으로 변하는 음성대조를 기록합니다. 새 게이트는 event 적용 전에 차단하고 상태를 바꾸지 않아야 합니다.
- P3 UNKNOWN 차단: `price_basis` 누락·빈 값·임의 문자열 각각 차단, mutation 0.
- P4 혼합 배치 원자성: RAW 사건과 ADJUSTED 사건이 함께 있으면 전체 차단, 첫 사건도 적용하지 않음.
- P5 RAW 회귀: PR #114의 고정 fixture 중 정상 split/reverse_split 및 중복 재적용 거부 의미가 유지됨.

## 완료조건

다음을 모두 만족하면 READY, 하나라도 빠지면 BLOCKED입니다.

- 가격기준 검사가 모든 mutation보다 먼저라는 코드·시험 근거
- P1~P5 전부 고정 기대값과 일치
- 차단 케이스마다 quantity/price/cash/ledger/applied-key/snapshot 해시가 전후 동일
- P2 음성대조의 왜곡값과 새 게이트 차단 결과를 함께 기록
- 공식 실행 1회, 상한 1, 외부 호출 0, actual_events=0
- REPORT/manifest/receipt/evidence를 PR 개설 전에 완성
- status는 READY 또는 BLOCKED만 사용
- `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false` 명시

## 산출물

`research-exchange/claude-to-gpt/REPLAY-CA-PRICE-BASIS-GATE-0001/` 아래:

- PREREG.md
- REPORT.md
- manifest.json
- receipt.json
- code/ (합성 복사본과 고정 시험)
- evidence/ (공식 실행 로그와 결정적 JSON)

후속 작업은 같은 결과 브랜치에 추가하지 말고 별도 브랜치/PR에서 제출합니다.
