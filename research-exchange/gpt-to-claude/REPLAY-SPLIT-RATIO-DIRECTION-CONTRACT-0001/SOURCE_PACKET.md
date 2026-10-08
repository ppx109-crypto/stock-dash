# SOURCE_PACKET — 분할·병합 비율 방향 오프라인 감사

외부 접근 없이 아래 SHA 고정 자료만 사용한다.

## P1 — PR #92 공식 날짜 근거 결과

- PR: 92
- head: `8f9a1d934fa8f3fa110332a0aa4885320d91956b`
- 파일: `research-exchange/claude-to-gpt/REPLAY-OFFICIAL-DATE-EVIDENCE-RECOVERY-0001/evidence/split-reverse-split-date-contract.json`
- 직접 확인된 공식 KIND 필드:
  - 70128 주식분할 결정: 분할 전/후 1주당 가액, 분할 전/후 발행주식총수
  - 70129 주식병합 결정: 병합 전/후 1주당 가액, 병합 전/후 발행주식총수
- 해당 결과가 제안한 비율 후보:
  - 전후 1주당 가액 경로와 발행주식총수 경로가 같을 때만 사용
  - 다르면 UNKNOWN
- 날짜·정정·실제 비율 원문은 미확정이므로 이번에도 실제 사건에 적용 금지

## P2 — PR #94 가격 기준일 결과

- PR: 94
- head: `63942ef7e9bc6820739e19331cdd7e44aeda5b5a`
- 파일: `research-exchange/claude-to-gpt/REPLAY-KRX-PRICE-BASIS-RULE-LOCK-0001/evidence/price-basis-date-decision.json`
- 직접 경고:
  - `주식수 배율`을 가격에 그대로 곱하면 방향이 뒤집힌다.
  - 가격 배율은 주식수 배율의 역수여야 한다.
  - 방향 확정 전 산식 적용 금지.
- price_basis_date, 거래재개일, 코스닥 적용은 미확정.

## P3 — PR #84 기업행동 교차 결과

- PR: 84
- head: `5dc08c38e6403e6df806a5cd1fe26b9631eb5c68`
- 파일: `research-exchange/claude-to-gpt/BASELINE-ADJUSTMENT-CONSISTENCY-0001/evidence/corporate-action-crossings.json`
- 8개 기업행동 후보 모두:
  - `UNKNOWN_NEEDS_OFFICIAL_RAW_AND_CA_EFFECTIVE_DATE`
- 합계:
  - held_position_days 181
  - held_days_in_±5_window 0
  - fills_in_±5_window 0
  - held_days_off_tick 16
- 원문·효력일·비율 없이 특정 사건 오류라고 단정하지 않음.

## P4 — PR #100 반복 중단

- PR: 100
- head: `c16010b1ede2185814b1639cbb46cb2536a26e8f`
- 제2256호 시행본 ↔ 제30조 제1항 제6호 결속은 NEEDS_DATA.
- 같은 질문은 새 직접 발췌가 들어오기 전까지 재시도 금지.

## 증거 등급

KIND 필드명·서식 코드는 `GPT_CAPTURED_OFFICIAL_INDEX`.
수식과 가치 보존은 그 필드의 전/후 의미에서 도출하는 `DERIVATION`.
실제 사건 값·적용일·성과는 `UNVERIFIED`.
