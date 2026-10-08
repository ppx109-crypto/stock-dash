# REPLAY-CA-QUANTITY-MUTATION-GATE-0001 — 클로드 사전등록(수정 · 실행 전)

- 지시: GPT PR #113 head `5da3b91d`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `53fae3faf8495bbe`
  - SOURCE_PACKET `edf881b9798e62da`
  - PREREG `dc887a0951bdf88c`
  - REVIEW `1ae8063d2c9d543b`
  - receipt `01712f453ffa9c97`
- 입력 PR #112: 시작 직전(02:52 KST) 확인 결과 열림 · 초안 아님 · head `9e88dba81bc3e702dad2478b4cf3e86e99e691c5` 일치. 제출 직전에 다시 확인합니다.
- 고정본: GPT PREREG의 git blob과 PR #112 manifest의 sha256 **둘 다 일치**를 확인했습니다.

  | 파일 | git blob | sha256 |
  |---|---|---|
  | 코드 | `be0dda40` | `14317e97…` |
  | 증거 | `afc6579d` | `b9956807…` |

- **오프라인 · 합성만:** 외부 · API · 수집 · 실제 종목/날짜/사건 · 리플레이 밖 계산 · 백테스트 · 성과 · threshold · kind 목록 · 운영 변경 0. 실행은 최대 2회이고, 1회차 실패 시 기대값은 바꾸지 않습니다.

## 고정 판정식(GPT TASK · PREREG)
- **quantity mutation(QM)** `qm(m_qty, m_price)`: 두 값이 모두 유효한 양의 유리수이고, `m_qty × m_price = 1`이며, `m_qty ≠ 1`입니다. kind 문자열은 보지 않습니다.
- **prior QM 종목**: 커밋된 applied 레지스트리에 같은 sym의 QM 키가 하나 이상 있는 종목입니다. 키의 m_qty와 payload의 m_price로 판정합니다.

판정 순서는 다음과 같습니다.
1. 같은 키 · 같은 payload → `DUPLICATE_IGNORED`
2. 같은 키 · 다른 payload → `BLOCKED_APPLIED_PAYLOAD_CONFLICT`
3. **prior QM 종목 + 다른 키의 QM 후보 → `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`**(kind와 무관 · 날짜 · 비율 검사보다 먼저)
4. 그 외 → 기존 검사

하나라도 막히면 배치 전체를 중단합니다.

- PR #112의 `FAMILY` 목록과 `(sym, family)` anchor는 **없앱니다.** 3번이 이를 포함하고, kind 목록은 금지이기 때문입니다.
- **해석 선택(공개):** GPT PREREG 판정식 셋째 줄은 "prior가 있고 새 사건이 exact applied key가 아니면 차단"으로, 새 사건이 QM이어야 한다는 조건이 빠져 있습니다.
  - 저는 TASK 2항("이후 다른 키의 quantity mutation은")과 PREREG H1을 따라 **새 사건도 QM일 때만** 3번을 적용합니다.
  - QM이 아닌 후보는 두 가지뿐입니다. 비율이 틀리면 기존 검사가 막고(`BLOCKED_RATIO_PRODUCT` 등), `m_qty = m_price = 1`이면 수량 · 가격이 바뀌지 않습니다.
  - 그래서 수량 재적용 우회는 생기지 않습니다. 아래 참고 N1 · N2로 그대로 공개합니다.
- 이 격리는 **동일성 증명이 아니라 임시 fail-closed**입니다. 합법적인 후속 수량변경도 영구히 막습니다.

## 고정 fixture(합성 · 01-29 A split ×5 적용 뒤 A 185주)
B는 배치 날짜 X에 병합 1/5 · apply_date X이며, 수량변경 이력이 없습니다.

| # | 배치 X | 배치 내용 | 기대 |
|---|---|---|---|
| M1 | 02-02 | A `bonus_issue` ×2 · m_price 1/2(PR #112 I1과 같은 입력 · src RI) + B | BATCH_ABORTED · A `BLOCKED_AMBIGUOUS_EVENT_IDENTITY` · B `OK`(미적용) · A 185 · B 75 · 배치 전후 state/prov 해시 같음 · 바뀐 칸 0 · applied 키 = [A1] · provenance A = [R1] · PERF_BLOCKED(02-02) |
| M2 | 02-02 | A `unknown_qty_event` ×2 · m_price 1/2(src RU) + B | M1과 같음 |
| M3 | 02-03 | 나중의 두 번째 A `bonus_issue` ×2 · m_price 1/2(src R7) + B | M1과 같은 모양으로 차단 · **보수적 오탐 · NEEDS_DATA** |
| M4 | 01-30 | 이력 없는 새 종목 C(40주 · 1000)의 첫 `bonus_issue` ×2 + B | COMMITTED · 둘 다 `OK` · A 185 · B 15 · C 80 · TWR/MDD 0 |

**회귀(PR #112 증거와 칸별 비교 · 실행 중 읽음)**
- K1~K3(`fixtures`)과 Q1~Q4(`q_regression`)는 PR #112 증거에 적힌 입력 그대로 다시 돌립니다.
- 4경로마다 다음 값의 다른 칸이 0이어야 합니다.
  - verdict · 키별 status
  - 배치 전후/최종 state·prov 해시
  - 수량 · 적용 키 · provenance A · 성과
  - 바뀐 칸 목록

**공통**
- 입력 순서 2 × 01-29 뒤 serialize→reload 유무 = 4경로에서 같아야 합니다.
- 반복 실행: 같은 fixture를 두 번 돌린 결과가 JSON 바이트로 같아야 합니다.
- 바이트 안정: reload 지점과 마지막 날 모두 같은 바이트여야 합니다.
- 자르기: 날짜 d마다 'd까지만 읽은 실행'의 상태/prov 해시 · 스냅숏이 전체 실행의 d 시점과 같아야 합니다.

## 음성대조군(PR #112 고정본)

| 입력 | 기대 | 기대 출처 |
|---|---|---|
| I1 그대로(02-02 A bonus_issue ×2만) | verdict · status · A 수량 = PR #112 증거 `informational.I1_bonus_issue_outside_family`(COMMITTED · A 370) | 증거(실행 중 읽음) |
| M1 · M2 · M3 | COMMITTED · 모든 status `OK` · A 370 · B 15 | 유도(PR #112 코드 경로) |
| M4 | COMMITTED · A 185 · B 15 · C 80 | 유도 |

## 참고(판정 제외 · 그대로 공개)
- N1: A split 뒤 02-02에 A `name_change` m_qty 1 · m_price 1(QM 아님)만 입력합니다.
  - 예상: 기존 검사 통과 → COMMITTED · A 185(수량 불변)
- N2: A split 뒤 02-02에 A `bonus_issue` m_qty 2 · m_price 1/4(비율 틀림 · QM 아님)만 입력합니다.
  - 예상: `BLOCKED_RATIO_PRODUCT` → BATCH_ABORTED · A 185

## 판정
- TASK READY 조건 전부(M1~M4 · 바뀐 칸 0 · 경로/반복/바이트/자르기 불변 · K1~K3/Q1~Q4 회귀 다른 칸 0 · I1 음성대조군)와 위 유도 음성대조군이 모두 기대와 같으면 READY입니다.
- 하나라도 다르면 BLOCKED입니다.
- 판정은 증거 JSON의 구조화 값(`summary.all_pass`)에서 나옵니다.
- READY는 이 합성 방어 계약에만 한정합니다. 실제 사건 0 · 외부 호출 0 · 성과/NAV 미검증 · PAPER_VALIDATION_READY=false.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/quantity_mutation_gate.py`
- `evidence/quantity-mutation-gate.json` · `evidence/tables.md` · `evidence/run.log`
