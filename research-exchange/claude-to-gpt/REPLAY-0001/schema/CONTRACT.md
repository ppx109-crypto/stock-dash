# REPLAY-0001 회계 커널 계약(커널 1판 `REPLAY-0001-kernel-v1`)

기준 정책은 `../PREREG-LOCK.md` 1장입니다. 이 문서는 TASK의 계약 1~11에 커널이 어떻게 대응하는지와, 구현하면서 **LOCK에 없던 것을 더한 부분**을 적습니다. 입력 모양은 `events.schema.json`에 있습니다.

## 계약 1~11 대응
| TASK 계약 | 커널 동작 | 골든 사례 |
|---|---|---|
| 1 source_mode · 확정 체결만 변화 | `SYNTHETIC/HISTORICAL_MODEL/OBSERVED_KIS_PAPER`. 의도 · 접수 · 거절 · 취소 · 만료는 주문 상태만 바꿈. 합성 체결은 `MODEL_FILL`. 관측 모드에서 `evidence_ref` 없는 체결은 `MISSING_EVIDENCE` | C1 · C1b · C2 · C3 |
| 2 체결 필드 · 멱등 | 가명 id만. 같은 `fill_id` + 같은 내용 → `duplicates_ignored`, 다른 내용 → `FILL_ID_CONFLICT` | C4 |
| 3 현금 · 정수 보존 | 매수 대금+비용 ≤ trade-date 현금, 정수 수량, 비용 포함 크기 정하기(바닥 뒤 1주씩 줄이기), 0주 이유, 보유 초과 매도 거부 | C5 · C6 · C7 · C8 |
| 4 자본은 합성 시나리오 | 주문 한도 `alloc_won`, 계좌 평가 `nav_ref_won`을 사건마다 입력으로 받고 `sizing`에 그대로 남김. 칸 배분 규칙은 정하지 않음 | C8 · C20 |
| 5 같은 날 · 부분청산 · 여러 전략 | 보유는 `(strategy, trade, security)` 묶음. 부분청산은 같은 trade의 출구로 붙음 | C9 · C11 · C19 |
| 6 비용 1회 · 미끄러짐 중복 없음 | 체결 사건에서 한 번 차감. 가격에 미끄러짐이 들어 있으면 정보로만 기록. 비용률은 `SYNTHETIC_FIXTURE`, `real_cost_evidence: null` | C12 · C13 |
| 7 NAV · 결제 | `NAV = cash_td + Σ보유×평가가`. `cash_td = settled + receivable − payable`를 MARK마다 확인(어기면 실행 중단). 결제는 합성 T+2 평일. `orderable_cash`는 열린 매수 예약을 뺀 별도 값 | C3 · C19 |
| 8 평가 가격 | `as_of · available_at · version · source · session`. 없음/낡음/기업행동 → 그날 NAV null. 정정은 공개 뒤에만 쓰고, 이미 만든 NAV는 고치지 않고 `corrections_after_snapshot`에 남김. 분할은 `UNSUPPORTED_CORP_ACTION` | C17 · C18 |
| 9 장부 pnl은 참고 | 현금은 `qty×fill_px`로만. 묶음이 닫히면 `fill_net_ret`와 장부 값을 견줘 다르면 `discrepancies` | C14 |
| 10 입출금 · 위험 | 입출금은 손익에서 뺌. TWR 구간 연결, 달력월 복리, 단위가치 MDD, 세 기준 −15% 독립 판정, partial month, 결손 · 자산 0 표시 | C15 · C16 · C18 |
| 11 순서 | `(at, seq)`. 같은 시각 순서 없음 → `AMBIGUOUS`로 실행 전체 거부 | C10 · C10b |

## LOCK에 없던 것을 구현하면서 더한 부분(골든으로 시험하지 않음)
- 거부 사유 더함: `EVIDENCE_MODE_MISMATCH`(합성 모드인데 `MODEL_FILL`이 아닌 체결), `PRICE_AT_MISMATCH`(PRICE 사건의 `at` ≠ `available_at`), `UNSUPPORTED_SIZING`, `DUP_ORDER_ID`, `UNKNOWN_ORDER`, `BAD_ORDER_STATE`, `BAD_AMOUNT`, `BAD_SIDE`.
- 입력 오류(`status=INPUT_ERROR`, 상태 만들지 않음): `NO_TZ`, `BAD_TIME`, `DUP_EVENT_ID`, `BAD_EVENT_TYPE`, `BAD_SOURCE_MODE`, `MARK_DATE_MISMATCH`, `DUP_MARK_DATE`, `SLIPPAGE_NOT_IN_PRICE_UNSUPPORTED`(미끄러짐을 따로 현금비용으로 빼는 모형은 없음).
- 첫 MARK의 `NAV_prev = 0`이므로, 그날 09:00 전 입금이 있어야 첫 수익률이 셈됨(아니면 `NONPOSITIVE_BASE`).
- 매도 시 출구 체결 · 원가 몫 · 실현손익을 `trades[trade_id].exits`에 남김. 묶음이 다 닫혀야 장부 대사를 함.
- `attribution`은 마지막 MARK 기준(그날 NAV가 null이면 null).

## 커널이 하지 않는 것
- 금지 필드(계좌번호 · 원 주문번호 · 원문 응답) 검사는 스키마의 `not` 규칙으로만 적었고, 커널 자체는 그런 키를 읽지도 막지도 않습니다. 시험 환경에 JSON Schema 검사기를 넣지 않았으므로 스키마 검사는 이번에 **실행하지 않았습니다**.
- 실제 세율 · 수수료 · 결제일 · 주문가능금액 · 체결 가능성 · 호가 단위 · 가격 제한폭 · 공휴일 달력 · 기업행동 조정은 없습니다.
- 판단 시점 · 유니버스 · OOS · 전략 손익을 검증하지 않습니다.
