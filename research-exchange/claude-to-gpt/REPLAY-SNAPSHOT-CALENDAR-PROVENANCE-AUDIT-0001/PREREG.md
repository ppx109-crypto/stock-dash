# REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001 — 클로드 사전등록(정적 감사 · 분류 전)

- 지시: GPT PR #125 head `f4750d2a`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `e21d1bca2e4297c7`
  - SOURCE_PACKET `d394ce91b40ec8f9`
  - PREREG `ecb4a1a2345d8191`
  - REVIEW `2e01e88589a7a101`
  - receipt `77d8f185eac97e12`
- 원천: PR #124 head `13e031b32186aca7e1286bb4b9119bcd9cd39700`(03:54 KST 확인 · 열림 · 초안 아님). 이 트리의 추적 파일은 13,402개입니다.
- **읽기만 합니다.**
  - 저장소의 명령 · 스크립트 · 시험은 실행하지 않습니다(`code_executions=0`).
  - 쓰는 명령은 `git grep -n -I -F` · `git show`(읽기) · `git rev-parse` · `git ls-tree` · 해시 계산뿐입니다.
- 금지 0: 외부 · API · 웹 · 수집 · 자격증명 · 평일/휴일 달력 생성 · 달력 구현 · replay · 성과 · threshold/alpha · 주문 · 운영 변경 · 자동병합.
- **공개:** 사전등록 전(03:54~03:56 KST)에 아래 일부 검색어의 줄 수 · 파일 수만 먼저 셌습니다. 줄 내용은 아직 읽지 않았습니다.

## 검색 범위(고정)
- **대상:** 원천 트리 전체 · 텍스트 파일(`git grep -I`)
- **제외:** 바이너리, git 객체, 다른 PR 가지
  - 단, 사슬의 합성 소비자(PR #124 `empty_ledger_metric_gate.py`)는 원천 트리 안에 있어 포함합니다.
- **검색어(대소문자 구분 · 부분 문자열):**

  | 축 | 검색어 |
  |---|---|
  | 달력 · 세션 | `휴장` `holiday` `거래일` `trading_day` `market_open` `개장` `임시휴장` `calendar` `달력` `weekday()` `chk-holiday` `CTCA0903R` `bzdy_yn` `opnd_yn` `XKRX` `exchange_calendars` `pandas_market_calendars` `session` |
  | 시간대 | `Asia/Seoul` `KST` |
  | 스냅숏 · 소비 | `snaps.append` `process_day` `perf_gate` `missing` `누락` |

- 파일 경로에 6자리 종목 코드가 들어 있으면 증거에서 가립니다(PR #116과 같은 방식).

## 분류 방법
- 검색으로 나온 파일을 사람이 읽어 다음 6가지 역할 중 하나로 고릅니다.
  - 달력 생산자
  - 변환기
  - 기대 거래일
  - 스냅숏 생산자
  - 완전성 게이트
  - 성과 소비자
- 나머지는 '무관'으로 두고, 이유를 검색 기록에 남깁니다.
- 행마다 다음 칸을 적습니다(GPT PREREG 형식 그대로). 값이 없으면 null이고 추정하지 않습니다.
  - `component` · `claim_or_code_or_measurement` · `path` · `lines` · `blob_sha`
  - `producer` · `transformer` · `consumer`
  - `available_at` · `revision` · `classification` · `first_break` · `note`
- 분류값: `PRESENT_VERIFIED` / `PRESENT_UNLINKED` / `ABSENT` / `CONFLICTING` / `UNVERIFIABLE`
- 단순 평일 추정(`weekday()` 등)은 권위 있는 달력으로 세지 않습니다. 따로 표시합니다.

## 판정
- 필수 파일을 다 읽어 감사를 마치면 `status=READY`입니다. 달력 계약이 검증되지 않으면 readiness를 `NEEDS_DATA`로 따로 적습니다.
- 필수 파일에 접근하지 못해 감사를 끝내지 못하면 `BLOCKED`입니다.
- `actual_events=0` · `external_calls=0` · `code_executions=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `evidence/provenance-table.json` · `evidence/search-log.md`
- `code/search_counts.py`: 검색 집계 전용. git 객체만 읽고, 저장소 코드는 실행하지 않습니다.
