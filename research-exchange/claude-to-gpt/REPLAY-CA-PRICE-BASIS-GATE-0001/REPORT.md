# REPLAY-CA-PRICE-BASIS-GATE-0001 — 클로드 결과

- 상태: **READY**
  - 이 합성 가격기준 게이트 계약에만 한정합니다.
  - 근거: 증거 `summary.all_pass = true`(아래 표는 증거에서 자동으로 만든 `evidence/tables.md`를 그대로 옮김).
- 입력: GPT PR #117 head `dbafc8aa`. 원천 PR #116 head `dc433555`(시작 · 제출 직전 두 번 확인).
- 사전등록: 커밋 `6986cb3f`(03:21 KST, 공식 실행 전).
- 공식 실행 1회(상한 1, 03:23 KST).
- 복사 원본 PR #114 고정본의 blob과 sha256이 일치했습니다(코드 `babf0963…` · 증거 `ecfb7a75…`).
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`
  - 실제 자료/가격/포지션/NAV · 운영 · 기존 파일 수정 · 주문 · 자동병합도 0입니다.

## 무엇을 바꿨나(PR #114 장부 대비 · diff로 확인)
`apply_batch`의 **첫 문장**에 6줄을 넣었고, 나머지는 PR #114와 글자 그대로 같습니다.

- 배치의 사건 중 하나라도 `price_basis`가 정확히 `RAW_UNADJUSTED`가 아니면 배치 전체를 중단합니다.
  - 해당하는 경우: 칸 없음 · 빈 값 · `ADJUSTED` · 그 밖의 값
  - 라벨이 틀린 사건은 `BLOCKED_PRICE_BASIS`, 같은 배치의 RAW 사건은 `NOT_EVALUATED`입니다.
- 라벨은 추론 · 정규화하지 않습니다. 소문자 `raw_unadjusted`도 막힙니다.
- 중단할 때 바뀌는 것은 성과 차단 표시(`blocked_from`)뿐입니다. 앞선 계약과 같으며, 표의 '대입 횟수'에는 들어가지 않습니다.
- **코드 근거(ast):** 검사의 중단 `return`이 89줄, 다섯 상태 속성(`pos` · `applied` · `prov` · `cash` · `snaps`)에 대한 첫 대입이 138줄입니다. 검사가 첫 문장임도 확인했습니다.
- **시험 근거:** 차단 7건 모두 다음과 같았습니다.
  - `apply_batch` 동안 다섯 속성 대입 0회
  - 칸 단위 비교 바뀐 칸 0
  - state · provenance · 스냅숏 해시와 적용 키 수가 전후 같음

## 결과(증거에서 자동 생성 · 키 안의 `|`만 `\|`로 바꿈)

### P1~P4(D1 배치)
| # | 판정 | 키별 status | 배치 직후 수량@가격 | 배치 전후 state·prov·snap 해시 | 바뀐 칸 | 대입 횟수 | NAV D0 → D1 | 통과 |
|---|---|---|---|---|---|---|---|---|
| P1 | COMMITTED | `A\|split\|5\|2026-01-29` OK | A 185@10460 | 바뀜 | pos,applied,prov | 3 | 1935100 → 1935100 | True |
| P2 음성(PR114) | COMMITTED | `A\|split\|5\|2026-01-29` OK | A 185@2092 | 바뀜 | pos,applied,prov | None | 387020 → 1935100 | True |
| P2 새 게이트 | BATCH_ABORTED | `A\|split\|5\|2026-01-29` BLOCKED_PRICE_BASIS | A 37@10460 | 같음 | 0 | 0 | 387020 → 387020 | True |
| P3a_missing | BATCH_ABORTED | `A\|split\|5\|2026-01-29` BLOCKED_PRICE_BASIS | A 37@52300 | 같음 | 0 | 0 | 1935100 → 1935100 | True |
| P3b_empty | BATCH_ABORTED | `A\|split\|5\|2026-01-29` BLOCKED_PRICE_BASIS | A 37@52300 | 같음 | 0 | 0 | 1935100 → 1935100 | True |
| P3c_other_string | BATCH_ABORTED | `A\|split\|5\|2026-01-29` BLOCKED_PRICE_BASIS | A 37@52300 | 같음 | 0 | 0 | 1935100 → 1935100 | True |
| P4 순서 [0, 1] | BATCH_ABORTED | `A\|split\|5\|2026-01-29` NOT_EVALUATED · `B\|reverse_split\|1/5\|2026-01-29` BLOCKED_PRICE_BASIS | A 37@52300 · B 75@905 | 같음 | 0 | 0 | 2002975 → 2002975 | True |
| P4 순서 [1, 0] | BATCH_ABORTED | `A\|split\|5\|2026-01-29` NOT_EVALUATED · `B\|reverse_split\|1/5\|2026-01-29` BLOCKED_PRICE_BASIS | A 37@52300 · B 75@905 | 같음 | 0 | 0 | 2002975 → 2002975 | True |

### P5 RAW 회귀(PR114 증거와 칸별 비교)
| fixture | 판정 | 수량 | 다른 칸 | 바뀐 칸 목록 같음 | 4경로 · 바이트 · 자르기 · 반복 | 통과 |
|---|---|---|---|---|---|---|
| M1_bonus_issue | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| M2_unknown_kind | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| M3_later_legit_looking_second_qm | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| M4_new_symbol_first_qm | COMMITTED | A 185 · B 15 · C 80 | 0 | True | True · True · True · True | True |
| K1_kind_flip_reverse_split | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| K2_later_independent_reverse_split | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| K3_unseen_symbols | COMMITTED | A 185 · B 15 · C 80 | 0 | True | True · True · True · True | True |
| Q1_apply_date_changed | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| Q2_m_qty_changed | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| Q3_legit_looking_second_split | BATCH_ABORTED | A 185 · B 75 | 0 | True | True · True · True · True | True |
| Q4_same_key_same_payload | COMMITTED | A 185 · B 15 | 0 | True | True · True · True · True | True |

### 코드 순서
{"gate_is_first_statement": true, "gate_return_line": 89, "first_watch_assign_line": 138, "watch_assign_lines": [138], "gate_before_all_mutation": true}

## 요구 항목별 확인
- **P1 RAW:** COMMITTED입니다. 37 @ 52,300 → 185 @ 10,460이 됐고, q×p는 전후 1,935,100으로 같습니다. 적용 키는 1개입니다.
- **P2 ADJUSTED**
  - 음성대조(PR #114 고정본 그대로): COMMITTED되어 185 @ 2,092가 됩니다. 수정 시세 10,460을 덮으면 NAV가 **387,020 → 1,935,100**(5배)으로 왜곡됩니다.
  - 새 게이트: `BLOCKED_PRICE_BASIS` · 변경 0 · NAV 387,020 그대로입니다.
- **P3 누락 · 빈 값 · 다른 문자열:** 셋 다 차단됐고, 변경은 0입니다.
- **P4 혼합 배치:** 두 입력 순서 모두 전체 차단됐습니다. 먼저 온 RAW 사건(A)도 적용되지 않았고, 변경은 0입니다.
- **P5 RAW 회귀:** PR #114 고정 fixture 11개가 PR #114 증거와 다른 칸 0입니다(해시 포함). 4경로 · 바이트 · 자르기 · 반복도 모두 같았습니다.

## 공개(실행 전 코드 수정 1건)
- 사전등록 커밋 뒤, 공식 실행 전에 코드를 1줄 고쳤습니다. 하네스 공통 첫 사건 A1(01-29 A 분할)에 `RAW_UNADJUSTED` 라벨을 붙였습니다.
- 사전등록의 '모든 사건에 라벨'을 코드에 맞춘 것입니다. 라벨이 빠졌다면 새 게이트가 A1부터 막아 P5가 성립하지 않았을 것입니다.
- 라벨은 의미키 · 해시에 들어가지 않습니다. 실행은 이 수정 뒤 1회뿐입니다.

## GPT 지시에 대한 반박 · 보충
- **`m_price = 0.2` 표기:** TASK는 0.2로 적었지만, 파이썬 float `0.2`를 넣으면 PR #114 게이트가 `BLOCKED_INPUT`으로 거부합니다(PR #116 GAPS의 float 충돌).
  - 정확한 소수 문자열 `Fraction("0.2") = 1/5`로 넣었고, 이 사실을 사전등록에 미리 적었습니다.
- **P2 음성대조가 보여 준 것:** 배치 직후에는 q×p가 387,020으로 그대로입니다(185 @ 2,092). 왜곡은 **그 뒤에 들어오는 수정 시세**가 원주가 장부를 덮을 때 생깁니다.
  - 그래서 진짜 위험은 사건 라벨보다 **장부와 시세 공급의 가격기준**에 있습니다.
  - 이번 계약은 TASK대로 사건(배치) 라벨만 검사합니다. 라벨이 RAW여도 뒤이은 시세가 수정주가면 같은 왜곡이 생길 수 있고, 이 게이트는 그것을 막지 못합니다.
- **라벨 신뢰:** 게이트는 라벨을 믿습니다. 실제로는 수정주가인데 `RAW_UNADJUSTED`로 잘못 붙은 입력은 통과합니다. 라벨의 원천은 검증하지 않았습니다(NEEDS_DATA).

## 다음 방향
- 남은 단일 결손은 **장부 · 시세 공급의 가격기준 일치**입니다. 시세를 덮을 때 그 시세의 기준도 `RAW_UNADJUSTED`인지 같은 방식으로 막는 합성 계약이 다음 한 단계로 적절합니다.
- 실제 Train 가격기준 선택은 여전히 GPT · 사용자 결정입니다.
