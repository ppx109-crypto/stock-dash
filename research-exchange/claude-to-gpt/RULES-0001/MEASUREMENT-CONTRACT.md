# MEASUREMENT-CONTRACT — 실측 계약(설계 · 비활성)

> **이번 단계에서 실제 수집은 하지 않았습니다.** 공개 저장소에는 이 문서 · `measurement.schema.json` · 합성 fixture만 둡니다. 실제 값(잔고 · 체결 · 금액 · NAV · 정규화 NAV 포함)은 **비공개 목적지가 정해진 뒤 별도 단계**에서만 다룹니다. 목적지: **미정**.
> 계약 함수: `fixtures/contract.py`(표준 라이브러리 · 네트워크 · 계좌 · 운영 모듈 import 없음) · 실행 결과: `test-result.json`(43건).

## 1. 사건을 나눔 (접수 ≠ 체결)
| 사건 | 필수 칸 | 지금 운영 기록 여부(00b98ab1) |
|---|---|---|
| 신호 판단 | signal_id · strategy_id · rule_version · decision_at · **max_feature_available_at** · signal_quote_at · code · side · requested_slots · assigned_slots · theoretical_price · skip_reason | 부분(daily-live/today.json 등 '그날 판단'만 덮어씀 · available_at 없음) |
| 주문 제출 | order_id_hash · order_submitted_at · broker_received_at · order_type · qty · qty_after_buyable_check | 부분(paper-orders.json에 '접수' 기록 · 주문번호 원값 · 금액 공개 위험 → 해시 필요) |
| 접수 · 거절 · 취소 · 만료 | order_status · reject_reason_code | 부분(접수 · 실패만) |
| 체결(부분 포함) | fill_time · fill_price · fill_qty · fees · taxes · venue(KRX/NXT) | **없음** — 장부가 접수 때 수량을 더함(paper_trade.py:405 · idle_live.py:402) |
| 일별 평가 | valuation_at · price_source(확정/잠정 종가) · cash(+결제 포함 여부) · receivable · payable · positions(전략 귀속) · corporate_actions · external_cashflows · NAV | **없음** — 잔고는 실행 안에서만 씀(broker_kis.py:736-742) |

계약 규칙(합성 시험으로 고정):
- 신호의 입력은 `available_at ≤ decision_at` 인 판만. 정정판은 **나온 시각 뒤에만** 쓰고 과거 판단을 덮어쓰지 않음(`avail.*` 4건).
- 봉은 `close_time ≤ observed_at` 일 때만(`bar.*`) · 체결 가정 가격은 `price_time ≥ order_submitted_at` 일 때만(`fill.*`). 봉을 늦게 셈했으면 이미 지난 다음 봉 시가로 체결했다고 적지 않음.
- 체결은 fills만 반영: 접수 뒤 0건이면 `unfilled`, 일부면 `partial`(`order.*`). 주문보다 많은 체결 · 가진 것보다 많은 매도는 오류.
- 한 OHLC 봉에서 익절 · 손절이 둘 다 닿으면 **손절 · ambiguous=true**(보수적 · `bar.tp_and_sl_same_bar_conservative`). 갭으로 손절선 아래에서 열리면 시가로(`bar.gap_down_*`). ※ 지금 운영 15분봉 · 1시간봉 · 1일봉은 **종가로만** 판단해 이 경우가 생기지 않음(as-is 시험 `*.trend_tp_and_sl_order_close_only`).

## 2. NAV · 수익률 · 손실 계산
- `NAV = 순현금 + Σ 수량 × 평가가 (+ 순결제채권, 단 예수금이 이미 결제분을 반영하면 더하지 않음)` — 중복 금지(`nav.*`). 운영은 D+2 예수금(`prvs_rcdl_excc_amt`)을 cash로 씀(paper_trade.py:121-128) → `cash_includes_settlement=true`로 기록해야 함.
- 하루 수익: 외부 입출금이 없으면 `r = NAV_close / NAV_prevclose − 1`. 있으면 입출금 시각으로 구간을 나눈 **TWR**(`twr.*` — 입금을 이익으로, 출금을 손실로 세지 않음). 시각을 모르면 `twr_is_approximation=true`로 표시하고 정확한 판정으로 쓰지 않음.
- 달력월 수익 = 그달 일별 TWR의 곱 − 1 · 기록 첫 달이 그달 첫 거래일에서 시작하지 않으면 `partial_month=true`(`month.calendar_boundary`).
- MTM MDD = `min(NAV_index / running_max − 1)`(`mdd.mtm`) — **사용자 손실 기준(하루 · 달력월 각각 −15%)과 별개**. 원금 · 고점 대비 −15%로 바꾸지 않음.
- 전략별 귀속 합 = 계좌 손익(내부 이체 · 비용 중복 차감 없이) · 차이는 `attribution_gap`으로 남김(`attr.*`).

## 3. 손실 정책(설계만 · 운영 적용 안 함)
- `day_twr ≤ −0.15 또는 month_to_date_twr ≤ −0.15` → **새 위험 늘리기 주문 막음** 상태(`gate.*` — −0.15 정확히도 막음). 보유 청산 · 재개 · 체결 불능 정책은 따로 정해야 함.
- **보장 아님**: 갭 · 거래정지 · 상하한가로 −15%보다 더 잃을 수 있음(`guarantee=false`).

## 4. 비용 시나리오(명세 · 이번에 셈하지 않음)
| 항목 | BASE | STRESS / EXTREME |
|---|---|---|
| 수수료 | 실제 적용 요율(상품 · 날짜별) — 운영 기록에 없음 → 체결 기록 필요 | 같은 근거 × 1.5 / × 2.0(가상 민감도라고 표시) |
| 거래세 | 매도만 · 시행일 기준 법정 세율(종목 · 시장 구분) — 임의로 곱한 값을 '현실 세금'이라 부르지 않음 | 세율 자체는 바꾸지 않음 |
| 스프레드 · 지연 | 주문 시각과 체결 시각 사이 가격 차 · 호가 단위 | 지연 × 2 등 |
| 시장 충격 | 참여율(주문 ÷ 거래대금) 기반 | 계수 × 1.5 / × 2.0 |
연구 perf2의 BASE(0.015% × 2 + 슬리피지 0.05% × 2 + 해마다 세율 + 0.10√(주문/ADV20))는 **연구 가정**이며 실측이 아님.

## 5. 기간 · 판정 경계
- 20거래일 기록 = **로그 품질 · 대사(시뮬 NAV와 같은 날 차이 분류) 점검**일 뿐, 알파 합격이 아님.
- 중복 회피 그림자(ALLOC-1)의 pilot 최소량 = **60거래일 AND 중복 기회 30건**(OR 아님) — 통계적 유의성 · 새 표본 · 장기 위험의 대체물이 아님. 그 기간의 CAGR로 장기 성과를 입증할 수 없음.
- 최종 선택 순서: ① 하루 · 달력월 위험 기준 → ② 비용 뒤 기대값 · 미지 검증 · 독립성 → ③ MDD · 현금 · 회전 · 수용량(Pareto). 현금을 줄이려고 음의 기대값 신호를 억지로 쓰지 않음.

## 6. 앞으로의 read-only 수집(별도 범위 · 승인 필요)
- 범위: 장 끝 뒤 1회 잔고 요약 · 그날 체결 조회(조회 전용 API) → **비공개 목적지**에만 · 공개 저장소에는 아무 값도 안 남김(정규화 NAV도 안 됨).
- 미결정: 목적지(비공개 저장소 · 외부 저장소 등) · 보존 기간 · 접근 권한 · 가명 키 규칙 · 주문번호 해시 소금 보관 위치.
