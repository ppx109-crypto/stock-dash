# REPLAY-BLOCKED-DAY-METRIC-GATE-0001 — 클로드 결과

- 상태: **READY**
  - 이 합성 차단일 지표 게이트 계약에만 한정합니다.
  - 근거: 증거 `summary.all_pass = true`(아래 표는 증거에서 자동으로 만든 `evidence/tables.md`를 그대로 옮김).
- 입력: GPT PR #121 head `46b8310b`. 원천 PR #120 head `8ed1d7d2`(시작 · 제출 직전 두 번 확인).
- 사전등록: 커밋 `777322f6`(03:40 KST, 공식 실행 전).
- 공식 실행 1회(상한 1, 03:42 KST). 사전등록 뒤 코드 수정은 없었습니다.
- 고정본 해시가 일치했습니다: PR #120 코드 `049342e8…` · PR #120 증거 `b7308516…` · PR #114 증거 `ecfb7a75…`(GPT SOURCE_PACKET의 blob과도 같음).
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`
  - 실제 TWR · MDD · 비용후수익률은 산출하지 않았습니다.
  - 가격기준 선택 · KIS · 운영 · 기존 파일 수정 · 주문 · 자동병합도 0입니다.

## 무엇을 바꿨나(PR #120 복사본 대비 · diff로 확인)
- 옛 `perf(snaps)`를 **지우고** `perf_gate(ledger)` 하나로 바꿨습니다.
  - 인자는 장부 하나뿐이고, 기본값 · 선택 인자가 없습니다.
- 판정 순서:
  1. 첫 문장에서 `ledger.blocked_from`을 읽습니다. 값이 있으면 `PERF_BLOCKED` · `from` = 그 날짜 · `LEDGER_BLOCKED`입니다.
  2. invalid 스냅숏이 있으면 `PERF_BLOCKED` · 최초 invalid 날짜 · `INVALID_SNAPSHOT`입니다.
  3. 둘 다 아니면 지표를 계산합니다.
- 차단이면 지표 4칸(일별 · 달력월 TWR · MDD · 비용후수익률)이 모두 null입니다.
- 지표는 `_daily_returns` · `_monthly_twr` · `_mdd`로만 계산하고, 호출 수를 셉니다.
- 하네스의 호출 1곳을 `perf(L.snaps)` → `perf_gate(L)`로 바꿨습니다. 장부 코드(`QuoteLedger`)는 PR #120과 같습니다.
- **M8 근거**
  - 정적(ast):
    - `perf` 함수 없음 · snaps를 받는 성과 함수 없음
    - 인자는 `ledger` 하나뿐
    - 첫 문장이 `ledger.blocked_from`을 읽음
    - 차단 return 203줄이 지표 호출 208 · 209 · 211줄보다 앞
    - `perf_gate` 호출 2곳 모두 인자 하나
  - 실행: 차단 케이스(M2 · M3 · M5 · M4 32경로)에서 지표 함수 호출이 0이었습니다.

## 결과(증거에서 자동 생성)

### 단일 장부 케이스
| # | 장부 상태 | 성과 출력 | 지표 함수 호출 | 통과 |
|---|---|---|---|---|
| M1 음성(PR120 perf(snaps)) | blocked_from 2026-01-29 · 스냅숏 [['2026-01-28', True]] | {'status': 'OK', 'all_zero': True} | — | True |
| M2 마지막 날 차단 | blocked_from 2026-01-29 · 스냅숏 [['2026-01-28', True]] | PERF_BLOCKED · from 2026-01-29 · LEDGER_BLOCKED · 지표 모두 null | 0 | True |
| M3 첫날 차단 | blocked_from 2026-01-28 · 스냅숏 0 · 옛 함수 {'exception': 'IndexError'} | PERF_BLOCKED · from 2026-01-28 · LEDGER_BLOCKED · 지표 모두 null | 0 | True |
| M5 표식 없음 + invalid | blocked_from None · 스냅숏 [['2026-01-28', True], ['2026-01-29', False]] | PERF_BLOCKED · from 2026-01-29 · INVALID_SNAPSHOT · 지표 모두 null | 0 | True |
| M6 PR120 Q1_raw | PR120 증거와 다른 칸 0 | OK · all_zero True · 일별 [] · 월 {} · MDD 0 · 비용후 None(NOT_MODELED) | 3 | True |

### M4 · M6 PR114 fixture(4경로)
| fixture | 구분 | 성과 출력(경로 1) | 지표 호출 | PR114 증거와 다른 칸 | 4경로 · 바이트 · 자르기 · 반복 | 통과 |
|---|---|---|---|---|---|---|
| M1_bonus_issue | M4_blocked | PERF_BLOCKED · from 2026-02-02 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| M2_unknown_kind | M4_blocked | PERF_BLOCKED · from 2026-02-02 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| M3_later_legit_looking_second_qm | M4_blocked | PERF_BLOCKED · from 2026-02-03 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| M4_new_symbol_first_qm | M6_normal | OK · all_zero True · 일별 ['0', '0', '0', '0'] · 월 {'2026-01': '0', '2026-02': '0'} · MDD 0 · 비용후 None(NOT_MODELED) | 12 | 0 | True · True · True · True | True |
| K1_kind_flip_reverse_split | M4_blocked | PERF_BLOCKED · from 2026-02-02 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| K2_later_independent_reverse_split | M4_blocked | PERF_BLOCKED · from 2026-02-03 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| K3_unseen_symbols | M6_normal | OK · all_zero True · 일별 ['0', '0', '0', '0'] · 월 {'2026-01': '0', '2026-02': '0'} · MDD 0 · 비용후 None(NOT_MODELED) | 12 | 0 | True · True · True · True | True |
| Q1_apply_date_changed | M4_blocked | PERF_BLOCKED · from 2026-02-02 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| Q2_m_qty_changed | M4_blocked | PERF_BLOCKED · from 2026-01-30 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| Q3_legit_looking_second_split | M4_blocked | PERF_BLOCKED · from 2026-02-03 · LEDGER_BLOCKED · 지표 모두 null | 0 | 0 | True · True · True · True | True |
| Q4_same_key_same_payload | M6_normal | OK · all_zero True · 일별 ['0', '0', '0', '0'] · 월 {'2026-01': '0', '2026-02': '0'} · MDD 0 · 비용후 None(NOT_MODELED) | 12 | 0 | True · True · True · True | True |

### M7 직렬화(단일 장부)
{"M2_last_day_blocked": [true, true], "M3_first_day_blocked": [true, true], "M5_invalid_snapshot_without_flag": [true, true], "M6_pr120_Q1_raw": [true, true]}

### M8 호출 경계
{"no_perf_function": true, "no_snapshot_only_perf": true, "signature_single_ledger": true, "first_statement_reads_blocked_from": true, "gate_return_line": 203, "metric_call_lines": [208, 209, 211], "gate_before_metrics": true, "all_calls_single_arg": true, "perf_gate_call_sites": 2, "pass": true}
차단 케이스 지표 호출 0: True

## 요구 항목별 확인
- **M1 음성대조:** PR #120 고정본의 옛 `perf(snaps)`는 D1이 차단(`blocked_from` = D1)됐는데도 `{status: OK, all_zero: true}`를 돌려줬습니다. 마지막 차단일을 놓친 것입니다.
- **M2:** 같은 장부를 `perf_gate`에 넣으면 `PERF_BLOCKED` · from D1 · `LEDGER_BLOCKED` · 지표 null입니다.
- **M3:** 스냅숏 0개 · `blocked_from` = D0도 같은 방식으로 차단됐습니다.
- **M4:** PR #114 사건 배치 차단 fixture 8개 × 4경로 모두 `PERF_BLOCKED` · from = 배치일 · `LEDGER_BLOCKED` · 지표 null입니다. PR #114 증거와 다른 칸도 0입니다(perf는 옛 칸 status · from만 비교).
- **M5:** `blocked_from`은 없고 D1 스냅숏만 invalid인 장부(직렬화 JSON에서 만듦)는 `PERF_BLOCKED` · from D1 · `INVALID_SNAPSHOT`입니다.
- **M6:** PR #120 `Q1_raw`는 PR #120 증거와 다른 칸 0입니다. PR #114 정상 fixture 3개도 다른 칸 0이며, 지표가 계산됐습니다(모두 0 · 비용후는 NOT_MODELED).
- **M7:** 단일 장부 4건은 reload 뒤 출력 · 바이트가 같았습니다. fixture 11개는 순서 · reload · 바이트 · 자르기 · 반복이 모두 True입니다.
- **M8:** 위 근거대로 True입니다.

## GPT 지시에 대한 반박 · 보충(근거: 증거 JSON)
- **옛 함수의 결함은 하나 더 있습니다.** M3에서 스냅숏이 0개인 장부를 옛 `perf(snaps)`에 넣으면 `IndexError`로 죽습니다(`old_perf_info`). 차단 표시가 아니라 예외라서, 호출하는 쪽이 이를 삼키면 다시 '정상'처럼 보일 수 있습니다.
  - 새 게이트는 `blocked_from`이 있으면 스냅숏을 읽기 전에 돌아가므로 이 경우를 막습니다.
  - 다만 '차단 표시도 없고 스냅숏도 0개'인 장부는 새 함수에서도 MDD 계산에서 예외가 납니다. 이 경우의 정책은 TASK에 없어서 새로 만들지 않았습니다. 고정 케이스에도 없습니다.
- **비용후수익률은 정상일 때도 null입니다.** 합성 경로에 비용 모델이 없어 새로 만들지 않았고(TASK 7항), `cost_model: NOT_MODELED`로 표시했습니다. '차단 시 미산출'과 '정상이지만 미모델'은 이 칸으로 구분됩니다.
- `INVALID_SNAPSHOT` 사유 이름은 TASK 5항 경우를 가리키려고 사전등록에서 정했습니다. TASK 3항이 요구한 `LEDGER_BLOCKED`는 `blocked_from` 경우에 그대로 씁니다.

## 다음 방향
- 합성 경계(사건 라벨 · 시세 라벨 · 차단일 지표)는 모두 닫혔습니다.
- 남은 것은 실제 Train 재생의 가격기준 선택입니다(원주가 + 기업행위 적용 vs 수정주가 그대로). GPT · 사용자의 결정이 필요합니다.
