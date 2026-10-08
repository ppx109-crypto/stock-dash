# REPLAY-BLOCKED-DAY-METRIC-GATE-0001 — 클로드 사전등록(수정 · 공식 실행 전)

- 지시: GPT PR #121 head `46b8310b`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `0b6ec928781c939e`
  - SOURCE_PACKET `a02ef535b9951fed`
  - PREREG `bfba7a3774f4a1a6`
  - REVIEW `6bf0b94e38d06f33`
  - receipt `cdbefd2934cad121`
- 원천 PR #120: 03:38 KST 확인 결과 열림 · 초안 아님 · head `8ed1d7d24a7fd564c200f2978bd51659f1af4316`. 제출 직전에 다시 확인합니다.
- 고정본: GPT SOURCE_PACKET의 blob · PR #120 manifest sha256과 둘 다 일치합니다.
  - 코드 `code/quote_basis_gate.py`: blob `80ab1496` · sha256 `049342e8…`
  - 증거 `evidence/quote-basis-gate.json`: blob `3b67cb16` · sha256 `b7308516…`
  - 비교 기준(M4 · M6) PR #114 증거: sha256 `ecfb7a75…`
- **공식 실행 1회(상한 1).** 실패하면 fixture · 수치 · 규칙을 바꾸지 않고 BLOCKED로 냅니다. 사전등록 뒤 코드를 고치게 되면 공식 실행 전에만 하고, 이유와 diff를 REPORT에 공개합니다.
- 금지 0: 외부 · API · 수집 · 실제 사건/시세/포지션/NAV · 가격기준 선택 · KIS 인자 · 라벨 추론 · 백테스트 · 실제 성과 주장 · threshold/alpha · 운영/기존 파일 수정 · 주문 · 자동병합.

## 고정 계약(GPT TASK 그대로)
- 옛 `perf(snaps)`는 복사본에서 **지웁니다.** 새 성과 함수는 `perf_gate(ledger)` 하나뿐입니다.
  - 인자는 장부 객체 하나이고, 기본값 · 선택 인자가 없습니다.
  - 하네스의 모든 호출을 `perf_gate(L)`로 바꿉니다.
- 판정 순서:
  1. **첫 문장**에서 `ledger.blocked_from`을 읽습니다. 값이 있으면 곧바로 `{status: PERF_BLOCKED, from: blocked_from, reason: LEDGER_BLOCKED}`를 돌려줍니다.
  2. 다음으로 `valid=False` 스냅숏이 있으면 `{status: PERF_BLOCKED, from: 최초 invalid 날짜, reason: INVALID_SNAPSHOT}`입니다.
     - 이 사유 이름은 TASK 5항의 경우를 가리키려고 정했습니다.
  3. 둘 다 아닐 때만 지표를 계산합니다.
- **지표 칸(차단 시 모두 null):**
  - `daily_returns`: 일별 r = NAV_t/NAV_{t−1} − 1
  - `monthly_twr`: 달력월마다 (1 + r)을 곱한 뒤 − 1
  - `mdd`: 고점 대비 최대 낙폭
  - `cost_after_return`
- **비용후수익률:** 합성 경로에는 비용 모델이 없습니다. 새로 만들지 않고(TASK 7항) 정상일 때도 `null`로 두며, `cost_model: NOT_MODELED`로 표시합니다.
- 정상 경로는 옛 함수와 같은 `status: OK` · `all_zero`를 함께 냅니다.
- 지표 계산은 `_daily_returns` · `_monthly_twr` · `_mdd` 세 함수로만 합니다. 실행 중 각 함수의 호출 수를 셉니다.

## 고정 케이스 · 기대값(현금 0 · D0 = 2026-01-28 · D1 = 2026-01-29 · 시작 A 37 @ 52,300)

| # | 장부 만들기 | 기대 |
|---|---|---|
| M1 음성대조 | PR #120 고정본 장부 · D0 시세 A 52,300(RAW) → 스냅숏 1개(valid). D1 시세 A 10,460(ADJUSTED) → 하루 차단 · 스냅숏 없음 · `blocked_from` = D1. 옛 `perf(snaps)`에 snaps만 넘김 | 옛 함수가 `{status: OK, all_zero: true}`를 돌려줌(차단을 놓침) |
| M2 마지막 날 차단 | M1과 같은 과정을 새 장부로 만듦 · `perf_gate(장부)` | `PERF_BLOCKED` · from D1 · `LEDGER_BLOCKED` · 지표 4칸 null · 지표 함수 호출 0 |
| M3 첫날 차단 | 새 장부 · D0 시세 A 52,300(ADJUSTED) → 스냅숏 0 · `blocked_from` = D0 | `PERF_BLOCKED` · from D0 · `LEDGER_BLOCKED` · 지표 null · 호출 0 |
| M4 사건 배치 차단 회귀 | PR #114 증거의 차단 fixture 8개(M1~M3 · K1 · K2 · Q1~Q3) · 4경로(사건 배치 중단 → `blocked_from` + invalid 스냅숏) | 모두 `PERF_BLOCKED` · from = 배치일 · `LEDGER_BLOCKED` · 지표 null. RCMP 칸이 PR #114 증거와 다른 칸 0. 단 `perf`는 옛 결과에 있던 칸(status · from)만 비교 |
| M5 불일치 방어 | 새 장부 · D0 · D1 모두 RAW 52,300 → 스냅숏 2개. 직렬화 JSON에서 D1 스냅숏만 `valid: false`로 바꿔 reload · `blocked_from` 없음 | `PERF_BLOCKED` · from D1 · `INVALID_SNAPSHOT` · 지표 null · 호출 0 |
| M6 정상 RAW | ① PR #120 `Q1_raw` 하루 케이스 재실행(같은 방식) ② PR #114 증거의 정상 fixture 3개(M4 · K3 · Q4) · 4경로 | ① 결과 칸이 PR #120 증거와 다른 칸 0. `perf_gate`는 OK · `all_zero` true · 지표 3칸 계산됨. ② RCMP(perf는 status · all_zero만) 다른 칸 0, `perf_gate` OK · 지표 계산됨 |

**M7 직렬화**
- M2 · M3 · M5 · M6①은 각각 장부를 serialize → reload 했을 때 두 가지가 같아야 합니다.
  - `perf_gate` 출력(판정 · from · 사유 · 지표)
  - 직렬화 바이트
- M4 · M6②는 하네스 안의 4경로(순서 × reload) · 바이트 · 자르기 · 반복 불변을 그대로 확인합니다.

**M8 호출 경계**
- 정적 근거(ast) 4가지를 확인합니다.
  1. 파일에 `perf` 이름의 함수와, `snaps`를 인자로 받는 성과 함수가 없음
  2. `perf_gate`의 인자가 정확히 `ledger` 하나이고 기본값이 없음
  3. `perf_gate`의 첫 문장이 `ledger.blocked_from`을 읽고, 그 차단 `return` 줄이 세 지표 함수 호출 줄보다 앞임
  4. 파일 안 `perf_gate` 호출이 모두 인자 하나로만 이루어짐
- 실행 근거: 차단 케이스(M2 · M3 · M5 · M4 32경로) 동안 지표 함수 호출이 0이어야 합니다.

## 판정
- M1~M8이 모두 기대와 같으면 READY, 하나라도 다르면 BLOCKED입니다.
- 판정은 증거 `summary.all_pass`에서 나옵니다.
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`
- 실제 TWR · MDD · 비용후수익률은 산출하지 않습니다. 정상 경로의 지표는 합성 장부의 0 확인용입니다.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/blocked_day_metric_gate.py`
- `evidence/blocked-day-metric-gate.json` · `evidence/tables.md` · `evidence/run.log`
