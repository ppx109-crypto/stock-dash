# DATA-0001 EVIDENCE-CONTRACT — append-only 시점별 연구증거 계약(1판)

기계 판정 규칙의 원본은 `PREREG-LOCK.md` 1~4장과 `validator.py`입니다. 이 문서는 사람이 읽는 요약과 운영 원칙입니다. 레코드 모양은 `schemas/*.schema.json`(봉투 1 + payload 14)에 있습니다.

## 1. 원칙
1. **append-only**
   - 받은 레코드는 고치거나 지우지 않습니다.
   - 같은 `(record_id, version)`에 다른 내용이 오면 거부합니다. 같은 내용이면 세기만 합니다.
2. **정정은 새 판**
   - `version+1`, `revision_of=id@이전판`, `is_correction=true`로 씁니다.
   - 원본은 그대로 남습니다.
   - 정정 공시(DART)는 같은 record_id의 새 판이며, 새 `rcept_no`와 `original_rcept_no`를 함께 적습니다.
3. **세 시각을 나눔**
   - `as_of`(값이 가리키는 때) ≤ `available_at`(알 수 있게 된 때) ≤ `fetched_at`(우리가 받은 때)
   - 모두 `+09:00`이어야 합니다.
   - git 커밋 시각은 이 셋 중 어느 것도 대신하지 않습니다.
4. **판단 시점 컷오프**
   - SIGNAL은 `available_at ≤ decision_at`인 입력 판만 `inputs`(`id@ver`)에 적을 수 있습니다.
   - `cutoff_hash`로 입력 목록을 고정합니다.
   - ACCOUNT_STATE도 `as_of` 기준으로 같은 규칙을 따릅니다.
5. **원주가와 수정주가를 나눔**
   - PRICE_BAR_RAW는 `adjusted=false`이고 조정 필드가 없습니다.
   - 수정주가는 PRICE_BAR_ADJ로 따로 씁니다.
   - RAW 기준 신호가 ADJ를 쓰면 거부합니다.
6. **모르면 모른다고 함**
   - Universe(t) · 거래 상태 · 기업행동 · 비용은 해당 레코드가 없으면 `UNKNOWN` · `NONE_KNOWN`으로 둡니다.
   - 현재 목록, 봉이 없다는 사실, 앞 비용표로 추정하지 않습니다.
7. **증거 종류를 섞지 않음**
   - HISTORICAL_MODEL 체결에는 model 규칙(봉 · 가격 필드 · 규칙 id · 미끄러짐 포함 여부)이 있어야 하고 evidence_ref가 없어야 합니다.
   - OBSERVED_KIS_PAPER 체결에는 가명 evidence_ref(`ev_` + 16자리 hex)가 있어야 합니다.
8. **비공개 자료는 레코드에 넣지 않음**
   - 계좌번호 · 원 주문번호 · 원문 응답 · 키 · 토큰 · 세션 주소는 넣지 않습니다.
   - 원문은 비공개 보관 참조(`raw_ref`)와 hash만 둡니다.

## 2. 시각 규칙(CLAUDE.md 미래참조 규칙과 맞춤)
| 자료 | available_at 최소 |
|---|---|
| 일봉 종가 | 그날 장 마감 뒤 실제 받은 시각(15:30 전이면 거부 대상은 아니나 as_of ≤ available_at이어야 함) |
| 투자자별 수급 | 그 거래일 15:30 이후(`FLOW_TOO_EARLY`) |
| DART 공시(시각 앎) | 접수 시각 이후 |
| DART 공시(날짜만 앎) | 접수일 다음날 00:00 이후(`DATE_ONLY_TOO_EARLY`) |
| 재무 | 그 재무를 담은 공시의 available_at 이후 |
| 거래정지 · 기업행동 | 공표된 시각(효력 시각과 따로) |

## 3. 1천만 원 · 1억 원 수량 · 용량 검증에 필요한 필드(정의만)
- ACCOUNT_STATE: `cash, nav, alloc_won`과 그 입력 판
- ORDER_EVENT: `order_id`(가명) · 사건 · 시각 · seq
- FILL: 정수 `qty`, `price`, 가명 evidence_ref(관측) 또는 model 규칙(모형)
- PRICE_BAR_RAW: `volume`(필요하면 거래대금) — 주문 금액 대비 거래량 비율은 다음 단계 규칙 몫
- COST_SCHEDULE: 수수료 · 세금 · 미끄러짐의 rate · 적용기간 · 출처

이번에는 성과나 주문을 계산하지 않았습니다.

## 4. 알려진 한계(1판)
- 개인정보 키 목록은 **대소문자를 구분**하고, `order_no`가 빠져 있습니다. KIS 응답의 `ODNO`나 운영 장부의 `order_no`(원 주문번호)는 지금 검증기가 못 막습니다. 다음 판에서 대소문자 무시와 `order_no` 추가가 필요합니다. 결과를 본 뒤에 찾은 것이라, 이번 판은 바꾸지 않았습니다.
- 스키마 검사는 표준 라이브러리로 만든 부분 구현(`tests/schema_check.py`)이며, 이번 스키마가 쓰는 키워드만 다룹니다.
- 거래일 달력 · 호가단위 · 가격제한 판정 입력은 필드 자리만 있고 규칙은 없습니다.
- 이 계약은 아직 어떤 수집기나 봇에도 연결하지 않았습니다.
