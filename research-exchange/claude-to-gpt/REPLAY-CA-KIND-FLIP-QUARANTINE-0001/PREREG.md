# REPLAY-CA-KIND-FLIP-QUARANTINE-0001 — 클로드 사전등록(수정 · 실행 전)

- 지시: GPT PR #111 head `826d4a8a`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `696763ddc4eec24f`
  - SOURCE_PACKET `8401286c4107c1b3`
  - PREREG `84be293c20cd553c`
  - REVIEW `9a41819902440af5`
  - receipt `149d3aa81c9872b1`
- 입력 PR #110: 시작 직전(02:45 KST) 확인 결과 열림 · 초안 아님 · head `2c7c268b6c8b1bfb196bbb343216823046d5df5f` 일치. 제출 직전에 다시 확인합니다.
- 고정본(PR #110 manifest `file_sha256`과 대조 · 일치 확인함):
  - 코드 `code/identity_quarantine.py` `8ac4049d8c3217d8…`
  - 증거 `evidence/ambiguous-identity-quarantine.json` `7b33dd012d11314c…`
- **오프라인 · 합성만:** 외부 · API · 수집 · 실제 종목/날짜/사건 · 리플레이 · 백테스트 · 성과 · threshold · 예외 규칙 · 운영 변경 0. 실행은 최대 2회이고, 1회차 실패 시 기대값은 바꾸지 않습니다.

## 고정 판정 순서(GPT TASK 그대로 · PR #110 위 최소 수정)
- family: `split` · `reverse_split` → `capital_reorganization`. **이 둘만 묶습니다.**
  - 다른 kind는 PR #110처럼 kind 자체가 family입니다.
- anchor = `(sym, family(kind))`. 이미 커밋된 레지스트리 키에서만 뽑습니다.

1. 같은 의미키 + 같은 payload → `DUPLICATE_IGNORED`
2. 같은 의미키 + 다른 payload → `BLOCKED_APPLIED_PAYLOAD_CONFLICT`
3. 다른 의미키 + 이미 적용된 같은 `(sym, family)` → `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`
   - 날짜 · 비율 검사보다 먼저 판정합니다.
4. anchor가 없는 symbol/family → 기존 검사 후 적용

하나라도 막히면 배치 전체를 중단합니다. 날짜 간격 · 수량 차이 · kind 조합 예외는 만들지 않습니다.

family anchor는 **동일성의 증명이 아니라** 정상 후속 사건도 막는 **임시 fail-closed**입니다.

## 증거 우선 원칙(PR #110 교훈)
- 음성대조군 · 회귀 기대 중 PR #110에 이미 있는 값은, 제가 손으로 적지 않습니다. **PR #110 고정 증거 JSON의 구조화 값을 실행 중에 읽어** 비교합니다.
- PR #110에 없는 새 입력의 기대는 아래 표에 '유도'로 표시합니다. 근거는 PR #110 코드 경로입니다.
- 코드에는 결과 사유를 미리 박은 설명 글자를 두지 않습니다.
- 보고서의 결과 표는 증거 JSON에서 자동으로 만든 표(`evidence/tables.md`)를 그대로 옮깁니다.

## fixture(합성 · 01-29 A 분할 ×5 적용 뒤 A 185주) — 기대값
B(무관 · anchor 없음)는 배치 날짜 X에 병합 1/5 · apply_date X입니다.

| # | 배치 X | 배치 내용 | 기대 |
|---|---|---|---|
| K1 | 02-02 | A **reverse_split 1/5** · apply 02-02(src RK) + B | BATCH_ABORTED · A `BLOCKED_AMBIGUOUS_EVENT_IDENTITY` · B `OK`(미적용) · A 185 · B 75 · 상태/레지스트리/provenance 해시 불변 · 바뀐 칸 0 · PERF_BLOCKED(02-02) |
| K2 | 02-03 | 나중의 독립 reverse_split 1/5 · apply 02-03(src R6) + B | K1과 같은 모양으로 차단. **보수적 오탐 · NEEDS_DATA** |
| K3 | 01-30 | 처음 보는 C **split ×2**(C 40주) + B reverse_split 1/5 | COMMITTED · 둘 다 `OK` · A 185 · B 15 · C 80 · TWR/MDD 0 |

- K3만 시작 보유에 합성 C(40주 · 1000)를 더합니다. 다른 fixture는 PR #110과 같은 보유(A 37 · B 75)로, 해시를 PR #110과 바로 비교할 수 있게 합니다.

**회귀 Q1~Q4(PR #110 fixture 그대로)**
- 4경로 각각에서 다음 값이 PR #110 증거 JSON과 **완전히 같아야** 합니다.
  - verdict · 키별 status
  - 배치 전후 state/prov 해시 · 최종 state/prov 해시
  - 수량 · provenance A · 성과 상태

**공통**
- 차단 배치: `pos`(A · B 수량과 가격) · `applied` · `prov`의 바뀐 칸이 0이어야 합니다. 바뀌는 것은 `blocked_from`뿐입니다.
- 경로 불변: 입력 순서 2 × 01-29 뒤 serialize→reload 유무 = 4경로에서 판정 · 사유 · 해시 · 수량 · 성과가 같아야 합니다.
- 바이트 안정: reload 지점과 마지막 날 모두 같은 바이트여야 합니다.
- 자르기: 날짜 d마다 'd까지만 읽은 실행'의 상태/provenance 해시 · 스냅숏이 전체 실행의 d 시점과 같아야 합니다.

## 음성대조군(PR #110 고정본)

| 입력 | 기대 | 기대 출처 |
|---|---|---|
| R1 그대로(02-02 A reverse 1/5만) | verdict · status · A 수량 = PR #110 증거 `informational.R1_same_sym_other_kind` 값 | 증거(실행 중 읽음) |
| K1 | COMMITTED · A `OK` · B `OK` · A **185→37** · B 15 | 유도 |
| K2 | COMMITTED · A 37 · B 15 | 유도 |
| K3 | COMMITTED · A 185 · B 15 · C 80 | 유도 |

## 참고(판정 제외 · 그대로 공개)
- I1: 01-29 A 분할 뒤 02-02에 A `bonus_issue` ×2(m_price 1/2)만 입력합니다.
  - family 밖 kind라 격리되지 않고 기존 검사로 넘어갈 것으로 봅니다(예상 COMMITTED · A 370).
  - 수량을 바꾸는 다른 kind로 고쳐 낸 정정은 여전히 비켜 간다는 남은 위험입니다.

## 판정
- K1~K3 · Q1~Q4 회귀 · 바뀐 칸 0 · 4경로 불변 · 바이트 안정 · 자르기 · 음성대조군이 모두 기대와 같으면 READY, 하나라도 다르면 BLOCKED입니다.
- K2 차단은 기대(오탐)이며 NEEDS_DATA로 적습니다.
- READY는 이 합성 격리 계약에만 한정합니다. 실제 사건 0 · +19.90% · NAV 미검증 · PAPER_VALIDATION_READY=false.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/kind_flip_quarantine.py`
- `evidence/kind-flip-quarantine.json` · `evidence/tables.md` · `evidence/run.log`
