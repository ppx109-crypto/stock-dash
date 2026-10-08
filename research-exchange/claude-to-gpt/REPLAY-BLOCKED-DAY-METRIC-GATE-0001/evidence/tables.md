## 단일 장부 케이스
| # | 장부 상태 | 성과 출력 | 지표 함수 호출 | 통과 |
|---|---|---|---|---|
| M1 음성(PR120 perf(snaps)) | blocked_from 2026-01-29 · 스냅숏 [['2026-01-28', True]] | {'status': 'OK', 'all_zero': True} | — | True |
| M2 마지막 날 차단 | blocked_from 2026-01-29 · 스냅숏 [['2026-01-28', True]] | PERF_BLOCKED · from 2026-01-29 · LEDGER_BLOCKED · 지표 모두 null | 0 | True |
| M3 첫날 차단 | blocked_from 2026-01-28 · 스냅숏 0 · 옛 함수 {'exception': 'IndexError'} | PERF_BLOCKED · from 2026-01-28 · LEDGER_BLOCKED · 지표 모두 null | 0 | True |
| M5 표식 없음 + invalid | blocked_from None · 스냅숏 [['2026-01-28', True], ['2026-01-29', False]] | PERF_BLOCKED · from 2026-01-29 · INVALID_SNAPSHOT · 지표 모두 null | 0 | True |
| M6 PR120 Q1_raw | PR120 증거와 다른 칸 0 | OK · all_zero True · 일별 [] · 월 {} · MDD 0 · 비용후 None(NOT_MODELED) | 3 | True |

## M4 · M6 PR114 fixture(4경로)
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

## M7 직렬화(단일 장부)
{"M2_last_day_blocked": [true, true], "M3_first_day_blocked": [true, true], "M5_invalid_snapshot_without_flag": [true, true], "M6_pr120_Q1_raw": [true, true]}

## M8 호출 경계
{"no_perf_function": true, "no_snapshot_only_perf": true, "signature_single_ledger": true, "first_statement_reads_blocked_from": true, "gate_return_line": 203, "metric_call_lines": [208, 209, 211], "gate_before_metrics": true, "all_calls_single_arg": true, "perf_gate_call_sites": 2, "pass": true}
차단 케이스 지표 호출 0: True
