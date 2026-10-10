# REPLAY-0001 PREREG-LOCK — 순수 회계 커널 사전 고정

- 입력: PR #16 head `49d5bafae17c02f7ffc4f7dd2a2162cca7de214c` (TASK.md · PREREG.md · REVIEW.md · INDEPENDENT-CHECK.json · receipt.json)
- 이 문서와 `fixtures/golden.json`은 **커널 구현 · 시험 실행 · 결과 보기 전에** 쓴 것입니다. 잠근 시각과 hash는 `PREREG-LOCK.stamp.json`과 첫 커밋에 남깁니다.
- 이 단계 앞에서 한 탐색(MEAS-0001의 a_mtm 현금 음수 · 같은 날 매매 누락 · 장부 pnl% 맞춤 등)은 **탐색 결과**이며 이번 사전검정이 아닙니다. 이번 사례는 그 결함을 계약으로 막는지 보는 합성 시험입니다.
- 골든 금액은 손으로 셈했습니다. 몇 개(C15 TWR, C20 정수주)는 손셈을 `fractions.Fraction` 계산기로 한 번 더 확인했으며, 커널 코드는 쓰지 않았습니다.
- 합성 비용률(0.001 · 0.002 · 0.00015 등)은 **시험용 값**이며 실제 국내 거래비용이 아닙니다. 실제 비용 근거는 `null`.

## 1. 커널 고정 정책

### 1.1 숫자
- 금액은 `Decimal`, 원 단위 정수. 수수료 · 세금은 **체결 1건마다** `금액×율`을 `ROUND_HALF_UP`으로 원 단위 반올림(수수료와 세금 따로).
- 비율(수익률 · MDD)은 `Decimal` 정밀도 28자리로 셈하고, 비교는 소수 12자리(`ROUND_HALF_EVEN`)로 맞춘 뒤 **정확히 같아야** PASS. 골든 비율은 분수 `"a/b"` 또는 끝나는 소수로 적음.
- 금액 비교는 오차 0(정수 일치). float 허용오차 없음.

### 1.2 사건과 순서
- 사건 종류: `DEPOSIT`, `WITHDRAW`, `ORDER_INTENT`, `ORDER_ACCEPTED`, `ORDER_REJECTED`, `ORDER_CANCELLED`, `ORDER_EXPIRED`, `FILL`, `PRICE`, `CORP_ACTION`, `MARK`(그날 평가 · 고정), `SNAPSHOT`(상태 확인만).
- 시각은 `+09:00`이 붙은 ISO 문자열이어야 함(없으면 입력 오류 `NO_TZ`, 실행 전체 거부).
- 순서: `(at, seq)`. **같은 `at`을 가진 사건이 둘 이상인데 그중 하나라도 `seq`가 없거나 `seq`가 겹치면** 실행 전체를 `AMBIGUOUS`로 거부하고 어떤 상태도 만들지 않음(‘매도 먼저’ 같은 추정 금지).
- 같은 `id`의 사건이 두 번 오면 입력 오류(`DUP_EVENT_ID`).

### 1.3 주문 · 체결
- 의도 · 접수 · 거절 · 취소 · 만료는 현금 · 수량을 바꾸지 않음. **확정 체결(FILL 또는 합성 MODEL_FILL)만** 바꿈.
- `source_mode`: `SYNTHETIC` / `HISTORICAL_MODEL` / `OBSERVED_KIS_PAPER`. `SYNTHETIC`·`HISTORICAL_MODEL`의 체결은 `evidence="MODEL_FILL"`로 표시. `OBSERVED_KIS_PAPER`에서 `evidence_ref`가 없는 체결은 `MISSING_EVIDENCE`로 거부. broker 원문 · 계좌 · 원 주문번호 필드는 받지 않음(가명 id만).
- 체결 내용 비교 필드: `order_id, trade_id, strategy_id, security_id, side, qty, price, fee, tax, at`. 같은 `fill_id`가 같은 내용으로 또 오면 무시하고 `duplicates_ignored`+1. 내용이 다르면 그 사건을 `FILL_ID_CONFLICT`로 거부(상태 불변).
- 체결 거부 사유와 검사 순서: `BAD_QTY`(정수 아님 · 0 이하) → `BAD_PRICE`(0 이하) → `MISSING_EVIDENCE` → 매도면 `OVERSELL`(그 (strategy, trade, security) 묶음 보유보다 많음) → 매수면 `INSUFFICIENT_CASH`(대금+수수료 > trade-date 현금). 거부된 사건은 상태를 바꾸지 않고 `rejections`에 `{event_id, reason}`로 남음.
- 보유는 `(strategy_id, trade_id, security_id)` 묶음별. 매도는 반드시 자기 묶음에서만 줄임(다른 전략 보유로 메꾸지 않음). 부분청산은 같은 `trade_id`의 출구 체결로 붙고 새 진입을 만들지 않음.
- 매수 원가 = 대금 + 매수 수수료. 부분 매도의 원가 몫 = 남은 원가 × (판 수량 ÷ 남은 수량), 원 단위 `ROUND_HALF_UP`; 마지막 매도는 남은 원가 전부. 실현손익 = (매도대금 − 매도 수수료 − 세금) − 원가 몫.
- `slippage_in_price=true`인 체결은 가격 안에 미끄러짐이 들어 있으므로 현금으로 따로 빼지 않음. `ref_price`가 있으면 `(price−ref_price)×qty`를 **정보로만** `slippage_info_won`에 기록.
- 장부 `ledger_pnl_pct`가 붙은 매도는 그 값으로 현금을 만들지 않음. 묶음이 다 닫힐 때 `fill_net_ret = 실현손익합 ÷ 진입원가합`을 셈하고, `ledger_pnl_pct/100`과 다르면 `discrepancies`에 남김(현금 · NAV는 체결로만).

### 1.4 주문 크기(합성 의도 `ORDER_INTENT` + `model_fill=true`)
- 매수: 의도에 `alloc_won`(이번 주문 한도, 입력으로 명시)과 `nav_ref_won`(그때 계좌 평가액, 기록용)을 줌. `limit = min(alloc_won, orderable_cash)`.
  `q = floor(limit ÷ (price × (1+buy_fee)))`, 그 뒤 `q×price + 반올림(q×price×buy_fee) > limit`이면 `q`를 1씩 줄임. 비용을 뺀 `min(원금, 현금)÷가격`은 쓰지 않음.
  - `naive_qty = floor(alloc_won ÷ price)`(비용 무시 기준, 비교용).
  - 사유: `q = naive_qty`이면 `OK`; `alloc_won ≤ orderable_cash`이고 `q < naive_qty`이면 `REDUCED_FOR_COST`; `orderable_cash < alloc_won`이고 `q > 0`이면 `REDUCED_BY_CASH`; `q = 0`이고 `orderable_cash < alloc_won`이면 `ZERO_BY_CASH`; `q = 0`이고 한도가 충분했으면 `ZERO_CANNOT_AFFORD_ONE_WITH_COST`. 현금 때문에 줄면 `shortfall_won = alloc_won − orderable_cash`.
  - `q > 0`이면 `price`로 MODEL_FILL을 만들고 그 체결도 1.3 검사를 거침. 숨은 차입 없음.
- 매도: `sizing="ALL_HELD"`이면 그 묶음 보유 전부를 `price`로 MODEL_FILL.

### 1.5 현금 · 결제
- 기본 현금은 **trade-date 경제 현금**(체결 순간 바뀜). 결제는 합성 정책 `T+2 평일`(공휴일 무시, 증권사 실측 아님). 체결에 `settle_date`가 있으면 그것을 씀. 입출금은 즉시 결제.
- `settled_cash`, `receivable`(미결제 매도 순대금), `payable`(미결제 매수 대금+수수료)을 따로 둠. 항등식 `cash_td = settled + receivable − payable`가 매 평가에서 성립해야 함(어기면 실행 오류).
- `orderable_cash = cash_td − 열린 매수 주문 예약`. 예약 = 남은 수량×지정가 + 반올림(남은 수량×지정가×buy_fee). 증권사 주문가능금액 실측이 아님.
- 출금이 trade-date 현금보다 크면 `INSUFFICIENT_CASH`로 거부.

### 1.6 평가 가격 · NAV
- `PRICE`: `prices{security: price}`, `as_of`, `available_at`, `version`, `source`, `session`. `available_at < as_of`이면 `BAD_PRICE_TIME`으로 거부.
- `MARK`(날짜 d, 시각 m): 보유 종목마다 `available_at ≤ m` 이고 `as_of ≤ m`인 값 중 `as_of`가 가장 늦은 것, 같은 `as_of`면 `version`이 가장 큰 것을 씀.
  - 쓸 값이 없음 → `MISSING_PRICE:<sec>`; 쓸 값의 `as_of` 날짜 < d → `STALE_PRICE:<sec>`; 그 종목에 `CORP_ACTION`(분할 등)이 m 이전에 있음 → `UNSUPPORTED_CORP_ACTION:<sec>`. 셋 중 하나라도 있으면 **그날 NAV = null**(앞 값 · 뒤 값으로 채우지 않음).
- `NAV = cash_td + Σ 정수보유×평가가격` (= settled + receivable − payable + 평가액). 미지급 비용은 체결 때 바로 현금에서 빠지므로 0.
- 한 번 만든 MARK 결과는 고정. 그 뒤 들어온 정정값(같은 `as_of`, 더 큰 `version`, `available_at` > 그 MARK 시각)은 과거 NAV를 바꾸지 않고 `corrections_after_snapshot`에 `{security, as_of, version, price, snapshot_date}`로 남김.

### 1.7 수익률 · 위험 판정
- 입출금 시각 분류: 09:00 전 → 그날 시작 흐름 `F_s`; 15:30 이후 → 그날 끝 흐름 `F_e`; 그 사이 → `INTRADAY_FLOW`(그날 수익률 null).
- 하루 수익률 `r_d = (NAV_d − F_e) ÷ (NAV_prev + F_s) − 1`. `NAV_prev`는 앞 MARK의 NAV, 첫 MARK면 0. 다음 중 하나면 `r_d = null`과 사유: NAV_d 또는 NAV_prev가 null(`NAV_NULL`), 분모 ≤ 0(`NONPOSITIVE_BASE`), `INTRADAY_FLOW`.
- 달력월 수익률 = 그 달 `r_d`의 복리(하나라도 null이면 null). `partial_month = true`: 그 달 첫 MARK 날이 그 달 첫 평일보다 늦거나, 마지막 MARK 날이 마지막 평일보다 이름.
- MDD: 단위가치 `U_0 = 1`(첫 입금 시점), `U_d = U_{d-1}×(1+r_d)`; `MDD = min_d (U_d ÷ max_{s≤d} U_s − 1)`. `r_d`가 하나라도 null이면 null. 원 NAV 고점 MDD(`raw_nav_mdd`)는 외부 입출금이 첫 입금 하나뿐일 때만 셈하고, 아니면 null + `FLOWS_PRESENT`.
- 판정(각각 독립): 하루 = 가장 나쁜 `r_d`, 달 = 가장 나쁜 달력월, MDD. 값 ≥ −0.15 → `PASS`, 값 < −0.15 → `FAIL`, null이 섞이면 null 아닌 값 중 FAIL이 있으면 `FAIL`, 없으면 `INCOMPLETE`. 종합 = FAIL 하나라도 → FAIL, 아니면 INCOMPLETE 하나라도 → INCOMPLETE, 아니면 PASS.

### 1.8 출력(시험이 보는 필드)
`status`(OK/AMBIGUOUS/INPUT_ERROR), `cash`(trade-date), `settled_cash`, `orderable_cash`, `positions{security: qty}`(0 제외), `navs{date: {nav, cash_td, settled, receivable, payable, mv, reason}}`, `returns{date: r|null}`, `return_reasons`, `months{YYYY-MM: {ret, partial}}`, `risk{day, month, mdd, raw_nav_mdd, verdict_day, verdict_month, verdict_mdd, verdict}`, `twr_total`, `net_flows`, `money_pnl`, `rejections[]`, `duplicates_ignored`, `sizing[]`, `orders{}`, `trades{}`, `discrepancies[]`, `corrections_after_snapshot[]`, `costs_by_date{}`, `snapshots[]`, `fills[]`, `ambiguous_ids[]`, `min_cash`, `max_gross_exposure`(MARK마다 평가액÷NAV의 최댓값), `attribution{strategy: 실현+마지막 MARK 평가손익}`, `risk.raw_nav_mdd_reason`.
- 시험 실행기가 출력에서 따로 셈하는 값: `fills_count = len(fills)`, `trades_count = len(trades)`, `total_qty = Σpositions`.
- 비교 방법: 기대값이 dict면 적힌 키만 봄(부분 비교), list면 길이가 같고 같은 자리끼리 비교(원소가 dict면 적힌 키만), 정수는 정확히 같음, 비율 문자열은 1.1의 12자리 비교, `null`은 null이어야 함.

## 2. 사례마다 함께 보는 불변식(모든 20사례 공통)
1. 모든 체결 직후 `cash_td ≥ 0`, 모든 보유 정수 ≥ 0.
2. 보존: `cash = Σ입금 − Σ출금 − Σ(매수대금+매수수수료) + Σ(매도대금 − 매도수수료 − 세금)`를 시험 쪽에서 체결 목록으로 따로 셈해 정확히 일치.
3. 모든 MARK에서 `cash_td = settled + receivable − payable`, NAV가 있으면 `nav = cash_td + mv`.
4. `max_gross_exposure`(평가액 ÷ NAV의 최댓값) ≤ 1(현물 무차입).

## 3. 고정 20사례(입력 전체는 `fixtures/golden.json`)
기본 설정: `SYNTHETIC`, buy_fee 0.001, sell_fee 0.001, sell_tax 0.002, 날짜 D1=2026-01-05(월), D2=01-06, D3=01-07, D4=01-08, 시작 입금은 08:00.

| # | 입력 요지 | 손셈 골든 기대값 |
|---|---|---|
| C1 | 1,000,000 입금, 매수 의도+접수 10주@50,000, 가격 50,000, MARK | cash 1,000,000 · 보유 없음 · NAV 1,000,000 · orderable 499,500(=1,000,000−500,000−500) · 주문 o1 남은 10 |
| C1b | OBSERVED_KIS_PAPER, 증거 없는 체결 1주@1,000 | 거부 MISSING_EVIDENCE · cash/NAV 1,000,000 |
| C2 | o1 거절, o2 접수→취소, o3 접수→만료 | cash 1,000,000 · 보유 없음 · NAV 1,000,000 · orderable 1,000,000 · 주문상태 REJECTED/CANCELLED/EXPIRED |
| C3 | o1 50주@2,000 접수, 20주 체결(09:10), SNAPSHOT 09:30, 잔량 취소 10:00 | 체결 20 · 대금 40,000 · 수수료 40 · cash 959,960 · SNAPSHOT orderable 899,900(예약 60,060) · 끝 orderable 959,960 · NAV 999,960 · o1 filled 20 / cancelled 30 |
| C4 | f1 매수 10@10,000, 같은 f1 재전달, f1 수량 11로 충돌 | cash 899,900 · 보유 10 · duplicates_ignored 1 · 거부 FILL_ID_CONFLICT 1 · NAV 999,900 |
| C5 | C4처럼 10주 보유 후 6건: 매도 11 · 수량 −5 · 수량 1.5 · 가격 0 · 가격 −100 · 매수 100@10,000 | 거부 순서 OVERSELL, BAD_QTY, BAD_QTY, BAD_PRICE, BAD_PRICE, INSUFFICIENT_CASH · cash 899,900 · 보유 10 · NAV 999,900 |
| C6 | alloc 1,000,000(=전 현금), 1,000원 매수 | naive 1,000 → 999주(REDUCED_FOR_COST) · 대금 999,000 · 수수료 999 · cash 1 · NAV 999,001 |
| C7 | 1,000원 입금, alloc 1,000, 1,000원 매수 | 0주 · ZERO_CANNOT_AFFORD_ONE_WITH_COST · 체결 없음 · cash 1,000 · NAV 1,000 |
| C8 | 1,000,000, 12종목 각 alloc 100,000(10칸 기준) 1,000원 순서대로 | 1~10번 각 99주(REDUCED_FOR_COST, 99,099씩) · 11번 9주 REDUCED_BY_CASH(shortfall 90,990) · 12번 0주 ZERO_BY_CASH(shortfall 99,999) · cash 1 · 총 999주 · NAV 999,001 · min_cash 1 · max_gross_exposure 999,000/999,001 |
| C9 | 같은 날 09:10 매수 100@5,000, 14:00 매도 100@5,100 | 비용 500+510+1,020 · cash 1,007,970 · 실현 7,970 · NAV 1,007,970 · r 0.00797 |
| C10 | 10:00 같은 시각 매수10 · 매도10, seq 없음 | status AMBIGUOUS · ambiguous_ids [c10_f1, c10_f2] · NAV 없음 |
| C10b | 같은 입력에 seq 1(매수) · 2(매도) | cash 999,600 · 보유 없음 · NAV 999,600 |
| C11 | 매수 50@10,000(T1), 매도 20, 매도 30(모두 10,000) | 원가 몫 200,200 / 300,300 · 실현 −800 / −1,200 · 합 −2,000 · 진입 1건 · 출구 2건 · cash 998,000 · NAV 998,000 |
| C12 | D1 매수 100@1,000, D2 보유, D3 매도 100@1,000, 가격 늘 1,000 | NAV 999,900 / 999,900 / 999,600 · r −0.0001 / 0 / −300/999900 · 비용 D1 100, D3 300 · 1월 수익률 −0.0004 · cash 999,600 |
| C13 | 기준가 100,000, 미끄러짐 포함 체결 1주@100,500, 평가 100,000 | 수수료 101(100.5→101) · cash 899,399 · NAV 999,399 · slippage_info 500 · 추가 현금차감 0 |
| C14 | D1 매수 100@5,000, D2 매도 100@5,150, 장부 pnl 3.0% | cash 1,012,955 · NAV D2 1,012,955 · fill_net_ret 2591/100100 · discrepancy 1건(ledger 0.03) |
| C15 | D1 1,000,000 입금 · 매수 50@10,000 · 평가 11,000; D2 08:00 +1,000,000 · 평가 10,000; D3 08:00 −500,000 · 평가 10,000 | NAV 1,049,500 / 1,999,500 / 1,499,500 · r 0.0495 / −50000/2049500 / 0 · TWR 195901/8198000 · net_flows 1,500,000 · money_pnl −500 · MDD −50000/2049500 · raw_nav_mdd null(FLOWS_PRESENT) |
| C16a | 비용 0, 01-29 매수 100@10,000, 01-30 평가 8,500 | r −0.15 · 1월 −0.15(partial) · MDD −0.15 · 세 판정 PASS |
| C16b | 같은데 01-30 평가 8,490 | r −0.151 · 세 판정 FAIL |
| C16c | 매수비용 0.001, 1,001,000 입금, 1,000주@1,000, 01-29 평가 1,000 · 01-30 850 | r −1/1001 / −0.15 · 하루 PASS · 1월 −151000/1001000 FAIL(partial) · MDD −151000/1001000 FAIL · 종합 FAIL |
| C17 | D1 매수 10@10,000; v1 10,000(D1 15:45 공개); v2 정정 9,000(D2 10:00 공개); D2 값 12,000; 공개시각이 as_of보다 앞선 가격 1건 | NAV D1 999,900(정정 반영 안 함) · NAV D2 1,019,900 · corrections_after_snapshot 1건(v2, snapshot D1) · 거부 BAD_PRICE_TIME 1 |
| C18a | 가격 없는 S2 10주@5,000 보유 | NAV null(MISSING_PRICE:S2) · 판정 INCOMPLETE |
| C18b | S1 10주@10,000, D1 가격 10,000, D2 가격 없음, D3 11,000 | NAV 999,900 / null(STALE_PRICE:S1) / 1,009,900 · r −0.0001 / null / null · 판정 INCOMPLETE |
| C18c | 1,000,000 입금, D2 08:00 전액 출금 | NAV 1,000,000 / 0 / 0 · r 0 / null(NONPOSITIVE_BASE) / null(NONPOSITIVE_BASE) · 판정 INCOMPLETE |
| C18d | S1 10주 보유, D2 분할 사건 | NAV D1 999,900 · D2 null(UNSUPPORTED_CORP_ACTION:S1) |
| C19 | D1 A 50주 · B 30주 @10,000(같은 종목, 다른 전략), D2 A 50주@11,000 매도, D3 A 10주 매도 시도, 평가 D1 10,000 · D2~D4 11,000 | D1: cash 199,200 · settled 1,000,000 · payable 800,800 · NAV 999,200 / D2: cash 747,550 · settled 1,000,000 · payable 800,800 · receivable 548,350 · NAV 1,077,550 / D3: settled 199,200 · payable 0 · receivable 548,350 / D4: settled 747,550 · receivable 0 · NAV 1,077,550 · A 실현 47,850 · B 평가손익 29,700 · 합 77,550 = NAV − 입금 · 거부 OVERSELL 1 · 계좌 보유 30 |
| C20 | 비용 buy 0.00015 · sell 0.00015 · tax 0.002; 1천만 / 1억 각각 alloc=입금/10, 12,345원 매수; D2 13,000원 전량 매도 | 1천만: 80주 · 대금 987,600 · 수수료 148 · cash 9,012,252 · NAV D1 9,999,852 · 매도 수수료 156 · 세금 2,080 · cash 10,050,016 / 1억: 809주(800 아님) · 대금 9,987,105 · 수수료 1,498 · cash 90,011,397 · NAV D1 99,998,502 · 매도 수수료 1,578 · 세금 21,034 · cash 100,505,785 |

사례 수: 주 사례 20개(C1~C20), 그 안의 부속 입력 C1b · C10b · C16a/b/c · C18a/b/c/d · C20 두 자본. 판정은 **주 사례 단위**: 부속까지 모두 맞아야 그 사례 PASS.

## 4. 원본 as-is 결함 노출 대조(신규 계약 판정과 따로 셈)
`research/a_mtm.py`(기준점 00b98ab1)의 `account()` 정의만 떼어 numpy 없이 같은 식으로 옮긴 함수로 다음 합성 입력을 돌림. 이것은 **결함이 드러나는지 보는 시험**이며 그 FAIL은 신규 커널 FAIL이 아님.
- X8(C8 대응): 같은 날 1칸짜리 12건 → as-is 현금 최저 −0.2(상대값), 노출 1.2 → `DEFECT_EXPOSED` 기대.
- X9(C9 대응): 같은 날 매수 · 매도 1건(pnl 2.0%, 10칸) → as-is 수익률 모두 0(거래 누락) → `DEFECT_EXPOSED` 기대.
- X14(C14 대응): D1 매수 · D2 매도, pnl 3.0%, 10칸 → as-is 마지막 날 수익률 +0.03(비용 0) vs 커널 1,012,955/1,000,000 → `DEFECT_EXPOSED` 기대.

## 5. 장부 입력 가능성 점검(INPUT-FEASIBILITY)
- 대상: RULES-0002@`a61f033ecd16ba0976c955a93bfec70c7463ad53` `research-exchange/claude-to-gpt/RULES-0002/results/d1_ledger_ASIS.csv`. 파일 sha256과 495행을 먼저 확인(다르면 중지하고 보고).
- 한 번 선형으로 읽고: 실제 컬럼명, 행 수, `(code, entry)` 묶음 수와 2행 이상 묶음(부분청산 후보) 수, 커널 fill 필수 필드(`fill_id, trade_id, strategy_id, security_id, at(시각+tz), side, qty, price, fee/tax 또는 비용모형, settle_date 선택`)별 있음/없음/날짜만.
- 미리 정한 판정: 체결 시각 · 체결가 · 수량 중 하나라도 없으면 그 행은 `MISSING_REQUIRED`로 그대로 두고 채우지 않음. 그런 행이 하나라도 있으면 `HISTORICAL_REPLAY = BLOCKED_NEEDS_DATA`. 가격 캐시 · 새 원장 · API를 찾지 않음.

## 6. 예산 · 실행 환경
- 커널 1판. 시험 실행은 20사례 + as-is 대조 3건 + 장부 1회 선형 읽기, 목표 2분 · 256MB 이내(`resource`로 재서 기록).
- 표준 라이브러리만. 시험 실행기는 `socket` 연결을 막고 운영 폴더를 import하지 않음(모듈 출처 확인). KIS/DART/PAPER/DISCORD 환경변수는 실행 전에 지움.

## 7. 판정과 고치기 규칙
- 커널 판정: 주 사례 20개가 모두 PASS이고 공통 불변식이 모두 성립하면 `VERIFIED_SYNTHETIC`. 아니면 `NOT_VERIFIED`.
- 첫 실행 결과는 `TEST-RESULT.run1.json`으로 그대로 보존. FAIL을 PASS로 만들려고 골든 기대값을 실제 출력으로 바꾸지 않음. 커널 결함을 고치면 고친 내용 · 이유를 `REPORT.md` 고치기 기록에 남기고 다시 돌린 결과를 `TEST-RESULT.json`으로 둠. 골든 자체의 명백한 손셈/입력 오류를 발견하면 고치기 전 · 후 값과 근거를 같은 기록에 남김.
- 커널 통과는 판단 시점 · 체결 가능성 · 유니버스 · OOS · 전략 수익성 · 모의 준비 · 실전 합격 어느 것도 뜻하지 않음. 역사 재생은 이번에 하지 않음.
