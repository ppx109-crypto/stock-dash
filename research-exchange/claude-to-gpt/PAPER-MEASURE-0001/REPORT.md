# PAPER-MEASURE-0001 결과 — 모의 체결 측정 연결부와 비식별 성과 출력

- 지시: PR #32 head `2e33273ca110225aefb6ca660d190b079a7da049` · source PR #31 head `1e6ed49b9b982ab3ab999082c7455e26cccc0bfd`
- PREREG-LOCK 첫 커밋 `8bfbf30c`(2026-10-08 11:28 KST, 도구 작성 전)
- **tool_status: READY**(도구 · 계약 · 시험 준비 완료) · **data_status: WAITING_DATA**(실측 체결 0행 · 실측 지표 0개)
- READY는 PAPER_VALIDATION_READY나 실전 승인이 아닙니다. `paper_validation_ready=false` · `live_approval=false`
- API · 로그인 · 주문 · 잔고/체결 조회 0 · 운영 파일 · 모의 봇 · 워크플로 변경 0 · 삭제 · 이력 수정 0 · 전략 실험 0

## 1. 판정
| 질문 | 답 |
|---|---|
| 지금 모의 기록이 체결 · 일별 MTM 검증에 충분한가 | **아니오.** `paper-orders`는 주문 접수 장부(ORDER_ACCEPTED_NOT_FILL)이고, 체결 원장과 일별 NAV는 저장소에 없음(`DATA-FLOW.md`) |
| 비공개를 지키는 오프라인 연결부가 fail-closed하는가 | **예(합성 시험).** 키 없음 · 작업트리 출력 · "접수" 행 · 필드 누락 · 충돌 중복을 모두 거부, 공개 출력 비밀 검사 통과 |
| 실측 성과 | 만들지 않음(WAITING_DATA) |

## 2. 왜 paper-orders는 체결이 아닌가(요약, 줄 근거는 DATA-FLOW §1 · §2)
- `paper_trade.py:401-411`: 주문 API가 주문번호를 돌려주면 바로 `status="접수"`로 적습니다. 체결은 조회하지 않습니다.
- `qty`는 넣은 수량, `price`는 판단 때 시세(`prices.get(code)`)입니다. 체결수량 · 평균체결가가 아닙니다.
- `held`는 접수 수량을 더하고 뺀 값입니다(`paper_trade.py:405-407` · `basket_live.py:205-207`).
- 확정 체결 규칙은 `predash/trades.py:18-54` `normalize_kis`에 이미 있지만 화면 표시에만 쓰이고 저장되지 않습니다.
- KIS 체결 행의 시각은 주문 시각이라, 새 원장도 `fill_at_basis = ORDER_TIME_LOWER_BOUND`로 표시합니다.

## 3. 만든 것(이 폴더 안에서만)
| 파일 | 내용 |
|---|---|
| `sanitize_fills.py` | 로컬 KIS 체결 원문 → 비공개 정규화 원장(JSONL). `normalize_kis`와 같은 확정 체결 규칙(날짜 · 시각 자리 수만 더 엄격). 원 주문 · 지점 번호 대신 로컬 키 HMAC `fill_uid`. 키 없으면 거부, 출력이 Git 작업트리 안이면 거부, 주문 장부 행 거부 |
| `build_daily_measurement.py` | 비공개 원장 + 시작 상태 + 일별 평가 + 입출금 + 기업행동 → 공개 비식별 일별 성과. 하나라도 빠지면 그날부터 null + 이유(보간 없음). 쓰기 전에 `public_guard`(금지 키 · 계좌/주문 꼴 문자열 · 원 단위 큰 숫자)와 `whitelist_guard`(허용 필드만) 통과 필수 |
| `PRIVATE-INPUT-SCHEMA.json` | 비공개 체결 원장 계약(TASK 5항 필드 포함: instrument_type · market_at_fill · fill_at_kst · side · quantity · fill_price · 실제/가정 비용 · strategy_id/rule_version · signal_at_kst · available_at 근거 · generator_commit). TASK 4항의 private_fill_schema에 해당 |
| `PUBLIC-OUTPUT-SCHEMA.json` | 공개 출력 계약(정규화 NAV · 일별 TWR · 일/달 손실 · 일별 MTM MDD · 현금/투자 비중 · 체결/거부 건수 · 비용/미끄러짐 bps · 완전성 · provenance). TASK 4항의 public_daily_schema에 해당 |
| `tests/test_measure.py` | 합성 시험 17개 |
| `DATA-FLOW.md` · `DATA-STATUS.json` · `PRIVACY-FINDINGS.md` | 분류표 · 자료 상태 · 노출 경로/개수 |

측정 정의: 일별 TWR은 E_t ÷ (E_{t−1} + 그날 시작 입출금) − 1, 정규화 NAV는 시작 1.0, MDD는 일별 NAV 기준, 하루 · 달 경보는 −15%보다 나쁠 때만(관측 경보 · 보장 아님). 자세한 정의는 PREREG-LOCK §2와 공개 스키마 `x-definitions`에 있습니다.

## 4. 시험(합성 · 실측 아님)
최종 **17/17 PASS**(`TEST-RESULT.json`).
| 묶음 | 시험 |
|---|---|
| 체결 분류 | 확정 · 취소 · 미체결(0 · 빈칸) · 같은 주문 재전달 1회 · 합계가 다른 중복 중단 · 부분체결 2건 합 · 반대 side 같은 시각 표시 |
| 누락 · 형식 | 평균가 빈칸/0 · 주문번호 없음 · side 03 · 날짜 7자리 · 잘못된 시각 · 종목코드 없음 거부, 맥락 누락은 null + 개수 |
| 의미 일치 | 같은 합성 행에서 `predash.trades.normalize_kis`와 (시각 · 종목 · side · 수량 · 가격 · 금액) 목록이 같음 |
| 비밀 | HMAC id가 같은 키에서 같고 다른 키에서 다름 · 출력에 원 주문/지점 번호 없음 · 키 없거나 짧으면 거부 · CLI가 키 없이/작업트리 안으로는 파일을 만들지 않음 · 공개 출력 금지 키/계좌 꼴/큰 숫자/허용 밖 필드 주입을 모두 잡음 |
| 측정 | 3일 손셈(매수 · 입금 · 매도 · 실제 비용)과 TWR · NAV · MDD 일치, 둘째 날 평가 손실이 MDD로 잡힘(매매 끝난 날 기준이면 0으로 숨는 경우) · 하루 정확히 −15%는 경보 아님 / 84.99는 경보 · 달 정확히 −15%는 아님 / 넘으면 경보 · 평가 누락은 그날과 뒤가 null · 분할 기록이 있으면 0%, 없으면 −50%로 보임 · 보유보다 많이 판 날 IMPOSSIBLE · 비용 누락 날 null · 미끄러짐 bps와 기준가 없으면 null · 기간 밖 체결 거부 |

- **첫 실행은 15/17**이었습니다(`TEST-RESULT.run1.json`).
  1. 날짜 `2026101`(7자리)이 다른 날로 읽혀 통과 → 도구를 고침(8자리 · 6자리만 받음, predash보다 엄격).
  2. 비용 bps 비교 허용치가 공개 출력의 소수 4자리 반올림보다 좁음 → 시험 허용치를 고침.
- 결함 주입 시험은 예산(합성 시험 묶음 1회) 때문에 따로 돌리지 않았습니다.
- 공개 전 비밀 검사(PRIVACY-0001 `guard.py`): 산출물 11개 PASS. `tests/test_measure.py` 1개만 5건이 걸렸습니다(`order_no` 2 · `odno` 1 · `access_token` 1 · `raw_response` 1). 모두 검사기가 잡는지 보려고 일부러 넣은 합성 키이고, 값은 `T…` · `x` · 변수입니다. 검사를 피하려고 고치지 않았습니다.

## 5. 실제 측정을 시작하려면(사용자 로컬에서만)
1. 저장소 밖 폴더에 KIS 체결 원문 행(`rows.json`)과 맥락(`context.json`: 상품 · 시장 · 전략 · 비용 · 기준가), 시작 상태 · 평가가격 · 입출금 · 기업행동 파일을 둡니다.
2. 16바이트 이상 키를 환경변수 `PAPER_MEASURE_HMAC_KEY`로만 줍니다(저장소 · 채팅에 넣지 않음).
3. 명령은 `DATA-STATUS.json`의 `safe_local_commands` 그대로입니다. 공개 저장소에 올리는 것은 마지막 공개 JSON 하나뿐입니다.
- 원 주문번호 · 계좌번호는 공개 출력에 필요하지 않습니다(비공개 HMAC 중복 제거에만 로컬에서 씀).

## 6. 공개 노출 발견(값 없이)
- `idle-live/paper-orders.json`에 원 모의 주문번호 1개(주문 2건 중 1칸). 커밋 `6a36a61c`(2026-10-07)부터 이력에 있습니다. 같은 파일에 절대 수량 칸 3개가 있고, `idle-live/today.json`에도 1개 있습니다. 계좌번호 꼴 · 토큰은 0개입니다.
- 삭제 · 이력 수정 · 키 교체는 하지 않았습니다. 권장 조치는 `PRIVACY-FINDINGS.md`에 있습니다.

## 7. 남은 결손
- 실제 체결 원문 · 시작 상태 · 일별 평가 · 입출금이 없음 → WAITING_DATA(실측 지표 0개).
- 체결 시각은 주문 시각 하한뿐 → 같은 날 체결 순서 · 장중 미끄러짐은 판단 못 함.
- 현금배당은 미지원(입력 계약 밖) · 세금 원 미만 처리 미확인(COST-REPLAY B5).
- 1천만 / 1억 용량은 비공개 수량 · 호가/ADV · 체결 괴리가 생긴 뒤에만 계산합니다.

## 다음 방향
- next_trigger는 고정했습니다. 사용자가 로컬에서 공개 비식별 배치를 만들어 올리기 전까지 후속 연구 · 감사 · 알파 TASK를 만들지 않습니다.
- 운영 장부의 원 주문번호 저장 방식을 HMAC이나 저장소 밖으로 바꿀지는 별도 승인으로 정하면 됩니다.
