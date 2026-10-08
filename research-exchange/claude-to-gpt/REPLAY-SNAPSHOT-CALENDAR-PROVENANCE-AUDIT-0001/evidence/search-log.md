# 검색 기록 — REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001

## 범위
- 원천: PR #124 head `13e031b32186aca7e1286bb4b9119bcd9cd39700` · 추적 파일 13,402개 · 텍스트만(`git grep -n -I -F`)
- 제외: 바이너리 · git 객체 · 다른 PR 가지 · 외부 자료
- 실행한 것: `git grep` · `git show`(읽기) · `git rev-parse` · `git ls-tree` · `code/search_counts.py`(git 객체만 읽는 제 집계 스크립트)
- 저장소의 스크립트 · 시험 · 워크플로 실행: **0**
- 줄 본문은 저장하지 않았습니다(`search-counts.json`에는 경로 · 줄 번호 · 줄 sha256 앞 16자만 있음). 경로의 6자리 종목 코드는 가렸습니다.

## 검색어별 결과(사전등록 고정 목록)
| 축 | 검색어 | 줄 | 파일 | git grep 종료 코드 |
|---|---|---|---|---|
| calendar_session | `휴장` | 8 | 8 | 0 |
| calendar_session | `holiday` | 4 | 4 | 0 |
| calendar_session | `거래일` | 707 | 281 | 0 |
| calendar_session | `trading_day` | 43 | 22 | 0 |
| calendar_session | `market_open` | 13 | 7 | 0 |
| calendar_session | `개장` | 11 | 11 | 0 |
| calendar_session | `임시휴장` | 0 | 0 | 1 |
| calendar_session | `calendar` | 40 | 19 | 0 |
| calendar_session | `달력` | 40 | 30 | 0 |
| calendar_session | `weekday()` | 17 | 15 | 0 |
| calendar_session | `chk-holiday` | 0 | 0 | 1 |
| calendar_session | `CTCA0903R` | 0 | 0 | 1 |
| calendar_session | `bzdy_yn` | 0 | 0 | 1 |
| calendar_session | `opnd_yn` | 0 | 0 | 1 |
| calendar_session | `XKRX` | 0 | 0 | 1 |
| calendar_session | `exchange_calendars` | 0 | 0 | 1 |
| calendar_session | `pandas_market_calendars` | 0 | 0 | 1 |
| calendar_session | `session` | 225 | 15 | 0 |
| timezone | `Asia/Seoul` | 84 | 43 | 0 |
| timezone | `KST` | 124 | 39 | 0 |
| snapshot_consumer | `snaps.append` | 1 | 1 | 0 |
| snapshot_consumer | `process_day` | 15 | 1 | 0 |
| snapshot_consumer | `perf_gate` | 48 | 7 | 0 |
| snapshot_consumer | `missing` | 57 | 33 | 0 |
| snapshot_consumer | `누락` | 91 | 88 | 0 |

## 사람이 고른 관련 파일과 역할(자세한 칸은 `provenance-table.json`)
- **손 목록 달력:** `idle_live.py` 50-53 · 68-74(HOLIDAYS · next_trading_day), `run_watch.py` 30-33(같은 목록 사용)
- **손 목록 특수 시간:** `collect_kis_intraday.py` 60-66(SPECIAL_HOURS)
- **당일 실시간 판정:** `collect_kis_intraday.py` 72-81(market_open_today · 대형 종목 1개 분봉) → 봇 5곳
- **직전 거래일:** `data_guard.py` 19-26(지수 일봉) · 36-44(실패 시 자료 최빈값)
- **자료 파생 달력:**
  - 종목 1개: `collect_kis_hourly.py` 95-97, `collect_public_daily.py` 34-36, `reconcile.py` 294-296
  - 전 종목 합집합: `collect_caps.py` 35-48, `lab.py` 566-575(연구 엔진), `research/z070.py` 76-77
- **평일 추정:** `collect_krx_daily.py` 93, `predash/krx.py` 16, `dashboard_ui.py` 709
- **합성 스냅숏 · 소비:** PR #124 `empty_ledger_metric_gate.py` 145-153(process_day) · 202-216(perf_gate) · 222(DAYS) · 231-243(quotes)
- **시험(실행 안 함):** `tests/test_idle_live.py` 27-30, `tests/test_special_hours.py`, `tests/test_data_guard.py` 41

## 무관으로 둔 것과 이유
- `session`(225줄): Streamlit `session_state`가 대부분이고, 나머지는 브라우저 세션 설명, 또는 대시보드(predash · classroom_ui)가 받은 일봉 행 수로 센 '최근 N거래일' 개수입니다(예: `predash/flow.py:26`). 기대 거래일 생산자가 아닙니다.
- `calendar`(40줄):
  - `calendar_sync.py` · 주간 점검 워크플로는 Google Calendar 일정 쓰기입니다.
  - `isocalendar()`는 주 번호 계산이고, `chat_research.py`의 `calendar.monthrange`는 월말 계산입니다.
  - 거래일 근거가 아닙니다.
- `missing` · `누락`(57 · 91줄): 수집 실패 수 · 화면 목록 · 후보 부족 표시 등 — 성과 스냅숏 누락 판정 아님.
- `거래일`(707줄) · `달력`(40줄): 대부분 주석 · 문서 · 연구 설명입니다. 코드로 달력을 만드는 곳은 위 '관련 파일'로 모두 옮겼습니다.
- `Asia/Seoul` · `KST`: 시간대 명시 근거로만 씁니다(달력 생산자 아님).
- 0건(exit 1): `임시휴장` `chk-holiday` `CTCA0903R` `bzdy_yn` `opnd_yn` `XKRX` `exchange_calendars` `pandas_market_calendars` — 권위 달력 API · 라이브러리 사용 흔적 없음.
