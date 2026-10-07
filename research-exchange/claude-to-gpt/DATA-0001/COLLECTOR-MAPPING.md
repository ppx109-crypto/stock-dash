# COLLECTOR-MAPPING — 기존 수집 · 모의주문 코드 → 계약 필드(읽기만, 실행 · 수정 안 함)

- 기준: 저장소 `origin/main` @`5998f42e9acbb0fd3912ae9ebc63c5e1edfb39dc`의 코드
- 표기
  - ✔ 지금도 있음
  - △ 파일 단위 · 추정만
  - ✘ 없음
- 공통으로 빠진 봉투 필드: `available_at`(레코드별), `version` · `revision_of` · `is_correction`(덮어씀), `raw_payload_sha256` · `normalized_sha256`, `ingest_run_id`, `collector_version`

| 원천 · 코드 | 지금 저장하는 것 | as_of | available_at | fetched_at | 판 · 정정 | 조정 | 계약 레코드 | 미지원 |
|---|---|---|---|---|---|---|---|---|
| 일봉 `collect_prices.py` → `broker_kis.daily`(`inquire-daily-itemchartprice`, `FID_ORG_ADJ_PRC='0'`) | [날짜, 종가] | ✔ 날짜 | ✘ | △ 파일 `fetched`(날짜) | ✘ 지난 값이 바뀌면 처음부터 다시 받아 덮어씀(`collect_prices.py:104-140`) | **수정주가**(`broker_kis.py:300`) | PRICE_BAR_ADJ로만 대응. RAW는 `FID_ORG_ADJ_PRC='1'` 조회가 따로 필요 | 시가 · 고가 · 저가(이 경로는 종가만), 원주가 |
| 거래량 · 고저 `collect_volumes.py` | [날짜, 거래량, 거래대금, 고가, 저가] | ✔ | ✘ | △ | ✘ | 표시 없음 | PRICE_BAR_ADJ/RAW 일부 | 조정 여부 |
| 코스닥 일봉 `collect_kosdaq.py` | 시가 · 고가 · 저가 · 종가 · 거래량 · 거래대금 | ✔ | ✘ | △ | ✘ | 수정주가(`:5`) | PRICE_BAR_ADJ | 원주가 |
| 시간봉 `collect_kis_hourly.py`(`FHKST03010230`) · `collect_hourly.py`(야후) | YYYYMMDDHH, OHLCV | ✔ 봉 시각 | ✘(장 끝난 날 봉만 저장한다는 규칙만 있음) | ✘ | 덧붙임(같은 줄은 집합으로 합침) | 기록 없음 | PRICE_BAR_*(session=시간봉) | 조정 여부 · 받은 시각 |
| 수급 `collect_investor_history.py` | [date, 개인, 외국인, 기관, 투신, 연기금, 사모, 종가] | ✔ | ✘ | ✘ | ✘ | — | INVESTOR_FLOW | 확정 · 수신 시각 |
| 공시 `collect_events.py`(DART list) | {date=rcept_dt, kind, title} | ✔ 접수일 | ✘(시각 없음 → 계약상 다음날 00:00부터) | △ fetched · recent | ✘ 정정 연결 없음 | — | DART_FILING(time_known=false) | rcept_no 저장 안 함, 정정 원본 연결 |
| 주식수 `collect_shares.py` | [접수일, 주식수] | ✔ 접수일 | △(접수일 = 공개일이라 적혀 있음) | △ | ✘ | — | FINANCIAL 비슷(별도 종류 필요) | rcept_no 전체 · 시각 |
| 목표가 `collect_opinion_history.py` / `broker_kis`(`FHKST663300C0`) | {date, member, target, opinion} | ✔ | ✘ | △ | ✘ | — | (새 종류 필요: OPINION) | 공개 시각 |
| 대차 · 원종가 `collect_kis_extra.py` | rows{date, …, 종가} | ✔ | ✘ | △ | ✘ | 원주가(caps.py 주석) | PRICE_BAR_RAW 일부(종가만) | 시가 · 고가 · 저가 · 받은 시각 |
| Universe | 없음(현재 파일 · 현재 목록만) | — | — | — | — | — | UNIVERSE_SNAPSHOT · SECURITY_EVENT | **출처 자체가 없음** |
| 거래정지 · 기업행동 비율 | 없음 | — | — | — | — | — | TRADING_STATUS · CORP_ACTION | **출처 자체가 없음** |
| 비용 | `lab.py:39 COST = 0.25`(어림) | — | — | — | — | — | COST_SCHEDULE | 출처 · 적용기간 |
| 모의주문 `paper_trade.py`(`order-cash`, `VTTC0012U/0011U`) | 주문 장부 {key, at(분), code, side, qty, status='접수', **order_no**, price} | ✔ 분 단위 | ✔(at) | — | — | — | ORDER_EVENT(INTENT · ACCEPTED) | 체결 조회 없음(FILLED · 체결가 · 수수료 없음), seq 없음 |

## 발견(운영 코드 · 자료 — 고치지 않고 보고만)
1. **원 주문번호가 장부에 저장됨**: `paper_trade.py:410`이 `order_no`(KIS 응답 `ODNO`)를 주문 장부에 적습니다. 장부는 저장소에 커밋되는 경로입니다.
   - 계약상 공개 금지 항목이라 다음 판 검증기에서 막아야 합니다(EVIDENCE-CONTRACT 4장).
   - 운영 코드 · 이미 커밋된 기록은 이번 범위 밖이라 열람 · 수정하지 않았습니다. **사용자 · GPT 결정이 필요**합니다.
2. **보유 수량을 '접수' 때 바꿈**: `paper_trade.py:405-407`. 체결 확인 없이 held가 바뀌므로 OBSERVED fill 증거가 될 수 없습니다(MEAS-0001에서도 확인).
3. 일봉 원천이 **수정주가 한 가지뿐**입니다. 원주가 OHLC를 따로 받는 경로가 없습니다(G1 · G2).

## 앞으로 필요한 최소 권한 · 자료(실행하지 않음, 승인 필요)
| 필요 | 무엇 | 승인 주체 |
|---|---|---|
| A1 | 원주가 OHLCV 조회(`FID_ORG_ADJ_PRC='1'`)를 장 뒤에 받아 PRICE_BAR_RAW로 append — 레코드마다 fetched_at · 원문 hash | 사용자(수집기 추가 · 워크플로) |
| A2 | 날짜별 상장 목록 · 거래정지 · 기업행동 비율 출처(KRX 정보데이터 등) | 사용자(새 원천) |
| A3 | DART 공시 수집에 `rcept_no` 보존 · 정정 원본 연결 | 사용자(수집기 수정) |
| A4 | 모의투자 체결 조회(일별 체결 내역)로 FILLED · 체결가 · 수수료를 가명 evidence_ref와 함께 기록, `order_no` 비공개 보관 | 사용자(운영 봇 변경) |
| A5 | 수수료 · 거래세 schedule의 출처 문서와 적용기간 | 사용자 · 문서 |
| A6 | calm 문턱 규칙 결정(G4) | 사용자 · GPT |
