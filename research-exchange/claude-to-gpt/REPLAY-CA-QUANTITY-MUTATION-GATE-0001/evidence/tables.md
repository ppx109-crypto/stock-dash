## M1~M4
| # | 배치 | 판정 | 키별 status | 수량 | 배치 전후 state·prov 해시 | 바뀐 칸(순서 1 / 2) | 성과 | 4경로 · 반복 · 바이트 · 자르기 | 통과 |
|---|---|---|---|---|---|---|---|---|---|
| M1_bonus_issue | 2026-02-02 | BATCH_ABORTED | `A|bonus_issue|2|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| M2_unknown_kind | 2026-02-02 | BATCH_ABORTED | `A|unknown_qty_event|2|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| M3_later_legit_looking_second_qm | 2026-02-03 | BATCH_ABORTED | `A|bonus_issue|2|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True · True | True |
| M4_new_symbol_first_qm | 2026-01-30 | COMMITTED | `B|reverse_split|1/5|2026-01-30` OK · `C|bonus_issue|2|2026-01-30` OK | A 185 · B 15 · C 80 | 바뀜 | pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov / pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov | OK · 0 | True · True · True · True | True |

## K1~K3 · Q1~Q4 회귀(PR112 증거와 칸별 비교)
| # | 배치 | 판정 | 키별 status | 수량 | 배치 전후 state·prov 해시 | 바뀐 칸(순서 1 / 2) | 성과 | 4경로 · 반복 · 바이트 · 자르기 | 통과 |
|---|---|---|---|---|---|---|---|---|---|
| K1_kind_flip_reverse_split | 2026-02-02 | BATCH_ABORTED | `A|reverse_split|1/5|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| K2_later_independent_reverse_split | 2026-02-03 | BATCH_ABORTED | `A|reverse_split|1/5|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True · True | True |
| K3_unseen_symbols | 2026-01-30 | COMMITTED | `B|reverse_split|1/5|2026-01-30` OK · `C|split|2|2026-01-30` OK | A 185 · B 15 · C 80 | 바뀜 | pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov / pos.B.0,pos.B.1,pos.C.0,pos.C.1,applied,prov | OK · 0 | True · True · True · True | True |
| Q1_apply_date_changed | 2026-02-02 | BATCH_ABORTED | `A|split|5|2026-02-02` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-02-02` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-02) | True · True · True · True | True |
| Q2_m_qty_changed | 2026-01-30 | BATCH_ABORTED | `A|split|10|2026-01-29` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-01-30` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-01-30) | True · True · True · True | True |
| Q3_legit_looking_second_split | 2026-02-03 | BATCH_ABORTED | `A|split|2|2026-02-03` BLOCKED_AMBIGUOUS_EVENT_IDENTITY · `B|reverse_split|1/5|2026-02-03` OK | A 185 · B 75 | 같음 | 0 / 0 | PERF_BLOCKED(2026-02-03) | True · True · True · True | True |
| Q4_same_key_same_payload | 2026-01-30 | COMMITTED | `A|split|5|2026-01-29` DUPLICATE_IGNORED · `B|reverse_split|1/5|2026-01-30` OK | A 185 · B 15 | 바뀜 | pos.B.0,pos.B.1,applied,prov / pos.B.0,pos.B.1,applied,prov | OK · 0 | True · True · True · True | True |

PR112 증거와 다른 칸 수: K1_kind_flip_reverse_split 0, K2_later_independent_reverse_split 0, K3_unseen_symbols 0, Q1_apply_date_changed 0, Q2_m_qty_changed 0, Q3_legit_looking_second_split 0, Q4_same_key_same_payload 0

## 음성대조군(PR112 고정본 · 순서 1)
| 입력 | 판정 | 키별 status | 수량 | 기대 출처 | 일치 |
|---|---|---|---|---|---|
| I1 그대로 | COMMITTED | `A|bonus_issue|2|2026-02-02` OK | A 370 | PR112 증거 | True |
| M1_bonus_issue | COMMITTED | `A|bonus_issue|2|2026-02-02` OK · `B|reverse_split|1/5|2026-02-02` OK | A 370 · B 15 | 유도 | True |
| M2_unknown_kind | COMMITTED | `A|unknown_qty_event|2|2026-02-02` OK · `B|reverse_split|1/5|2026-02-02` OK | A 370 · B 15 | 유도 | True |
| M3_later_legit_looking_second_qm | COMMITTED | `A|bonus_issue|2|2026-02-03` OK · `B|reverse_split|1/5|2026-02-03` OK | A 370 · B 15 | 유도 | True |
| M4_new_symbol_first_qm | COMMITTED | `B|reverse_split|1/5|2026-01-30` OK · `C|bonus_issue|2|2026-01-30` OK | A 185 · B 15 · C 80 | 유도 | True |

## 참고 N1 · N2(판정 제외)
{"N1_non_qm_identity_ratio": {"input": {"sym": "A", "kind": "name_change", "m_qty": "1", "m_price": "1", "apply_date": "2026-02-02", "src": "RN"}, "verdict": "COMMITTED", "status": {"A|name_change|1|2026-02-02": "OK"}, "A_qty": "185"}, "N2_bad_ratio_not_qm": {"input": {"sym": "A", "kind": "bonus_issue", "m_qty": "2", "m_price": "1/4", "apply_date": "2026-02-02", "src": "RX"}, "verdict": "BATCH_ABORTED", "status": {"A|bonus_issue|2|2026-02-02": "BLOCKED_RATIO_PRODUCT"}, "A_qty": "185"}}
