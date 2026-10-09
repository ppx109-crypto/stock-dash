# BASELINE-ADJUSTMENT-CONSISTENCY-0001 — 클로드 사전등록(계산 전)

- 입력: GPT PR #83 head `8c13268f`(REVIEW · TASK · receipt) · source PR #82 `c18f10d4`
- 일: PR #82의 off-tick 저장가격 74/747이 신호 · 모의 진입/청산 · 비용 notional · 보유 중 MTM · 기업행동 전후 수량/현금에 닿은 범위를 셉니다.
  - 성과 · NAV 재실행, 영향 금액 · 수익률 추정, 외부 API · 네트워크 · Actions는 없습니다.

## 1. 입력(PR #82 manifest 해시와 대조 · 모두 일치)
| 입력 | sha256 |
|---|---|
| PR #68 control_trades.json | `880a277bad0fa0eaebd34cdd9dc9c7acab9a4d4c511f97570e488190c5561ad3` |
| PR #74 signals_old.json | `0625d2a84c6aac796f2ba9a03f9bd11e55596a4d1261a78990f5c3389c1a7a7d` |
| PR #76 fixed_local_only.json(일봉 고침 원장) | `0619fd234ef9386e419d3641add36b62acee8f03b848896da9e0e19a781e51d8` |
| 옛 nrl-cache.pkl | `84030fcf259288dc4e0c698f7694a99a8231f49d5ca0e726380ec443dcb94560` |
| PR #68 nav_control_candidate.csv(경로 B: 통제 NAV) | `2c3b4bceccf7a5f45fe0f46e0197dac437bca8dbe5c56c6e71e23acfef1577b1` |
| PR #76 nav_train_control_old_fixed.csv(경로 B: 고친 후보 NAV) | `007cebe625b316102df01f31acaf31a363bc60a541ce092871d0afbbc3107137` |
| PR #82 tick_check.py · tick-check.json | `2be9df1fe2377f45228261f5c626bf5a653035dd23390dd089912e8ebe604dbd` · `6166b3eafd055730aa9b41c93843453e19d36eb727e202b507fc9f5d31aa785b` |
| salt(로컬 · 공개는 salt sha256) | `eb7b7d0859a3a81b83e18f49d78248b697089fc286096655938908408d08e4eb` |
| 자료 스냅샷 b2(dart-events · kosdaq-data · 비용식 ADV) · git 판 이력 | `00b98ab1655c84806357f44f2de6f1509ef1447f` |
| code/pa_audit.py | `b7fb8f76133a2ec2e1a091aa046aaed05bbae489aef6e15d563d7af12eef1612` |
| code/kernel2.py · cost_contract.py(PR #68과 같음) | `a1b0802865656ed98eaf98bd347f0c174d8895f26d97bd85836cfcebf6ae80ac` · `c8c006c10fead5db60861f89c8e50304dfe9918c03ce11c32c74beec3496aaae` |

## 2. 분모 747 재구성
- (종목, 날짜) 합집합 · 중복 제거입니다. 범위는 2025-09-18 ~ 2026-03-31입니다.
  - D1 신호 줄(signals_old picks)
  - 통제 D1 · 바구니 체결(PR #68)
  - 고친 후보 D1 · 바구니 체결(PR #76)
- 747 · off-tick 74가 재현되지 않으면 BLOCKED입니다(코드 assert).
- 원장 범위: **통제(PR #68) · 고친 후보(PR #76) × D1 · 바구니.**
  - 옛 후보는 baseline에서 버린 것이라 뺍니다.
  - 15분봉은 747 분모 밖(봉 가격)이라 뺍니다.

## 3. off-tick 판정
- PR #82 `tick_check.py`와 같은 호가표(2023-01-25 뒤): <2천 1 · <5천 5 · <2만 10 · <5만 50 · <20만 100 · <50만 500 · 그 위 1000
- 값 ÷ 호가가 정수가 아니면(허용 1e−9) off-tick입니다.

## 4. 역할 매핑(레코드 (c, d)마다 · 비배타)
- signal: (c, d)가 D1 신호 줄
- entry / exit: 범위 원장에 (c, d) 매수 / 매도 체결
- fee_tax_notional: (c, d)에 체결이 하나라도 있음(비용 · 세금은 수량 × 그 가격으로 셈 — kernel2 Costs.rate)
- open_position_mtm: 그날 마감에 범위 원장 중 하나가 c를 보유(그날 MTM에 그 종가를 씀)
- ca_window: c가 기업행동 공시 종목이고, d가 Train 안 저장 공시일 ±5 거래일 안(탐색 표시 · 원인 확정 아님)
- 배타 묶음(합 74): 신호에만 / MTM에만 / 체결에 사용 / 둘 이상(체결 없음) / 역할 없음. 조합 교차표도 냅니다.

## 5. 독립 분모
- 가격 레코드 74
- 그 위 체결(원장 · 소계정 · 방향별)과 고유 (종목, 날)
- 포지션-일(원장 · 소계정별)
- 범위 안 모든 체결(유효성 분모)
- 원장 · 소계정별 전체 포지션-일 가운데 off-tick MTM 포지션-일(보조 분모 · 74 밖 포함)

## 6. 판정 규칙
- **체결:** off-tick 체결가 → `IMPOSSIBLE_RAW_FILL`. on-tick → `UNKNOWN_RAW_OR_ADJUSTED`. 가격 없음 · 매핑 불가 → `UNKNOWN_MISSING_MAPPING`.
  - 통제 체결가는 원장 가격 칸입니다. PR #76 체결가는 그날 저장 종가입니다(그 재생 코드 규칙).
- **원장 회계(원장 · 소계정별):**
  - 경로 A: 원장 직접 재구성(현금 · 수량 · 비용식, PR #76은 매수 묶음별 매도 비용)
  - 경로 B: 저장 NAV CSV
  - 날마다 차이 ≤ 1원, `기말현금 = 기초 − 매수대금 + 매도대금 − 비용`(조정 0), `기말수량 = 기초 + 매수 − 매도`(음수 0)이면 `INTERNAL_CONSISTENCY_PASS`. 아니면 `INTERNAL_INCONSISTENCY_PROVED`.
  - 명시적 기업행동 조정 레코드 수를 함께 적습니다.
- **기업행동 종목(실제 보유구간):** 아래를 셉니다.
  - ±5 거래일 창과 겹친 포지션-일 · 체결
  - 보유일 종가 전일 대비 ±30% 넘음(가격제한 밖 = 기계적 재배율 흔적)
  - git 판 사이 값 바뀜
  - 거래 없는 수량 · 현금 변화
  - 판정: 보유 없음 `NOT_HELD_IN_TRAIN`, 그 밖 `UNKNOWN_NEEDS_OFFICIAL_RAW_AND_CA_EFFECTIVE_DATE`
  - 원장 회계가 깨지면 `INTERNAL_INCONSISTENCY_PROVED`
  - 공식 효력일 · 비율 없이 특정 사건 오류라고 단정하지 않습니다.
- 영향 금액 · 수익률은 추정하지 않습니다.

## 7. 출력 · 상태
- `evidence/off-tick-role-coverage.json` · `fill-validity.json` · `position-accounting.json` · `corporate-action-crossings.json` · `run.log`
- 종목은 salted hash, 그 밖은 개수 · 비율만 씁니다.
- READY: 74 · 747 재현 + 위 판정 완료
- BLOCKED: 입력 해시 불일치 · 필수 필드 없음 · 74 재현 실패
- 버그 수정이 필요하면 첫 결과를 남기고, 사유 · 전후 해시 · 재실행 횟수를 적습니다.
