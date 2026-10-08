# REPLAY-CA-LEDGER-ATOMICITY-CONTRACT-0001 — 클로드 사전등록(계산 · 코드 검색 · 판정 전)

- 지시: GPT PR #103 head `751eadf9`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `22f42e0d660b78f6`
  - SOURCE_PACKET `38c7d90147b09b64`
  - PREREG `815ff96c0914cde6`
  - REVIEW `dad0ded1edece853`
  - receipt `5a651077023035ee`
- 입력 PR #102: 시작 직전(02:12 KST) 확인 결과 열림 · 초안 아님 · head `b940b28347c10bc4ca13b995dd49daca505dc5e7` 일치. 제출 직전에 다시 확인합니다.
- **오프라인 · 합성만**: 외부 URL · API · 키 · 수집 · 캐시 · 원시 공시 · 실제 종목/계좌 0. 실제 8건 적용 0. 리플레이 · 백테스트 · 성과/NAV 주장 0
- 실행은 1회입니다. 고치면 1회차를 남기고 이유를 적습니다.

## 합성 원장(정확 유리수 `Fraction`)
- **상태:** 현금, 보유 `{종목: (수량, 표시가격)}`, 적용된 event_key 집합, 날짜 snapshot 목록
- **하루 처리 순서**
  1. 그날 사건을 모두 검증합니다(모두 통과해야 적용).
  2. 통과한 사건을 **새 상태 복사본**에 수량 · 표시가격을 함께 적용한 뒤 한 번에 바꿔 끼웁니다(커밋).
  3. 그날 시세가 있으면 표시가격을 그 시세로 갱신합니다.
  4. snapshot NAV = 현금 + Σ 수량 × 표시가격
- 중간 상태(수량만 바뀐 상태)는 snapshot에 나타날 수 없게 합니다.
- **event:** `event_key`, 명시적 `apply_date`(합성 날짜 · 실제 시장 날짜 아님), `m_qty`, `m_price`
  - `event_key` = (종목, 사건 종류, m_qty, apply_date). 출처 접수번호는 키에 넣지 않습니다.
  - 같은 사건이 다른 접수번호로 두 번 들어와도 하나로 봅니다.
- **검증(실패 시 상태 변경 0 · 그 종목이 든 날부터 NAV 무효 · TWR/MDD 계산에서 제외)**
  - `BLOCKED_DUPLICATE_EVENT`(같은 event_key 두 번째)
  - `BLOCKED_APPLY_DATE_MISSING`
  - `BLOCKED_APPLY_DATE_MISMATCH`(처리 날짜 ≠ apply_date)
  - `BLOCKED_ORDER`(apply_date가 마지막 snapshot 날짜 이전 = 순서 역전)
  - `BLOCKED_RATIO_PRODUCT`(m_qty × m_price ≠ 1)
  - `BLOCKED_FRACTIONAL`(적용 결과 단주)
  - `BLOCKED_INPUT`(0 · 음수 · 누락 · 비유한 · 부동소수)
  - `APPLY_BLOCKED_NO_PRICE_BASIS_DATE`(실제 사건 표시가 붙은 event)
- **지표**
  - `r_t = NAV_t/NAV_{t-1} − 1`(외부 현금흐름 0)
  - 달력월 TWR = 그 달 일별 (1 + r)의 곱 − 1
  - MDD = 일별 NAV의 고점 대비 최대 하락률
  - NAV 무효일이 하나라도 있으면 TWR/MDD는 `PERF_BLOCKED`입니다.

## 정상 fixture 4건(PR #102 합성 사례 재사용)
- 분할 1:5 · 1:10, 병합 10:1 · 5:1
- 현금 1,000,000, 비용 · 단주 · 현금보상 0
- 날짜는 달을 넘도록 합성 2026-01-28 ~ 2026-02-03(실제 시장 날짜 아님)입니다.
- 사건 당일은 **시세 없음(거래정지 가정)**, 다음 날부터 새 기준 시세(= 앞 시세 × m_price)를 둡니다. 경제적 가격 변화는 0입니다.
- 기대값: 모든 날 r_t = 0, 1월 · 2월 TWR = 0, MDD = 0, 현금 불변, 사건 전후 NAV가 정확히 같음

## 음성대조군(보정하지 않고 탐지만)
1. **부분 업데이트:** 사건 당일 수량만 바꾸고 표시가격은 다음 snapshot에서 바꿉니다. → 당일 NAV 왜곡 · r_t ≠ 0 · MDD > 0을 크기와 함께 보고합니다.
2. **반대 방향:** 표시가격에 m_qty를 곱합니다. → 왜곡 배수(1:5면 25)를 보고합니다.
3. 같은 event_key 두 번, 그리고 다른 출처 번호로 같은 사건 → 두 번째는 `BLOCKED_DUPLICATE_EVENT`이고, 상태 해시가 첫 적용 직후와 같아야 합니다.
4. apply_date 누락 · 불일치 · 순서 역전, m_qty × m_price ≠ 1, 단주, 0 · 음수 · 누락 · NaN · 부동소수 → 차단 · 상태 불변 · `PERF_BLOCKED`

## 코드 경로 감사(읽기 전용 · 좁게)
- 범위: PR #86 `raw_replay.py`, PR #88 `raw_replay_v2.py`, origin/main의 원장 · 모의 장부 코드(`kernel*`, `paper*`, `*ledger*`, `*account*` 파일)
- 검색식: `ratio` · `CA_QTY` · `applied` · `분할` · `split` 계열
- 분류: 같은 사건이 두 번 적용될 수 있는 경로가 있는지, 키가 무엇인지
- 정규식으로 놓칠 수 있는 표현(간접 호출 · 동적 키 등)도 적습니다. 코드는 고치지 않습니다.

## 상태
- 정상 4건이 보존 · TWR 0 · 월 TWR 0 · MDD 0을 만족하고, 중복 멱등, 음성대조군 전부 탐지, 실제 적용 0이면 READY입니다.
- 하나라도 실패하면 BLOCKED이고, 실패 fixture와 NEEDS_DATA를 적습니다.
- READY여도 실제 사건 0 · 성과/NAV 미검증 · PAPER_VALIDATION_READY=false입니다.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/ledger_atomicity.py`
- `evidence/ledger-atomicity.json` · `evidence/code-path-audit.json` · `evidence/run.log`
