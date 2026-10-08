# REPLAY-CA-PRICE-BASIS-GATE-0001 — 클로드 사전등록(수정 · 공식 실행 전)

- 지시: GPT PR #117 head `dbafc8aa`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `ada9ab1b28df718a`
  - SOURCE_PACKET `5352492ad3fbf5d0`
  - PREREG `2e6220d4634f2a10`
  - REVIEW `651af9d5b122005a`
  - receipt `93554612b3b9dd46`
- 원천 PR #116: 03:19 KST 확인 결과 열림 · 초안 아님 · head `dc4335554b45ba8f257596acab44a0f6d2e985ff`. 제출 직전에 다시 확인합니다.
- 복사 원본 PR #114 고정본 — blob과 PR #114 manifest sha256이 일치합니다.

  | 파일 | blob | sha256 |
  |---|---|---|
  | 코드 | `58417375` | `babf0963…` |
  | 증거 | `02f65d3c` | `ecfb7a75…` |

- **공식 실행 1회(상한 1).** 실패하면 수치 · 규칙을 바꾸지 않고 BLOCKED로 냅니다.
- 금지 0: 외부 · API · 수집 · 실제 자료/사건/가격/포지션/NAV · 백테스트 · 성과 · threshold/alpha · 운영/기존 파일 수정 · 주문 · 자동병합.

## 고정 계약(GPT TASK 그대로)
- **사건 단위 라벨:** 모든 사건에 `price_basis`가 있어야 합니다. 배치는 모든 사건의 라벨이 정확히 `RAW_UNADJUSTED`일 때만 PR #114 경로로 들어갑니다.
  - 문자열이 완전히 같아야 합니다. 대소문자를 고치거나 앞뒤 공백을 지우거나 추론하지 않습니다.
- 그 밖의 경우는 `BLOCKED_PRICE_BASIS`로 **배치 전체를 중단**합니다. 해당하는 경우: `ADJUSTED` · 칸 없음 · 빈 값 · 그 밖의 값이 하나라도 있을 때
  - 라벨이 틀린 사건의 status는 `BLOCKED_PRICE_BASIS`입니다.
  - 같은 배치의 RAW 사건은 `NOT_EVALUATED`이며, 아무 검사도 하지 않습니다.
- 이 검사는 `apply_batch`의 **첫 문장**입니다.
  - 해시 계산 · 정규화 · 중복/충돌 · 수량 게이트 · `check()`보다 앞에 둡니다.
  - 중단할 때 바꾸는 것은 성과 차단 표시(`blocked_from`)뿐입니다. 앞선 계약과 같으며, 따로 기록합니다.
- 라벨은 상태 해시 · 의미키 · payload에 넣지 않습니다. 그래서 RAW 경로의 해시는 PR #114와 같아야 합니다.
- 합성 `m_price = 0.2`는 정확한 소수 문자열 `Fraction("0.2") = 1/5`로 넣습니다.
  - 파이썬 float `0.2`는 PR #114 게이트가 `BLOCKED_INPUT`으로 거부합니다(PR #116 GAPS의 충돌 그대로).

## 고정 케이스 · 기대값(현금 0 · 합성 날짜 D0 = 2026-01-28, D1 = 2026-01-29)
사건 공통: A split `m_qty = 5` · `m_price = 0.2` · apply_date D1. D0에는 사건 없이 시세만 넣습니다.

| # | 시작 | D1 배치 · 라벨 | D1 시세 | 기대 |
|---|---|---|---|---|
| P1 | A 37 @ 52,300 | 분할 · `RAW_UNADJUSTED` | A 10,460 | COMMITTED · `OK` · 배치 직후 q 185 · p 10,460 · q×p 전후 1,935,100 · 적용 키 1 · D1 NAV 1,935,100 |
| P2-음성 | A 37 @ 10,460 | 분할(PR #114 고정본 · 라벨 무시) | A 10,460(수정) | COMMITTED · 배치 직후 q 185 · p 2,092 · D1 시세를 덮으면 **NAV 387,020 → 1,935,100**(왜곡 기록) |
| P2-새 | A 37 @ 10,460 | 분할 · `ADJUSTED` | A 10,460(수정) | BATCH_ABORTED · `BLOCKED_PRICE_BASIS` · q 37 · p 10,460 · D1 NAV 387,020 · 변경 0 |
| P3a/b/c | A 37 @ 52,300 | 분할 · 라벨 칸 없음 / `""` / `"raw_unadjusted"` | 없음 | 각각 BATCH_ABORTED · `BLOCKED_PRICE_BASIS` · q 37 · p 52,300 · 변경 0 |
| P4 | A 37 @ 52,300 · B 75 @ 905 | A 분할 `RAW_UNADJUSTED` + B 병합 1/5 `ADJUSTED` · 두 입력 순서 | 없음 | 두 순서 모두 BATCH_ABORTED · A `NOT_EVALUATED` · B `BLOCKED_PRICE_BASIS` · A 37 · B 75 · 변경 0 |

**P5 RAW 회귀**
- PR #114 증거의 고정 fixture 11개(M1~M4 · K1~K3 · Q1~Q4)를 다시 돌립니다. 입력은 PR #114 증거에서 읽고, 모든 사건에 `RAW_UNADJUSTED`를 붙입니다.
- 4경로 각각에서 다음 값이 PR #114 증거와 다른 칸이 0이어야 합니다.
  - verdict · 키별 status
  - 배치 전후/최종 state·prov 해시
  - 수량 · 적용 키 · provenance A · 성과
  - 바뀐 칸 목록
- 순서 · reload · 반복 · 바이트 · 자르기 불변도 True여야 합니다.
- 시작 보유는 PR #114 증거 `start_pos`가 있으면 그 값을 씁니다. 없으면 입력에 C가 있을 때 C 포함 보유(PR #112 K3와 같음), 아니면 A · B 보유입니다.

## '변경 0'의 측정(차단 케이스마다)
- 배치 전후에 다음을 비교해 모두 같아야 합니다.
  - state 해시(현금 · 수량 · 가격 · 적용 레지스트리)
  - provenance 해시 · 스냅숏 해시
  - 적용 키 수
  - 칸 단위 비교(pos 수량 · 가격, applied, prov, cash, snaps)
- `apply_batch`가 도는 동안 `pos` · `applied` · `prov` · `cash` · `snaps`에 대입한 횟수를 셉니다(시험용 하위 클래스). 0이어야 합니다.
- **코드 근거(정적):** `apply_batch` 본문에서 가격기준 검사 줄이, 위 다섯 속성에 대한 어떤 대입 줄보다 앞에 있어야 합니다(ast로 줄 번호 비교).

## 판정
- P1~P5 · 변경 0 · 코드 순서 근거가 모두 기대와 같으면 READY, 하나라도 다르면 BLOCKED입니다.
- 판정은 증거 JSON `summary.all_pass`에서 나옵니다.
- READY여도 실제 가격 라벨의 원천 · available_at · 정정 · 날짜 · 배수 변환기는 검증하지 않습니다.
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/price_basis_gate.py`
- `evidence/price-basis-gate.json` · `evidence/tables.md` · `evidence/run.log`
