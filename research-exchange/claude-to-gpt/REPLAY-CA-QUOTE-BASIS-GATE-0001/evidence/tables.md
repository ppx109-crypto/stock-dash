## Q1~Q6(D1 하루 처리)
| # | 하루 판정 | 처리 뒤 수량@가격 | state·prov·snap 해시 | 바뀐 칸 | apply_batch 호출 | 대입 | 가격 변경 칸 | 스냅숏 증가 | NAV D0 → D1 | 통과 |
|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | COMMITTED | A 185@10460 | 바뀜 | pos,applied,prov,snaps | 1 | 3 | 1 | 1 | 1935100 → 1935100 | True |
| Q2 음성(PR118) | COMMITTED | A 185@10460 | 바뀜 | pos,applied,prov,snaps | None | None | 0 | 1 | 387020 → 1935100 | True |
| Q3_adjusted_quote | DAY_BLOCKED · BLOCKED_QUOTE_PRICE_BASIS · 막힌 A | A 37@10460 | 같음 | 0 | 0 | 0 | 0 | 0 | 387020 → 387020 | True |
| Q4a_missing | DAY_BLOCKED · BLOCKED_QUOTE_PRICE_BASIS · 막힌 A | A 37@52300 | 같음 | 0 | 0 | 0 | 0 | 0 | 1935100 → 1935100 | True |
| Q4b_empty | DAY_BLOCKED · BLOCKED_QUOTE_PRICE_BASIS · 막힌 A | A 37@52300 | 같음 | 0 | 0 | 0 | 0 | 0 | 1935100 → 1935100 | True |
| Q4c_other_string | DAY_BLOCKED · BLOCKED_QUOTE_PRICE_BASIS · 막힌 A | A 37@52300 | 같음 | 0 | 0 | 0 | 0 | 0 | 1935100 → 1935100 | True |
| Q5_mixed_order_AB | DAY_BLOCKED · BLOCKED_QUOTE_PRICE_BASIS · 막힌 B | A 37@52300 · B 75@905 | 같음 | 0 | 0 | 0 | 0 | 0 | 2002975 → 2002975 | True |
| Q5_mixed_order_BA | DAY_BLOCKED · BLOCKED_QUOTE_PRICE_BASIS · 막힌 B | A 37@52300 · B 75@905 | 같음 | 0 | 0 | 0 | 0 | 0 | 2002975 → 2002975 | True |
| Q6_valid_event_bad_quote | DAY_BLOCKED · BLOCKED_QUOTE_PRICE_BASIS · 막힌 B | A 37@52300 · B 75@905 | 같음 | 0 | 0 | 0 | 0 | 0 | 2002975 → 2002975 | True |

Q5 두 순서 결과 같음: True

## Q7 RAW 회귀
- PR118 P1: 다른 칸 0 · 통과 True

| PR114 fixture | 판정 | 수량 | 다른 칸 | 바뀐 칸 목록 같음 | 4경로 · 바이트 · 자르기 · 반복 | 통과 |
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

## Q8 결정성
{"day_cases_reload_repeat": {"Q1_raw": true, "Q3_adjusted_quote": true, "Q4a_missing": true, "Q4b_empty": true, "Q4c_other_string": true, "Q5_mixed_order_AB": true, "Q5_mixed_order_BA": true, "Q6_valid_event_bad_quote": true}, "q5_order_independent": true, "pass": true}

## 코드 순서
{"gate_is_first_two_statements": true, "gate_return_line": 147, "apply_batch_lines": [148], "quote_assign_lines": [150], "snapshot_append_lines": [151], "gate_before_all": true}
