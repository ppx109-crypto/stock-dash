# REPLAY-CA-APPLIED-PAYLOAD-PROVENANCE-0001 — 적용 레지스트리 내용 보존 · 정정 충돌 탐지(합성)

- 지시: GPT PR #107 head `4d8f4f1d`
- 입력 PR #106 head `dacbcb09`: 열림 · 초안 아님. 시작 직전과 제출 직전 2회 확인했습니다.
- 사전등록: 커밋 `c708501e`(2026-10-09 02:29 KST, 수정 · 실행 전)
- **status: READY** — 합성 영속 멱등성 계약에 한정됩니다.
  - 실제 적용 0
  - +19.90% · NAV 미검증
  - PAPER_VALIDATION_READY=false
- 실행 1회(상한 2회), 실패 0
- 외부 · API · 수집 · 실제 종목/날짜/8건 · 리플레이 · 백테스트 · 성과 · threshold · 운영 변경은 모두 0입니다.
- 실행 코드: `code/payload_registry.py`(Fraction · 네트워크 함수 막음)

## 0. 인정
- PR #106 `batch_atomicity.py` 64줄 `if k in self.applied:`는 내용 비교 없이 중복으로 넘겼습니다. `self.applied`도 키 집합만 저장했습니다.
- 그래서 이미 적용된 사건이 다른 내용으로 다시 와도 조용히 무시됐습니다. GPT 지적이 맞습니다.

## 1. 수정
- **적용 레지스트리:** `key → canonical payload (m_price 정규 분수 문자열, real)`. 최초 적용 때 수량 · 가격과 **같은 커밋**에서 기록합니다.
- **provenance:** `key → 관찰된 출처 번호 집합`. 커밋되는 배치에서만 갱신하고, 같은 내용의 다른 출처 재전송도 관찰로 남깁니다.
- **해시:** state hash = 현금 · 수량/표시가격 · 레지스트리(키+내용). provenance hash는 따로 셉니다.
- **판정**
  - 이미 적용된 키 + 같은 내용 → `DUPLICATE_IGNORED`
  - 이미 적용된 키 + 다른 내용 → `BLOCKED_APPLIED_PAYLOAD_CONFLICT` → **배치 전체 `BATCH_ABORTED`**
  - 나머지 규칙(당일 같은 키 다른 내용 · 같은 종목 복수 사건 · S0 선검증 · 1회 커밋)은 PR #106 그대로입니다.
- **직렬화:** 정렬 · 고정 구분자 JSON(분수는 문자열)입니다. 다시 읽은 뒤 다시 쓰면 같은 바이트가 나옵니다.

## 2. fixture — 전부 기대와 같음
- 공통: 01-29에 A 분할 ×5(출처 R1) 적용 → 01-30에 배치 [A 변형, B 병합 1/5 정상]
- 각 fixture를 **두 입력 순서 × reload 유무 = 4경로**로 돌렸고, 판정 · 키별 상태 · 배치 직후/최종 state 해시 · provenance 해시 · 성과 판정이 4경로 모두 같았습니다(P4 · P5).

| # | 01-30의 A | 판정 | A 상태 | 수량 A · B | 해시 | provenance A | 성과 |
|---|---|---|---|---|---|---|---|
| P1 | 같은 내용 · 출처 R2 | COMMITTED | DUPLICATE_IGNORED | 185 · **15**(B 1회) | 바뀜(B 반영) | {R1, R2} | TWR · MDD 0 |
| P2 | m_price 1/4 | **BATCH_ABORTED** | BLOCKED_APPLIED_PAYLOAD_CONFLICT | 185 · **75**(B 미적용) | state · provenance **불변** | {R1} | PERF_BLOCKED(01-30) |
| P3 | real = true | **BATCH_ABORTED** | BLOCKED_APPLIED_PAYLOAD_CONFLICT | 185 · **75** | state · provenance **불변** | {R1} | PERF_BLOCKED(01-30) |

- **직렬화 왕복:** 01-29 처리 뒤 직렬화 → 다시 읽기 → 다시 직렬화한 바이트가 모든 경로에서 같았습니다. 다시 읽은 원장의 이후 판정도 안 읽은 원장과 같았습니다.

## 3. 수정 전 음성대조군(PR #106 고정본 sha256 `db4403a7…` = PR #106 manifest 값)
| 입력 | 순서 | 판정 | A 상태 | B 수량 |
|---|---|---|---|---|
| P2(m_price 변경) | A→B · B→A | COMMITTED · COMMITTED | **DUPLICATE_IGNORED** | **15**(반영됨) |
| P3(real 변경) | A→B · B→A | COMMITTED · COMMITTED | **DUPLICATE_IGNORED** | **15** |

- 수정 전에는 내용이 바뀐 재전송이 조용히 무시됐고, 같이 온 B까지 커밋됐습니다. 결함이 재현됐습니다.

## 4. 남은 위험(참고 시험 · 판정 제외 · 사전등록대로 결과 그대로)
| # | 입력 | 결과 | 의미 |
|---|---|---|---|
| G1 | 01-29 A ×5 적용 뒤, 02-02에 'A ×5 · apply_date 02-02'(일정 정정처럼 보이는 입력) | **COMMITTED · A 37 → 185 → 925** | 의미키에 apply_date가 들어 있어 **새 사건으로 보이고 두 번 적용**됩니다 |
| G2 | 01-29 A ×5 적용 뒤, 01-30에 'A ×10 · apply_date 01-29'(비율 정정) | BATCH_ABORTED(`BLOCKED_ORDER`) | 새 키지만 지난 날짜라 **우연히** 막힘 |

- 정리하면, 이번 계약은 **m_price · real의 변경**을 잡습니다. **m_qty · apply_date의 변경은 키가 달라져 잡지 못합니다.**
  - 비율 정정은 대개 날짜 순서 검사에 걸리지만, **적용일 정정(미래 날짜)**은 그대로 두 번 적용됩니다.
- 이를 막으려면 '같은 종목 · 같은 종류의 사건이 이미 있는가'를 판단할 **출처 사건 식별자**(정정 사슬)나 기간 기준이 필요합니다.
  - 정정 사슬은 PR #90에서 DART에 원 접수 칸이 없어 UNKNOWN이었습니다.
  - 기간 기준은 새 threshold라 이번에 만들지 않았습니다(NEEDS_DATA).

## 5. 유지
- 실제 8개 기업행동 후보: UNKNOWN(적용 0)
- price_basis_date: BLOCKED → 실제 사건은 `APPLY_BLOCKED_NO_PRICE_BASIS_DATE`
- 정정 사슬: UNKNOWN_CA_VERSION_PIT(PR #90) — 위 G1 위험의 뿌리
- threshold · alpha: 만들지 않음
- +19.90% · NAV · PAPER_VALIDATION_READY: 미검증 · false

## 실행 계수
- 오프라인 실행 1회 · 실패 0
  - 정상 판정 경로: 3 fixture × 4경로 = 12
  - 음성대조군 4회 · 참고 시험 2회
- 외부 0 · API 0 · 수집 0 · 실제 적용 0 · 리플레이 0 · 백테스트 0 · 성과 0 · 운영 변경 0 · 새 세션 0 · 자동병합 0

## 다음 방향
- G1(적용일 정정의 이중 적용)은 합성 원장만으로는 닫을 수 없습니다. 실제 공시의 정정 사슬(원 공시 ↔ 정정)을 얻는 경로가 정해져야 합니다.
- 그전까지 실제 적용은 계속 막혀 있으므로 운영 위험은 없습니다. 다만 수집기를 만들 때 '같은 종목 · 종류 사건의 기존 적용 여부'를 확인하는 단계가 필요하다는 점을 기록해 둡니다.
