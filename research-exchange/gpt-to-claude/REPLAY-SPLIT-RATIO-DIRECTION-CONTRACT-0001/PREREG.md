# 사전등록 — REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001

판정 전에 아래 축을 고정한다.

## 고정 입력

- source PR #100 head `c16010b1ede2185814b1639cbb46cb2536a26e8f`
- PR #92 evidence: KIND 70128/70129에 분할/병합 전후 1주당 가액과 발행주식총수 필드 존재
- PR #94 evidence: 주식수 배율을 가격에 그대로 곱하면 방향 역전 가능
- PR #84 evidence: 8개 기업행동 후보 모두 공식 원주가·효력일·비율 없이 UNKNOWN

## 고정 수식

양수·유한·누락 없음일 때만 계산한다.

- `m_qty = q1/q0`
- `m_face = f0/f1`
- 검증: `m_qty == m_face`
- `m_price = 1/m_qty = q0/q1 = f1/f0`

허용 오차를 임의로 정하지 않는다. 정수·유리수로 정확 비교 가능한 입력만 ACCEPT한다.
실제 공시 숫자의 반올림/단위가 불명확하면 UNKNOWN이다.

## truth table 기대

- split: `m_qty > 1`, `0 < m_price < 1`
- reverse_split: `0 < m_qty < 1`, `m_price > 1`
- `m_qty = 1`: split/reverse_split로 ACCEPT하지 않음
- 방향과 KIND 사건명이 모순되면 BLOCKED/UNKNOWN, 값을 뒤집어 맞추지 않음

## 가치 보존

단주·세금·비용·현금보상·반올림 전:
`qty_before × price_before = qty_after × price_after`.

이 등식은 방향 검산용이며 실제 체결 가능성, 기준가격 적용일, NAV 유효성을 증명하지 않는다.

## 상태

- 계약이 모순 없이 재현되고 fail-closed가 완전하면 READY
- 직접 필드 방향 부족, 수식 모순, 기존 코드가 반대 방향인데 수정 범위가 불명확하면 BLOCKED

READY는 회계 계약 준비 상태일 뿐 실제 재생/성과/PAPER_VALIDATION_READY가 아니다.
