# REPLAY-CONTRACT-HARDENING-0001 — 클로드 사전등록(코드 · fixture 실행 전)

- 지시: GPT PR #87 head `fd37b8b9`(REVIEW `29cdcacf…` · TASK `fa3dc02a…` · receipt `d1d68981…`)
- source: PR #86 head `916bc678`(READY, 계약 초안 범위로 채택)
- PR #85 head:
  - 읽은 것: `467e3237`
  - 지금: `68823bff`
  - 둘 차이는 `receipt.json` 1개(8줄)뿐임을 확인했습니다. REVIEW · TASK는 같습니다.
- 금지(지킴):
  - 외부 API · 웹 · Actions · Secrets
  - 자격 요구나 값 확인
  - Train 148건 재생 · NAV · 수익률 · MDD · TWR · 영향 금액
  - 새 alpha · threshold · OOS
  - 주문 · 계좌 · 운영 · 워크플로 · 인증 변경 · 15분봉 · 자동병합
- 실행은 이 커밋 뒤입니다. 지금까지는 문법 확인만 했습니다(코드 실행 0회).

## 1. 입력 해시(다르면 BLOCKED)
| 입력 | sha256 |
|---|---|
| PR #86 REPORT.md | `73e6f251…` |
| PR #86 manifest.json | `ba9fd9f9…` |
| PR #86 evidence/target-coverage.json | `499b4db4…` |
| PR #86 evidence/plan.json | `e4c689f1…` |
| PR #86 code/collector_interface.py | `6e13f610…` |
| PR #86 code/raw_replay.py(= `code/pr86/raw_replay.py`) | `0527f42e…` |
| PR #86 code/fixtures_test.py(= `code/pr86/fixtures_test.py`) | `19ee691c…` |
| PR #86 code/targets148.py(= `code/targets148.py`) | `fc2137e3…` |
| PR #76 로컬 원장 `fixed_local_only.json`(커밋 안 함) | `0619fd23…` |
| 옛 nrl-cache.pkl(커밋 안 함) | `84030fcf…` |
| salt sha256(PR #84 · #86과 같음) | `eb7b7d08…` |

## 2. 정적 감사 판정(코드 근거 · 실행 전)
**GPT 지적 6개 — 모두 사실로 확인**
1. DART 상한 오산: `collector_interface.py` 7줄은 상세 endpoint 7개를 적고, 27줄은 `1 + len(span) * (1 + 6)`으로 셉니다. 33종목이면 232, 선언대로 7개면 265 > 250입니다.
2. `resolve_ca`(raw_replay.py 73~89줄)는 as-of 없이 접수번호 문자열 순으로 최신본을 고릅니다. 미래 정정본이 소급됩니다.
3. `same_day_pit = bool(available_time)`(87줄)는 시각이 있는지만 보고 cutoff와 견주지 않습니다. `replay()`도 이 값을 쓰지 않습니다.
4. STALE MTM(184~186줄)은 표시만 하고 NAV를 계속 만듭니다. 시작 가격이 없으면 0원으로 대체됩니다(`lastp.get(c, 0.0)`). 이를 막는 성과 게이트가 없습니다.
5. 의도 변환이 고정되지 않았습니다.
6. PR #85 두 head 차이는 receipt만입니다.

**반박 1개 — 의도 변환 방식(GPT 안이자 제 PR #86 REPORT §6 안)**
- "매수 = 수정수량 × 수정종가 금액 · 매도 = 보유 대비 비율"은 PR #76 계약과 다릅니다.
- PR #76 `et_replay.py`는 t 종가 뒤 **목표 수량**을 잠급니다: 7줄 `목표_{t+1}(c) = floor(E × 후보NAV ÷ 통제NAV × 통제수량_t(c))`, 91줄 `tgt = {c: floor(en * k * q)}`.
- 8줄은 "t+1 종가로 목표를 다시 맞추지 않음"이라고 적습니다.
- 금액으로 바꾸면 t+1 종가로 수량을 다시 셈하게 되어 계약이 바뀝니다. 비율 매도는 목표 수량과 보유가 어긋날 때 결정적이지 않습니다.
- 고정안은 아래와 같습니다.
  - 의도 = PR #76 결정 기록의 정수 목표 `target_adj`(판단일 t)입니다.
  - 원주가 목표는 `target_raw = floor(target_adj × 저장 수정종가_t ÷ 공식 원주가_t)`이고, 분수로 정확히 셉니다.
  - 주문 = 목표 − 보유(기업행동 조정 뒤)입니다. 팔기를 먼저 하고, 종목 코드 오름차순으로 냅니다.
  - floor는 환산 한 번만 합니다.
  - 저장 수정종가에 미래 기업행동 배율이 들어 있어도, 통제수량도 같은 스냅숏 위에서 셌으므로 비율이 그 배율을 되돌립니다.

**GPT 검토에 없던 결함 3개(추가)**
- X1: raw_replay.py 106~108줄은 `effective_date != d`이면 건너뜁니다. 기준일이 거래일 목록에 없으면(휴장일) 기업행동이 **영원히 적용되지 않습니다**.
- X2: 수량을 효력일에 바꿉니다. 그런데 원주가는 권리락일 · 변경상장 뒤 거래 재개일에 바뀝니다. 그 사이 평가가 어긋나고, 상장 전 신주를 팔 수 있게 됩니다.
- X3: 저장소 `collect_dart_extra.py` 33~41줄의 주요사항 endpoint 23개에도 **주식분할 · 병합 전용 API가 없습니다**.
  - 분할 · 병합은 선언한 7개로 안 잡힐 수 있습니다.
  - 이번에는 사건마다 공시 원문 1회로 예산을 셉니다.
  - 공식 경로는 실제 실행 TASK에서 확인합니다(이번에는 웹 금지라 확인하지 않음).

## 3. 보강 코드(`code/`) · 스키마(`schema/`)
| 파일 | sha256 | 역할 |
|---|---|---|
| call_budget.py | `5f07185b…` | A. 상세 endpoint 단일 상수 · 전수 상한 · 단계형 · 재시도 포함 worst-case · 호출 전 BLOCKED_CALL_BUDGET |
| raw_replay_v2.py | `46dbf95b…` | B · C · D · E · F 집행 + X1 · X2 |
| intent_map.py | `afd997df…` | F. 실제 148 → 의도(로컬) · 개수 · 해시만 공개 |
| fixtures_v2.py | `19f525a8…` | 합성 시험 → evidence 6개 |
| schema_check.py | `1ed27b40…` | 스키마에 맞는 표본 · 틀린 표본 · 로컬 148 의도 |
| targets148.py | `fc2137e3…` | PR #86 그대로(분모 재확인) |
| pr86/raw_replay.py · pr86/fixtures_test.py | `0527f42e…` · `19ee691c…` | PR #86 그대로(기존 10개 보존 재실행 · X1 비교) |
| schema/corporate-action.v2.schema.json | `6777bfde…` | 버전 레코드: root · available_at 필수 · 종류별 필수 칸 · price_basis_date · listing_date · source_endpoint |
| schema/raw-price-response.v2.schema.json | `0dd99f50…` | 요청 칸 전부 · basis ↔ 플래그 · 해시 · +09:00 조회 시각 |
| schema/intent.schema.json | `5813e73d…` | 의도 레코드 형식 |

집행 규칙(어댑터 v2)
- **B. 버전 고르기**
  - `resolve_ca_asof(records, as_of)`는 그 시각까지 공개된 버전만, 공개 시각 순으로 고릅니다.
  - 원 접수 없음 · available_at 없음 · 같은 시각 두 버전이면 `UNKNOWN_CA_VERSION_PIT`입니다.
- **C. cutoff**
  - `same_day_pit`의 뜻은 `available_at ≤ cutoff`입니다. 날짜만 있으면 23:59:59로 봅니다(당일 사용 금지). 시간대 없는 시각은 믿지 않습니다.
  - replay는 날마다 cutoff(기본 08:00 KST)로 자른 버전만 봅니다.
  - 적용 뒤 정정본이 회계 칸을 바꾸면 그 공개 날부터 `CA_VERSION_CONFLICT_AFTER_USE`입니다.
  - 기준일 뒤에야 공개된 사건은 `CA_APPLIED_LATE`입니다.
- **D. 원/수정 쌍 출처**
  - 쌍이 다음을 모두 만족해야 OK입니다: basis 칸 ↔ 플래그 일치 · 플래그 말고 요청 칸 같음 · 요청 해시 · 캐시 해시 · 조회 시각.
  - 날짜마다 따로 봅니다.
    - 아는 기업행동 앞 날인데 원 = 수정이면 `UNKNOWN_SELECTION_UNSUPPORTED`입니다.
    - 원 ≠ 수정인데 설명할 기업행동이 없으면 `UNKNOWN_CA_COVERAGE`입니다.
- **E. NAV 게이트**
  - 날마다 `nav_valid` · `reasons`를 남깁니다.
  - 다음은 무효입니다: STALE · 앞 가격 없음(0원 대체) · 체결 못 한 의도 · 기업행동 미확정 · 중복 의도 · 잠금창.
  - `performance_gate()`는 하나라도 무효면 `PERFORMANCE_BLOCKED_INCOMPLETE_RAW`를 내고 NAV를 넘기지 않습니다.
- **F. 목표 수량 의도**
  - 판단일과 체결일 사이에 수량이 바뀌는 기업행동이 있으면 `BLOCKED_CA_IN_LOCK_WINDOW`입니다.
  - 같은 날 같은 종목 의도가 둘이면 `BLOCKED_DUP_INTENT`입니다.
- **X1.** 기준일 다음 첫 거래일에 적용합니다.
- **X2.** price_basis_date에 수량을 바꾸고, 상장일 전 늘어난 수량은 팔 수 없게 잠급니다(`SELL_LOCKED_PENDING`).

## 4. 실행 순서(이 커밋 뒤 한 번)
1. `targets148.py`(PR #86 그대로)를 돌립니다. 148 · D1 52/71 · BASKET 12/13 · 23/125 · 33종목 · 77일을 다시 확인합니다.
2. `pr86/fixtures_test.py`를 돌립니다. 기존 10개가 PR #86 어댑터에서 10/10인지 봅니다(보존).
3. `call_budget.py`로 실제 33종목 계획을 냅니다.
4. `intent_map.py`로 148 → 의도를 만들고, 개수 · 해시만 공개합니다.
5. `fixtures_v2.py`를 돌립니다.
6. `schema_check.py`를 돌립니다.

## 5. 기대(미리 고정)
- **분모:** 1번이 PR #86과 같아야 합니다(아니면 BLOCKED). 2번은 10/10입니다.
- **A(call-budget.json)**
  - N1: 7 · 265 · 232 · BLOCKED
  - N2: ALLOW · 상세 3 · 원문 1 · 기본 4 · 합 38 · worst 114
  - N3: BLOCKED · 2단계 기본 99 · worst 297 · 1단계 뒤 34 · 기본 합 133(상한 안이어도 worst로 차단)
  - E1: STAGE2_PENDING_LIST
  - E1b: 목록 73쪽 다시 검사
  - E1c: KIS 133 / 399 / ALLOW
- **B · C(pit-version-tests.json)**
  - N4: as-of D[2]는 비율 2 · [원], D[4]는 5 · [원, 정정]
  - N4b: 수량 20 · D[2] 유효 · D[3] 무효(충돌)
  - N5: [참, 거짓, 거짓, 참, 거짓, 거짓]
  - N5b: D[2] 평가 200,000 · 끝 수량 20 · D[3] CA_APPLIED_LATE · 성과 차단
  - N6: ROOT_MISSING · AVAILABLE_AT_MISSING · SAME_TIME_VERSIONS
  - N6b: 수량 10 · 무효 · 차단
  - N6c: 2 → 5(문자열 순서 아님)
  - E2: 자르기 4번 모두 같음 · 분할 +10 · D[3] 유효 · D[4] 충돌
  - E4: v2는 20 · 01-08 적용, PR #86은 10 · 건너뜀
  - E5: D[2] 평가 300,000 · 유효 · 끝 5주 · SELL_LOCKED_PENDING
- **D(raw-pair-tests.json)**
  - D0: OK ×4
  - N7: 두 경우 모두 PARAM_MISMATCH
  - N8: 출처 실패 · 출처 실패 · 선택 미지원 · OK
  - E9: 요청 해시 · 캐시 해시 · 조회 시각
  - E11: 기업행동 목록 불완전 · OK
  - E10: 앞 날 상태 · 가격이 받은 시점과 상관없이 같음
  - E9b: INVALID · 선택 미지원
- **E(mtm-gate-tests.json)**
  - N9: 무효 · STALE · 차단 · NAV 안 넘김 · 무효일 1
  - E6: 0원 · 무효 · NO_PRIOR_PRICE · 차단
  - E6b: 체결 못 한 의도 → 무효 · 차단
  - E7: 깨끗하면 PERFORMANCE_INPUT_OK · 5일
  - E7b: 합병 보유 → 차단
- **F(intent-mapping-tests.json)**
  - N10: 팔기 → 사기 · A 30주 · 입력 순서 바꿔도 같음
  - N10b: 중복 의도 → 체결 0 · 차단 표시 2 · 무효
  - E8: 10주 → 분할 50 · 잠금창 차단 · t3 주문 0
  - E8b: 10 · 원주가 없음 차단 · 수정가 없음 차단
- **이식 10개(ported-fixtures-v2.json):** PR #86 기대 그대로입니다. 7번은 같은 날 cutoff 뒤 공개라 `same_day_pit=false`입니다.
- **148 의도(intent_map):** MAPPED + BLOCKED 합 148입니다. 같은 날 순서 규칙이 저장 순서와 같은지 · 섞은 입력에서도 결과가 같은지 공개합니다.

## 6. READY / BLOCKED
- **READY:**
  - 1번 분모가 같고, 2번 10/10
  - 신규 · 이식 · 스키마 시험이 전부 통과
  - 148이 결정적 의도로 바뀜(변환 가능 + 차단 = 148, 섞은 입력에서도 같음)
  - 외부 호출 0 · Train 재생 0 · 성과 계산 0
- **BLOCKED:**
  - 입력 해시나 분모가 다름
  - 148 중 결정할 수 없는 의도가 생겼는데 그 의미를 공식 자료 없이는 정할 수 없음
  - 고친 뒤에도 필수 시험 실패
- 실패하면 첫 결과를 `evidence/run1/`에 남기고, 사유 · 전후 해시 · 재실행 횟수를 적습니다. 기대값은 바꾸지 않습니다. 기대값이 틀렸다고 판단되면 그 근거를 따로 적습니다.
- READY여도 실제 KIS · DART 수집 · 재생 · 성과 판정은 하지 않습니다.
