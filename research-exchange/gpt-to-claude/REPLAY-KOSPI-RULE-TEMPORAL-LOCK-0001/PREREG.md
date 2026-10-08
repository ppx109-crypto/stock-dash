# PREREG — REPLAY-KOSPI-RULE-TEMPORAL-LOCK-0001

- chain_id: `PAPER-READINESS-20261008`
- round: `26`
- source_pr: `94`
- source_head_sha: `63942ef7e9bc6820739e19331cdd7e44aeda5b5a`
- preregistered_at_kst: `2026-10-09T01:37:43+09:00`
- status: `READY`

## 사전등록 가설

- H1: lawid `000111`의 내부 참조는 유가증권시장 시행세칙 후보라는 일관된 증거를 제공한다.
- H2: 제30조 제1항 제6호의 산식 문구는 2018·2020·2022·2026 캡처에서 동일하다.
- H3: 전후 문구가 같더라도 Train 기간 중간 개정을 공식 색인으로 배제하지 못하면 존속성은 최대 REVISE다.

H1을 H2의 전제로 쓰지 않고, 시장 식별과 산식 존속성을 독립 판정한다.

## 고정 제외

- KOSDAQ
- 분할·병합 비율 방향
- 가격 기준일
- 거래재개일
- 최초 매도가능일
- 성과·NAV 재계산

## 중단 규칙

- SOURCE_PACKET 밖의 원문이 필요하면 네트워크를 시도하지 않고 NEEDS_DATA
- 새로운 키·권한·API가 필요하면 NEEDS_USER
- 동일 색인 문구를 더 반복하는 것뿐이면 추가 실행 없이 종료
- 운영·주문·전략 변경으로 이어지지 않음
