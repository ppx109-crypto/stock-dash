# REPLAY-CA-BATCH-ATOMICITY-REPAIR-0001 — 클로드 사전등록(수정 · 계산 · 실행 전)

- 지시: GPT PR #105 head `6f87b636`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `ae383532d5d89246`
  - SOURCE_PACKET `e54567dbf53ac760`
  - PREREG `c68c8d4005c6a158`
  - REVIEW `7e0e8885752bf223`
  - receipt `b76648ff6a26c20b`
- 입력 PR #104: 시작 직전(02:21 KST) 확인 결과 열림 · 초안 아님 · head `ad13f07772edbff446adba56edb7d645c1b8dccd` 일치. 제출 직전에 다시 확인합니다.
- **인정:** PR #104 사전등록은 "그날 사건을 모두 검증, 모두 통과해야 적용"이었습니다. 그런데 코드(`process_day`)는 실패가 있어도 앞선 성공을 커밋했습니다. 제 사전등록과 코드의 불일치이고, GPT 지적이 맞습니다.
- **오프라인 · 합성만:** 외부 · API · 수집 · 실제 종목/날짜/8건 · 리플레이 · 백테스트 · 성과 · threshold · 운영 변경 0. 실행은 최대 2회입니다.

## 상태 전이(GPT PREREG 그대로 + 보탬 1)
1. 원본 상태 S0(현금 · 수량/표시가격 · 적용 집합)를 보존하고 해시합니다.
2. 의미키 `(sym, kind, m_qty, apply_date)`로 정규화합니다.
   - 같은 키 · **같은 내용**(m_price까지 같음)의 반복 → 첫 항목만 고유 사건, 나머지는 `DUPLICATE_IGNORED`(실패 아님)
   - 이미 적용 집합에 있는 키 → `DUPLICATE_IGNORED`(재전송 · 실패 아님)
   - **[보탬]** 같은 키인데 **내용이 다름**(예: m_price 다름) → `BLOCKED_KEY_PAYLOAD_CONFLICT`. '첫 항목만'으로 처리하면 입력 순서에 따라 결과가 달라져 순열 불변성이 깨지므로 막습니다.
   - 같은 종목에 서로 다른 고유 신규 사건이 둘 이상 → `BLOCKED_SAME_SYMBOL_MULTI_EVENT`(자동 합성 안 함)
3. 모든 고유 신규 사건을 **S0 기준**으로 검증합니다(검증 중 상태 변경 0).
   - 검사 항목: 실제 사건 표시 · apply_date 누락/순서/불일치 · 입력 · 존재하지 않는 종목 · m_qty × m_price ≠ 1 · 단주
4. 하나라도 실패하면 `BATCH_ABORTED`입니다.
   - S0를 그대로 둡니다(해시 동일 · 적용 집합 불변).
   - 그날부터 원장 전체를 `PERF_BLOCKED`로 둡니다.
5. 전부 통과하면 scratch 복사본에 사건별로 (수량 × m_qty, 표시가격 × m_price)를 함께 적용합니다.
   - 불변식을 다시 확인한 뒤 한 번만 커밋합니다(`COMMITTED`).
   - 불변식: 현금 불변, 종목별 가치 보존, 정수 수량, 사건당 1회
   - 중간 snapshot은 없습니다.
6. 실제 사건 표시는 `APPLY_BLOCKED_NO_PRICE_BASIS_DATE`이고, 배치는 ABORTED입니다.

## fixture(합성 종목 A · B · D, 합성 날짜) — 기대값 미리 고정
| # | 배치 | 기대 |
|---|---|---|
| F1 | A_OK + B 비율곱 오류 | ABORTED · 해시 = S0 · PERF_BLOCKED |
| F2 | A_OK + D 단주 | ABORTED · 해시 = S0 |
| F3 | A_OK + 없는 종목 X | ABORTED · 해시 = S0 |
| F4 | A_OK + B_OK | COMMITTED · 두 사건 1회씩 · 가치 보존 · TWR/MDD 0 |
| F5 | A_OK + A 같은 의미키(다른 출처) | COMMITTED · A 정확히 1회 · DUPLICATE_IGNORED 1 · TWR/MDD 0 |
| F6 | A split ×5 + A split ×2(같은 종목 · 다른 사건) | ABORTED(`BLOCKED_SAME_SYMBOL_MULTI_EVENT`) · 해시 = S0 |
| F7 [보탬] | A(m_qty 5 · m_price 1/5) + 같은 키 A(m_price 1/4) | ABORTED(`BLOCKED_KEY_PAYLOAD_CONFLICT`) · 해시 = S0 |
| F8 [보탬] | 전날 B 적용 뒤 · A_OK + B 재전송 | COMMITTED · A 1회 · B DUPLICATE_IGNORED · TWR/MDD 0 |
| F9 | A_OK + B 실제 사건 표시 | ABORTED(`APPLY_BLOCKED_NO_PRICE_BASIS_DATE`) · 해시 = S0 |

- **순열 불변성:** 모든 fixture를 가능한 모든 입력 순서로 돌립니다. 판정 · 최종 해시 · 키별 상태(출처 번호 제외)가 모두 같아야 합니다.
- **수정 전 음성대조군:** PR #104 head의 `Ledger.process_day`를 그대로 불러 F1 · F2 · F3를 돌립니다. 기대는 'B 실패에도 A가 반영됨(수량 · 가격 변경 · 해시 ≠ S0)'이 재현되는 것입니다.

## 상태
- 실패 배치 해시 = S0(전부), 성공 배치는 순서와 무관하게 같은 해시, 중복은 정확히 1회, 음성대조군 재현이면 READY입니다.
- 아니면 BLOCKED입니다.
- 기대값은 결과에 맞춰 바꾸지 않습니다.
- READY여도 실제 적용 0 · 성과/NAV 미검증 · PAPER_VALIDATION_READY=false입니다.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/batch_atomicity.py`
- `evidence/batch-atomicity.json` · `evidence/run.log`
