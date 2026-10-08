# REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001 — 클로드 결과

- 상태: **READY**(감사 완료) · readiness: **NEEDS_DATA**(달력 계약 미검증)
- 입력: GPT PR #125 head `f4750d2a`. 원천 PR #124 head `13e031b3`(시작 · 제출 직전 확인).
- 사전등록: 커밋 `6dbe94cb`(03:55 KST, 분류 전).
  - 사전등록 전에는 일부 검색어의 줄 수만 셌습니다(공개).
- **읽기만 했습니다.** 저장소 스크립트 · 시험 · 워크플로 실행은 0입니다.
  - 쓴 명령: `git grep` · `git show` · `git rev-parse` · `git ls-tree`
  - 제 집계 스크립트 `code/search_counts.py`는 git 객체만 읽습니다.
- `actual_events=0` · `external_calls=0` · `code_executions=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`
  - 평일/휴일 달력을 만들거나 구현하지 않았습니다. replay · 성과 · 주문 · 운영 변경도 없습니다.
- 증거: `evidence/provenance-table.json`(20행 · 행마다 경로 · 줄 · blob · 분류) · `evidence/search-log.md` · `evidence/search-counts.json`

## 1. 연결 표

| 단계 | 저장소에 있는 것 | 분류 |
|---|---|---|
| ① 달력/세션 원천 | 권위 있는 KRX 거래일 · 세션 생산자 **0건**<br>· 거래소 휴장일 조회 API · 달력 라이브러리 흔적 없음 | **ABSENT ← 최초 단절점** |
| (대용품) | 서로 다른 정의 6가지(아래 2절) | CONFLICTING / UNVERIFIABLE |
| ② 변환기 | 대용품마다 경계 규칙이 다름: `START <= d < today` · `d >= since` · `first <= d <= last` | CONFLICTING |
| ③ 기대 거래일 목록 | 저장된 목록 없음(그때그때 계산 · 판/시각 없음) | ABSENT |
| ④ 스냅숏 생산 | 합성 `process_day`(PR #124 `empty_ledger_metric_gate.py:145-153`) | PRESENT_UNLINKED |
| ⑤ 완전성 게이트 | `perf_gate`는 차단 · invalid · 빈 원장만 봄 · 기대일 인자 없음 | ABSENT |
| ⑥ 성과 소비자 | 합성 `perf_gate(ledger)`(202-216) · 실제 자료와 연결 0 | PRESENT_UNLINKED |

- ④의 Train 쪽: 연구 엔진 `lab.run`(`lab.py:746,812-830`)은 **일별 MTM 스냅숏을 만들지 않습니다.** 손익은 닫힌 매매로 셉니다.

## 2. 달력 대용품 6가지(서로 충돌)

| # | 정의 | 위치 | 성격 |
|---|---|---|---|
| a | 손으로 적은 휴장일 + 평일 | `idle_live.py:50-53,68-74`(`run_watch.py:30-33`도 사용) | 2026-10-05 ~ 2027-12-31만 · 출처 없음 · 주석에 '틀려도 하루 늦거나…' |
| b | 손으로 적은 특수 장 시간 | `collect_kis_intraday.py:60-66` | 2건 · 출처 문서 없음 |
| c | 오늘 분봉 행 존재(대형 종목 1개) | `collect_kis_intraday.py:72-81` | 당일만 · 저장 안 함 |
| d | 지수 일봉의 직전 거래일 | `data_guard.py:19-26`(실패 시 자료 최빈값 36-44) | 직전 하루만 |
| e | 자료 파생: 대표 종목 1개의 일봉 날짜 | `collect_kis_hourly.py:95-97` · `collect_public_daily.py:34-36` · `reconcile.py:294-296` | 수정주가 자료 · 경계 제각각 |
| f | 자료 파생: 전 종목 합집합 | `collect_caps.py:35-48` · `lab.py:566-575`(Train 엔진) · `research/z070.py:76-77` | 어느 종목이라도 행이 있는 날 |

- **평일 추정**(`collect_krx_daily.py:93` · `predash/krx.py:16` · `dashboard_ui.py:709`)은 달력으로 세지 않았습니다.
- 시간대(KST)는 여러 곳에 명시돼 있습니다(`run_watch.py:19` 등 Asia/Seoul 84줄).

## 3. 필수 질문 7개

| 질문 | 분류 | 근거 |
|---|---|---|
| Q1 권위 있는 거래일 생산자 | **ABSENT** | 검색 0건 · 대용품뿐 |
| Q2 KST · 휴장 · 임시휴장 · 경계 · 첫 기대일 | **CONFLICTING** | KST는 명시, 휴장은 손 목록(2026-10~), 임시휴장 0, 경계는 함수마다 다름, 첫 스냅숏 기대일 규칙 없음 |
| Q3 available_at · 판 · 정정 정책 | **ABSENT** | 어느 달력에도 없음. `price-data`는 파일당 `fetched` 날짜 하나이고, 수정주가 재다운로드로 덮어씀 |
| Q4 스냅숏 날짜 생산 · 사유 구분 | **PRESENT_UNLINKED** | 합성 `process_day`가 만들지만 **차단만** 구분됨(아래 5절) |
| Q5 기대일 → 완전성 → 성과 연결 | **ABSENT** | 연결 없음 |
| Q6 Train · 연구 구간 기대일 재현 | **UNVERIFIABLE** | 자료 파생 달력은 다시 셀 수 있으나, 판/시각 근거가 없고 정의가 여러 개 |
| Q7 같은 목적의 진행 중 연구 | **ABSENT** | 관련 운영 확인(`data_guard.daily_ready` · `reconcile` 준비 검사)은 있으나 성과용이 아님(PRESENT_UNLINKED로 표에 적음) |

## 4. 최초 단절점과 영향
**최초 단절점: ① 달력/세션 원천 — 권위 있는 KRX 거래일 목록이 없음(ABSENT).** 그 뒤 단계가 모두 이 목록을 기대일로 받아야 성립합니다.

- **일별 TWR:** 빠진 날이 있으면 그 앞뒤 스냅숏 사이 수익이 '하루' 수익 하나로 합쳐집니다. 날짜 수와 일평균이 틀어집니다.
- **달력월 TWR:** 월말 거래일이 빠지면 그 달 마지막 수익이 다음 달로 넘어갑니다(`_monthly_twr`는 뒤 날짜의 달로 묶음).
- **MDD:** 빠진 날이 저점이면 낙폭을 덜 잡습니다(과소평가).

## 5. 거래일 누락과 정당한 무스냅숏의 구분
지금은 **구분할 수 없습니다.** 합성 `process_day` 기준으로 정리하면 다음과 같습니다.

| 경우 | 지금 남는 흔적 | 구분 |
|---|---|---|
| 차단일 | 스냅숏 없음 + `blocked_from` | 됨 |
| 무시세(그 종목 시세 없음) | 앞 가격을 그대로 두고 스냅숏 생성(`quotes()` 231-243이 종목을 빼면 가격 유지) | 안 됨('가격 안 바뀜'과 같아 보임) |
| 무보유 | NAV = 현금인 스냅숏 | 안 됨(사유 칸 없음) |
| 휴장일 | 아무 흔적 없음 | 안 됨 |
| 누락(처리 안 된 거래일) | 아무 흔적 없음 | 안 됨(휴장과 같아 보임) |

## 6. 필요한 최소 추가 자료(필드 단위 · 자동 요청 · 수집하지 않음)
**거래일 목록** — 날마다 한 줄

| 필드 | 내용 |
|---|---|
| `date` | YYYYMMDD · KST |
| `market` | KOSPI / KOSDAQ |
| `is_open` | 열림 여부 |
| `session_open` · `session_close` | 특수 시간 포함 |
| `closure_reason` | 정기 휴장 · 임시휴장 |
| `source_id` | 거래소 공지 번호 또는 자료 이름 |
| `source_published_at` | KST 시각 |
| `available_at` | 처음 알 수 있게 된 시각 |
| `revision_id` · `revision_reason` | 임시휴장 추가 등 |
| `coverage_start` · `coverage_end` | 목록 전체의 범위 |

**스냅숏 쪽**

| 필드 | 내용 |
|---|---|
| `expected_date` | 위 목록과 연결 |
| `snapshot_reason` | TRADED · NO_POSITION · NO_QUOTE · BLOCKED 중 하나 |
| `quote_present` | 종목별 |

**대상 기간:** 위 거래일 목록이 Train 구간(2025-09-18 ~ 2026-03-31 등 앞선 회차 기준)을 모두 덮어야 합니다.

## 7. GPT 지시에 대한 반박 · 보충(근거: provenance-table)
- **'최초 단절점 하나'로는 부족합니다.** 권위 달력이 생겨도 두 곳이 더 끊겨 있습니다.
  - ⑤ `perf_gate`에 기대일 인자가 없습니다.
  - ④ 스냅숏에 사유 칸이 없습니다.
  - 그래서 달력만 넣으면 '누락'과 '무보유 · 무시세'를 여전히 가르지 못합니다.
- **실제 Train 엔진은 스냅숏 기반이 아닙니다.** `lab.run`은 자료 합집합 달력(`lab.py:566-575`)을 돌며 닫힌 매매로 손익을 셉니다(`lab.py:812-830`). 그래서 지금까지 고친 합성 `perf_gate` 사슬(PR #120~#124)은 Train 성과 계산과 연결돼 있지 않습니다.
  - 일별 MTM 기반 일/월 TWR · MDD를 Train에서 내려면, 스냅숏 생산자부터 새로 연결해야 합니다.
- **손으로 적은 휴장일 목록은 운영 봇 판단에 이미 쓰입니다**(`idle_live.week_end` · `run_watch`). 출처 · 판 근거가 없으므로, 성과 달력의 근거로 승격하면 안 됩니다.

## 다음 방향
- 실제 자료가 필요한 단계입니다. 위 6절의 거래일 목록(출처 · 공개 시각 · 판 포함)을 어디서 확보할지 GPT · 사용자의 결정이 필요합니다.
- 그 전에는 구현으로 넘어가지 않습니다(GPT PREREG 그대로).
