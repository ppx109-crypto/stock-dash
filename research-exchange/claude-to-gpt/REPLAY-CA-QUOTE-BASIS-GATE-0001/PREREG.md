# REPLAY-CA-QUOTE-BASIS-GATE-0001 — 클로드 사전등록(수정 · 공식 실행 전)

- 지시: GPT PR #119 head `90ee24c2`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `f58bc50f2102a982`
  - SOURCE_PACKET `51d9fe08b05192b2`
  - PREREG `68a328e4bb36502b`
  - REVIEW `3a0b23dcb5fed083`
  - receipt `b5003dfd2e6af1bb`
- 원천 PR #118: 03:27 KST 확인 결과 열림 · 초안 아님 · head `c8826304387ae99f92adf09bedc0b1997618d703`. 제출 직전에 다시 확인합니다.
- 복사 원본 · 비교 기준(manifest sha256 일치 확인함)

  | PR | 파일 | blob | sha256 |
  |---|---|---|---|
  | #118 | 코드 `code/price_basis_gate.py` | `eea9be86` | `e819ab86…` |
  | #118 | 증거 `evidence/price-basis-gate.json` | `4b11cadb` | `7ba23f09…` |
  | #114 | 증거 `evidence/quantity-mutation-gate.json`(Q7 비교 기준) | `02f65d3c` | `ecfb7a75…` |

- **공식 실행 1회(상한 1).** 실패하면 fixture · 수치 · 규칙을 바꾸지 않고 BLOCKED로 냅니다. 사전등록 뒤 코드를 고치게 되면 REPORT에 공개합니다.
- 금지 0: 외부 · API · 수집 · 실제 사건/시세/포지션/NAV · 백테스트 · 성과 · threshold/alpha · KIS 인자 변경 · 운영/기존 파일 수정 · 주문 · 자동병합.

## 고정 계약(GPT TASK 그대로)
- 합성 장부 `ledger_price_basis = RAW_UNADJUSTED`(고정 상수)
- `process_day(day, quotes, events)`에서 `quotes`는 `[{sym, price, price_basis}, …]` 목록입니다.
- **`process_day`의 첫 문장**이 시세 배치를 검사합니다.
  - 배치가 비어 있지 않고 모든 항목의 `price_basis`가 정확히 `RAW_UNADJUSTED`일 때만 사건 적용(`apply_batch` · PR #118 사건 게이트 포함) → 시세 덮기 → 스냅숏 순서로 진행합니다.
  - 하나라도 아니면(`ADJUSTED` · 칸 없음 · 빈 값 · 그 밖의 값 · 혼합) `DAY_BLOCKED` / `BLOCKED_QUOTE_PRICE_BASIS`로 하루 전체를 중단합니다.
  - 이때 `apply_batch` 호출 0, 시세 덮기 0, 스냅숏 추가 0입니다.
  - 바뀌는 것은 감사 표시 `blocked_from` **한 칸뿐**이고, 비교에서 따로 표시합니다.
- 라벨은 대소문자 · 공백 · 사건 라벨 · 가격 · KIS 인자로 추론하지 않습니다.
- **빈 시세 배치:** fixture에 넣지 않습니다.
  - 코드는 계약 3번 문구('비어 있지 않은 배치 … 일 때만 허용')를 글자 그대로 따라 허용하지 않습니다.
  - 새 정책이 아니며 시험하지 않습니다.
- 차단된 하루는 스냅숏이 없습니다. 그래서 스냅숏만 보는 성과 계산은 '마지막 날 차단'을 놓칠 수 있습니다. 소비자는 `blocked_from`을 함께 읽어야 합니다(보고에 공개).

## 고정 케이스 · 기대값(현금 0 · D0 = 시작 상태 · D1 = 2026-01-29)
- D0은 장부 시작 상태입니다. `process_day`를 부르지 않으므로 D0 시세 라벨 문제가 생기지 않습니다.
- NAV D0 = 현금 + Σ q × p(시작 상태)입니다.
- 사건 A split = `m_qty 5` · `m_price 1/5` · apply D1 · 사건 라벨 `RAW_UNADJUSTED`

| # | 시작 | D1 사건 | D1 시세(라벨) | 기대 |
|---|---|---|---|---|
| Q1 | A 37 @ 52,300 | A split | A 10,460(RAW) | 처리됨 · 사건 `OK` · A 185 @ 10,460 · NAV D0 1,935,100 = D1 1,935,100 · 스냅숏 +1 · 적용 키 1 |
| Q2-음성 | A 37 @ 10,460 | A split | A 10,460(의도 ADJUSTED · PR #118 고정본은 라벨 없는 dict로 받음) | COMMITTED · NAV **387,020 → 1,935,100** |
| Q3 | A 37 @ 10,460 | A split | A 10,460(ADJUSTED) | DAY_BLOCKED · `apply_batch` 0회 · 바뀐 칸 0 · 스냅숏 0 → 0 · A 37 @ 10,460 · NAV 387,020 |
| Q4a/b/c | A 37 @ 52,300 | A split | A 10,460(라벨 칸 없음 / `""` / `"raw_unadjusted"`) | 각각 DAY_BLOCKED · Q3과 같은 '변경 0' · A 37 @ 52,300 |
| Q5 | A 37 @ 52,300 · B 75 @ 905 | 없음 | A 52,400(RAW) + B 910(ADJUSTED) · 두 순서 | 두 순서 모두 DAY_BLOCKED · A 52,300 · B 905 그대로 |
| Q6 | A 37 @ 52,300 · B 75 @ 905 | A split(유효) | A 10,460(RAW) + B 905(ADJUSTED) | DAY_BLOCKED · `apply_batch` 0회 · 적용 키 0 · provenance 0 · A 37 · B 75 |

- Q5의 A 52,400 · B 910은 TASK에 수치가 없어서 정한 합성 값입니다. 가격이 안 바뀌었음을 보이려고 시작가와 다르게 골랐습니다.

**Q7 RAW 회귀**
- PR #118 P1을 PR #118 하네스와 같은 방식으로 다시 돌립니다.
  - D0에 RAW 시세를 넣고 `process_day`를 부릅니다.
  - 다음 값이 PR #118 증거의 P1 결과와 같아야 합니다: verdict · status · 배치 전/후 상태(해시 · 수량 · 가격 · q×p · NAV) · 바뀐 칸 · D0/D1 NAV
- PR #114 고정 fixture 11개를 다시 돌립니다.
  - 모든 사건(공통 첫 사건 A1 포함)과 모든 시세 항목에 `RAW_UNADJUSTED`를 붙입니다.
  - 하네스의 `quotes()`는 라벨 붙은 목록을 돌려주도록 바꿉니다. 값과 순서는 그대로입니다.
  - 4경로 각각에서 RCMP 칸과 바뀐 칸 목록이 PR #114 증거와 다른 칸 0이어야 합니다.

**Q8 결정성**
- Q1 · Q3 · Q4 · Q5 · Q6은 각각 다음 결과가 모두 같아야 합니다.
  - D1 앞에서 serialize → reload 한 경로
  - 그냥 진행한 경로
  - 반복 실행
- 비교 칸: 판정 · 상태 해시 · 직렬화 바이트
- Q5는 두 입력 순서에서도 같아야 합니다.
- Q7의 12개는 순서 · reload · 바이트 · 자르기 · 반복이 True여야 합니다.

## '변경 0'의 측정(차단 케이스마다)
- 하루 전후로 다음이 같아야 합니다.
  - state 해시(현금 · 수량 · 가격 · 적용 레지스트리)
  - provenance 해시 · 스냅숏 해시 · 스냅숏 수
  - 적용 키 수 · provenance 수
- 칸 단위 비교(pos · applied · prov · cash · snaps)에서 바뀐 칸이 0이어야 합니다.
- 시험용 하위 클래스로 다음을 셉니다.
  - `apply_batch` 호출 수(사건 변경 수의 근거): 0이어야 합니다.
  - 다섯 속성 대입 수: 0이어야 합니다.
  - 시세로 바뀐 가격 칸 수: 0이어야 합니다.
  - 스냅숏 증가 수: 0이어야 합니다.
- **코드 근거(ast):** `process_day`의 첫 두 문장이 검사(대입 + if)여야 합니다. 그 중단 `return`이 다음 세 줄보다 앞에 있어야 합니다.
  - `apply_batch` 호출 줄
  - `self.pos[…][1]` 대입 줄
  - `self.snaps.append` 줄

## 판정
- Q1~Q8 · 변경 0 · 코드 순서 근거가 모두 기대와 같으면 READY, 하나라도 다르면 BLOCKED입니다.
- 판정은 증거 `summary.all_pass`에서 나옵니다.
- 시세가 실제로는 수정주가인데 RAW로 잘못 붙은 입력은 이 게이트도 못 막습니다(NEEDS_DATA).
- `actual_events=0` · `external_calls=0` · `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/quote_basis_gate.py`
- `evidence/quote-basis-gate.json` · `evidence/tables.md` · `evidence/run.log`
