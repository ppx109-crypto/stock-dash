# REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001 — 분할 · 병합 비율 방향 회계 계약

- 지시: GPT PR #101 head `d0313d20`
- 입력 PR #100 head `c16010b1`: 열림 · 초안 아님. 시작 직전 · 제출 직전 2회 확인했습니다.
- 사전등록: 커밋 `a22e9fb2`(2026-10-09 02:05 KST, 계산 · 코드 검색 · 판정 전)
- **status: READY** — 회계 계약 준비 상태일 뿐입니다.
  - 어느 실제 사건에도 적용하지 않았습니다. 적용일(price_basis_date)이 BLOCKED라 적용 게이트가 막습니다.
  - +19.90% · NAV · PAPER_VALIDATION_READY는 그대로 미검증입니다.
- 오프라인 1회입니다.
  - 외부 URL · 네트워크 · API · 키 · 수집 · 캐시 0
  - 실제 종목 · 원시 공시 · 계좌자료 열람 0
  - 리플레이 · 백테스트 · 성과 · NAV 0
- 실행 코드: `code/ratio_contract.py`. Fraction으로 정확히 계산하고 허용 오차는 없습니다. 네트워크 함수를 막았고, 코드 감사는 로컬 git grep만 씁니다.

## CLAIM / CODE / MEASUREMENT 구분
| | 내용 | 등급 |
|---|---|---|
| CLAIM | KIND 70128 · 70129에 전/후 1주당 가액 · 전/후 발행주식총수 필드가 있다(PR #92) | GPT_CAPTURED_OFFICIAL_INDEX |
| CODE | 아래 계약 · 전환 · 적용 게이트(`ratio_contract.py`) | DERIVATION |
| MEASUREMENT | 합성 15건 검산 · 코드 방향 감사(로컬 git) | 합성 · 실제 종목 아님 |
| 실제 사건 비율 · 적용일 · 성과 | 하지 않음 | UNVERIFIED |

## 1. 계약(사전등록 수식 그대로)
- 기호
  - `q0, q1` = 전/후 발행주식총수
  - `f0, f1` = 전/후 1주당 가액
  - `m_qty = q1/q0`
  - `m_face = f0/f1`
  - `m_price = 1/m_qty = q0/q1 = f1/f0`(코드 assert로 세 식이 같음을 확인)
- **ACCEPT 조건:** 양수, 정수 또는 유리수, 누락 없음. 그리고 `m_qty == m_face`(정확), `m_qty ≠ 1`, 사건명과 방향이 일치해야 합니다.
- 두 경로는 서로 독립입니다. 주식 수 경로와 액면 경로가 정확히 같을 때만 비율 방향을 받아들입니다.

## 2. Truth table
| 사건 | m_qty | m_price | 보유 수량 | 가격 |
|---|---|---|---|---|
| split | > 1 | 0 < · < 1 | 증가 | 감소 |
| reverse_split | 0 < · < 1 | > 1 | 감소 | 증가 |
| m_qty = 1 | — | — | — | `UNKNOWN_NO_CHANGE` |
| 사건명 ↔ 방향 모순 | — | — | — | `UNKNOWN_DIRECTION_CONTRADICTION`(값을 뒤집어 맞추지 않음) |

- ACCEPT된 합성 5건 모두 이 표와 일치합니다.

## 3. 합성 검산(실제 종목 아님) — 15/15 기대와 같음
| 사례 | q0 → q1 | f0 → f1 | m_qty | m_price | 보유 전환 | 결과 |
|---|---|---|---|---|---|---|
| 분할 1:5 | 1,000,000 → 5,000,000 | 5,000 → 1,000 | 5 | 1/5 | 37주 @52,300 → 185주 @10,460 | ACCEPT · 가치 1,935,100 보존 |
| 분할 1:10 | 2,400,000 → 24,000,000 | 500 → 50 | 10 | 1/10 | 3주 @812,000 → 30주 @81,200 | ACCEPT · 보존 |
| 병합 10:1 | 12,345,670 → 1,234,567 | 100 → 1,000 | 1/10 | 10 | 120주 @1,234 → 12주 @12,340 | ACCEPT · 보존 |
| 병합 5:1 | 50,000,000 → 10,000,000 | 200 → 1,000 | 1/5 | 5 | 75주 @905 → 15주 @4,525 | ACCEPT · 보존 |
| 단주 발생 | 병합 10:1 | | 1/10 | 10 | 7주 → 0.7주 | `UNKNOWN_CASH_IN_LIEU` · 적용 안 함 |
| 두 경로 불일치 | 주식 수 ×5 · 액면 ×10 | | | | | `UNKNOWN_RATIO_MISMATCH` |
| **병합 뒤 1주 어긋남** | 12,345,678 → 1,234,567 | 100 → 1,000 | | | | `UNKNOWN_RATIO_MISMATCH` |
| 0 · 음수 · 누락 · NaN · 부동소수 | | | | | | 각각 `UNKNOWN_ZERO` · `_NEGATIVE` · `_MISSING` · `_NONFINITE` · `_FLOAT_INPUT` |
| 변화 없음 | 같음 | 같음 | 1 | | | `UNKNOWN_NO_CHANGE` |
| 사건명 모순 2건 | split인데 감소 · reverse인데 증가 | | | | | `UNKNOWN_DIRECTION_CONTRADICTION` |

## 4. 가치 보존(단주 · 비용 · 현금보상 전)
- `qty_after × price_after = (qty × m_qty) × (price × m_price) = qty × price × (m_qty × m_price) = qty × price`
- `m_price = 1/m_qty`이므로 유리수 등식으로 성립합니다. ACCEPT 4건 모두 코드가 정확한 등식을 확인했습니다.
- 이 등식은 **방향 검산용**입니다. 체결 가능성 · 기준가격 적용일 · NAV 유효성을 증명하지 않습니다.
- **반대 방향 오류의 크기(PR #94 경고 재현):** 분할 1:5에서 가격에 주식수 배율(5)을 곱하면 가격이 52,300 → 261,500이 됩니다. 185주 평가액은 **25배**로 부풀어 가치 보존이 깨집니다.

## 5. fail-closed(아무 회계 · NAV에도 적용 안 함)
- 입력 문제: `UNKNOWN_MISSING` · `UNKNOWN_ZERO` · `UNKNOWN_NEGATIVE` · `UNKNOWN_NONFINITE` · `UNKNOWN_FLOAT_INPUT` · `UNKNOWN_TYPE`
- 비율 문제: `UNKNOWN_RATIO_MISMATCH` · `UNKNOWN_NO_CHANGE` · `UNKNOWN_DIRECTION_CONTRADICTION`
- 보유 문제: `UNKNOWN_CASH_IN_LIEU`(단주 처리 규칙을 추정하지 않음)
- **적용일 미확정:** `APPLY_BLOCKED_NO_PRICE_BASIS_DATE`
  - 계약이 ACCEPT여도, PR #94의 price_basis_date가 BLOCKED이므로 적용 게이트가 막습니다(코드로 확인).
  - 분할 · 병합 종목은 계속 정지 시작일부터 NAV 무효입니다.

## 6. 기존 코드 · 문서 방향 감사(읽기 전용 · `evidence/code-direction-audit.json`)
- 범위: `origin/main`(운영 + 연구) · PR #86 · PR #88 연구 복사본
- 원시 일치 1,399줄은 대부분 `str.split` 같은 무관 항목입니다. 비율 사용처만 분류했습니다.

| 위치 | 문구 | 방향 |
|---|---|---|
| PR #86 `raw_replay.py:113` | `new = q[c] * e["ratio"]` | 수량 × 수량 배율 — **올바름** |
| PR #88 `raw_replay_v2.py:266` | `new = Fraction(q[c]) * Fraction(str(e["ratio"]))` | 수량 × 수량 배율 — **올바름** |
| PR #86 · #88 스키마 `ratio` 설명 | "기존 1주당 효력 후 주식 수" | = `m_qty`(가격 배율 아님) |
| main `tests/test_fix_recent_days.py:43` | `"종가": c / 2`(액면분할) | 가격 × 역수 — **올바름** |
| main `research/e002.py:5` | '목표가 ÷ 수정 종가' 급변으로 재배율 | 분할 비율을 쓰지 않음 — 무관 |

- **가격 × 주식수 배율(반대 방향): 0건.** 운영 코드에서는 분할 비율을 계산에 쓰는 곳 자체가 없습니다(주석 · 수정주가 설명뿐).
- 연구 어댑터들은 원주가를 그대로 쓰고, 가격을 비율로 바꾸지 않습니다.
- 다만 이 감사는 정규식 기반이라 모든 표현을 잡는다고 보장하지는 않습니다. 분류 규칙은 코드에 있습니다.
- KIS `prtt_rate`('분할 비율')는 값 방향이 미확인(PR #90 NEEDS_DATA)이라 이 계약에 쓰지 않습니다.

## 7. 보완 · 반박 — 정확 비교 규칙의 대가
- 액면 경로(f0/f1)는 보통 정수 액면(예: 5,000 → 100)이라 정확합니다.
- 그런데 주식 수 경로(q1/q0)는 **병합 때 회사 단위 단주 처리로 1주만 어긋나도** 정확 비교에서 떨어집니다(합성 '병합 뒤 1주 어긋남').
- PR #92의 분할 예시도 '발행주식총수 정정'이 있었습니다.
- 그래서 실제 병합 공시 상당수가 이 규칙으로 UNKNOWN이 될 수 있습니다.
- 안전 쪽(fail-closed)이지만 적용 범위가 줄어듭니다. 허용 범위(예: 단주로 설명되는 차이)를 둘지는 이번 범위 밖이며 별도 사전등록이 필요합니다.

## 8. 유지
- PR #84의 8개 기업행동 후보: 모두 `UNKNOWN_NEEDS_OFFICIAL_RAW_AND_CA_EFFECTIVE_DATE`(공식 원주가 · 효력일 · 실제 비율 없음) 그대로
- price_basis_date · 거래재개일 · 최초 매도가능일 · KOSDAQ: 미확정
- 제2256호 ↔ 제30조 결속: NEEDS_DATA로 정지(재시도 안 함)
- +19.90% · NAV · PAPER_VALIDATION_READY: 미검증 · false

## 실행 계수
- 오프라인 실행 1회 · 실패 0
- 외부 URL 0 · API 0 · 키 0 · 수집 0 · 캐시 0 · 리플레이 0 · 백테스트 0 · threshold 0 · 성과 0 · 운영 변경 0 · 새 세션 0 · 자동병합 0

## 다음 방향
- 이 계약은 실제 분할 · 병합 공시 값(전후 가액 · 발행주식총수)과 적용일이 들어와야 쓸 수 있습니다. 둘 다 아직 막혀 있습니다.
- 다음으로 독립 검증할 수 있는 빈칸은 '병합 시 단주로 설명되는 주식 수 차이'를 허용할 근거를 정하는 것, 또는 정정 공시 사슬입니다.
