# REPLAY-EMPTY-LEDGER-METRIC-GATE-0001 — 클로드 사전등록(수정 · 공식 실행 전)

- 지시: GPT PR #123 head `2fbeaac0`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `648a0f77a33d9b67`
  - SOURCE_PACKET `ba0faa91b989708e`
  - PREREG `07536f7a6f81a66f`
  - REVIEW `3bd9297ec005e0ac`
  - receipt `112d52f7f2f143aa`
- 원천 PR #122: 03:46 KST 확인 결과 열림 · 초안 아님 · head `2ec2e13b55578290c3bcb822a3b78b30b77c9047`. 제출 직전에 다시 확인합니다.
- 고정본: GPT SOURCE_PACKET의 blob · PR #122 manifest sha256과 둘 다 일치합니다.
  - 코드 `code/blocked_day_metric_gate.py`: blob `66ef2652` · sha256 `a28cf40e…`
  - 증거 `evidence/blocked-day-metric-gate.json`: blob `32f563a1` · sha256 `edee9e29…`
- E6 회귀에 쓰는 앞선 고정본(PR #122 manifest에 적힌 sha256으로 대조)
  - PR #120 코드 `049342e8…` · PR #120 증거 `b7308516…`
  - PR #114 증거 `ecfb7a75…`
- **공식 실행 1회(상한 1).** 실패하면 fixture · 규칙을 바꾸지 않고 BLOCKED로 냅니다. 사전등록 뒤 코드를 고치게 되면 공식 실행 전에만 하고, 이유와 diff를 REPORT에 공개합니다.
- 금지 0: 외부 · API · 수집 · 실제 사건/시세/포지션/NAV/성과 · 가격기준 선택 · KIS · 운영/기존 파일 수정 · threshold/alpha · 주문 · 자동병합.

## 고정 계약(GPT TASK 그대로 · PR #122 `perf_gate`에 한 분기 추가)
판정 순서: `blocked_from` → invalid 스냅숏 → **빈 스냅숏** → 정상 지표

- `blocked_from`이 있으면 → `LEDGER_BLOCKED` · from = 그 날짜(바뀌지 않음)
- invalid 스냅숏이 있으면 → `INVALID_SNAPSHOT` · 최초 invalid 날짜(바뀌지 않음)
- **새 분기:** `ledger.snaps`가 비었으면 → `{status: PERF_BLOCKED, from: null, reason: NO_SNAPSHOTS}`
  - 지표 4칸은 모두 null이고, 지표 함수 호출은 0입니다.
- 스냅숏이 1개 이상이고 모두 valid일 때만 정상 경로로 갑니다. 정상 수치와 `cost_model: NOT_MODELED`는 바꾸지 않습니다.

## 고정 케이스 · 기대값(현금 0 · D0 = 2026-01-28 · D1 = 2026-01-29 · 시작 A 37 @ 52,300)

| # | 장부 | 기대 |
|---|---|---|
| E1 음성대조 | PR #122 고정본 장부 · `blocked_from` 없음 · 스냅숏 0 · PR #122 `perf_gate` | `IndexError` 예외 |
| E2 | 같은 장부 · 새 `perf_gate` | `PERF_BLOCKED` · from null · `NO_SNAPSHOTS` · 지표 4칸 null · 지표 호출 0 |
| E3 | D0 시세 A 52,300(ADJUSTED) → `blocked_from` = D0 · 스냅숏 0 | `LEDGER_BLOCKED` · from D0 · 지표 null · 호출 0 |
| E4 | D0 · D1 RAW 52,300 → 스냅숏 2 · 직렬화 JSON에서 D1만 `valid: false` · 표식 없음 | `INVALID_SNAPSHOT` · from D1 · 지표 null · 호출 0 |
| E5 | D0 RAW 52,300 → 스냅숏 1(valid) · 표식 없음 | 같은 방법으로 만든 PR #122 고정본 장부에 PR #122 `perf_gate`를 넣은 출력과 dict 전체가 같음(OK · all_zero true · 일별 [] · 월 {} · MDD "0" · 비용후 null · NOT_MODELED) · 지표 호출 3 |

**E6 PR #122 회귀(PR #122 증거와 칸별 비교)**
같은 방법으로 다시 만들어 비교합니다.

| 항목 | 비교 칸 |
|---|---|
| M1 | PR #120 고정본 장부 · 옛 함수 출력 · `blocked_from` · 스냅숏 |
| M2 · M3 · M5 | `perf_gate` 출력 전체 · 지표 호출 수 · reload 출력/바이트 같음 · 바이트 sha256 |
| M4 · M6② | PR #114 fixture 11개마다 다음 칸<br>· `perf_gate_first_path` · 지표 호출 수<br>· PR #114 증거와 다른 칸 수(0)<br>· 4경로 · 바이트 · 자르기 · 반복 |
| M6① | PR #120 `Q1_raw` 재실행 diff(0) · `perf_gate` 출력 · 지표 호출 수 · reload |
| M8 | 정적 판정 참/거짓 칸<br>· 줄 번호 · 호출 지점 수는 파일이 바뀌어 다르므로 비교하지 않음 |

**E7 직렬화 · 결정성**
- E2~E5 각각 다음 세 경로가 모두 같아야 합니다.
  - serialize → reload 뒤 출력
  - 바이트
  - 장부를 다시 만들어 반복한 출력

**E8 호출 경계**
- 정적(ast) 근거
  - `perf_gate` 인자는 `ledger` 하나뿐(기본값 · 선택 인자 없음)
  - `perf` 함수 없음 · snaps만 받는 성과 함수 없음
  - 문장 순서가 [`blocked_from` 읽기, 그 if, invalid 목록, 그 if, **빈 스냅숏 if**]
  - 세 차단 `return` 줄이 모두 지표 함수 호출 줄보다 앞
  - 파일 안 `perf_gate` 호출은 모두 인자 하나
- 실행 근거: E2 · E3 · E4에서 지표 호출 0

## 판정
- E1~E8이 모두 기대와 같으면 READY, 하나라도 다르면 BLOCKED입니다.
- 판정은 증거 `summary.all_pass`에서 나옵니다.
- 이 게이트는 거래일 완전성(빠진 날 검출) 계약이 아닙니다(GPT PREREG 경계 그대로).
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/empty_ledger_metric_gate.py`
- `evidence/empty-ledger-metric-gate.json` · `evidence/tables.md` · `evidence/run.log`
