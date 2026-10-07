# DATA-0001 PREREG-LOCK — 시점별 연구증거 계약 · 오프라인 검증기

- 지시: PR #20 head `8ac5377ac934c67e7909208b1a55b9e9c5a3503d`. source PR #19 head `1d295ee32e16e05bbed6fe41f60b8efe44106bf6`.
- 이 문서와 `fixtures/fixtures.json`(만드는 도우미 `fixtures/make_fixtures.py` 포함)은 **검증기 · 스키마 · 시험 실행기를 쓰기 전에** 결과 가지의 첫 커밋으로 잠급니다.
- 잠그기 전에 본 것: PR #20 파일, REPLAY-0001 커널 계약, REPLAY-0002 GAPS(G1~G12). 기존 수집 코드는 아직 열지 않았습니다(매핑은 잠근 뒤).
- 성공의 뜻은 **"계약과 오프라인 검증기가 합성 결함을 막는다"**뿐입니다. 실제 자료가 수집됐거나, 전략이 수익이 나거나, 모의투자 준비가 끝났다는 뜻이 아닙니다. `PAPER_VALIDATION_READY=false`

## 1. 공통 봉투(envelope) — 모든 레코드 필수
`record_id, record_type, schema_version, security_id, market, source_system, source_endpoint_or_report, source_mode, as_of, available_at, fetched_at, version, revision_of, is_correction, raw_payload_sha256 또는 raw_ref, normalized_sha256, ingest_run_id, collector_version, created_at, public_ok, evidence_ref, payload`(`corp_code`는 있으면 씀)

- 시각 필드(`as_of, available_at, fetched_at, created_at`와 payload 안의 `*_at`)는 반드시 `+09:00`이 붙어야 합니다.
- `normalized_sha256` = sha256(payload를 `sort_keys`, 구분자 `,` `:`, `ensure_ascii=False`로 직렬화한 UTF-8).
- `source_mode`는 `OBSERVED_MARKET`(시장 · 공시 자료), `HISTORICAL_MODEL`, `OBSERVED_KIS_PAPER`, `SYNTHETIC` 중 하나입니다.

## 2. 레코드 종류
| 종류 | payload 핵심 |
|---|---|
| PRICE_BAR_RAW | date, session, open, high, low, close, volume, `adjusted=false`. 조정 관련 필드(`adj_basis`, `adj_factor`)는 있으면 안 됨 |
| PRICE_BAR_ADJ | 위와 같되 `adjusted=true`, `adj_basis` |
| UNIVERSE_SNAPSHOT | date, market, complete, members[{security_id, status}] |
| SECURITY_EVENT | kind ∈ {LISTING, DELISTING, MARKET_MOVE, CODE_CHANGE}, effective_at |
| TRADING_STATUS | status ∈ {TRADING, HALTED}, effective_at |
| CORP_ACTION | kind, ratio, record_date, effective_date, rcept_no, rcept_at — 모두 필수 |
| DART_FILING | rcept_no, rcept_dt, rcept_at(시각을 모르면 null), time_known, report_nm, original_rcept_no |
| INVESTOR_FLOW | trade_date(as_of = 그날 00:00), 투자자별 값 |
| FINANCIAL | period_end, filing_record(`id@ver`), values |
| SIGNAL | strategy_id, strategy_hash, signal_id, signal_at, decision_at, earliest_order_at, price_basis, inputs[`id@ver`], cutoff_hash = sha256(정렬한 inputs를 `\n`으로 이은 것) |
| ORDER_EVENT | order_id, event ∈ {INTENT, ACCEPTED, REJECTED, CANCELLED, FILLED}, at, seq(선택) |
| FILL | order_id, side, qty, price. HISTORICAL_MODEL은 `model{bar, price_field, rule_id, slippage_in_price}` |
| COST_SCHEDULE | component ∈ {FEE, TAX, SLIPPAGE}, rate, valid_from, valid_to(포함, null = 열림), source_ref |
| ACCOUNT_STATE | cash, nav, alloc_won, inputs[`id@ver`] (as_of = 그 시점) |

## 3. 검증 규칙(레코드를 들어온 순서로 처리, 첫 위반이 거부 사유)
1. `ENVELOPE_MISSING`: 봉투 필수 필드 없음
2. `PRIVACY_FIELD`: 봉투나 payload 어디든 다음 키가 있음 — `account_no, acct_no, cano, broker_order_no, odno, raw_response, appkey, appsecret, access_token, session_url`
3. 시각 형식
   - `NO_TZ`: 시각에 offset이 없음
   - `NOT_KST`: offset이 `+09:00`이 아님
4. `HASH_MISMATCH`: normalized_sha256이 payload 계산값과 다름
5. 시각 순서
   - `AVAILABLE_BEFORE_ASOF`: available_at < as_of
   - `FETCHED_BEFORE_AVAILABLE`: fetched_at < available_at
6. append-only: 같은 `(record_id, version)`이 이미 받아졌을 때
   - normalized_sha256이 같으면 `DUPLICATE_IGNORED`(거부 아님, 세기만)
   - 다르면 `OVERWRITE_REJECTED`
7. 정정 연결(lineage)
   - version 1은 `revision_of=null`, `is_correction=false`
   - version n>1은 `revision_of = record_id@(n-1)`이 이미 받아진 같은 종류의 레코드이고 `is_correction=true`
   - 자기 자신이나 더 뒤 판을 가리키면 `LINEAGE_CYCLE`, 그 밖의 위반은 `LINEAGE_BROKEN`
8. 종류별
   - PRICE_BAR_RAW: adjusted≠false이거나 조정 필드가 있으면 `ADJUSTED_AS_RAW`
   - PRICE_BAR_ADJ: adjusted≠true이면 `RAW_AS_ADJUSTED`
   - SECURITY_EVENT: kind가 목록 밖이거나 effective_at이 없으면 `BAD_SECURITY_EVENT`
   - CORP_ACTION: 필수값이 하나라도 null이면 `CORP_ACTION_INCOMPLETE`
   - DART_FILING
     - time_known=false인데 available_at < (rcept_dt 다음날 00:00)이면 `DATE_ONLY_TOO_EARLY`
     - time_known=true인데 available_at < rcept_at이면 `AVAILABLE_BEFORE_RCEPT`
   - INVESTOR_FLOW: available_at < trade_date 15:30이면 `FLOW_TOO_EARLY`
   - FINANCIAL
     - filing_record가 아직 안 받아졌으면 `INPUT_UNKNOWN`
     - available_at < filing의 available_at이면 `FINANCIAL_BEFORE_FILING`
   - SIGNAL: 다음 순서로 봅니다.
     1. signal_at ≤ decision_at ≤ earliest_order_at가 아니면 `SIGNAL_TIME_ORDER`
     2. 입력이 받아진 적 없으면 `INPUT_UNKNOWN`
     3. 입력의 available_at > decision_at이면 `INPUT_AFTER_DECISION`
     4. price_basis=RAW인데 PRICE_BAR_ADJ를 입력으로 쓰면 `BASIS_MIX`
     5. cutoff_hash가 맞지 않으면 `CUTOFF_HASH_MISMATCH`
   - ACCOUNT_STATE
     - 입력이 받아진 적 없으면 `INPUT_UNKNOWN`
     - 입력의 available_at > as_of이면 `INPUT_AFTER_ASOF`
   - ORDER_EVENT
     - 같은 order_id에 같은 at인 앞선 사건이 있는데 두 사건 중 하나라도 seq가 없거나 seq가 같으면 `AMBIGUOUS_ORDER_SEQ`
     - 순서 위반이면 `BAD_ORDER_TRANSITION`. 허용 순서: INTENT가 처음 → ACCEPTED · REJECTED는 INTENT 뒤 → FILLED · CANCELLED는 ACCEPTED 뒤(FILLED는 여러 번 가능)
   - FILL
     - OBSERVED_KIS_PAPER: evidence_ref가 없으면 `OBSERVED_NO_EVIDENCE`, `^ev_[0-9a-f]{16}$` 모양이 아니면 `EVIDENCE_REF_NOT_PSEUDONYMOUS`
     - HISTORICAL_MODEL: model 4필드가 빠지면 `MODEL_FILL_INCOMPLETE`, evidence_ref가 있으면 `SOURCE_MODE_MIX`
   - COST_SCHEDULE: source_ref나 valid_from이 없으면 `COST_SOURCE_MISSING`

## 4. 조회(시점 질의) — 추정 금지
- `asof(record_id, t)`: available_at ≤ t인, 받아진 판 가운데 가장 큰 판(`id@v`). 없으면 `NONE`.
- `universe(date, market, t)`: payload.date = date이고 available_at ≤ t인 스냅숏의 최신 판을 씁니다.
  - 그런 스냅숏이 없으면 `UNKNOWN:NO_SNAPSHOT`
  - complete=false이면 `UNKNOWN:INCOMPLETE`
  - 그 밖에는 members 정렬 목록. 다른 날짜 스냅숏이나 현재 목록으로 대신하지 않습니다.
- `status(security, t)`: available_at ≤ t이고 effective_at ≤ t인 상태 레코드 가운데 effective_at이 가장 늦은 것을 씁니다. 없으면 `UNKNOWN`(봉이 없다고 정지로 보지 않음).
- `corp(security, date, t)`: available_at ≤ t이고 effective_date ≤ date인 기업행동의 kind 정렬 목록. 없으면 `NONE_KNOWN`.
- `cost(component, date, t)`: available_at ≤ t인 schedule(record_id별 최신 판) 가운데 date를 덮는 것을 셉니다.
  - 0개인데 그 component의 schedule이 있으면 `UNKNOWN:GAP`, 아예 없으면 `UNKNOWN:NONE`
  - 2개 이상이면 `UNKNOWN:OVERLAP`
  - 1개면 rate 문자열

## 5. 고정 fixture 42개(기대 판정 — `fixtures/fixtures.json`이 기계용 원본)
날짜 D=2026-01-05, D2=2026-01-06. 거부는 `[레코드 순번(0부터), 규칙]`.

| id | 내용 | 기대 |
|---|---|---|
| FX01 | 정상 원주가 봉 | 거부 없음 · asof → bar@1 |
| FX02 | 최초판 + 정정판(D2 08:00 공개) | 거부 없음 · asof(D 16:00) bar@1 · asof(D2 09:00) bar@2 |
| FX03 | 같은 id@1을 다른 값으로 다시 | [1, OVERWRITE_REJECTED] · asof bar@1 |
| FX04 | 같은 id@1 같은 값 재전달 | 거부 없음 · 중복 1 |
| FX05 | available_at에 offset 없음 | [0, NO_TZ] |
| FX06 | offset +00:00 | [0, NOT_KST] |
| FX07 | available_at < as_of | [0, AVAILABLE_BEFORE_ASOF] |
| FX08 | fetched_at < available_at | [0, FETCHED_BEFORE_AVAILABLE] |
| FX09 | 15:40 공개 봉을 15:15 결정 신호가 씀 | [1, INPUT_AFTER_DECISION] |
| FX10 | v1(D 15:40) · v2(D2 10:00) 뒤 D2 09:00 결정 신호가 v1을 씀 / v2를 씀 | [3, INPUT_AFTER_DECISION] |
| FX11 | v1 없이 v2 | [0, LINEAGE_BROKEN] |
| FX12 | v2가 자기(bar@2)를 가리킴 | [1, LINEAGE_CYCLE] |
| FX13 | v2인데 is_correction=false | [1, LINEAGE_BROKEN] |
| FX14 | RAW에 adjusted=true | [0, ADJUSTED_AS_RAW] |
| FX15 | RAW에 adj_basis 필드 | [0, ADJUSTED_AS_RAW] |
| FX16 | normalized_sha256 틀림 | [0, HASH_MISMATCH] |
| FX17 | D 스냅숏(08:30 공개) | universe(D, D 09:00) [S001, S002] · universe(D2, D2 09:00) UNKNOWN:NO_SNAPSHOT · universe(D, D 08:00) UNKNOWN:NO_SNAPSHOT |
| FX18 | complete=false 스냅숏 | universe(D, D 09:00) UNKNOWN:INCOMPLETE |
| FX19 | 거래 08:00 · 정지 10:00 · 재개 14:00 | status 09:30 TRADING · 11:00 HALTED · 15:00 TRADING · 다른 종목 UNKNOWN |
| FX20 | 정지 효력 10:00, 공개 10:05 | status 10:02 TRADING · 10:06 HALTED |
| FX21 | 분할 1:5, 접수 D 16:10, 효력 01-08 | corp(01-08, D 15:00) NONE_KNOWN · corp(01-08, D2 09:00) [SPLIT] · corp(01-07, D2 09:00) NONE_KNOWN |
| FX22 | 기업행동 ratio 없음 | [0, CORP_ACTION_INCOMPLETE] |
| FX23 | 장중 공시 11:20 → 15:15 결정 신호 | 거부 없음 |
| FX24 | 장후 공시 17:30 → D 15:15 신호 / D2 15:15 신호 | [1, INPUT_AFTER_DECISION] |
| FX25 | 날짜만 아는 공시를 D 09:00 공개로 / 다른 공시 D2 00:00 공개 | [0, DATE_ONLY_TOO_EARLY] |
| FX26 | 정정공시(v2, 원 접수번호 연결) | 거부 없음 · asof(D 13:00) filing@1 · asof(D2 09:00) filing@2 |
| FX27 | 관측 모의체결 evidence_ref 없음 | [0, OBSERVED_NO_EVIDENCE] |
| FX28 | 숫자 주문번호 모양 evidence / 정상 ev_ 모양 | [0, EVIDENCE_REF_NOT_PSEUDONYMOUS] |
| FX29 | payload broker_order_no / 봉투 account_no | [0, PRIVACY_FIELD], [1, PRIVACY_FIELD] |
| FX30 | model price_field 없음 / HISTORICAL_MODEL에 evidence_ref | [0, MODEL_FILL_INCOMPLETE], [1, SOURCE_MODE_MIX] |
| FX31 | FEE 01-01~06-30, 07-02~ | cost(FEE, 03-02) 0.00015 · cost(FEE, 07-01) UNKNOWN:GAP · cost(TAX, 03-02) UNKNOWN:NONE |
| FX32 | FEE 01-01~06-30, 03-01~12-31, 출처 없는 schedule | [2, COST_SOURCE_MISSING] · cost(FEE, 03-02) UNKNOWN:OVERLAP · cost(FEE, 02-02) 0.00015 |
| FX33 | INTENT · ACCEPTED(09:00 seq 1·2), FILLED · CANCELLED(09:05 seq 없음) | [3, AMBIGUOUS_ORDER_SEQ] |
| FX34 | INTENT 뒤 접수 없이 FILLED | [1, BAD_ORDER_TRANSITION] |
| FX35 | 수급 D 15:00 공개 / D 18:00 공개 | [0, FLOW_TOO_EARLY] |
| FX36 | 공시 16:00 공개, 재무 15:00 공개 / 16:30 공개 | [1, FINANCIAL_BEFORE_FILING] |
| FX37 | cutoff_hash 틀린 신호 | [1, CUTOFF_HASH_MISMATCH] |
| FX38 | earliest_order_at < decision_at | [1, SIGNAL_TIME_ORDER] |
| FX39 | 계좌 상태 15:35가 15:40 공개 봉을 씀 / 16:00 | [1, INPUT_AFTER_ASOF] |
| FX40 | RAW 신호가 ADJ 봉을 씀 | [1, BASIS_MIX] |
| FX41 | 상장폐지 사건 정상 / kind 목록 밖 | [1, BAD_SECURITY_EVENT] |
| FX42 | 봉투에 ingest_run_id 없음 | [0, ENVELOPE_MISSING] |

모든 fixture에서 기대 `duplicates`는 FX04만 1이고 나머지는 0입니다.

## 6. 공통 불변식(시험 실행기가 검증기 출력과 따로 확인)
- I1: 받아진 `(record_id, version)`마다 normalized_sha256이 하나뿐
- I2: 받아진 정정판은 모두 같은 종류의 직전 판이 먼저 받아져 있고 `is_correction=true`
- I3: 받아진 SIGNAL · ACCOUNT_STATE의 모든 입력은 available_at ≤ decision_at · as_of
- I4: 받아진 레코드에 개인정보 키 없음
- I5: 받아진 PRICE_BAR_RAW는 모두 `adjusted=false`이고 조정 필드가 없음
- I6: 받아진 OBSERVED_KIS_PAPER 체결은 모두 가명 evidence_ref가 있고, HISTORICAL_MODEL 체결은 evidence_ref가 없음
- I7: 받아진 레코드의 시각은 모두 `+09:00`

## 7. 변이 시험(검증기에 일부러 넣을 결함 21개와 잡아야 할 fixture)
| 변이 | 잡아야 할 fixture(하나 이상) |
|---|---|
| M01 덮어쓰기 검사 끔 | FX03 |
| M02 시간대 검사 끔 | FX05 · FX06 |
| M03 available<as_of 검사 끔 | FX07 |
| M04 fetched 검사 끔 | FX08 |
| M05 결정 시각 컷오프를 하루 늦춤 | FX09 · FX10 · FX24 |
| M06 정정 연결 검사 끔 | FX11 · FX12 · FX13 |
| M07 수정주가 검사 끔 | FX14 · FX15 |
| M08 hash 검사 끔 | FX16 |
| M09 Universe가 날짜와 관계없이 최신 스냅숏을 씀 | FX17 |
| M10 불완전 스냅숏 허용 | FX18 |
| M11 상태 기록이 없으면 TRADING | FX19 |
| M12 상태 질의에서 available_at 무시 | FX20 |
| M13 기업행동 필수값 검사 끔 | FX22 |
| M14 날짜만 아는 공시 허용 | FX25 |
| M15 관측 체결 증거 검사 끔 | FX27 |
| M16 개인정보 키 검사 끔 | FX29 |
| M17 비용 공백이면 앞 schedule 씀 | FX31 |
| M18 비용 중첩이면 첫 것 씀 | FX32 |
| M19 같은 시각 seq 검사 끔 | FX33 |
| M20 수급 공개 시각 검사 끔 | FX35 |
| M21 RAW · ADJ 섞임 검사 끔 | FX40 |

## 8. G1~G12 추적(계획 — 결과 파일 `GAP-TRACEABILITY.json`)
| G | 계약 레코드 · 규칙 | 계획 분류 |
|---|---|---|
| G1 첫 도착 원주가 | PRICE_BAR_RAW · 정정 연결 · append-only · asof | CONTRACT_COVERED + 자료는 STILL_NEEDS_EXTERNAL_DATA(앞으로 수집 승인) |
| G2 다음 거래일 원주가 시가 | PRICE_BAR_RAW(open, session) · ADJUSTED_AS_RAW | 같음 |
| G3 신호 원료 시점별 판 | SIGNAL inputs · cutoff_hash · INPUT_AFTER_DECISION | CONTRACT_COVERED + 운영 기록 변경 승인 필요(STILL_NEEDS_AUTHORITY) |
| G4 calm 문턱 | SIGNAL strategy_hash로 규칙판 고정만 | STILL_NEEDS_AUTHORITY(규칙 결정) |
| G5 Universe(t) | UNIVERSE_SNAPSHOT · SECURITY_EVENT · universe 질의 | CONTRACT_COVERED + STILL_NEEDS_EXTERNAL_DATA(날짜별 상장 목록 출처) |
| G6 정지 · 상장 · 폐지 | TRADING_STATUS · SECURITY_EVENT · status 질의 | 같음 |
| G7 기업행동 | CORP_ACTION · corp 질의 | CONTRACT_COVERED + 자료 필요 · 커널 지원은 별도 |
| G8 수급 · 의견 공개 시각 | INVESTOR_FLOW · FLOW_TOO_EARLY · DART_FILING | CONTRACT_COVERED + 자료 필요 |
| G9 비용 출처 · 기간 | COST_SCHEDULE · cost 질의 | CONTRACT_COVERED + 출처 문서 필요 |
| G10 당시 NAV · 배분 | ACCOUNT_STATE · INPUT_AFTER_ASOF | CONTRACT_COVERED + 운영 기록 승인 필요 |
| G11 trade_id | ORDER_EVENT · FILL(order_id) | CONTRACT_COVERED(앞으로). 과거 29묶음은 복구 불가 |
| G12 관측 모의체결 | FILL OBSERVED_KIS_PAPER · evidence_ref | CONTRACT_COVERED + STILL_NEEDS_AUTHORITY(모의 체결 조회 · 기록 승인) |

## 9. 예산 · 판정
- 표준 라이브러리만 씁니다. 합성 자료만 씁니다. 네트워크 · API 0회.
- 검증 규칙 세트는 1개입니다. 결과 실행(`tests/run_tests.py` 호출)은 최대 3회이며, 한 번 호출 안에 결정론 2회와 변이 21회가 들어 있습니다.
- 목표: 5분 · 512MB.
- 격리 검사: 파일 열기 기록 훅으로 열린 경로가 **허용 디렉터리**(이 DATA-0001 폴더와 파이썬 표준 라이브러리 경로)뿐인지 확인합니다. 소켓 연결은 막고, 운영 모듈 import는 허용 디렉터리 밖 모듈 0으로 확인합니다.
- status
  - `READY`: 42개 fixture가 모두 기대와 같고, 불변식 I1~I7이 모두 성립하고, 변이 21개가 모두 잡히고, 2회 출력 hash가 같을 때
  - `BLOCKED`: 그 밖
- 첫 실행 결과는 `TEST-RESULT.run1.json`으로 보존합니다.
  - 기대값을 실제 출력으로 바꾸지 않습니다.
  - 검증기 결함을 고치면 원인 · 변경 · 실행 횟수를 REPORT에 적습니다.
  - 결과를 본 뒤 fixture나 규칙을 바꾸면 그 사례는 사전검정이 아니라고 표시합니다.
