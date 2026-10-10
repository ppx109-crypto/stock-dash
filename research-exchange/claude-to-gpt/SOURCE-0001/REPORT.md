# [클로드 결과] SOURCE-0001 — 기초 데이터 출처 · 가용시점 · 권한 감사

- 입력
  - PR #26 head `9bfc62720e1e89b10552268a997bbb6766c9aa48`
  - task SOURCE-0001 · chain MEAS-20261008 · round 7 · stage DATA-SOURCE-FEASIBILITY
  - source PR #25 head `bb188d57827341463efc24aec9a05c9cd88329f8`
- 저장소 기준 `e9a22ee`(main): 코드 선언 · 경로 · 파일 수만 읽었고, 자료 값은 읽지 않았습니다.
- 사전등록 잠금 `cd3a0b6`(09:16 KST)으로 분류 규칙을 증거 수집 전에 고정했습니다.
- **status: READY** — 뜻은 **A1~A6의 출처 · 결손 · 최소 승인 목록이 완전하다**는 것뿐입니다.
  - 자료를 확보했다는 뜻도, 전략을 검증했다는 뜻도 아닙니다.
  - `paper_validation_ready=false` · `live_approval=false`
- 데이터 API 호출 0회. 공식 문서는 읽기만 했습니다.

## 1. 결론 한 줄
지금 저장소에는 **시점이 증명된(point-in-time) 입력이 A1~A6 어디에도 없습니다.** 필요한 공식 출처는 대부분 있습니다(KRX Open API · DART OpenAPI · 한국투자증권 Open API · 법령). 다만 쓰려면 **사용자 승인(키 신청 · 수집 변경 · 모의 봇 기록 변경)과 앞으로 쌓는 기간**이 필요합니다.

## 2. 판정 표(16행 — 기계판독은 `SOURCE-MATRIX.json`)
| 행 | 내용 | 지금 보유 | 받을 수 있나 | 판정 | 최소 승인 · 다음 일 |
|---|---|---|---|---|---|
| A1-1 | 저장소 기존 일봉 · 시간봉 | 있음(수정주가 · 덮어씀 · 받은 시각 없음) | — | NOT_VERIFIED | (기존 자료 판정) |
| A1-2 | KIS 원주가 OHLCV(앞으로) | 없음 | 공식(원주가 = `fid_org_adj_prc` 1, 한 번 100건) | NEEDS_USER_APPROVAL | 원주가 일봉 append-only 수집 추가 |
| A1-3 | KRX Open API 일별매매정보(전 종목 · 원주가) | **수집기 코드만 있고 자료 0** | 공식(키 + API별 활용 신청 · 승인, 하루 1만 회) | NEEDS_USER_APPROVAL | 사용자가 키 · 활용 신청 |
| A2-1 | Universe(t) | 없음 | A1-3과 같은 자료(폐지 종목 포함) | NEEDS_USER_APPROVAL | A1-3과 같음 |
| A2-2 | 상장폐지 · 관리 · 거래정지 | 없음 | KIND · 정보데이터(웹, 조건 미확인) | NEEDS_USER_APPROVAL | 이용 조건 확인 뒤 경로 결정 |
| A2-3 | 기업행위(증자 · 감자 · 합병 · 분할) | 일부(dart-events, 판 · 받은 시각 없음) | DART 주요사항보고서 | NEEDS_USER_APPROVAL | 기존 수집을 append-only로 |
| A3-1 | DART rcept_no · 시각 · 정정 계보 | 일부(접수일 · 일부 접수번호) | list.json: rcept_no · 접수일 · report_nm 정정 표기 · rm 정/철. **접수 시각 없음 · 원 공시 연결 필드 없음** | NEEDS_USER_APPROVAL | 공시 수집이 rcept_no · report_nm · rm · 받은 시각을 판으로 남기게 |
| A4-1 | 모의 체결 · 미체결 | 없음(접수 2건만) | 공식(일별주문체결조회 모의 `VTTC0081R`/`VTSC9215R`) | NEEDS_USER_APPROVAL | 체결조회 기록 추가 + 원 주문번호 비공개 처리 |
| A4-2 | 신호 · 이론가 기록 | 일부(분 단위, 입력 판 없음) | — | NEEDS_USER_APPROVAL | 신호 기록에 inputs · cutoff_hash |
| A5-1 | 증권거래세 연도표 | 없음(`lab.py:39` 어림 0.25%) | 법령(시행령 제5조) | NOT_VERIFIED | 법령 본문으로 표 확정(읽기만) |
| A5-2 | 수수료 | 없음 | 확인 못 함 | NOT_VERIFIED | 계좌 요율 확인(비식별 요율만) |
| A5-3 | 가격제한 · 호가단위 | 없음(종가 어림) | ±30% · 절사 규칙은 확인, 호가단위표는 미확인 | NOT_VERIFIED | 규정 본문 읽기 |
| A5-4 | 유동성 · 시장충격 | 없음 | 과거 호가 이력 출처 없음 | NOT_VERIFIED | 충격 모형 결정 |
| A6-1 | 거래일 달력 | 어림(`idle_live.py:50` 직접 적은 휴장일) | A1-3 날짜 목록으로 대체 가능 | NOT_VERIFIED | A1-3 승인으로 해결 |
| A6-2 | 지수 일별 | 있음(받은 시각 · 판 없음) | 공식 | NOT_VERIFIED | A1-2와 같은 기록 승인 |
| A6-3 | calm · TWR · daily MTM 입력 | 없음 | A1 · A4 + 규칙 결정 | NEEDS_USER_APPROVAL | calm 규칙 결정 + A1-2 · A4-1 |

**"endpoint가 있다"와 "과거 원자료를 확보했다"는 따로 적었습니다.** AVAILABLE_PUBLIC_OFFICIAL은 `obtainable` 칸에만 쓰였고, AVAILABLE_EXISTING_READONLY인 행은 0입니다.

## 3. available_at · 정정 · 기업행위 · Universe(t) · 비용 · 체결 요구
- **available_at**
  - 일봉 · 지수: 공식 확정 시각을 확인하지 못했으므로 다음 거래일부터 씁니다.
  - 수급: 다음 거래일부터 씁니다.
  - DART: list.json이 날짜만 주므로 다음 거래일 09:00부터 씁니다. 공시 시각이 필요하면 KIND 공시 시각 경로를 따로 확인해야 합니다(NOT_VERIFIED).
- **정정**: DART 정정은 새 rcept_no로 오고 `report_nm`의 [기재정정] 등과 `rm`의 정 · 철 표시가 있지만, 원 공시를 가리키는 필드가 없습니다. 과거 시점의 '정정 전' 상태는 지금 다시 받아도 재현되지 않으므로, 앞으로 판을 남기며 쌓아야 합니다.
- **Universe(t)**: 현재 생존 종목 목록으로 대신하지 않습니다. KRX Open API 날짜별 전 종목(폐지 포함)이 유일하게 확인된 공식 경로이고, 저장소에는 아직 없습니다.
- **비용**: 고정 0.25% 어림 하나뿐입니다. 거래세는 연도 · 시장별로 바뀌었습니다(코스닥 2026 0.20% 조문은 검색 요약으로 확인, 2023~24 값은 미확정). 수수료 · 호가단위 · 충격은 미확인입니다.
- **체결**: 모의 체결조회 공식 경로는 있으나 현재 봇은 '접수'만 적습니다. 원 주문번호(ODNO) 공개 금지 처리가 먼저입니다.

## 4. KIS + DART 결합 게이트(수익률 숫자 없음)
1. DART 사건의 시점 재구성: **부분적.** rcept_no · 접수일은 됩니다. 시각 · 정정 계보 · 과거 정정 전 상태는 안 됩니다. → NEEDS_USER_APPROVAL
2. KIS 자료를 같은 available_at 규칙으로 정렬: 일 단위 규칙은 정할 수 있습니다. 그러나 지금 자료에는 받은 시각 · 판이 없고, 장중 자료는 과거가 없습니다. → NEEDS_USER_APPROVAL
3. KIS 단독 · DART 단독 · 결합 비교의 최소 입력: **아직 없습니다.** Universe(t)와 폐지 종목 가격이 0이기 때문입니다.
4. 필요한 것
   - KRX Open API 키 · 활용 승인
   - append-only 수집 변경 승인
   - 모의 체결 기록 승인
   - calm 규칙 결정
   - 비용 공식 표
   - KIND 이용 조건 확인
   - 그리고 **승인 뒤 앞으로 쌓는 기간**

## 5. 공개 / 비공개 분리
- **공개 가능**(비식별 파생): 날짜별 종목 목록, 원주가 OHLCV, 공시 메타(rcept_no · 날짜 · 종류 · 정정 표시), 가명 체결 요약, 비용 요율표, 수집 hash · 받은 시각
- **비공개**: 키 · 토큰 · 계좌번호 · 원 주문번호(ODNO) · 계좌 응답 원문, 그리고 재배포 조건이 확인되지 않은 KRX · KIND 원자료 파일(조건 확인 전까지 저장소에 원본을 올리지 않는 쪽이 안전)

## 6. 증거와 한계
- **E1**(저장소, 파일:행): `broker_kis.py:300-312` · `collect_prices.py:104-140` · `collect_krx_daily.py:1-12,23,26,58-62` · `collect_events.py:92-99` · `collect_shares.py:79` · `collect_dart_extra.py:1-13,26,115-119,140,189` · `paper_trade.py:405-410` · `collect_kis_extra.py:8,145` · `idle_live.py:50` · `collect_kis_intraday.py:71` · `lab.py:39 · 1271`
  - krx-data 파일 0개, 워크플로 없음, dart-events 437파일(파일 수만 셈)
- **E2**: 한국투자증권 공식 GitHub 예제를 직접 열람했습니다(기간별시세 · 일별주문체결조회 · README).
- **E2s**: OpenDART 개발가이드, KRX Open API 이용방법 · 약관, KIND, 법령정보센터, KRX 규정은 이 환경의 네트워크 정책으로 **직접 열지 못했습니다.** 공식 도메인 페이지의 검색 요약으로 대신했으므로, 그 값들은 다음 단계에서 원문으로 다시 확인해야 합니다.
- E4(저장소 주석만)인 사항은 AVAILABLE로 올리지 않았습니다. 예: 한투는 상장폐지 종목 일봉을 주지 않음, data.krx는 로그인이 필요함, DART 하루 2만 회.

## 7. 다음 한 단계(자동 수집 아님)
- **사용자 승인 목록**(우선순위 순)
  1. KRX Open API 키와 '유가증권/코스닥 일별매매정보' 활용 신청 — Universe(t) · 폐지 종목 · 원주가 · 달력을 한 번에 풀어 줍니다.
  2. 원주가 · 공시 판을 append-only로 남기는 수집 변경(DATA-0001 계약 적용)
  3. 모의 체결조회 기록 + 원 주문번호 비공개 처리
  4. calm 규칙 결정
- 승인 없이 할 수 있는 읽기 전용 한 단계: 거래세 · 호가단위 · 수수료 **공식 원문 표 확정**. 다만 법령 · 규정 원문을 열 수 있는 경로가 필요합니다. 이 환경에서는 막혀 있습니다.
- 기존 read-only 자료만으로 할 수 있는 BASELINE은 없습니다. 시점 증명 입력이 0이기 때문입니다.

## 다음 방향
- 사용자께서 위 승인 1번(KRX Open API 키 신청)을 하실지 정해 주시면, 그다음은 받기 전에 그 자료의 append-only 수집 계약(DATA-0001)을 붙이는 설계 · 사전등록입니다.
