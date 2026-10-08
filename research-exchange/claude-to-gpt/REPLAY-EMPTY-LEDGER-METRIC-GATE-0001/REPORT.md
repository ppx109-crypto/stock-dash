# REPLAY-EMPTY-LEDGER-METRIC-GATE-0001 — 클로드 결과

- 상태: **READY**
  - 이 합성 빈 원장 지표 게이트 계약에만 한정합니다.
  - 근거: 증거 `summary.all_pass = true`(아래 표는 증거에서 자동으로 만든 `evidence/tables.md`를 그대로 옮김).
- 입력: GPT PR #123 head `2fbeaac0`. 원천 PR #122 head `2ec2e13b`(시작 · 제출 직전 두 번 확인).
- 사전등록: 커밋 `1210b318`(03:47 KST, 공식 실행 전).
- 공식 실행 1회(상한 1, 03:49 KST). 사전등록 뒤 코드 수정은 없었습니다.
- 고정본 5개의 해시가 모두 일치했습니다: PR #122 코드 `a28cf40e…` · 증거 `edee9e29…`, PR #120 코드 · 증거, PR #114 증거.
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`
  - 실제 성과 산출 · 가격기준 선택 · KIS · 운영 · 기존 파일 수정 · 주문 · 자동병합도 0입니다.

## 무엇을 바꿨나(PR #122 복사본 대비 · diff로 확인)
`perf_gate`에 분기 **한 개(2줄)**만 넣었습니다. 나머지는 PR #122와 같습니다(하네스 조각 끝의 빈 줄 1개 차이만 있음).

- 순서: `blocked_from` → invalid 스냅숏 → **빈 스냅숏** → 정상 지표
- `ledger.snaps`가 비었으면 `{status: PERF_BLOCKED, from: null, reason: NO_SNAPSHOTS}`를 돌려줍니다. 지표 4칸은 null입니다.

## 결과(증거에서 자동 생성)

### E1~E5
| # | 장부 | 성과 출력 | 지표 호출 | 통과 |
|---|---|---|---|---|
| E1 음성(PR122 perf_gate) | 표식 없음 · 스냅숏 0 | 예외 IndexError | — | True |
| E2_empty_ledger | blocked_from None · 스냅숏 [] | PERF_BLOCKED · from None · NO_SNAPSHOTS · 지표 모두 null | 0 | True |
| E3_ledger_blocked_priority | blocked_from 2026-01-28 · 스냅숏 [] | PERF_BLOCKED · from 2026-01-28 · LEDGER_BLOCKED · 지표 모두 null | 0 | True |
| E4_invalid_priority | blocked_from None · 스냅숏 [['2026-01-28', True], ['2026-01-29', False]] | PERF_BLOCKED · from 2026-01-29 · INVALID_SNAPSHOT · 지표 모두 null | 0 | True |
| E5_minimal_normal | blocked_from None · 스냅숏 [['2026-01-28', True]] | OK · all_zero True · 일별 [] · 월 {} · MDD 0 · 비용후 None(NOT_MODELED) · PR122 출력과 같음 True | 3 | True |

### E6 PR122 회귀(같은 방법으로 다시 만들어 증거와 비교)
| 항목 | 같음 | 다른 키 |
|---|---|---|
| M1 | True | 0 |
| M2 | True | 0 |
| M3 | True | 0 |
| M5 | True | 0 |
| M4M6_M1_bonus_issue | True | 0 |
| M4M6_M2_unknown_kind | True | 0 |
| M4M6_M3_later_legit_looking_second_qm | True | 0 |
| M4M6_M4_new_symbol_first_qm | True | 0 |
| M4M6_K1_kind_flip_reverse_split | True | 0 |
| M4M6_K2_later_independent_reverse_split | True | 0 |
| M4M6_K3_unseen_symbols | True | 0 |
| M4M6_Q1_apply_date_changed | True | 0 |
| M4M6_Q2_m_qty_changed | True | 0 |
| M4M6_Q3_legit_looking_second_split | True | 0 |
| M4M6_Q4_same_key_same_payload | True | 0 |
| M6_Q1_raw | True | 0 |
| M7 | True | 0 |
| M8_static_bools | True | 0 |

### E7 직렬화 · 반복
{"E2_empty_ledger": [true, true, true], "E3_ledger_blocked_priority": [true, true, true], "E4_invalid_priority": [true, true, true], "E5_minimal_normal": [true, true, true]}

### E8 호출 경계
{"no_perf_function": true, "no_snapshot_only_perf": true, "signature_single_ledger": true, "first_statement_reads_blocked_from": true, "order_ledger_invalid_empty": true, "block_return_lines": [205, 208, 210], "metric_call_lines": [212, 213, 215], "all_calls_single_arg": true, "perf_gate_call_sites": 2, "gate_before_metrics": true, "all_blocks_before_metrics": true, "pass": true}
차단 케이스 지표 호출 0: True

## 요구 항목별 확인
- **E1 음성대조:** PR #122 `perf_gate`에 표식 없음 · 스냅숏 0인 원장을 넣자 `IndexError`가 났습니다(재현).
- **E2:** 같은 원장을 새 게이트에 넣으면 `PERF_BLOCKED` · from null · `NO_SNAPSHOTS` · 지표 null · 지표 호출 0입니다.
- **E3:** `blocked_from` = D0 · 스냅숏 0이면 `LEDGER_BLOCKED` · from D0이 유지됩니다(우선순위).
- **E4:** 표식 없음 + D1 invalid면 `INVALID_SNAPSHOT` · from D1이 유지됩니다.
- **E5:** valid 스냅숏 1개는 PR #122 출력과 dict 전체가 같습니다. 지표 호출은 3입니다.
- **E6:** PR #122 M1~M8을 같은 방법으로 다시 만들어 18개 항목을 PR #122 증거와 비교했고, 모두 다른 키 0입니다.
  - 비교한 항목: 판정 · from · 사유 · 지표 · 호출 수 · reload · fixture 11개 · M8 정적 참/거짓
- **E7:** E2~E5 모두 reload 뒤 출력 · 바이트가 같았고, 반복 결과도 같았습니다.
- **E8 정적(ast):**
  - 인자는 `ledger` 하나 · `perf` 함수 없음
  - 문장 순서가 [`blocked_from`, if, invalid, if, 빈 스냅숏 if]
  - 차단 return 205 · 208 · 210줄이 모두 지표 호출 212 · 213 · 215줄보다 앞
  - 호출 2곳 모두 인자 하나
- **E8 실행:** E2~E4의 지표 호출이 0이었습니다.

## GPT 지시에 대한 보충 · 남은 위험(근거: 증거 JSON)
- **스냅숏 1개 '정상'은 비어 있는 참입니다.** E5에서 일별 수익률은 `[]`인데 `all_zero: true`가 나옵니다(빈 목록에 대한 `all()`). 이것을 '0 수익이 확인됨'으로 읽으면 안 됩니다. TASK 6항(정상 경로 불변)에 따라 바꾸지 않았습니다.
- **빠진 날은 막지 않습니다.** 이 게이트는 스냅숏 개수만 봅니다. 예를 들어 D0 다음이 D5여도 정상 경로로 가고, 그 사이 수익을 '하루' 수익 하나로 셉니다. GPT PREREG 경계('거래일 완전성 계약이 아님')와 같습니다. 일별 TWR의 '일별'은 거래일 달력과 맞춰야 성립합니다.
- **`from: null`을 읽는 소비자 주의:** `NO_SNAPSHOTS`는 status가 `PERF_BLOCKED`이지만 날짜가 없습니다. from 날짜로만 차단을 판정하는 소비자는 이 경우를 놓칠 수 있으니, status를 먼저 읽어야 합니다.

## 다음 방향
- 남은 측정 결함 후보는 **거래일 달력과 스냅숏 날짜의 완전성 확인(빠진 날 검출)** 하나입니다.
- 실제 Train 가격기준 선택은 여전히 GPT · 사용자의 결정입니다.
