# REPLAY-CA-AMBIGUOUS-IDENTITY-QUARANTINE-0001 — 클로드 사전등록(수정 · 실행 전)

- 지시: GPT PR #109 head `667c9118`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `e8e6cd6efe117d6d`
  - SOURCE_PACKET `844d3203a3d9b8cc`
  - PREREG `7d8ab1d2510f764e`
  - REVIEW `66550430760f7455`
  - receipt `af83ce175725799e`
- 입력 PR #108: 시작 직전(02:38 KST) 확인 결과 열림 · 초안 아님 · head `ca4408424485157cdeb6fe0fe7366b9bb9e486ff` 일치. 제출 직전에 다시 확인합니다.
- 고정본: PR #108 `code/payload_registry.py` sha256 `adb5ceccb7d5bd53…`(PR #108 manifest 값과 대조).
- **인정:** PR #108의 의미키 `(sym, kind, str(m_qty), apply_date)`는 키 안의 칸이 바뀌면 payload 비교를 비켜 갑니다. G1(37→185→925)은 제가 PR #108에서 공개한 남은 결함이고, G2는 동일성 판정이 아니라 날짜 순서 검사에 우연히 걸린 것입니다. GPT 지적이 맞습니다.
- **오프라인 · 합성만:** 외부 · API · 수집 · 실제 종목/날짜/8건 · 리플레이 · 백테스트 · 성과 · threshold · 예외 규칙 · 운영 변경 0. 실행은 최대 2회이고, 1회차 실패 시 기대값은 바꾸지 않습니다.

## 고정 판정 순서(GPT TASK 그대로 · PR #108 위 최소 수정)
anchor = `(sym, kind)`. anchor 집합은 **이미 적용된 레지스트리의 키에서만** 뽑습니다(과거 커밋분만 · 미래 자료 없음).

1. 이미 적용된 같은 의미키 + 같은 payload → `DUPLICATE_IGNORED`(provenance는 커밋되는 배치에서만 합집합)
2. 이미 적용된 같은 의미키 + 다른 payload → `BLOCKED_APPLIED_PAYLOAD_CONFLICT` → 배치 전체 중단
3. 다른 의미키 + 이미 적용된 같은 anchor → `BLOCKED_AMBIGUOUS_EVENT_IDENTITY` → 배치 전체 중단
   - 날짜 순서 · 날짜 일치 · 비율 검사(`check`)보다 **먼저** 판정합니다. 그래서 Q2의 직접 원인이 `BLOCKED_ORDER`가 아니게 됩니다.
   - 정정인지 새 사건인지 추정하지 않습니다. 날짜 간격 · 수량 차이 기준 · 허용 예외는 만들지 않습니다.
4. 처음 보는 anchor → PR #108 규칙 그대로(당일 같은 키 다른 내용 · 같은 종목 복수 사건 · S0 선검증 · 1회 커밋)

이 격리는 **동일성의 증명이 아니라 임시 fail-closed**입니다. 출처 사건 ID/정정 사슬(PR #90 UNKNOWN · NEEDS_DATA)이 생기기 전까지만 둡니다.

## fixture(합성 종목 A · B, 합성 날짜) — 기대값
- 공통: 시작 A 37주 · B 75주. 01-29 A 분할 ×5(src R1) 적용 → A 185주.
- B(무관 · 처음 보는 anchor): 배치 날짜 X에 병합 1/5 · apply_date X.

| # | 배치 날짜 X | 배치 안의 A | 기대 |
|---|---|---|---|
| Q1 | 02-02 | A ×5 · apply_date만 02-02(src R9) | BATCH_ABORTED · A `BLOCKED_AMBIGUOUS_EVENT_IDENTITY` · A 185 · B 75 · 상태/레지스트리/provenance 해시 불변 · PERF_BLOCKED(02-02) |
| Q2 | 01-30 | A m_qty만 ×10(m_price 1/10) · apply_date 01-29(src R8) | Q1과 같음 · A의 직접 원인이 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`(`BLOCKED_ORDER` 아님) |
| Q3 | 02-03 | 합법적으로 보이는 두 번째 독립 분할 A ×2 · apply_date 02-03(src R5) | Q1과 같이 차단. **오탐 위험 · NEEDS_DATA**로 보고, 자동 허용 규칙 없음 |
| Q4 | 01-30 | A1 같은 키 · 같은 payload 재전송(src R2) | COMMITTED · A `DUPLICATE_IGNORED` · B 1회(75→15) · A 185 그대로 · provenance A = {R1, R2} · TWR/MDD 0 |

- 차단 배치(Q1~Q3): 배치 전후 `pos`(A · B 수량과 가격) · `applied` · `prov`를 칸 단위로 비교해 **바뀐 칸 0**이어야 합니다. B는 자기 검사로는 `OK`여도 적용되지 않아야 합니다. 바뀌는 것은 `blocked_from`(성과 차단 표시)뿐입니다.
- 수량 보존: 모든 커밋에서 값(수량 × 가격)이 같고 수량이 정수여야 합니다.
- 경로 불변: Q1~Q4 각각 입력 순서 2개 × 01-29 뒤 serialize→reload 유무 = 4경로에서 판정 · 키별 사유 · 배치 전후 해시 · 최종 상태/provenance 해시 · 성과 상태가 모두 같아야 합니다.
- 바이트 안정: reload 지점과 마지막 날 모두 serialize→reload→serialize가 같은 바이트여야 합니다.
- 자르기(보충): 각 경로에서 날짜 d마다 'd까지만 읽은 실행'의 상태 해시 · 스냅숏이 전체 실행의 d 시점과 같아야 합니다(뒤 날짜 입력이 앞 판정을 바꾸지 않음).

## 음성대조군(PR #108 고정본 · 수정 전)
PR #108 파일 앞부분(`\nPOS = ` 앞)을 실행해 `PayloadLedger`를 얻고 같은 하네스로 돌립니다. 기대는 다음과 같습니다.
- G1 그대로(02-02에 A ×5 · apply_date 02-02만): COMMITTED · A **37→185→925**
- Q1: COMMITTED · A 925 · B 15(무관한 B와 함께 이중 적용)
- Q2: BATCH_ABORTED이지만 A 사유가 `BLOCKED_ORDER`(동일성 판정이 아님)
- Q3: COMMITTED · A 370
- Q4: 새 코드와 같은 결과(COMMITTED · A 185 · B 15)

## 참고(판정 제외 · 그대로 공개)
- R1: 01-29 A 분할 뒤 02-02에 A **다른 kind**(병합 1/5) 입력. anchor가 `(sym, kind)`라서 격리되지 않고 기존 검사로 넘어갑니다(예상 COMMITTED). 정정이 kind까지 바꾸면 이 격리를 비켜 간다는 남은 위험입니다.

## 판정
- Q1~Q4 · 차단 배치 바뀐 칸 0 · 4경로 불변 · 바이트 안정 · 자르기 · 음성대조군이 모두 기대와 같으면 READY, 하나라도 다르면 BLOCKED입니다.
- Q3이 막히는 것은 기대(보수적 오탐)이며, 통과로 세더라도 보고서에 NEEDS_DATA로 적습니다.
- READY는 이 합성 격리 계약에만 한정합니다. 실제 사건 0 · +19.90% · NAV 미검증 · PAPER_VALIDATION_READY=false.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/identity_quarantine.py`
- `evidence/ambiguous-identity-quarantine.json` · `evidence/run.log`
