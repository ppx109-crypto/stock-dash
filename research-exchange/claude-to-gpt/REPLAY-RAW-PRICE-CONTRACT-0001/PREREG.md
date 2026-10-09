# REPLAY-RAW-PRICE-CONTRACT-0001 — 클로드 사전등록(코드 · fixture 실행 전)

- 입력: GPT PR #85 head `467e3237`(REVIEW · TASK · receipt) · source PR #84 `5dc08c38`
- 일: 현재 수정 후보(PR #76 일봉 고침) **D1 + BASKET 체결 148건**을 공식 원주가 · 기업행동으로 재생하기 위한 준비입니다.
  - 데이터 계약 · 스키마 · 재생 어댑터 · 합성 fixture만 만듭니다.
  - 외부 호출 · 수집 · Train 재생 · NAV/수익률 계산은 0입니다. 15분봉은 범위 밖입니다.

## 1. 입력(PR #84 manifest 해시와 같음)
| 입력 | sha256 |
|---|---|
| PR #76 fixed_local_only.json | `0619fd234ef9386e419d3641add36b62acee8f03b848896da9e0e19a781e51d8` |
| PR #76 nav_train_control_old_fixed.csv | `007cebe625b316102df01f31acaf31a363bc60a541ce092871d0afbbc3107137` |
| 옛 nrl-cache.pkl(가격 · 달력) | `84030fcf259288dc4e0c698f7694a99a8231f49d5ca0e726380ec443dcb94560` |
| PR #82 tick_check.py · tick-check.json | `2be9df1fe2377f45228261f5c626bf5a653035dd23390dd089912e8ebe604dbd` · `6166b3eafd055730aa9b41c93843453e19d36eb727e202b507fc9f5d31aa785b` |
| PR #84 REPORT · manifest · fill-validity · position-accounting | `ee6b5ce4abf1c1c86c4c84909ba125e92c5abed19cf01e3653e3dd7262797014` · `fae3ac1b048f3b99c19991d6fdde193ff8db76705c331e5854585ca7624d7799` · `2ec09c888019b28d29ed3c67e30a3aba6f869d52e05643450a1b4963d58ea205` · `b8320bdf6cc2cd1663202a1802b200a58056918c7f87605ae249be6194a9b871` |
| PR #84 kernel2.py · cost_contract.py | `a1b0802865656ed98eaf98bd347f0c174d8895f26d97bd85836cfcebf6ae80ac` · `c8c006c10fead5db60861f89c8e50304dfe9918c03ce11c32c74beec3496aaae` |
| salt(로컬 · 공개는 sha256) | `eb7b7d0859a3a81b83e18f49d78248b697089fc286096655938908408d08e4eb` |

**코드 · 스키마(이 커밋으로 고정)**
| 파일 | sha256 |
|---|---|
| code/targets148.py | `fc2137e3f0eb0f9a5fb4790dd99aa39add707db1a92198dce1a46cd16adf43e7` |
| code/raw_replay.py | `0527f42ebe47b0b799e0887c5795ca98949f646f7a4846cd3eb6f83100e5d348` |
| code/fixtures_test.py | `c6460e69ae13fb283b4b17c266ed47d5c5ae127e453bd0952354351dbff671e6` |
| code/collector_interface.py | `6e13f610d13ced427c0621f3e497b61d3143fd141ff6ab8982660671c9efff29` |
| code/contract_evidence.py | `fe1240e27c57fb25a73df054721fe184aa7a2ba7798973fe67e12f55ea3defbf` |
| schema/raw-price-response.schema.json | `aae99fb1d753ffc82811d096604fd8adb678fafa24f191ab61ec472dc7cf3e45` |
| schema/corporate-action.schema.json | `e82efc4af6ae15512680e4f51906b096428383f1405e0ee7e6c04e5a89bf8244` |

## 2. 148체결 재구성 · 분모
- PR #76 원장 `trades`(날, 종목, 방향, 수량)를 D1 · BASKET 순서로 읽습니다. 체결가는 그날 저장 종가입니다(PR #76 재생 규칙).
- 반드시 재현할 분모(아니면 BLOCKED):
  - D1 매수 52 · 매도 71
  - BASKET 매수 12 · 매도 13
  - 합 148 · off-tick 23 · on-tick 125
- 함께 냅니다: 고유 (종목, 날짜) · 고유 종목 · 고유 날짜 · off-tick 고유 (종목, 날짜)
- 통제 원장은 재생 대상이 아닙니다(비교 메타데이터).

## 3. 공개 · 로컬 경계
- 공개: 개수 · 비율 · `fill_id → sha256(salt|종목|날짜|방향)` 앞 16자 · salt sha256 · 스키마 · 코드 해시
- 로컬 전용(커밋 안 함): `targets_local_only.json`(실제 종목 · 날짜 · 수량 · 저장 종가) · salt · 앞으로의 API 응답 캐시

## 4. 공식 자료 스키마(`schema/`)
- KIS `FHKST03010100` 원(`FID_ORG_ADJ_PRC='1'`) · 수정(`'0'`) 쌍입니다.
  - 기록: 요청 · 조회 시각 · 요청 sha256 · 캐시 sha256 · output2 칸(stck_bsop_date · 시/고/저/종가 · 거래량 · 있으면 flng_cls_code · prtt_rate · mod_yn)
  - pair_check(선택이 실제로 다른지)를 둡니다.
  - 칸 이름은 저장소 코드 근거입니다. 공식 문서 재확인은 실제 실행 TASK에서 합니다.
- DART 주요사항 칸: 접수번호 · 접수일 · 보고서명(로컬) · 정정 여부 · 원 접수 · kind · ratio · 기준일 · 효력일 · 상장일 · 단주 현금 · 접수 시각(없으면 null → same_day_pit=false) · 캐시 sha256

## 5. 재생 불변식(`code/raw_replay.py`)
- 체결가 = 그날 공식 원주가 종가 · 호가 배수입니다. 아니면 `INVALID_OFFICIAL_RAW`이고 체결하지 않습니다.
- 원/수정 응답이 기업행동 영향 구간에서 같으면 `UNKNOWN_SELECTION_UNSUPPORTED`입니다.
- 매수 수량 = floor(min(의도 금액, 비용 포함 현금 한도) ÷ 원주가)입니다. 줄이면 `BUY_REDUCED`입니다.
- 매도 수량 ≤ 기업행동 조정 뒤 보유입니다. 넘으면 `SELL_CAPPED`이고, 음수는 금지입니다.
- 비용 · 세금 = 원주가 × 원수량 × rate(실제 실행은 kernel2.Costs · 비용 2배)
- 일별 MTM = 원주가 × 수량입니다. 값이 없으면 `UNKNOWN_MTM_STALE`입니다.
- 기업행동: 효력일 장 시작 전에 `CA_QTY`(수량이 바뀌는 사건만)와 `CA_CASH`(단주 현금 칸이 있을 때)를 남깁니다.
  - 단주 현금 칸이 없으면 `UNKNOWN_CASH_IN_LIEU`, 필수 칸이 없으면 `UNKNOWN_CA_FIELDS`(수량을 바꾸지 않음)입니다.
- 정정공시는 원 접수로 묶고 최신을 쓰며, 사슬을 보존합니다.
- 15분봉 입력은 `OUT_OF_SCOPE_15M`으로 거부합니다.
- 두 경로 항등식: 날마다 쌓은 현금 = 기초 − 매수대금 − 매수비용 + 매도대금 − 매도비용 + 현금조정. 수량 = 매수 − 매도 + 수량조정. 체결가는 모두 호가 배수입니다.

## 6. 합성 fixture(`code/fixtures_test.py`)와 기대 판정
| # | 사례 | 기대 |
|---|---|---|
| 1 | 기업행동 없음(원 = 수정) | 상태 OK · 손으로 쓴 현금식 = 어댑터 · 수량 맞음 |
| 2 | 액면분할 1→5 | 과거 수정주가 off-tick · 효력일 수량 9 → 45 · 수량 항등식 |
| 3 | 감자 10→1 | 25주 → 2주 + 단주 현금 25,000원(칸 있을 때) · 현금 항등식 · 칸 없으면 UNKNOWN_CASH_IN_LIEU |
| 4 | 무상(기준일 없음) · 유상(효력일 없음) | 둘 다 UNKNOWN_CA_FIELDS |
| 5 | 원/수정 같은 응답(효력일 앞) | UNKNOWN_SELECTION_UNSUPPORTED · 그날 매수 0 |
| 6 | 원주가 호가 밖 | INVALID_OFFICIAL_RAW |
| 7 | 정정공시 | 1개 사슬 · 최신 비율 5 · 사슬 [원, 정정] · same_day_pit=false |
| 8 | 비용 · 세금 | 손으로 쓴 현금식 = 어댑터 · 비용 합 = (원 notional) × rate · 체결가 호가 배수 |
| 9 | 한도 · 음수 | BUY_REDUCED · SELL_CAPPED · 현금 ≥ 0 · 끝 수량 0 |
| 10 | 15분봉 입력 | OUT_OF_SCOPE_15M |

## 7. READY / BLOCKED · 다음 실행
- READY 조건: 148 · 23/125 재현 + fixture 10/10 통과 + 외부 호출 0 · Train 재생 0
- BLOCKED 조건: 입력 해시 불일치 · 148/23 재현 실패 · 필요한 회계 칸 없음
- 다음 실제 실행의 결손 자격 이름: `KIS_APP_KEY` · `KIS_APP_SECRET`(시세만) · `DART_CRTFC_KEY`. 이 세션에는 없습니다(PR #82).
- 예상 호출 상한은 `collector_interface.py`가 계산합니다(호출은 안 함).
- 버그 수정이 필요하면 첫 결과를 남기고, 사유 · 전후 해시 · 재실행 횟수를 적습니다.
