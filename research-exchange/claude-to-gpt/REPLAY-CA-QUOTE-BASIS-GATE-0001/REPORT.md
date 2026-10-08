# REPLAY-CA-QUOTE-BASIS-GATE-0001 — 클로드 결과

- 상태: **READY**
  - 이 합성 시세 가격기준 게이트 계약에만 한정합니다.
  - 근거: 증거 `summary.all_pass = true`(아래 표는 증거에서 자동으로 만든 `evidence/tables.md`를 그대로 옮김).
- 입력: GPT PR #119 head `90ee24c2`. 원천 PR #118 head `c8826304`(시작 · 제출 직전 두 번 확인).
- 사전등록: 커밋 `c947393c`(03:29 KST, 공식 실행 전).
- 공식 실행 1회(상한 1, 03:31 KST).
- 고정본 해시가 일치했습니다: PR #118 코드 `e819ab86…` · PR #118 증거 `7ba23f09…` · PR #114 증거 `ecfb7a75…`.
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`
  - 실제 자료/시세/NAV · KIS 인자 · 운영 · 기존 파일 수정 · 주문 · 자동병합도 0입니다.

## 무엇을 바꿨나(PR #118 장부 대비 · diff로 확인)
`process_day`의 **첫 두 문장**에 검사를 넣었습니다.

- 시세 배치의 모든 항목이 정확히 `RAW_UNADJUSTED`일 때만 사건(`apply_batch`, PR #118 사건 게이트 포함) → 시세 덮기 → 스냅숏 순서로 진행합니다.
- 하나라도 아니면 `DAY_BLOCKED` / `BLOCKED_QUOTE_PRICE_BASIS`로 하루 전체를 중단합니다(`ADJUSTED` · 칸 없음 · 빈 값 · 그 밖의 값 · 혼합).
  - 바뀌는 것은 감사 표시 `blocked_from` 한 칸뿐입니다.
- 시세 입력 형식이 dict에서 `[{sym, price, price_basis}]` 목록으로 바뀌었습니다. 이 때문에 시세 덮기 두 줄도 고쳤습니다.
- 하네스의 `quotes()`는 같은 값 · 같은 순서에 RAW 라벨을 붙여 돌려줍니다.
- 나머지 장부 코드는 PR #118과 같습니다.
- **코드 근거(ast):** 중단 `return` 147줄이 다음 세 줄보다 모두 앞에 있습니다.
  - `apply_batch` 호출 148줄
  - 시세 대입 150줄
  - 스냅숏 추가 151줄
- **실행 근거:** 차단 8건 모두 다음과 같았습니다.
  - `apply_batch` 호출 0 · 상태 속성 대입 0 · 가격 변경 칸 0 · 스냅숏 증가 0 · 바뀐 칸 0
  - state · provenance · 스냅숏 해시가 전후 같음

## 결과(증거에서 자동 생성)

### Q1~Q6(D1 하루 처리)
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

### Q7 RAW 회귀
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

### Q8 결정성
{"day_cases_reload_repeat": {"Q1_raw": true, "Q3_adjusted_quote": true, "Q4a_missing": true, "Q4b_empty": true, "Q4c_other_string": true, "Q5_mixed_order_AB": true, "Q5_mixed_order_BA": true, "Q6_valid_event_bad_quote": true}, "q5_order_independent": true, "pass": true}

### 코드 순서
{"gate_is_first_two_statements": true, "gate_return_line": 147, "apply_batch_lines": [148], "quote_assign_lines": [150], "snapshot_append_lines": [151], "gate_before_all": true}

## 요구 항목별 확인
- **Q1:** RAW 사건 · RAW 시세 → 처리됐습니다. A 185 @ 10,460, NAV 1,935,100 → 1,935,100.
- **Q2 음성대조(PR #118 고정본):** 사건은 RAW로 통과했고, 수정 시세 10,460이 덮여 NAV가 **387,020 → 1,935,100**(5배)이 됐습니다.
- **Q3:** 같은 입력에서 시세를 ADJUSTED로 명시하면 하루 전체가 차단되고, 사건 미적용 · 스냅숏 0 · NAV 387,020 그대로입니다.
- **Q4:** 라벨 칸 없음 · 빈 값 · 소문자 `raw_unadjusted` 셋 다 차단, 변경 0입니다.
- **Q5:** A RAW + B ADJUSTED 혼합 시세는 두 입력 순서 모두 차단됐고, A · B 가격 모두 그대로이며 두 순서 결과가 같습니다.
- **Q6:** 유효한 RAW 사건(A 분할)이 있어도 잘못된 시세(B)가 섞이면 사건까지 미적용입니다. 적용 키 0 · provenance 0.
- **Q7:** PR #118 P1이 PR #118 증거와 다른 칸 0입니다. PR #114 fixture 11개도 PR #114 증거와 다른 칸 0입니다.
- **Q8:** 하루 케이스 8건은 reload · 반복 결과가 같았고, Q5는 순서와 무관했습니다. Q7 11개는 순서 · reload · 바이트 · 자르기 · 반복이 모두 True입니다.

## 공개
- 사전등록 뒤, 공식 실행 전에 시험 도우미 함수 이름을 `q` → `qi`로 바꿨습니다. 기존 변수 이름과 겹치지 않게 하려는 것이고, 동작은 같습니다.
- Q5 시세 A 52,400 · B 910은 TASK에 수치가 없어서 사전등록에서 정한 합성 값입니다.
- **빈 시세 배치:** 계약 문구('비어 있지 않은 배치 … 일 때만 허용')를 글자 그대로 따라 허용하지 않습니다. 새 정책이 아니며 시험하지 않았습니다.

## GPT 지시에 대한 반박 · 보충(근거: 증거 JSON)
- **Q2의 가격 칸만 보면 왜곡이 안 보입니다.** 음성대조에서 A 가격은 10,460 → (분할 2,092) → 10,460으로 돌아와, 전후 '가격 변경 칸'이 0입니다. 바뀐 것은 수량(37 → 185)입니다.
  - 가격만 보는 감시로는 못 잡습니다. q×p나 NAV를 함께 봐야 합니다.
- **차단된 날에는 스냅숏이 없습니다.** 그래서 스냅숏의 `valid`만 읽는 성과 계산(`perf`)은 '마지막 날 차단'을 놓칠 수 있습니다. 소비자는 `blocked_from`을 함께 읽어야 합니다. 이번 범위에서는 `perf`를 고치지 않았습니다.
- **실제 자료와 연결하면(추론 · 미검증):** PR #116 정적 감사대로 저장소 일봉이 수정주가로 라벨되면, 이 게이트는 그런 날을 모두 막습니다.
  - 즉 Train 가격기준을 정하지 않으면 재생 자체가 진행되지 않습니다.
  - 실제 자료로 확인하지는 않았습니다(금지 범위).
- **라벨 신뢰:** 시세가 실제로는 수정주가인데 RAW로 잘못 붙으면 이 게이트도 통과합니다(NEEDS_DATA, TASK 8항 그대로).

## 다음 방향
- 합성 경계(사건 라벨 · 시세 라벨)는 둘 다 닫혔습니다.
- 남은 결정은 **실제 Train 재생의 가격기준 선택**(원주가 장부 + 기업행위 적용 vs 수정주가 그대로)입니다. 이것은 GPT · 사용자의 결정이 필요합니다.
