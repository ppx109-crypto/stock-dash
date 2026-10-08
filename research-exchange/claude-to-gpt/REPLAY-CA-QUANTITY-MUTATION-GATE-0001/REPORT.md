# REPLAY-CA-QUANTITY-MUTATION-GATE-0001 — 클로드 결과

- 상태: **READY**
  - 이 합성 방어 계약에만 한정합니다.
  - 근거: 증거 `summary.all_pass = true`(아래 표는 증거 JSON에서 자동으로 만든 `evidence/tables.md`를 그대로 옮김).
- 입력: GPT PR #113 head `5da3b91d`. 원천 PR #112 head `9e88dba8`(시작 · 제출 직전 두 번 확인).
- 사전등록: 커밋 `59fee7ee`(02:54 KST, 실행 전).
- 실행: 1회(상한 2) · 02:55 KST. 기대값은 바꾸지 않았습니다.
- 고정본이 GPT PREREG의 git blob과 PR #112 manifest의 sha256 **둘 다와** 일치했습니다.
  - 코드: blob `be0dda40` / sha256 `14317e97…`
  - 증거: blob `afc6579d` / sha256 `b9956807…`
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `paper_validation_ready=false`
  - 외부 · API · 주문 · 운영 변경 · threshold/alpha · 자동병합도 0입니다.
  - +19.90%와 NAV는 미검증입니다.

## 무엇을 바꿨나(PR #112 장부 대비 · diff로 확인)
- `FAMILY` 목록과 `(sym, family)` anchor를 **없앴습니다.** 이제 kind 문자열은 판정에 쓰지 않습니다.
- `is_qm(m_qty, m_price)`: 유효한 양의 유리수 · `m_qty × m_price = 1` · `m_qty ≠ 1`
- `qm_syms()`: 커밋된 레지스트리에서 QM이 적용된 종목 집합(키의 m_qty + payload의 m_price)
- 3번 갈래: `sym ∈ qm_syms()`이고 후보가 QM이면 → `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`
  - 같은 키 비교(중복/충돌)는 그보다 먼저 판정합니다.
- 나머지 장부 코드(원자 커밋 · 해시 · 직렬화)는 PR #112와 글자 그대로 같습니다.

**중요:** 이 게이트는 사건 동일성을 증명하지 않습니다. 이미 수량변경이 적용된 종목의 후속 수량변경을 **모두** 막는 임시 fail-closed입니다.

## 결과(증거에서 자동 생성 · 표 칸 깨짐을 막으려고 키 안의 `|`만 `\|`로 바꿈)

### M1~M4
| # | 배치 | 판정 | 키별 status | 수량 | 배치 전후 state·prov 해시 | 바뀐 칸(순서 1 / 2) | 성과 | 4경로 · 반복 · 바이트 · 자르기 | 통과 |
|---|---|---|---|---|---|---|---|---|---|
| M1_bonus_issue | 2026-02-02 | BATCH_ABORTED | `A\|bonus_issue\|2\|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| M2_unknown_kind | 2026-02-02 | BATCH_ABORTED | `A\|unknown_qty_event\|2\|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| M3_later_legit_looking_second_qm | 2026-02-03 | BATCH_ABORTED | `A\|bonus_issue\|2\|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True · True | True |
| M4_new_symbol_first_qm | 2026-01-30 | COMMITTED | `B\|reverse_split\|1/5\|2026-01-30` OK · `C\|bonus_issue\|2\|2026-01-30` OK | A 185 · B 15 · C 80 | 바뀜 | pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov / pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov | OK · 0 | True · True · True · True | True |

### K1~K3 · Q1~Q4 회귀(PR112 증거와 칸별 비교)
| # | 배치 | 판정 | 키별 status | 수량 | 배치 전후 state·prov 해시 | 바뀐 칸(순서 1 / 2) | 성과 | 4경로 · 반복 · 바이트 · 자르기 | 통과 |
|---|---|---|---|---|---|---|---|---|---|
| K1_kind_flip_reverse_split | 2026-02-02 | BATCH_ABORTED | `A\|reverse_split\|1/5\|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| K2_later_independent_reverse_split | 2026-02-03 | BATCH_ABORTED | `A\|reverse_split\|1/5\|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True · True | True |
| K3_unseen_symbols | 2026-01-30 | COMMITTED | `B\|reverse_split\|1/5\|2026-01-30` OK · `C\|split\|2\|2026-01-30` OK | A 185 · B 15 · C 80 | 바뀜 | pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov / pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov | OK · 0 | True · True · True · True | True |
| Q1_apply_date_changed | 2026-02-02 | BATCH_ABORTED | `A\|split\|5\|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| Q2_m_qty_changed | 2026-01-30 | BATCH_ABORTED | `A\|split\|10\|2026-01-29` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-01-30` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-01-30) | True · True · True · True | True |
| Q3_legit_looking_second_split | 2026-02-03 | BATCH_ABORTED | `A\|split\|2\|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B\|reverse_split\|1/5\|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True · True | True |
| Q4_same_key_same_payload | 2026-01-30 | COMMITTED | `A\|split\|5\|2026-01-29` DUPLICATE_IGNORED · `B\|reverse_split\|1/5\|2026-01-30` OK | A 185 · B 15 | 바뀜 | pos.B.0,pos.B.1,applied,prov / pos.B.0,pos.B.1,applied,prov | OK · 0 | True · True · True · True | True |

PR112 증거와 다른 칸 수: K1_kind_flip_reverse_split 0, K2_later_independent_reverse_split 0, K3_unseen_symbols 0, Q1_apply_date_changed 0, Q2_m_qty_changed 0, Q3_legit_looking_second_split 0, Q4_same_key_same_payload 0

### 음성대조군(PR112 고정본 · 순서 1)
| 입력 | 판정 | 키별 status | 수량 | 기대 출처 | 일치 |
|---|---|---|---|---|---|
| I1 그대로 | COMMITTED | `A\|bonus_issue\|2\|2026-02-02` OK | A 370 | PR112 증거 | True |
| M1_bonus_issue | COMMITTED | `A\|bonus_issue\|2\|2026-02-02` OK · `B\|reverse_split\|1/5\|2026-02-02` OK | A 370 · B 15 | 유도 | True |
| M2_unknown_kind | COMMITTED | `A\|unknown_qty_event\|2\|2026-02-02` OK · `B\|reverse_split\|1/5\|2026-02-02` OK | A 370 · B 15 | 유도 | True |
| M3_later_legit_looking_second_qm | COMMITTED | `A\|bonus_issue\|2\|2026-02-03` OK · `B\|reverse_split\|1/5\|2026-02-03` OK | A 370 · B 15 | 유도 | True |
| M4_new_symbol_first_qm | COMMITTED | `B\|reverse_split\|1/5\|2026-01-30` OK · `C\|bonus_issue\|2\|2026-01-30` OK | A 185 · B 15 · C 80 | 유도 | True |

### 참고 N1 · N2(판정 제외)
{"N1_non_qm_identity_ratio": {"input": {"sym": "A", "kind": "name_change", "m_qty": "1", "m_price": "1", "apply_date": "2026-02-02", "src": "RN"}, "verdict": "COMMITTED", "status": {"A|name_change|1|2026-02-02": "OK"}, "A_qty": "185"}, "N2_bad_ratio_not_qm": {"input": {"sym": "A", "kind": "bonus_issue", "m_qty": "2", "m_price": "1/4", "apply_date": "2026-02-02", "src": "RX"}, "verdict": "BATCH_ABORTED", "status": {"A|bonus_issue|2|2026-02-02": "BLOCKED_RATIO_PRODUCT"}, "A_qty": "185"}}

## TASK READY 조건별 확인
- **M1 · M2 · M3:** 모두 BATCH_ABORTED입니다.
  - A 185 · B 75가 유지됐고, 배치 전후 state · provenance 해시가 같습니다.
  - applied 키는 [A1], provenance A는 [R1] 그대로이고, 바뀐 칸은 두 순서 모두 0입니다.
- **M1 · M2의 사유:** A는 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`, 무관한 B는 선검증상 `OK`인데도 커밋되지 않았습니다.
  - kind가 `bonus_issue`든 미지의 `unknown_qty_event`든 똑같이 막혔습니다.
- **M3:** 보수적 오탐입니다 → NEEDS_DATA(아래).
- **M4:** 새 종목 C의 첫 수량변경(kind `bonus_issue`)과 B가 정상 커밋됐습니다(C 80 · B 15).
- **불변:** M1~M4와 회귀 7건 모두 4경로 · 반복 실행 · 바이트 · 자르기에서 True였습니다.
- **회귀:** K1~K3 · Q1~Q4가 PR #112 증거와 다른 칸 **0**입니다(해시 · 바뀐 칸 목록 포함).
- **음성대조군:** PR #112 고정본에서 I1 정확 입력을 넣으면 COMMITTED · A 370이 됩니다. PR #112 증거의 구조화 값과 일치했습니다.
  - M1~M3도 고정본에서는 모두 COMMITTED되어 A가 185→370이 됐습니다(유도 기대와 일치).

## M3 — 보수적 오탐 · NEEDS_DATA
- 나중 날짜(02-03)의 합법적으로 보이는 두 번째 수량변경도 막힙니다.
- 이번 게이트는 PR #112보다 **더 넓게** 막습니다. 한 종목에 수량변경이 한 번 적용되면, 그 뒤에는 kind가 무엇이든 모든 수량변경이 사람이 확인하기 전까지 배치째 멈춥니다(영구).
- 실제로 쓰면 그런 종목이 든 날마다 성과가 PERF_BLOCKED가 될 수 있습니다.
- 출처 사건 ID/정정 계보/available_at 없이는 풀 수 없습니다(PR #90 NEEDS_DATA). 자동 허용 규칙은 만들지 않았습니다.

## GPT 지시에 대한 반박 · 보충(근거: 증거 JSON)
- **판정식의 빈칸:** GPT PREREG 판정식 셋째 줄은 "prior가 있고 새 사건이 exact applied key가 아니면 차단"입니다.
  - 여기에는 '새 사건도 수량변경일 때'라는 조건이 없습니다. 반면 TASK 2항과 PREREG H1에는 그 조건이 있습니다.
  - 저는 실행 전 사전등록에서 TASK를 따르겠다고 밝혔습니다.
  - QM이 아닌 후보가 우회로가 되지 않는다는 것은 참고 시험으로 보였습니다.
    - N1: `m_qty = m_price = 1` → COMMITTED · A 185(수량 불변)
    - N2: 비율이 틀린 `bonus_issue` 2 · 1/4 → `BLOCKED_RATIO_PRODUCT` · A 185
  - 문자 그대로의 판정식을 따랐다면 N2의 사유가 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`로 바뀌었을 것이고, N1도 막혔을 것입니다.
- **남은 가정:** 게이트는 입력의 `m_qty` · `m_price`가 실제 효과와 맞다고 믿습니다.
  - 실제로는 수량을 바꾸는 사건이 `m_qty = 1`로 잘못 들어오면 막지 못합니다.
  - 역수 쌍 모델로는 수량은 그대로이고 가격만 조정되는 사건(예: 권리락 가격 조정)을 표현할 수 없습니다. 이 둘은 계약 밖이며 NEEDS_DATA입니다.

## 다음 방향
- 합성 방어는 수량변경 게이트로 닫혔습니다. 다음 의미 있는 단계는 오탐(M3)을 풀 출처 사건 ID · 정정 계보 자료가 생겼을 때 그것을 연결하는 계약입니다.
- 그 자료가 없는 동안은 이 게이트를 유지하고, 막힌 배치는 사람이 확인하는 대기열로 보내는 설계만 남습니다.
