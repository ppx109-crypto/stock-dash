# REPLAY-CA-QUOTE-BASIS-GATE-0001

- task_id: REPLAY-CA-QUOTE-BASIS-GATE-0001
- chain_id: PAPER-READINESS
- round: 38
- status: READY
- source_pr: 118
- source_head_sha: c8826304387ae99f92adf09bedc0b1997618d703

## 목적

PR #118이 남긴 단일 결손인 장부·시세 공급 가격기준 불일치만 다룹니다. 합성 연구 복사본의 하루 처리 시작점에 시세 배치 fail-closed 경계를 추가하여, 수정주가가 RAW 장부를 덮기 전에 그 날의 사건·시세·스냅숏 처리를 전부 중단합니다.

실제 Train 가격기준 선택, 실제 시세 라벨 생산, 실제 사건 변환기, 성과 재생은 이번 단계가 아닙니다.

## 고정 계약

1. 합성 장부의 `ledger_price_basis`는 `RAW_UNADJUSTED`로 고정합니다.
2. `process_day`는 시세를 `[{sym, price, price_basis}, ...]` 형태의 배치로 받습니다.
3. 비어 있지 않은 시세 배치의 모든 항목이 정확히 `RAW_UNADJUSTED`일 때만 그 날의 사건 적용과 시세 덮기, snapshot 생성을 허용합니다.
4. 항목 하나라도 `ADJUSTED`, 누락, 빈 값, 그 밖의 값이면 `BLOCKED_QUOTE_PRICE_BASIS`로 **하루 전체를 첫 문장에서 중단**합니다.
5. 하루 차단은 `apply_batch`보다 먼저 일어나야 하며 event ledger, positions, cash, quantity, price, applied/provenance, snapshot, NAV 파생값을 바꾸지 않습니다. fail-closed 감사 표시는 별도 필드 하나만 허용하고 비교에서 명시합니다.
6. 라벨 대소문자·공백을 고치거나 사건 라벨·가격값·KIS 인자에서 추론하지 않습니다.
7. 빈 시세 배치는 이번 fixture에 넣지 않습니다. 이에 대한 정책을 새로 만들지 않습니다.
8. 실제 시세가 수정주가인데 RAW로 잘못 라벨되면 이 게이트도 막지 못합니다. 이를 `NEEDS_DATA`로 유지합니다.

## 허용 범위

- PR #118 합성 코드를 별도 결과 폴더에 최소 복사
- 하루 시작 시세 배치 게이트와 결정적 합성 fixture/test 추가
- 아래 고정 케이스만 공식 1회 실행
- 정적 코드 순서 근거, JSON·표·실행 로그 작성
- 기존 고정 증거 읽기와 해시 확인

## 금지 범위

- 외부 API·신규 수집·인증·Secrets·원본 계좌 응답
- 실제 사건·실제 시세·실제 포지션·실제 NAV
- 운영/모의 봇·전략·배분·워크플로·인증 또는 기존 파일 변경
- 백테스트·성과·threshold/alpha 탐색·파라미터 조정
- 실제 KIS `FID_ORG_ADJ_PRC` 값을 바꾸거나 호출해 의미를 추정
- 주문·자동병합·Validation/OOS 재명명

## 고정 합성 케이스

- Q1 RAW 정상: D0 q=37, p=52,300. D1 RAW split(`m_qty=5`, `m_price=1/5`)과 RAW quote 10,460. q=185, p=10,460, NAV 1,935,100 불변.
- Q2 음성대조: PR #118 사건 게이트만 사용하고 사건은 RAW로 라벨, 시세는 ADJUSTED 10,460. 시작 q=37, adjusted p=10,460에서 D1 NAV가 387,020→1,935,100으로 5배 변하는 것을 재현.
- Q3 새 게이트: Q2와 같은 입력에서 시세 항목을 ADJUSTED로 명시. 사건 적용 전 `BLOCKED_QUOTE_PRICE_BASIS`, 하루 전체 mutation 0, snapshot 0, NAV 파생 출력 0.
- Q4 UNKNOWN: 시세 항목의 `price_basis` 누락·빈 값·`raw_unadjusted` 각각 하루 전체 차단.
- Q5 혼합 시세: A RAW quote와 B ADJUSTED quote를 두 입력 순서로 실행. 두 순서 모두 전체 차단, 어느 종목도 가격 변경 없음.
- Q6 원자성: 유효 RAW 사건과 잘못된 시세가 같은 날 있으면 사건도 미적용, applied/provenance 변화 0.
- Q7 RAW 회귀: PR #118의 P1 및 PR #114 고정 fixture 11개를 모든 시세 RAW 라벨로 실행하고 기존 증거와 다른 칸 0.
- Q8 결정성: 입력 순서·reload·반복·직렬화 바이트·prefix cut 결과가 동일.

## 완료조건

다음을 모두 만족하면 READY, 하나라도 빠지면 BLOCKED입니다.

- 시세 기준 검사가 `apply_batch`, quote mutation, snapshot/NAV보다 먼저라는 AST와 실행 근거
- Q1~Q8 고정 기대값 일치
- 모든 차단 케이스에서 event ledger/positions/cash/quantity/price/applied/provenance/snapshot 전후 해시 동일
- Q2 음성대조와 Q3 차단 결과를 같은 증거에 기록
- 공식 실행 1회·상한 1, actual_events=0, external_calls=0
- REPORT·manifest·receipt·evidence를 PR 개설 전에 완성
- status는 READY 또는 BLOCKED만 사용
- `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false` 명시

## 산출물

`research-exchange/claude-to-gpt/REPLAY-CA-QUOTE-BASIS-GATE-0001/` 아래:

- PREREG.md
- REPORT.md
- manifest.json
- receipt.json
- code/quote_basis_gate.py
- evidence/quote-basis-gate.json
- evidence/tables.md
- evidence/run.log

결과 브랜치는 제출 후 불변으로 유지합니다. 후속 연구는 별도 브랜치/PR에서 수행합니다.
