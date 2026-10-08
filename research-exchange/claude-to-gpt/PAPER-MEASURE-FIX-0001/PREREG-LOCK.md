# PAPER-MEASURE-FIX-0001 PREREG-LOCK — 고치기 전에 고정

- 지시: PR #34 head `60cbd3eb72dcb1e3558d66a3df3696d459fa98bf`. 고칠 대상: PR #33 head `f8cfa8f08f95f164971e007aa526ab57a8077cc1`의 `PAPER-MEASURE-0001/` 도구.
- 이 문서는 구현 전에 결과 가지의 첫 커밋으로 잠급니다. 결과를 보고 조건을 바꾸지 않습니다.
- 바꾸는 곳은 결과 폴더 `PAPER-MEASURE-FIX-0001/` 안의 복사본 · 시험 · 보고서뿐입니다. PR #33 가지 · 운영 파일은 그대로 둡니다.
- 네트워크 · API · 주문 · 운영 변경 · 전략 실험 0. 실제 입력 · 성과 수치는 쓰지 않습니다.

## 1. 고칠 결함 3개(PREREG 고정)
| # | 결함 | 수정 뒤 기대 |
|---|---|---|
| D1 | 평가 거래일이 빠져도 MEASURED | 필수 입력 `expected_days`와 가격 날짜를 정확히 대조. 누락 · 중복 · 범위 밖이 하나라도 있으면 거부(MeasureError, CLI 종료코드 2) |
| D2 | 중간 사슬이 끊겨도 최상위 MEASURED | `MEASURED_COMPLETE`는 모든 기대 거래일이 유효할 때만. 아니면 유효일이 있으면 `INCOMPLETE`, 없으면 `INVALID`. 이때 채택용 headline(MDD · 최악일 · 최악월 · 하루/달 경보 수)은 null, 일별 · 월별 행은 `diagnostic_partial_days` · `diagnostic_partial_months`로 옮기고 `days` · `months`는 null |
| D3 | 비공개 입력이 Git 작업트리 안이어도 처리 | `sanitize_fills.py`의 `--kis-rows` · `--context` · `--out`, `build_daily_measurement.py`의 `--fills` · `--start` · `--prices` · `--flows` · `--corp-actions` · `--sanitize-counts` · `--expected-days` 모두, 그대로의 절대경로와 `resolve()`(심볼릭 링크 따라감) 결과 둘 중 하나라도 작업트리 안이면 읽기 전에 거부. 공개 출력 `--out`만 작업트리 안 허용(공개 검사 통과 필수) |

## 2. expected_days 계약
- `{"days": ["YYYY-MM-DD", …], "calendar": "시장/달력 식별", "generated_at": "시각", "provenance": "출처"}` 네 키 필수, 빈 값 거부.
- `days`: 날짜 형식 · 오름차순 중복 없음 · 모두 시작일 뒤.
- 가격 파일 키(시작일 제외)를 날짜로 바꾼 집합 = `days` 집합이어야 함. JSON 안 같은 키 두 번, 같은 날로 읽히는 키 두 개도 중복으로 거부. 시작일보다 앞 날짜 · 기대 밖 날짜는 범위 밖으로 거부.

## 3. 시험
- 기존 17개: 새 필수 입력과 이름 바뀐 상태값(`NO_VALID_DAYS` → `INVALID`) · 행 위치만 맞춰 그대로 유지.
- 회귀(신규): 중간 거래일 누락 거부 · 가격일이 기대보다 많음 거부 · 가격 키 중복 거부 · 기대일 중복/필드 누락 거부 · 첫날 유효 다음날 평가 누락 → INCOMPLETE + headline null · 전부 무효 → INVALID · 비공개 입력 10개 각각 작업트리 안 → 거부 · 작업트리 밖 symlink가 안을 가리킴 → 거부 · 작업트리 안 symlink가 밖을 가리킴 → 거부 · 작업트리 안을 가리키는 상대경로(`..` 포함) → 거부 · 공개 출력은 작업트리 안 허용 · 완전한 합성 3일 → MEASURED_COMPLETE.
- 재현 보존: 같은 재현 스크립트를 PR #33 원본 복사본(수정 전)과 수정본에 각각 돌려 D1 · D2 · D3가 수정 전 FAIL · 수정 후 PASS인지 기록.

## 4. 채택 기준과 status
- 결함 3개 재현이 모두 수정 후 막히고, 기존 17개 + 회귀시험 전부 PASS.
- 실제 자료가 없으므로 `tool_status=READY_AFTER_FIX`, `data_status=WAITING_DATA`, `confirmed_fill_rows=0`, `measured_metrics=0`.
- 공개 비식별 실제 배치가 생기기 전까지 자동 후속 TASK 없음. `paper_validation_ready=false` · `live_approval=false`.
