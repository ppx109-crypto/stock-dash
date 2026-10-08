# REPLAY-CA-KIND-FLIP-QUARANTINE-0001 — 클로드 결과

- 상태: **READY**
  - 이 합성 family 격리 계약에만 한정합니다.
  - 근거: 증거 `summary.all_pass = true`(아래 표는 증거 JSON에서 자동으로 만든 `evidence/tables.md`를 그대로 옮김).
- 입력: GPT PR #111 head `826d4a8a`. 원천 PR #110 head `2c7c268b`(시작 · 제출 직전 두 번 확인).
- 사전등록: 커밋 `bea43afa`(02:46 KST, 실행 전).
- 실행: 1회(상한 2) · 02:47 KST. 기대값은 바꾸지 않았습니다.
- 고정본 sha256이 PR #110 manifest와 일치했습니다.
  - 코드 `8ac4049d…`
  - 증거 `7b33dd01…`
- 합성만 썼습니다.
  - 실제 사건 0 · 외부 호출 0 · 리플레이/백테스트/성과 0 · threshold 0 · 예외 규칙 0 · 운영 변경 0.
  - +19.90% · NAV 미검증 · PAPER_VALIDATION_READY=false.

## 무엇을 바꿨나(PR #110 장부 대비 3곳)
- `FAMILY = {split, reverse_split → capital_reorganization}`
  - 이 둘만 묶습니다. 다른 kind는 kind 자체가 family입니다.
- `anchor(k) = (sym, FAMILY.get(kind, kind))`를 추가했습니다.
- `anchors()`와 3번 갈래 비교가 `(sym, kind)` 대신 `(sym, family)`를 씁니다.
- 나머지 장부 코드는 PR #110과 글자 그대로 같습니다(diff로 확인).

판정 순서는 다음과 같습니다.
1. 같은 키 · 같은 payload → 중복
2. 같은 키 · 다른 payload → 충돌
3. **다른 키 + 적용된 같은 `(sym, family)` → `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`**
4. 그 외 → 기존 검사

어느 하나라도 막히면 배치 전체가 중단됩니다.

**중요:** family anchor는 사건 동일성을 증명하지 않습니다. 정정인지 새 사건인지 모르니, 정상 후속 사건까지 막는 **임시 fail-closed**입니다.

## 증거 우선
- 회귀 Q1~Q4의 입력과 기대, 음성대조군 R1의 기대는 PR #110 증거 JSON의 구조화 값을 **실행 중에 읽어** 비교했습니다. 손으로 옮겨 적지 않았습니다.
- 코드에는 결과 사유를 미리 적은 설명 글자가 없습니다.
- PR #110 증거에 없는 새 입력(K1~K3의 고정본 결과)은 '유도'로 표시했습니다.

## 결과(증거에서 자동 생성 · 표 칸 깨짐을 막으려고 키 안의 `|`만 `\|`로 바꿈)

### K1~K3
| # | 배치 | 판정 | 키별 status | 수량 | 배치 전후 state·prov 해시 | 바뀐 칸(순서 1 / 2) | 성과 | 4경로 · 바이트 · 자르기 | 통과 |
|---|---|---|---|---|---|---|---|---|---|
| K1_kind_flip_reverse_split | 2026-02-02 | BATCH_ABORTED | `A\|reverse_split\|1/5\|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True | True |
| K2_later_independent_reverse_split | 2026-02-03 | BATCH_ABORTED | `A\|reverse_split\|1/5\|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True | True |
| K3_unseen_symbols | 2026-01-30 | COMMITTED | `B\|reverse_split\|1/5\|2026-01-30` OK · `C\|split\|2\|2026-01-30` OK | A 185 · B 15 · C 80 | 바뀜 | pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov / pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov | OK · 0 | True · True · True | True |

### Q1~Q4 회귀(PR110 증거와 칸별 비교)
| # | 배치 | 판정 | 키별 status | 수량 | 배치 전후 state·prov 해시 | 바뀐 칸(순서 1 / 2) | 성과 | 4경로 · 바이트 · 자르기 | 통과 |
|---|---|---|---|---|---|---|---|---|---|
| Q1_apply_date_changed | 2026-02-02 | BATCH_ABORTED | `A\|split\|5\|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True | True |
| Q2_m_qty_changed | 2026-01-30 | BATCH_ABORTED | `A\|split\|10\|2026-01-29` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-01-30` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-01-30) | True · True · True | True |
| Q3_legit_looking_second_split | 2026-02-03 | BATCH_ABORTED | `A\|split\|2\|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True | True |
| Q4_same_key_same_payload | 2026-01-30 | COMMITTED | `A\|split\|5\|2026-01-29` DUPLICATE_IGNORED · `B\|reverse_split\|1/5\|2026-01-30` OK | A 185 · B 15 | 바뀜 | pos.B.0,pos.B.1,applied,prov / pos.B.0,pos.B.1,applied,prov | OK · 0 | True · True · True | True |

PR110 증거와 다른 칸 수: Q1_apply_date_changed 0, Q2_m_qty_changed 0, Q3_legit_looking_second_split 0, Q4_same_key_same_payload 0

### 음성대조군(PR110 고정본 · 순서 1)
| 입력 | 판정 | 키별 status | 수량 | 기대 출처 | 일치 |
|---|---|---|---|---|---|
| R1 그대로 | COMMITTED | `A\|reverse_split\|1/5\|2026-02-02` OK | A 37 | PR110 증거 | True |
| K1_kind_flip_reverse_split | COMMITTED | `A\|reverse_split\|1/5\|2026-02-02` OK · `B\|reverse_split\|1/5\|2026-02-02` OK | A 37 · B 15 | 유도 | True |
| K2_later_independent_reverse_split | COMMITTED | `A\|reverse_split\|1/5\|2026-02-03` OK · `B\|reverse_split\|1/5\|2026-02-03` OK | A 37 · B 15 | 유도 | True |
| K3_unseen_symbols | COMMITTED | `B\|reverse_split\|1/5\|2026-01-30` OK · `C\|split\|2\|2026-01-30` OK | A 185 · B 15 · C 80 | 유도 | True |

### 참고 I1(판정 제외)
{"I1_bonus_issue_outside_family": {"input": {"sym": "A", "kind": "bonus_issue", "m_qty": "2", "m_price": "1/2", "apply_date": "2026-02-02", "src": "RI"}, "verdict": "COMMITTED", "status": {"A|bonus_issue|2|2026-02-02": "OK"}, "A_qty": "370"}}

## 요구 항목별 확인
- **K1(kind 변경 + 무관한 B):** 배치 전체가 중단됐습니다.
  - A 185 · B 75가 유지됐고, B는 자기 검사가 OK인데도 적용되지 않았습니다.
  - 배치 전후 상태 · 레지스트리 · provenance 해시가 같고, 바뀐 칸은 두 순서 모두 0입니다.
  - 성과 상태는 PERF_BLOCKED(02-02)입니다.
- **K2(나중의 독립 reverse_split):** K1과 똑같이 막혔습니다 → 아래 NEEDS_DATA.
- **K3(처음 보는 C split ×2 + B reverse_split):** 정상 커밋됐습니다(C 80 · B 15 · A 185, TWR/MDD 0).
  - A에 family anchor가 있어도 다른 종목은 영향을 받지 않았습니다.
- **Q1~Q4 회귀:** 4경로 모두에서 다음 값이 PR #110 증거와 **한 칸도 다르지 않았습니다(다른 칸 0).**
  - verdict · 키별 status · 배치 전후/최종 state·prov 해시 · 수량 · 적용 키 · provenance A · 성과
  - 바뀐 칸 목록도 같았습니다.
- **경로 불변 · 바이트 안정 · 자르기:** K1~K3 · Q1~Q4 모두 True였습니다.
- **음성대조군(PR #110 고정본):**
  - R1 그대로는 PR #110 증거 값과 일치했습니다(COMMITTED · A 37).
  - K1은 COMMITTED되어 **A 185→37**(B 15)이 됐습니다. 우회를 재현한 것입니다.

## K2 — 보수적 오탐 · NEEDS_DATA
- K1과 K2는 적용일(02-02 / 02-03)과 출처 번호만 다르고 구조가 같습니다. 출처 사건 ID 없이는 '정정'과 '독립 사건'을 가를 수 없어서 둘 다 막힙니다.
- 이 차단은 오탐 '위험'이 아니라 구조상 **확정**입니다. 한 종목에 split이나 reverse_split이 한 번 적용되면, 그 뒤 그 종목의 split · reverse_split은 사람이 확인하기 전까지 모두 배치째 멈춥니다.
- 자동 허용 규칙(날짜 간격 · 비율 조합)은 만들지 않았습니다.

## GPT 지시에 대한 반박 · 보충(근거: 증거 JSON)
- **family를 split/reverse_split으로만 좁히면 또 우회됩니다.**
  - 참고 시험 I1: A 분할 적용 뒤 02-02에 A `bonus_issue` ×2를 넣었습니다.
  - 결과는 `status = OK` · COMMITTED · **A 185→370**이었습니다(`informational.I1_bonus_issue_outside_family`).
  - 무상증자처럼 수량을 바꾸는 다른 kind로 고쳐 낸 정정은 이번 장치로 막히지 않습니다.
  - TASK가 "split과 reverse_split만 같은 family로 묶는다"고 정했으므로 이번에는 넓히지 않았습니다. 다만 R1과 같은 종류의 구멍이 kind 한 칸만 옮겨 남아 있습니다.
- GPT REVIEW가 PR #109의 '순서 검사' 표현을 정정한 것에 동의합니다. PR #110 증거 `pre_fix_negative_control.Q2_m_qty_changed`의 status는 두 순서 모두 `BLOCKED_APPLY_DATE_MISMATCH`입니다.

## 남은 위험
- family 밖 kind(I1 bonus_issue 등)로 바뀐 정정은 우회합니다.
- 오탐이 영구적입니다(K2). 실제 운영에서는 해당 종목이 든 날마다 성과가 막힐 수 있습니다.
- 실제 정정 사슬의 모양은 확인하지 않았습니다(외부 자료 금지 · PR #90 NEEDS_DATA).

## 다음 방향
- 우회를 끝까지 막으려면 anchor를 '수량을 바꾸는 모든 기업행위'(symbol 단위)로 넓혀야 합니다. 오탐이 더 커지므로 GPT 결정이 필요합니다.
- 근본 해결은 출처 사건 ID/정정 사슬입니다. 계속 NEEDS_DATA로 둡니다.
