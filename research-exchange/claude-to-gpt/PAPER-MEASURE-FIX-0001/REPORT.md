# PAPER-MEASURE-FIX-0001 결과 — 거래일 완전성 · 불완전 상태 · 비공개 입력 경계 교정

- 지시: PR #34 head `60cbd3eb72dcb1e3558d66a3df3696d459fa98bf` · 고친 대상: PR #33 head `f8cfa8f08f95f164971e007aa526ab57a8077cc1`의 `PAPER-MEASURE-0001/` 도구
- PREREG-LOCK 첫 커밋 `2f8f35ba`(2026-10-08 11:46 KST, 구현 전)
- **tool_status: READY_AFTER_FIX** · **data_status: WAITING_DATA** · confirmed_fill_rows 0 · measured_metrics 0
- READY_AFTER_FIX는 도구 교정 완료일 뿐이며 PAPER_VALIDATION_READY나 실전 승인이 아닙니다. `paper_validation_ready=false` · `live_approval=false`
- 바꾼 곳은 이 폴더의 복사본 · 시험 · 보고서뿐입니다. PR #33 가지 · 운영 파일 · 봇 · 워크플로는 그대로이고, 네트워크 · API · 주문 · 전략 실험은 0입니다.

## 1. 결함 3개 — 수정 전 FAIL · 수정 후 PASS
같은 스크립트(`tests/repro_defects.py`)를 PR #33 원본 복사본(`REPRO-BEFORE.json`)과 수정본(`REPRO-AFTER.json`)에 돌렸습니다.

| 결함 | 수정 전 | 수정 후 |
|---|---|---|
| D1 거래일 10-02 가격 누락 | **FAIL** — `MEASURED` · 2일로 계산 | **PASS** — 거부("기대 거래일 1일의 평가가격이 없습니다") |
| D2 첫날 유효 · 다음날 평가 누락 | **FAIL** — `MEASURED` · days_valid 1/2 · MDD · 최악일 · 경보 수가 값으로 나옴 | **PASS** — `INCOMPLETE` · headline 모두 null |
| D3 비공개 KIS 원문이 Git 작업트리 안 · 출력은 밖 | **FAIL** — 종료코드 0 · 원장 파일 생김 | **PASS** — 종료코드 2 · 파일 안 생김 |

## 2. 무엇을 고쳤나
1. **거래일 완전성(D1)**: 필수 입력 `expected_days`(`days` · `calendar` · `generated_at` · `provenance`)를 추가했습니다. `days`는 YYYY-MM-DD, 오름차순, 중복 없음, 모두 시작일 뒤여야 합니다. 가격 파일 날짜(시작일 제외)가 `days`와 정확히 같아야 하며, 아래는 모두 거부합니다(CLI 종료코드 2).
   - 누락 · 추가 · 시작일 앞 날짜
   - 다른 표기(`2026-10-02T00:00` · `2026-10-2`)
   - JSON 안 같은 키 두 번
2. **상태 의미(D2)**: `MEASURED_COMPLETE`는 기대 거래일이 전부 유효할 때만 나옵니다. 아니면 유효일이 있으면 `INCOMPLETE`, 없으면 `INVALID`입니다.
   - 불완전할 때 채택용 headline(`mdd_daily_mtm` · `worst_day_twr` · `worst_month_twr` · `day_alerts` · `month_alerts`)은 null입니다.
   - `days` · `months`도 null이고, 행은 `diagnostic_partial_days` · `diagnostic_partial_months`로만 나옵니다.
   - 코드 안 단언으로 "days_valid < days_total인데 MEASURED_COMPLETE"인 경로를 막았습니다.
3. **비공개 입력 경계(D3)**: 아래 비공개 경로 10개 모두 두 가지로 검사합니다. 그대로의 절대경로(`..`만 정리, 링크 안 따라감)와 `resolve()` 결과(링크 따라감) 중 하나라도 Git 작업트리 안이면 **읽기 전에** 거부합니다. 공개 출력(`build --out`)만 작업트리 안을 허용하며, 기존 공개 검사를 통과해야 합니다.
   - `sanitize_fills.py`: `--kis-rows` · `--context` · `--out`
   - `build_daily_measurement.py`: `--fills` · `--start` · `--prices` · `--expected-days` · `--flows` · `--corp-actions` · `--sanitize-counts`

## 3. 시험(합성 · 실측 아님)
| 묶음 | 결과 |
|---|---|
| 기존 17개(`tests/test_measure.py`) | **17/17 PASS**(`TEST-RESULT.existing17.json`). 기대값은 그대로이고 호출만 맞췄습니다: `expected_days`는 가격 키로 만들어 넣음 · 상태 이름 `NO_VALID_DAYS` → `INVALID` · 불완전일 때 행 위치. 바뀐 줄은 이 셋과 도움 함수뿐임을 원본과 비교해 확인 |
| 회귀 11개(`tests/test_regression.py`) | **11/11 PASS**(`TEST-RESULT.regression.json`, 첫 실행부터) |
| 재현 3개(`tests/repro_defects.py`) | 수정 전 0/3 → 수정 후 3/3 |

회귀 11개:
1. 중간 거래일 누락 거부
2. 기대보다 많은 · 시작일 앞 · 기대 밖 가격일 거부
3. 같은 날 다른 표기 거부
4. expected_days 계약(중복 · 순서 · 형식 · 시작일 · 네 필드 각각 누락/빈 값 · 인자 자체 누락)
5. JSON 같은 키 두 번 거부(CLI)
6. 첫날 유효 · 다음날 평가 누락 → INCOMPLETE · headline null · 공개 검사 통과
7. 전부 무효 → INVALID
8. 완전한 합성 3일 → MEASURED_COMPLETE
9. 비공개 입력 10개 각각 작업트리 안 → 거부(출력 안 생김)
10. 밖 링크 → 안 파일 · 안 링크 → 밖 파일 · `..` 상대경로 → 거부(밖 상대경로는 허용)
11. 공개 출력은 작업트리 안 허용

작업트리 안 시험 파일은 `tests/` 아래 임시 폴더에 만들고 시험이 끝나면 지웠습니다.

공개 전 비밀 검사(PRIVACY-0001 `guard.py`): 15개 중 시험 파일 3개만 걸렸습니다(`test_measure.py` 5건 · `test_regression.py` 2건 · `repro_defects.py` 1건). 모두 KIS 행 꼴을 흉내 낸 합성 키(`odno` · `order_no` · `access_token` · `raw_response`)이고 값은 `T0001` · `x` 같은 시험값입니다. 검사를 피하려고 고치지 않았습니다.

## 4. 남은 한계
- 실제 체결 원문 · 공개 비식별 배치 없음 → WAITING_DATA. 실측 수치 0개.
- `expected_days` 자체가 맞는지는 입력자가 책임집니다(공식 휴장일 원문은 이 환경에서 받지 못했음 · SOURCE-VERIFY-0001 T6). 도구는 가격 날짜와 정확히 같은지만 봅니다.
- PR #33의 나머지 결손(체결 시각은 주문 시각 하한, 현금배당 미지원, 용량 대기)은 그대로입니다.

## 다음 방향
- 자동 후속 TASK는 만들지 않습니다. 공개 비식별 실제 배치가 생기면 그때만 BASELINE 측정을 다시 시작합니다(`DATA-STATUS.json` next_trigger).
